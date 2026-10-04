"""Tests for lab.bench_entry (Issue #19)."""

from analysis.record_check import check, load_record
from lab import bench_entry
from lab import physics as P


def test_run_agent_produces_valid_record_and_passes_all_story_checks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def evaluate(stack):
        return P.simulate_stack(stack.materials, stack.thicknesses_nm, stack.substrate)

    res = bench_entry.run_agent(evaluate=evaluate, seed=1, budget=40, target=52.0)

    assert "llm_calls" in res and res["llm_calls"] > 0
    assert "record_path" in res

    entries, errors = load_record(res["record_path"])
    assert not errors

    result = check(entries)
    assert not result["errors"]

    # Verify story checks
    story = {s["check"]: s["ok"] for s in result["story"]}
    assert story["control passes before any design experiment"]
    assert story["planner chooses between 2+ candidate tests"]
    assert story["at least one hypothesis is refuted"]
    assert story["a refutation changes the next step"]
    assert story["every verdict rests on a result"]
    assert story["a human approval decision is recorded"]
    assert story["hypotheses, plans and verdicts cite their evidence"]


def test_run_agent_no_analyst_ablation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def evaluate(stack):
        return P.simulate_stack(stack.materials, stack.thicknesses_nm, stack.substrate)

    res = bench_entry.run_agent_no_analyst(evaluate=evaluate, seed=1, budget=20, target=52.0)
    assert "record_path" in res
    assert "llm_calls" in res
