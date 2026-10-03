"""Candidate physical laws for launch angle dependence on drag number beta."""

import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Any, Optional


@dataclass
class CandidateLaw:
    """Mathematical formulation of a candidate law for theta*(beta)."""

    name: str
    tier: int
    formula_str: str
    param_names: List[str]
    initial_params: List[float]
    predict_fn: Callable[[float, List[float]], float]

    def predict(self, beta: float, params: List[float]) -> float:
        return self.predict_fn(beta, params)


def _predict_linear(beta: float, params: List[float]) -> float:
    a = params[0]
    return 45.0 + a * beta


def _predict_power(beta: float, params: List[float]) -> float:
    a, p = params[0], params[1]
    if beta <= 0:
        return 45.0
    return 45.0 + a * (beta ** max(0.01, min(p, 5.0)))


def _predict_logarithmic(beta: float, params: List[float]) -> float:
    a, c = params[0], params[1]
    arg = max(1e-9, 1.0 + c * max(0.0, beta))
    return 45.0 + a * math.log(arg)


def _predict_saturating(beta: float, params: List[float]) -> float:
    a, c = params[0], params[1]
    denom = max(1e-9, 1.0 + c * max(0.0, beta))
    return 45.0 + (a * beta) / denom


def _predict_log_power(beta: float, params: List[float]) -> float:
    a, c, p = params[0], params[1], params[2]
    p_clamped = max(0.01, min(p, 5.0))
    arg = max(1e-9, 1.0 + c * (max(0.0, beta) ** p_clamped))
    return 45.0 + a * math.log(arg)


def _predict_reciprocal_log(beta: float, params: List[float]) -> float:
    a, c = params[0], params[1]
    denom = max(1e-5, 1.0 + a * math.log(max(1e-9, 1.0 + c * max(0.0, beta))))
    return 45.0 / denom


def _predict_cot_log(beta: float, params: List[float]) -> float:
    a, c = params[0], params[1]
    # cot(theta*) = 1 + a * ln(1 + c * beta)
    # theta* = atan(1 / (1 + a * ln(1 + c * beta)))
    cot_val = max(1e-5, 1.0 + a * math.log(max(1e-9, 1.0 + c * max(0.0, beta))))
    theta_rad = math.atan(1.0 / cot_val)
    return math.degrees(theta_rad)


CANDIDATE_LAWS: Dict[str, CandidateLaw] = {
    "linear": CandidateLaw(
        name="linear",
        tier=1,
        formula_str="theta* = 45 + a*beta",
        param_names=["a"],
        initial_params=[-0.5],
        predict_fn=_predict_linear,
    ),
    "power": CandidateLaw(
        name="power",
        tier=1,
        formula_str="theta* = 45 + a*beta^p",
        param_names=["a", "p"],
        initial_params=[-3.0, 0.5],
        predict_fn=_predict_power,
    ),
    "logarithmic": CandidateLaw(
        name="logarithmic",
        tier=1,
        formula_str="theta* = 45 + a*ln(1 + c*beta)",
        param_names=["a", "c"],
        initial_params=[-4.0, 1.0],
        predict_fn=_predict_logarithmic,
    ),
    "saturating": CandidateLaw(
        name="saturating",
        tier=1,
        formula_str="theta* = 45 + a*beta/(1 + c*beta)",
        param_names=["a", "c"],
        initial_params=[-20.0, 1.0],
        predict_fn=_predict_saturating,
    ),
    "log_power": CandidateLaw(
        name="log_power",
        tier=2,
        formula_str="theta* = 45 + a*ln(1 + c*beta^p)",
        param_names=["a", "c", "p"],
        initial_params=[-4.0, 1.0, 0.8],
        predict_fn=_predict_log_power,
    ),
    "reciprocal_log": CandidateLaw(
        name="reciprocal_log",
        tier=2,
        formula_str="45/theta* = 1 + a*ln(1 + c*beta)",
        param_names=["a", "c"],
        initial_params=[0.15, 1.0],
        predict_fn=_predict_reciprocal_log,
    ),
    "cot_log": CandidateLaw(
        name="cot_log",
        tier=2,
        formula_str="cot(theta*) = 1 + a*ln(1 + c*beta)",
        param_names=["a", "c"],
        initial_params=[0.25, 0.8],
        predict_fn=_predict_cot_log,
    ),
}


def get_laws_for_tier(max_tier: int = 1) -> List[CandidateLaw]:
    return [law for law in CANDIDATE_LAWS.values() if law.tier <= max_tier]
