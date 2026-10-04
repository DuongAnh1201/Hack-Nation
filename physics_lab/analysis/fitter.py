"""Nonlinear regression and Leave-One-Out (LOO) cross-validation for candidate laws."""

import math
from typing import List, Tuple, Dict, Any, Optional
from physics_lab.analysis.laws import CandidateLaw, get_laws_for_tier, CANDIDATE_LAWS


def nelder_mead(
    cost_fn,
    x0: List[float],
    max_iter: int = 500,
    tol: float = 1e-6,
) -> Tuple[List[float], float]:
    """Pure Python Nelder-Mead simplex optimization."""
    n = len(x0)
    # Initialize simplex around x0
    simplex = [list(x0)]
    for i in range(n):
        point = list(x0)
        point[i] = point[i] * 1.05 if point[i] != 0.0 else 0.005
        simplex.append(point)

    alpha = 1.0  # Reflection
    gamma = 2.0  # Expansion
    rho = 0.5    # Contraction
    sigma = 0.5  # Shrink

    for _ in range(max_iter):
        simplex.sort(key=cost_fn)
        best = simplex[0]
        worst = simplex[-1]
        second_worst = simplex[-2]

        f_best = cost_fn(best)
        f_worst = cost_fn(worst)

        if abs(f_worst - f_best) < tol:
            break

        # Centroid of all points except worst
        centroid = [
            sum(simplex[i][j] for i in range(n)) / n
            for j in range(n)
        ]

        # Reflection
        xr = [centroid[j] + alpha * (centroid[j] - worst[j]) for j in range(n)]
        fxr = cost_fn(xr)

        if f_best <= fxr < cost_fn(second_worst):
            simplex[-1] = xr
            continue

        # Expansion
        if fxr < f_best:
            xe = [centroid[j] + gamma * (xr[j] - centroid[j]) for j in range(n)]
            if cost_fn(xe) < fxr:
                simplex[-1] = xe
            else:
                simplex[-1] = xr
            continue

        # Contraction
        xc = [centroid[j] + rho * (worst[j] - centroid[j]) for j in range(n)]
        if cost_fn(xc) < f_worst:
            simplex[-1] = xc
            continue

        # Shrink
        for i in range(1, n + 1):
            simplex[i] = [best[j] + sigma * (simplex[i][j] - best[j]) for j in range(n)]

    simplex.sort(key=cost_fn)
    return simplex[0], cost_fn(simplex[0])


def fit_law(
    law: CandidateLaw,
    data: List[Tuple[float, float]],
) -> Dict[str, Any]:
    """Fit a single candidate law to (beta, theta*) data points."""
    n = len(data)
    if n == 0:
        return {"params": law.initial_params, "rmse": 999.0, "fitted_params": {}}

    def loss(p: List[float]) -> float:
        sq_err = 0.0
        for beta, theta in data:
            try:
                pred = law.predict(beta, p)
                sq_err += (pred - theta) ** 2
            except (ValueError, OverflowError, ZeroDivisionError):
                sq_err += 1e6
        return sq_err

    best_p, min_loss = nelder_mead(loss, list(law.initial_params))
    rmse = math.sqrt(min_loss / n)

    fitted_dict = {name: round(val, 4) for name, val in zip(law.param_names, best_p)}
    return {
        "params": best_p,
        "fitted_params": fitted_dict,
        "rmse": rmse,
    }


def fit_law_loo(
    law: CandidateLaw,
    data: List[Tuple[float, float]],
) -> Dict[str, Any]:
    """Fit candidate law using Leave-One-Out cross-validation."""
    n = len(data)
    if n < 3:
        fit_res = fit_law(law, data)
        return {
            "name": law.name,
            "formula": law.formula_str,
            "fitted_params": fit_res["fitted_params"],
            "loo_rmse_deg": fit_res["rmse"],
            "loo_max_error_deg": fit_res["rmse"],
            "systematic_residuals": False,
        }

    errors = []
    for i in range(n):
        train_data = [data[j] for j in range(n) if j != i]
        test_beta, test_theta = data[i]

        fit_res = fit_law(law, train_data)
        try:
            pred = law.predict(test_beta, fit_res["params"])
            err = abs(pred - test_theta)
        except Exception:
            err = 99.0
        errors.append(err)

    full_fit = fit_law(law, data)
    loo_rmse = math.sqrt(sum(e ** 2 for e in errors) / n)
    loo_max = max(errors)

    # Check for systematic residuals (runs of sign)
    residuals = []
    for beta, theta in sorted(data, key=lambda x: x[0]):
        try:
            p = law.predict(beta, full_fit["params"])
            residuals.append(p - theta)
        except Exception:
            pass

    # Simple run-test for residual structure
    signs = [1 if r > 0 else -1 for r in residuals if abs(r) > 0.01]
    runs = 1 + sum(1 for k in range(len(signs) - 1) if signs[k] != signs[k + 1])
    systematic = (loo_rmse > 0.1) and (len(signs) >= 5 and runs <= len(signs) / 2)

    return {
        "name": law.name,
        "formula": law.formula_str,
        "fitted_params": full_fit["fitted_params"],
        "loo_rmse_deg": round(loo_rmse, 3),
        "loo_max_error_deg": round(loo_max, 3),
        "systematic_residuals": systematic,
        "full_fit_params": full_fit["params"],
    }


def rank_laws(
    data: List[Tuple[float, float]],
    tier: int = 1,
) -> List[Dict[str, Any]]:
    """Rank candidate laws for a given tier by LOO RMSE."""
    laws = get_laws_for_tier(tier)
    rankings = []
    for law in laws:
        ranking = fit_law_loo(law, data)
        rankings.append(ranking)

    rankings.sort(key=lambda x: x["loo_rmse_deg"])
    return rankings
