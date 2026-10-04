import json
import math

import numpy as np
import pytest

from analysis import speedup as S
from analysis.fake_benchmark import make_fake


def bench(methods, target=40.0, budget=2000, fake=False):
    raw = {"target_w_m2": target, "budget": budget, "seeds": 10, "methods": methods}
    if fake:
        raw["_fake"] = True
    return S.parse_benchmark(raw)


def runs(evals, target=40.0):
    return {"evals_to_target": evals, "best_w_m2": [target + 1 if e is not None else target - 1 for e in evals]}


def test_median_is_when_half_the_runs_reached_the_target():
    assert S.median_evals(np.array([100, 200, 300, 400, math.inf, math.inf])) == 300
    assert S.median_evals(np.array([100.0] * 4 + [math.inf] * 6)) == math.inf  # only 4/10 reached
    assert S.median_evals(np.array([500.0, 100, 300, 200, 400, 600, 700, 800, 900, 1000])) == 500  # 5th of 10


def test_failed_runs_are_counted_not_dropped():
    b = bench({"agent_lab": runs([100, None, None, 200]), "random": runs([None] * 4)})
    s = S.summarize(b.methods["agent_lab"])
    assert (s["reached"], s["runs"], s["success_rate"]) == (2, 4, 0.5)
    assert S.reach_curve(b.methods["agent_lab"], 2000) == [[0, 0.0], [100, 0.25], [200, 0.5], [2000, 0.5]]


def test_speedup_point_and_ci_are_reproducible():
    b = bench({"agent_lab": runs([100, 120, 140, 160, 180, 200, 220, 240, 260, 280]),
               "bayes_opt": runs([400, 450, 500, 550, 600, 650, 700, 750, 800, 850])})
    s1 = S.speedup(b.methods["agent_lab"], b.methods["bayes_opt"], 2000, 2000, seed=1)
    s2 = S.speedup(b.methods["agent_lab"], b.methods["bayes_opt"], 2000, 2000, seed=1)
    assert s1["ci95"] == s2["ci95"]
    assert s1["point"] == pytest.approx(600 / 180)
    assert s1["ci95"][0] <= s1["point"] <= s1["ci95"][1]
    assert s1["supported"] and "we claim at least" in s1["claim"]


def test_censored_baseline_gives_a_conservative_lower_bound():
    b = bench({"agent_lab": runs([100] * 10), "random": runs([1500, None, None, None, None, None, None, None, None, None])})
    s = S.speedup(b.methods["agent_lab"], b.methods["random"], 2000, 2000, seed=0)
    assert s["baseline_censored"]
    assert s["point"] == pytest.approx(2000 / 100)  # budget stands in for the unknown, larger median
    assert "capped at the budget" in s["claim"]


def test_no_claim_when_the_agent_lab_mostly_fails():
    b = bench({"agent_lab": runs([100, None, None, None]), "bayes_opt": runs([500, 600, 700, 800])})
    s = S.speedup(b.methods["agent_lab"], b.methods["bayes_opt"], 2000, 2000, seed=0)
    assert s["focus_censored"] and not s["supported"]
    assert s["claim"].startswith("No speed-up claimed")


def test_no_claim_when_ci_includes_one_or_agent_is_slower():
    b = bench({"agent_lab": runs([900, 1000, 1100, 1200]), "bayes_opt": runs([400, 500, 600, 700])})
    s = S.speedup(b.methods["agent_lab"], b.methods["bayes_opt"], 2000, 2000, seed=0)
    assert not s["supported"] and s["claim"].startswith("No speed-up")


@pytest.mark.parametrize("raw, message", [
    ({"target_w_m2": "<Stanford P_net in our simulator>", "budget": 2000, "methods": {"a": runs([1])}}, "must be a number"),
    ({"target_w_m2": 40.0, "budget": 2000, "methods": {"a": runs([2500])}}, "integer in 1..2000"),
    ({"target_w_m2": 40.0, "budget": 2000, "methods": {"a": {"evals_to_target": [1, 2], "best_w_m2": [41]}}}, "2 evals"),
    ({"target_w_m2": 40.0, "budget": True, "methods": {"a": runs([1])}}, "positive integer"),
    ({"budget": 2000, "methods": {}}, "missing 'target_w_m2'"),
])
def test_bad_input_is_rejected_with_a_clear_message(raw, message):
    with pytest.raises(S.BenchmarkError, match=message):
        S.parse_benchmark(raw)


def test_inconsistent_input_produces_warnings():
    b = bench({"agent_lab": {"evals_to_target": [100, 200], "best_w_m2": [39.0, 41.0]},
               "random": runs([None, None, None])})
    text = " ".join(b.warnings)
    assert "best_w_m2 39.0 < target" in text
    assert "different numbers of runs" in text


def test_wilson_interval():
    lo, hi = S.wilson_interval(9, 10)
    assert 0.5 < lo < 0.9 < hi <= 1.0


def test_fake_data_is_stamped_everywhere():
    b = S.parse_benchmark(make_fake())
    r = S.analyze(b, n_boot=500)
    assert r["fake"]
    assert "FAKE DATA" in S.render_markdown(r)
    assert "FAKE DATA" in S.render_svg(r)


def test_cli_writes_all_outputs(tmp_path):
    src = tmp_path / "benchmark.json"
    src.write_text(json.dumps(make_fake()), encoding="utf-8")
    assert S.main([str(src), "--bootstrap", "500"]) == 0
    out = json.loads((tmp_path / "speedup.json").read_text(encoding="utf-8"))
    assert out["method_order"][0] == "agent_lab"
    assert set(out["curves"]) == set(out["methods"])
    assert (tmp_path / "speedup_chart.svg").read_text(encoding="utf-8").startswith("<svg")
    assert "# Measured improvement" in (tmp_path / "speedup.md").read_text(encoding="utf-8")


def test_cli_reports_bad_input(tmp_path, capsys):
    src = tmp_path / "benchmark.json"
    src.write_text(json.dumps({"target_w_m2": "TBD", "budget": 2000, "methods": {}}), encoding="utf-8")
    assert S.main([str(src)]) == 2
    assert "must be a number" in capsys.readouterr().err
