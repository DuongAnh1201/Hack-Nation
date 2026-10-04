"""The lab bench: net radiative cooling power of a thin-film stack on a metal mirror.

Shared contract (docs/team-plan.md, "Simulator API"):

    simulate_stack(materials, thicknesses_nm, substrate="Ag") -> dict
    optimize_thicknesses(materials, substrate="Ag", budget=50, seed=0) -> dict

Layer order: ``materials[0]`` faces the sky, ``materials[-1]`` sits on the substrate.

Evaluation accounting (the unit of the speed-up claim)
-----------------------------------------------------
* Every call to ``simulate_stack`` is one evaluation, valid or not. It is counted
  *inside* this module; callers cannot opt out.
* ``optimize_thicknesses`` only evaluates designs by calling ``simulate_stack``,
  so every thickness tweak is counted too.
* ``evaluation_count()`` returns the process total. If ``LAB_EVAL_LEDGER`` is set,
  every evaluation is also appended to that JSONL file (an audit trail that a
  counter reset cannot erase; the micro-VM workers ship it back to the host).
* ``set_evaluation_budget(n)`` (or ``LAB_EVAL_BUDGET``) makes the bench refuse
  evaluation number n + 1 with ``EvaluationBudgetExceeded``.

Physics (assumptions in docs/physics-bench.md)
----------------------------------------------
P_net(T_amb) = P_rad(T_amb) - P_atm(T_amb) - P_sun, with P_cond+conv = 0 at T = T_amb.
Optics by the transfer-matrix (characteristic matrix) method, vectorised over
wavelength and angle, both polarisations averaged. The substrate mirror is opaque
(semi-infinite), so emissivity = absorptivity = 1 - R.
"""

import hashlib
import json
import os
import threading
import time

import numpy as np

from lab import materials as _mat
from lab import spectra as _spec

# ---------------------------------------------------------------------------
# Search space: identical for every method (random search, BO, the agent lab)
# ---------------------------------------------------------------------------

ALLOWED_MATERIALS = ("SiO2", "Al2O3", "Si3N4", "TiO2", "MgF2")
ALLOWED_SUBSTRATES = ("Ag", "Al")
MIN_LAYERS = 1
MAX_LAYERS = 5
THICKNESS_BOUNDS_NM = (10.0, 1000.0)  # inclusive, every layer, every method
T_AMBIENT_K = 300.0

SEARCH_SPACE = {
    "materials": list(ALLOWED_MATERIALS),
    "substrates": list(ALLOWED_SUBSTRATES),
    "min_layers": MIN_LAYERS,
    "max_layers": MAX_LAYERS,
    "thickness_bounds_nm": list(THICKNESS_BOUNDS_NM),
    "repeated_materials_allowed": True,
    "layer_order": "materials[0] faces the sky; materials[-1] touches the substrate",
    "t_ambient_k": T_AMBIENT_K,
}

# ---------------------------------------------------------------------------
# Spectral grids (micrometres)
# ---------------------------------------------------------------------------

SOLAR_GRID_UM = np.concatenate([np.arange(0.30, 2.50, 0.002), np.arange(2.50, 4.0001, 0.01)])
THERMAL_GRID_UM = np.linspace(2.5, 25.0, 451)  # 0.05 um steps
SOLAR_BAND_UM = (0.3, 2.5)
WINDOW_BAND_UM = (8.0, 13.0)
N_ANGLES = 8  # Gauss-Legendre nodes in mu = sin^2(theta) on [0, 1]

_mu, _w = np.polynomial.legendre.leggauss(N_ANGLES)
ANGLE_MU = 0.5 * (_mu + 1.0)  # sin^2(theta)
ANGLE_W = 0.5 * _w  # sums to 1
ANGLE_SIN = np.sqrt(ANGLE_MU)
ANGLE_COS = np.sqrt(1.0 - ANGLE_MU)

_AM15 = _spec.am15_global(SOLAR_GRID_UM)
_SOLAR_MASK = (SOLAR_GRID_UM >= SOLAR_BAND_UM[0]) & (SOLAR_GRID_UM <= SOLAR_BAND_UM[1])
_WINDOW_MASK = (THERMAL_GRID_UM >= WINDOW_BAND_UM[0]) & (THERMAL_GRID_UM <= WINDOW_BAND_UM[1])
_T_ZENITH = _spec.zenith_transmittance(THERMAL_GRID_UM)
_EPS_ATM = 1.0 - _T_ZENITH[:, None] ** (1.0 / ANGLE_COS[None, :])  # (n_lambda, n_angles)


# ---------------------------------------------------------------------------
# Evaluation counter, budget and ledger
# ---------------------------------------------------------------------------


class EvaluationBudgetExceeded(RuntimeError):
    """Raised when simulate_stack is called after the evaluation budget is spent."""


_lock = threading.Lock()
_count = 0
_budget = int(os.environ["LAB_EVAL_BUDGET"]) if os.environ.get("LAB_EVAL_BUDGET") else None


def evaluation_count():
    """Number of simulate_stack calls in this process since the last reset."""
    return _count


def reset_evaluation_count():
    """Benchmark harness only (between seeds). Not exposed as an agent tool."""
    global _count
    with _lock:
        _count = 0


def set_evaluation_budget(budget):
    """Cap evaluations for this process (None removes the cap)."""
    global _budget
    _budget = None if budget is None else int(budget)


def evaluation_budget():
    return _budget


def _claim_evaluation():
    global _count
    with _lock:
        ledger_path = os.environ.get("LAB_EVAL_LEDGER")
        if ledger_path and os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8") as fh:
                    ledger_lines = sum(1 for line in fh if line.strip())
                if ledger_lines > _count:
                    _count = ledger_lines
            except Exception:
                pass
        if _budget is not None and _count >= _budget:
            raise EvaluationBudgetExceeded(f"evaluation budget of {_budget} spent")
        _count += 1
        return _count


def _ledger_write(entry):
    path = os.environ.get("LAB_EVAL_LEDGER")
    if not path:
        return
    with _lock, open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Optics
# ---------------------------------------------------------------------------


def _reflectance(n_layers, d_nm, n_sub, lam_um, sin0):
    """Unpolarised reflectance R(lambda, theta) of a layer stack on an opaque substrate.

    n_layers: (L, n_lambda) complex, n + ik, top layer first.
    d_nm:     (L,) thicknesses.
    n_sub:    (n_lambda,) complex substrate index.
    sin0:     (n_angles,) sine of the incidence angle in air.
    Returns (n_lambda, n_angles).

    Characteristic-matrix method (Macleod) in the N = n - ik convention, so
    the conjugate of the n + ik data is used. Reflectance is unaffected.
    """
    s2 = (sin0**2)[None, :]  # (1, A)
    cos0 = np.sqrt(1.0 - s2).astype(complex)

    def normal_component(nn):  # N cos(theta) with Im <= 0 (decaying wave)
        q = np.sqrt(np.conj(nn)[:, None] ** 2 - s2)
        return np.where(q.imag > 0, -q, q)

    def admittances(nn, q):
        return q, np.conj(nn)[:, None] ** 2 / q  # (s, p)

    eta0 = (cos0, 1.0 / cos0)
    q_sub = normal_component(n_sub)
    eta_sub = admittances(n_sub, q_sub)

    r_total = 0.0
    for pol in (0, 1):
        m11 = np.ones_like(q_sub)
        m12 = np.zeros_like(q_sub)
        m21 = np.zeros_like(q_sub)
        m22 = np.ones_like(q_sub)
        for nn, d in zip(n_layers, d_nm):
            q = normal_component(nn)
            eta = admittances(nn, q)[pol]
            delta = 2.0 * np.pi * q * (d * 1e-3) / lam_um[:, None]
            c, s = np.cos(delta), np.sin(delta)
            a11, a12, a21, a22 = c, 1j * s / eta, 1j * eta * s, c
            m11, m12, m21, m22 = (
                m11 * a11 + m12 * a21,
                m11 * a12 + m12 * a22,
                m21 * a11 + m22 * a21,
                m21 * a12 + m22 * a22,
            )
        b = m11 + m12 * eta_sub[pol]
        cc = m21 + m22 * eta_sub[pol]
        r = (eta0[pol] * b - cc) / (eta0[pol] * b + cc)
        r_total = r_total + np.abs(r) ** 2
    return np.clip(r_total / 2.0, 0.0, 1.0)


def _evaluate(materials, thicknesses_nm, substrate):
    """Physics only: no validation, no counting. Returns metrics + spectra."""
    d = np.asarray(thicknesses_nm, dtype=float)

    if len(materials) == 0:
        n_sol = np.empty((0, len(SOLAR_GRID_UM)), dtype=complex)
        n_th = np.empty((0, len(THERMAL_GRID_UM)), dtype=complex)
    else:
        n_sol = np.array([_mat.refractive_index(m, SOLAR_GRID_UM) for m in materials]).reshape(len(materials), -1)
        n_th = np.array([_mat.refractive_index(m, THERMAL_GRID_UM) for m in materials]).reshape(len(materials), -1)

    r_sun = _reflectance(n_sol, d, _mat.refractive_index(substrate, SOLAR_GRID_UM), SOLAR_GRID_UM, np.array([0.0]))[:, 0]
    eps_sun = 1.0 - r_sun

    eps_th = 1.0 - _reflectance(n_th, d, _mat.refractive_index(substrate, THERMAL_GRID_UM), THERMAL_GRID_UM, ANGLE_SIN)

    bb = _spec.planck_radiance(T_AMBIENT_K, THERMAL_GRID_UM)[:, None]
    # Hemispherical integral: int dOmega cos(theta) f = pi * int_0^1 f d(sin^2 theta)
    p_rad = np.pi * np.trapezoid(bb[:, 0] * (eps_th @ ANGLE_W), THERMAL_GRID_UM)
    p_atm = np.pi * np.trapezoid(bb[:, 0] * ((eps_th * _EPS_ATM) @ ANGLE_W), THERMAL_GRID_UM)
    p_sun = np.trapezoid(_AM15 * eps_sun, SOLAR_GRID_UM)

    solar_reflectance = np.trapezoid((_AM15 * r_sun)[_SOLAR_MASK], SOLAR_GRID_UM[_SOLAR_MASK]) / np.trapezoid(
        _AM15[_SOLAR_MASK], SOLAR_GRID_UM[_SOLAR_MASK]
    )
    eps_normal = eps_th[:, 0]  # node closest to normal incidence
    window_emissivity = float(np.mean(eps_normal[_WINDOW_MASK]))

    return {
        "p_net_w_m2": float(p_rad - p_atm - p_sun),
        "solar_reflectance": float(solar_reflectance),
        "window_emissivity": window_emissivity,
        "p_rad_w_m2": float(p_rad),
        "p_atm_w_m2": float(p_atm),
        "p_sun_w_m2": float(p_sun),
        "_spectra": {
            "solar_um": SOLAR_GRID_UM,
            "solar_emissivity": eps_sun,
            "thermal_um": THERMAL_GRID_UM,
            "thermal_emissivity_near_normal": eps_normal,
        },
    }


# ---------------------------------------------------------------------------
# Public API (shared contract)
# ---------------------------------------------------------------------------


def validate_design(materials, thicknesses_nm, substrate="Ag"):
    """Return (valid, reason). The same rules apply to every search method."""
    if not isinstance(materials, (list, tuple)) or not isinstance(thicknesses_nm, (list, tuple, np.ndarray)):
        return False, "materials and thicknesses_nm must be lists"
    if len(materials) != len(thicknesses_nm):
        return False, f"{len(materials)} materials but {len(thicknesses_nm)} thicknesses"
    if not MIN_LAYERS <= len(materials) <= MAX_LAYERS:
        return False, f"layer count {len(materials)} outside [{MIN_LAYERS}, {MAX_LAYERS}]"
    if substrate not in ALLOWED_SUBSTRATES:
        return False, f"substrate {substrate!r} not in {ALLOWED_SUBSTRATES}"
    for m in materials:
        if m not in ALLOWED_MATERIALS:
            return False, f"material {m!r} not in {ALLOWED_MATERIALS}"
    lo, hi = THICKNESS_BOUNDS_NM
    for t in thicknesses_nm:
        try:
            t = float(t)
        except (TypeError, ValueError):
            return False, f"thickness {t!r} is not a number"
        if not np.isfinite(t) or not lo <= t <= hi:
            return False, f"thickness {t} nm outside [{lo}, {hi}] nm"
    return True, "ok"


def _design_hash(materials, thicknesses_nm, substrate):
    key = json.dumps([list(materials), [round(float(t), 6) for t in thicknesses_nm], substrate])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def simulate_stack(materials, thicknesses_nm, substrate="Ag"):
    """One evaluation. Always counted, including invalid designs.

    Invalid designs return ``valid=False``, ``p_net_w_m2=None`` and a reason.
    """
    n = _claim_evaluation()
    materials = list(materials)
    thicknesses_nm = [float(t) if isinstance(t, (int, float, np.floating, np.integer)) else t for t in thicknesses_nm]
    valid, reason = validate_design(materials, thicknesses_nm, substrate)
    if valid:
        metrics = _evaluate(materials, thicknesses_nm, substrate)
        result = {
            "p_net_w_m2": metrics["p_net_w_m2"],
            "solar_reflectance": metrics["solar_reflectance"],
            "window_emissivity": metrics["window_emissivity"],
            "n_layers": len(materials),
            "valid": True,
            "reason": "ok",
        }
    else:
        result = {
            "p_net_w_m2": None,
            "solar_reflectance": None,
            "window_emissivity": None,
            "n_layers": len(materials) if isinstance(materials, list) else 0,
            "valid": False,
            "reason": reason,
        }
    result["evaluation"] = n
    _ledger_write(
        {
            "evaluation": n,
            "t": time.time(),
            "pid": os.getpid(),
            "design": _design_hash(materials, thicknesses_nm, substrate) if valid else None,
            "materials": materials,
            "thicknesses_nm": [float(t) for t in thicknesses_nm] if valid else None,
            "substrate": substrate,
            "valid": valid,
            "p_net_w_m2": result["p_net_w_m2"],
        }
    )
    return result


class _LocalBudgetSpent(Exception):
    pass


def optimize_thicknesses(materials, substrate="Ag", budget=50, seed=0):
    """Optimise layer thicknesses for a fixed material order, within ``budget`` evaluations.

    Bounded Powell search from a seeded random start. Every trial goes through
    ``simulate_stack``, so all of them are counted globally as well.
    """
    from scipy.optimize import minimize

    materials = list(materials)
    budget = int(budget)
    if budget < 1:
        raise ValueError("budget must be >= 1")
    rng = np.random.default_rng(seed)
    lo, hi = THICKNESS_BOUNDS_NM
    x0 = rng.uniform(lo, hi, size=len(materials))

    used = 0
    best = None
    best_x = None

    def objective(x):
        nonlocal used, best, best_x
        if used >= budget:
            raise _LocalBudgetSpent
        x = np.clip(x, lo, hi)
        used += 1
        res = simulate_stack(materials, list(x), substrate)
        if not res["valid"]:
            return 1e6
        if best is None or res["p_net_w_m2"] > best["p_net_w_m2"]:
            best, best_x = res, [float(v) for v in x]
        return -res["p_net_w_m2"]

    try:
        minimize(
            objective,
            x0,
            method="Powell",
            bounds=[(lo, hi)] * len(materials),
            options={"maxfev": budget, "xtol": 0.5, "ftol": 1e-4},
        )
    except _LocalBudgetSpent:
        pass
    return {"best": best, "thicknesses_nm": best_x, "evaluations": used}


# ---------------------------------------------------------------------------
# Control: Raman et al., Nature 515, 540 (2014), Fig. 1
# ---------------------------------------------------------------------------

STANFORD_DESIGN = {
    "materials": ["SiO2", "HfO2", "SiO2", "HfO2", "SiO2", "HfO2", "SiO2"],
    "thicknesses_nm": [230.0, 485.0, 688.0, 13.0, 73.0, 34.0, 54.0],
    "substrate": "Ag",
    "source": "Raman et al., Nature 515, 540-544 (2014), Fig. 1d, top to bottom on 200 nm Ag",
}
PUBLISHED = {"solar_reflectance": 0.97, "cooling_power_w_m2": 40.1}
# Pass criteria, fixed before the first control run:
CONTROL_TOLERANCE = {
    "solar_reflectance_abs": 0.02,  # |R_solar - 0.97| <= 0.02
    "p_net_range_w_m2": (10.0, 80.0),  # positive cooling under full 1000 W/m^2 AM1.5 normal sun (vs 850 W/m^2 @ 30 deg in paper)
}


def stanford_control():
    """Evaluate the fixed 7-layer HfO2/SiO2 control (outside the search space).

    Not counted as a search evaluation: it takes no inputs, so it cannot be used
    to search. Its P_net is the benchmark target.
    """
    d = STANFORD_DESIGN
    m = _evaluate(d["materials"], d["thicknesses_nm"], d["substrate"])
    r_ok = abs(m["solar_reflectance"] - PUBLISHED["solar_reflectance"]) <= CONTROL_TOLERANCE["solar_reflectance_abs"]
    lo, hi = CONTROL_TOLERANCE["p_net_range_w_m2"]
    p_ok = lo <= m["p_net_w_m2"] <= hi
    return {
        "design": {k: v for k, v in d.items()},
        "simulated": {k: v for k, v in m.items() if not k.startswith("_")},
        "published": PUBLISHED,
        "gap": {
            "solar_reflectance": m["solar_reflectance"] - PUBLISHED["solar_reflectance"],
            "p_net_w_m2": m["p_net_w_m2"] - PUBLISHED["cooling_power_w_m2"],
        },
        "tolerance": {"solar_reflectance_abs": CONTROL_TOLERANCE["solar_reflectance_abs"], "p_net_range_w_m2": [lo, hi]},
        "checks": {"solar_reflectance": bool(r_ok), "p_net": bool(p_ok)},
        "passed": bool(r_ok and p_ok),
        "target_w_m2": m["p_net_w_m2"],
        "conditions": {
            "t_ambient_k": T_AMBIENT_K,
            "sun": "ASTM G173 AM1.5 global, normal incidence",
            "sky": _spec.atmosphere_model_name(),
            "p_cond_conv": "0 at T = T_ambient",
        },
    }
