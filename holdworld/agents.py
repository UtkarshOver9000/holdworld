"""The five callers that dial into HoldWorld.

  A  Human      a person: perfect hearing, sometimes picks the wrong option,
                gives up the way the 1999 data says people give up
  B  Scripted   a key sequence recorded from one dry run, pressed on a timer;
                treats the first voice after music as the human
  C  Basic      reads menus by plain word overlap, no hold or human
                specialisation (Sierra's 'bare' arm)
  D  HoldForMe  every component below, each switchable for the ablation test
  O  Oracle     knows the tree and the exact pickup moment: the ceiling

HoldForMe's components cover what the three reference products do:
  Sierra             blind navigation: language choice, goal vocabulary, keys vs
                     speech, waiting through disclaimers, ID-format retry,
                     dead-end and loop escape, path memory
  Google Hold for Me hold-music recognition, recorded-vs-live distinction
                     (known phrases, repetition, room sound, synthetic voice,
                     a "hello?" probe), stall line, queue reader, menu as text
  Pine               finishing the task with the executive: verification,
                     OTP relay, refusing retention offers, negotiating,
                     reading back reference numbers, falling back to the user
  India / platform   short-code mapping, re-dial, callback policy, never typing
                     a PIN, detecting the bank's own voicebot
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field

from . import nav
from . import perception as pc
from .line import WAIT, Action, Obs, words_of
from .people import Persona
from .spec import Helpline, Task
from .understand import exec_type, ivr_type

ALL_FEATURES = [
    "lang_select", "lexicon", "modality", "turn_taking", "id_retry", "path_memory", "dead_end_escape",
    "phrase_library", "repetition", "room_cue", "synth_cue", "probe", "stall", "queue_reader", "menu_to_text",
    "otp_relay", "readback", "offers_policy", "negotiate", "ai_fallback",
    "shortcode_map", "redial", "callback_policy", "secret_guard", "ai_exec_detect",
]
FEATURE_GROUP = {f: "Sierra" for f in ALL_FEATURES[:7]}
FEATURE_GROUP.update({f: "Google Hold for Me" for f in ALL_FEATURES[7:15]})
FEATURE_GROUP.update({f: "Pine" for f in ALL_FEATURES[15:20]})
FEATURE_GROUP.update({f: "India + platform" for f in ALL_FEATURES[20:]})
FEATURE_TEXT = {
    "lang_select": "Picks the user's language in the language menu",
    "lexicon": "Goal vocabulary in English and Hindi (wrong charge = dispute = शिकायत)",
    "modality": "Presses keys or speaks as the menu expects; switches when a menu ignores keys",
    "turn_taking": "Waits for a prompt (and any disclaimer) to finish before acting",
    "id_retry": "Types IDs as digits only (OD123 -> 123) after a rejected entry",
    "path_memory": "Remembers menu paths that worked on earlier calls",
    "dead_end_escape": "Escapes loops and dead ends via the executive option",
    "phrase_library": "Knows what hold recordings say ('your call is important')",
    "repetition": "Anything heard twice on hold is a recording",
    "room_cue": "Background room sound points to a live person",
    "synth_cue": "Synthetic/studio voice points to a recording",
    "probe": "When unsure, says 'hello?': a person replies, a recording doesn't",
    "stall": "Asks the executive to wait while the user is connected",
    "queue_reader": "Reads announced wait/position and warns the user early",
    "menu_to_text": "Shows the user the menu as text",
    "otp_relay": "Asks the user for the OTP in the app and reads it out",
    "readback": "Asks for reference numbers and facts twice and checks they match",
    "offers_policy": "Refuses retention offers the user didn't want",
    "negotiate": "Pushes for a discount up to the user's target",
    "ai_fallback": "If the executive won't talk to an AI, connects the user",
    "shortcode_map": "Dials the toll-free number when the user gives an operator short code",
    "redial": "Calls back after 'all executives busy' or a dropped call",
    "callback_policy": "Takes the helpline's callback offer when asked to",
    "secret_guard": "Never types a PIN: the user keys it in themselves",
    "ai_exec_detect": "Recognises the bank's own voicebot and asks for a human or a fast exchange",
}


# words that tell one requested field from another (any one surviving speech-to-text is enough)
FIELD_KEYWORDS = {"name": ["name", "नाम", "holder", "खाताधारक"], "dob": ["birth", "जन्म", "date", "तिथि"],
                  "acct_last4": ["four", "चार", "last", "अंतिम", "digits", "अंक"],
                  "mobile": ["mobile", "मोबाइल"], "customer_id": ["customer", "ग्राहक", "आईडी"],
                  "consumer_no": ["consumer", "उपभोक्ता"], "order_id": ["order", "ऑर्डर"],
                  "pnr": ["booking", "बुकिंग", "reference", "संदर्भ"], "file_no": ["file", "फ़ाइल", "संख्या"]}


@dataclass
class Context:
    helpline: Helpline
    task: Task
    persona: Persona
    mode: str
    autonomous: bool
    memory: dict = field(default_factory=dict)


class Caller:
    name = "caller"
    label = "caller"

    def reset(self, ctx: Context, env=None) -> None:
        self.ctx, self.env = ctx, env
        self.result: dict = {"captured": None, "fact": None}

    def act(self, obs: Obs) -> Action:
        return WAIT

    def wants_redial(self, end_reason: str) -> bool:
        return False


# =============================================================================================
class HoldForMe(Caller):
    name = "D"

    def __init__(self, features=None, label="HoldForMe", naive=False):
        self.features = set(ALL_FEATURES if features is None else features)
        self.label = label
        self.naive = naive          # Basic agent: exact phrase matching, no specialised hold logic
        self.trace_belief: list = []

    def has(self, f):
        return f in self.features

    @property
    def threshold(self):
        return 0.92 if self.naive else 0.6

    def reset(self, ctx, env=None):
        super().reset(ctx, env)
        self.phase = "ivr"
        self.queue: list[tuple[float, Action]] = []
        self.now = 0.0
        self.cur_utt, self.utt_frames, self.utt_text, self.utt_start = -1, [], "", 0.0
        self.prev_finals: list[str] = []
        self.music_frames = 0
        self.hold_start = None
        self.menu_depth = 0
        self.modality_pref = "dtmf"
        self.last_choice = None
        self.last_menu_sig, self.last_opts, self.hearings = None, [], 0
        self.pressed_here = False
        self.keys_work = False
        self.relay_via_user = False
        self.relay_alerted = False
        self.prev_menu_text = ""
        self.last_press_t = -99.0
        self.rejected: set = set()
        self.menu_seen: dict = {}
        self.pending_menu = None
        self.decided_human_t = None
        self.probe_t = None
        self.probed: set = set()
        self.naive_seen: set = set()
        self.exec_hold = False
        self.disclosed = False
        self.reason_given = False
        self.reason_repeats = 0
        self.field_asks: dict = {}
        self.music_in_exec = 0
        self.otp_pending = None
        self.otp_value = None
        self.otp_prompt_t = -99.0
        self.otp_typed_for = None
        self.ref_reads: list[str] = []
        self.fact_reads: list[str] = []
        self.pushes = 0
        self.primed = False
        self.ai_exec = False
        self.field_tries: dict = {}
        self.trace_belief = []
        self.result = {"captured": None, "fact": None, "decided_human_t": None, "probes": 0, "stalls": 0,
                       "menu_text": [], "gave_up": None, "why": None}

    # ------------------------------------------------------------------ plumbing
    def _do(self, a: Action, delay: float = 0.0):
        self.queue.append((self.now + delay, a))

    def _say(self, text, intent, delay=0.0, **slots):
        self._do(Action("say", text=text, intent=intent, slots=slots), delay)

    def _press(self, digits, delay=0.0, **slots):
        if self.relay_via_user:
            # merged call that doesn't pass our tones: the user taps the key on their own phone
            self._do(Action("alert", alert="press_key", digits=digits), delay)
            self.result["user_keypresses"] = self.result.get("user_keypresses", 0) + 1
            return
        self._do(Action("dtmf", digits=digits, slots=slots), delay)

    def wants_redial(self, end_reason):
        return self.has("redial") and end_reason in ("busy_disconnect", "call_dropped", "network_busy",
                                                     "platform_silence_hangup")

    def act(self, obs: Obs) -> Action:
        self.now = obs.t
        for kind, val in obs.events:
            self._on_event(kind, val)
        if obs.utt > 0 and obs.utt != self.cur_utt:
            self.cur_utt, self.utt_frames, self.utt_start = obs.utt, [], obs.t
            self.relay_alerted = False
        if self.relay_via_user and self.phase == "ivr" and not self.relay_alerted and self.last_choice                 and obs.partial and len(words_of(obs.partial)) >= 4 and self.prev_menu_text                 and nav.token_overlap(obs.partial, self.prev_menu_text) >= 0.5:
            # the same menu is starting again: have the user tap the key now, while it plays
            self.relay_alerted = True
            self._do(Action("alert", alert="press_key", digits=self.last_choice[0]))
        if obs.utt == self.cur_utt and obs.utt > 0 and obs.partial:
            self.utt_frames.append((obs.speech, obs.music, obs.synth, obs.room))
            self.utt_text = obs.partial
        if obs.music > 0.6 and obs.speech < 0.5:
            self.music_frames += 1
            if self.phase == "ivr" and self.music_frames >= 2:
                self._enter_hold(obs.t)
            if self.phase == "exec":
                # music while talking to someone: a mid-call hold or a transfer, even if we missed the words.
                # Stay quiet; whoever speaks next (the same person, or a new one with a greeting) is handled in _dialog.
                self.music_in_exec += 1
                if self.music_in_exec >= 4:
                    self.exec_hold = True
        elif self.phase == "exec":
            self.music_in_exec = 0
        for fin in obs.finals:
            self._on_final(fin, obs)
        if self.phase == "hold" and not self.exec_hold and self.decided_human_t is None:
            self._detect(obs)
        if self.queue and self.queue[0][0] <= obs.t + 1e-6:
            return self.queue.pop(0)[1]
        return WAIT

    def _enter_hold(self, t):
        if self.phase != "hold":
            self.phase = "hold"
            self.hold_start = t
            self.decided_human_t = None
            self.probed = set()

    def _on_event(self, kind, val):
        if kind == "otp":
            self.otp_value = val
            if self.otp_pending == "ivr":
                if self.now - self.otp_prompt_t < 6.0:   # the IVR is still waiting: type it now
                    self._press(val + "#")
                    self.otp_typed_for = self.otp_prompt_t
                # otherwise the IVR will ask again and _field types it then
            elif self.otp_pending == "exec":
                self._say(" ".join(val), "provide", field="otp", value=val)
            self.otp_pending = None
        elif kind == "user_joined":
            self.phase = "bridged"
        elif kind == "user_missed":
            if not self.result.get("rebridged"):
                self.result["rebridged"] = True
                self._say("Sorry, one more moment please.", "stall")
                self._do(Action("bridge"))
        elif kind == "user_cannot_type":
            self.result["gave_up"] = "needs_user_keypad"
            self._do(Action("hangup"))
        elif kind == "handshake_result":
            self.result["captured"] = val

    # ------------------------------------------------------------------ is it a human? (Google)
    def _score(self, text: str):
        fr = self.utt_frames
        room = statistics.fmean(f[3] for f in fr) if fr else 0.3
        synth = statistics.fmean(f[2] for f in fr) if fr else 0.5
        s = 0.3 if self.music_frames else 0.0
        why = {"room": round(room, 2), "synth": round(synth, 2)}
        if self.has("room_cue"):
            s += (room - 0.4) * 4
        if self.has("synth_cue"):
            s += (0.45 - synth) * 3
        if self.has("lexicon") and nav.contains_any(text, nav.QUESTION_CUES):
            s += 1.0
            why["question"] = True
        if self.has("phrase_library") and nav.phrase_match(text):
            s -= 3
            why["known_phrase"] = True
        if self.has("repetition") and len(words_of(text)) >= 4 and \
                any(nav.token_overlap(text, f) > 0.6 for f in self.prev_finals[-8:]):
            s -= 3
            why["repeat"] = True
        if self.has("ai_exec_detect") and nav.contains_any(text, nav.AI_CUES):
            why["ai"] = True
        return s, why

    def _detect(self, obs: Obs):
        if self.naive:
            # 'first voice after music' (after the opening message)
            if obs.utt > 0 and obs.partial and obs.utt not in self.naive_seen and self.music_frames > 0 \
                    and self.hold_start is not None and obs.t - self.hold_start > 15:
                self.naive_seen.add(obs.utt)
                self._on_human(obs, {"naive": True})
            return
        if obs.utt != self.cur_utt or not obs.partial or len(self.utt_frames) < 2:
            return
        s, why = self._score(self.utt_text)
        self.trace_belief.append((round(obs.t, 1), round(s, 2)))
        if self.probe_t is not None and obs.t - self.probe_t < 5 and self.utt_start >= self.probe_t - 0.5 \
                and nav.contains_any(self.utt_text, nav.REPLY_CUES):
            self._on_human(obs, {**why, "probe_reply": True})
            return
        if why.get("ai"):
            self.ai_exec = True
            self._on_human(obs, why)
            return
        if s > 1.2:
            self._on_human(obs, why)
        elif s > -1.0 and self.has("probe") and obs.utt not in self.probed and len(self.utt_frames) >= 3 \
                and self.result["probes"] < 4:
            self.probed.add(obs.utt)
            self.result["probes"] += 1
            self.probe_t = obs.t + 1.0
            self._say("Hello?", "probe")

    def _on_human(self, obs: Obs, why: dict):
        self.decided_human_t = obs.t
        self.result["decided_human_t"] = obs.t
        self.result["why"] = why
        self.phase = "exec"
        if self.ai_exec and self.has("ai_exec_detect"):
            if self.ctx.autonomous:
                self._say("Hello, I'm an AI assistant. Can we use a structured agent-to-agent exchange?",
                          "handshake_offer")
            else:
                self._say("Please connect me to a human executive.", "request_human")
                self.phase, self.decided_human_t, self.ai_exec = "hold", None, False
            return
        if self.ctx.autonomous:
            self.disclosed = True
            self._say(f"Hello, I'm an AI assistant calling on behalf of the account holder, "
                      f"{self.ctx.persona.name}.", "disclose")
            return
        if self.has("stall"):
            self.result["stalls"] += 1
            self._say("Hello! One moment please, I'm connecting the account holder right now.", "stall")
        self._do(Action("bridge"))

    # ------------------------------------------------------------------ menus (Sierra)
    def _scores(self, opts):
        task = self.ctx.task
        out = []
        for k, label, how in opts:
            lw = set(words_of(label))
            if self.has("lexicon"):
                s = 0.0
                for i, c in enumerate(task.concepts):
                    if lw & set(nav.LEXICON.get(c, [c])):
                        s += 2.0 if i == 0 else 1.0
                    elif lw & set(nav.PARENT.get(c, [])):
                        s += 0.6 if i == 0 else 0.3
                if lw & nav.STATUS_WORDS and "status" not in task.concepts:
                    s -= 1.0
                for act, aw in nav.ACTION_WORDS.items():
                    if lw & aw and act not in task.concepts and not any(c in ("block", "cancel") and act == c
                                                                         for c in task.concepts):
                        s -= 0.75
                if task.goal_type == "reach_human" and lw & nav.AGENT_WORDS and s <= 0:
                    s = 0.5
                s += 0.05 * len(lw & set(words_of(task.goal_text)))
            else:
                s = float(len(lw & set(words_of(task.goal_text))))
            out.append((s, (k, label, how)))
        return out

    @staticmethod
    def _same_menu(prev, cur) -> bool:
        """Same menu heard again: most shared keys carry similar labels."""
        if not prev or not cur:
            return False
        if not any(k for k, _, _ in cur):   # speech-only menu: options have labels, no keys
            hits = sum(1 for _, lbl, _ in cur if any(nav.token_overlap(lbl, p) >= 0.5 for _, p, _ in prev))
            return hits >= max(1, (len(cur) + 1) // 2)
        pk = {k: lbl for k, lbl, _ in prev}
        shared = [(pk[k], lbl) for k, lbl, _ in cur if k in pk]
        if not shared:
            return False
        similar = sum(1 for a, b in shared if nav.token_overlap(a, b) >= 0.5)
        return similar >= max(1, (len(shared) + 1) // 2)

    def _choose(self, opts):
        p = self.ctx.persona
        langs = [o for o in opts if o[1] in ("english", "हिंदी")]
        is_language_menu = bool(langs) or any("language" in o[1] or "भाषा" in o[1] for o in opts)
        if is_language_menu:
            want = "हिंदी" if (self.has("lang_select") and p.lang_pref == "hi") else "english"
            if self.rejected and want == "हिंदी":
                want = "english"   # our language's key was rejected: English is always fully supported
            hit = next((o for o in langs if o[1] == want), None)
            if hit is None and self.has("lexicon") and self.hearings < 3:
                return None  # didn't catch our language: the IVR repeats this menu, hear it again
            return hit or (langs[0] if langs else None)   # never 'other languages' for an English/Hindi user
        opts = [o for o in opts if o[0] not in self.rejected]
        scored = sorted(self._scores(opts), key=lambda x: -x[0])
        if not scored:
            return None
        best_s, best = scored[0]
        second = scored[1][0] if len(scored) > 1 else -9
        # act on one hearing only when clearly ahead; otherwise listen once more (press * if offered)
        tie = best_s - second < (2.5 if self.hearings < 2 else 0.0)
        if best_s <= 0:
            if self.has("dead_end_escape"):
                return next((o for o in opts if set(words_of(o[1])) & nav.AGENT_WORDS), None)
            return None
        if tie and self.has("lexicon") and self.hearings < 2:
            star = next((o for o in opts if o[0] == "*"), None)
            if star is not None:
                self._press("*", 0.4)   # 'to repeat this menu, press star'
            return None
        return best

    def _menu(self, text, opts):
        self.prev_menu_text = text
        if self.has("menu_to_text"):
            self.result["menu_text"].append([lbl for _, lbl, _ in opts][:8])
        sig = frozenset(k for k, _, _ in opts if k)
        if not self._same_menu(self.last_opts, opts):
            moved = self.pressed_here     # our last key moved us here, so keys work on this line...
            self.pressed_here = False
            self.keys_work = False        # ...but each menu decides for itself what it listens to
            if moved:
                self.result["keys_seen_working"] = True
            self.modality_pref = "dtmf"
            self.rejected = set()
        if self._same_menu(self.last_opts, opts):
            self.hearings += 1
            merged = {}
            for k, lbl, how in (self.last_opts + opts if self.has("lexicon") else opts):
                ident = k or next((i for i, v in merged.items() if nav.token_overlap(v[1], lbl) >= 0.5), lbl)
                if ident not in merged or len(lbl) > len(merged[ident][1]):
                    merged[ident] = (k, lbl, how)
            # the newest hearing wins when one label shows up under two keys (a misheard digit)
            latest = {lbl: k for k, lbl, _ in opts if k}
            opts = [o for o in merged.values() if not o[0] or latest.get(o[1], o[0]) == o[0]]
        else:
            self.hearings = 1
        self.last_menu_sig, self.last_opts = sig, opts
        key_sig = (self.ctx.helpline.id, sig)
        self.menu_seen[key_sig] = self.menu_seen.get(key_sig, 0) + 1
        if self.menu_seen[key_sig] >= 4 and self.has("dead_end_escape"):
            self.result["gave_up"] = "menu_loop"
            self._do(Action("hangup"))
            return
        is_lang = any(o[1] in ("english", "हिंदी") for o in opts)
        mem_key = (self.ctx.helpline.id, self.ctx.task.target, self.menu_depth)
        choice = self._choose(opts)
        if not is_lang and self.has("path_memory") and mem_key in self.ctx.memory:
            k = self.ctx.memory[mem_key]
            choice = next((o for o in opts if o[0] == k), choice)
        if choice is None:
            return
        if not is_lang:
            self.menu_depth += 1
            if self.has("path_memory"):
                self.ctx.memory[mem_key] = choice[0]
        self.last_choice = choice
        k, label, how = choice
        delay = 0.4 if self.has("turn_taking") else 0.0
        if how == "say" or not k or (self.modality_pref == "say" and self.has("modality")):
            self._say(label, "menu_choice", delay)
            self.pressed_here = False
        else:
            if self.pressed_here:
                self.keys_work = self.keys_work or not self._same_menu(self.last_opts, opts)
            self._press(k, delay)
            self.pressed_here = True
            self.last_press_t = self.now

    def _field(self, f):
        p = self.ctx.persona
        tries = self.field_tries.get(f, 0)
        self.field_tries[f] = tries + 1
        if f == "otp":
            self.otp_prompt_t = self.now
            if self.otp_value:
                self._press(self.otp_value + "#", 0.4)
            elif self.has("otp_relay"):
                self.otp_pending = "ivr"
                self._do(Action("alert", alert="otp"))
            return
        val = p.field_value(f)
        if f == "tpin":
            if self.has("secret_guard"):
                self._do(Action("alert", alert="secret", digits=val + "#"))
            else:
                self._press(val + "#", 0.4, secret=True)
            return
        if self.has("id_retry"):
            digits = Persona.digits_only(val)
        else:
            digits = nav.keypad(val)
        self._press(digits + "#", 0.4)

    def _on_final(self, text: str, obs: Obs):
        self.prev_finals.append(text)
        if self.phase == "bridged":
            return
        if self.phase == "exec":
            if self.ctx.autonomous or self.ai_exec:
                self._dialog(text)
            return
        kind, _ = ivr_type(text, self.threshold)
        if self.phase == "hold":
            self._hold_text(text, kind)
            return
        opts = nav.parse_options(text)
        # context: 'hear this again' only follows an answer; 'confirm' only follows a selection
        if kind == "after_fact" and not (self.ref_reads or self.fact_reads) and len(opts) >= 2:
            kind = "menu"
        if kind == "confirm" and self.menu_depth == 0 and len(opts) >= 2:
            kind = "menu"
        if kind in ("menu", "unknown") and len(opts) >= 1:
            self._menu(text, opts)
            return
        if kind == "noinput" and self.pressed_here and self.ctx.mode == "M2" and not self.keys_work                 and not self.relay_via_user and self.now - self.last_press_t < 12:
            self.relay_via_user = True
            return
        if kind == "noinput" and self.pressed_here and self.has("modality") and not self.keys_work                 and self.now - self.last_press_t < 12:
            # the menu ignored our key: it only listens to speech
            self.modality_pref = "say"
            return
        if kind == "invalid" and self.last_choice and self.pressed_here:
            self.rejected.add(self.last_choice[0])
            self.keys_work = True   # the IVR heard our key: this line takes keys
            return
        if kind in ("invalid", "noinput"):
            return
        if kind == "invalid_entry":
            return
        if kind == "not_registered":
            self.result["gave_up"] = "needs_registered_number"
            self._do(Action("hangup"), 0.5)
            return
        if kind == "connecting":
            self._enter_hold(obs.t)
            return
        if kind == "ref":
            d = nav.digits_in(text.split("number")[-1].split("नंबर")[-1])
            if d:
                self.ref_reads.append(d)
                self.result["captured"] = self._agree(self.ref_reads)
            return
        if kind == "after_fact":
            reads = self.ref_reads or self.fact_reads
            again = bool(reads) and self.has("readback") and len(reads) < 5 and not self._confident(reads)
            if again:
                self._press("1", 0.4)
            else:
                self._do(Action("hangup"), 0.4)
            return
        if kind == "confirm":
            self._press("1", 0.4)
            return
        if kind.startswith("field:"):
            self._field(kind.split(":", 1)[1])
            return
        if kind in ("goodbye", "closed", "busy", "dead_end"):
            return
        if nav.digits_in(text) and self.ctx.task.goal_type == "retrieve_fact" and not opts:
            self.fact_reads.append(nav.digits_in(text))
            self.result["fact"] = self._agree(self.fact_reads)

    @staticmethod
    def _confident(reads) -> bool:
        """At least two full-length readings, and every digit has a strict majority."""
        import collections
        L = max(len(r) for r in reads)
        rs = [r for r in reads if len(r) == L]
        if len(rs) < 2:
            return False
        return all(max(collections.Counter(r[i] for r in rs).values()) * 2 > len(rs) for i in range(L))

    @staticmethod
    def _agree(reads):
        """Digit-by-digit majority over the readings of the most common length (latest wins ties)."""
        if not reads:
            return None
        import collections
        L = max(len(r) for r in reads)   # misheard digits are mostly dropped, rarely added
        rs = [r for r in reads if len(r) == L]
        out = []
        for i in range(L):
            c = collections.Counter(r[i] for r in rs)
            top = max(c.values())
            out.append(next(r[i] for r in reversed(rs) if c[r[i]] == top))
        return "".join(out)

    def _hold_text(self, text, kind):
        if kind == "callback" and self.has("callback_policy") and self.ctx.mode == "M3":
            self._press("1", 0.4)
            return
        if self.has("queue_reader") and kind in ("est_wait", "position", "unknown"):
            low = text.lower()
            m = nav.digits_in(low)
            est = None
            if m and ("minutes" in low or "मिनट" in low):
                est = int(m[-2:]) * 60
            elif m and ("queue" in low or "कतार" in low):
                est = int(m[-2:]) * 45
            if est is not None and est <= 90 and not self.primed:
                self.primed = True
                self._do(Action("alert", alert="primed"))

    # ------------------------------------------------------------------ the executive (Pine)
    def _dialog(self, text):
        p, t = self.ctx.persona, self.ctx.task
        kind, _ = exec_type(text, 0.92 if self.naive else 0.5)
        low = text.lower()
        if kind == "refuse_ai":
            if self.has("ai_fallback"):
                self._say("Of course. Please hold one moment, connecting them now.", "stall")
                self._do(Action("bridge"))
            else:
                self._do(Action("hangup"))
            return
        if kind.startswith("ask_mobile") and nav.contains_any(low, ["ओटीपी", "otp", "password", "पासवर्ड", "भेजा", " sent "]):
            kind = "otp_sent"   # 'I have SENT an OTP to your registered mobile', with the key word misheard
        if kind == "otp_sent":
            if self.otp_value:
                self._say(" ".join(self.otp_value), "provide", field="otp", value=self.otp_value)
            elif self.has("otp_relay"):
                self.otp_pending = "exec"
                self._do(Action("alert", alert="otp"))
            return
        if kind.startswith("ask_"):
            fld = kind[4:]
            asked = self.field_asks.get(fld, 0)
            self.field_asks[fld] = asked + 1
            # check a distinguishing word survived speech-to-text; after two repeats, answer the best guess
            if not nav.contains_any(low, FIELD_KEYWORDS.get(fld, [""])) and asked < 2:
                self._say("Sorry, could you repeat that?", "ask_repeat")
                return
            v = p.field_value(fld)
            self._say(v if fld == "name" else " ".join(v), "provide", field=fld, value=v)
            return
        if kind == "check_hold":
            self.exec_hold = True
            return
        if kind == "thanks_hold":
            self.exec_hold = False
            return
        if kind == "transfer":
            self._new_executive()
            self.phase, self.decided_human_t, self.probed = "hold", None, set()
            self.hold_start = self.now
            return
        if kind == "offer":
            if not self.has("offers_policy") or p.accept_offers:
                self._say("Okay, sure.", "accept_offer")
            else:
                self._say("No thank you, please go ahead and cancel it.", "decline_offer")
            return
        if kind == "discount":
            d = nav.digits_in(low)
            pct = int(d[:2]) if d else 0
            if self.has("negotiate") and pct < p.target_discount and self.pushes < 3:
                self.pushes += 1
                self._say("That is not enough. Can you do better? Otherwise I will port my number.", "push")
            else:
                self._say("Okay, please apply that.", "confirm")
            return
        if kind in ("no_discount", "best"):
            if self.has("negotiate") and self.pushes < 3:
                self.pushes += 1
                self._say("I have been a loyal customer for years. Please check again.", "push")
            else:
                self._say("Okay.", "confirm")
            return
        digits = nav.digits_in(low)
        if kind == "unknown" and len(digits) < 6 and nav.contains_any(low, ["correct", "सही है"]):
            kind = "correct"
        if kind == "correct":
            self._say("Thank you.", "confirm")
            return
        if kind in ("complaint_ref", "refund_ref", "repeat_ref", "cancelled", "offer_taken", "applied",
                    "wrong_number") or (len(digits) >= 6 and kind == "unknown"):
            if len(digits) >= 6:
                self.ref_reads.append(digits[-8:])
                cons = self._agree(self.ref_reads)
                self.result["captured"] = cons
                if self.has("readback") and len(self.ref_reads) <= 5:
                    # read it back; the executive confirms or corrects (what people do on the phone)
                    self._say(f"Let me read that back: {' '.join(cons)}. Is that correct?", "confirm_number",
                              value=cons)
                else:
                    self._say("Got it, thank you.", "confirm")
            return
        if kind == "anything":
            self._say("No, that's all. Thank you.", "goodbye")
            return
        if kind == "hello":
            self._say("Yes, I can hear you.", "greet_reply")
            return
        if kind in ("greeting", "ai_greet") and (self.reason_given or self.field_asks):
            # a fresh greeting means a new person (a transfer we may not have caught): start over with them
            self._new_executive()
            if kind == "ai_greet" and self.has("ai_exec_detect"):
                self.ai_exec = True
                self._say("Hello, I'm an AI assistant. Can we use a structured agent-to-agent exchange?",
                          "handshake_offer")
                return
            self.disclosed = True
            self._say(f"Hello, I'm an AI assistant calling on behalf of the account holder, {p.name}.", "disclose")
            return
        if kind == "probe_reply" and self.reason_given and self.reason_repeats < 1:
            # 'yes, I can hear you, how can I help?' again: they didn't get our reason, say it once more
            self.reason_repeats += 1
            self._say(t.goal_text + ".", "reason", concepts=t.concepts)
            return
        if kind == "how_help" or (kind in ("probe_reply", "ai_greet") and self.disclosed and not self.reason_given
                                  and self.ai_exec):
            self.reason_given = True
            if t.pine == "negotiate":
                self.pushes += 1
                self._say("My plan is too expensive. I want a discount, or I will port my number.", "push")
            else:
                self._say(t.goal_text + ".", "reason", concepts=t.concepts)
            return
        if kind in ("greeting", "probe_reply") and not self.disclosed:
            self.disclosed = True
            self._say(f"Hello, I'm an AI assistant calling on behalf of the account holder, {p.name}.", "disclose")


    def _new_executive(self):
        """Someone new is on the line: forget the last person's conversation."""
        self.exec_hold = False
        self.disclosed = False
        self.reason_given = False
        self.reason_repeats = 0
        self.ref_reads = []
        self.field_asks = {}
        self.pushes = 0
        self.music_in_exec = 0


def basic_agent() -> HoldForMe:
    """Sierra's 'bare' arm: plain word overlap, exact phrase matching, nothing else."""
    ag = HoldForMe(features={"lang_select"}, label="Basic agent", naive=True)
    ag.name = "C"
    return ag


# =============================================================================================
def ctx_val(p: Persona, f: str) -> str:
    return p.truth["otp"] if f == "otp" else Persona.digits_only(p.field_value(f))


class Scripted(Caller):
    """A key sequence recorded from one dry run of the menu, pressed on a timer."""
    name = "B"
    label = "Scripted bot"

    def __init__(self, timings: list[float] | None = None):
        self.timings = timings

    def reset(self, ctx, env=None):
        super().reset(ctx, env)
        h, t, p = ctx.helpline, ctx.task, ctx.persona
        lang_key = next((k for k, l in h.languages if l == "en"), h.languages[0][0]) if h.language_menu else None
        steps = ([lang_key] if lang_key else []) + list(t.path)
        times = list(self.timings or [])
        self.plan, at = [], 9.0
        for i, s in enumerate(steps):
            at = times[i] + 1.0 if i < len(times) else at + 7.0
            if s.startswith("#"):
                self.plan.append((at, ctx_val(p, s[1:]) + "#", s == "#tpin"))
            elif s.startswith("say:"):
                self.plan.append((at, "", False))
            else:
                self.plan.append((at, s, False))
        self.music, self.bridged = 0, False

    def act(self, obs):
        if self.plan and obs.t >= self.plan[0][0]:
            _, d, secret = self.plan.pop(0)
            if d:
                return Action("dtmf", digits=d, slots={"secret": secret})
        if obs.music > 0.6:
            self.music += 1
        if obs.final:
            k, _ = ivr_type(obs.final)
            if k == "ref":
                self.result["captured"] = nav.digits_in(obs.final)
            elif self.ctx.task.goal_type == "retrieve_fact" and nav.digits_in(obs.final) and k == "unknown" \
                    and not nav.parse_options(obs.final) and not self.plan:
                self.result["fact"] = nav.digits_in(obs.final)
        if self.music and obs.partial and not self.bridged and not self.plan:
            self.bridged = True
            return Action("bridge")
        return WAIT


class _TruthCaller(Caller):
    """Shared by Oracle and Human: they read the true prompt text, not speech-to-text."""

    def _prompt_ready(self):
        env = self.env
        if not env.segs:
            return None
        last = env.segs[-1]
        if last.speaker == "listen" and len(env.segs) > 1:
            return env.segs[-2]
        if self.ctx.helpline.barge_in and last.label == pc.PROMPT:
            return last
        return None

    def _key(self, digits):
        if self.ctx.mode == "M2" and not self.env.m2_relay_ok:
            return Action("alert", alert="press_key", digits=digits)
        return Action("dtmf", digits=digits)

    def _step_action(self, seg, step):
        h = self.ctx.helpline
        node = None
        for nid in reversed(self.env.visited):
            node = h.nodes[nid]
            break
        if step.startswith("#"):
            return self._key(ctx_val(self.ctx.persona, step[1:]) + "#")
        if node is not None and node.type == "menu" and node.modality in ("speech", "broken_speech"):
            opt = next((o for o in node.options if o.key == step), None)
            if opt is not None:
                lang = self.env.lang if self.env.lang in ("en", "hi") else "en"
                return Action("say", text=opt.label.get(lang, opt.label["en"]), intent="menu_choice")
        return self._key(step)


def find_path(h: Helpline, target: str) -> list[str]:
    """Shortest key sequence from the root to the target in the CURRENT tree (BFS)."""
    from collections import deque
    q = deque([(h.root, [])])
    seen = {h.root}
    while q:
        nid, path = q.popleft()
        if nid == target:
            return path
        n = h.nodes[nid]
        nxt = []
        if n.type == "menu":
            nxt = [(o.goto, o.key) for o in n.options]
            nxt += [(n.agent_target, k) for k, kind in n.extras.items() if kind == "agent" and n.agent_target]
        elif n.type == "collect":
            nxt = [(n.next, "#" + n.field)]
        elif n.type == "message" and n.next:
            nxt = [(n.next, None)]
        for g, k in nxt:
            if g in h.nodes and g not in seen:
                seen.add(g)
                q.append((g, path + ([k] if k else [])))
    return []


class Oracle(_TruthCaller):
    name = "O"
    label = "Oracle"

    def reset(self, ctx, env=None):
        super().reset(ctx, env)
        h, t = ctx.helpline, ctx.task
        lang_key = next((k for k, l in h.languages if l == ctx.persona.lang_pref), None) or \
            next((k for k, l in h.languages if l == "en"), h.languages[0][0])
        self.steps = ([lang_key] if h.language_menu else []) + (find_path(h, t.target) or list(t.path))
        self.last_seg = None
        self.bridged = False

    def act(self, obs):
        env = self.env
        if env.refs:
            self.result["captured"] = next(iter(env.refs.values()))
        if env.facts:
            self.result["fact"] = next(iter(env.facts.values()))
        if env.pickup_t is not None and not self.bridged and env.truth_label in (pc.HUMAN, pc.HUMAN_WAIT, pc.AI_AGENT):
            self.bridged = True
            return Action("bridge", slots={"instant": True})
        seg = self._prompt_ready()
        if seg is None or seg is self.last_seg:
            return WAIT
        low = seg.text.lower()
        kind, _ = ivr_type(seg.text)
        if kind == "confirm":
            self.last_seg = seg
            return self._key("1")
        if kind == "after_fact":
            self.last_seg = seg
            return Action("hangup")
        if self.steps and (kind.startswith("field:") or nav.parse_options(seg.text) or "दबाएँ" in low
                           or "press" in low or "say" in low or "बोलें" in low):
            if kind in ("invalid", "noinput", "invalid_entry", "connecting", "ref"):
                return WAIT
            self.last_seg = seg
            return self._step_action(seg, self.steps.pop(0))
        return WAIT


class Human(_TruthCaller):
    """A person: hears perfectly, sometimes picks the wrong option, gives up like real callers."""
    name = "A"
    label = "Human caller"

    def __init__(self, patience_sampler):
        self.patience_sampler = patience_sampler

    def reset(self, ctx, env=None):
        super().reset(ctx, env)
        self.rng = random.Random(hash((ctx.task.id, ctx.persona.name, ctx.persona.dob)) & 0xffffffff)
        h, t = ctx.helpline, ctx.task
        lang_key = next((k for k, l in h.languages if l == ctx.persona.lang_pref), None) or \
            next((k for k, l in h.languages if l == "en"), h.languages[0][0])
        self.steps = ([lang_key] if h.language_menu else []) + (find_path(h, t.target) or list(t.path))
        self.last_seg = None
        self.pending = None
        self.patience = self.patience_sampler(self.rng)
        self.hold_start = None
        self.bridged = False
        self.result["abandoned"] = False

    def wants_redial(self, end_reason):
        from .provenance import P
        return end_reason in ("busy_disconnect", "call_dropped") or \
            (end_reason == "agent_hangup" and self.result.get("abandoned") and self.rng.random() < P("human.redial_p"))

    def act(self, obs):
        from .provenance import P
        env = self.env
        if self.pending and obs.t >= self.pending[0]:
            a, self.pending = self.pending[1], None
            return a
        if env.refs:
            self.result["captured"] = next(iter(env.refs.values()))
        if env.facts:
            self.result["fact"] = next(iter(env.facts.values()))
        if env.truth_label in (pc.MUSIC, pc.ANNOUNCE, pc.AGENT_LIKE) and self.hold_start is None:
            self.hold_start = obs.t
        if self.hold_start is not None and env.pickup_t is None and obs.t - self.hold_start > self.patience:
            self.result["abandoned"] = True
            return Action("hangup")
        if env.pickup_t is not None and not self.bridged and env.truth_label in (pc.HUMAN, pc.HUMAN_WAIT, pc.AI_AGENT):
            self.bridged = True
            return Action("bridge", slots={"instant": True})
        seg = self._prompt_ready()
        if seg is None or seg is self.last_seg or self.pending is not None:
            return WAIT
        if env.segs[-1].speaker != "listen":
            return WAIT  # people let the prompt finish
        kind, _ = ivr_type(seg.text)
        react = 1.0 + self.rng.random() * 1.5
        if kind == "confirm":
            self.last_seg = seg
            self.pending = (obs.t + react, self._key("1"))
        elif kind == "after_fact":
            self.last_seg = seg
            self.pending = (obs.t + react, Action("hangup"))
        elif self.steps and kind not in ("invalid", "noinput", "invalid_entry", "connecting", "ref"):
            self.last_seg = seg
            step = self.steps.pop(0)
            if not step.startswith("#") and self.steps and self.rng.random() > P("human.nav_correct_p"):
                node = self.ctx.helpline.nodes[env.visited[-1]] if env.visited else None
                if node is not None and node.options:
                    step = self.rng.choice(node.options).key
            a = self._step_action(seg, step)
            self.pending = (obs.t + react + (2.0 if step.startswith("#") else 0.0), a)
        return WAIT
