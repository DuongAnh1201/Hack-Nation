"""Run the Stanford control and write results/control.json.

    python -m lab.control            # writes results/control.json
    python -m lab.control --stdout   # print only

``target_w_m2`` in the output is the benchmark target: the Stanford design's
P_net computed by *this* simulator under the fixed bench conditions, never the
paper's 40.1 W/m^2. ``target_status`` says whether the control passed.
"""

import argparse
import json
import subprocess
from pathlib import Path

from lab import physics

ROOT = Path(__file__).resolve().parent.parent


def _git_rev():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def build_report():
    c = physics.stanford_control()
    c["target_status"] = "final" if c["passed"] else "provisional: control did not pass all checks"
    c["search_space"] = physics.SEARCH_SPACE
    c["evaluation_unit"] = "one simulate_stack call (counted inside lab.physics, invalid designs included)"
    c["git_rev"] = _git_rev()
    c["reproduce"] = "python -m lab.control"
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stdout", action="store_true", help="print, do not write results/control.json")
    ap.add_argument("--out", default=str(ROOT / "results" / "control.json"))
    args = ap.parse_args(argv)
    report = build_report()
    text = json.dumps(report, indent=2)
    if args.stdout:
        print(text)
        return
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n")
    print(f"wrote {out}: target {report['target_w_m2']:.2f} W/m^2 ({report['target_status']})")


if __name__ == "__main__":
    main()
