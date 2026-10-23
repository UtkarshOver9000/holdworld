"""Voice platforms the agent can run on, with their documented limits and prices."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .provenance import P


@dataclass(frozen=True)
class Platform:
    name: str
    label: str
    can_send_dtmf: bool
    dtmf_latency_s: float
    call_cap_s: float
    silence_hangup_s: float | None    # platform hangs up after this much far-end silence
    online_check_s: float | None      # platform says "Hello, are you still there?"
    hybrid: bool                      # cheap hold classifier during hold, full pipeline otherwise
    note: str

    def cost_inr(self, total_s: float, talk_s: float, hold_s: float) -> float:
        tel = P("telephony.rate_inr_min") * math.ceil(total_s / 30) * 0.5
        if self.hybrid:
            return tel + P("pipeline.rate_inr_min") * talk_s / 60 + P("holdclassifier.rate_inr_min") * hold_s / 60
        pulses = math.ceil(total_s / P("bolna.pulse_s"))
        return tel + P("bolna.rate_inr_min") * pulses * P("bolna.pulse_s") / 60


PLATFORMS = {p.name: p for p in [
    Platform("bolna_default", "Bolna, default settings", P("bolna.can_send_dtmf"), 0.0,
             P("bolna.call_terminate_default_s"), P("bolna.hangup_after_silence_s"), P("bolna.online_check_s"),
             False, "90 s call limit, 10 s silence hang-up, cannot press keys"),
    Platform("bolna_naive", "Bolna, limit raised only", True, P("dtmf.latency_s.bolna_custom_fn"),
             P("bolna.call_max_s"), P("bolna.hangup_after_silence_s"), P("bolna.online_check_s"),
             False, "40 min limit, silence defaults left on, keys via a custom function to Plivo"),
    Platform("bolna_tuned", "Bolna, tuned for holds", True, P("dtmf.latency_s.bolna_custom_fn"),
             P("bolna.call_max_s"), None, None, False, "40 min limit, silence hang-up and online check off"),
    Platform("plivo_hybrid", "Plivo stream + hold classifier", P("plivo.can_send_dtmf"), P("dtmf.latency_s.plivo"),
             P("plivo.time_limit_s"), None, None, True, "4 h limit, sendDTMF on the stream, LLM only while talking"),
    Platform("exotel_stream", "Exotel voicebot stream", P("exotel.can_send_dtmf"), 0.0,
             P("exotel.stream_max_s"), None, None, True, "60 min stream, no documented way to press keys"),
]}
