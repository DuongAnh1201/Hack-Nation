"""Analytical closed-form solutions for projectile motion in vacuum."""

import math
from typing import Dict
from physics_lab.physics.models import ProjectileParams


def vacuum_range(params: ProjectileParams) -> float:
    """Analytical range in vacuum: R = (v0^2 / g) * (sin(theta) * cos(theta) + cos(theta) * sqrt(sin^2(theta) + 2*g*h0/v0^2))."""
    theta_rad = math.radians(params.launch_angle)
    v0 = params.initial_velocity
    g = params.gravity
    h0 = params.launch_height

    sin_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)

    if h0 == 0.0:
        return (v0 ** 2) * math.sin(2.0 * theta_rad) / g

    term = math.sqrt(sin_t ** 2 + 2.0 * g * h0 / (v0 ** 2))
    return (v0 ** 2 / g) * cos_t * (sin_t + term)


def vacuum_optimal_angle_deg(params: ProjectileParams) -> float:
    """Optimal launch angle in vacuum. 45 deg if h0 == 0; arcsin(1 / sqrt(2 + 2*g*h0/v0^2)) if h0 > 0."""
    if params.launch_height == 0.0:
        return 45.0
    v0 = params.initial_velocity
    g = params.gravity
    h0 = params.launch_height
    # Lichtenberg & Wills 1978: sin(theta*) = 1 / sqrt(2 + 2*g*h0/v0^2)
    sin_theta = 1.0 / math.sqrt(2.0 + (2.0 * g * h0) / (v0 ** 2))
    return math.degrees(math.asin(sin_theta))


def vacuum_flight_time(params: ProjectileParams) -> float:
    """Flight time in vacuum."""
    theta_rad = math.radians(params.launch_angle)
    v0 = params.initial_velocity
    g = params.gravity
    h0 = params.launch_height
    vy0 = v0 * math.sin(theta_rad)
    return (vy0 + math.sqrt(vy0 ** 2 + 2.0 * g * h0)) / g


def vacuum_max_height(params: ProjectileParams) -> float:
    """Maximum height above ground in vacuum."""
    theta_rad = math.radians(params.launch_angle)
    v0 = params.initial_velocity
    g = params.gravity
    h0 = params.launch_height
    vy0 = v0 * math.sin(theta_rad)
    return h0 + (vy0 ** 2) / (2.0 * g)
