"""Safety evaluation and compute budget enforcement."""

from typing import Dict, Any, List, Tuple


def evaluate_safety(
    experiment_spec: Dict[str, Any],
    total_session_simulations: int = 0,
    human_approved: bool = False,
) -> Dict[str, Any]:
    """Safety evaluation of an experiment specification against compute and physical bounds."""
    issues: List[str] = []
    warnings: List[str] = []
    approval_reasons: List[str] = []

    conditions = experiment_spec.get("conditions", [])
    if not conditions:
        issues.append("Experiment spec contains no test conditions.")

    est_sims_per_cond = 25
    if experiment_spec.get("kind") == "single_shot":
        est_sims_per_cond = 1

    estimated_simulations = len(conditions) * est_sims_per_cond

    for i, cond in enumerate(conditions):
        params = cond.get("params", {})
        label = cond.get("label", f"condition {i+1}")

        v0 = params.get("initial_velocity", 30.0)
        cd = params.get("drag_coefficient", 0.0)
        mass = params.get("mass", 0.145)
        area = params.get("cross_section_area", 0.0042)
        rho = params.get("air_density", 1.225)
        g = params.get("gravity", 9.81)

        if v0 <= 0 or mass <= 0 or area <= 0 or g <= 0 or cd < 0 or rho < 0:
            issues.append(f"{label}: Invalid physical parameter(s) detected (must be positive).")

        if v0 > 250.0:
            warnings.append(
                f"{label}: v0 = {v0:.1f} m/s approaches sonic speed; air compressibility is not modeled."
            )

        # Compute beta
        if mass > 0 and g > 0:
            k = (rho * cd * area) / (2.0 * mass)
            beta = (k * (v0 ** 2)) / g
            if beta > 100.0:
                warnings.append(
                    f"{label}: beta = {beta:.1f} > 100 enters extreme turbulence; outside calibrated range."
                )

    if not experiment_spec.get("hypothesis_ids"):
        warnings.append("experiment is not linked to any hypothesis")

    # Budget gate
    if estimated_simulations > 400:
        if not human_approved:
            return {
                "verdict": "needs_human",
                "issues": issues,
                "warnings": warnings,
                "approval_reasons": [],
                "estimated_simulations": estimated_simulations,
                "approver": "human_gate_required",
                "summary": f"Rejected automatic execution: estimated {estimated_simulations} simulations exceeds 400 cap. Human sign-off required.",
            }
        else:
            approval_reasons.append(f"Run authorized by human sign-off ({estimated_simulations} simulations).")

    if total_session_simulations + estimated_simulations > 5000:
        return {
            "verdict": "reject",
            "issues": issues + [f"Total session simulations limit (5,000) reached."],
            "warnings": warnings,
            "approval_reasons": [],
            "estimated_simulations": estimated_simulations,
            "approver": "hard_session_cap",
            "summary": "Session compute quota exhausted (5,000 simulations).",
        }

    if issues:
        return {
            "verdict": "reject",
            "issues": issues,
            "warnings": warnings,
            "approval_reasons": [],
            "estimated_simulations": estimated_simulations,
            "approver": "safety_gate",
            "summary": f"Rejected: {'; '.join(issues)}",
        }

    return {
        "verdict": "approve",
        "issues": [],
        "warnings": warnings,
        "approval_reasons": approval_reasons or ["Within compute bounds and valid physical parameters."],
        "estimated_simulations": estimated_simulations,
        "approver": "automatic (within limits)" if not human_approved else "human_approved",
        "summary": f"approved (approve; approver: {'automatic (within limits)' if not human_approved else 'human_approved'})",
    }
