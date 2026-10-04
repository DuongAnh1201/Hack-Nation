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


def test_common_knowledge_hub_integration(tmp_path, monkeypatch):
    ck_path = tmp_path / "common_knowledge.json"
    monkeypatch.chdir(tmp_path)

    # Log from literature secretary
    l_res = tools.log_to_common_knowledge("literature", {"id": "F1", "statement": "Stanford benchmark achieves 11.83 W/m2 in bench"})
    assert l_res["status"] == "success"
    assert l_res["department"] == "literature"

    # Log from hypothesis secretary
    h_res = tools.log_to_common_knowledge("hypothesis", {"id": "H1", "claim": "SiO2 + Si3N4 on Ag", "status": "proposed"})
    assert h_res["status"] == "success"

    # Read back common knowledge
    state = tools.read_common_knowledge()
    assert state["cycle"] == 1
    assert len(state["facts"]) >= 1
    assert "H1" in state["hypotheses"]
    assert state["hypotheses"]["H1"]["claim"] == "SiO2 + Si3N4 on Ag"


def test_execute_experiment_script(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    res = tools.execute_experiment_script(
        experiment_id="E1",
        materials=["SiO2", "HfO2", "SiO2"],
        thicknesses_nm=[100.0, 50.0, 100.0],
        substrate="Ag",
        run_id="test_run",
    )
    assert res["status"] == "completed"
    assert res["experiment_id"] == "E1"
    assert Path(res["script_path"]).exists()
    assert Path(res["csv_path"]).exists()
    assert res["row_count"] >= 1
    content = Path(res["script_path"]).read_text()
    assert "Experiment Script: E1" in content
    assert "Inputs:" in content
    assert "Outputs:" in content


def test_write_and_read_results_csv(tmp_path):
    from lab.csv_helper import write_results_csv, read_results_csv

    csv_file = tmp_path / "results.csv"
    rows = [
        {
            "design_id": "E3-001",
            "materials": ["SiO2", "TiO2", "SiO2"],
            "thicknesses_nm": [120.0, 85.0, 640.0],
            "substrate": "Ag",
            "p_net_w_m2": 38.4,
            "solar_reflectance": 0.962,
            "window_emissivity": 0.71,
            "valid": True,
            "reason": "",
            "seed": 0,
        },
        {
            "design_id": "E3-002",
            "materials": ["SiO2"] * 6,
            "thicknesses_nm": [50.0] * 6,
            "substrate": "Ag",
            "p_net_w_m2": None,
            "valid": False,
            "reason": "6 layers > 5",
            "seed": 1,
        },
    ]

    out_path = write_results_csv(rows, csv_file)
    assert out_path == str(csv_file.resolve())
    assert csv_file.exists()

    loaded = read_results_csv(csv_file)
    assert len(loaded) == 2
    assert loaded[0]["design_id"] == "E3-001"
    assert loaded[0]["materials"] == ["SiO2", "TiO2", "SiO2"]
    assert loaded[0]["thicknesses_nm"] == [120.0, 85.0, 640.0]
    assert loaded[0]["p_net_w_m2"] == 38.4
    assert loaded[0]["valid"] is True
    assert loaded[1]["valid"] is False
    assert "6 layers > 5" in loaded[1]["reason"]


def test_package_run(tmp_path, monkeypatch):
    import zipfile
    from pathlib import Path
    monkeypatch.chdir(tmp_path)

    run_dir = tmp_path / "runs" / "test_pkg"
    run_dir.mkdir(parents=True)
    (run_dir / "record.jsonl").write_text('{"id": "L1"}\n')
    (run_dir / "final_report.md").write_text("# Report\n")

    pkg_path = tools.package_run("test_pkg")
    assert Path(pkg_path).exists()
    assert pkg_path.endswith("test_pkg.zip")

    with zipfile.ZipFile(pkg_path, "r") as z:
        names = z.namelist()
        assert "record.jsonl" in names
        assert "final_report.md" in names


def test_search_papers_alias():
    assert tools.search_papers is tools.search_academic_papers
    res = tools.search_papers("radiative cooling", limit=1)
    assert len(res) == 1
    assert "origin" in res[0]
    assert res[0]["origin"] in ("openalex", "offline_fallback")






def test_search_marks_origin_and_fallback_respects_allowed_sources(monkeypatch):
    def offline(*args, **kwargs):
        raise OSError("network disabled for this test")

    monkeypatch.setattr(tools.urllib.request, "urlopen", offline)
    papers = tools.search_academic_papers("radiative cooling", limit=10)
    assert papers, "the offline fallback should still return papers"
    for p in papers:
        assert p["origin"] == "offline_fallback"
        assert tools._is_legitimate_source("", p["venue"], p["doi"], p["url"])


def test_fallback_database_entries_are_all_allowed_sources():
    for paper in tools.VERIFIED_PAPERS_DATABASE:
        assert tools._is_legitimate_source("", paper["venue"], paper["doi"], paper["url"]), paper["doi"]


def test_compare_to_benchmark_with_optical_metrics():
    comp = tools.compare_to_benchmark(12.5, solar_reflectance=0.95, window_emissivity=0.5)
    assert comp["beats_target"] is True
    control = tools._control_simulated()
    assert comp["solar_reflectance"]["achieved"] == 0.95
    assert comp["solar_reflectance"]["control"] == round(control["solar_reflectance"], 4)
    assert comp["window_emissivity"]["delta"] == round(0.5 - control["window_emissivity"], 4)
    assert "solar_reflectance" not in tools.compare_to_benchmark(12.5)


def test_run_experiment_runs_agent_code_and_saves_output_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exp_dir = tmp_path / "runs" / "r1" / "experiments" / "E1"
    exp_dir.mkdir(parents=True)
    (exp_dir / "run.py").write_text(
        "from lab.physics import simulate_stack\n"
        "from lab.csv_helper import write_results_csv\n"
        "r = simulate_stack(['SiO2'], [500.0])\n"
        "print('p_net', r['p_net_w_m2'])\n"
        "write_results_csv([{'design_id': 'E1-001', 'materials': ['SiO2'], 'thicknesses_nm': [500.0],\n"
        "                    'substrate': 'Ag', **r}], 'results.csv')\n"
    )
    script_before = (exp_dir / "run.py").read_text()

    out = tools.run_experiment("E1", run_id="r1")

    assert out["exit_code"] == 0 and out["timed_out"] is False
    assert out["rows"] == 1
    assert "p_net" in (exp_dir / "output.log").read_text()
    assert (exp_dir / "run.py").read_text() == script_before


def test_run_experiment_reports_failures_and_missing_script(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exp_dir = tmp_path / "runs" / "r1" / "experiments" / "E2"
    exp_dir.mkdir(parents=True)
    (exp_dir / "run.py").write_text("raise SystemExit('bad plan')\n")

    out = tools.run_experiment("E2", run_id="r1")
    assert out["exit_code"] != 0
    assert out["rows"] is None
    assert "bad plan" in (exp_dir / "output.log").read_text()

    with pytest.raises(FileNotFoundError):
        tools.run_experiment("missing", run_id="r1")
