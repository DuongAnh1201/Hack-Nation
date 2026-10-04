"""Plug points for Person 4's simulator and Person 3's agent lab, loaded by dotted path."""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable

from bench.evaluate import Objective
from bench.placeholder import PLACEHOLDER_NAME, placeholder_p_net
from bench.space import Stack

PLACEHOLDER_KEY = "placeholder"


def load(path: str) -> Callable:
    module_name, sep, attr = path.partition(":")
    if not sep:
        module_name, _, attr = path.rpartition(".")
    if not module_name or not attr:
        raise ValueError(f"expected 'package.module:function', got {path!r}")
    return getattr(importlib.import_module(module_name), attr)


def simulator_objective(simulate: Callable) -> Objective:
    def objective(stack: Stack) -> float:
        out = simulate(
            [layer.material for layer in stack.layers],
            [layer.thickness_nm for layer in stack.layers],
            substrate=stack.metal,
        )
        if isinstance(out, (int, float)):
            return float(out)
        if not out.get("valid", True):
            return -math.inf
        value = out.get("p_net_w_m2")
        return -math.inf if value is None else float(value)

    return objective


def resolve_objective(spec: str) -> tuple[str, Objective, bool]:
    if spec in (PLACEHOLDER_KEY, PLACEHOLDER_NAME):
        return PLACEHOLDER_NAME, placeholder_p_net, False
    return spec, simulator_objective(load(spec)), True
