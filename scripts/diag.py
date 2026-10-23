"""Developer diagnostic: run HoldForMe on every task and show one annotated trace per failure type.

    python scripts/diag.py [seeds] [arm]
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from holdworld import agents as A, episode as E, helplines as H, nav  # noqa: E402
from holdworld.understand import ivr_type  # noqa: E402

seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
arm = sys.argv[2] if len(sys.argv) > 2 else "D"
make = {"D": lambda: A.HoldForMe(), "O": A.Oracle, "C": A.basic_agent}[arm]
pf = "bolna_tuned" if arm == "C" else "plivo_hybrid"
hls = H.all_helplines()
ok = tot = 0
first = {}
by_task = collections.Counter()
for hid, h in hls.items():
    for task in h.tasks:
        for seed in range(seeds):
            mode = "M2" if h.caller_id_auth else "M1"
            ag = make()
            cr, env = E.run_task(h, task, ag, mode=mode, platform=pf, hour=12, seed=seed, wait_s=120,
                                 service_s=200, keep_env=True)
            tot += 1
            ok += cr.success
            if not cr.success:
                key = (hid, task.id, cr.end_reason)
                by_task[key] += 1
                first.setdefault(key, (seed, env, ag, cr))
print(f"{arm}: {ok}/{tot} = {ok / tot:.0%}")
for key, n in sorted(by_task.items(), key=lambda kv: -kv[1]):
    print(n, key)
if "-v" in sys.argv:
    for key, (seed, env, ag, cr) in list(first.items())[:12]:
        print("\n=====", key, "seed", seed, "lang", env.persona.lang_pref, "captured", ag.result.get("captured"),
              "fact", ag.result.get("fact"), "truth", env.facts, env.refs, env.exec_outcome)
        for x in env.transcript[-12:]:
            k = ivr_type(x["text"])[0] if x["who"] == "ivr" else ""
            print(f"  {x['t']:>6} {x['who'][:5]:5} {x['label'][:7]:7} {k:14} {x['text'][:110]}")
