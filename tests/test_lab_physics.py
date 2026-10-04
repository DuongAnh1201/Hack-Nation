"""Tests for the radiative-cooling bench (lab/physics.py)."""

import json

import numpy as np
import pytest

tmm = pytest.importorskip("tmm")

from lab import materials as M  # noqa: E402
from lab import physics as P  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_counter():
    P.reset_evaluation_count()
    P.set_evaluation_budget(None)
    yield
    P.set_evaluation_budget(None)


def test_tmm_matches_reference_package():
    lam = np.array([0.4, 0.55, 1.2, 8.5, 9.6, 11.0, 18.0])
    mats, d = ["SiO2", "TiO2", "Si3N4", "MgF2"], [230.0, 85.0, 400.0, 120.0]
    nl = np.array([M.refractive_index(m, lam) for m in mats])
    ns = M.refractive_index("Al", lam)
    for th in (0.0, 0.5, 1.3):
        ours = P._reflectance(nl, np.array(d), ns, lam, np.array([np.sin(th)]))[:, 0]
        ref = []
        for i, l in enumerate(lam):
            n_list = [1.0] + list(nl[:, i]) + [ns[i]]
            dl = [np.inf] + d + [np.inf]
            ref.append(0.5 * sum(tmm.coh_tmm(p, n_list, dl, th, l * 1000)["R"] for p in "sp"))
        assert np.allclose(ours, ref, atol=1e-9)


def test_bare_silver_reflects_sunlight_and_barely_emits():
    m = P._evaluate([], [], "Ag")
    assert m["solar_reflectance"] > 0.95
    assert m["window_emissivity"] < 0.05


def test_every_call_counts_including_invalid_and_optimizer_trials():
    P.simulate_stack(["SiO2"], [500.0])
    bad = P.simulate_stack(["HfO2"], [500.0])  # not an allowed material
    assert bad["valid"] is False and bad["p_net_w_m2"] is None
    assert P.evaluation_count() == 2
    out = P.optimize_thicknesses(["SiO2", "Al2O3"], budget=7, seed=1)
    assert out["evaluations"] == 7
    assert P.evaluation_count() == 9


def test_budget_is_enforced_inside_the_simulator():
    P.set_evaluation_budget(3)
    for _ in range(3):
        P.simulate_stack(["SiO2"], [300.0])
    with pytest.raises(P.EvaluationBudgetExceeded):
        P.simulate_stack(["SiO2"], [300.0])
    assert P.evaluation_count() == 3


@pytest.mark.parametrize(
    "materials,thicknesses,substrate",
    [
        (["SiO2"] * 6, [100.0] * 6, "Ag"),  # too many layers
        ([], [], "Ag"),  # too few
        (["SiO2"], [5.0], "Ag"),  # below bound
        (["SiO2"], [1000.1], "Ag"),  # above bound
        (["SiO2"], [float("nan")], "Ag"),
        (["SiO2"], [100.0], "Au"),  # substrate not allowed
        (["SiO2", "TiO2"], [100.0], "Ag"),  # length mismatch
    ],
)
def test_invalid_designs_do_not_crash(materials, thicknesses, substrate):
    r = P.simulate_stack(materials, thicknesses, substrate)
    assert r["valid"] is False and r["reason"]


def test_bounds_are_inclusive():
    lo, hi = P.THICKNESS_BOUNDS_NM
    assert P.simulate_stack(["SiO2", "MgF2"], [lo, hi], "Al")["valid"]


def test_ledger_records_every_evaluation(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("LAB_EVAL_LEDGER", str(ledger))
    P.simulate_stack(["SiO2"], [300.0])
    P.simulate_stack(["Si3N4"], [2.0])
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert [r["evaluation"] for r in rows] == [1, 2]
    assert [r["valid"] for r in rows] == [True, False]


def test_control_is_not_counted_and_matches_published_reflectance():
    c = P.stanford_control()
    assert P.evaluation_count() == 0
    assert c["checks"]["solar_reflectance"]
    assert c["target_w_m2"] == c["simulated"]["p_net_w_m2"]


def test_search_space_excludes_hafnia():
    assert "HfO2" not in P.ALLOWED_MATERIALS
    assert P.MAX_LAYERS == 5


def test_zero_thickness_and_vacuum_layers_do_not_crash():
    # Zero thickness returns invalid without crashing
    res_zero = P.simulate_stack(["SiO2"], [0.0], "Ag")
    assert res_zero["valid"] is False
    assert "thickness" in res_zero["reason"].lower() or "bound" in res_zero["reason"].lower()

    # Low-index dielectric approaching vacuum index does not divide by zero
    n_vacuum = np.ones(7, dtype=complex)
    r_vac = P._reflectance(np.array([n_vacuum]), np.array([100.0]), np.array([0.1 + 3.0j] * 7), np.array([0.55] * 7), np.array([0.0]))
    assert np.all(np.isfinite(r_vac))


def test_evaluation_counter_across_two_separate_processes(tmp_path):
    import subprocess
    import sys

    ledger = tmp_path / "shared_ledger.jsonl"
    code1 = f"""
import os, sys
os.environ['LAB_EVAL_LEDGER'] = r'{ledger}'
from lab import physics as P
P.simulate_stack(['SiO2'], [100.0])
P.simulate_stack(['TiO2'], [50.0])
"""
    code2 = f"""
import os, sys
os.environ['LAB_EVAL_LEDGER'] = r'{ledger}'
from lab import physics as P
P.simulate_stack(['Si3N4'], [80.0])
"""
    p1 = subprocess.run([sys.executable, "-c", code1], capture_output=True, text=True, check=True)
    p2 = subprocess.run([sys.executable, "-c", code2], capture_output=True, text=True, check=True)

    assert ledger.exists()
    lines = ledger.read_text().splitlines()
    assert len(lines) == 3
    data = [json.loads(line) for line in lines]
    assert [d["evaluation"] for d in data] == [1, 2, 3]
