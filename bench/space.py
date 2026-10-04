"""Shared coating search space.

Every baseline samples this same description. Person 4's optimizer and
Person 3's agent should use these bounds too, so the comparison stays fair.

Thickness limits are provisional until Person 4 confirms them.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

MATERIALS = ("SiO2", "Al2O3", "Si3N4", "TiO2", "MgF2")
HIGH_INDEX = ("TiO2", "Si3N4")
LOW_INDEX = ("SiO2", "MgF2")
METALS = ("Ag", "Al")

MIN_LAYERS = 1
MAX_LAYERS = 5

# Provisional. Log-uniform: optical thickness is a ratio, not a linear gap.
THICKNESS_NM_MIN = 10.0
THICKNESS_NM_MAX = 1000.0


@dataclass(frozen=True)
class Layer:
    material: str
    thickness_nm: float

    def __post_init__(self) -> None:
        if self.material not in MATERIALS:
            raise ValueError(f"unknown material {self.material}")
        if not THICKNESS_NM_MIN <= self.thickness_nm <= THICKNESS_NM_MAX:
            raise ValueError(f"thickness {self.thickness_nm} nm is outside the shared bounds")


@dataclass(frozen=True)
class Stack:
    layers: tuple[Layer, ...]
    metal: str

    def __post_init__(self) -> None:
        if self.metal not in METALS:
            raise ValueError(f"unknown metal {self.metal}")
        if not MIN_LAYERS <= len(self.layers) <= MAX_LAYERS:
            raise ValueError("a stack must have 1 to 5 layers")

    def key(self) -> tuple:
        """Cache key. Thicknesses rounded to 1 nm are the same design."""
        rounded = tuple((layer.material, round(layer.thickness_nm)) for layer in self.layers)
        return (self.metal, rounded)

    def to_dict(self) -> dict:
        return {
            "metal": self.metal,
            "layers": [
                {"material": layer.material, "thickness_nm": round(layer.thickness_nm, 3)}
                for layer in self.layers
            ],
        }


def _log_uniform(rng: random.Random, low: float, high: float) -> float:
    return math.exp(rng.uniform(math.log(low), math.log(high)))


def sample_random(rng: random.Random) -> Stack:
    n_layers = rng.randint(MIN_LAYERS, MAX_LAYERS)
    layers = tuple(
        Layer(rng.choice(MATERIALS), _log_uniform(rng, THICKNESS_NM_MIN, THICKNESS_NM_MAX))
        for _ in range(n_layers)
    )
    return Stack(layers, rng.choice(METALS))


def sample_alternating(rng: random.Random) -> Stack:
    """High-index / low-index pairs on silver. The usual radiative-cooling pattern."""
    n_layers = rng.randint(MIN_LAYERS, MAX_LAYERS)
    start_high = rng.random() < 0.5
    layers = []
    for index in range(n_layers):
        want_high = (index % 2 == 0) == start_high
        pool = HIGH_INDEX if want_high else LOW_INDEX
        layers.append(Layer(rng.choice(pool), _log_uniform(rng, THICKNESS_NM_MIN, THICKNESS_NM_MAX)))
    return Stack(tuple(layers), "Ag")


def is_alternating(stack: Stack) -> bool:
    if stack.metal != "Ag" or not stack.layers:
        return False
    first_high = stack.layers[0].material in HIGH_INDEX
    for index, layer in enumerate(stack.layers):
        want_high = first_high if index % 2 == 0 else not first_high
        pool = HIGH_INDEX if want_high else LOW_INDEX
        if layer.material not in pool:
            return False
    return True
