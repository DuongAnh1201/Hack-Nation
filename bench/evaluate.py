"""Evaluation counter. A repeated design does not spend another simulation."""

from __future__ import annotations

import math
from collections.abc import Callable

from bench.space import Stack

Objective = Callable[[Stack], float]


class BudgetExhausted(RuntimeError):
    pass


class EvaluationCache:
    def __init__(self, objective: Objective, budget: int | None = None) -> None:
        self._objective = objective
        self._values: dict[tuple, float] = {}
        self.budget = budget
        self.unique_calls = 0
        self.cache_hits = 0
        self.invalid_calls = 0
        self.best_so_far: list[float] = []

    def evaluate(self, stack: Stack) -> float:
        key = stack.key()
        if key in self._values:
            self.cache_hits += 1
            return self._values[key]
        if self.budget is not None and self.unique_calls >= self.budget:
            raise BudgetExhausted(f"budget of {self.budget} simulator calls is used up")
        value = float(self._objective(stack))
        if math.isnan(value):
            value = -math.inf
        if value == -math.inf:
            self.invalid_calls += 1
        self._values[key] = value
        self.unique_calls += 1
        previous = self.best_so_far[-1] if self.best_so_far else -math.inf
        self.best_so_far.append(max(previous, value))
        return value

    def first_hit(self, target: float | None) -> int | None:
        if target is None:
            return None
        for index, best in enumerate(self.best_so_far, start=1):
            if best >= target:
                return index
        return None
