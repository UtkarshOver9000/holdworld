"""Every experiment, writing results/raw.json and the data the dashboard replays.

    python -m holdworld run [--quick]
"""
from __future__ import annotations

import json
import math
import random
import statistics
import time
from dataclasses import asdict
from pathlib import Path

from . import anonbank as ab
from . import callqueue as cq
from . import perception as pc
from .agents import ALL_FEATURES, FEATURE_GROUP, FEATURE_TEXT, HoldForMe, Human, Oracle, Scripted, basic_agent
from .episode import record_script, run_task, trace_of
from .helplines import all_helplines
from .people import User
from .platforms import PLATFORMS
from .provenance import P, Param, export, register
from .scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
SITE = ROOT / "site"
ARM_LABEL = {"A": "Human caller", "B": "Scripted bot", "C": "Basic agent", "D": "HoldForMe", "O": "Oracle"}
ARM_PLATFORM = {"A": "plivo_hybrid", "B": "plivo_hybrid", "C": "bolna_naive", "D": "plivo_hybrid",
                "O": "plivo_hybrid"}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(p, 4), round(max(0, c - h), 4), round(min(1, c + h), 4))


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class World:
    """Everything fitted once: the real year, queue profiles, wait tables."""

    def __init__(self, quick=False):
        self.quick = quick
        self.calls = ab.load()
        self.model = ab.fit_model(self.calls)
        self.helplines = all_helplines()
        self.profiles, self.waits = {}, {}
        for hid, h in self.helplines.items():
            q = h.queue
            make = lambda beta, q=q, hid=hid: cq.build_profile(
                hid, self.model, q["volume_scale"], beta, tuple(q["open"]), q.get("service_scale", 1.0), q["tag"],
                q.get("note", ""))
            beta = q["beta"]
            if q.get("calibrate"):
                beta = cq.calibrate_beta(make, q["calibrate"]["target"], q["calibrate"]["limit_s"])
                register(Param(f"queue.{hid}.beta", round(beta, 3), "OFFICIAL", "trai_qos",
                               note=f"solved so {q['calibrate']['target']:.0%} answered within "
                                    f"{q['calibrate']['limit_s']} s"))
            self.profiles[hid] = make(beta)
            self.waits[hid] = cq.wait_table(self.profiles[hid], days=4 if quick else 10)

    def wait_for(self, hid, hour, rng):
        w = self.waits[hid].sample(hour, rng)
        return 20.0 if w is None else max(5.0, w)

    def service_for(self, hid, rng):
        return self.model.sample_service(rng) * self.helplines[hid].queue.get("service_scale", 1.0)

    def hour_for(self, hid, rng):
        prof = self.profiles[hid]
        hours = [h for h in range(24) if prof.agents[h] > 0]
        weights = [prof.arrivals[h] for h in hours]
        return rng.choices(hours, weights=weights)[0]


def make_caller(arm, world, h, task, features=None):
    if arm == "A":
        return Human(lambda rng: world.model.sample_patience(rng))
    if arm == "B":
        return Scripted(record_script(h, task))
    if arm == "C":
        return basic_agent()
    if arm == "O":
        return Oracle()
    return HoldForMe(features)


def mode_for(h):
    return "M2" if h.caller_id_auth else "M1"


# ---------------------------------------------------------------------------------------------
def exp_real_data(world):
    log("real data: summary, patience curve, hold-out replay check")
    s = ab.summarize(world.calls)
    register(Param("data.anonbank.records", s["records"], "DATA", "anonbank"))
    register(Param("data.anonbank.abandon_frac", round(s["abandon_frac"], 4), "DATA", "anonbank"))
    register(Param("data.anonbank.mean_wait_s", round(s["mean_wait_served_s"], 1), "DATA", "anonbank", "s"))
    register(Param("data.anonbank.service_median_s", s["service"]["median_s"], "DATA", "anonbank", "s"))
    register(Param("data.anonbank.patience_spikes_s", s["patience"]["spikes_s"][:3], "DATA", "anonbank", "s",
                   "hang-up hazard spikes: first message and the ~60 s replay"))
    dates = sorted({c.date for c in world.calls if c.weekday in ab.WORKDAYS})
    counts = {}
    for c in world.calls:
        if c.wanted_agent:
            counts[c.date] = counts.get(c.date, 0) + 1
    good = [d for d in dates if counts.get(d, 0) > 800]
    rng = random.Random(42)
    train = rng.sample([d for d in good if int(d[2:4]) <= 6], 6 if world.quick else 10)
    test = rng.sample([d for d in good if int(d[2:4]) >= 7], 6 if world.quick else 12)
    W = cq.fit_wrapup({d: ab.day(world.calls, d) for d in train}, world.model, iters=6 if world.quick else 8)
    register(Param("queue.wrapup_s", round(W, 1), "DATA", "anonbank", "s",
                   "after-call work fitted on Jan-Jun days, tested on held-out Jul-Dec days"))
    hold = cq.holdout_check({d: ab.day(world.calls, d) for d in test}, world.model, W)
    return {"summary": s, "wrapup_s": W, "train_days": train, "holdout": hold}


def exp_real_day(world, wrapup):
    """A real day for the queue animation, plus the same day with AI holders."""
    d = ab.busiest_workdays(world.calls, 11, 1)[0]
    dc = [c for c in ab.day(world.calls, d) if c.type != "IN"]   # the regular-service queue
    staff = ab.staffing_by_interval(dc, 900)
    events = []
    for c in dc:
        events.append({"a": c.arrival, "q": c.q_time if c.queued else 0, "o": c.outcome,
                       "s": c.ser_time, "srv": c.server, "t": c.type, "p": c.priority})
    sims = {}
    for alpha in (0.0, 0.25, 0.5):
        rng = random.Random(11)
        callers, _ = cq.replay(dc, world.model, rng, wrapup=wrapup)
        hum = [c for c in callers if c.kind == "human"]
        ai_ids = set(rng.sample([c.cid for c in hum], int(alpha * len(hum))))
        for c in callers:
            c.start = c.abandoned_at = c.desk = None
            if c.cid in ai_ids:
                c.patience, c.kind = cq.INF, "ai"
        cq.run(callers, lambda t, s=staff: s.get(int(t // 900) * 900, 0) or 1, [float(x) for x in sorted(staff)])
        hum = [c for c in callers if c.kind == "human"]
        ai = [c for c in callers if c.kind == "ai"]
        sims[str(alpha)] = {
            "human_wait": round(statistics.fmean(c.wait for c in hum if c.wait is not None), 1),
            "human_abandon": round(sum(c.abandoned_at is not None for c in hum) / max(len(hum), 1), 4),
            "ai_wait": round(statistics.fmean(c.wait for c in ai if c.wait is not None), 1) if ai else None,
            "callers": [{"a": round(c.arrival), "w": round(c.wait) if c.wait is not None else None,
                         "srv": c.served, "k": c.kind, "d": c.desk, "s": round(c.service)} for c in callers],
        }
    return {"date": d, "events": events, "staffing": {str(k): v for k, v in sorted(staff.items())}, "sims": sims}


def exp_waits(world):
    log("wait by hour per helpline (Google's 'wait times')")
    out = {}
    for hid, wt in world.waits.items():
        prof = world.profiles[hid]
        out[hid] = {"stats": wt.stats(), "agents": prof.agents, "arrivals": [round(a, 1) for a in prof.arrivals],
                    "tag": prof.tag, "note": prof.note}
        if hid == "telecom":
            out[hid]["answered_90s"] = round(cq.answered_within(prof, 90), 4)
    return out


def exp_arms(world, seeds):
    log(f"arms: A B C D O across every task, {seeds} seeds")
    rows, traces = [], {}
    for hid, h in world.helplines.items():
        for task in h.tasks:
            for seed in range(seeds):
                rng = random.Random(seed * 1009 + hash(task.id) % 1000)
                hour = world.hour_for(hid, rng)
                wait = world.wait_for(hid, hour, rng)
                svc = world.service_for(hid, rng)
                for arm in ("A", "B", "C", "D", "O"):
                    caller = make_caller(arm, world, h, task)
                    cr, env = run_task(h, task, caller, mode=mode_for(h), platform=ARM_PLATFORM[arm], hour=hour,
                                       seed=seed, wait_s=wait, service_s=svc, keep_env=True)
                    rows.append(asdict(cr))
                    if seed == 0 and arm in ("D", "C", "B", "A"):
                        traces[cr.trace_id] = trace_of(env, caller, cr)
    return rows, traces


def summarize_rows(rows, key="arm"):
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    out = {}
    for k, rs in groups.items():
        n = len(rs)
        succ = sum(r["success"] for r in rs)
        out[k] = {
            "n": n, "success": wilson(succ, n),
            "user_minutes_median": median([r["user_minutes"] for r in rs]),
            "user_minutes_mean": round(statistics.fmean(r["user_minutes"] for r in rs), 2),
            "time_to_human_median": median([r["time_to_human"] for r in rs]),
            "detect_latency_median": median([r["detect_latency"] for r in rs]),
            "false_alerts_per_call": round(statistics.fmean(r["false_alerts"] for r in rs), 3),
            "missed_pickups": sum(r["missed_pickup"] for r in rs),
            "cost_inr_median": median([r["cost_inr"] for r in rs]),
            "secrets_by_agent": sum(r["secrets_by_agent"] for r in rs),
            "end_reasons": _count(r["end_reason"] for r in rs),
        }
    return out


def _count(xs):
    c = {}
    for x in xs:
        c[x] = c.get(x, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def exp_stress(world, n, arms=("B", "C", "D", "O"), features=None, label="D"):
    rows, traces = [], {}
    for sc in SCENARIOS:
        h = sc.helpline_for(world.helplines)
        task = h.task(sc.task)
        for arm in arms:
            for seed in range(n):
                rng = random.Random(seed * 31 + int(sc.id[1:]))
                hour = world.hour_for(sc.helpline, rng)
                hour = max(hour, h.hours[0]) if h.hours[1] - h.hours[0] < 24 else hour
                wait = min(world.wait_for(sc.helpline, hour, rng), 400.0)
                svc = world.service_for(sc.helpline, rng)
                caller = make_caller(arm, world, world.helplines[sc.helpline] if arm == "B" else h, task, features)
                pf = sc.platform.get(arm if arm != "D" or features is None else "D", ARM_PLATFORM[arm])
                if arm == "D" and "D" not in sc.platform:
                    pf = "plivo_hybrid"
                dial = sc.dial
                if dial and arm == "D" and (features is None or "shortcode_map" in features) and h.shortcode:
                    dial = h.shortcode["long"]
                cr, env = run_task(h, task, caller, mode=sc.mode, platform=pf, hour=hour, seed=seed, wait_s=wait,
                                   service_s=svc, scn=dict(sc.scn), scenario=sc.id, dial=dial, keep_env=True)
                d = asdict(cr)
                d["pass"] = bool(sc.passes(cr))
                d["arm"] = label if arm == "D" else arm
                rows.append(d)
                if seed == 0 and features is None:
                    traces[cr.trace_id] = trace_of(env, caller, cr)
    return rows, traces


def stress_table(rows):
    t = {}
    for r in rows:
        cell = t.setdefault(r["scenario"], {}).setdefault(r["arm"], [0, 0])
        cell[0] += r["pass"]
        cell[1] += 1
    return {s: {a: wilson(k, n) for a, (k, n) in arms.items()} for s, arms in t.items()}


def exp_ablation(world, n):
    log(f"ablation: HoldForMe minus one component at a time, {n} runs per scenario")
    full_rows, _ = exp_stress(world, n, arms=("D",))
    full = stress_table(full_rows)
    out = {"full": {s: v["D"][0] for s, v in full.items()}, "minus": {}}
    for f in ALL_FEATURES:
        feats = [x for x in ALL_FEATURES if x != f]
        rows, _ = exp_stress(world, n, arms=("D",), features=feats, label=f"-{f}")
        tab = stress_table(rows)
        out["minus"][f] = {s: v[f"-{f}"][0] for s, v in tab.items()}
    return out


def exp_modes(world, seeds):
    log("handoff modes M1 / M2 / M3 on the bank complaint line")
    h = world.helplines["airline"]
    task = h.task("air_change")
    rows = []
    for mode in ("M1", "M2", "M3"):
        for stall in (True, False):
            feats = None if stall else [f for f in ALL_FEATURES if f != "stall"]
            for seed in range(seeds):
                rng = random.Random(seed + 500)
                hour = world.hour_for("airline", rng)
                cr = run_task(h, task, HoldForMe(feats), mode=mode, platform="plivo_hybrid", hour=hour, seed=seed,
                              wait_s=world.wait_for("airline", hour, rng), service_s=world.service_for("airline", rng))
                d = asdict(cr)
                d["stall"] = stall
                rows.append(d)
    table = {}
    for r in rows:
        k = f"{r['mode']}|{'stall' if r['stall'] else 'no stall'}"
        table.setdefault(k, []).append(r["success"])
    return {"table": {k: wilson(sum(v), len(v)) for k, v in table.items()}, "rows": rows}


def exp_handoff_grid():
    """Success of the handoff by executive patience x user answer time (pure model, 20k draws)."""
    rng = random.Random(3)
    patience = [4, 6, 8, 10, 12, 15, 20, 25, 30]
    out = {}
    for mode in ("M1", "M2"):
        for stall in (False, True):
            row = []
            for p in patience:
                ok = 0
                N = 4000
                for _ in range(N):
                    u = User(rng, mode).answer_delay()
                    if u is None:
                        continue
                    budget = p + (2 * P("exec.stall_extension_s") * P("exec.max_stalls") if stall else 0)
                    ok += u <= budget
                row.append(round(ok / N, 4))
            out[f"{mode}|{'stall' if stall else 'no stall'}"] = row
    return {"patience": patience, "success": out}


def exp_platforms(world, seeds):
    log("platforms and cost per call")
    rows = []
    for pf in PLATFORMS:
        for hid in ("psu_bank", "airline", "electricity", "telecom"):
            h = world.helplines[hid]
            for task in h.tasks[:2]:
                for seed in range(seeds):
                    rng = random.Random(seed + 77)
                    hour = world.hour_for(hid, rng)
                    cr = run_task(h, task, HoldForMe(), mode=mode_for(h), platform=pf, hour=hour, seed=seed,
                                  wait_s=world.wait_for(hid, hour, rng), service_s=world.service_for(hid, rng))
                    rows.append(asdict(cr))
    return {"by_platform": summarize_rows(rows, "platform"),
            "platforms": {k: {"label": v.label, "note": v.note, "dtmf": v.can_send_dtmf, "cap_s": v.call_cap_s,
                              "silence_hangup_s": v.silence_hangup_s, "hybrid": v.hybrid} for k, v in PLATFORMS.items()}}


def exp_city(world):
    log("city: what happens when callers stop hanging up")
    out = {}
    for hid in ("psu_bank", "airline"):
        prof = world.profiles[hid]
        out[hid] = {
            "none": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3),
            "deadline_20min": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_patience=1200.0),
            "handshake": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_service_factor=0.8),
        }
    return out


def exp_path_memory(world, seeds):
    """Second call to the same line: path memory skips re-listening."""
    h = world.helplines["psu_bank"]
    task = h.task("psu_complaint")
    first, second = [], []
    for seed in range(seeds):
        mem = {}
        for i in range(2):
            cr = run_task(h, task, HoldForMe(), mode="M1", platform="plivo_hybrid", hour=11, seed=seed * 10 + i,
                          wait_s=60, service_s=120, memory=mem, scn={"busy_disconnect_p": 0.0})
            (first if i == 0 else second).append(cr.t_ivr)
    return {"first_call_ivr_s": median(first), "second_call_ivr_s": median(second), "n": seeds}


def run_all(quick=False):
    t0 = time.time()
    RESULTS.mkdir(exist_ok=True)
    seeds = 3 if quick else 8
    world = World(quick)
    real = exp_real_data(world)
    day = exp_real_day(world, real["wrapup_s"])
    waits = exp_waits(world)
    arm_rows, traces = exp_arms(world, seeds)
    stress_rows, stress_traces = exp_stress(world, 3 if quick else 10)
    traces.update(stress_traces)
    ablation = exp_ablation(world, 2 if quick else 5)
    modes = exp_modes(world, 4 if quick else 12)
    grid = exp_handoff_grid()
    platforms = exp_platforms(world, 2 if quick else 4)
    city = exp_city(world)
    memory = exp_path_memory(world, 3 if quick else 8)
    raw = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "quick": quick,
        "real": real, "real_day": day, "waits": waits,
        "arms": {"summary": summarize_rows(arm_rows), "by_goal": {g: summarize_rows([r for r in arm_rows if r["goal_type"] == g])
                                                                   for g in ("reach_human", "retrieve_fact", "execute_action")},
                 "by_helpline": {hid: summarize_rows([r for r in arm_rows if r["helpline"] == hid]) for hid in world.helplines},
                 "rows": arm_rows},
        "stress": {"table": stress_table(stress_rows), "rows": stress_rows,
                   "scenarios": [{"id": s.id, "title": s.title, "breaks": s.breaks, "helpline": s.helpline,
                                  "task": s.task, "mode": s.mode, "source": s.source} for s in SCENARIOS]},
        "ablation": ablation, "modes": modes, "handoff_grid": grid, "platforms": platforms, "city": city,
        "path_memory": memory,
        "features": [{"key": f, "group": FEATURE_GROUP[f], "text": FEATURE_TEXT[f]} for f in ALL_FEATURES],
        "provenance": export(),
        "runtime_s": round(time.time() - t0, 1),
    }
    (RESULTS / "raw.json").write_text(json.dumps(raw, default=str), encoding="utf-8")
    log(f"done in {raw['runtime_s']} s")
    return raw, traces, world
