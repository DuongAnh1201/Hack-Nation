"""Simulation execution engine with numerical verification."""

import math
from typing import Optional
from physics_lab.physics.models import ProjectileParams, SimulationResult
from physics_lab.physics.rk4 import integrate_trajectory
from physics_lab.physics.vacuum import vacuum_range, vacuum_flight_time, vacuum_max_height


def simulate(
    params: ProjectileParams,
    record_trajectory: bool = False,
    max_frames: int = 240,
    verify_convergence: bool = True,
) -> SimulationResult:
    """Simulate a projectile trajectory with RK4 integration and step-doubling verification."""
    m_base, frames = integrate_trajectory(
        params,
        step_multiplier=1.0,
        record_trajectory=record_trajectory,
        max_frames=max_frames,
    )

    numerical_info = {
        "step_size_dt": m_base["dt"],
        "steps_taken": m_base["steps"],
        "energy_error_J": m_base["energy_error_J"],
    }

    # Step-doubling check if drag is present and verification is requested
    if verify_convergence and params.drag_coefficient > 0 and params.air_density > 0:
        m_coarse, _ = integrate_trajectory(params, step_multiplier=2.0, record_trajectory=False)
        range_diff = abs(m_base["range_m"] - m_coarse["range_m"])
        rel_error = range_diff / max(1e-9, abs(m_base["range_m"]))
        numerical_info["step_doubling_range_diff_m"] = range_diff
        numerical_info["step_doubling_rel_error"] = rel_error
    elif params.drag_coefficient == 0.0 or params.air_density == 0.0:
        # Vacuum exact comparison
        exact_r = vacuum_range(params)
        exact_t = vacuum_flight_time(params)
        exact_h = vacuum_max_height(params)
        numerical_info["vacuum_exact_range_m"] = exact_r
        numerical_info["vacuum_range_diff_m"] = abs(m_base["range_m"] - exact_r)
        numerical_info["vacuum_flight_time_diff_s"] = abs(m_base["flight_time_s"] - exact_t)
        numerical_info["vacuum_max_height_diff_m"] = abs(m_base["max_height_m"] - exact_h)

    return SimulationResult(
        params=params,
        range_m=m_base["range_m"],
        flight_time_s=m_base["flight_time_s"],
        max_height_m=m_base["max_height_m"],
        time_to_apex_s=m_base["time_to_apex_s"],
        impact_speed_m_s=m_base["impact_speed_m_s"],
        impact_angle_deg=m_base["impact_angle_deg"],
        energy_initial_J=m_base["energy_initial_J"],
        energy_final_J=m_base["energy_final_J"],
        energy_lost_to_drag_J=m_base["energy_lost_to_drag_J"],
        energy_error_J=m_base["energy_error_J"],
        beta=m_base["beta"],
        eta=m_base["eta"],
        numerical=numerical_info,
        trajectory=frames,
    )
