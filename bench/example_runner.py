"""Example of the runner interface Person 3 implements. Not an agent and never reported as one.

A runner receives `evaluate`, `seed`, `budget`, and `target`, builds bench.space.Stack designs,
and calls `evaluate(stack)` for every simulation it wants. It may return a dict with `llm_calls`
and anything else worth keeping (for example `record_path`).
"""

from __future__ import annotations

import random

from bench.evaluate import BudgetExhausted
from bench.space import THICKNESS_NM_MAX, THICKNESS_NM_MIN, Layer, Stack, sample_alternating


def run_example(*, evaluate, seed: int, budget: int, target: float | None) -> dict:
    rng = random.Random(seed)
    best_stack, best_value = None, None
    used = 0
    try:
        while used < budget:
            if best_stack is None or rng.random() < 0.3:
                stack = sample_alternating(rng)
            else:
                stack = _nudge(best_stack, rng)
            value = evaluate(stack)
            used += 1
            if best_value is None or value > best_value:
                best_stack, best_value = stack, value
            if target is not None and value >= target:
                break
    except BudgetExhausted:
        pass
    return {"llm_calls": 0, "note": "example runner, not an agent"}


def _nudge(stack: Stack, rng: random.Random) -> Stack:
    layers = []
    for layer in stack.layers:
        thickness = min(THICKNESS_NM_MAX, max(THICKNESS_NM_MIN, layer.thickness_nm * rng.uniform(0.7, 1.4)))
        layers.append(Layer(layer.material, thickness))
    return Stack(tuple(layers), stack.metal)
