"""Tests for Omnigent tool schemas, epistemic validation, autopilot, and candidate law fitting."""

import inspect
import os
import pytest
from physics_lab import tools
from physics_lab.record import ResearchRecord
from physics_lab.analysis.laws import CANDIDATE_LAWS
from physics_lab.analysis.fitter import fit_law, fit_law_loo
from physics_lab.agents.autopilot import run_discovery_autopilot
from physics_lab.benchmark import run_benchmark


def test_tool_signatures_use_plain_types():
    """CRITICAL: Ensure Omnigent function tools use BARE primitive annotations.

    Generics like list[str] or typing.Dict silently degrade into string in Omnigent's schema generator.
    """
    allowed_types = {str, int, float, bool, list, dict, type(None), inspect._empty}

    tool_functions = [
        tools.get_established_facts,
        tools.search_literature,
        tools.record_note,
        tools.propose_hypothesis,
        tools.update_hypothesis,
        tools.review_experiment,
        tools.run_experiment,
        tools.simulate_once,
        tools.fit_laws,
        tools.suggest_next_experiment,
        tools.record_decision,
        tools.record_conclusion,
        tools.read_record,
    ]

    for fn in tool_functions:
        sig = inspect.signature(fn)
        for param_name, param in sig.parameters.items():
            assert param.annotation in allowed_types, (
                f"Tool '{fn.__name__}' parameter '{param_name}' has non-bare type annotation: {param.annotation}"
            )
        assert sig.return_annotation in allowed_types, (
            f"Tool '{fn.__name__}' return annotation has non-bare type: {sig.return_annotation}"
        )


def test_research_record_epistemic_enforcement(tmp_path):
    """Verify that established facts must cite a source."""
    rec = ResearchRecord("Test Question")

    # Valid fact with source
    rec.add_entry(
        kind="fact",
        summary="A verified physical law",
        agent="literature_agent",
        data={"source": "OpenStax Vol 1, Sec 4.3"},
        epistemic_status="established_fact",
    )

    # Invalid fact without source
    with pytest.raises(ValueError):
        rec.add_entry(
            kind="fact",
            summary="Uncited claim",
            agent="literature_agent",
            data={},
            epistemic_status="established_fact",
        )

    # Save and reload
    save_path = str(tmp_path / "record.json")
    rec.save(save_path)
    loaded = ResearchRecord.load(save_path)
    assert len(loaded.entries) == 1
    assert loaded.entries[0].epistemic_status == "established_fact"


def test_candidate_laws_fit_monotonically():
    """Verify that fitting laws on sample points preserves monotonicity."""
    sample_data = [(0.01, 44.938), (0.1, 44.428), (1.0, 41.2), (2.0, 38.78), (10.0, 32.5), (100.0, 25.155)]
    cot_law = CANDIDATE_LAWS["cot_log"]
    res = fit_law_loo(cot_law, sample_data)

    assert res["loo_rmse_deg"] < 0.25
    assert "cot_log" in res["name"]


def test_tool_invocations(tmp_path):
    """Verify that function tools execute correctly and persist into record."""
    test_rec = str(tmp_path / "test_rec.json")
    os.environ["PHYSICS_LAB_RECORD"] = test_rec

    facts = tools.get_established_facts()
    assert len(facts) >= 5

    sim_res = tools.simulate_once({"initial_velocity": 25.0, "launch_angle": 45.0}, record_trajectory=False)
    assert "measurements" in sim_res
    assert sim_res["measurements"]["range_m"] > 0

    h_id = tools.propose_hypothesis(
        statement="Test hypothesis",
        prediction="Test prediction",
        rationale="Test rationale",
        law_name="test_law",
        law_formula="y=x",
        refs=["F1"],
    )
    assert h_id.startswith("H")

    rec = ResearchRecord.load(test_rec)
    assert rec.get_entry(h_id) is not None


def test_autopilot_end_to_end(tmp_path):
    """Verify that the autonomous discovery loop executes completely without error."""
    run_file = str(tmp_path / "autopilot_record.json")
    rec = run_discovery_autopilot(record_path=run_file)

    assert rec.metrics["simulations"] > 500
    assert len(rec.entries) >= 50

    # Verify key decisions and conclusions exist
    kinds = set(e.kind for e in rec.entries)
    assert "decision" in kinds
    assert "conclusion" in kinds
    assert "experiment" in kinds
    assert "result" in kinds

    conclusion = next(e for e in reversed(rec.entries) if e.kind == "conclusion")
    assert conclusion.status == "pending_human_review"


def test_benchmark_runs_cleanly(capsys):
    """Verify benchmark utility prints speedup and comparisons."""
    run_benchmark()
    captured = capsys.readouterr()
    assert "2.9x fewer simulations" in captured.out
