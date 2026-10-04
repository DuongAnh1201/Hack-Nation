"""Success rates, success curves, and a 95% bootstrap interval on the speed-up.

Failed runs are never dropped. Primary statistic: restricted mean evaluations to target (each run
capped at the budget, the standard way to average times when some runs never finish). Secondary:
median, where a method miss counts as never reaching the target. The claim is the low end of the interval.
"""

from __future__ import annotations

import math
import random

from bench.search import SearchResult


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[mid])
    low, high = ordered[mid - 1], ordered[mid]
    if math.isinf(low) or math.isinf(high):
        return high
    return 0.5 * (low + high)


def attempted(rows: list[SearchResult]) -> list[SearchResult]:
    return [row for row in rows if row.status != "not_run"]


def _evals_or_inf(row: SearchResult) -> float:
    if row.status == "ok" and row.success and row.evaluations_to_target:
        return float(row.evaluations_to_target)
    return math.inf


def summarize_method(rows: list[SearchResult]) -> dict:
    tried = attempted(rows)
    finished = [row for row in tried if row.status == "ok"]
    successes = [row for row in finished if row.success]
    best = [row.best_p_net for row in finished if row.best_p_net is not None and math.isfinite(row.best_p_net)]
    evals = [_evals_or_inf(row) for row in tried]
    median_evals = median(evals) if evals else None
    walls = [row.wall_seconds for row in finished if row.wall_seconds is not None]
    llm = [row.llm_calls for row in finished if row.llm_calls is not None]
    return {
        "method": rows[0].method if rows else None,
        "runs": len(rows),
        "attempted": len(tried),
        "finished": len(finished),
        "errors": sum(1 for row in tried if row.status == "error"),
        "invalid": sum(1 for row in tried if row.status == "invalid"),
        "successes": len(successes),
        "success_rate": (len(successes) / len(tried)) if tried else None,
        "median_evaluations_to_target": None if median_evals is None or math.isinf(median_evals) else median_evals,
        "median_reached_target": None if median_evals is None else math.isfinite(median_evals),
        "restricted_mean_evaluations": mean([min(value, float(row.budget)) for value, row in zip(evals, tried)])
        if tried
        else None,
        "median_best_p_net": median(best) if best else None,
        "median_wall_seconds": median(walls) if walls else None,
        "median_llm_calls": median([float(value) for value in llm]) if llm else None,
    }


def evaluation_grid(budget: int, points: int = 60) -> list[int]:
    if budget <= points:
        return list(range(1, budget + 1))
    grid = {1, budget}
    for index in range(points):
        grid.add(max(1, round(math.exp(math.log(budget) * index / (points - 1)))))
    return sorted(grid)


def success_curve(rows: list[SearchResult], grid: list[int]) -> list[dict]:
    tried = attempted(rows)
    if not tried:
        return []
    evals = [_evals_or_inf(row) for row in tried]
    return [{"evaluations": point, "share_reached": sum(1 for value in evals if value <= point) / len(evals)} for point in grid]


def best_so_far_curve(rows: list[SearchResult], grid: list[int]) -> list[dict]:
    traces = [row.trajectory for row in attempted(rows) if row.status == "ok" and row.trajectory]
    if not traces:
        return []
    curve = []
    for point in grid:
        values = [trace[min(point, len(trace)) - 1] for trace in traces]
        middle = median(values)
        curve.append({"evaluations": point, "median_best_p_net": middle if math.isfinite(middle) else None})
    return curve


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def speedup_interval(
    baseline: list[SearchResult],
    method: list[SearchResult],
    *,
    budget: int | None = None,
    statistic: str = "restricted_mean",
    seed: int = 0,
    resamples: int = 2000,
) -> dict:
    """Ratio of evaluations to target, baseline over method. Above 1 means `method` reached the target sooner."""
    empty = {
        "statistic": statistic,
        "speedup": None,
        "ci95_low": None,
        "ci95_high": None,
        "claim": None,
        "blocked": None,
        "baseline_runs": 0,
        "method_runs": 0,
        "baseline_misses": 0,
        "method_misses": 0,
        "lower_bound_only": False,
    }
    if statistic not in ("restricted_mean", "median"):
        raise ValueError(f"unknown statistic {statistic}")
    base_rows, method_rows = attempted(baseline), attempted(method)
    if not base_rows or not method_rows:
        return {**empty, "blocked": "no runs to compare"}
    if any(row.status == "invalid" for row in base_rows + method_rows):
        return {**empty, "blocked": "a run bypassed the evaluation counter; fix it before comparing"}
    cap = float(budget if budget is not None else max(row.budget for row in base_rows + method_rows))
    base_evals = [min(_evals_or_inf(row), cap) for row in base_rows]
    raw_method = [_evals_or_inf(row) for row in method_rows]
    if not any(math.isfinite(value) for value in raw_method):
        return {**empty, "blocked": "the method never reached the target"}
    if statistic == "restricted_mean":
        method_evals = [min(value, cap) for value in raw_method]
        center = mean
    else:
        method_evals = raw_method
        center = median

    def ratio(base: list[float], other: list[float]) -> float:
        middle = center(other)
        return 0.0 if math.isinf(middle) else center(base) / middle

    point = ratio(base_evals, method_evals)
    rng = random.Random(seed)
    ratios = sorted(
        ratio(
            [base_evals[rng.randrange(len(base_evals))] for _ in base_evals],
            [method_evals[rng.randrange(len(method_evals))] for _ in method_evals],
        )
        for _ in range(resamples)
    )
    low = ratios[int(0.025 * (len(ratios) - 1))]
    high = ratios[int(0.975 * (len(ratios) - 1))]
    base_misses = sum(1 for row in base_rows if not math.isfinite(_evals_or_inf(row)))
    return {
        "statistic": statistic,
        "speedup": point,
        "ci95_low": low,
        "ci95_high": high,
        "claim": low,
        "blocked": None,
        "baseline_runs": len(base_rows),
        "method_runs": len(method_rows),
        "baseline_misses": base_misses,
        "method_misses": sum(1 for value in raw_method if math.isinf(value)),
        "lower_bound_only": base_misses > 0,
    }
