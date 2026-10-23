"""Run one task end to end (with re-dials) and score it against the truth."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from . import perception as pc
from .agents import Caller, Context, HoldForMe
from .line import CallEnv
from .people import make_persona
from .platforms import PLATFORMS
from .spec import Helpline, Task

MAX_STEPS = 4 * 3600 * 2  # 4 hours of half-second frames


@dataclass
class CallResult:
    arm: str
    helpline: str
    task: str
    goal_type: str
    pine: str
    mode: str
    platform: str
    hour: int
    seed: int
    scenario: str
    success: bool
    end_reason: str
    attempts: int
    t_total: float
    t_ivr: float
    t_hold: float
    time_to_human: float | None
    detect_latency: float | None
    false_alerts: int
    missed_pickup: bool
    handed_off: bool
    dept_ok: bool | None
    user_minutes: float
    phone_busy_minutes: float
    secrets_by_agent: int
    platform_utterances: int
    dtmf_unavailable: int
    cost_inr: float
    captured_ok: bool | None
    discount: int | None
    accepted_offer: bool | None
    probes: int
    transfers: int
    gave_up: str | None
    trace_id: str | None = None


def run_task(hl: Helpline, task: Task, caller: Caller, *, mode: str, platform: str, hour: int, seed: int,
             wait_s: float, service_s: float, scn: dict | None = None, scenario: str = "base",
             autonomous: bool | None = None, dial: str | None = None, memory: dict | None = None,
             keep_env: bool = False, max_attempts: int = 3):
    rng = random.Random(seed)
    persona = make_persona(random.Random(seed * 7 + 1))
    if scn and "lang_pref" in scn:
        persona.lang_pref = scn["lang_pref"]
    auto = bool(task.pine) if autonomous is None else autonomous
    ctx = Context(hl, task, persona, mode, auto, memory if memory is not None else {})
    pf = PLATFORMS[platform]
    total = ivr = hold = 0.0
    t_human = latency = None
    false_alerts = 0
    attempts = 0
    env = None
    for attempts in range(1, max_attempts + 1):
        env = CallEnv(hl, task, persona, mode=mode, platform=pf, wait_s=wait_s, hour=hour,
                      rng=random.Random(rng.random()), scn=scn, dial=dial)
        caller.reset(ctx, env)
        obs = env.step(None)
        steps = 0
        while not env.done and steps < MAX_STEPS:
            obs = env.step(caller.act(obs))
            steps += 1
        caller.act(obs)  # the last frame can carry results (a handshake reference, a final readout)
        for t, lab in env.alerts:
            if lab not in pc.LIVE_LABELS and lab != pc.AI_AGENT:
                false_alerts += 1
        ivr += env.t_queue_enter if env.t_queue_enter is not None else env.t
        hold += env.hold_s
        if env.pickup_t is not None and t_human is None:
            t_human = total + env.pickup_t
            d = caller.result.get("decided_human_t") if isinstance(caller, HoldForMe) else None
            if d is not None and d >= env.pickup_t:
                latency = d - env.pickup_t
        total += env.t
        if env.end_reason in ("handed_off", "completed", "ivr_completed", "callback_scheduled"):
            break
        if not caller.wants_redial(env.end_reason):
            break
        total += 30.0  # back-off before dialling again
        if scn and "drop_at" in scn:      # a one-off network drop, not a property of the line
            scn = {k: v for k, v in scn.items() if k != "drop_at"}
    res = caller.result
    t = task
    eo = env.exec_outcome
    handed = env.handed_off
    dept_ok = eo.get("dept_ok")
    captured_ok = None
    discount = eo.get("discount")
    accepted = eo.get("accepted_offer")
    # --- success, by goal type
    if t.goal_type == "reach_human" and not t.pine:
        success = handed and bool(dept_ok)
    elif t.pine and auto and not handed:
        if t.pine in ("complaint", "refund_status"):
            captured_ok = res.get("captured") is not None and res.get("captured") == eo.get("ref")
            success = bool(eo.get("completed")) and captured_ok
        elif t.pine == "cancel":
            captured_ok = res.get("captured") == eo.get("ref")
            success = bool(eo.get("completed")) and accepted is False
        else:
            success = bool(eo.get("completed")) and (discount or 0) >= persona.target_discount
        if eo.get("handshake"):
            captured_ok = res.get("captured") == eo.get("ref")
            success = captured_ok
    elif t.pine:
        success = handed and bool(dept_ok)
    elif t.goal_type == "retrieve_fact":
        truth = env.facts.get(hl.node(t.target).fact)
        # facts like "delivered on 12 November" are checked on their digits
        captured_ok = None if truth is None else res.get("fact") is not None and             "".join(ch for ch in str(res.get("fact")) if ch.isdigit()) == "".join(ch for ch in truth if ch.isdigit())
        success = captured_ok
    else:
        truth = env.refs.get(hl.node(t.target).action)
        captured_ok = None if truth is None else res.get("captured") == truth
        success = captured_ok
    if env.end_reason == "callback_scheduled":
        # the bank calls back the registered number; the user answers it themselves
        success = rng.random() > 0.1 and (t.goal_type == "reach_human")
    missed = env.pickup_t is not None and not handed and env.end_reason == "exec_hung_up"
    # --- the user's own time
    if caller.name in ("A",):
        user_min = (total + (service_s if handed else 0)) / 60
        busy_min = user_min
    else:
        user_min = 0.0
        busy_min = (total / 60) if mode == "M2" else 0.0
        if env.user_join_t is not None:
            user_min += service_s / 60
            if not (env.bridge_truth in pc.LIVE_LABELS or env.bridge_truth == pc.AI_AGENT):
                user_min += max(0.0, (env.wait_s - (env.bridge_t - (env.t_queue_enter or 0)))) / 60
            if dept_ok is False:
                user_min += env.wait_s * 0.3 / 60
        user_min += 0.25 * false_alerts + 0.4 * sum(1 for x in env.transcript if x.get("label") == "alert")
    talk = total - hold
    cost = pf.cost_inr(total, talk, hold) if caller.name not in ("A",) else 0.0
    trace_id = f"{caller.name}-{hl.id}-{t.id}-{mode}-{seed}-{scenario}"
    cr = CallResult(
        arm=caller.name, helpline=hl.id, task=t.id, goal_type=t.goal_type, pine=t.pine, mode=mode, platform=platform,
        hour=hour, seed=seed, scenario=scenario, success=bool(success), end_reason=env.end_reason, attempts=attempts,
        t_total=round(total, 1), t_ivr=round(ivr, 1), t_hold=round(hold, 1),
        time_to_human=round(t_human, 1) if t_human is not None else None,
        detect_latency=round(latency, 2) if latency is not None else None, false_alerts=false_alerts,
        missed_pickup=missed, handed_off=handed, dept_ok=dept_ok, user_minutes=round(user_min, 2),
        phone_busy_minutes=round(busy_min, 2), secrets_by_agent=env.secrets_by_agent,
        platform_utterances=env.platform_utterances, dtmf_unavailable=env.dtmf_unavailable, cost_inr=round(cost, 2),
        captured_ok=captured_ok, discount=discount, accepted_offer=accepted,
        probes=res.get("probes", 0) if isinstance(res, dict) else 0, transfers=env.transfers,
        gave_up=res.get("gave_up") if isinstance(res, dict) else None, trace_id=trace_id,
    )
    return (cr, env) if keep_env else cr


_SCRIPTS: dict = {}


def record_script(hl: Helpline, task: Task) -> list[float]:
    """Key-press times from one dry run of the menu, the way a script writer would record them."""
    key = (hl.id, task.id)
    if key not in _SCRIPTS:
        from .agents import Oracle
        o = Oracle()
        cr, env = run_task(hl, task, o, mode="M1", platform="plivo_hybrid", hour=12, seed=99, wait_s=30,
                           service_s=60, scn={"lang_pref": "en", "busy_disconnect_p": 0.0, "network_busy_p": 0.0,
                                               "drop_per_min": 0.0}, keep_env=True)
        _SCRIPTS[key] = [x["t"] for x in env.transcript if x.get("label") == "dtmf"]
    return _SCRIPTS[key]


def trace_of(env: CallEnv, caller: Caller, cr: CallResult) -> dict:
    """Everything the animations replay for one call."""
    segs = [{"s": round(s.start, 2), "e": round(min(s.end, env.t), 2), "l": s.label, "x": s.text, "sp": s.speaker}
            for s in env.segs if s.start < env.t and s.end > s.start]
    frames = env.frames
    belief = getattr(caller, "trace_belief", [])
    return {
        "id": cr.trace_id, "result": asdict(cr), "segments": segs,
        "frames": {"t": [f[0] for f in frames], "label": [f[1] for f in frames], "speech": [f[2] for f in frames],
                   "music": [f[3] for f in frames], "synth": [f[4] for f in frames], "room": [f[5] for f in frames],
                   "agent_speaking": [1 if f[6] else 0 for f in frames]},
        "belief": belief, "transcript": env.transcript, "visited": env.visited, "visited_t": env.visited_t,
        "q_enter": env.t_queue_enter, "duration": round(env.t, 1), "helpline": env.hl.id, "task": env.task.id,
        "goal": env.task.goal_text, "pickup_t": env.pickup_t,
        "bridge_t": env.bridge_t, "user_join_t": env.user_join_t, "exec_patience": round(env.exec_patience, 1),
        "menu_text": caller.result.get("menu_text", []) if isinstance(caller.result, dict) else [],
        "lang": env.lang, "why": caller.result.get("why") if isinstance(caller.result, dict) else None,
    }
