"""Random search baseline for multilayer radiative cooling design.

Explores the identical search space as all other methods:
- 1 to 5 layers
- Allowed materials: SiO2, Al2O3, Si3N4, TiO2, MgF2
- Allowed substrates: Ag, Al
- Layer thicknesses: [10.0, 1000.0] nm (inclusive)

Every simulation call is counted through `lab.physics.simulate_stack`.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import numpy as np

from lab import physics

DEFAULT_CONTROL_PATH = Path(__file__).resolve().parent.parent / "results" / "control.json"


def get_default_target() -> float:
    """Load the computed target cooling power from results/control.json if present,

    or compute it via stanford_control().
    """
    if DEFAULT_CONTROL_PATH.exists():
        try:
            data = json.loads(DEFAULT_CONTROL_PATH.read_text(encoding="utf-8"))
            return float(data["target_w_m2"])
        except Exception:
            pass
    control = physics.stanford_control()
    return float(control["target_w_m2"])


def run_random_search(
    seed: int = 0,
    budget: int = 20,
    target_w_m2: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute one random-search run with a fixed random seed and evaluation budget.

    Returns:
        dict with:
            seed: int
            budget: int
            target_w_m2: float
            evaluations_used: int
            best_w_m2: float or None
            best_design: dict or None
            evals_to_target: int or None (None if target was never reached)
            history: list of evaluation records
    """
    if target_w_m2 is None:
        target_w_m2 = get_default_target()

    rng = np.random.default_rng(seed)
    physics.reset_evaluation_count()
    physics.set_evaluation_budget(budget)

    materials_pool = list(physics.ALLOWED_MATERIALS)
    substrates_pool = list(physics.ALLOWED_SUBSTRATES)
    lo, hi = physics.THICKNESS_BOUNDS_NM

    best_p_net = -float("inf")
    best_design = None
    evals_to_target: Optional[int] = None
    history: List[Dict[str, Any]] = []

    for step in range(1, budget + 1):
        n_layers = int(rng.integers(physics.MIN_LAYERS, physics.MAX_LAYERS + 1))
        chosen_materials = [str(m) for m in rng.choice(materials_pool, size=n_layers, replace=True)]
        chosen_substrate = str(rng.choice(substrates_pool))
        chosen_thicknesses = [round(float(t), 2) for t in rng.uniform(lo, hi, size=n_layers)]

        try:
            res = physics.simulate_stack(
                materials=chosen_materials,
                thicknesses_nm=chosen_thicknesses,
                substrate=chosen_substrate,
            )
        except physics.EvaluationBudgetExceeded:
            break

        p_net = res.get("p_net_w_m2")
        history.append({
            "step": step,
            "materials": chosen_materials,
            "thicknesses_nm": chosen_thicknesses,
            "substrate": chosen_substrate,
            "p_net_w_m2": p_net,
            "solar_reflectance": res.get("solar_reflectance"),
            "window_emissivity": res.get("window_emissivity"),
            "valid": res.get("valid", False),
        })

        if p_net is not None and p_net > best_p_net:
            best_p_net = p_net
            best_design = {
                "materials": chosen_materials,
                "thicknesses_nm": chosen_thicknesses,
                "substrate": chosen_substrate,
                "p_net_w_m2": p_net,
            }

        if evals_to_target is None and p_net is not None and p_net >= target_w_m2:
            evals_to_target = step

    actual_evals = physics.evaluation_count()

    return {
        "seed": seed,
        "budget": budget,
        "target_w_m2": target_w_m2,
        "evaluations_used": actual_evals,
        "best_w_m2": round(best_p_net, 4) if best_p_net != -float("inf") else None,
        "best_design": best_design,
        "evals_to_target": evals_to_target,
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Run random search baseline for radiative cooling.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--budget", type=int, default=20, help="Total evaluation budget")
    parser.add_argument("--target", type=float, default=None, help="Target net cooling power (W/m^2)")
    args = parser.parse_args()

    result = run_random_search(seed=args.seed, budget=args.budget, target_w_m2=args.target)
    print(json.dumps({
        "seed": result["seed"],
        "budget": result["budget"],
        "target_w_m2": result["target_w_m2"],
        "evaluations_used": result["evaluations_used"],
        "best_w_m2": result["best_w_m2"],
        "evals_to_target": result["evals_to_target"],
        "best_design": result["best_design"],
    }, indent=2))


if __name__ == "__main__":
    main()
