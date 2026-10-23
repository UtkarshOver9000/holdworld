"""The Line layer: one phone call, stepped every half-second.

The helpline side (IVR, hold queue, executive) is written as a script that
yields what it plays and waits for; the driver advances it in 0.5 s frames,
delivers the caller's key presses and speech, and records the truth of every
frame so the caller can be scored exactly.
"""
from __future__ import annotations

import heapq
import math
import random
import re
from dataclasses import dataclass, field

from . import perception as pc
from .people import Persona, User
from .platforms import Platform
from .provenance import P
from .spec import (FIELD_TEXT, SECRET_FIELDS, SYSTEM_TEXT, Helpline, Node, Task, language_prompt, menu_prompt)

FRAME = 0.5
DIGIT_S = (P("dtmf.tone_ms") + P("dtmf.gap_ms")) / 1000.0

EXEC = {
    "hello": ("Hello? Hello, can you hear me?", "हेलो? हेलो, क्या आप मुझे सुन पा रहे हैं?"),
    "bye_dead": ("I'm unable to hear you. Please call back. Thank you.", "मुझे आपकी आवाज़ नहीं आ रही है। कृपया दोबारा कॉल करें। धन्यवाद।"),
    "hold_ok": ("Sure, I'll hold.", "ठीक है, मैं होल्ड करता हूँ।"),
    "hold_over": ("I can't hold the line any longer. Please call back.", "मैं अब और लाइन होल्ड नहीं कर सकता। कृपया दोबारा कॉल करें।"),
    "probe_reply": ("Yes, hello, I can hear you. How may I help you?", "जी, हेलो, मैं आपको सुन पा रहा हूँ। बताइए, मैं क्या मदद कर सकता हूँ?"),
    "refuse_ai": ("I'm sorry, I can only discuss this with the account holder. Can you connect them to the call?",
                  "माफ़ कीजिए, मैं यह केवल खाताधारक से ही बात कर सकता हूँ। क्या आप उन्हें कॉल पर जोड़ सकते हैं?"),
    "otp_sent": ("I have sent a one time password to the registered mobile number. Please read it out.",
                 "मैंने पंजीकृत मोबाइल नंबर पर एक ओटीपी भेजा है। कृपया उसे बताइए।"),
    "take_time": ("Please take your time.", "कोई बात नहीं, आराम से बताइए।"),
    "mismatch": ("Sorry, that doesn't match our records.", "माफ़ कीजिए, यह हमारे रिकॉर्ड से मेल नहीं खाता।"),
    "how_help": ("Thank you for verifying. How can I help you today?", "सत्यापन के लिए धन्यवाद। बताइए, मैं आज आपकी क्या मदद करूँ?"),
    "check_hold": ("Please hold for a moment while I check.", "कृपया एक क्षण रुकिए, मैं जाँच कर रहा हूँ।"),
    "thanks_hold": ("Thank you for holding.", "प्रतीक्षा करने के लिए धन्यवाद।"),
    "complaint_ref": ("I have registered your complaint. Your complaint number is {ref}.",
                      "मैंने आपकी शिकायत दर्ज कर ली है। आपका शिकायत नंबर {ref} है।"),
    "refund_ref": ("Your refund of rupees {amt} was processed on {date}. The reference number is {ref}.",
                   "आपका {amt} रुपये का रिफंड {date} को प्रोसेस हो गया है। संदर्भ नंबर {ref} है।"),
    "repeat_ref": ("Sure. The number is {ref}.", "ज़रूर। नंबर है {ref}।"),
    "correct": ("Yes, that's correct.", "जी, यह सही है।"),
    "wrong_number": ("No, the number is {ref}.", "नहीं, नंबर है {ref}।"),
    "offer": ("Before I cancel, we can offer you {offer}. Would you like that?",
              "रद्द करने से पहले, हम आपको {offer} दे सकते हैं। क्या आप यह लेना चाहेंगे?"),
    "cancelled": ("Okay, I have cancelled it. Your reference number is {ref}.",
                  "ठीक है, मैंने इसे रद्द कर दिया है। आपका संदर्भ नंबर {ref} है।"),
    "offer_taken": ("Great, I have applied the offer instead. Your reference number is {ref}.",
                    "बढ़िया, मैंने ऑफ़र लागू कर दिया है। आपका संदर्भ नंबर {ref} है।"),
    "discount": ("I can offer you a {d} percent discount for six months.", "मैं आपको छह महीने के लिए {d} प्रतिशत की छूट दे सकता हूँ।"),
    "no_discount": ("I'm sorry, I can't offer any discount right now.", "माफ़ कीजिए, अभी मैं कोई छूट नहीं दे सकता।"),
    "best": ("That's the best I can do.", "इससे बेहतर मैं नहीं कर सकता।"),
    "applied": ("Done, the discount is applied. Your reference number is {ref}.", "हो गया, छूट लागू कर दी गई है। आपका संदर्भ नंबर {ref} है।"),
    "transfer": ("Let me transfer your call to the {dept} team. Please stay on the line.",
                 "मैं आपकी कॉल {dept} टीम को ट्रांसफर कर रहा हूँ। कृपया लाइन पर बने रहें।"),
    "anything": ("Is there anything else I can help you with?", "क्या मैं आपकी और कोई मदद कर सकता हूँ?"),
    "bye": ("Thank you for calling. Have a nice day.", "कॉल करने के लिए धन्यवाद। आपका दिन शुभ हो।"),
    "ai_greet": ("Hi, I'm Asha, the virtual assistant for {brand}. How can I help you today?",
                 "नमस्ते, मैं आशा हूँ, {brand} की वर्चुअल असिस्टेंट। बताइए, मैं आपकी क्या मदद करूँ?"),
    "ai_connect": ("Sure, connecting you to an executive.", "ज़रूर, मैं आपको एक अधिकारी से जोड़ रही हूँ।"),
    "ask_name": ("May I know the account holder's full name?", "क्या मैं खाताधारक का पूरा नाम जान सकता हूँ?"),
    "ask_dob": ("Please tell me the date of birth.", "कृपया जन्म तिथि बताइए।"),
    "ask_acct_last4": ("Please tell me the last four digits of the account number.", "कृपया खाता नंबर के अंतिम चार अंक बताइए।"),
    "ask_mobile": ("Please tell me the registered mobile number.", "कृपया पंजीकृत मोबाइल नंबर बताइए।"),
    "ask_customer_id": ("Please tell me the customer ID.", "कृपया ग्राहक आईडी बताइए।"),
    "ask_consumer_no": ("Please tell me the consumer number.", "कृपया उपभोक्ता नंबर बताइए।"),
    "ask_order_id": ("Please tell me the order number.", "कृपया ऑर्डर नंबर बताइए।"),
    "ask_pnr": ("Please tell me the booking reference.", "कृपया बुकिंग संदर्भ बताइए।"),
    "ask_file_no": ("Please tell me the file number.", "कृपया फ़ाइल संख्या बताइए।"),
}
NETWORK_TEXT = {
    "unreachable": "आप जिस नंबर पर कॉल कर रहे हैं वह मौजूद नहीं है। The number you have dialled does not exist. Please check the number.",
    "busy": "आप जिस नंबर पर कॉल कर रहे हैं वह अभी व्यस्त है। The number you are calling is busy. Please try after some time.",
}
WORD = re.compile(r"[^\s।,.?!'\"]+")
SENT = re.compile(r"(?<=[.।?!])\s+")


def words_of(text: str) -> list[str]:
    return WORD.findall(text.lower())


def spaced(digits: str) -> str:
    return " ".join(digits)


@dataclass
class Utterance:
    text: str
    intent: str = ""
    slots: dict = field(default_factory=dict)
    by: str = "agent"


@dataclass
class Action:
    kind: str = "wait"          # wait | dtmf | say | bridge | alert | hangup
    digits: str = ""
    text: str = ""
    intent: str = ""
    slots: dict = field(default_factory=dict)
    alert: str = ""             # human | otp | press_key | secret | primed | info


WAIT = Action()


@dataclass
class Obs:
    t: float
    speech: float
    music: float
    synth: float
    room: float
    tone: str | None
    partial: str
    final: str | None
    utt: int
    lang: str | None
    events: list
    speaking: bool
    ended: bool = False
    end_reason: str = ""
    finals: list = field(default_factory=list)


@dataclass
class _Ev:
    t: float
    kind: str                   # dtmf | speech | user_join
    value: object = None
    by: str = "agent"


@dataclass
class _Play:
    label: str
    text: str = ""
    lang: str = "en"
    dur: float | None = None
    speaker: str = "ivr"
    barge: frozenset = frozenset()


@dataclass
class _Listen:
    timeout: float
    accept: frozenset = frozenset({"dtmf"})
    label: str = pc.IVR_WAIT


@dataclass
class Seg:
    start: float
    end: float
    label: str
    text: str = ""
    lang: str = ""
    speaker: str = ""
    utt: int = -1
    heard: list = field(default_factory=list)


class _End(Exception):
    pass


class CallEnv:
    def __init__(self, hl: Helpline, task: Task, persona: Persona, *, mode: str, platform: Platform,
                 wait_s: float, hour: int, rng: random.Random, scn: dict | None = None,
                 dial: str | None = None, record: bool = True):
        self.hl, self.task, self.persona = hl, task, persona
        self.mode, self.platform, self.wait_s, self.hour = mode, platform, wait_s, hour
        self.rng = rng
        self.scn = scn or {}
        self.snr = self.scn.get("snr", "good")
        self.record = record
        self.user = User(random.Random(rng.random()), mode)
        self.registered = (mode == "M2") or not hl.caller_id_auth
        self.m2_relay_ok = rng.random() < self.scn.get("m2_dtmf_relay_p", 0.5) if mode == "M2" else True
        self.music_is_silence = rng.random() < P("platform.music_counts_as_silence_p")
        self.dial = dial or hl.dial
        ex = hl.executive
        lo, hi = self.scn.get("exec_patience", P("exec.dead_air_patience_s"))
        self.exec_patience = rng.uniform(lo, hi)
        self.refuse_ai = rng.random() < (ex["refuse_ai_p"] if ex["refuse_ai_p"] is not None else
                                         self.scn.get("refuse_ai_p", P("exec.refuse_ai_p")))
        self.ai_exec = self.scn.get("ai_exec", rng.random() < ex.get("ai_exec_p", 0.0))
        self.lang = "en"
        self.t = 0.0
        self.cursor = 0.0
        self.pending: list = []
        self._seq = 0
        self.inbox: list[_Ev] = []
        self.agent_events: list = []
        self.agent_speaking_until = 0.0
        self.last_activity = 0.0
        self.online_spoken = False
        self.done = False
        self.end_reason = ""
        self.segs: list[Seg] = []
        self._finalised: set = set()
        self.utt = 0
        # truth / metrics
        self.visited: list[str] = []
        self.visited_t: list[float] = []
        self.dept_reached: str | None = None
        self.t_queue_enter: float | None = None
        self.hold_s = 0.0
        self.pickup_t: float | None = None
        self.exec_speaking_t: float | None = None
        self.user_join_t: float | None = None
        self.bridge_t: float | None = None
        self.user_ringing = False
        self.bridge_truth: str | None = None
        self.handed_off = False
        self.alerts: list[tuple[float, str]] = []
        self.facts: dict[str, str] = {}
        self.refs: dict[str, str] = {}
        self.exec_outcome: dict = {}
        self.secrets_by_agent = 0
        self.platform_utterances = 0
        self.dtmf_sent = 0
        self.dtmf_unavailable = 0
        self.dtmf_lost = 0
        self.callback_t: float | None = None
        self.transfers = 0
        self.frames: list = []
        self.transcript: list = []
        self.script = self._call()
        self.instr = None
        self._advance(None, 0.0, first=True)

    # ------------------------------------------------------------------ driver
    def _push(self, ev: _Ev) -> None:
        heapq.heappush(self.pending, (ev.t, self._seq, ev))
        self._seq += 1

    def _advance(self, result, at: float, first: bool = False) -> None:
        if self.segs and self.segs[-1].end > at:
            self.segs[-1].end = at
        self.cursor = at
        try:
            self.instr = next(self.script) if first else self.script.send(result)
        except (StopIteration, _End):
            self.instr = None
            if not self.done:
                self._end("ivr_finished", at)
            return
        self._begin(self.instr)

    def _begin(self, ins) -> None:
        if isinstance(ins, _Play):
            if ins.dur is None:
                rate = P("speech.rate_wps").get(ins.lang, 2.5)
                ins.dur = max(0.8, len(words_of(ins.text)) / rate + 0.4) if ins.text else 1.0
            seg = Seg(self.cursor, self.cursor + ins.dur, ins.label, ins.text, ins.lang, ins.speaker)
            if ins.label in pc.SPEECH_LABELS and ins.text:
                self.utt += 1
                seg.utt = self.utt
                wer = pc.wer_for(ins.lang if ins.lang in ("en", "hi") else "hi", self.snr, self.scn.get("wer_mult", 1.0),
                                 recorded=ins.label != pc.HUMAN)
                # speech-to-text keeps sentence punctuation (Deepgram/Sarvam do); words inside are misheard
                heard = []
                for sent in SENT.split(ins.text.strip()):
                    ws = pc.mishear(words_of(sent), wer, ins.lang, self.rng)
                    if ws:
                        ws[-1] = ws[-1] + ("।" if sent.rstrip().endswith("।") else ".")
                        heard.extend(ws)
                seg.heard = heard
                if ins.speaker in ("exec", "ivr", "network"):
                    self.transcript.append({"t": round(self.cursor, 1), "who": ins.speaker, "label": ins.label,
                                            "text": ins.text})
            self.segs.append(seg)
            ins._end = seg.end
        else:
            ins._deadline = self.cursor + ins.timeout
            self.inbox = [e for e in self.inbox if e.kind == "user_join" or e.t >= self.cursor - 3.0]
            self.segs.append(Seg(self.cursor, ins._deadline, ins.label, speaker="listen"))

    def _end(self, reason: str, at: float | None = None) -> None:
        if self.done:
            return
        self.done = True
        self.end_reason = reason
        at = self.t if at is None else at
        if self.segs and self.segs[-1].end > at:
            self.segs[-1].end = at
        self.segs.append(Seg(at, at + 1e9, pc.ENDED))

    def _take(self, kinds, before: float):
        for i, e in enumerate(self.inbox):
            if e.kind in kinds and e.t <= before:
                return self.inbox.pop(i)
        return None

    def step(self, a: Action | None) -> Obs:
        if a is not None and a.kind != "wait" and not self.done:
            self._apply(a)
        t0, t1 = self.t, self.t + FRAME
        while self.pending and self.pending[0][0] <= t1:
            _, _, ev = heapq.heappop(self.pending)
            if ev.kind == "agent_event":
                if ev.value[0] == "_ring_over":
                    self.user_ringing = False
                    continue
                self.agent_events.append(ev.value)
            else:
                self.inbox.append(ev)
                if ev.kind == "user_join" and self.user_join_t is None:
                    self.user_join_t = ev.t
        guard = 0
        while self.instr is not None and not self.done and guard < 50:
            guard += 1
            ins = self.instr
            if isinstance(ins, _Play):
                ev = self._take(ins.barge, min(ins._end, t1)) if ins.barge else None
                if ev:
                    self._advance(ev, max(ev.t, self.segs[-1].start))
                    continue
                if ins._end <= t1:
                    self._advance(None, ins._end)
                    continue
                break
            ev = self._take(ins.accept, t1)
            if ev:
                self._advance(ev, max(ev.t, self.cursor))
                continue
            if ins._deadline <= t1:
                self._advance(None, ins._deadline)
                continue
            break
        self.t = t1
        return self._observe(t0, t1)

    def _seg_at(self, t: float) -> Seg:
        for s in reversed(self.segs):
            if s.start <= t < s.end:
                return s
        return self.segs[-1]

    def _observe(self, t0: float, t1: float) -> Obs:
        mid = t0 + FRAME / 2
        seg = self._seg_at(mid)
        label = seg.label
        if label == pc.HUMAN and self.scn.get("soft_hello") and self.pickup_t and mid < self.pickup_t + 2.5:
            sp, mu, sy, ro = pc.acoustic(pc.HUMAN, "poor", self.rng)
            sp *= 0.55
        else:
            sp, mu, sy, ro = pc.acoustic(label, self.snr, self.rng)
        tone = "ring" if label == pc.RING else ("busy" if label == pc.BUSY else None)
        partial, final, utt, lang = "", None, -1, None
        finals = []
        for s in self.segs[-8:]:
            # every utterance that finished inside this frame, in order
            if s.utt > 0 and t0 < s.end <= t1 and s.utt not in self._finalised:
                self._finalised.add(s.utt)
                finals.append(" ".join(s.heard))
        for s in reversed(self.segs[-6:]):
            if s.utt > 0 and s.start < t1 and s.end > t0 - FRAME:
                frac = min(1.0, (t1 - s.start) / max(s.end - s.start, 1e-6))
                n = math.ceil(frac * len(s.heard))
                partial = " ".join(s.heard[:n])
                utt, lang = s.utt, s.lang
                break
        final = finals[-1] if finals else None
        speaking = self.agent_speaking_until > t0
        # platform behaviour
        active = label in pc.SPEECH_LABELS or speaking or (label == pc.MUSIC and not self.music_is_silence)
        if active:
            self.last_activity = t1
            self.online_spoken = False
        pf = self.platform
        if not self.done:
            quiet = t1 - self.last_activity
            if pf.online_check_s and quiet >= pf.online_check_s and not self.online_spoken:
                self.online_spoken = True
                self.platform_utterances += 1
                self._say(Utterance("Hello, are you still there?", "platform_check", by="platform"))
            if pf.silence_hangup_s and quiet >= pf.silence_hangup_s:
                self._end("platform_silence_hangup", t1)
            if t1 >= pf.call_cap_s:
                self._end("platform_cap", t1)
        events, self.agent_events = self.agent_events, []
        ob = Obs(t1, sp, mu, sy, ro, tone, partial, final, utt, lang, events, speaking, self.done, self.end_reason,
                 finals)
        if self.record:
            self.frames.append((round(t1, 1), label, round(sp, 2), round(mu, 2), round(sy, 2), round(ro, 2), speaking))
        self.truth_label = label
        return ob

    # ------------------------------------------------------------------ caller actions
    def _say(self, u: Utterance) -> None:
        dur = max(0.6, len(words_of(u.text)) / 2.6)
        start = max(self.t, self.agent_speaking_until)
        self.agent_speaking_until = start + dur
        self._push(_Ev(start + dur, "speech", u, u.by))
        self.transcript.append({"t": round(start, 1), "who": u.by, "label": "caller", "text": u.text,
                                "intent": u.intent})

    def _apply(self, a: Action) -> None:
        if a.kind == "dtmf":
            if a.slots.get("secret"):
                self.secrets_by_agent += 1
            if not self.platform.can_send_dtmf:
                self.dtmf_unavailable += len(a.digits)
                return
            for i, d in enumerate(a.digits):
                t = self.t + self.platform.dtmf_latency_s + i * DIGIT_S
                self.dtmf_sent += 1
                if not self.m2_relay_ok:
                    self.dtmf_lost += 1
                    continue
                self._push(_Ev(t, "dtmf", d, "agent"))
            self.transcript.append({"t": round(self.t, 1), "who": "agent", "label": "dtmf", "text": a.digits})
        elif a.kind == "say":
            self._say(Utterance(a.text, a.intent, dict(a.slots)))
        elif a.kind == "bridge":
            if self.bridge_t is not None and (self.user_join_t is not None or self.user_ringing):
                return
            self.user_ringing = True
            self.bridge_t = self.t
            self.bridge_truth = getattr(self, "truth_label", None)
            self.alerts.append((self.t, self.bridge_truth))
            delay = 0.0 if a.slots.get("instant") else self.user.answer_delay()
            if delay is None:
                self._push(_Ev(self.t + 30, "agent_event", ("user_missed", None)))
                self._push(_Ev(self.t + 30, "agent_event", ("_ring_over", None)))
            else:
                self._push(_Ev(self.t + delay, "user_join", None, "user"))
                self._push(_Ev(self.t + delay, "agent_event", ("user_joined", None)))
            self.transcript.append({"t": round(self.t, 1), "who": "agent", "label": "bridge", "text": "connecting the user"})
        elif a.kind == "alert":
            if a.alert == "human":
                self.alerts.append((self.t, getattr(self, "truth_label", None)))
            elif a.alert == "primed":
                self.user.primed = True
            elif a.alert == "otp":
                self._push(_Ev(self.t + self.user.otp_delay(), "agent_event", ("otp", self.persona.truth["otp"])))
            elif a.alert in ("press_key", "secret"):
                if self.mode != "M2":
                    self._push(_Ev(self.t + 2, "agent_event", ("user_cannot_type", None)))
                    return
                start = self.t + self.user.keypress_delay()
                for i, d in enumerate(a.digits):
                    self._push(_Ev(start + i * 0.35, "dtmf", d, "user"))
            self.transcript.append({"t": round(self.t, 1), "who": "agent", "label": "alert", "text": a.alert})
        elif a.kind == "hangup":
            self._end("agent_hangup", self.t)

    # ------------------------------------------------------------------ helpline script
    def _p(self, label, text, lang=None, speaker="ivr", barge=frozenset(), dur=None):
        return _Play(label, text, lang or self.lang, dur, speaker, frozenset(barge))

    def _sys(self, key, **kw):
        return SYSTEM_TEXT[key][self.lang if self.lang in ("en", "hi") else "en"].format(**kw)

    def _call(self):
        hl, rng = self.hl, self.rng
        sc = hl.shortcode
        if sc and self.dial == sc["code"] and sc.get("network_only"):
            yield _Play(pc.RING, dur=2.0, speaker="network")
            yield _Play(pc.NETWORK, NETWORK_TEXT["unreachable"], "hi", speaker="network")
            self._end("unreachable", self.cursor)
            return
        cad = P("tone.ring.cadence")
        ring_s = self.scn.get("ring_s", rng.uniform(3.0, 7.0))
        t = 0.0
        while t < ring_s:
            yield _Play(pc.RING, dur=cad[0] + cad[1] + cad[2], speaker="network")
            yield _Play(pc.RING, dur=cad[3], speaker="network")  # silent part of the cadence
            t += sum(cad)
        if rng.random() < self.scn.get("network_busy_p", 0.01):
            yield _Play(pc.NETWORK, NETWORK_TEXT["busy"], "hi", speaker="network")
            self._end("network_busy", self.cursor)
            return
        first = next((l for _, l in hl.languages if l in ("en", "hi")), "en")
        self.lang = first
        yield self._p(pc.PROMPT, hl.welcome.get(first, ""), first)
        if hl.disclaimer:
            yield self._p(pc.PROMPT, hl.disclaimer.get(first, ""), first,
                          barge={"dtmf"} if hl.barge_in else ())
        if hl.language_menu:
            lang = yield from self._language_menu(hl.languages)
            if lang is None:
                yield self._p(pc.PROMPT, SYSTEM_TEXT["goodbye"][first], first)
                self._end("ivr_fail_language", self.cursor)
                return
            self.lang = lang if lang in ("en", "hi") else "en"
        node_id = hl.root
        steps = 0
        while node_id and steps < 60:
            steps += 1
            node_id = yield from self._node(node_id)

    def _language_menu(self, langs):
        text, _ = language_prompt(langs)
        for attempt in range(3):
            ev = yield _Play(pc.PROMPT, text, "hi", None, "ivr", frozenset({"dtmf", "speech"}))
            if ev is None:
                ev = yield _Listen(6.0, frozenset({"dtmf", "speech"}))
            if ev is None or ev.kind != "dtmf":
                yield self._p(pc.PROMPT, SYSTEM_TEXT["noinput"]["en"], "en")
                continue
            for k, l in langs:
                if k == ev.value:
                    if l == "more":
                        return (yield from self._language_menu(self.hl.more_languages))
                    return l
            yield self._p(pc.PROMPT, SYSTEM_TEXT["invalid"]["en"], "en")
        return None

    def _node(self, nid: str):
        node = self.hl.node(nid)
        self.visited.append(nid)
        self.visited_t.append(round(self.cursor, 2))
        h = getattr(self, f"_n_{node.type}")
        return (yield from h(node))

    def _n_message(self, node: Node):
        yield self._p(pc.PROMPT, node.text.get(self.lang, node.text.get("en", "")))
        return node.next

    def _match_speech(self, node: Node, u: Utterance):
        said = set(words_of(u.text))
        best, score = None, 0
        for o in node.options:
            lab = set(words_of(o.label.get(self.lang, "")) + words_of(o.label.get("en", "")))
            s = len(said & lab)
            if s > score:
                best, score = o, s
        if best and self.rng.random() < 0.9:
            return best
        return None

    def _n_menu(self, node: Node):
        prompt = menu_prompt(node, self.lang)
        tries = 0
        while True:
            ev = yield self._p(pc.PROMPT, prompt, barge={"dtmf", "speech"} if self.hl.barge_in else ())
            if ev is None:
                ev = yield _Listen(node.timeout_s, frozenset({"dtmf", "speech"}))
            choice = None
            if ev is not None and ev.kind == "dtmf" and node.modality in ("dtmf", "both"):
                k = ev.value
                kind = node.extras.get(k)
                if kind == "repeat":
                    continue
                if kind == "main":
                    return self.hl.root
                if kind == "back":
                    return self.visited[-2] if len(self.visited) > 1 else self.hl.root
                if kind == "agent":
                    return node.agent_target
                choice = next((o for o in node.options if o.key == k), None)
                if choice is None:
                    tries += 1
                    if tries > node.repeats:
                        break
                    yield self._p(pc.PROMPT, self._sys("invalid"))
                    continue
            elif ev is not None and ev.kind == "speech" and node.modality in ("speech", "both", "broken_speech"):
                choice = self._match_speech(node, ev.value)
                if choice is None:
                    tries += 1
                    if tries > node.repeats:
                        break
                    yield self._p(pc.PROMPT, self._sys("invalid"))
                    continue
            if choice is not None:
                return choice.goto
            tries += 1
            if tries > node.repeats:
                break
            yield self._p(pc.PROMPT, self._sys("noinput"))
        if node.on_fail != "disconnect":
            return node.on_fail
        yield self._p(pc.PROMPT, self._sys("goodbye"))
        self._end("ivr_fail", self.cursor)
        raise _End

    def _n_collect(self, node: Node):
        prompt = FIELD_TEXT[node.field][self.lang]
        if node.field in SECRET_FIELDS and node.field == "otp":
            pass
        expected = (self.persona.truth["otp"] if node.field == "otp" else
                    Persona.digits_only(self.persona.field_value(node.field)))
        for attempt in range(node.repeats + 1):
            ev = yield self._p(pc.PROMPT, prompt, barge={"dtmf"})
            got, by = "", set()
            timeout = 7.0
            while True:
                if ev is None:
                    ev = yield _Listen(timeout, frozenset({"dtmf"}))
                if ev is None:
                    break
                by.add(ev.by)
                if ev.value == "#":
                    break
                got += ev.value
                ev = None
                timeout = 3.5
                if len(got) >= max(node.digits, len(expected)) + 2:
                    break
            if node.field in SECRET_FIELDS and "agent" in by:
                self.secrets_by_agent += 0  # counted when the agent sent it
            if got == expected:
                return node.next
            if not got:
                yield self._p(pc.PROMPT, self._sys("noinput"))
            else:
                yield self._p(pc.PROMPT, self._sys("invalid_entry"))
        yield self._p(pc.PROMPT, self._sys("goodbye"))
        self._end("ivr_fail_entry", self.cursor)
        raise _End

    def _value_text(self, value: str) -> str:
        return value

    def _n_fact(self, node: Node):
        if node.requires_registered and not self.registered:
            yield self._p(pc.PROMPT, self._sys("not_registered"))
            return self.hl.root
        value = self.persona.truth.get(node.fact, "0")
        text = node.text.get(self.lang, node.text["en"]).format(value=value)
        for _ in range(3):
            yield self._p(pc.PROMPT, text)
            self.facts[node.fact] = value
            ev = yield self._p(pc.PROMPT, self._sys("after_fact"), barge={"dtmf"})
            if ev is None:
                ev = yield _Listen(5.0, frozenset({"dtmf"}))
            if ev is not None and ev.value == "1":
                continue
            if ev is not None and ev.value == "0":
                return self.hl.root
            break
        yield self._p(pc.PROMPT, self._sys("goodbye"))
        self._end("ivr_completed", self.cursor)
        raise _End

    def _n_action(self, node: Node):
        if node.requires_registered and not self.registered:
            yield self._p(pc.PROMPT, self._sys("not_registered"))
            return self.hl.root
        for _ in range(2):
            ev = yield self._p(pc.PROMPT, self._sys("confirm"), barge={"dtmf"})
            if ev is None:
                ev = yield _Listen(6.0, frozenset({"dtmf"}))
            if ev is not None and ev.value == "1":
                ref = "".join(str(self.rng.randrange(10)) for _ in range(node.ref_digits))
                self.refs[node.action] = ref
                text = self._sys("ref", ref=spaced(ref))
                for _ in range(3):
                    yield self._p(pc.PROMPT, text)
                    ev = yield self._p(pc.PROMPT, self._sys("after_fact"), barge={"dtmf"})
                    if ev is None:
                        ev = yield _Listen(5.0, frozenset({"dtmf"}))
                    if ev is None or ev.value != "1":
                        break
                yield self._p(pc.PROMPT, self._sys("goodbye"))
                self._end("ivr_completed", self.cursor)
                raise _End
            if ev is not None and ev.value == "2":
                return self.hl.root
        return self.hl.root

    # -------------------------------------------------------------- queue, hold, executive
    def _n_queue(self, node: Node):
        hl, rng = self.hl, self.rng
        self.dept_reached = node.dept
        if self.t_queue_enter is None:
            self.t_queue_enter = self.cursor
        o, c = hl.hours
        if not (o <= self.hour < c):
            yield self._p(pc.PROMPT, self._sys("closed", open=o, close=c - 12 if c > 12 else c))
            self._end("closed", self.cursor)
            raise _End
        if rng.random() < self.scn.get("busy_disconnect_p", hl.hold["busy_disconnect_p"]):
            yield self._p(pc.ANNOUNCE, self._sys("busy"))
            self._end("busy_disconnect", self.cursor)
            raise _End
        yield self._p(pc.PROMPT, self._sys("connecting"))
        yield from self._hold(self.wait_s, offer_callback=True)
        yield from self._executive(node.dept)

    def _hold(self, wait: float, offer_callback: bool):
        hl, rng, h = self.hl, self.rng, self.hl.hold
        start = self.cursor
        deadline = start + wait
        every = self.scn.get("announce_every_s", h["announce_every_s"])
        agent_like_p = self.scn.get("agent_like_p", h["agent_like_p"])
        cb_at = h.get("callback_after_s") if offer_callback else None
        drop_rate = self.scn.get("drop_per_min", h["drop_per_min"]) / 60.0
        drop_at = start + rng.expovariate(drop_rate) if drop_rate > 0 else math.inf
        if "drop_at" in self.scn:
            drop_at = start + self.scn["drop_at"]
        next_ann = start + h["first_msg_s"]
        first = True
        lang = self.lang if self.lang in ("en", "hi") else "en"
        while self.cursor < deadline - 0.25:
            now = self.cursor
            if now >= drop_at:
                self.hold_s += now - start
                self._end("call_dropped", now)
                raise _End
            if cb_at is not None and now >= start + cb_at:
                cb_at = None
                ev = yield self._p(pc.ANNOUNCE, self._sys("callback"), barge={"dtmf"})
                if ev is None:
                    ev = yield _Listen(6.0, frozenset({"dtmf"}), pc.MUSIC)
                if ev is not None and ev.value == "1":
                    yield self._p(pc.ANNOUNCE, self._sys("callback_ok"))
                    self.callback_t = self.cursor
                    self.hold_s += self.cursor - start
                    self._end("callback_scheduled", self.cursor)
                    raise _End
                continue
            if now >= next_ann:
                if not first and rng.random() < agent_like_p:
                    yield self._p(pc.AGENT_LIKE, h["agent_like"][lang])
                else:
                    text = h["announce"][lang]
                    remaining = max(deadline - now, 0)
                    if h.get("position"):
                        text += " " + self._sys("position", k=max(1, round(remaining / 45)))
                    if h.get("est_wait"):
                        text += " " + self._sys("est_wait", m=max(1, round(remaining / 60 + rng.gauss(0, 0.8))))
                    yield self._p(pc.ANNOUNCE, text)
                first = False
                next_ann = self.cursor + every
                continue
            seg_end = min(next_ann, deadline, drop_at, start + cb_at if cb_at is not None else math.inf)
            if rng.random() < h["silence_gap_p"] * 0.3 and seg_end - now > 6:
                gap = rng.uniform(*h["silence_gap_s"])
                yield _Play(pc.SILENCE, dur=min(gap, seg_end - now), speaker="hold")
                continue
            yield _Play(pc.MUSIC, dur=max(0.5, seg_end - now), speaker="hold")
        self.hold_s += self.cursor - start
        if not (self.scn.get("abrupt", rng.random() < h["abrupt_pickup_p"])):
            yield _Play(pc.SILENCE, dur=rng.uniform(0.6, 1.6), speaker="hold")

    def _xs(self, key, **kw):
        en, hi = EXEC[key]
        return (hi if self.lang == "hi" else en).format(**kw)

    def _executive(self, dept: str):
        """A customer-care executive, or the bank's own voicebot (S18)."""
        ex, rng = self.hl.executive, self.rng
        name = rng.choice(ex["names"])
        label = pc.AI_AGENT if self.ai_exec else pc.HUMAN
        if self.pickup_t is None:
            self.pickup_t = self.cursor
        greet = self._xs("ai_greet", brand=ex["brand"]) if self.ai_exec else \
            ex["greeting"]["hi" if self.lang == "hi" else "en"].format(name=name, brand=ex["brand"])
        yield self._p(label, greet, speaker="exec")
        target_dept = self.hl.node(self.task.target).dept if self.hl.node(self.task.target).type == "queue" else dept
        patience = self.exec_patience * (4 if self.ai_exec else 1)
        stalls, hello_said, idle = 0, False, 0
        listen = frozenset({"speech", "user_join"})
        while True:
            ev = yield _Listen(patience / 2, listen, pc.HUMAN_WAIT)
            if ev is None:
                if not hello_said:
                    hello_said = True
                    yield self._p(label, self._xs("hello"), speaker="exec")
                    continue
                yield self._p(label, self._xs("bye_dead"), speaker="exec")
                self.exec_outcome["hung_up"] = "dead_air"
                self._end("exec_hung_up", self.cursor)
                raise _End
            if ev.kind == "user_join":
                self.handed_off = True
                self.exec_outcome["dept_ok"] = dept == target_dept
                self._end("handed_off", self.cursor)
                raise _End
            u: Utterance = ev.value
            if u.intent == "stall":
                if stalls < P("exec.max_stalls"):
                    stalls += 1
                    hello_said = False
                    yield self._p(label, self._xs("hold_ok"), speaker="exec")
                    patience = P("exec.stall_extension_s") * 2
                    continue
                yield self._p(label, self._xs("hold_over"), speaker="exec")
                self.exec_outcome["hung_up"] = "stall_limit"
                self._end("exec_hung_up", self.cursor)
                raise _End
            if u.intent in ("probe", "platform_check", "greet_reply"):
                idle += 1
                if idle > 3:   # nobody says what they want: a real executive gives up
                    yield self._p(label, self._xs("bye_dead"), speaker="exec")
                    self.exec_outcome["hung_up"] = "no_request"
                    self._end("exec_hung_up", self.cursor)
                    raise _End
                hello_said = False
                patience = self.exec_patience
                yield self._p(label, self._xs("probe_reply"), speaker="exec")
                continue
            if u.intent == "handshake_offer" and self.ai_exec and ex.get("handshake", False) or \
                    (u.intent == "handshake_offer" and self.ai_exec and self.scn.get("handshake")):
                yield _Play(pc.DATA, dur=1.5, speaker="exec")
                ref = "".join(str(rng.randrange(10)) for _ in range(8))
                self.refs["handshake"] = ref
                self.exec_outcome.update({"completed": True, "handshake": True, "ref": ref})
                self.agent_events.append(("handshake_result", ref))
                self._end("completed", self.cursor)
                raise _End
            if u.intent == "request_human" and self.ai_exec:
                yield self._p(label, self._xs("ai_connect"), speaker="exec")
                self.ai_exec = False
                self.transfers += 1
                yield from self._hold(self.wait_s * rng.uniform(0.15, 0.4), offer_callback=False)
                return (yield from self._executive(dept))
            if u.intent in ("disclose", "reason", "provide"):
                return (yield from self._autonomous(label, dept, target_dept, u))
            # anything else counts as the caller being present
            hello_said = False
            patience = self.exec_patience

    def _ask(self, label, key, timeout=20.0):
        yield self._p(label, self._xs(key), speaker="exec")
        return (yield _Listen(timeout, frozenset({"speech", "user_join"}), pc.HUMAN_WAIT))

    def _autonomous(self, label, dept, target_dept, first: Utterance):
        """The executive deals with HoldForMe directly (Pine-style task completion)."""
        ex, rng, per = self.hl.executive, self.rng, self.persona
        if self.refuse_ai and not self.ai_exec:
            ev = yield from self._ask(label, "refuse_ai", 25.0)
            if ev is not None and ev.kind == "user_join":
                self.handed_off = True
                self.exec_outcome.update({"dept_ok": dept == target_dept, "refused_ai": True})
                self._end("handed_off", self.cursor)
                raise _End
            self.exec_outcome["refused_ai"] = True
            yield self._p(label, self._xs("bye"), speaker="exec")
            self._end("exec_refused_ai", self.cursor)
            raise _End
        for f in ex["verify"]:
            ok = False
            attempt = repeats = 0
            while attempt < 2:
                ev = yield from self._ask(label, f"ask_{f}")
                if ev is not None and ev.kind == "speech" and ev.value.intent == "ask_repeat" and repeats < 2:
                    repeats += 1
                    continue
                attempt += 1
                if ev is not None and ev.kind == "user_join":
                    self.handed_off = True
                    self.exec_outcome["dept_ok"] = dept == target_dept
                    self._end("handed_off", self.cursor)
                    raise _End
                if ev is not None and ev.value.slots.get("field") == f:
                    val = str(ev.value.slots.get("value", "")).lower().replace(" ", "")
                    truth = str(per.field_value(f)).lower().replace(" ", "")
                    if val == truth or (f not in ("name",) and Persona.digits_only(val) == Persona.digits_only(truth)):
                        ok = True
                        break
                yield self._p(label, self._xs("mismatch"), speaker="exec")
            if not ok:
                self.exec_outcome["verification_failed"] = f
                yield self._p(label, self._xs("bye"), speaker="exec")
                self._end("verification_failed", self.cursor)
                raise _End
        if ex.get("otp"):
            yield self._p(label, self._xs("otp_sent"), speaker="exec")
            got = None
            for wait in (45.0, 45.0):
                ev = yield _Listen(wait, frozenset({"speech"}), pc.HUMAN_WAIT)
                if ev is not None and ev.value.slots.get("field") == "otp":
                    got = str(ev.value.slots.get("value"))
                    break
                yield self._p(label, self._xs("take_time"), speaker="exec")
            if got != per.truth["otp"]:
                self.exec_outcome["verification_failed"] = "otp"
                yield self._p(label, self._xs("bye"), speaker="exec")
                self._end("verification_failed", self.cursor)
                raise _End
        ev = yield from self._ask(label, "how_help", 25.0)
        if ev is None or ev.kind != "speech":
            self._end("exec_hung_up", self.cursor)
            raise _End
        first_push = ev.value.intent == "push"
        forced = self.scn.get("force_transfer") and self.transfers == 0   # the scenario forces one transfer, not a loop
        if dept != target_dept or forced or (self.transfers == 0 and rng.random() < ex.get("transfer_p", 0) * 0.5):
            yield self._p(label, self._xs("transfer", dept=target_dept.replace("_", " ")), speaker="exec")
            self.transfers += 1
            yield from self._hold(self.wait_s * rng.uniform(0.15, 0.4), offer_callback=False)
            self.ai_exec = False
            return (yield from self._executive(target_dept))
        if self.scn.get("midcall_hold", rng.random() < P("exec.midcall_hold_p")):
            yield self._p(label, self._xs("check_hold"), speaker="exec")
            yield _Play(pc.MUSIC, dur=rng.uniform(*P("exec.midcall_hold_s")), speaker="hold")
            yield self._p(label, self._xs("thanks_hold"), speaker="exec")
        pine = self.task.pine or "complaint"
        ref = "".join(str(rng.randrange(10)) for _ in range(8))
        self.exec_outcome["ref"] = ref
        if pine in ("complaint", "refund_status"):
            if pine == "complaint":
                line = self._xs("complaint_ref", ref=spaced(ref))
            else:
                amt, date = rng.randrange(2500, 12000), f"{rng.randrange(1, 28)} October"
                self.exec_outcome.update({"amount": str(amt), "date": date})
                line = self._xs("refund_ref", ref=spaced(ref), amt=amt, date=date)
            yield self._p(label, line, speaker="exec")
            yield from self._repeat_loop(label, ref)
            self.exec_outcome["completed"] = True
        elif pine == "cancel":
            accepted = False
            for offer in ex.get("offers", []):
                ev = yield from self._ask_text(label, self._xs("offer", offer=offer))
                if ev is not None and ev.value.intent == "accept_offer":
                    accepted = True
                    break
            self.exec_outcome["accepted_offer"] = accepted
            yield self._p(label, self._xs("offer_taken" if accepted else "cancelled", ref=spaced(ref)), speaker="exec")
            self.exec_outcome["completed"] = True
            yield from self._repeat_loop(label, ref)
        elif pine == "negotiate":
            ladder = ex.get("discounts", [0, 10, 20])
            level = 0
            pushes = 0
            while True:
                if first_push:
                    it, first_push = "push", False
                else:
                    ev = yield _Listen(15.0, frozenset({"speech"}), pc.HUMAN_WAIT)
                    if ev is None:
                        break
                    it = ev.value.intent
                if it == "push" and pushes < 3:
                    pushes += 1
                    if level < len(ladder) - 1 and rng.random() < 0.65:
                        level += 1
                        yield self._p(label, self._xs("discount", d=ladder[level]), speaker="exec")
                    elif level == 0:
                        yield self._p(label, self._xs("no_discount"), speaker="exec")
                    else:
                        yield self._p(label, self._xs("best"), speaker="exec")
                    continue
                break
            self.exec_outcome["discount"] = ladder[level]
            yield self._p(label, self._xs("applied", ref=spaced(ref)), speaker="exec")
            self.exec_outcome["completed"] = True
            yield from self._repeat_loop(label, ref)
        ev = yield from self._ask(label, "anything", 10.0)
        yield self._p(label, self._xs("bye"), speaker="exec")
        self._end("completed", self.cursor)
        raise _End

    def _ask_text(self, label, text):
        yield self._p(label, text, speaker="exec")
        return (yield _Listen(15.0, frozenset({"speech"}), pc.HUMAN_WAIT))

    def _repeat_loop(self, label, ref):
        """The caller may ask for the number again, or read it back for confirmation."""
        for _ in range(6):
            ev = yield _Listen(8.0, frozenset({"speech"}), pc.HUMAN_WAIT)
            if ev is not None and ev.value.intent == "ask_repeat":
                yield self._p(label, self._xs("repeat_ref", ref=spaced(ref)), speaker="exec")
                continue
            if ev is not None and ev.value.intent == "confirm_number":
                if str(ev.value.slots.get("value")) == ref:
                    self.exec_outcome["read_back_ok"] = True
                    yield self._p(label, self._xs("correct"), speaker="exec")
                    break
                yield self._p(label, self._xs("wrong_number", ref=spaced(ref)), speaker="exec")
                continue
            break
