"""Object and celestial body presets."""

import math
from typing import Dict, Any
from physics_lab.physics.models import ProjectileParams


OBJECT_PRESETS: Dict[str, Dict[str, float]] = {
    "baseball": {
        "mass": 0.145,
        "cross_section_area": 0.0042,
        "drag_coefficient": 0.35,
    },
    "shot_put": {
        "mass": 7.26,
        "cross_section_area": 0.0104,
        "drag_coefficient": 0.47,
    },
    "ping_pong_ball": {
        "mass": 0.0027,
        "cross_section_area": 0.00126,
        "drag_coefficient": 0.5,
    },
    "beach_ball": {
        "mass": 0.1,
        "cross_section_area": 0.0707,
        "drag_coefficient": 0.47,
    },
    "bowling_ball": {
        "mass": 6.0,
        "cross_section_area": 0.0366,
        "drag_coefficient": 0.47,
    },
}

PLANET_PRESETS: Dict[str, Dict[str, float]] = {
    "earth": {
        "gravity": 9.81,
        "air_density": 1.225,
    },
    "mars": {
        "gravity": 3.73,
        "air_density": 0.016,
    },
    "venus": {
        "gravity": 8.87,
        "air_density": 65.0,
    },
}


def preset(object_name: str, planet_name: str = "earth", **overrides) -> ProjectileParams:
    """Create ProjectileParams combining an object preset and a planet preset."""
    obj_key = object_name.lower().replace(" ", "_")
    planet_key = planet_name.lower().replace(" ", "_")

    if obj_key not in OBJECT_PRESETS:
        raise ValueError(f"Unknown object preset '{object_name}'. Available: {list(OBJECT_PRESETS.keys())}")
    if planet_key not in PLANET_PRESETS:
        raise ValueError(f"Unknown planet preset '{planet_name}'. Available: {list(PLANET_PRESETS.keys())}")

    merged: Dict[str, Any] = {}
    merged.update(OBJECT_PRESETS[obj_key])
    merged.update(PLANET_PRESETS[planet_key])
    merged.update(overrides)

    return ProjectileParams.from_dict(merged)


def velocity_for_beta(params: ProjectileParams, beta: float) -> float:
    """Compute required launch velocity v0 for a target beta group: v0 = sqrt(2 * m * g * beta / (rho * Cd * A))."""
    if beta <= 0:
        raise ValueError("beta must be > 0")
    if params.drag_coefficient <= 0 or params.air_density <= 0:
        raise ValueError("Cannot calculate beta for vacuum conditions (Cd or air_density is zero)")
    numerator = 2.0 * params.mass * params.gravity * beta
    denominator = params.air_density * params.drag_coefficient * params.cross_section_area
    return math.sqrt(numerator / denominator)
