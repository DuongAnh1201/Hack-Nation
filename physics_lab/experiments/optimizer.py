"""Adaptive launch angle optimizer using bracket search and golden-section refinement."""

import math
from typing import Dict, Any, List, Tuple, Optional
from physics_lab.physics.models import ProjectileParams, SimulationResult
from physics_lab.physics.engine import simulate
from physics_lab.physics.vacuum import vacuum_optimal_angle_deg


GOLDEN_RATIO = (math.sqrt(5.0) - 1.0) / 2.0  # ~0.6180339887


def optimize_angle(
    base_params: ProjectileParams,
    tol_deg: float = 0.005,
    prior_deg: Optional[float] = None,
) -> Dict[str, Any]:
    """Find range-maximizing launch angle theta* using adaptive bracketing + golden-section search."""
    search_trace: List[Dict[str, Any]] = []
    eval_cache: Dict[float, SimulationResult] = {}

    if prior_deg is None:
        prior_deg = vacuum_optimal_angle_deg(base_params)

    def eval_angle(angle: float, note: str) -> SimulationResult:
        # Round angle to 4 decimal places for precision and cache
        r_angle = round(angle, 4)
        if r_angle in eval_cache:
            return eval_cache[r_angle]

        p = ProjectileParams(
            initial_velocity=base_params.initial_velocity,
            launch_angle=r_angle,
            mass=base_params.mass,
            gravity=base_params.gravity,
            drag_coefficient=base_params.drag_coefficient,
            cross_section_area=base_params.cross_section_area,
            air_density=base_params.air_density,
            launch_height=base_params.launch_height,
        )
        sim_res = simulate(p, verify_convergence=False)
        eval_cache[r_angle] = sim_res
        search_trace.append({
            "angle_deg": r_angle,
            "range_m": sim_res.range_m,
            "note": note,
        })
        return sim_res

    # 1. Start at prior
    r_prior = eval_angle(prior_deg, "start at prior (vacuum optimum)")

    # 2. Step 5 deg below prior
    step_size = 5.0
    a_below = max(0.5, prior_deg - step_size)
    r_below = eval_angle(a_below, f"probe {step_size:.0f} deg below the prior")

    bracket_left: float
    bracket_mid: float
    bracket_right: float

    if r_below.range_m > r_prior.range_m:
        # Drag pulls optimum downwards: probe further down
        prev_a = a_below
        prev_r = r_below
        while True:
            next_a = max(0.5, prev_a - step_size)
            r_next = eval_angle(next_a, f"R({prev_a:.0f}) > R({prev_a+step_size:.0f}): optimum is below {prev_a+step_size:.0f} deg; probe {next_a:.0f}")
            if r_next.range_m <= prev_r.range_m or next_a <= 0.5:
                bracket_left = next_a
                bracket_mid = prev_a
                bracket_right = prev_a + step_size
                break
            prev_a = next_a
            prev_r = r_next
    else:
        # Probe above prior
        a_above = min(89.5, prior_deg + step_size)
        r_above = eval_angle(a_above, f"R({a_below:.0f}) <= R({prior_deg:.0f}); probe {step_size:.0f} deg above; bracket found [{a_below:.0f}, {a_above:.0f}]")
        if r_above.range_m > r_prior.range_m:
            prev_a = a_above
            prev_r = r_above
            while True:
                next_a = min(89.5, prev_a + step_size)
                r_next = eval_angle(next_a, f"probe {next_a:.0f}")
                if r_next.range_m <= prev_r.range_m or next_a >= 89.5:
                    bracket_left = prev_a - step_size
                    bracket_mid = prev_a
                    bracket_right = next_a
                    break
                prev_a = next_a
                prev_r = r_next
        else:
            # Peak is bracketed between a_below and a_above with prior in between
            bracket_left = a_below
            bracket_mid = prior_deg
            bracket_right = a_above

    # 3. Golden Section Search inside [bracket_left, bracket_right]
    a = min(bracket_left, bracket_right)
    b = max(bracket_left, bracket_right)

    # Initial interior points
    c = b - GOLDEN_RATIO * (b - a)
    d = a + GOLDEN_RATIO * (b - a)

    rc = eval_angle(c, f"golden-section refine in [{a:.1f}, {b:.1f}]")
    rd = eval_angle(d, f"golden-section refine in [{a:.1f}, {b:.1f}]")

    while (b - a) > (2.0 * tol_deg):
        if rc.range_m > rd.range_m:
            b = d
            d = c
            rd = rc
            c = b - GOLDEN_RATIO * (b - a)
            rc = eval_angle(c, f"narrow bracket to [{a:.2f}, {b:.2f}]")
        else:
            a = c
            c = d
            rc = rd
            d = a + GOLDEN_RATIO * (b - a)
            rd = eval_angle(d, f"narrow bracket to [{a:.2f}, {b:.2f}]")

    theta_opt = 0.5 * (a + b)
    final_res = eval_angle(theta_opt, f"final optimum: {theta_opt:.3f} deg")

    uncertainty_deg = 0.5 * (b - a)
    energy_rel_error = final_res.energy_error_J / max(1e-9, final_res.energy_initial_J)

    return {
        "params": final_res.params.to_dict(),
        "beta": final_res.beta,
        "eta": final_res.eta,
        "theta_opt_deg": round(theta_opt, 3),
        "theta_uncertainty_deg": round(uncertainty_deg, 4),
        "range_m": round(final_res.range_m, 3),
        "range_uncertainty_m": round(abs(final_res.range_m - eval_cache[round(a, 4)].range_m), 4),
        "flight_time_s": round(final_res.flight_time_s, 3),
        "max_height_m": round(final_res.max_height_m, 3),
        "energy_lost_to_drag_J": round(final_res.energy_lost_to_drag_J, 2),
        "energy_balance_rel_error": energy_rel_error,
        "bracket_deg": [round(bracket_left, 1), round(bracket_right, 1)],
        "simulations": len(search_trace),
        "search_trace": search_trace,
    }
