# Optional integrations

These tools are opt-in. They do not place calls or send provider requests during `python -m holdworld run`.

## Sarvam voice cache

Set `SARVAM_API_KEY`, then run:

```sh
python scripts/cache_sarvam_audio.py
python scripts/cache_sarvam_audio.py --telephony
```

The first command caches disclosed English/Hindi WAV samples for the browser. The second also requests raw G.711 mu-law at 8 kHz for telephony. Sample lines are illustrative, not recordings of the named banks. Generated audio stays ignored by Git until reviewed.

## YAMNet audio scoring

Install the optional packages and score a generated WAV:

```sh
pip install -r requirements-audio.txt
python scripts/classify_yamnet.py site/audio/en_main_menu.wav
```

The first run downloads the TensorFlow Hub model. It writes class scores to a neighboring `.yamnet.json` file. This is a real-audio analysis tool; it is not yet wired into the simulation's event classifier or browser traces.

## Plivo bidirectional stream adapter

Install `requirements-live.txt`, configure a strong shared token and public TLS WebSocket, then run:

```sh
set HOLDWORLD_STREAM_TOKEN=<secret>
set HOLDWORLD_PUBLIC_WSS=wss://your-host/plivo/stream
uvicorn holdworld.live_stream:app --host 0.0.0.0 --port 8000
```

Configure the Plivo Answer URL as `https://your-host/plivo/answer?token=<same-secret>`. The adapter accepts the documented start/media/DTMF stream, counts audio chunks without storing them, and exposes authenticated `/live` and DTMF/audio control endpoints. Put it behind HTTPS/WSS and restrict the host. This adapter is not connected to the HoldForMe simulation scorer or an LLM agent yet.

## Asterisk/SIPp local load test

See [`../testbed/README.md`](../testbed/README.md). The Compose setup needs Docker and has not been run in this development environment.

## India Hold Atlas

Copy `data/atlas/atlas_template.csv` to `data/atlas/measurements.csv`, fill it with real observations, and run `python -m holdworld run`. Three queue observations for a helpline replace its sampled wait pool; three or more dead-air, announcement, or OTP observations register those values with the `ATLAS` provenance tag. The model summary and dashboard show the imported call count. Never place recordings of an executive into the repository.
