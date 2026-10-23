# Cached voice samples

These generated sample lines can be produced with `python scripts/cache_sarvam_audio.py` after setting `SARVAM_API_KEY`. The script reads `manifest.json`, caches WAV files here, and never makes a call to a helpline. Add `--telephony` to also request raw 8 kHz G.711 mu-law files for a phone testbed. Generated audio files are ignored until a team member reviews and chooses them for a deploy.

Every line is labeled as generated simulation audio. The text is illustrative and does not claim to reproduce an institution's recorded prompts. The browser simulation keeps its speech-synthesis fallback when no cached clip exists.
