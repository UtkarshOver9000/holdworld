"""Score a WAV with YAMNet and save Speech / Speech synthesizer / Music scores.

Install requirements-audio.txt first. YAMNet is fetched from TensorFlow Hub on
the first run and cached by TensorFlow Hub; input WAV audio is resampled to 16 kHz.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tensorflow_hub as hub
from scipy.io import wavfile
from scipy.signal import resample_poly

MODEL_URL = "https://tfhub.dev/google/yamnet/1"


def classify(path: Path) -> dict:
    rate, audio = wavfile.read(path)
    if audio.ndim == 2:
        audio = audio.astype(np.float32).mean(axis=1)
    if np.issubdtype(audio.dtype, np.integer):
        audio = audio.astype(np.float32) / max(abs(np.iinfo(audio.dtype).min), np.iinfo(audio.dtype).max)
    else:
        audio = audio.astype(np.float32)
    if rate != 16000:
        from math import gcd
        d = gcd(int(rate), 16000)
        audio = resample_poly(audio, 16000 // d, int(rate) // d).astype(np.float32)
    model = hub.load(MODEL_URL)
    scores, _, _ = model(audio)
    mean = np.mean(scores.numpy(), axis=0)
    class_path = model.class_map_path().numpy().decode("utf-8")
    with open(class_path, encoding="utf-8") as fh:
        labels = [r["display_name"] for r in csv.DictReader(fh)]
    wanted = ["Speech", "Speech synthesizer", "Music"]
    result = {label: float(mean[labels.index(label)]) for label in wanted if label in labels}
    return {"file": path.name, "sample_rate_hz": 16000, "seconds": len(audio) / 16000,
            "model": "YAMNet AudioSet (TensorFlow Hub)", "scores": result,
            "top_classes": [{"label": labels[i], "score": float(mean[i])}
                            for i in np.argsort(mean)[-8:][::-1]]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = classify(args.audio)
    dest = args.output or args.audio.with_suffix(".yamnet.json")
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
