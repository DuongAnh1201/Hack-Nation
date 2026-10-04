"""Random search, alternating-stack search, Optuna TPE, a genetic algorithm, and external (agent) runs on one space."""

from __future__ import annotations

import math
import random
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field

from bench.evaluate import BudgetExhausted, EvaluationCache, Objective
from bench.space import (
    MATERIALS,
    MAX_LAYERS,
    METALS,
    MIN_LAYERS,
    THICKNESS_NM_MAX,
    THICKNESS_NM_MIN,
    Layer,
    Stack,
    sample_alternating,
    sample_random,
)

MAX_ATTEMPTS_PER_EVALUATION = 30
BASELINES = ("random", "alternating", "tpe", "ga")
Sampler = Callable[[random.Random], Stack]
Evaluate = Callable[[Stack], float]
ExternalRunner = Callable[..., "dict | None"]
EvaluationCounter = Callable[[], int]


@dataclass(frozen=True)
class SearchResult:
    method: str
    seed: int
    budget: int
    evaluations: int
    cache_hits: int
    best_p_net: float | None
    success: bool
    evaluations_to_target: int | None
    best_stack: dict | None
    status: str = "ok"
    reason: str | None = None
    invalid_evaluations: int = 0
    wall_seconds: float | None = None
    llm_calls: int | None = None
    trajectory: list[float] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "seed": self.seed,
            "status": self.status,
            "reason": self.reason,
            "budget": self.budget,
            "evaluations": self.evaluations,
            "cache_hits": self.cache_hits,
            "invalid_evaluations": self.invalid_evaluations,
            "best_p_net": _finite_or_none(self.best_p_net),
            "success": self.success,
            "evaluations_to_target": self.evaluations_to_target,
            "best_stack": self.best_stack,
            "wall_seconds": self.wall_seconds,
            "llm_calls": self.llm_calls,
            "trajectory": [_finite_or_none(value) for value in self.trajectory],
            "extra": self.extra,
        }


def _finite_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return value


def run_search(
    method: str,
    objective: Objective,
    *,
    seed: int,
    budget: int,
    target: float | None = None,
) -> SearchResult:
    if budget < 1:
        raise ValueError("budget is the number of simulator calls and must be at least 1")
    if method == "random":
        return _sampled(method, sample_random, objective, seed=seed, budget=budget, target=target)
    if method == "alternating":
        return _sampled(method, sample_alternating, objective, seed=seed, budget=budget, target=target)
    if method == "tpe":
        return _tpe(objective, seed=seed, budget=budget, target=target)
    if method == "ga":
        return _ga(objective, seed=seed, budget=budget, target=target)
    raise ValueError(f"unknown method {method}")


def not_run(method: str, seed: int, budget: int, reason: str) -> SearchResult:
    return SearchResult(
        method=method,
        seed=seed,
        budget=budget,
        evaluations=0,
        cache_hits=0,
        best_p_net=None,
        success=False,
        evaluations_to_target=None,
        best_stack=None,
        status="not_run",
        reason=reason,
    )


def run_external(
    method: str,
    runner: ExternalRunner,
    objective: Objective,
    *,
    seed: int,
    budget: int,
    target: float | None,
    counter: EvaluationCounter | None = None,
) -> SearchResult:
    cache = EvaluationCache(objective, budget=budget)
    best: dict = {"value": None, "stack": None}

    def evaluate(stack: Stack) -> float:
        if not isinstance(stack, Stack):
            raise TypeError("evaluate() takes a bench.space.Stack so every method shares one search space")
        value = cache.evaluate(stack)
        if best["value"] is None or value > best["value"]:
            best["value"] = value
            best["stack"] = stack
        return value

    counter_start = counter() if counter is not None else None
    start = time.perf_counter()
    status, reason, info = "ok", None, {}
    try:
        info = runner(evaluate=evaluate, seed=seed, budget=budget, target=target) or {}
    except BudgetExhausted:
        reason = "runner tried to exceed the budget; extra calls were refused"
    except Exception as exc:
        status, reason = "error", f"{type(exc).__name__}: {exc}"
    wall = time.perf_counter() - start

    if counter is not None:
        spent = counter() - counter_start
        if spent != cache.unique_calls:
            status = "invalid"
            reason = (
                f"simulator ran {spent} times but only {cache.unique_calls} went through the bench; "
                "some evaluations bypassed the counter, so this run cannot be compared"
            )

    llm_calls = info.get("llm_calls") if isinstance(info, dict) else None
    extra = {key: value for key, value in info.items() if key != "llm_calls"} if isinstance(info, dict) else {}
    return _result(
        method,
        seed,
        budget,
        cache,
        best["value"],
        best["stack"],
        target,
        wall,
        status=status,
        reason=reason,
        llm_calls=llm_calls,
        extra=extra,
    )


def _sampled(
    method: str,
    sample: Sampler,
    objective: Objective,
    *,
    seed: int,
    budget: int,
    target: float | None,
) -> SearchResult:
    rng = random.Random(seed)
    cache = EvaluationCache(objective, budget=budget)
    best_value: float | None = None
    best_stack: Stack | None = None
    attempts = 0
    attempt_limit = budget * MAX_ATTEMPTS_PER_EVALUATION
    start = time.perf_counter()

    while cache.unique_calls < budget and attempts < attempt_limit:
        attempts += 1
        before = cache.unique_calls
        stack = sample(rng)
        value = cache.evaluate(stack)
        if cache.unique_calls == before:
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_stack = stack
        if target is not None and value >= target:
            break

    return _result(method, seed, budget, cache, best_value, best_stack, target, time.perf_counter() - start)


def _tpe(
    objective: Objective,
    *,
    seed: int,
    budget: int,
    target: float | None,
) -> SearchResult:
    try:
        import optuna
    except ImportError as exc:
        raise RuntimeError("Bayesian optimization needs optuna. pip install optuna") from exc

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sampler = optuna.samplers.TPESampler(
            seed=seed,
            multivariate=True,
            group=True,
            n_startup_trials=min(20, max(1, budget // 5)),
        )
    study = optuna.create_study(direction="maximize", sampler=sampler)
    cache = EvaluationCache(objective, budget=budget)
    best_value: float | None = None
    best_stack: Stack | None = None
    attempts = 0
    attempt_limit = budget * MAX_ATTEMPTS_PER_EVALUATION
    start = time.perf_counter()

    while cache.unique_calls < budget and attempts < attempt_limit:
        attempts += 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            trial = study.ask()
            stack = _suggest(trial)
        before = cache.unique_calls
        value = cache.evaluate(stack)
        study.tell(trial, value if math.isfinite(value) else -1e9)
        if cache.unique_calls == before:
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_stack = stack
        if target is not None and value >= target:
            break

    return _result("tpe", seed, budget, cache, best_value, best_stack, target, time.perf_counter() - start)


GA_POPULATION = 24
GA_ELITE = 2
GA_TOURNAMENT = 3
GA_MUTATION = 0.3


def _ga(
    objective: Objective,
    *,
    seed: int,
    budget: int,
    target: float | None,
) -> SearchResult:
    rng = random.Random(seed)
    cache = EvaluationCache(objective, budget=budget)
    best: dict = {"value": None, "stack": None}
    start = time.perf_counter()
    attempts = 0
    attempt_limit = budget * MAX_ATTEMPTS_PER_EVALUATION

    def score(stack: Stack) -> float | None:
        before = cache.unique_calls
        if cache.unique_calls >= budget and stack.key() not in cache._values:
            return None
        value = cache.evaluate(stack)
        if cache.unique_calls > before and (best["value"] is None or value > best["value"]):
            best["value"], best["stack"] = value, stack
        return value

    def reached() -> bool:
        return target is not None and best["value"] is not None and best["value"] >= target

    population: list[tuple[float, Stack]] = []
    while len(population) < min(GA_POPULATION, budget) and attempts < attempt_limit and not reached():
        attempts += 1
        stack = sample_random(rng)
        value = score(stack)
        if value is not None:
            population.append((value, stack))

    while cache.unique_calls < budget and attempts < attempt_limit and not reached() and population:
        population.sort(key=lambda item: item[0], reverse=True)
        children = population[:GA_ELITE]
        while len(children) < GA_POPULATION and cache.unique_calls < budget and attempts < attempt_limit:
            attempts += 1
            child = _mutate(_crossover(_tournament(population, rng), _tournament(population, rng), rng), rng)
            value = score(child)
            if value is None:
                break
            children.append((value, child))
            if reached():
                break
        population = children

    return _result("ga", seed, budget, cache, best["value"], best["stack"], target, time.perf_counter() - start)


def _tournament(population: list[tuple[float, Stack]], rng: random.Random) -> Stack:
    picks = [population[rng.randrange(len(population))] for _ in range(GA_TOURNAMENT)]
    return max(picks, key=lambda item: item[0])[1]


def _crossover(a: Stack, b: Stack, rng: random.Random) -> Stack:
    cut_a = rng.randint(0, len(a.layers))
    cut_b = rng.randint(0, len(b.layers))
    layers = (a.layers[:cut_a] + b.layers[cut_b:])[:MAX_LAYERS]
    if len(layers) < MIN_LAYERS:
        layers = a.layers
    return Stack(tuple(layers), rng.choice((a.metal, b.metal)))


def _mutate(stack: Stack, rng: random.Random) -> Stack:
    layers = list(stack.layers)
    metal = stack.metal
    for index, layer in enumerate(layers):
        if rng.random() < GA_MUTATION:
            factor = math.exp(rng.gauss(0.0, 0.3))
            thickness = min(THICKNESS_NM_MAX, max(THICKNESS_NM_MIN, layer.thickness_nm * factor))
            layers[index] = Layer(layer.material, thickness)
        if rng.random() < GA_MUTATION / 3:
            layers[index] = Layer(rng.choice(MATERIALS), layers[index].thickness_nm)
    if rng.random() < GA_MUTATION / 3 and len(layers) < MAX_LAYERS:
        layers.insert(
            rng.randint(0, len(layers)),
            Layer(rng.choice(MATERIALS), math.exp(rng.uniform(math.log(THICKNESS_NM_MIN), math.log(THICKNESS_NM_MAX)))),
        )
    if rng.random() < GA_MUTATION / 3 and len(layers) > MIN_LAYERS:
        layers.pop(rng.randrange(len(layers)))
    if rng.random() < GA_MUTATION / 6:
        metal = rng.choice(METALS)
    return Stack(tuple(layers), metal)


def _suggest(trial) -> Stack:
    n_layers = trial.suggest_int("n_layers", MIN_LAYERS, MAX_LAYERS)
    metal = trial.suggest_categorical("metal", list(METALS))
    layers = []
    for index in range(n_layers):
        material = trial.suggest_categorical(f"material_{index}", list(MATERIALS))
        thickness = trial.suggest_float(
            f"thickness_nm_{index}",
            THICKNESS_NM_MIN,
            THICKNESS_NM_MAX,
            log=True,
        )
        layers.append(Layer(material, thickness))
    return Stack(tuple(layers), metal)


def _result(
    method: str,
    seed: int,
    budget: int,
    cache: EvaluationCache,
    best_value: float | None,
    best_stack: Stack | None,
    target: float | None,
    wall_seconds: float,
    *,
    status: str = "ok",
    reason: str | None = None,
    llm_calls: int | None = None,
    extra: dict | None = None,
) -> SearchResult:
    hit_at = cache.first_hit(target)
    success = status == "ok" and hit_at is not None
    return SearchResult(
        method=method,
        seed=seed,
        budget=budget,
        evaluations=cache.unique_calls,
        cache_hits=cache.cache_hits,
        best_p_net=best_value,
        success=success,
        evaluations_to_target=hit_at if success else None,
        best_stack=None if best_stack is None else best_stack.to_dict(),
        status=status,
        reason=reason,
        invalid_evaluations=cache.invalid_calls,
        wall_seconds=round(wall_seconds, 4),
        llm_calls=llm_calls,
        trajectory=list(cache.best_so_far),
        extra=extra or {},
    )
