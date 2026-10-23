"""Understanding what was said, robust to speech-to-text errors.

Each prompt or executive line is classified by fuzzy overlap with standard
phrasings (the share of a cue phrase's words that survived recognition).
This stands in for the language model a real agent would use: it tolerates
dropped and swapped words, and says 'unknown' rather than guessing.
"""
from __future__ import annotations

from .line import EXEC, words_of
from .spec import FIELD_TEXT, SYSTEM_TEXT

IVR_TYPES: dict[str, list[str]] = {}
for k in ("invalid", "noinput", "invalid_entry", "not_registered", "confirm", "after_fact", "closed", "busy",
          "callback", "callback_ok", "connecting", "goodbye", "dead_end"):
    IVR_TYPES[k] = [SYSTEM_TEXT[k]["en"], SYSTEM_TEXT[k]["hi"]]
IVR_TYPES["ref"] = [SYSTEM_TEXT["ref"]["en"].split("{")[0], SYSTEM_TEXT["ref"]["hi"].split("{")[0]]
IVR_TYPES["position"] = [SYSTEM_TEXT["position"]["en"].replace("{k}", ""), SYSTEM_TEXT["position"]["hi"].replace("{k}", "")]
IVR_TYPES["est_wait"] = [SYSTEM_TEXT["est_wait"]["en"].replace("{m}", ""), SYSTEM_TEXT["est_wait"]["hi"].replace("{m}", "")]
for f, d in FIELD_TEXT.items():
    IVR_TYPES[f"field:{f}"] = [d["en"], d["hi"]]

import re as _re

EXEC_TYPES: dict[str, list[str]] = {}
for k, (en, hi) in EXEC.items():
    if k not in ("complaint_ref", "repeat_ref", "cancelled", "offer_taken", "applied"):
        en, hi = _re.sub(r"\{\w+\}", "", en), _re.sub(r"\{\w+\}", "", hi)
    EXEC_TYPES[k] = [en.split("{")[0] if k in ("complaint_ref", "repeat_ref", "cancelled", "offer_taken", "applied")
                     else en.replace("{offer}", "").replace("{d}", "").replace("{dept}", "").replace("{brand}", ""),
                     hi.split("{")[0] if k in ("complaint_ref", "repeat_ref", "cancelled", "offer_taken", "applied")
                     else hi.replace("{offer}", "").replace("{d}", "").replace("{dept}", "").replace("{brand}", "")]
EXEC_TYPES["greeting"] = ["good day this is from how may i help you", "नमस्कार मैं से बात कर रहा हूँ मैं आपकी क्या सहायता कर सकता हूँ"]

STOP = set("""for press to the a an your you is and or of please this that on in at with from we our us are be will
it i my me say has have been can may now right sorry thank thanks yes no do here there just
के लिए दबाएँ का की को है हैं में से और या कृपया आपका आपकी आपके अपना अपनी हम हमें यह वह पर तक बोलें कर करें करने
गया गई दिया रहा रही हूँ मैं जी""".split())


def content(text: str) -> set:
    return {w for w in words_of(text) if w and w not in STOP and not w.isdigit()}


_CUE_WORDS = {k: [content(c) for c in v] for k, v in {**IVR_TYPES, **{"x:" + a: b for a, b in EXEC_TYPES.items()}}.items()}


def overlap(text_words: set, cue: set) -> float:
    """Share of the cue that was heard; short cues need more than one word to score high."""
    if not cue:
        return 0.0
    return len(text_words & cue) / max(len(cue), 3)


def f1(text_words: set, cue: set) -> float:
    """Balance: how much of the cue was heard, and how much of the sentence the cue explains."""
    if not cue or not text_words:
        return 0.0
    m = len(text_words & cue)
    if m == 0:
        return 0.0
    recall = m / max(len(cue), 3)
    precision = m / len(text_words)
    return 2 * precision * recall / (precision + recall)


def classify(text: str, table: dict[str, list[str]], prefix: str = "", threshold: float = 0.6):
    tw = content(text)
    best, score = "unknown", 0.0
    for k in table:
        for cue in _CUE_WORDS[prefix + k]:
            s = max(f1(tw, cue), overlap(tw, cue) * 0.9 if len(tw) <= len(cue) + 2 else 0.0)
            if s > score:
                best, score = k, s
    return (best, score) if score >= threshold else ("unknown", score)


def ivr_type(text: str, threshold: float = 0.6):
    from .nav import parse_options
    if len(parse_options(text)) >= 3:
        return "menu", 1.0
    return classify(text, IVR_TYPES, "", threshold)


def exec_type(text: str, threshold: float = 0.55):
    return classify(text, EXEC_TYPES, "x:", threshold)
