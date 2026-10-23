"""The stress suite: each scenario breaks one thing real calls break, and says what 'pass' means."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable

from .helplines import all_helplines
from .spec import Helpline


@dataclass
class Scenario:
    id: str
    title: str
    breaks: str
    helpline: str
    task: str
    mode: str = "M1"
    scn: dict = field(default_factory=dict)
    mutate: Callable[[Helpline], Helpline] | None = None
    dial: str | None = None
    platform: dict = field(default_factory=dict)   # arm -> platform override
    passes: Callable = None                        # (CallResult) -> bool
    source: str = ""

    def helpline_for(self, base: dict) -> Helpline:
        h = base[self.helpline]
        return self.mutate(copy.deepcopy(h)) if self.mutate else h


def _ok(r):
    return r.success


def _no_false(r):
    return r.success and r.false_alerts == 0


def _broken_speech(h):
    h.nodes["dep"].modality = "broken_speech"
    return h


def _menu_changed(h):
    # the bank moved complaints from 4 to 2 since the script was recorded
    m = h.nodes["main"]
    keys = {o.goto: o for o in m.options}
    keys["dep"].key, keys["card"].key = "2", "4"
    m.options.sort(key=lambda o: o.key)
    return h


SCENARIOS = [
    Scenario("S1", "Hindi menus, Hinglish labels", "language handling, Hindi vocabulary", "psu_bank", "psu_complaint",
             scn={"lang_pref": "hi"}, passes=_ok, source="SBI official menu, 15 languages"),
    Scenario("S2", "Menu says 'press' but only listens to speech", "keys vs speech", "psu_bank", "psu_complaint",
             mutate=_broken_speech, passes=_ok, source="Sierra hurdle 4"),
    Scenario("S3", "40 s disclaimer, keys ignored while it plays", "turn-taking", "gov_docs", "gov_officer",
             passes=_ok, source="Regal case study (80% -> 96%)"),
    Scenario("S4", "Menu loop and a dead end", "navigation recovery", "gas", "gas_safety", passes=_ok,
             source="Sierra hurdle 4"),
    Scenario("S5", "Account menu needs the registered mobile", "registered-number gate", "tpin_bank", "tpin_balance",
             mode="M1", passes=lambda r: r.captured_ok is not False or r.gave_up == "needs_registered_number",
             source="KVB official: registration from the registered mobile"),
    Scenario("S6", "A recording that sounds like a person, every minute", "recorded-vs-live detection", "psu_bank",
             "psu_complaint", scn={"agent_like_p": 1.0, "announce_every_s": 30}, passes=_no_false,
             source="Sierra hurdle 3; Google Hold for Me"),
    Scenario("S7", "Music cut mid-note by a soft 'hello?'", "pickup detection speed", "psu_bank", "psu_complaint",
             scn={"abrupt": True, "soft_hello": True},
             passes=lambda r: r.success and (r.detect_latency is None or r.detect_latency <= 3.0),
             source="Sierra hurdle 3"),
    Scenario("S8", "Queue position announced in Hindi every 30 s", "false alarms on hold", "airline", "air_change",
             scn={"lang_pref": "hi", "announce_every_s": 30}, passes=_no_false, source="hold behaviour"),
    Scenario("S9", "Callback offered after 2 minutes", "callback policy", "airline", "air_change", mode="M3",
             passes=lambda r: r.success or r.end_reason == "callback_scheduled", source="Kotak courtesy callback"),
    Scenario("S10", "'All executives are busy, call later'", "re-dial", "psu_bank", "psu_complaint",
             scn={"busy_disconnect_p": 0.6}, passes=_ok, source="common Indian helpline behaviour"),
    Scenario("S11", "Call drops 40 s into the hold", "resilience", "psu_bank", "psu_complaint",
             scn={"drop_at": 40.0}, passes=_ok, source="mobile network drops (TRAI QoS)"),
    Scenario("S12", "Bad line: poor signal, 1.6x speech errors", "noise robustness", "psu_bank", "psu_balance",
             scn={"snr": "poor", "wer_mult": 1.6}, passes=_ok, source="Gram Vaani phone WER 29.7-34.8%"),
    Scenario("S13", "User gives the operator short code 199", "short-code mapping", "telecom", "tel_network",
             mode="M2", dial="199", passes=_ok, source="Jio: 199 only from a Jio SIM"),
    Scenario("S14", "Transferred to another team, second hold", "re-entering hold", "psu_bank", "psu_dispute",
             scn={"force_transfer": True}, passes=_ok, source="ServiceNow: 36% frustrated by transfers"),
    Scenario("S15", "Impatient executive (4-6 s of silence)", "handoff race", "psu_bank", "psu_complaint",
             scn={"exec_patience": (4.0, 6.0)}, passes=_ok, source="dead-air patience (Atlas to measure)"),
    Scenario("S16", "OTP to the registered mobile mid-call", "OTP relay", "telecom", "tel_cancel", mode="M2",
             passes=_ok, source="Pine-style verification"),
    Scenario("S17", "Voice platform left on default settings", "silence hang-up, 'are you still there?'",
             "psu_bank", "psu_complaint", platform={"D": "bolna_naive", "C": "bolna_naive"}, passes=_ok,
             source="Bolna docs: hangup_after_silence 10 s"),
    Scenario("S18", "The bank's own voicebot answers", "agent-to-agent handshake", "psu_bank", "psu_dispute",
             scn={"ai_exec": True, "handshake": True}, passes=_ok, source="GibberLink (ElevenLabs hackathon)"),
    Scenario("S19", "Menu changed since the script was recorded", "blind navigation", "psu_bank", "psu_complaint",
             mutate=_menu_changed, passes=_ok, source="Sierra: agents remember paths; menus change"),
    Scenario("S20", "Account menu needs a PIN", "never typing a PIN", "tpin_bank", "tpin_balance", mode="M2",
             passes=lambda r: r.success and r.secrets_by_agent == 0, source="KVB official: TPIN"),
]


def by_id() -> dict[str, Scenario]:
    return {s.id: s for s in SCENARIOS}


def base_helplines():
    return all_helplines()
