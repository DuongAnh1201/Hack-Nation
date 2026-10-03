"""Experiment execution engine running parameter conditions and optimizing angles."""

from typing import Dict, Any, List, Optional
from physics_lab.physics.models import ProjectileParams
from physics_lab.physics.engine import simulate
from physics_lab.experiments.optimizer import optimize_angle
from physics_lab.record import ResearchRecord


def execute_experiment(
    experiment_spec: Dict[str, Any],
    record: Optional[ResearchRecord] = None,
) -> Dict[str, Any]:
    """Execute an experiment spec across conditions and return structured result data."""
    kind = experiment_spec.get("kind", "optimize_angle")
    conditions = experiment_spec.get("conditions", [])

    condition_results: List[Dict[str, Any]] = []
    total_simulations = 0

    for cond in conditions:
        label = cond.get("label", "")
        params_dict = cond.get("params", {})
        params = ProjectileParams.from_dict(params_dict)

        if kind == "optimize_angle":
            opt = optimize_angle(params)
            opt["label"] = label
            condition_results.append(opt)
            total_simulations += opt["simulations"]
        else:
            sim_res = simulate(params, record_trajectory=True)
            res_dict = sim_res.to_dict()
            res_dict["label"] = label
            condition_results.append(res_dict)
            total_simulations += 1

    if record:
        record.increment_simulations(total_simulations)

    thetas = [c.get("theta_opt_deg") for c in condition_results if "theta_opt_deg" in c]
    summary_str = f"{experiment_spec.get('id', 'Exp')}: {total_simulations} simulations; theta* = {thetas} deg"

    result_data = {
        "kind": kind,
        "conditions": condition_results,
        "total_simulations": total_simulations,
    }

    return {
        "summary": summary_str,
        "data": result_data,
        "simulations": total_simulations,
    }
