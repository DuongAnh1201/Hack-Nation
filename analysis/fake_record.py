"""Generate a FAKE research record (runs/<run_id>/record.jsonl) for building and testing
the replay UI before Person 3's real lab runs exist.

The top-level fields follow the README contract (id, kind, agent, t, based_on, content).
The per-kind `content` fields are Person 2's PROPOSAL for what the UI needs; agree them
with Person 3. Every line carries "_fake": true: the agent decisions are scripted.
The design results are real outputs of Person 4's simulator (lab.physics._evaluate,
analytic clear sky, 1000 W/m2 AM1.5) for these hand-picked designs. The benchmark
target of 55 W/m2 is a proposal: random designs reach it about once in 500 evaluations.

Run:  python -m analysis.fake_record --out analysis/fixtures/fake_record.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

T0 = 1_759_532_000.0
RAMAN = "Raman et al., Nature 515, 540-544 (2014)"
RAMAN_URL = "https://www.nature.com/articles/nature13883"
TARGET_W_M2 = 55.0


def fake_record() -> list[dict]:
    rows = [
        ("L1", "literature", "literature_agent", [], {
            "claim": "7 alternating HfO2/SiO2 layers on silver reflect 97% of sunlight and give 40.1 W/m2 "
                     "cooling power at ambient temperature",
            "source": RAMAN, "url": RAMAN_URL,
            "values": {"solar_reflectance": 0.97, "p_net_w_m2": 40.1}}),
        ("L2", "literature", "literature_agent", [], {
            "claim": "Machine learning has been used to optimize radiative-cooling coatings",
            "source": "Radiative cooling technology with artificial intelligence (review)",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11612785/"}),
        ("H1", "hypothesis", "hypothesis_agent", ["L1"], {
            "claim": "Control: our simulator reproduces the Stanford design's 97% solar reflectance within 2 points",
            "rationale": "No design claim is trusted until the bench reproduces a published result",
            "status": "proposed"}),
        ("P1", "plan", "planner", ["H1"], {
            "candidates": [
                {"test": "A", "description": "Run the Stanford 7-layer control", "expected_gain": "validates the bench",
                 "cost_evals": 1},
                {"test": "B", "description": "Skip the control and start the constrained search",
                 "expected_gain": "saves 1 evaluation", "cost_evals": 0}],
            "chosen": "A", "why": "Policy control_first: no design simulations before the control passes",
            "budget_left": 2000}),
        ("E1", "experiment", "supervisor", ["P1"], {
            "type": "control", "hypothesis": "H1",
            "materials": ["SiO2", "HfO2", "SiO2", "HfO2", "SiO2", "HfO2", "SiO2"],
            "thicknesses_nm": [230, 485, 688, 13, 73, 34, 54], "substrate": "Ag", "eval_budget": 1}),
        ("R1", "result", "supervisor", ["E1"], {
            "experiment": "E1", "p_net_w_m2": 11.83, "solar_reflectance": 0.977, "window_emissivity": 0.386,
            "n_layers": 7, "valid": True, "evaluations": 1, "evaluations_total": 1}),
        ("V1", "verdict", "analyst", ["R1", "L1"], {
            "hypothesis": "H1", "status": "supported",
            "reason": "97.7% vs 97% solar reflectance. Cooling power 11.8 vs published 40.1 W/m2: our sky model and "
                      "film data give lower 8-13 um emission (0.39); documented as a known gap",
            "next": f"Search cheap stacks against the benchmark target of {TARGET_W_M2:g} W/m2"}),
        ("H2", "hypothesis", "hypothesis_agent", ["V1", "L1"], {
            "claim": f"A 5-layer TiO2/SiO2 stack reaches {TARGET_W_M2:g} W/m2: TiO2's high index makes a strong solar mirror",
            "rationale": "High index contrast reflects sunlight with few layers; thick SiO2 emits near 9 um",
            "materials": ["TiO2", "SiO2"], "status": "proposed"}),
        ("H3", "hypothesis", "hypothesis_agent", ["V1"], {
            "claim": f"A 5-layer Al2O3/SiO2 stack reaches {TARGET_W_M2:g} W/m2: Al2O3 adds emission at 11-13 um",
            "rationale": "Al2O3 and SiO2 emit in different parts of the window and absorb little sunlight",
            "materials": ["Al2O3", "SiO2"], "status": "proposed"}),
        ("P2", "plan", "planner", ["H2", "H3"], {
            "candidates": [
                {"test": "A", "description": "Test H2: optimize TiO2/SiO2, 5 layers",
                 "expected_gain": "high: strongest solar mirror", "cost_evals": 50},
                {"test": "B", "description": "Test H3: optimize Al2O3/SiO2, 5 layers",
                 "expected_gain": "medium: weaker mirror", "cost_evals": 50}],
            "chosen": "A", "why": "Same cost; reflecting sunlight is the hardest part of daytime cooling",
            "budget_left": 1999}),
        ("E2", "experiment", "supervisor", ["P2", "H2"], {
            "type": "design", "hypothesis": "H2", "materials": ["TiO2", "SiO2", "TiO2", "SiO2", "SiO2"],
            "thicknesses_nm": [30, 66, 946, 784, 377], "substrate": "Ag", "eval_budget": 50}),
        ("R2", "result", "supervisor", ["E2"], {
            "experiment": "E2", "p_net_w_m2": 39.85, "solar_reflectance": 0.969, "window_emissivity": 0.757,
            "n_layers": 5, "valid": True, "evaluations": 50, "evaluations_total": 51}),
        ("V2", "verdict", "analyst", ["R2", "R1", "H2"], {
            "hypothesis": "H2", "status": "refuted",
            "reason": f"39.9 W/m2 < {TARGET_W_M2:g} target: emission is strong (0.76) but the stack absorbs 31 W/m2 of "
                      "sunlight vs 23 for the control; TiO2 itself absorbs below 0.4 um",
            "next": "Replace TiO2 with Si3N4: transparent in the near-UV and emits at 10-12 um"}),
        ("H4", "hypothesis", "hypothesis_agent", ["V2", "R2"], {
            "claim": f"4 layers of Si3N4/SiO2 on Ag reach {TARGET_W_M2:g} W/m2: Si3N4 emits at 10-12 um and SiO2 "
                     "near 9 um, with little solar absorption",
            "rationale": "Keeps H2's window coverage while removing the near-UV absorber",
            "materials": ["Si3N4", "SiO2"], "status": "proposed"}),
        ("P3", "plan", "planner", ["H4", "H3", "V2"], {
            "candidates": [
                {"test": "A", "description": "Test H4: Si3N4/SiO2, 4 layers", "expected_gain": "high",
                 "cost_evals": 50},
                {"test": "B", "description": "Test H3: Al2O3/SiO2, 5 layers", "expected_gain": "medium",
                 "cost_evals": 50}],
            "chosen": "A", "why": "V2 showed solar absorption is the bottleneck; H4 removes the absorber with one layer less",
            "budget_left": 1949}),
        ("E3", "experiment", "supervisor", ["P3", "H4"], {
            "type": "design", "hypothesis": "H4", "materials": ["Si3N4", "SiO2", "Si3N4", "SiO2"],
            "thicknesses_nm": [424, 406, 606, 72], "substrate": "Ag", "eval_budget": 50}),
        ("R3", "result", "supervisor", ["E3"], {
            "experiment": "E3", "p_net_w_m2": 56.66, "solar_reflectance": 0.978, "window_emissivity": 0.835,
            "n_layers": 4, "valid": True, "evaluations": 50, "evaluations_total": 101}),
        ("V3", "verdict", "analyst", ["R3", "H4", "V1"], {
            "hypothesis": "H4", "status": "supported",
            "reason": f"56.7 W/m2 >= {TARGET_W_M2:g} target with 4 cheap layers; absorbs 22 W/m2 of sunlight vs 31 for E2",
            "next": "Check robustness: thickness tolerances and a second sky model"}),
        ("A1", "approval", "safety", ["V3", "R3"], {
            "request": "Propose fabrication of the E3 design (4 layers Si3N4/SiO2 on Ag) for outdoor testing",
            "policy": "fabrication_gate", "decision": "approved", "approver": "human"}),
    ]
    out = []
    for i, (id_, kind, agent, based_on, content) in enumerate(rows):
        out.append({"id": id_, "kind": kind, "agent": agent, "t": T0 + 7.5 * i, "based_on": based_on,
                    "content": content, "_fake": True})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m analysis.fake_record", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="analysis/fixtures/fake_record.jsonl")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fake_record()), encoding="utf-8")
    print(f"wrote FAKE record to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
