"""Load India Hold Atlas field calls and register what they measure.

    python -m holdworld.atlas data/atlas/my_calls.csv
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

from .provenance import REGISTRY, Param, register


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if any(v.strip() for v in r.values() if v)]


def summarize(rows: list[dict]) -> dict:
    out = {"calls": len(rows), "by_helpline": {}}
    for hid in sorted({r["helpline"] for r in rows}):
        rs = [r for r in rows if r["helpline"] == hid]
        q = [x for x in (_num(r["queue_seconds"]) for r in rs) if x is not None]
        ivr = [x for x in (_num(r["ivr_seconds"]) for r in rs) if x is not None]
        out["by_helpline"][hid] = {"n": len(rs), "median_queue_s": statistics.median(q) if q else None,
                                   "median_ivr_s": statistics.median(ivr) if ivr else None}
    dead = [x for x in (_num(r.get("executive_dead_air_tolerance_s")) for r in rows) if x is not None]
    ann = [x for x in (_num(r.get("announcement_interval_s")) for r in rows) if x is not None]
    otp = [x for x in (_num(r.get("otp_seconds")) for r in rows) if x is not None]
    out["dead_air"] = dead
    out["announce"] = ann
    out["otp"] = otp
    return out


def apply(s: dict) -> list[str]:
    changed = []
    if len(s["dead_air"]) >= 3:
        lo, hi = min(s["dead_air"]), max(s["dead_air"])
        register(Param("exec.dead_air_patience_s", [lo, hi], "ATLAS", "atlas", "s", f"{len(s['dead_air'])} measured calls"))
        changed.append("exec.dead_air_patience_s")
    if len(s["announce"]) >= 3:
        register(Param("queue.announce_every_s", statistics.median(s["announce"]), "ATLAS", "atlas", "s"))
        changed.append("queue.announce_every_s")
    if len(s["otp"]) >= 3:
        register(Param("otp.delay_s.median", statistics.median(s["otp"]), "ATLAS", "atlas", "s"))
        changed.append("otp.delay_s.median")
    return changed


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/atlas/atlas_template.csv")
    s = summarize(load(p))
    print(f"{s['calls']} Atlas calls")
    for hid, v in s["by_helpline"].items():
        print(f"  {hid}: n={v['n']} median queue {v['median_queue_s']} s, median IVR {v['median_ivr_s']} s")
    before = {k: REGISTRY[k].tag for k in ("exec.dead_air_patience_s", "queue.announce_every_s", "otp.delay_s.median")}
    for k in apply(s):
        print(f"  {k}: {before[k]} -> ATLAS ({REGISTRY[k].value})")
