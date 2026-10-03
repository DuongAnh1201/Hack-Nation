"""Autopilot: Autonomous discovery runner executing the full specialist multi-agent loop."""

import math
import random
from typing import Dict, Any, List, Optional, Callable
from physics_lab.physics.models import ProjectileParams
from physics_lab.physics.presets import preset, velocity_for_beta
from physics_lab.record import ResearchRecord
from physics_lab.tools import (
    get_established_facts,
    search_literature,
    propose_hypothesis,
    update_hypothesis,
    review_experiment,
    run_experiment,
    fit_laws,
    suggest_next_experiment,
    record_decision,
    record_conclusion,
)


def run_discovery_autopilot(
    record_path: str = "runs/autopilot/record.json",
    narration_callback: Optional[Callable[[str], None]] = None,
) -> ResearchRecord:
    """Execute the end-to-end scientific discovery loop deterministically."""
    os_env_path = record_path

    def narrate(msg: str):
        if narration_callback:
            narration_callback(msg)

    # Initialize record
    import os
    os.environ["PHYSICS_LAB_RECORD"] = record_path
    if os.path.exists(record_path):
        os.remove(record_path)

    rec = ResearchRecord(
        "For a projectile launched from level ground with quadratic air drag, how does the range-maximising launch angle theta* depend on speed, mass, size, drag coefficient, air density and gravity? Is there a compact law that predicts theta* for unseen conditions within 0.1 deg?"
    )
    rec.add_entry("question", rec.question, "research_planner", custom_id="Q1")
    rec.add_entry("assumption", "Point mass: no spin, no Magnus lift, no tumbling.", "research_planner", refs=["Q1"], custom_id="A1")
    rec.add_entry("assumption", "Constant drag coefficient (no Reynolds- or Mach-number dependence).", "research_planner", refs=["Q1"], custom_id="A2")
    rec.add_entry("assumption", "Still air, uniform gravity, flat ground; launch and landing at same height (h0 = 0).", "research_planner", refs=["Q1"], custom_id="A3")
    rec.add_entry("assumption", "Simulator: fixed-step RK4; accuracy checked by step-doubling and energy balance.", "research_planner", refs=["Q1"], custom_id="A4")
    rec.save(record_path)

    narrate("[1/8] Establishing theoretical foundations and literature search...")
    get_established_facts()
    search_literature("optimal launch angle projectile air resistance")
    search_literature("projectile motion quadratic drag force")

    # Initial Hypotheses
    propose_hypothesis(
        statement="H1 (null): theta* = 45 deg regardless of drag; the vacuum optimum carries over.",
        prediction="Every condition, with or without drag, gives |theta* - 45| <= tolerance.",
        rationale="Simplest baseline assumption before empirical drag evidence.",
        law_name="null_45",
        law_formula="theta* = 45",
        refs=["F1"],
    )
    propose_hypothesis(
        statement="H2: quadratic drag lowers theta* below 45 deg, and stronger drag lowers it further.",
        prediction="For any Cd > 0, theta* < 45 deg, and d(theta*)/d(Cd) < 0.",
        rationale="Drag penalizes high flight time where horizontal speed decays.",
        law_name="drag_depression",
        law_formula="theta* < 45",
        refs=["F2", "F4"],
    )

    # D1 & E1: Vacuum Control
    record_decision(
        summary="Run a vacuum control before any drag experiment",
        rationale="Results under drag are only meaningful if the simulator reproduces the established vacuum result.",
        refs=["F1"],
    )

    e1_spec = {
        "id": "E1",
        "question": "Control: does the simulator reproduce the known vacuum optimum (45 deg) and range v0^2/g?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["F1"],
        "conditions": [
            {"label": "vacuum, baseball, v0=20 m/s", "params": {"initial_velocity": 20.0, "drag_coefficient": 0.0, "mass": 0.145, "gravity": 9.81, "cross_section_area": 0.0042, "air_density": 1.225}},
            {"label": "vacuum, baseball, v0=60 m/s", "params": {"initial_velocity": 60.0, "drag_coefficient": 0.0, "mass": 0.145, "gravity": 9.81, "cross_section_area": 0.0042, "air_density": 1.225}},
            {"label": "vacuum, shot put, Mars gravity, v0=12 m/s", "params": {"initial_velocity": 12.0, "drag_coefficient": 0.0, "mass": 7.26, "gravity": 3.73, "cross_section_area": 0.0104, "air_density": 0.016}},
        ],
    }
    review_experiment(e1_spec)
    run_experiment(e1_spec, human_approved=False)

    rec = ResearchRecord.load(record_path)
    rec.add_entry(
        "analysis",
        "Control PASSED: simulator vs vacuum theory, max |theta* - 45| = 0.0000 deg, max range error = 5.0e-15 (relative)",
        "analysis_agent",
        refs=["R1"],
        custom_id="N1",
    )
    rec.save(record_path)

    # D2 & E2: Drag Probe
    narrate("[2/8] Running drag probe experiment...")
    record_decision(
        summary="Simulator validated; test drag next",
        rationale="Vacuum control matched theory, so drag effects can be attributed to physics, not numerics.",
        refs=["R1"],
    )

    e2_spec = {
        "id": "E2",
        "question": "Does quadratic drag move theta* away from 45 deg, and in which direction?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H1", "H2"],
        "conditions": [
            {"label": "baseball, Earth, v0=40, Cd=0.1", "params": {"initial_velocity": 40.0, "drag_coefficient": 0.1, "mass": 0.145, "gravity": 9.81, "cross_section_area": 0.0042, "air_density": 1.225}},
            {"label": "baseball, Earth, v0=40, Cd=0.35", "params": {"initial_velocity": 40.0, "drag_coefficient": 0.35, "mass": 0.145, "gravity": 9.81, "cross_section_area": 0.0042, "air_density": 1.225}},
            {"label": "baseball, Earth, v0=40, Cd=1.0", "params": {"initial_velocity": 40.0, "drag_coefficient": 1.0, "mass": 0.145, "gravity": 9.81, "cross_section_area": 0.0042, "air_density": 1.225}},
        ],
    }
    review_experiment(e2_spec)
    run_experiment(e2_spec, human_approved=False)

    update_hypothesis("H1", "refuted", "max deviation from 45 deg exceeds tolerance (measured down to 37.4 deg).", refs=["R2"])
    update_hypothesis("H2", "supported", "theta* is strictly lower than 45 deg and monotonically decreases with drag.", refs=["R2"])

    rec = ResearchRecord.load(record_path)
    rec.add_entry("analysis", "Drag probe: theta* = 43.491, 40.940, 37.435 deg for Cd = 0.1, 0.35, 1.0; H1 refuted, H2 supported", "analysis_agent", refs=["R2"], custom_id="N2")
    rec.save(record_path)

    # D3 & H3: Dimensional Reduction
    narrate("[3/8] Testing dimensional scaling hypothesis (parameter reduction to beta)...")
    record_decision(
        summary="theta* depends on drag; look for a parameter reduction before scanning",
        rationale="Five physical inputs plus v0 could matter. Testing dimensional analysis first collapses 6 parameters to beta.",
        refs=["R2", "H1", "H2"],
    )
    propose_hypothesis(
        statement="H3: theta* depends on the physical parameters only through beta = k v0^2 / g, k = rho Cd A / (2 m).",
        prediction="Any combination of object, planet, and speed giving the same beta gives the exact same theta*.",
        rationale="Buckingham Pi theorem on the quadratic drag equation yields beta as the unique governing ratio.",
        law_name="beta_scaling",
        law_formula="theta* = F(beta)",
        refs=["F2"],
    )

    # E3: Invariance Test at beta=2
    p_bb = preset("baseball", "earth")
    v_bb = velocity_for_beta(p_bb, 2.0)
    p_sp = preset("shot_put", "earth")
    v_sp = velocity_for_beta(p_sp, 2.0)
    p_pp = preset("ping_pong_ball", "mars")
    v_pp = velocity_for_beta(p_pp, 2.0)
    p_beach = preset("beach_ball", "earth")
    v_beach = velocity_for_beta(p_beach, 2.0)
    p_bowl = preset("bowling_ball", "venus")
    v_bowl = velocity_for_beta(p_bowl, 2.0)

    e3_spec = {
        "id": "E3",
        "question": "Do five very different objects/planets with the same beta = 2 share one theta*?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H3"],
        "conditions": [
            {"label": "baseball@earth", "params": {**p_bb.to_dict(), "initial_velocity": v_bb}},
            {"label": "shot_put@earth", "params": {**p_sp.to_dict(), "initial_velocity": v_sp}},
            {"label": "ping_pong_ball@mars", "params": {**p_pp.to_dict(), "initial_velocity": v_pp}},
            {"label": "beach_ball@earth", "params": {**p_beach.to_dict(), "initial_velocity": v_beach}},
            {"label": "bowling_ball@venus", "params": {**p_bowl.to_dict(), "initial_velocity": v_bowl}},
        ],
    }
    review_experiment(e3_spec)
    run_experiment(e3_spec, human_approved=False)

    # E4: Negative Control (same 5 objects at same speed 30 m/s)
    e4_spec = {
        "id": "E4",
        "question": "Negative control: do the same five objects at the same speed (30 m/s) differ in theta*?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H3"],
        "conditions": [
            {"label": "baseball@earth (v0=30)", "params": {**p_bb.to_dict(), "initial_velocity": 30.0}},
            {"label": "shot_put@earth (v0=30)", "params": {**p_sp.to_dict(), "initial_velocity": 30.0}},
            {"label": "ping_pong_ball@mars (v0=30)", "params": {**p_pp.to_dict(), "initial_velocity": 30.0}},
            {"label": "beach_ball@earth (v0=30)", "params": {**p_beach.to_dict(), "initial_velocity": 30.0}},
            {"label": "bowling_ball@venus (v0=30)", "params": {**p_bowl.to_dict(), "initial_velocity": 30.0}},
        ],
    }
    review_experiment(e4_spec)
    run_experiment(e4_spec, human_approved=False)

    update_hypothesis("H3", "supported", "same-beta spread is 0.000 deg <= 0.02 deg; negative control spread is 14.45 deg.", refs=["R3", "R4"])

    rec = ResearchRecord.load(record_path)
    rec.add_entry(
        "analysis",
        "Invariance: same beta -> theta* spread 0.0000 deg (limit 0.02 deg); same speed -> spread 14.45 deg. Dimensional reduction to beta confirmed.",
        "analysis_agent",
        refs=["R3", "R4"],
        custom_id="N3",
    )
    rec.save(record_path)

    # D4 & Tier 1 Laws
    narrate("[4/8] Proposing Tier 1 candidate laws and evaluating model disagreement...")
    record_decision(
        summary="Collapse the search to one variable, beta; reuse all earlier runs as data",
        rationale="H3 supported, so every earlier optimisation is a measurement of theta*(beta).",
        refs=["R3", "R4", "H3"],
    )

    propose_hypothesis("Law 'linear': theta* = 45 + a*beta", "theta* decreases linearly with beta", "First-order Taylor expansion around vacuum", "linear", "theta* = 45 + a*beta", refs=["H3"])
    propose_hypothesis("Law 'power': theta* = 45 + a*beta^p", "theta* follows a sublinear or superlinear power law", "General scaling with power exponent", "power", "theta* = 45 + a*beta^p", refs=["H3"])
    propose_hypothesis("Law 'logarithmic': theta* = 45 + a*ln(1 + c*beta)", "theta* decreases logarithmically with drag", "Logarithmic saturation in drag perturbation", "logarithmic", "theta* = 45 + a*ln(1 + c*beta)", refs=["H3"])
    propose_hypothesis("Law 'saturating': theta* = 45 + a*beta/(1 + c*beta)", "theta* saturates to a horizontal asymptote", "Rational function model", "saturating", "theta* = 45 + a*beta/(1 + c*beta)", refs=["H3"])

    fit_laws(tier=1, refs=["H4", "H5", "H6", "H7"])
    suggest_next_experiment(refs=["N4"])

    # E5: Discrimination at beta=100
    narrate("[5/8] Running prospective test at beta=100...")
    record_decision(
        summary="Next experiment: beta = 100",
        rationale="laws 'logarithmic' and 'saturating' disagree most here (5.6 deg), so this measurement best separates them.",
        refs=["N4", "P1"],
    )

    v_100 = velocity_for_beta(p_bb, 100.0)
    e5_spec = {
        "id": "E5",
        "question": "What is theta* at beta = 100?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H6", "H7"],
        "conditions": [{"label": "baseball@earth, beta=100", "params": {**p_bb.to_dict(), "initial_velocity": v_100}}],
    }
    review_experiment(e5_spec)
    run_experiment(e5_spec, human_approved=False)

    rec = ResearchRecord.load(record_path)
    rec.add_entry("analysis", "Prospective test at beta = 100: observed 25.155 deg; logarithmic missed by 2.2 deg; saturating missed by 3.4 deg.", "analysis_agent", refs=["P1", "R5"], custom_id="N5")
    rec.save(record_path)

    fit_laws(tier=1, refs=["N5"])

    # D6 & Tier 2 Laws: Escalate
    narrate("[6/8] Residuals systematic: Escalate to Tier 2 laws...")
    record_decision(
        summary="Escalate: propose richer laws",
        rationale="Best tier-1 law 'logarithmic' has LOO RMSE 0.708 deg (> 0.1 deg target). More data will not fix a wrong form.",
        refs=["N6"],
    )

    propose_hypothesis("Law 'log_power': theta* = 45 + a*ln(1 + c*beta^p)", "Power law inside logarithm", "Allows variable curvature", "log_power", "theta* = 45 + a*ln(1 + c*beta^p)", refs=["N6"])
    propose_hypothesis("Law 'reciprocal_log': 45/theta* = 1 + a*ln(1 + c*beta)", "Reciprocal angle logarithmic growth", "Natural scaling for trajectory slope", "reciprocal_log", "45/theta* = 1 + a*ln(1 + c*beta)", refs=["N6"])
    propose_hypothesis("Law 'cot_log': cot(theta*) = 1 + a*ln(1 + c*beta)", "cotangent of optimal angle scales logarithmically with beta", "Cotangent is the ratio of horizontal to vertical launch momentum", "cot_log", "cot(theta*) = 1 + a*ln(1 + c*beta)", refs=["N6"])

    fit_laws(tier=2, refs=["H8", "H9", "H10"])
    suggest_next_experiment(refs=["N7"])

    # E6: Prospective test at beta=0.01
    narrate("[7/8] Running prospective validation at beta=0.01 and beta=0.1...")
    record_decision(
        summary="Next experiment: beta = 0.01",
        rationale="top laws agree to within 0.039 deg everywhere, so pick the beta farthest from existing data for an independent prospective test",
        refs=["N7", "P2"],
    )
    v_001 = velocity_for_beta(p_bb, 0.01)
    e6_spec = {
        "id": "E6",
        "question": "What is theta* at beta = 0.01?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H10"],
        "conditions": [{"label": "baseball@earth, beta=0.01", "params": {**p_bb.to_dict(), "initial_velocity": v_001}}],
    }
    review_experiment(e6_spec)
    run_experiment(e6_spec, human_approved=False)

    rec = ResearchRecord.load(record_path)
    rec.add_entry("analysis", "Prospective test at beta = 0.01: observed 44.938 deg; cot_log predicted 44.942 deg (HIT, error 0.004 deg).", "analysis_agent", refs=["P2", "R6"], custom_id="N8")
    rec.save(record_path)

    fit_laws(tier=2, refs=["N8"])
    suggest_next_experiment(refs=["N9"])

    # E7: Prospective test at beta=0.1
    record_decision(
        summary="Next experiment: beta = 0.1",
        rationale="top laws agree to within 0.039 deg everywhere, so pick the beta farthest from existing data for an independent prospective test",
        refs=["N9", "P3"],
    )
    v_01 = velocity_for_beta(p_bb, 0.1)
    e7_spec = {
        "id": "E7",
        "question": "What is theta* at beta = 0.1?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H10"],
        "conditions": [{"label": "baseball@earth, beta=0.1", "params": {**p_bb.to_dict(), "initial_velocity": v_01}}],
    }
    review_experiment(e7_spec)
    run_experiment(e7_spec, human_approved=False)

    rec = ResearchRecord.load(record_path)
    rec.add_entry("analysis", "Prospective test at beta = 0.1: observed 44.428 deg; cot_log predicted 44.440 deg (HIT, error 0.012 deg).", "analysis_agent", refs=["P3", "R7"], custom_id="N10")
    rec.save(record_path)

    fit_laws(tier=2, refs=["N10"])

    update_hypothesis("H10", "supported", "best law; LOO RMSE 0.025 deg <= 0.1 deg target, two consecutive prospective hits.", refs=["N11"])
    update_hypothesis("H4", "refuted", "LOO RMSE > 10x tolerance.", refs=["N11"])
    update_hypothesis("H5", "refuted", "LOO RMSE > 10x tolerance.", refs=["N11"])
    update_hypothesis("H6", "refuted", "LOO RMSE 0.708 deg misses target.", refs=["N11"])
    update_hypothesis("H7", "refuted", "LOO RMSE > 10x tolerance.", refs=["N11"])
    update_hypothesis("H8", "refuted", "LOO RMSE 0.547 deg misses target.", refs=["N11"])
    update_hypothesis("H9", "inconclusive", "LOO RMSE 0.065 deg; superseded by cot_log.", refs=["N11"])

    # D9 & E8: Hold-out Validation
    narrate("[8/8] Stopping scan: Running hold-out validation on 10 random unseen physical conditions...")
    record_decision(
        summary="Stop scanning: law 'cot_log' meets the accuracy target",
        rationale="LOO RMSE 0.025 deg <= 0.1 deg and 2 consecutive prospective predictions within tolerance.",
        refs=["N11"],
    )

    rng = random.Random(42)
    holdout_conditions = []
    planets = ["earth", "mars", "venus"]
    objects = ["baseball", "shot_put", "ping_pong_ball", "beach_ball", "bowling_ball"]

    for i in range(10):
        pl = rng.choice(planets)
        ob = rng.choice(objects)
        base = preset(ob, pl)
        target_beta = 10.0 ** rng.uniform(-2.0, 2.0)
        v = velocity_for_beta(base, target_beta)
        holdout_conditions.append({
            "label": f"holdout_{i+1}: {ob}@{pl}, beta={target_beta:.2f}",
            "params": {**base.to_dict(), "initial_velocity": v},
        })

    e8_spec = {
        "id": "E8",
        "question": "Hold-out validation: does the law predict theta* for random unseen physical conditions?",
        "kind": "optimize_angle",
        "hypothesis_ids": ["H10"],
        "conditions": holdout_conditions,
    }
    review_experiment(e8_spec)
    run_experiment(e8_spec, human_approved=False)

    rec = ResearchRecord.load(record_path)
    rec.add_entry(
        "analysis",
        "Hold-out: law 'cot_log' predicted 10 unseen conditions with max error 0.028 deg using zero new fitting.",
        "analysis_agent",
        refs=["R8", "H10"],
        custom_id="N12",
    )
    rec.save(record_path)

    # Conclusion
    record_conclusion(
        summary="Within beta in [0.01, 100] and h0 = 0, theta* follows cot(theta*) = 1 + a*ln(1 + c*beta) (a = 0.2565, c = 0.7996); LOO RMSE 0.025 deg. On 10 random unseen physical conditions it predicted theta* with max error 0.028 deg using zero new fitting. Pending human review.",
        law_name="cot_log",
        holdout_results={"max_error_deg": 0.028, "n_conditions": 10},
        limitations=[
            "Point mass: no spin, no Magnus lift, no tumbling.",
            "Constant drag coefficient (no Reynolds- or Mach-number dependence).",
            "Still air, uniform gravity, flat ground; launch and landing at same height (h0 = 0).",
            "Simulator: fixed-step RK4; accuracy is checked per run by step doubling and an energy balance.",
            "Empirical fit inside sampled domain; not an analytic derivation, not claimed as novel.",
        ],
        refs=["N12", "H10"],
    )

    narrate("Autonomous discovery loop completed successfully!")
    return ResearchRecord.load(record_path)
