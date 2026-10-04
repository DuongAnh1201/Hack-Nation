import json
import math
import random

import pytest

from bench.evaluate import EvaluationCache
from bench.example_runner import run_example
from bench.placeholder import placeholder_p_net
from bench.plugins import resolve_objective, simulator_objective
from bench.run_all import ContractError, run_benchmark, to_contract
from bench.search import SearchResult, run_external, run_search
from bench.space import Layer, Stack, sample_random
from bench.summary import speedup_interval, success_curve, summarize_method


def fake_rows(method, evals, budget):
    rows = []
    for seed, value in enumerate(evals):
        hit = value is not None and value <= budget
        rows.append(
            SearchResult(
                method=method,
                seed=seed,
                budget=budget,
                evaluations=value if hit else budget,
                cache_hits=0,
                best_p_net=1.0,
                success=hit,
                evaluations_to_target=value if hit else None,
                best_stack=None,
            )
        )
    return rows


def geometric_draws(rng, mean, n):
    return [max(1, int(rng.expovariate(1 / mean)) + 1) for _ in range(n)]


def test_identical_methods_do_not_show_a_speedup():
    rng = random.Random(7)
    covered = 0
    for _ in range(20):
        a = fake_rows("a", geometric_draws(rng, 200, 10), 5000)
        b = fake_rows("b", geometric_draws(rng, 200, 10), 5000)
        result = speedup_interval(a, b, budget=5000, resamples=500)
        covered += result["ci95_low"] <= 1.0 <= result["ci95_high"]
    assert covered >= 17


def test_a_truly_faster_method_is_detected():
    rng = random.Random(3)
    slow = fake_rows("slow", geometric_draws(rng, 400, 10), 5000)
    fast = fake_rows("fast", geometric_draws(rng, 50, 10), 5000)
    slow = fake_rows("slow", geometric_draws(rng, 400, 100), 5000)
    fast = fake_rows("fast", geometric_draws(rng, 80, 20), 5000)
    result = speedup_interval(slow, fast, budget=5000, resamples=1000)
    assert result["claim"] > 2.0
    assert result["ci95_low"] <= result["speedup"] <= result["ci95_high"]
    assert result["claim"] == result["ci95_low"]


def test_failed_runs_are_not_dropped():
    budget = 1000
    baseline = fake_rows("base", [300] * 10, budget)
    lucky = fake_rows("lucky", [5] + [None] * 9, budget)
    result = speedup_interval(baseline, lucky, budget=budget, statistic="median", resamples=300)
    assert result["speedup"] == 0.0
    assert speedup_interval(baseline, lucky, budget=budget, resamples=300)["speedup"] < 1.0
    assert result["method_misses"] == 9
    assert summarize_method(lucky)["median_reached_target"] is False


def test_baseline_misses_make_the_claim_a_lower_bound():
    budget = 1000
    baseline = fake_rows("base", [None] * 10, budget)
    method = fake_rows("m", [100] * 10, budget)
    result = speedup_interval(baseline, method, budget=budget, resamples=300)
    assert result["lower_bound_only"] is True
    assert result["statistic"] == "restricted_mean"
    assert result["speedup"] == pytest.approx(10.0)


def test_success_curve_counts_misses_as_not_reached():
    rows = fake_rows("m", [10, 20, None, None], 100)
    curve = {point["evaluations"]: point["share_reached"] for point in success_curve(rows, [10, 20, 100])}
    assert curve == {10: 0.25, 20: 0.5, 100: 0.5}


def test_runner_cannot_exceed_the_budget():
    def greedy(*, evaluate, seed, budget, target):
        rng = random.Random(seed)
        while True:
            evaluate(sample_random(rng))

    row = run_external("agent", greedy, placeholder_p_net, seed=0, budget=15, target=None)
    assert row.status == "ok"
    assert row.evaluations == 15
    assert "exceed the budget" in row.reason


def test_runner_must_use_the_shared_space():
    def sneaky(*, evaluate, seed, budget, target):
        evaluate((("HfO2", 100.0),))

    row = run_external("agent", sneaky, placeholder_p_net, seed=0, budget=5, target=None)
    assert row.status == "error"
    with pytest.raises(ValueError):
        Layer("HfO2", 100.0)


def test_bypassing_the_counter_invalidates_the_run_and_blocks_the_claim():
    calls = {"n": 0}

    def counted(stack):
        calls["n"] += 1
        return placeholder_p_net(stack)

    def bypass(*, evaluate, seed, budget, target):
        rng = random.Random(seed)
        evaluate(sample_random(rng))
        counted(sample_random(rng))

    row = run_external(
        "agent", bypass, counted, seed=0, budget=10, target=None, counter=lambda: calls["n"]
    )
    assert row.status == "invalid"
    baseline = [run_search("random", placeholder_p_net, seed=0, budget=10, target=8.0)]
    assert speedup_interval(baseline, [row], budget=10)["blocked"]


def test_trajectory_is_best_so_far_and_one_per_evaluation():
    row = run_search("random", placeholder_p_net, seed=4, budget=40, target=None)
    assert len(row.trajectory) == row.evaluations == 40
    assert all(later >= earlier for earlier, later in zip(row.trajectory, row.trajectory[1:]))
    assert row.trajectory[-1] == row.best_p_net


def test_tpe_respects_the_shared_space():
    row = run_search("tpe", placeholder_p_net, seed=1, budget=30, target=None)
    assert row.evaluations == 30
    assert 1 <= len(row.best_stack["layers"]) <= 5


def test_ga_respects_space_budget_and_seed():
    first = run_search("ga", placeholder_p_net, seed=5, budget=80, target=None)
    again = run_search("ga", placeholder_p_net, seed=5, budget=80, target=None)
    assert first.evaluations == 80
    assert 1 <= len(first.best_stack["layers"]) <= 5
    assert first.best_p_net == again.best_p_net
    assert first.trajectory == again.trajectory


def test_ga_beats_random_on_a_learnable_score():
    ga = [run_search("ga", placeholder_p_net, seed=seed, budget=200, target=None).best_p_net for seed in range(6)]
    rnd = [run_search("random", placeholder_p_net, seed=seed, budget=200, target=None).best_p_net for seed in range(6)]
    assert sum(ga) > sum(rnd)


def test_simulator_adapter_handles_invalid_designs():
    def simulate(materials, thicknesses_nm, substrate="Ag"):
        if len(materials) > 3:
            return {"valid": False, "reason": "too thick", "p_net_w_m2": 99.0}
        return {"valid": True, "p_net_w_m2": 12.5}

    objective = simulator_objective(simulate)
    assert objective(Stack((Layer("SiO2", 100.0),), "Ag")) == 12.5
    four = Stack(tuple(Layer("SiO2", 100.0) for _ in range(4)), "Ag")
    assert objective(four) == -math.inf
    cache = EvaluationCache(objective)
    cache.evaluate(four)
    assert cache.invalid_calls == 1


def test_placeholder_is_never_marked_measured():
    name, _, real = resolve_objective("placeholder")
    assert real is False
    payload = run_benchmark(
        seeds=[0],
        budget=10,
        target=8.0,
        objective_name=name,
        objective=placeholder_p_net,
        measured=real,
    )
    assert payload["measured"] is False
    assert payload["headline"][0].startswith("Not measured")


def test_contract_matches_the_shared_format():
    payload = run_benchmark(
        seeds=[0, 1],
        budget=30,
        target=12.0,
        objective_name="synthetic",
        objective=placeholder_p_net,
        measured=True,
        agent=run_example,
        resamples=100,
    )
    contract = to_contract(payload, "results/benchmark_full.json")
    assert set(contract["methods"]) == {"random", "alternating", "bayes_opt", "genetic_algorithm", "agent_lab"}
    for runs in contract["methods"].values():
        assert len(runs["evals_to_target"]) == len(runs["best_w_m2"]) == 2
        for evals, best in zip(runs["evals_to_target"], runs["best_w_m2"]):
            assert evals is None or 1 <= evals <= 30
            assert math.isfinite(best)
    assert "_fake" not in contract
    json.dumps(contract, allow_nan=False)


def test_contract_refuses_missing_target_and_marks_placeholders():
    payload = run_benchmark(
        seeds=[0], budget=10, target=None, objective_name="p", objective=placeholder_p_net, measured=False
    )
    with pytest.raises(ContractError):
        to_contract(payload)
    payload["target_p_net"] = 8.0
    assert to_contract(payload)["_fake"] is True


def test_full_run_with_a_runner_is_strict_json():
    payload = run_benchmark(
        seeds=[0, 1, 2],
        budget=40,
        target=12.0,
        objective_name="synthetic",
        objective=placeholder_p_net,
        measured=True,
        agent=run_example,
        resamples=200,
    )
    json.dumps(payload, allow_nan=False)
    statuses = {row["method"]: row["status"] for row in payload["rows"]}
    assert statuses["agent"] == "ok"
    assert statuses["ablation"] == "not_run"
    assert payload["curves"]["agent"]["success"]
    assert "vs_tpe" in payload["speedup"]["agent"]
    assert payload["measured"] is True
