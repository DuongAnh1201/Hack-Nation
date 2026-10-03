"""High-precision 4th-order Runge-Kutta numerical integrator for quadratic air drag."""

import math
from typing import Tuple, List, Dict, Any, Optional
from physics_lab.physics.models import ProjectileParams, TrajectoryFrame, SimulationResult


def derivatives(state: Tuple[float, float, float, float, float], g: float, k: float) -> Tuple[float, float, float, float, float]:
    """Compute state derivatives [dx/dt, dy/dt, dvx/dt, dvy/dt, dW_drag/dt]."""
    x, y, vx, vy, w_drag = state
    v = math.sqrt(vx * vx + vy * vy)
    ax = -k * v * vx
    ay = -g - k * v * vy
    # Rate of mechanical energy lost to drag: P_drag = m * k * v^3 per unit mass = k * v^3
    dw_drag = k * (v ** 3)
    return (vx, vy, ax, ay, dw_drag)


def rk4_step(
    state: Tuple[float, float, float, float, float],
    dt: float,
    g: float,
    k: float,
) -> Tuple[float, float, float, float, float]:
    """Standard 4th-order Runge-Kutta integration step."""
    k1 = derivatives(state, g, k)

    s2 = tuple(state[i] + 0.5 * dt * k1[i] for i in range(5))
    k2 = derivatives(s2, g, k)

    s3 = tuple(state[i] + 0.5 * dt * k2[i] for i in range(5))
    k3 = derivatives(s3, g, k)

    s4 = tuple(state[i] + dt * k3[i] for i in range(5))
    k4 = derivatives(s4, g, k)

    new_state = tuple(
        state[i] + (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
        for i in range(5)
    )
    return new_state  # type: ignore


def find_root_step(
    state: Tuple[float, float, float, float, float],
    dt_bracket: float,
    g: float,
    k: float,
    target_idx: int,
    target_val: float = 0.0,
    tol: float = 1e-12,
    max_iter: int = 50,
) -> Tuple[float, Tuple[float, float, float, float, float]]:
    """Use bisection/secant to find partial dt in [0, dt_bracket] where state[target_idx] == target_val."""
    low = 0.0
    high = dt_bracket

    best_dt = dt_bracket
    best_state = state

    for _ in range(max_iter):
        mid = 0.5 * (low + high)
        st = rk4_step(state, mid, g, k)
        val = st[target_idx]
        diff = val - target_val

        if abs(diff) < tol or (high - low) < 1e-15:
            return mid, st

        # If searching for y=0 crossing (falling from positive y to negative y)
        if target_idx == 1:
            if val > target_val:
                low = mid
            else:
                high = mid
                best_dt = mid
                best_state = st
        # If searching for vy=0 (ascending to descending)
        elif target_idx == 3:
            if val > target_val:
                low = mid
            else:
                high = mid
                best_dt = mid
                best_state = st

    return best_dt, best_state


def integrate_trajectory(
    params: ProjectileParams,
    step_multiplier: float = 1.0,
    record_trajectory: bool = False,
    max_frames: int = 240,
) -> Tuple[Dict[str, Any], Optional[List[TrajectoryFrame]]]:
    """Integrate projectile trajectory to impact using adaptive RK4 with partial step root finding."""
    theta_rad = math.radians(params.launch_angle)
    v0 = params.initial_velocity
    g = params.gravity
    k = params.k
    m = params.mass
    h0 = params.launch_height

    vx0 = v0 * math.cos(theta_rad)
    vy0 = v0 * math.sin(theta_rad)

    # Determine base time step from shortest relevant time scale
    t_grav = v0 / g
    if k > 0 and (k * v0) > 0:
        t_drag = 1.0 / (k * v0)
        t_scale = min(t_grav, t_drag)
    else:
        t_scale = t_grav

    dt = (t_scale / 200.0) * step_multiplier
    # Ensure dt is reasonable
    dt = max(1e-6, min(dt, 0.05))

    # State: [x, y, vx, vy, w_drag_per_mass]
    state = (0.0, h0, vx0, vy0, 0.0)
    t = 0.0

    raw_history = []
    if record_trajectory:
        raw_history.append((t, state))

    apex_t = 0.0
    apex_y = h0
    passed_apex = False if vy0 > 0 else True

    steps = 0
    max_steps = 200_000

    while steps < max_steps:
        prev_state = state
        prev_t = t

        next_state = rk4_step(state, dt, g, k)
        next_t = t + dt
        steps += 1

        # Check for apex crossing (vy crossing 0 from positive to negative)
        if not passed_apex and state[3] > 0 and next_state[3] <= 0:
            dt_apex, st_apex = find_root_step(state, dt, g, k, target_idx=3, target_val=0.0)
            apex_t = prev_t + dt_apex
            apex_y = st_apex[1]
            passed_apex = True

        # Check for ground impact (y crossing 0 from above)
        if next_state[1] <= 0.0:
            dt_impact, final_state = find_root_step(state, dt, g, k, target_idx=1, target_val=0.0)
            t = prev_t + dt_impact
            state = final_state
            if record_trajectory:
                raw_history.append((t, state))
            break

        state = next_state
        t = next_t

        if record_trajectory:
            raw_history.append((t, state))

    # If launch angle was downward or flat, apex is at launch
    if not passed_apex:
        apex_t = 0.0
        apex_y = h0

    x_final, y_final, vx_final, vy_final, w_drag_unit = state
    impact_speed = math.sqrt(vx_final ** 2 + vy_final ** 2)
    impact_angle = math.degrees(math.atan2(abs(vy_final), vx_final))

    e_init = 0.5 * m * (v0 ** 2) + m * g * h0
    e_final = 0.5 * m * (impact_speed ** 2) + m * g * max(0.0, y_final)
    e_drag = m * w_drag_unit
    energy_error = abs(e_init - (e_final + e_drag))

    measurements = {
        "range_m": x_final,
        "flight_time_s": t,
        "max_height_m": apex_y,
        "time_to_apex_s": apex_t,
        "impact_speed_m_s": impact_speed,
        "impact_angle_deg": impact_angle,
        "energy_initial_J": e_init,
        "energy_final_J": e_final,
        "energy_lost_to_drag_J": e_drag,
        "energy_error_J": energy_error,
        "beta": params.beta,
        "eta": params.eta,
        "steps": steps,
        "dt": dt,
    }

    frames: Optional[List[TrajectoryFrame]] = None
    if record_trajectory and raw_history:
        frames = []
        n = len(raw_history)
        if n <= max_frames:
            selected_indices = list(range(n))
        else:
            selected_indices = [int(i * (n - 1) / (max_frames - 1)) for i in range(max_frames)]
            if 0 not in selected_indices:
                selected_indices[0] = 0
            if (n - 1) not in selected_indices:
                selected_indices[-1] = n - 1

        for idx in selected_indices:
            frame_t, (fx, fy, fvx, fvy, _) = raw_history[idx]
            fspeed = math.sqrt(fvx * fvx + fvy * fvy)
            fax = -k * fspeed * fvx
            fay = -g - k * fspeed * fvy
            f_drag_x = -0.5 * params.air_density * params.drag_coefficient * params.cross_section_area * fspeed * fvx
            f_drag_y = -0.5 * params.air_density * params.drag_coefficient * params.cross_section_area * fspeed * fvy
            f_grav_y = -m * g
            f_net_x = f_drag_x
            f_net_y = f_grav_y + f_drag_y

            ke = 0.5 * m * (fspeed ** 2)
            pe = m * g * max(0.0, fy)

            frames.append(
                TrajectoryFrame(
                    t=frame_t,
                    position=[fx, fy, 0.0],
                    velocity=[fvx, fvy, 0.0],
                    acceleration=[fax, fay, 0.0],
                    forces={
                        "gravity": [0.0, f_grav_y, 0.0],
                        "drag": [f_drag_x, f_drag_y, 0.0],
                        "net": [f_net_x, f_net_y, 0.0],
                    },
                    speed=fspeed,
                    kinetic_energy=ke,
                    potential_energy=pe,
                )
            )

    return measurements, frames
