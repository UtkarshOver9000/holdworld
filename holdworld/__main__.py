"""HoldWorld command line.

    python -m holdworld fetch-data     download the real 1999 call-centre data (10.6 MB)
    python -m holdworld run [--quick]  run every experiment and build the site data
    python -m holdworld test           run the test suite and save the proof report
"""
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "run"
    sys.stdout.reconfigure(encoding="utf-8")
    if cmd == "fetch-data":
        from .fetch import fetch
        fetch()
    elif cmd == "run":
        from .experiments import run_all
        from .report import build
        raw, traces, world = run_all(quick="--quick" in argv)
        build(raw, traces, world)
    elif cmd == "test":
        from .proof import run_tests
        sys.exit(run_tests())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
