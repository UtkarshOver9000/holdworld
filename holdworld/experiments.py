"""Every experiment, writing results/raw.json and the data the dashboard replays.

    python -m holdworld run [--quick]
"""
from __future__ import annotations

import json
import math
import random
import statistics
import time
import zlib
from dataclasses import asdict, replace
from pathlib import Path

from . import anonbank as ab
from . import atlas as atlas_data
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
        atlas_path = ROOT / "data" / "atlas" / "measurements.csv"
        atlas_rows = atlas_data.load(atlas_path) if atlas_path.exists() else []
        self.atlas_summary = atlas_data.summarize(atlas_rows)
        if atlas_rows:
            atlas_data.apply(self.atlas_summary)
        self.atlas_waits = {hid: [float(r["queue_seconds"]) for r in atlas_rows
                                  if r.get("helpline") == hid and atlas_data._num(r.get("queue_seconds")) is not None]
                            for hid in self.helplines}
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
        observed = self.atlas_waits.get(hid, [])
        if len(observed) >= 3:
            return max(0.0, rng.choice(observed))
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
                rng = random.Random(seed * 1009 + zlib.crc32(task.id.encode("utf-8")) % 1000)
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


def exp_noise_sweep(world, n=30):
    """Hold the task, seed, and poor phone channel fixed while sweeping ASR WER."""
    log(f"noise sweep: 10-50% word error rate, all five callers, {n} seeds per cell")
    h = world.helplines["psu_bank"]
    task = h.task("psu_complaint")
    targets = [round(x / 100, 2) for x in range(10, 51, 10)]
    out = []
    base = P("asr.wer.recorded") + 0.14  # recorded Hindi prompts on the poor SNR channel
    for arm in ("A", "B", "C", "D", "O"):
        for target in targets:
            rows = []
            for seed in range(n):
                rng = random.Random(81000 + seed)
                hour = 11
                wait = world.wait_for("psu_bank", hour, rng)
                service = world.service_for("psu_bank", rng)
                caller = make_caller(arm, world, h, task)
                cr = run_task(h, task, caller, mode="M1", platform=ARM_PLATFORM[arm], hour=hour, seed=seed,
                              wait_s=wait, service_s=service,
                              scn={"snr": "poor", "lang_pref": "hi", "wer_mult": target / base})
                rows.append(cr)
            out.append({"arm": arm, "wer": target, "n": len(rows),
                        "success": wilson(sum(r.success for r in rows), len(rows)),
                        "false_alerts_per_call": round(statistics.fmean(r.false_alerts for r in rows), 3),
                        "mean_user_minutes": round(statistics.fmean(r.user_minutes for r in rows), 2)})
    return out


def exp_sensitivity(world, n=30):
    """One-factor success sensitivity. Each factor uses its own representative task."""
    log(f"assumption sensitivity: five factors, three levels, {n} seeds per point")
    cases = [
        ("Executive silence tolerance", "psu_bank", "psu_complaint", "M1", "exec_patience",
         [(4.0, 6.0), (10.0, 14.0), (24.0, 30.0)], {}),
        ("Speech error rate", "psu_bank", "psu_balance", "M1", "wer", [0.10, 0.35, 0.50], {"snr": "poor"}),
        ("Executive AI refusal", "psu_bank", "psu_complaint", "M1", "refuse_ai_p", [0.0, 0.15, 0.40], {}),
        ("OTP delivery delay", "telecom", "tel_cancel", "M2", "otp_delay_mult", [0.5, 1.0, 2.0], {}),
        ("M2 keypad relay reliability", "telecom", "tel_network", "M2", "m2_dtmf_relay_p", [0.0, 0.5, 1.0], {}),
    ]
    out = []
    for factor, hid, task_id, mode, key, levels, base_scn in cases:
        h = world.helplines[hid]
        task = h.task(task_id)
        group = []
        for value in levels:
            scn = dict(base_scn)
            if key == "wer":
                scn["wer_mult"] = value / (P("asr.wer.recorded") + 0.14)
                shown = round(value * 100)
            else:
                scn[key] = value
                if key == "exec_patience":
                    shown = f"{value[0]:g}-{value[1]:g} s"
                elif key == "otp_delay_mult":
                    shown = f"{value:g}x"
                else:
                    shown = f"{value * 100:.0f}%"
            rows = []
            for seed in range(n):
                rng = random.Random(41000 + seed)
                hour = 11
                cr = run_task(h, task, make_caller("D", world, h, task), mode=mode, platform="plivo_hybrid",
                              hour=hour, seed=seed, wait_s=world.wait_for(hid, hour, rng),
                              service_s=world.service_for(hid, rng), scn=scn)
                rows.append(cr)
            group.append({"factor": factor, "value": shown, "n": len(rows),
                          "success": wilson(sum(r.success for r in rows), len(rows))})
        baseline = group[1]["success"][0]
        for row in group:
            row["delta_pp"] = round((row["success"][0] - baseline) * 100, 1)
            row["baseline"] = baseline
        out.extend(group)
    return out


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


def exp_prewarn(world, n=1000):
    """Compare predictive alert leads with a heads-up and one missed-ring retry."""
    log(f"pre-warn timing policy: {n} paired samples per lead")
    pool = world.waits["psu_bank"].by_hour.get(11, [])
    if not pool:
        pool = [world.wait_for("psu_bank", 11, random.Random(i)) for i in range(200)]
    lo, hi = P("exec.dead_air_patience_s")
    leads = list(range(0, 121, 10))
    points = []
    heads_up_s, retry_gap_s = 60.0, 12.0
    for lead in leads:
        on_time, single_on_time, early, late = 0, 0, [], []
        missed, recovered = 0, 0
        for seed in range(n):
            rng = random.Random(92000 + seed)
            wait = rng.choice(pool)
            estimate = max(0.0, wait + rng.gauss(0, 25.0))  # queue prediction error is assumed
            alert_at = max(0.0, estimate - lead)
            heads_up_at = max(0.0, alert_at - heads_up_s)
            primed = alert_at - heads_up_at >= 10.0
            patience = rng.uniform(lo, hi)
            response = User(rng, "M1", primed=primed).answer_delay()
            single_lateness = (patience + 120.0) if response is None else alert_at + response - wait
            single_on_time += single_lateness <= patience
            lateness = single_lateness
            if response is None:
                missed += 1
                retry = User(rng, "M1", primed=primed).answer_delay()
                if retry is not None:
                    lateness = alert_at + retry_gap_s + retry - wait
                    recovered += lateness <= patience
            on_time += lateness <= patience
            early.append(max(0.0, -lateness))
            late.append(max(0.0, lateness))
        points.append({"lead_s": lead, "n": n, "ready_by_pickup_plus_patience": round(on_time / n, 4),
                       "single_alert_ready_rate": round(single_on_time / n, 4),
                       "missed_primary_alerts": missed, "fallback_recovered": recovered,
                       "mean_early_ready_s": round(statistics.fmean(early), 1),
                       "mean_late_s": round(statistics.fmean(late), 1),
                       "heads_up_s": heads_up_s, "retry_gap_s": retry_gap_s})
    eligible = [p for p in points if p["ready_by_pickup_plus_patience"] >= 0.9]
    target_met = bool(eligible)
    if eligible:
        selected = min(eligible, key=lambda p: (p["mean_early_ready_s"], -p["ready_by_pickup_plus_patience"]))
    else:
        best_rate = max(p["ready_by_pickup_plus_patience"] for p in points)
        selected = min((p for p in points if p["ready_by_pickup_plus_patience"] == best_rate),
                       key=lambda p: p["mean_early_ready_s"])
    return {"points": points, "selected_lead_s": selected["lead_s"], "success_target": 0.9,
            "target_met": target_met,
            "prediction_error_sd_s": 25, "heads_up_s": heads_up_s, "retry_gap_s": retry_gap_s,
            "fallback": "one independent retry after missed primary alert (ASSUMED)",
            "primed": "60 s app heads-up before voice ring when available (ASSUMED)",
            "selection_rule": "minimize early-ready time among leads with >=90% handoff readiness; otherwise report best observed readiness"}


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
    for hid in world.profiles:
        prof = world.profiles[hid]
        policies = {
            "none": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3),
            "deadline_20min": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_patience=1200.0),
            "callback": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_strategy="callback"),
            "offpeak": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_strategy="offpeak"),
            "handshake": cq.city(prof, [0.0, 0.1, 0.25, 0.5], seeds=3, ai_service_factor=0.8),
        }
        base_wait = policies["none"][0]["hum_wait"]
        at_quarter = [(name, rows[2]) for name, rows in policies.items() if rows[2]["ai_wait"] is not None]
        eligible = [(name, row) for name, row in at_quarter if row["ai_wait"] <= 1200]
        choice = min(eligible or at_quarter, key=lambda pair: (pair[1]["hum_wait"], pair[1]["ai_wait"]))
        policies["recommendation"] = {"policy": choice[0], "adoption": 0.25,
                                      "human_wait_delta_s": round(choice[1]["hum_wait"] - base_wait, 1),
                                      "ai_wait_s": round(choice[1]["ai_wait"], 1), "ai_wait_cap_s": 1200,
                                      "objective": "minimize added human wait subject to mean AI queue wait <= 20 min"}
        out[hid] = policies
    return out


def exp_disruption(world):
    """Illustrative airline surge; the 3x multiplier is an explicit assumption."""
    p = world.profiles["airline"]
    surge = replace(p, arrivals=[x * 3 for x in p.arrivals])
    return {"helpline": "airline", "volume_multiplier": 3.0, "tag": "ASSUMED",
            "none": cq.city(surge, [0.0, 0.25, 0.5], seeds=5),
            "deadline_20min": cq.city(surge, [0.0, 0.25, 0.5], seeds=5, ai_patience=1200.0),
            "handshake": cq.city(surge, [0.0, 0.25, 0.5], seeds=5, ai_service_factor=0.8)}


def exp_calendar(world):
    """Historical weekday arrival shape plus an explicitly assumed peak-volume sweep."""
    by_date = {}
    by_weekday = {}
    for call in world.calls:
        if not call.wanted_agent:
            continue
        by_date[call.date] = (call.weekday, by_date.get(call.date, (call.weekday, 0))[1] + 1)
    for day, (weekday, count) in by_date.items():
        by_weekday.setdefault(weekday, []).append(count)
    overall = statistics.fmean(count for _, count in by_date.values())
    weekday = [{"day": i, "label": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[i],
                "mean_calls": round(statistics.fmean(by_weekday.get(i, [0])), 1),
                "index": round(statistics.fmean(by_weekday.get(i, [0])) / overall, 3)} for i in range(7)]
    p = world.profiles["psu_bank"]
    peaks = []
    for mult in (1.0, 1.25, 1.5):
        profile = replace(p, arrivals=[x * mult for x in p.arrivals])
        point = cq.city(profile, [0.25], seeds=3)[0]
        peaks.append({"volume_multiplier": mult, "mean_human_wait_s": round(point["hum_wait"], 1),
                      "human_abandon": round(point["hum_ab"], 4)})
    return {"weekday_source": "1999 call-centre records", "weekday": weekday,
            "peak_sweep_tag": "ASSUMED", "peak_sweep": peaks}


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
    seeds = 3 if quick else 30
    world = World(quick)
    real = exp_real_data(world)
    day = exp_real_day(world, real["wrapup_s"])
    waits = exp_waits(world)
    arm_rows, traces = exp_arms(world, seeds)
    stress_rows, stress_traces = exp_stress(world, 3 if quick else 30)
    traces.update(stress_traces)
    noise_sweep = exp_noise_sweep(world, 3 if quick else 30)
    sensitivity = exp_sensitivity(world, 3 if quick else 30)
    ablation = exp_ablation(world, 2 if quick else 5)
    modes = exp_modes(world, 4 if quick else 12)
    grid = exp_handoff_grid()
    prewarn = exp_prewarn(world, 300 if quick else 1000)
    platforms = exp_platforms(world, 2 if quick else 4)
    city = exp_city(world)
    disruption = exp_disruption(world)
    calendar = exp_calendar(world)
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
        "ablation": ablation, "modes": modes, "handoff_grid": grid, "prewarn": prewarn,
        "platforms": platforms, "city": city, "disruption": disruption, "calendar": calendar,
        "noise_sweep": noise_sweep, "sensitivity": sensitivity,
        "path_memory": memory,
        "features": [{"key": f, "group": FEATURE_GROUP[f], "text": FEATURE_TEXT[f]} for f in ALL_FEATURES],
        "provenance": export(), "atlas": world.atlas_summary,
        "runtime_s": round(time.time() - t0, 1),
    }
    (RESULTS / "raw.json").write_text(json.dumps(raw, default=str), encoding="utf-8")
    log(f"done in {raw['runtime_s']} s")
    return raw, traces, world
