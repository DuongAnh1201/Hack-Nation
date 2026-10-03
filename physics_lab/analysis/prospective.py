"""Prospective validation and next-experiment selection via model disagreement."""

import math
from typing import List, Tuple, Dict, Any, Optional
from physics_lab.analysis.laws import CANDIDATE_LAWS


def predict_for_all_laws(
    rankings: List[Dict[str, Any]],
    beta: float,
) -> Dict[str, float]:
    """Calculate prospective predictions for each candidate law at target beta."""
    preds = {}
    for item in rankings:
        name = item["name"]
        law = CANDIDATE_LAWS[name]
        params = item.get("full_fit_params")
        if not params:
            # Re-extract params from fitted_params dict in order
            params = [item["fitted_params"].get(p, 0.0) for p in law.param_names]
        try:
            val = law.predict(beta, params)
            preds[name] = round(val, 3)
        except Exception:
            preds[name] = 45.0
    return preds


def select_next_beta(
    rankings: List[Dict[str, Any]],
    existing_betas: List[float],
    min_beta: float = 0.01,
    max_beta: float = 100.0,
    disagreement_threshold_deg: float = 0.05,
) -> Dict[str, Any]:
    """Select the most informative beta condition to test next."""
    if len(rankings) < 2:
        return {
            "beta": 1.0,
            "disagreement_deg": 0.0,
            "reason": "Default beta=1.0 for initial exploration.",
            "mode": "initial",
        }

    law1 = CANDIDATE_LAWS[rankings[0]["name"]]
    p1 = rankings[0]["full_fit_params"]
    law2 = CANDIDATE_LAWS[rankings[1]["name"]]
    p2 = rankings[1]["full_fit_params"]

    # Sample candidates in log space
    sample_points = []
    curr = min_beta
    while curr <= max_beta * 1.0001:
        sample_points.append(curr)
        curr *= 1.5

    best_beta = sample_points[0]
    max_disagreement = -1.0

    for b in sample_points:
        try:
            v1 = law1.predict(b, p1)
            v2 = law2.predict(b, p2)
            disagree = abs(v1 - v2)
            if disagree > max_disagreement:
                max_disagreement = disagree
                best_beta = b
        except Exception:
            continue

    if max_disagreement > disagreement_threshold_deg:
        return {
            "beta": round(best_beta, 4),
            "disagreement_deg": round(max_disagreement, 3),
            "reason": f"laws '{law1.name}' and '{law2.name}' disagree most here ({max_disagreement:.3f} deg)",
            "mode": "model_discrimination",
        }

    # If laws agree everywhere, find beta farthest in log space from existing points
    log_existing = [math.log10(max(1e-5, b)) for b in existing_betas]
    best_dist = -1.0
    farthest_beta = min_beta

    candidates = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
    for b in candidates:
        lb = math.log10(b)
        min_dist = min(abs(lb - le) for le in log_existing) if log_existing else 10.0
        if min_dist > best_dist:
            best_dist = min_dist
            farthest_beta = b

    return {
        "beta": round(farthest_beta, 4),
        "disagreement_deg": round(max_disagreement, 3),
        "reason": f"top laws agree to within {disagreement_threshold_deg} deg everywhere, so pick the beta farthest from existing data for an independent prospective test",
        "mode": "boundary_check",
    }
