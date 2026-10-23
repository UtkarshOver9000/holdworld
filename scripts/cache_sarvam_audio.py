"""Cache short, disclosed Sarvam TTS samples for the static demo.

Requires SARVAM_API_KEY. This only synthesizes the text in site/audio/manifest.json;
it does not place phone calls. Uses Sarvam's documented /text-to-speech REST API.
"""
from __future__ import annotations

import base64
import argparse
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "audio"
MANIFEST = OUT / "manifest.json"
API = "https://api.sarvam.ai/text-to-speech"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telephony", action="store_true", help="also cache raw 8 kHz G.711 mu-law clips")
    args = parser.parse_args()
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        raise SystemExit("Set SARVAM_API_KEY to generate audio; no request was sent.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for clip in manifest["clips"]:
        for codec, rate, suffix in [("wav", 24000, ".wav")] + ([ ("mulaw", 8000, ".ulaw") ] if args.telephony else []):
            target = OUT / f"{clip['id']}{suffix}"
            if target.exists():
                continue
            response = requests.post(API, headers={"api-subscription-key": key, "Content-Type": "application/json"},
                                     json={"text": clip["text"], "model": "bulbul:v4-flash",
                                           "language_code": clip["language_code"], "speaker": clip["speaker"],
                                           "output_audio_codec": codec, "speech_sample_rate": rate}, timeout=90)
            response.raise_for_status()
            body = response.json()
            audio = body.get("audios", [])
            if not audio:
                raise RuntimeError(f"Sarvam returned no audio for {clip['id']}: {body}")
            target.write_bytes(base64.b64decode(audio[0], validate=True))
            print(f"wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
