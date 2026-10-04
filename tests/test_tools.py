"""Tests for lab function tools (lab/tools.py)."""

import os
import tempfile
import pytest

from lab import physics as P
from lab import tools


@pytest.fixture(autouse=True)
def _fresh_counter():
    P.reset_evaluation_count()
    P.set_evaluation_budget(None)
    yield
    P.set_evaluation_budget(None)


def test_search_academic_papers_strictly_filters_legitimate_sources():
    # Query for radiative cooling papers
    papers = tools.search_academic_papers("radiative cooling metamaterial", limit=3)
    assert len(papers) > 0
    assert len(papers) <= 3

    for p in papers:
        # Strict validation of keys
        assert "title" in p and p["title"]
        assert "authors" in p
        assert "year" in p
        assert "venue" in p
        assert "doi" in p
        assert "url" in p
        assert "abstract_excerpt" in p
        assert "citations" in p

        # Strict venue validation: must belong to Springer, Nature, IEEE, or arXiv
        venue_text = f"{p['venue']} {p['doi']} {p['url']}".lower()
        is_legit = any(v.lower() in venue_text for v in ("springer", "nature", "ieee", "arxiv", "10.1038", "10.1007", "10.1109", "10.48550"))
        assert is_legit, f"Disallowed source detected: {p['venue']}"


def test_search_academic_papers_empty_query():
    assert tools.search_academic_papers("") == []
    assert tools.search_academic_papers("   ") == []


def test_list_materials_and_constraints():
    cats = tools.list_materials()
    assert len(cats) >= 3

    candidates = next(c["materials"] for c in cats if c["category"] == "dielectric_candidates")
    substrates = next(c["materials"] for c in cats if c["category"] == "substrates")
    excluded = next(c["materials"] for c in cats if c["category"] == "excluded_benchmark_only")

    assert "SiO2" in candidates
    assert "Al2O3" in candidates
    assert "Si3N4" in candidates
    assert "TiO2" in candidates
    assert "MgF2" in candidates
    assert "HfO2" not in candidates
    assert "HfO2" in excluded
    assert "Ag" in substrates
    assert "Al" in substrates


def test_material_properties_valid_and_invalid():
    sio2 = tools.material_properties("SiO2")
    assert sio2["valid"] is True
    assert sio2["allowed_in_search"] is True
    assert "9." in sio2["reststrahlen_band"]
    assert len(sio2["samples"]) > 0

    hfo2 = tools.material_properties("HfO2")
    assert hfo2["valid"] is True
    assert hfo2["allowed_in_search"] is False  # excluded from search space

    bad = tools.material_properties("Unobtainium")
    assert bad["valid"] is False
    assert "error" in bad


def test_simulate_stack_tool_and_budget_tracking():
    # Before simulation
    b0 = tools.budget_left(max_budget=100)
    assert b0["evaluations_used"] == 0
    assert b0["evaluations_remaining"] == 100

    # Execute simulation
    res = tools.simulate_stack_tool(["SiO2", "TiO2"], [300.0, 100.0], "Ag")
    assert res["valid"] is True
    assert "p_net_w_m2" in res
    assert "solar_reflectance" in res
    assert "window_emissivity" in res

    # Budget updated
    b1 = tools.budget_left(max_budget=100)
    assert b1["evaluations_used"] == 1
    assert b1["evaluations_remaining"] == 99


def test_compare_to_benchmark():
    comp = tools.compare_to_benchmark(12.5)
    assert comp["target_w_m2"] == tools.STANFORD_BENCHMARK_TARGET_W_M2
    assert comp["achieved_w_m2"] == 12.5
    assert comp["beats_target"] is True
    assert comp["delta_w_m2"] > 0

    comp_low = tools.compare_to_benchmark(5.0)
    assert comp_low["beats_target"] is False
    assert comp_low["delta_w_m2"] < 0


def test_record_read_write_cycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_path = os.path.join(tmpdir, "record.jsonl")
        os.environ["PHYSICS_LAB_RECORD"] = rec_path

        # Write literature entry
        l1 = tools.write_record(
            kind="literature",
            agent="literature_web_search",
            content={"title": "Raman et al.", "p_net": 40.1},
        )
        assert l1["id"] == "L1"
        assert l1["kind"] == "literature"
        assert l1["based_on"] == []

        # Write hypothesis entry referencing literature
        h1 = tools.write_record(
            kind="hypothesis",
            agent="hypothesis_physics",
            content={"claim": "SiO2 + Al2O3 covers 8-13 um window"},
            based_on=[l1["id"]],
        )
        assert h1["id"] == "H1"
        assert h1["based_on"] == ["L1"]

        # Write second hypothesis
        h2 = tools.write_record(
            kind="hypothesis",
            agent="hypothesis_materials",
            content={"claim": "MgF2 top layer reduces solar reflection losses"},
            based_on=[h1["id"]],
        )
        assert h2["id"] == "H2"

        # Read specific entry
        read_h1 = tools.read_record("H1")
        assert read_h1["id"] == "H1"
        assert read_h1["content"]["claim"] == "SiO2 + Al2O3 covers 8-13 um window"

        # Read non-existent entry
        bad_entry = tools.read_record("X99")
        assert "error" in bad_entry

        # Read full summary
        full_rec = tools.read_record()
        assert full_rec["total_entries"] == 3
        assert full_rec["by_kind"]["literature"] == 1
        assert full_rec["by_kind"]["hypothesis"] == 2
        assert full_rec["latest_id"] == "H2"
