import random

from bench.evaluate import EvaluationCache
from bench.placeholder import placeholder_p_net
from bench.run_all import run_benchmark
from bench.search import run_search
from bench.space import Layer, Stack, is_alternating, sample_alternating, sample_random
from bench.summary import median, speedup_interval


def test_random_and_alternating_share_the_bounds():
    rng = random.Random(1)
    for sample in (sample_random, sample_alternating):
        stack = sample(rng)
        assert 1 <= len(stack.layers) <= 5
        assert stack.metal in ("Ag", "Al")


def test_alternating_prior_is_silver_and_paired():
    stack = sample_alternating(random.Random(2))
    assert stack.metal == "Ag"
    assert is_alternating(stack)


def test_repeat_does_not_spend_another_evaluation():
    calls = {"n": 0}

    def objective(stack: Stack) -> float:
        calls["n"] += 1
        return 1.0

    cache = EvaluationCache(objective)
    stack = sample_random(random.Random(0))
    assert cache.evaluate(stack) == 1.0
    assert cache.evaluate(stack) == 1.0
    assert cache.unique_calls == 1
    assert cache.cache_hits == 1
    assert calls["n"] == 1


def test_search_stops_when_the_target_is_hit():
    result = run_search("alternating", placeholder_p_net, seed=0, budget=30, target=8.0)
    assert result.success
    assert result.evaluations_to_target is not None
    assert result.evaluations_to_target <= result.evaluations
    assert result.evaluations < 30


def test_rounded_nanometer_is_the_same_design():
    stack = Stack((Layer("SiO2", 100.2),), "Ag")
    nudged = Stack((Layer("SiO2", 100.4),), "Ag")
    assert stack.key() == nudged.key()


def test_agent_rows_stay_empty():
    payload = run_benchmark(
        seeds=[0],
        budget=8,
        target=None,
        objective_name="bench.placeholder.placeholder_p_net",
        objective=placeholder_p_net,
        measured=False,
    )
    assert payload["measured"] is False
    statuses = {row["method"]: row["status"] for row in payload["rows"]}
    assert statuses["random"] == "ok"
    assert statuses["alternating"] == "ok"
    assert statuses["agent"] == "not_run"
    assert statuses["ablation"] == "not_run"
    assert payload["speedup"]["agent"]["vs_random"]["claim"] is None


def test_claim_is_the_low_end_of_the_interval():
    faster = [
        run_search("alternating", placeholder_p_net, seed=seed, budget=25, target=8.0) for seed in range(8)
    ]
    slower = [
        run_search("random", placeholder_p_net, seed=seed, budget=25, target=8.0) for seed in range(8)
    ]
    interval = speedup_interval(slower, faster, seed=0, resamples=400)
    assert interval["speedup"] is not None
    assert interval["claim"] == interval["ci95_low"]
    assert interval["ci95_low"] <= interval["speedup"] <= interval["ci95_high"]
    assert median([1, 2, 3]) == 2
