"""Example experiment script (Issue #35).

Demonstrates the pattern for experiment scripts written by the Experiment Runner:
1. Imports lab.physics:simulate_stack and lab.csv_helper:write_results_csv
2. Evaluates designs and records metrics (including invalid trials)
3. Outputs results.csv and logs progress to output.log
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lab.physics import simulate_stack
from lab.csv_helper import write_results_csv


def main() -> None:
    exp_dir = Path(__file__).resolve().parent
    log_file = exp_dir / "output.log"
    csv_file = exp_dir / "results.csv"

    # Define candidate trials for E0 (baseline & parameter explorations)
    trials = [
        {
            "design_id": "E0-001",
            "materials": ["SiO2", "TiO2", "SiO2", "TiO2", "SiO2"],
            "thicknesses_nm": [100.0, 50.0, 100.0, 50.0, 100.0],
            "substrate": "Ag",
            "seed": 0,
        },
        {
            "design_id": "E0-002",
            "materials": ["Si3N4", "SiO2", "Si3N4", "SiO2"],
            "thicknesses_nm": [115.0, 390.0, 75.0, 410.0],
            "substrate": "Ag",
            "seed": 0,
        },
        {
            "design_id": "E0-003",
            "materials": ["Al2O3", "SiO2", "Al2O3"],
            "thicknesses_nm": [150.0, 200.0, 150.0],
            "substrate": "Al",
            "seed": 1,
        },
        {
            "design_id": "E0-004",
            "materials": ["SiO2", "TiO2", "SiO2", "TiO2", "SiO2", "SiO2"],
            "thicknesses_nm": [50.0, 50.0, 50.0, 50.0, 50.0, 50.0],
            "substrate": "Ag",
            "seed": 2,
        },
    ]

    results = []
    log_lines = [f"Starting Experiment E0 in {exp_dir}"]

    for trial in trials:
        mats = trial["materials"]
        thicks = trial["thicknesses_nm"]
        sub = trial["substrate"]
        did = trial["design_id"]

        # Bounds check
        if len(mats) > 5:
            log_lines.append(f"[{did}] INVALID: 6 layers > 5 allowed")
            results.append({
                "design_id": did,
                "materials": mats,
                "thicknesses_nm": thicks,
                "substrate": sub,
                "n_layers": len(mats),
                "p_net_w_m2": None,
                "solar_reflectance": None,
                "window_emissivity": None,
                "valid": False,
                "reason": f"{len(mats)} layers > 5",
                "seed": trial.get("seed", ""),
            })
            continue

        res = simulate_stack(mats, thicks, sub)
        p_net = res.get("p_net_w_m2", 0.0)
        r_sol = res.get("solar_reflectance", 0.0)
        eps = res.get("window_emissivity", 0.0)

        log_lines.append(f"[{did}] P_net = {p_net:.2f} W/m2, R_solar = {r_sol:.4f}, eps_win = {eps:.4f}")
        results.append({
            "design_id": did,
            "materials": mats,
            "thicknesses_nm": thicks,
            "substrate": sub,
            "n_layers": len(mats),
            "p_net_w_m2": p_net,
            "solar_reflectance": r_sol,
            "window_emissivity": eps,
            "valid": True,
            "reason": "",
            "seed": trial.get("seed", ""),
        })

    # Write CSV
    write_results_csv(results, csv_file)
    log_lines.append(f"Wrote {len(results)} rows to {csv_file.name}")

    # Write log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))


if __name__ == "__main__":
    main()
