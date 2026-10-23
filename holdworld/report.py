"""Turns results into the static site's data files and a plain-text report."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from . import perception as pc

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "site" / "data"
RESULTS = ROOT / "results"
LABELS = [pc.RING, pc.BUSY, pc.NETWORK, pc.PROMPT, pc.IVR_WAIT, pc.MUSIC, pc.ANNOUNCE, pc.AGENT_LIKE, pc.SILENCE,
          pc.HUMAN, pc.HUMAN_WAIT, pc.AI_AGENT, pc.DATA, pc.ENDED]
ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def enc(xs):
    """0..1 floats -> one character each (64 levels)."""
    return "".join(ALPHA[max(0, min(63, round(float(x) * 63)))] for x in xs)


def compact_trace(tr: dict) -> dict:
    f = tr["frames"]
    lab = {l: ALPHA[i] for i, l in enumerate(LABELS)}
    return {
        "id": tr["id"], "r": tr["result"],
        "t0": f["t"][0] if f["t"] else 0, "n": len(f["t"]),
        "L": "".join(lab.get(x, "8") for x in f["label"]),
        "sp": enc(f["speech"]), "mu": enc(f["music"]), "sy": enc(f["synth"]), "ro": enc(f["room"]),
        "ag": "".join(str(x) for x in f["agent_speaking"]),
        "seg": [[s["s"], s["e"], s["l"], s["x"][:220], s["sp"]] for s in tr["segments"]],
        "bel": tr["belief"], "tx": tr["transcript"], "vis": tr["visited"], "vt": tr.get("visited_t", []),
        "qe": tr.get("q_enter"), "dur": tr.get("duration"), "hl": tr.get("helpline"), "task": tr.get("task"),
        "goal": tr.get("goal"), "pk": tr["pickup_t"],
        "br": tr["bridge_t"], "uj": tr["user_join_t"], "pat": tr["exec_patience"], "menu": tr["menu_text"][:6],
        "lang": tr["lang"], "why": tr["why"],
    }


PARITY = [
    # (product, feature, HoldWorld component, evidence key)
    ("Google Hold for Me", "Waits on hold for you", "Hold phase on every queue task", "arms:D:time_to_human_median"),
    ("Google Hold for Me", "Recognises hold music", "Music/speech classifier scores per frame", "stress:S8"),
    ("Google Hold for Me", "Tells a recorded message from a representative",
     "Known phrases, repetition, room sound, synthetic voice, 'hello?' probe", "stress:S6"),
    ("Google Hold for Me", "Alerts you when a person picks up", "Bridge / alert with measured detection delay",
     "arms:D:detect_latency_median"),
    ("Google Hold for Me", "Asks the representative to wait", "Stall line, executive patience model", "stress:S15"),
    ("Google Hold for Me", "Direct My Call: the menu as text", "menu_to_text", "feature:menu_to_text"),
    ("Google Hold for Me", "Wait times by hour", "Queue layer probe waits per hour", "waits"),
    ("Google Hold for Me", "Limited to Pixel, English, US/AU/CA toll-free", "Hindi + English, Indian numbers, short codes",
     "stress:S13"),
    ("Pine", "Calls customer service and finishes the task", "Autonomous mode with the executive", "goal:pine"),
    ("Pine", "Verification with your details", "Executive verification script", "stress:S16"),
    ("Pine", "One-time password relay", "otp_relay", "stress:S16"),
    ("Pine", "Cancels subscriptions, refuses retention offers", "offers_policy", "task:tel_cancel"),
    ("Pine", "Negotiates bills", "negotiate (discount ladder)", "task:tel_negotiate"),
    ("Pine", "Files complaints and gets reference numbers", "Read-back confirmation, digit voting", "task:psu_dispute"),
    ("Pine", "Hands over to you when the company insists", "ai_fallback", "feature:ai_fallback"),
    ("Pine", "Tracks time saved", "User minutes per call vs a human caller", "arms:D:user_minutes_median"),
    ("Sierra", "IVR simulator: synthesised prompts, DTMF, timers, holds", "Line layer (event level); DTMF timing ITU-T Q.24",
     "arms"),
    ("Sierra", "Agent blind to the tree", "HoldForMe gets only the goal and the user's details", "arms:D"),
    ("Sierra", "Goal types: reach a person, get a fact, do an action", "Tasks of all three types", "goal"),
    ("Sierra", "Bare vs guided comparison", "Basic agent (C) vs HoldForMe (D)", "arms:C"),
    ("Sierra", "Timing: preambles, disclaimers, silence", "turn_taking", "stress:S3"),
    ("Sierra", "Keys vs speech, broken prompts", "modality", "stress:S2"),
    ("Sierra", "Dead ends, loops, closed hours, missing inputs", "dead_end_escape, honest give-up", "stress:S4"),
    ("Sierra", "ID-format retry (drop the prefix)", "id_retry", "feature:id_retry"),
    ("Sierra", "Remembers which paths work", "path_memory", "path_memory"),
    ("Ours", "Indian helplines from official menus", "SBI / KVB / Union structures", "helplines"),
    ("Ours", "Queue replay from a real call centre", "440,837 real calls, held-out validation", "real"),
    ("Ours", "Registered-mobile, PIN and short-code rules", "Caller-ID gates, secret_guard, shortcode_map", "stress:S20"),
    ("Ours", "The handoff race", "Modes M1/M2/M3, patience x answer time", "modes"),
    ("Ours", "What happens at scale", "City layer: AI holders vs human callers", "city"),
]


def build(raw: dict, traces: dict, world=None) -> None:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    proof = {}
    pj = RESULTS / "tests.json"
    if pj.exists():
        proof = json.loads(pj.read_text(encoding="utf-8"))
    helplines = {}
    if world is not None:
        for hid, h in world.helplines.items():
            helplines[hid] = {
                "id": hid, "name": h.display_name, "brand": h.brand, "sector": h.sector,
                "source": h.structure_source, "tag": h.structure_tag, "dial": h.dial, "root": h.root,
                "languages": h.languages, "barge_in": h.barge_in, "caller_id_auth": h.caller_id_auth,
                "hours": h.hours, "notes": h.notes,
                "nodes": {nid: {"type": n.type, "opts": [[o.key, o.label.get("en"), o.label.get("hi"), o.goto]
                                                        for o in n.options],
                               "field": n.field, "next": n.next, "dept": n.dept, "fact": n.fact, "action": n.action,
                               "modality": n.modality, "extras": n.extras, "agent": n.agent_target}
                          for nid, n in h.nodes.items()},
                "tasks": [{"id": t.id, "goal": t.goal_text, "type": t.goal_type, "pine": t.pine, "target": t.target}
                          for t in h.tasks],
            }
    rd = raw["real_day"]
    world_data = {
        "generated_at": raw["generated_at"], "quick": raw["quick"], "runtime_s": raw["runtime_s"],
        "real": {k: raw["real"]["summary"][k] for k in raw["real"]["summary"]},
        "holdout": raw["real"]["holdout"], "wrapup_s": raw["real"]["wrapup_s"], "train_days": raw["real"]["train_days"],
        "real_day": {"date": rd["date"], "staffing": rd["staffing"],
                     "servers": sorted({e["srv"] for e in rd["events"] if e["srv"] != "NO_SERVER"}),
                     "events": [[e["a"], e["q"], e["o"][0], e["s"], e["p"], e["srv"]] for e in rd["events"]],
                     "sims": {a: {k: v for k, v in s.items() if k != "callers"} | {
                         "callers": [[c["a"], c["w"], 1 if c["srv"] else 0, c["k"][0], c["d"], c["s"]]
                                     for c in s["callers"]]} for a, s in rd["sims"].items()}},
        "waits": raw["waits"],
        "arms": {k: v for k, v in raw["arms"].items() if k != "rows"},
        "stress": {k: v for k, v in raw["stress"].items() if k != "rows"},
        "stress_rows": [[r["scenario"], r["arm"], r["seed"], r["pass"], r["trace_id"], r["end_reason"]]
                        for r in raw["stress"]["rows"]],
        "arm_rows": [[r["arm"], r["helpline"], r["task"], r["seed"], r["success"], r["trace_id"], r["end_reason"],
                      r["user_minutes"], r["t_total"], r["time_to_human"], r["cost_inr"]] for r in raw["arms"]["rows"]],
        "ablation": raw["ablation"], "modes": raw["modes"]["table"], "handoff_grid": raw["handoff_grid"],
        "platforms": raw["platforms"], "city": raw["city"], "path_memory": raw["path_memory"],
        "features": raw["features"], "provenance": raw["provenance"], "parity": PARITY, "helplines": helplines,
        "trace_ids": sorted(traces), "proof": proof,
    }
    (SITE_DATA / "world.js").write_text("window.HW=" + json.dumps(world_data, default=str, ensure_ascii=False) + ";",
                                        encoding="utf-8")
    ct = {tid: compact_trace(t) for tid, t in traces.items()}
    (SITE_DATA / "traces.js").write_text("window.HW_TRACES=" + json.dumps(ct, default=str, ensure_ascii=False) + ";",
                                         encoding="utf-8")
    write_markdown(raw)
    print(f"site data: world.js {(SITE_DATA / 'world.js').stat().st_size // 1024} KB, "
          f"traces.js {(SITE_DATA / 'traces.js').stat().st_size // 1024} KB ({len(ct)} calls)")


def _pct(w):
    return "-" if not w or w[0] is None else f"{w[0] * 100:.0f}% [{w[1] * 100:.0f}-{w[2] * 100:.0f}]"


def write_markdown(raw: dict) -> None:
    s = raw["real"]["summary"]
    h = raw["real"]["holdout"]
    L = ["# HoldWorld results", "", f"Generated {raw['generated_at']} (quick={raw['quick']}). Every number below is "
         "produced by `python -m holdworld run`; nothing is typed by hand.", "",
         "## 1. The real call-centre year (Anonymous Bank, 1999)", "",
         f"- Records: {s['records']:,} calls over {s['days']} days; {s['wanted_agent']:,} asked for an agent",
         f"- Abandoned while waiting: {s['abandon_frac'] * 100:.1f}%; mean wait of served callers {s['mean_wait_served_s']:.0f} s; "
         f"{s['p_wait_zero'] * 100:.0f}% served immediately",
         f"- Service time: median {s['service']['median_s']:.0f} s, mean {s['service']['mean_s']:.0f} s (lognormal "
         f"mu {s['service']['log_mu']:.2f}, sigma {s['service']['log_sigma']:.2f})",
         f"- Hang-up hazard spikes at {s['patience']['spikes_s'][:3]} s (first message, and the ~60 s replay)",
         f"- Replay check on {len(h['days'])} held-out days: real mean wait {h['mean_real_wait']:.1f} s vs simulated "
         f"{h['mean_sim_wait']:.1f} s; abandonment {h['mean_real_abandon'] * 100:.1f}% vs {h['mean_sim_abandon'] * 100:.1f}%; "
         f"correlation across days {h['corr_wait']:.3f} (wait), {h['corr_abandon']:.3f} (abandonment)",
         f"- After-call work fitted on Jan-Jun: {raw['real']['wrapup_s']:.1f} s", "",
         "## 2. Callers on every task (success, 95% interval)", "",
         "| Caller | n | Success | User minutes (median) | Time to human (median s) | False alerts / call | Cost INR (median) |",
         "|---|---|---|---|---|---|---|"]
    names = {"A": "Human caller", "B": "Scripted bot", "C": "Basic agent", "D": "HoldForMe", "O": "Oracle"}
    for arm in ("A", "B", "C", "D", "O"):
        v = raw["arms"]["summary"].get(arm)
        if v:
            L.append(f"| {names[arm]} | {v['n']} | {_pct(v['success'])} | {v['user_minutes_median']} | "
                     f"{v['time_to_human_median']} | {v['false_alerts_per_call']} | {v['cost_inr_median']} |")
    L += ["", "## 3. Stress suite (pass rate)", "", "| Scenario | " + " | ".join(names[a] for a in ("B", "C", "D", "O")) + " |",
          "|---|---|---|---|---|"]
    titles = {x["id"]: x["title"] for x in raw["stress"]["scenarios"]}
    for sid, cells in raw["stress"]["table"].items():
        L.append(f"| {sid} {titles.get(sid, '')} | " + " | ".join(_pct(cells.get(a)) for a in ("B", "C", "D", "O")) + " |")
    L += ["", "## 4. Handoff modes (airline line)", ""]
    for k, w in raw["modes"]["table"].items():
        L.append(f"- {k}: {_pct(w)}")
    L += ["", "## 5. City: share of callers who never hang up", ""]
    for hid, d in raw["city"].items():
        for mit, rows in d.items():
            L.append(f"- {hid} / {mit}: " + "; ".join(
                f"alpha {r['alpha']}: human wait {r['hum_wait']:.0f} s, human abandon {r['hum_ab'] * 100:.1f}%" for r in rows))
    L += ["", f"Path memory: first call IVR {raw['path_memory']['first_call_ivr_s']} s, second call "
          f"{raw['path_memory']['second_call_ivr_s']} s", "",
          "Provenance counts: " + ", ".join(f"{k} {v}" for k, v in raw["provenance"]["counts"].items())]
    (RESULTS / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
