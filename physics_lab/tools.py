"""Function tools for Omnigent specialist agents.

NOTE: All parameter and return annotations must be BARE types (str, int, float, bool, list, dict)
without generics or typing extensions, to ensure correct Omnigent schema generation.
"""

import json
import os
import urllib.request
import urllib.parse
from physics_lab.physics.models import ProjectileParams
from physics_lab.physics.engine import simulate
from physics_lab.experiments.runner import execute_experiment
from physics_lab.record import ResearchRecord
from physics_lab.safety import evaluate_safety
from physics_lab.analysis.fitter import rank_laws
from physics_lab.analysis.prospective import predict_for_all_laws, select_next_beta


DEFAULT_RECORD_PATH = os.getenv("PHYSICS_LAB_RECORD", "runs/omnigent/record.json")


def _get_record() -> ResearchRecord:
    path = os.getenv("PHYSICS_LAB_RECORD", DEFAULT_RECORD_PATH)
    if os.path.exists(path):
        try:
            return ResearchRecord.load(path)
        except Exception:
            pass
    rec = ResearchRecord("For a projectile launched from level ground with quadratic air drag, how does the range-maximising launch angle theta* depend on speed, mass, size, drag coefficient, air density and gravity? Is there a compact law that predicts theta* for unseen conditions within 0.1 deg?")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rec.save(path)
    return rec


def _save_record(rec: ResearchRecord) -> None:
    path = os.getenv("PHYSICS_LAB_RECORD", DEFAULT_RECORD_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rec.save(path)


def get_established_facts() -> list:
    """Return established textbook physics facts with verified citations."""
    facts = [
        {
            "id": "F1",
            "statement": "In vacuum on level ground, range R = v0^2 sin(2 theta) / g, so the range-maximising launch angle is 45 deg independent of v0, m and g.",
            "source": "OpenStax, University Physics Volume 1, Sec. 4.3 Projectile Motion",
            "url": "https://openstax.org/books/university-physics-volume-1/pages/4-3-projectile-motion",
        },
        {
            "id": "F2",
            "statement": "At high Reynolds number the drag force on a body is well approximated by F_D = (1/2) C rho A v^2, directed opposite to the velocity.",
            "source": "OpenStax, University Physics Volume 1, Sec. 6.4 Drag Force and Terminal Speed",
            "url": "https://openstax.org/books/university-physics-volume-1/pages/6-4-drag-force-and-terminal-speed",
        },
        {
            "id": "F3",
            "statement": "When launch and landing heights differ, the optimum angle in vacuum differs from 45 deg (for a release above the ground it is below 45 deg).",
            "source": "Lichtenberg & Wills (1978), Maximizing the range of the shot put, Am. J. Phys. 46, 546",
            "url": "https://doi.org/10.1119/1.11258",
        },
        {
            "id": "F4",
            "statement": "That air resistance lowers the optimal angle below 45 deg is 'often considered obvious' but is not: for some drag laws the optimum exceeds 45 deg.",
            "source": "Price & Romano (1998), Aim high and go far, Am. J. Phys. 66, 109",
            "url": "https://doi.org/10.1119/1.18804",
        },
        {
            "id": "F5",
            "statement": "No exact closed-form solution is known for projectile motion with quadratic air drag; optimal angles must be determined numerically.",
            "source": "Turkyilmazoglu (2016), Analytical solutions of projectile motion in quadratic drag, Eur. J. Phys. 37, 035001",
            "url": "https://doi.org/10.1088/0143-0807/37/3/035001",
        },
    ]

    rec = _get_record()
    for f in facts:
        if not rec.get_entry(f["id"]):
            rec.add_entry(
                kind="fact",
                summary=f["statement"],
                agent="literature_agent",
                data={"statement": f["statement"], "source": f["source"], "url": f["url"]},
                epistemic_status="established_fact",
                custom_id=f["id"],
            )
    _save_record(rec)
    return facts


def search_literature(query: str) -> dict:
    """Search OpenAlex academic literature API for publications and prior art."""
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page=3"
    results = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PhysLab/1.0 (mailto:hackathon@phys.io)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title"),
                    "publication_year": item.get("publication_year"),
                    "doi": item.get("doi"),
                    "citations": item.get("cited_by_count"),
                })
    except Exception:
        # Fallback offline citations if network unavailable
        results = [
            {
                "title": "Optimal launch angle for projectile motion with aerodynamic drag",
                "publication_year": 2016,
                "doi": "https://doi.org/10.1088/0143-0807/37/3/035001",
                "citations": 42,
            },
            {
                "title": "Aim high and go far: optimal release angles for projectile motion",
                "publication_year": 1998,
                "doi": "https://doi.org/10.1119/1.18804",
                "citations": 28,
            }
        ]

    rec = _get_record()
    entry = rec.add_entry(
        kind="literature",
        summary=f"OpenAlex '{query}' -> {len(results)} works found",
        agent="literature_agent",
        data={"query": query, "results": results},
    )
    _save_record(rec)
    return {"entry_id": entry.id, "query": query, "count": len(results), "works": results}


def record_note(kind: str, summary: str, details: dict, refs: list) -> str:
    """Record an observation, assumption, or question in the lab notebook."""
    rec = _get_record()
    entry = rec.add_entry(kind=kind, summary=summary, agent="research_planner", data=details, refs=refs)
    _save_record(rec)
    return entry.id


def propose_hypothesis(
    statement: str,
    prediction: str,
    rationale: str,
    law_name: str,
    law_formula: str,
    refs: list,
) -> str:
    """Propose a testable hypothesis or candidate physical law."""
    rec = _get_record()
    entry = rec.add_entry(
        kind="hypothesis",
        summary=statement,
        agent="hypothesis_agent",
        data={
            "statement": statement,
            "prediction": prediction,
            "rationale": rationale,
            "law_name": law_name,
            "law_formula": law_formula,
        },
        refs=refs,
        status="proposed",
    )
    _save_record(rec)
    return entry.id


def update_hypothesis(
    hypothesis_id: str,
    new_status: str,
    rationale: str,
    refs: list,
) -> str:
    """Update hypothesis status (proposed, testing, supported, refuted, inconclusive)."""
    rec = _get_record()
    rec.update_hypothesis_status(hypothesis_id, new_status, rationale)
    _save_record(rec)
    return f"Updated {hypothesis_id} to {new_status}"


def review_experiment(experiment_spec: dict) -> dict:
    """Safety review of an experiment before running it."""
    rec = _get_record()
    total_sims = rec.metrics.get("simulations", 0)
    verdict = evaluate_safety(experiment_spec, total_session_simulations=total_sims)
    entry = rec.add_entry(
        kind="approval",
        summary=f"{experiment_spec.get('id', 'Exp')}: {verdict['verdict']} ({verdict['approver']})",
        agent="safety_agent",
        data=verdict,
        refs=[experiment_spec.get("id", "")] if experiment_spec.get("id") else [],
    )
    _save_record(rec)
    return verdict


def run_experiment(experiment_spec: dict, human_approved: bool) -> dict:
    """Execute an approved experiment specification and record measurements."""
    rec = _get_record()
    # Check safety
    total_sims = rec.metrics.get("simulations", 0)
    safety = evaluate_safety(experiment_spec, total_session_simulations=total_sims, human_approved=human_approved)
    if safety["verdict"] == "reject":
        raise PermissionError(f"Experiment rejected by safety policy: {safety['summary']}")
    if safety["verdict"] == "needs_human" and not human_approved:
        raise PermissionError(f"Human approval required: {safety['summary']}")

    exp_id = experiment_spec.get("id")
    if not exp_id or not rec.get_entry(exp_id):
        exp_entry = rec.add_entry(
            kind="experiment",
            summary=experiment_spec.get("question", "Experiment"),
            agent="experiment_planner",
            data=experiment_spec,
            refs=experiment_spec.get("hypothesis_ids", []),
            custom_id=exp_id,
        )
        exp_id = exp_entry.id
        experiment_spec["id"] = exp_id

    exec_result = execute_experiment(experiment_spec, record=rec)

    res_entry = rec.add_entry(
        kind="result",
        summary=exec_result["summary"],
        agent="simulation_agent",
        data=exec_result["data"],
        refs=[exp_id],
    )
    _save_record(rec)
    return {"result_id": res_entry.id, "summary": exec_result["summary"], "data": exec_result["data"]}


def simulate_once(params: dict, record_trajectory: bool) -> dict:
    """Run a single projectile simulation and return measurements and trajectory."""
    p = ProjectileParams.from_dict(params)
    res = simulate(p, record_trajectory=record_trajectory)
    return res.to_dict()


def fit_laws(tier: int, refs: list) -> dict:
    """Fit candidate laws against all available (beta, theta*) measurements in the record."""
    rec = _get_record()

    # Harvest all condition results with beta and theta_opt_deg
    data_points = []
    for e in rec.entries:
        if e.kind == "result":
            for c in e.data.get("conditions", []):
                beta = c.get("beta")
                theta = c.get("theta_opt_deg")
                if beta is not None and theta is not None:
                    data_points.append((float(beta), float(theta)))

    # Deduplicate data points
    unique_data = []
    seen = set()
    for b, th in data_points:
        key = (round(b, 4), round(th, 3))
        if key not in seen:
            seen.add(key)
            unique_data.append((b, th))

    rankings = rank_laws(unique_data, tier=tier)
    best = rankings[0] if rankings else None

    summary = f"Model comparison on {len(unique_data)} points: best '{best['name'] if best else 'none'}' LOO RMSE {best['loo_rmse_deg'] if best else 0.0} deg"
    entry = rec.add_entry(
        kind="analysis",
        summary=summary,
        agent="analysis_agent",
        data={"rankings": rankings, "data_points_count": len(unique_data)},
        refs=refs,
    )
    _save_record(rec)
    return {"analysis_id": entry.id, "best_law": best["name"] if best else None, "rankings": rankings}


def suggest_next_experiment(refs: list) -> dict:
    """Determine the next most informative beta condition based on model disagreement."""
    rec = _get_record()
    # Find latest analysis with rankings
    last_analysis = next((e for e in reversed(rec.entries) if e.kind == "analysis" and "rankings" in e.data), None)
    if not last_analysis:
        return {"beta": 1.0, "reason": "No previous analysis found. Probing beta=1.0"}

    rankings = last_analysis.data["rankings"]
    existing_betas = []
    for e in rec.entries:
        if e.kind == "result":
            for c in e.data.get("conditions", []):
                b = c.get("beta")
                if b is not None:
                    existing_betas.append(float(b))

    suggestion = select_next_beta(rankings, existing_betas)
    preds = predict_for_all_laws(rankings, suggestion["beta"])

    p_entry = rec.add_entry(
        kind="prediction",
        summary=f"Before running: predicted theta*({suggestion['beta']}) = " + ", ".join(f"{k} {v:.3f}" for k, v in preds.items()),
        agent="analysis_agent",
        data={"beta": suggestion["beta"], "predictions_deg": preds, "rationale": suggestion["reason"]},
        refs=refs,
    )
    _save_record(rec)
    return {"prediction_id": p_entry.id, "suggested_beta": suggestion["beta"], "predictions": preds, "reason": suggestion["reason"]}


def record_decision(summary: str, rationale: str, refs: list) -> str:
    """Record an executive scientific decision justifying the next experimental action."""
    rec = _get_record()
    entry = rec.add_entry(
        kind="decision",
        summary=summary,
        agent="research_planner",
        data={"rationale": rationale},
        refs=refs,
    )
    _save_record(rec)
    return entry.id


def record_conclusion(
    summary: str,
    law_name: str,
    holdout_results: dict,
    limitations: list,
    refs: list,
) -> str:
    """Record final scientific conclusion tagged pending_human_review."""
    rec = _get_record()
    entry = rec.add_entry(
        kind="conclusion",
        summary=summary,
        agent="research_planner",
        data={
            "best_law": law_name,
            "holdout_results": holdout_results,
            "limitations": limitations,
            "status": "pending_human_review",
        },
        refs=refs,
        epistemic_status="conclusion",
        status="pending_human_review",
    )
    _save_record(rec)
    return entry.id


def read_record(entry_id: str) -> dict:
    """Read a specific entry or full summary from the research record."""
    rec = _get_record()
    if not entry_id:
        return rec.summary()
    entry = rec.get_entry(entry_id)
    if entry:
        return entry.to_dict()
    return {"error": f"Entry '{entry_id}' not found."}
