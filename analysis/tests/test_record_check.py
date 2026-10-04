import copy
import json

import pytest

from analysis import record_check as RC
from analysis.fake_record import fake_record


def run(entries):
    for n, e in enumerate(entries, start=1):
        e["_line"] = n
    return RC.check(entries)


def story(report):
    return {s["check"]: s["ok"] for s in report["story"]}


def test_fake_record_is_replayable_and_tells_the_whole_story():
    report = run(fake_record())
    assert report["errors"] == []
    assert all(story(report).values())
    board = report["summary"]["hypotheses"]
    assert board["H2"] == {"claim": board["H2"]["claim"], "status": "refuted", "decided_by": "V2"}
    assert report["summary"]["best_design"]["experiment"] == "E3"
    assert report["summary"]["fake"]


def test_status_change_by_repeating_an_id_is_rejected():
    rec = fake_record()
    again = copy.deepcopy(next(e for e in rec if e["id"] == "H2"))
    again["content"]["status"] = "refuted"
    rec.append(again)
    assert any("duplicate id" in m for m in run(rec)["errors"])


def test_evidence_must_exist_and_come_first():
    rec = fake_record()
    rec[2]["based_on"] = ["R3"]          # H1 cites a result that appears later
    rec[3]["based_on"] = ["X9"]          # P1 cites nothing real
    errors = " ".join(run(rec)["errors"])
    assert "comes later" in errors and "'X9' does not exist" in errors


def test_missing_content_fields_and_bad_values():
    rec = fake_record()
    r2 = next(e for e in rec if e["id"] == "R2")
    del r2["content"]["solar_reflectance"]
    v3 = next(e for e in rec if e["id"] == "V3")
    v3["content"]["status"] = "proposed"
    p2 = next(e for e in rec if e["id"] == "P2")
    p2["content"]["chosen"] = "C"
    errors = " ".join(run(rec)["errors"])
    assert "needs ['solar_reflectance']" in errors
    assert "verdict status must be one of" in errors
    assert "chosen 'C' is not one of the candidates" in errors


@pytest.mark.parametrize("mutate, failed_check", [
    (lambda r: [e for e in r if e["id"] not in ("V2",) and "V2" not in e["based_on"]],
     "at least one hypothesis is refuted"),
    (lambda r: [e for e in r if e["kind"] != "approval"], "a human approval decision is recorded"),
    (lambda r: [dict(e, based_on=[]) if e["id"] == "H4" else e for e in r if e["id"] != "P3"
                and e["id"] not in ("E3", "R3", "V3", "A1")], "a refutation changes the next step"),
])
def test_story_checks_catch_a_weak_demo(mutate, failed_check):
    assert story(run(mutate(fake_record())))[failed_check] is False


def test_control_must_pass_before_designs():
    rec = fake_record()
    order = [e["id"] for e in rec]
    e2 = rec.pop(order.index("E2"))
    rec.insert(order.index("E1"), dict(e2, based_on=[]))  # design experiment before the control
    assert story(run(rec))["control passes before any design experiment"] is False


def test_cli(tmp_path, capsys):
    path = tmp_path / "record.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in fake_record()) + "not json\n", encoding="utf-8")
    assert RC.main([str(path)]) == 1
    assert "not valid JSON" in capsys.readouterr().out
