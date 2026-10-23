"""Run the test suite and save a machine-readable proof report (results/tests.json + junit.xml)."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def run_tests() -> int:
    RESULTS.mkdir(exist_ok=True)
    junit = RESULTS / "junit.xml"
    t0 = time.time()
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}",
                        str(ROOT / "tests")], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    (RESULTS / "pytest_output.txt").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    tests = []
    if junit.exists():
        root = ET.parse(junit).getroot()
        for case in root.iter("testcase"):
            status = "passed"
            msg = ""
            for tag in ("failure", "error", "skipped"):
                el = case.find(tag)
                if el is not None:
                    status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                    msg = (el.get("message") or "")[:300]
            doc = ""
            tests.append({"name": case.get("name"), "module": (case.get("classname") or "").split(".")[-1],
                          "time": round(float(case.get("time") or 0), 3), "status": status, "message": msg})
    summary = {"ran_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t0, 1),
               "total": len(tests), "passed": sum(t["status"] == "passed" for t in tests),
               "failed": sum(t["status"] in ("failed", "error") for t in tests),
               "skipped": sum(t["status"] == "skipped" for t in tests), "python": sys.version.split()[0],
               "tests": tests}
    (RESULTS / "tests.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(r.stdout[-2000:])
    print(f"proof: {summary['passed']}/{summary['total']} passed -> results/tests.json")
    return r.returncode
