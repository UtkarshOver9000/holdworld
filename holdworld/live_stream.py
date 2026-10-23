"""Optional Plivo bidirectional-stream receiver for a real test call.

This adapter records event counts and DTMF metadata only. Inbound audio payloads
are never written to disk. Configure TLS/WSS at the public reverse proxy.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import json
import os
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

app = FastAPI(title="HoldWorld Plivo Stream Adapter")
TOKEN = os.environ.get("HOLDWORLD_STREAM_TOKEN", "")
PUBLIC_WSS = os.environ.get("HOLDWORLD_PUBLIC_WSS", "")
ACTIVE: dict[str, dict[str, Any]] = {}
CALLS: dict[str, WebSocket] = {}
WATCHERS: set[WebSocket] = set()


def _authorized(value: str | None) -> bool:
    return bool(TOKEN) and bool(value) and hmac.compare_digest(value, TOKEN)


async def _broadcast(event: dict) -> None:
    stale = []
    payload = json.dumps(event, separators=(",", ":"))
    for ws in WATCHERS:
        try:
            await ws.send_text(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        WATCHERS.discard(ws)


@app.get("/health")
async def health():
    return {"ok": True, "active_streams": len(ACTIVE), "public_wss_configured": bool(PUBLIC_WSS),
            "token_configured": bool(TOKEN)}


@app.post("/plivo/answer")
async def answer(token: str | None = None):
    if not _authorized(token):
        raise HTTPException(status_code=403, detail="invalid stream token")
    if not PUBLIC_WSS.startswith("wss://"):
        raise HTTPException(status_code=503, detail="HOLDWORLD_PUBLIC_WSS must be a public wss:// URL")
    stream = f"{PUBLIC_WSS.rstrip('/')}?token={token}"
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
           "<Response><Stream bidirectional=\"true\" keepCallAlive=\"true\" "
           "contentType=\"audio/x-mulaw;rate=8000\">" + stream + "</Stream></Response>")
    return Response(content=xml, media_type="application/xml")


@app.websocket("/plivo/stream")
async def plivo_stream(ws: WebSocket):
    if not _authorized(ws.query_params.get("token")):
        await ws.close(code=1008)
        return
    await ws.accept()
    stream_id = None
    try:
        while True:
            event = json.loads(await ws.receive_text())
            kind = event.get("event")
            if kind == "start":
                start = event.get("start", {})
                stream_id = start.get("streamId")
                if not stream_id:
                    await ws.close(code=1003)
                    return
                ACTIVE[stream_id] = {"call_id": start.get("callId"), "started_at": time.time(),
                                     "media_frames": 0, "audio_bytes_seen": 0, "dtmf": [],
                                     "encoding": start.get("mediaFormat", {}).get("encoding"),
                                     "sample_rate": start.get("mediaFormat", {}).get("sampleRate")}
                CALLS[stream_id] = ws
                await _broadcast({"type": "started", "stream_id": stream_id, "call_id": start.get("callId")})
            elif kind == "media" and stream_id in ACTIVE:
                payload = event.get("media", {}).get("payload", "")
                # Count only; never decode or persist customer audio.
                ACTIVE[stream_id]["media_frames"] += 1
                ACTIVE[stream_id]["audio_bytes_seen"] += (len(payload) * 3) // 4
            elif kind == "dtmf" and stream_id in ACTIVE:
                digit = str(event.get("dtmf", {}).get("digit", ""))
                if re.fullmatch(r"[0-9*#A-D]", digit):
                    ACTIVE[stream_id]["dtmf"].append(digit)
                    await _broadcast({"type": "dtmf", "stream_id": stream_id, "digit": digit})
            elif kind == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        if stream_id:
            summary = ACTIVE.pop(stream_id, {})
            CALLS.pop(stream_id, None)
            await _broadcast({"type": "stopped", "stream_id": stream_id,
                              "media_frames": summary.get("media_frames", 0),
                              "dtmf_count": len(summary.get("dtmf", []))})


@app.get("/live")
async def live(token: str | None = Header(default=None, alias="X-HoldWorld-Token")):
    if not _authorized(token):
        raise HTTPException(status_code=403, detail="invalid stream token")
    return {sid: {k: v for k, v in row.items() if k != "audio_bytes_seen"} for sid, row in ACTIVE.items()}


@app.post("/live/{stream_id}/dtmf")
async def send_dtmf(stream_id: str, body: dict, token: str | None = Header(default=None, alias="X-HoldWorld-Token")):
    if not _authorized(token):
        raise HTTPException(status_code=403, detail="invalid stream token")
    digits = str(body.get("digits", ""))
    if not digits or not re.fullmatch(r"[0-9*#A-D]+", digits):
        raise HTTPException(status_code=422, detail="digits must contain only DTMF characters")
    ws = CALLS.get(stream_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="stream is not active")
    await ws.send_text(json.dumps({"event": "sendDTMF", "dtmf": digits}))
    return {"sent": True, "stream_id": stream_id, "digits_count": len(digits)}


@app.post("/live/{stream_id}/audio")
async def play_audio(stream_id: str, body: dict, token: str | None = Header(default=None, alias="X-HoldWorld-Token")):
    if not _authorized(token):
        raise HTTPException(status_code=403, detail="invalid stream token")
    ws = CALLS.get(stream_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="stream is not active")
    payload = str(body.get("payload", ""))
    try:
        audio = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=422, detail="payload must be base64 audio")
    if not audio or len(audio) > 1_000_000:
        raise HTTPException(status_code=422, detail="audio payload must be between 1 byte and 1 MB")
    await ws.send_text(json.dumps({"event": "playAudio", "media": {
        "contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": payload}}))
    return {"sent": True, "stream_id": stream_id, "bytes": len(audio)}


@app.websocket("/live/watch")
async def watch(ws: WebSocket):
    if not _authorized(ws.query_params.get("token")):
        await ws.close(code=1008)
        return
    await ws.accept()
    WATCHERS.add(ws)
    try:
        await ws.send_text(json.dumps({"type": "snapshot", "active_streams": len(ACTIVE)}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        WATCHERS.discard(ws)
