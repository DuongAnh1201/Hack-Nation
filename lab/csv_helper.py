"""Standardized CSV helper for experimental results (Issue #35).

Knowledge & Memory merges every results.csv across experiments, so all
simulations adhere strictly to this schema.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Union

RESULTS_COLUMNS = [
    "design_id",
    "materials",
    "thicknesses_nm",
    "substrate",
    "n_layers",
    "p_net_w_m2",
    "solar_reflectance",
    "window_emissivity",
    "valid",
    "reason",
    "seed",
]


def write_results_csv(rows: List[Dict[str, Any]], path: Union[str, Path]) -> str:
    """Write experiment simulation trials to CSV with the standardized schema.

    Args:
        rows: List of dicts representing simulation trials.
        path: Filepath where the CSV will be written.

    Returns:
        The resolved absolute path string of the written CSV.
    """
    target_path = Path(path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    formatted_rows = []
    for r in rows:
        mats = r.get("materials", [])
        if isinstance(mats, (list, tuple)):
            mats_str = "|".join(str(m) for m in mats)
            n_layers = len(mats)
        else:
            mats_str = str(mats)
            n_layers = r.get("n_layers", len(mats_str.split("|")) if mats_str else 0)

        thicks = r.get("thicknesses_nm", [])
        if isinstance(thicks, (list, tuple)):
            thicks_str = "|".join(f"{float(t):.1f}" for t in thicks)
        else:
            thicks_str = str(thicks)

        p_net = r.get("p_net_w_m2")
        p_net_val = f"{float(p_net):.2f}" if p_net is not None and str(p_net) != "" else ""

        r_sol = r.get("solar_reflectance")
        r_sol_val = f"{float(r_sol):.4f}" if r_sol is not None and str(r_sol) != "" else ""

        eps_win = r.get("window_emissivity")
        eps_win_val = f"{float(eps_win):.4f}" if eps_win is not None and str(eps_win) != "" else ""

        valid = bool(r.get("valid", True))
        reason = str(r.get("reason", ""))
        seed = r.get("seed", "")

        formatted_rows.append({
            "design_id": str(r.get("design_id", "")),
            "materials": mats_str,
            "thicknesses_nm": thicks_str,
            "substrate": str(r.get("substrate", "Ag")),
            "n_layers": n_layers,
            "p_net_w_m2": p_net_val,
            "solar_reflectance": r_sol_val,
            "window_emissivity": eps_win_val,
            "valid": "true" if valid else "false",
            "reason": reason,
            "seed": str(seed) if seed is not None else "",
        })

    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_COLUMNS)
        writer.writeheader()
        writer.writerows(formatted_rows)

    return str(target_path)


def read_results_csv(path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Read a standardized results CSV into typed dictionaries."""
    target_path = Path(path).resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {target_path}")

    rows = []
    with open(target_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            mats = r["materials"].split("|") if r["materials"] else []
            thicks = [float(t) for t in r["thicknesses_nm"].split("|")] if r["thicknesses_nm"] else []
            rows.append({
                "design_id": r["design_id"],
                "materials": mats,
                "thicknesses_nm": thicks,
                "substrate": r["substrate"],
                "n_layers": int(r["n_layers"]) if r["n_layers"] else len(mats),
                "p_net_w_m2": float(r["p_net_w_m2"]) if r["p_net_w_m2"] else None,
                "solar_reflectance": float(r["solar_reflectance"]) if r["solar_reflectance"] else None,
                "window_emissivity": float(r["window_emissivity"]) if r["window_emissivity"] else None,
                "valid": r["valid"].lower() == "true",
                "reason": r["reason"],
                "seed": int(r["seed"]) if r["seed"] and r["seed"].isdigit() else r["seed"],
            })
    return rows
