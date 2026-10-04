"""Check a research record (runs/<run_id>/record.jsonl) before the UI replays it.

Two levels:
  errors - the UI cannot replay the file (bad JSON, missing fields, unknown kinds,
           links to entries that do not exist or come later)
  story  - what the judges look for: the control passes before any design, the
           planner chooses between 2+ tests, a hypothesis is refuted and that
           changes the next step, every verdict rests on a result, a human approval

The top-level fields are the README contract. The per-kind `content` fields are
Person 2's proposal of what the UI needs (see analysis/fake_record.py); agree them
with Person 3.

Run:  python -m analysis.record_check runs/<run_id>/record.jsonl [--json summary.json] [--strict]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TOP_FIELDS = {"id": str, "kind": str, "agent": str, "t": (int, float), "based_on": list, "content": dict}
KINDS = ("literature", "hypothesis", "plan", "experiment", "result", "verdict", "approval")
STATUSES = ("proposed", "supported", "refuted", "inconclusive")
VERDICT_STATUSES = ("supported", "refuted", "inconclusive")
DECISIONS = ("approved", "denied", "pending")
AGENTS = ("supervisor", "literature_agent", "hypothesis_agent", "planner", "analyst", "safety")
CONTENT_REQUIRED = {
    "literature": ("claim", "source"),
    "hypothesis": ("claim", "status"),
    "plan": ("candidates", "chosen", "why"),
    "experiment": ("type", "materials", "thicknesses_nm", "substrate"),
    "result": ("experiment", "p_net_w_m2", "solar_reflectance", "evaluations"),
    "verdict": ("hypothesis", "status", "reason"),
    "approval": ("request", "decision"),
}


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def load_record(path: str | Path) -> tuple[list[dict], list[str]]:
    entries, errors = [], []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(obj, dict):
            errors.append(f"line {n}: must be a JSON object")
            continue
        obj["_line"] = n
        entries.append(obj)
    return entries, errors


def check(entries: list[dict]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    by_id: dict[str, dict] = {}
    order: dict[str, int] = {}

    def err(e: dict, msg: str) -> None:
        errors.append(f"line {e['_line']} ({e.get('id', '?')}): {msg}")

    def warn(e: dict, msg: str) -> None:
        warnings.append(f"line {e['_line']} ({e.get('id', '?')}): {msg}")

    # pass 1: top-level fields, ids
    valid = []
    for e in entries:
        bad = [f for f, typ in TOP_FIELDS.items() if not isinstance(e.get(f), typ) or isinstance(e.get(f), bool)]
        if bad:
            err(e, f"missing or wrong-typed field(s) {bad}; contract: id, kind, agent, t, based_on, content")
            continue
        if e["kind"] not in KINDS:
            err(e, f"unknown kind {e['kind']!r}; allowed {list(KINDS)}")
            continue
        if e["id"] in by_id:
            err(e, f"duplicate id (first used on line {by_id[e['id']]['_line']}); a status change must be a new "
                   "'verdict' entry, not a repeated id")
            continue
        by_id[e["id"]] = e
        order[e["id"]] = len(valid)
        valid.append(e)

    # pass 2: links, time, per-kind content
    last_t, last_total = -math.inf, -1
    for e in valid:
        c, k = e["content"], e["kind"]
        for ref in e["based_on"]:
            if ref not in by_id:
                err(e, f"based_on {ref!r} does not exist")
            elif order[ref] >= order[e["id"]]:
                err(e, f"based_on {ref!r} comes later in the record (evidence must come first)")
        if e["t"] < last_t:
            warn(e, "timestamp goes backwards")
        last_t = max(last_t, e["t"])
        if e["agent"] not in AGENTS:
            warn(e, f"unknown agent {e['agent']!r} (UI colours: {list(AGENTS)})")
        missing = [f for f in CONTENT_REQUIRED[k] if f not in c]
        if missing:
            err(e, f"{k} content needs {missing} (the UI shows these)")
            continue

        if k == "hypothesis" and c["status"] not in STATUSES:
            err(e, f"status {c['status']!r} not in {list(STATUSES)}")
        elif k == "plan":
            cands = c["candidates"] if isinstance(c["candidates"], list) else []
            tests = [x.get("test") for x in cands if isinstance(x, dict)]
            if not cands or None in tests:
                err(e, "candidates must be a list of objects with a 'test' name")
            elif c["chosen"] not in tests:
                err(e, f"chosen {c['chosen']!r} is not one of the candidates {tests}")
        elif k == "experiment":
            if c["type"] not in ("control", "design"):
                err(e, f"type must be 'control' or 'design', got {c['type']!r}")
            if not isinstance(c["materials"], list) or not isinstance(c["thicknesses_nm"], list) \
                    or len(c["materials"]) != len(c["thicknesses_nm"]):
                err(e, "materials and thicknesses_nm must be lists of the same length")
            h = c.get("hypothesis")
            if h is not None and by_id.get(h, {}).get("kind") != "hypothesis":
                err(e, f"hypothesis {h!r} is not a hypothesis entry")
        elif k == "result":
            if by_id.get(c["experiment"], {}).get("kind") != "experiment":
                err(e, f"experiment {c['experiment']!r} is not an experiment entry")
            for f in ("p_net_w_m2", "solar_reflectance"):
                if not _num(c[f]):
                    err(e, f"{f} must be a finite number")
            if _num(c["solar_reflectance"]) and not 0 <= c["solar_reflectance"] <= 1:
                err(e, "solar_reflectance must be between 0 and 1")
            if not isinstance(c["evaluations"], int) or c["evaluations"] < 0:
                err(e, "evaluations must be a non-negative integer")
            total = c.get("evaluations_total")
            if isinstance(total, int):
                if total < last_total:
                    warn(e, "evaluations_total decreased")
                last_total = max(last_total, total)
        elif k == "verdict":
            if by_id.get(c["hypothesis"], {}).get("kind") != "hypothesis":
                err(e, f"hypothesis {c['hypothesis']!r} is not a hypothesis entry")
            if c["status"] not in VERDICT_STATUSES:
                err(e, f"verdict status must be one of {list(VERDICT_STATUSES)}")
        elif k == "approval" and c["decision"] not in DECISIONS:
            err(e, f"decision must be one of {list(DECISIONS)}")

    story = judge_story(valid, by_id, order)
    return {"errors": errors, "warnings": warnings, "story": story, "summary": summarize(valid, by_id)}


def judge_story(entries: list[dict], by_id: dict[str, dict], order: dict[str, int]) -> list[dict]:
    def of(kind: str) -> list[dict]:
        return [e for e in entries if e["kind"] == kind]

    def item(name: str, ok: bool, detail: str) -> dict:
        return {"check": name, "ok": ok, "detail": detail}

    out = []
    exps = [e for e in of("experiment") if isinstance(e["content"], dict)]
    controls = [e for e in exps if e["content"].get("type") == "control"]
    designs = [e for e in exps if e["content"].get("type") == "design"]
    passed = [v for v in of("verdict") if v["content"].get("status") == "supported"
              and any(by_id.get(ex.get("content", {}).get("hypothesis"), {}).get("id") == v["content"].get("hypothesis")
                      for ex in controls)]
    first_design = min((order[d["id"]] for d in designs), default=math.inf)
    ok = bool(passed) and order[passed[0]["id"]] < first_design
    out.append(item("control passes before any design experiment", ok,
                    f"control verdict {passed[0]['id']}" if passed else "no supported control verdict found"))

    plans = of("plan")
    few = [p["id"] for p in plans if len(p["content"].get("candidates", [])) < 2]
    out.append(item("planner chooses between 2+ candidate tests", bool(plans) and not few,
                    f"{len(plans)} plans" + (f"; fewer than 2 candidates in {few}" if few else "")))

    refuted = [v for v in of("verdict") if v["content"].get("status") == "refuted"]
    out.append(item("at least one hypothesis is refuted", bool(refuted),
                    ", ".join(f"{v['id']} refutes {v['content'].get('hypothesis')}" for v in refuted) or "none"))

    changed = [(v["id"], e["id"]) for v in refuted for e in entries
               if v["id"] in e["based_on"] and e["kind"] in ("hypothesis", "plan")]
    out.append(item("a refutation changes the next step", bool(changed),
                    ", ".join(f"{e} is based on {v}" for v, e in changed) or "no hypothesis/plan cites a refuting verdict"))

    unbased = [v["id"] for v in of("verdict") if not any(by_id.get(r, {}).get("kind") == "result" for r in v["based_on"])]
    out.append(item("every verdict rests on a result", bool(of("verdict")) and not unbased,
                    f"without a result: {unbased}" if unbased else f"{len(of('verdict'))} verdicts"))

    approvals = [a for a in of("approval") if a["content"].get("decision") in ("approved", "denied")]
    out.append(item("a human approval decision is recorded", bool(approvals),
                    ", ".join(f"{a['id']}: {a['content'].get('decision')} by {a['content'].get('approver', '?')}"
                              for a in approvals) or "none"))

    loose = [e["id"] for e in entries if e["kind"] in ("hypothesis", "plan", "verdict") and not e["based_on"]]
    out.append(item("hypotheses, plans and verdicts cite their evidence", not loose,
                    f"no based_on: {loose}" if loose else "all cite record ids"))
    return out


def summarize(entries: list[dict], by_id: dict[str, dict]) -> dict[str, Any]:
    board = {}
    for e in entries:
        c = e["content"]
        if e["kind"] == "hypothesis":
            board[e["id"]] = {"claim": c.get("claim"), "status": c.get("status"), "decided_by": None}
        elif e["kind"] == "verdict" and c.get("hypothesis") in board:
            board[c["hypothesis"]].update(status=c.get("status"), decided_by=e["id"])
    best = None
    for e in entries:
        c = e["content"]
        exp = by_id.get(c.get("experiment"), {}) if e["kind"] == "result" else {}
        if exp.get("content", {}).get("type") == "design" and c.get("valid", True) and _num(c.get("p_net_w_m2")):
            if best is None or c["p_net_w_m2"] > best["p_net_w_m2"]:
                best = {"result": e["id"], "experiment": exp["id"], "p_net_w_m2": c["p_net_w_m2"],
                        "solar_reflectance": c.get("solar_reflectance"), "materials": exp["content"].get("materials"),
                        "substrate": exp["content"].get("substrate"), "n_layers": len(exp["content"].get("materials", []))}
    totals = [e["content"].get("evaluations_total") for e in entries if e["kind"] == "result"]
    return {
        "fake": any(e.get("_fake") for e in entries),
        "entries": len(entries),
        "by_kind": dict(Counter(e["kind"] for e in entries)),
        "by_agent": dict(Counter(e["agent"] for e in entries)),
        "hypotheses": board,
        "best_design": best,
        "evaluations_total": max((t for t in totals if isinstance(t, int)), default=None),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m analysis.record_check", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record")
    ap.add_argument("--json", help="also write the summary for the UI to this path")
    ap.add_argument("--strict", action="store_true", help="exit 1 if a story check fails too")
    args = ap.parse_args(argv)
    try:
        entries, parse_errors = load_record(args.record)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = check(entries)
    report["errors"] = parse_errors + report["errors"]

    s = report["summary"]
    if s["fake"]:
        print("FAKE DATA: this record is invented, for development only.")
    print(f"{s['entries']} entries · " + ", ".join(f"{k} {v}" for k, v in s["by_kind"].items()))
    print(f"\nErrors ({len(report['errors'])}):" + ("" if report["errors"] else " none, the UI can replay this file"))
    for m in report["errors"]:
        print(f"  ✗ {m}")
    if report["warnings"]:
        print(f"\nWarnings ({len(report['warnings'])}):")
        for m in report["warnings"]:
            print(f"  ! {m}")
    print("\nStory (what the judges look for):")
    for it in report["story"]:
        print(f"  {'✓' if it['ok'] else '✗'} {it['check']}: {it['detail']}")
    print("\nHypothesis board:")
    for hid, h in s["hypotheses"].items():
        print(f"  {hid} [{h['status']}{' by ' + h['decided_by'] if h['decided_by'] else ''}] {h['claim']}")
    if s["best_design"]:
        b = s["best_design"]
        print(f"\nBest design: {b['experiment']} {'/'.join(b['materials'])} on {b['substrate']} "
              f"({b['n_layers']} layers) -> {b['p_net_w_m2']} W/m², solar reflectance {b['solar_reflectance']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {args.json}")
    story_ok = all(it["ok"] for it in report["story"])
    return 1 if report["errors"] or (args.strict and not story_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
