"""Export real spectra from Person 4's simulator for the UI's spectrum view.

For every experiment in a research record, call lab.physics._evaluate (physics only:
it does not count evaluations, so exporting never touches the benchmark budget) and
write one JSON file the UI reads:

  {"wavelength_um": [...], "bands": {"solar": [..], "window": [..]}, "ideal": [...],
   "sky_transmittance": [...],
   "designs": {"<experiment id>": {"label", "emissivity": [...], "p_net_w_m2", ...}}}

The solar part (normal incidence) is used below 2.5 um and the thermal part
(near-normal) above, downsampled so the file stays small.

Run:  python -m analysis.export_spectra runs/<run_id>/record.jsonl --out frontend/public/demo/spectra.json
      (add --lab-path <dir containing lab/> while the simulator is not on main yet)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SOLAR_STEP = 5  # keep every 5th point of the 2 nm solar grid


def load_experiments(record: Path) -> list[dict]:
    out = []
    for line in record.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "experiment":
                out.append(e)
    return out


def label(e: dict) -> str:
    c = e["content"]
    mats = list(dict.fromkeys(c["materials"]))
    kind = "Stanford control" if c.get("type") == "control" else f"test {c.get('hypothesis', '')}".strip()
    return f"{e['id']} · {len(c['materials'])} layers {'/'.join(mats)} ({kind})"


def build(experiments: list[dict], physics) -> dict:
    sol = physics.SOLAR_GRID_UM
    th = physics.THERMAL_GRID_UM
    keep_sol = np.arange(len(sol))[(sol < th[0])][::SOLAR_STEP]
    lam = np.concatenate([sol[keep_sol], th])
    win_lo, win_hi = physics.WINDOW_BAND_UM
    sky = physics._spec.zenith_transmittance(th)

    designs = {}
    for e in experiments:
        c = e["content"]
        r = physics._evaluate(c["materials"], c["thicknesses_nm"], c.get("substrate", "Ag"))
        s = r["_spectra"]
        eps = np.concatenate([np.asarray(s["solar_emissivity"])[keep_sol], np.asarray(s["thermal_emissivity_near_normal"])])
        designs[e["id"]] = {
            "label": label(e),
            "emissivity": [round(float(x), 4) for x in eps],
            "p_net_w_m2": r["p_net_w_m2"],
            "solar_reflectance": r["solar_reflectance"],
            "window_emissivity": r["window_emissivity"],
        }
    return {
        "_source": "lab.physics._evaluate (Person 4's simulator)",
        "wavelength_um": [round(float(x), 4) for x in lam],
        "bands": {"solar": list(physics.SOLAR_BAND_UM), "window": [win_lo, win_hi]},
        "ideal": [1.0 if win_lo <= x <= win_hi else 0.0 for x in lam],
        "sky_transmittance": [0.0] * len(keep_sol) + [round(float(x), 4) for x in sky],
        "sky_model": physics._spec.atmosphere_model_name(),
        "designs": designs,
    }


def _git_rev(path: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m analysis.export_spectra", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record")
    ap.add_argument("--out", default="frontend/public/demo/spectra.json")
    ap.add_argument("--lab-path", help="directory that contains the lab/ package (default: repo root)")
    args = ap.parse_args(argv)
    if args.lab_path:
        sys.path.insert(0, str(Path(args.lab_path).resolve()))
    try:
        from lab import physics
    except ImportError as exc:
        print(f"error: cannot import lab.physics ({exc}); pass --lab-path", file=sys.stderr)
        return 2
    experiments = load_experiments(Path(args.record))
    if not experiments:
        print("error: no experiment entries in the record", file=sys.stderr)
        return 2
    data = build(experiments, physics)
    rev = _git_rev(Path(args.lab_path or "."))
    if rev:
        data["_source"] += f" @ {rev}"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data), encoding="utf-8")
    for k, d in data["designs"].items():
        print(f"{k}: P_net {d['p_net_w_m2']:.2f} W/m², solar reflectance {d['solar_reflectance']:.3f}, "
              f"window emissivity {d['window_emissivity']:.3f}")
    print(f"wrote {out} ({len(data['wavelength_um'])} wavelengths, sky model {data['sky_model']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
