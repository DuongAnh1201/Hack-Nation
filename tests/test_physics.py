"""Tests for physics simulation accuracy, analytical controls and numerical energy conservation."""

import pytest
import math
from physics_lab.physics.models import ProjectileParams
from physics_lab.physics.engine import simulate
from physics_lab.physics.vacuum import vacuum_range, vacuum_flight_time, vacuum_max_height, vacuum_optimal_angle_deg
from physics_lab.physics.presets import preset, velocity_for_beta


def test_vacuum_analytic_equivalence():
    """Verify RK4 numerical simulation matches closed-form vacuum equations to high precision."""
    params = ProjectileParams(initial_velocity=35.0, launch_angle=45.0, drag_coefficient=0.0)
    res = simulate(params, verify_convergence=False)

    exact_r = vacuum_range(params)
    exact_t = vacuum_flight_time(params)
    exact_h = vacuum_max_height(params)

    assert abs(res.range_m - exact_r) < 1e-10
    assert abs(res.flight_time_s - exact_t) < 1e-10
    assert abs(res.max_height_m - exact_h) < 1e-10


def test_energy_conservation_under_drag():
    """Verify energy balance: Initial Energy = Final Kinetic Energy + Drag Dissipated Work."""
    params = ProjectileParams(
        initial_velocity=45.0,
        launch_angle=40.0,
        drag_coefficient=0.45,
        air_density=1.225,
        mass=0.2,
        cross_section_area=0.005,
    )
    res = simulate(params, record_trajectory=True)

    # Relative energy error should be under 1e-7
    rel_error = res.energy_error_J / res.energy_initial_J
    assert rel_error < 1e-7


def test_step_doubling_convergence():
    """Verify numerical convergence via step-doubling check."""
    params = ProjectileParams(initial_velocity=50.0, launch_angle=42.0, drag_coefficient=0.35)
    res = simulate(params, verify_convergence=True)

    assert "step_doubling_rel_error" in res.numerical
    assert res.numerical["step_doubling_rel_error"] < 1e-6


def test_parameter_validation():
    """Verify ProjectileParams rejects physical impossibilities."""
    with pytest.raises(ValueError):
        ProjectileParams(initial_velocity=-10.0)

    with pytest.raises(ValueError):
        ProjectileParams(launch_angle=95.0)

    with pytest.raises(ValueError):
        ProjectileParams(mass=0.0)

    with pytest.raises(ValueError):
        ProjectileParams.from_dict({"initial_velocity": 30.0, "non_existent_key": 123})


def test_presets_and_beta_calculation():
    """Verify object and celestial presets and beta velocity calculations."""
    earth_bb = preset("baseball", "earth")
    assert earth_bb.gravity == 9.81
    assert earth_bb.mass == 0.145

    v_target = velocity_for_beta(earth_bb, 2.0)
    assert 55.0 < v_target < 58.0

    earth_bb.initial_velocity = v_target
    assert abs(earth_bb.beta - 2.0) < 1e-5
