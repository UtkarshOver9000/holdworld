"""What the agent 'hears' each half-second, with realistic mistakes.

Phase 1 has no audio, so each frame carries the outputs a real listening
pipeline would produce: speech-to-text words, and scores a sound classifier
such as YAMNet gives (Speech / Speech synthesizer / Music / Silence, plus a
'live room' score from background noise). The class means below are
ASSUMED until phase 2 runs YAMNet on real Atlas audio; the word error rate is
taken from the measured range (Sarvam 11.8% to Gram Vaani 29.7-34.8%).
"""
from __future__ import annotations

import random

from .provenance import P, Param, register

# truth labels, one per frame
RING, BUSY, NETWORK, PROMPT, IVR_WAIT = "ringback", "busy_tone", "network_announcement", "ivr_prompt", "ivr_waiting"
MUSIC, ANNOUNCE, AGENT_LIKE, SILENCE = "hold_music", "hold_announcement", "agent_like_recording", "silence"
HUMAN, HUMAN_WAIT, AI_AGENT, DATA, ENDED = "human_live", "human_listening", "ai_agent", "data_burst", "disconnected"
SPEECH_LABELS = {NETWORK, PROMPT, ANNOUNCE, AGENT_LIKE, HUMAN, AI_AGENT}
LIVE_LABELS = {HUMAN, HUMAN_WAIT}

# (speech, music, synth, room) means per label
_MEANS = {
    RING: (0.05, 0.10, 0.05, 0.10), BUSY: (0.05, 0.10, 0.05, 0.10),
    NETWORK: (0.88, 0.05, 0.70, 0.12), PROMPT: (0.88, 0.05, 0.72, 0.12),
    IVR_WAIT: (0.04, 0.03, 0.05, 0.10), SILENCE: (0.04, 0.03, 0.05, 0.10),
    MUSIC: (0.25, 0.85, 0.10, 0.10), ANNOUNCE: (0.85, 0.30, 0.66, 0.15),
    AGENT_LIKE: (0.85, 0.22, 0.42, 0.28), HUMAN: (0.84, 0.05, 0.16, 0.62),
    HUMAN_WAIT: (0.10, 0.04, 0.05, 0.55), AI_AGENT: (0.86, 0.03, 0.76, 0.15),
    DATA: (0.20, 0.40, 0.20, 0.10), ENDED: (0.0, 0.0, 0.0, 0.0),
}
SNR = {"good": (0.12, 0.0), "fair": (0.17, 0.15), "poor": (0.22, 0.30)}  # (sd, pull towards 0.5)

register(Param("perception.class_means", "see perception.py", "ASSUMED", "assumption",
               note="classifier score means per sound class; phase 2 replaces with YAMNet on real audio"))
register(Param("speech.rate_wps", {"en": 2.6, "hi": 2.4}, "ASSUMED", "assumption", "words/s",
               "IVR prompt speaking rate; Atlas recordings will measure it"))


def acoustic(label: str, snr: str, rng: random.Random) -> tuple[float, float, float, float]:
    sd, pull = SNR[snr]
    out = []
    for m in _MEANS.get(label, _MEANS[SILENCE]):
        m = m + (0.5 - m) * pull
        out.append(min(1.0, max(0.0, rng.gauss(m, sd))))
    return out[0], out[1], out[2], out[3]


def wer_for(lang: str, snr: str, mult: float = 1.0, recorded: bool = False) -> float:
    """Default inside the measured 10-35% range; a bad line pushes it to the top of it."""
    base = P("asr.wer.recorded") if recorded else (P("asr.wer.hi") if lang == "hi" else P("asr.wer.en"))
    bump = {"good": 0.0, "fair": 0.06, "poor": 0.14}[snr]
    return min(0.6, max(0.03, (base + bump) * mult))


_FILLER = {"en": ["the", "a", "and", "for", "to", "uh", "of", "in"], "hi": ["के", "और", "है", "में", "को", "से"]}


def mishear(words: list[str], wer: float, lang: str, rng: random.Random) -> list[str]:
    """Substitutions, deletions and a few insertions at the given word error rate."""
    out = []
    for w in words:
        r = rng.random()
        if r < wer * 0.6:            # substitution
            if any(ch.isdigit() for ch in w):
                out.append("".join(str(rng.randrange(10)) if ch.isdigit() else ch for ch in w))
            else:
                out.append(rng.choice(_FILLER.get(lang, _FILLER["en"])))
        elif r < wer * 0.9:          # deletion
            continue
        else:
            out.append(w)
            if rng.random() < wer * 0.1:
                out.append(rng.choice(_FILLER.get(lang, _FILLER["en"])))
    return out
