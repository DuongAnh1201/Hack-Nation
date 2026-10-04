"""HTTP API around Person 4's simulator (lab.physics) and Person 2's analysis.

Website calls never touch the benchmark's evaluation counter or ledger: they use
lab.physics._evaluate directly (physics only), not simulate_stack.

Endpoints (all under /api):
  POST /simulate         one design -> metrics, power breakdown, merged spectrum
  POST /optimize         thickness optimization for a fixed material order
  GET  /materials        n, k curves and sources for every material
  GET  /control          Stanford reference: simulated vs published, gap explanation
  GET  /runs             research records found on disk
  GET  /runs/{id}/record record.jsonl lines as JSON
  GET  /runs/{id}/spectra spectra for every experiment in a record
  GET  /benchmark        speed-up statistics from results/benchmark.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import materials as _mat  # noqa: E402
from lab import physics as P  # noqa: E402

router = APIRouter(prefix="/api")

REFERENCE_MATERIALS = ("HfO2",)  # allowed only for reference designs, outside the search space
MAX_REFERENCE_LAYERS = 7
SOLAR_STEP = 5
RUNS_DIRS = [Path(os.getenv("LAB_RUNS_DIR", ROOT / "runs")), ROOT / "analysis" / "fixtures"]


class Design(BaseModel):
    materials: list[str]
    thicknesses_nm: list[float]
    substrate: str = "Ag"


class OptimizeRequest(BaseModel):
    materials: list[str]
    substrate: str = "Ag"
    budget: int = Field(50, ge=5, le=300)
    seed: int = 0


def _check(d: Design) -> tuple[bool, str | None]:
    """Physical validity (always enforced) and whether the design is inside the shared search space."""
    if not 1 <= len(d.materials) <= MAX_REFERENCE_LAYERS:
        raise HTTPException(422, f"1 to {MAX_REFERENCE_LAYERS} layers allowed, got {len(d.materials)}")
    if len(d.materials) != len(d.thicknesses_nm):
        raise HTTPException(422, "materials and thicknesses_nm must have the same length")
    known = set(P.ALLOWED_MATERIALS) | set(REFERENCE_MATERIALS)
    for m in d.materials:
        if m not in known:
            raise HTTPException(422, f"unknown material {m!r}; choose from {sorted(known)}")
    if d.substrate not in P.ALLOWED_SUBSTRATES:
        raise HTTPException(422, f"substrate must be one of {list(P.ALLOWED_SUBSTRATES)}")
    lo, hi = P.THICKNESS_BOUNDS_NM
    for t in d.thicknesses_nm:
        if not np.isfinite(t) or not lo <= t <= hi:
            raise HTTPException(422, f"thickness {t} nm outside [{lo:g}, {hi:g}] nm")
    ok, reason = P.validate_design(d.materials, d.thicknesses_nm, d.substrate)
    return ok, None if ok else reason


def _merged_spectrum(spectra: dict) -> dict:
    sol, th = P.SOLAR_GRID_UM, P.THERMAL_GRID_UM
    keep = np.arange(len(sol))[sol < th[0]][::SOLAR_STEP]
    lam = np.concatenate([sol[keep], th])
    eps = np.concatenate([np.asarray(spectra["solar_emissivity"])[keep], np.asarray(spectra["thermal_emissivity_near_normal"])])
    sky = np.concatenate([np.zeros(len(keep)), P._spec.zenith_transmittance(th)])
    return {
        "wavelength_um": [round(float(x), 4) for x in lam],
        "emissivity": [round(float(x), 4) for x in eps],
        "sky_transmittance": [round(float(x), 4) for x in sky],
    }


def conditions() -> dict:
    return {
        "t_ambient_k": P.T_AMBIENT_K,
        "sun": "ASTM G173 AM1.5 global, normal incidence, ~1000 W/m2",
        "sky": P._spec.atmosphere_model_name(),
        "solar_band_um": list(P.SOLAR_BAND_UM),
        "window_band_um": list(P.WINDOW_BAND_UM),
    }


def evaluate(d: Design, with_spectrum: bool = True) -> dict:
    in_space, reason = _check(d)
    r = P._evaluate(d.materials, d.thicknesses_nm, d.substrate)
    out = {k: r[k] for k in ("p_net_w_m2", "p_rad_w_m2", "p_atm_w_m2", "p_sun_w_m2", "solar_reflectance", "window_emissivity")}
    out.update(design=d.model_dump(), in_search_space=in_space, search_space_note=reason, conditions=conditions())
    if with_spectrum:
        out["spectrum"] = _merged_spectrum(r["_spectra"])
    return out


@router.post("/simulate")
def simulate(d: Design) -> dict:
    return evaluate(d)


@router.post("/optimize")
def optimize(req: OptimizeRequest) -> dict:
    """Bounded Powell search over thicknesses (same method as lab.physics.optimize_thicknesses),
    run outside the benchmark counter. Returns the per-evaluation history."""
    from scipy.optimize import minimize

    base = Design(materials=req.materials, thicknesses_nm=[100.0] * len(req.materials), substrate=req.substrate)
    in_space, reason = _check(base)
    if not in_space:
        raise HTTPException(422, f"design outside the search space: {reason}")
    lo, hi = P.THICKNESS_BOUNDS_NM
    rng = np.random.default_rng(req.seed)
    x0 = rng.uniform(lo, hi, size=len(req.materials))
    history: list[dict] = []
    best: dict = {"p": -np.inf, "x": None}

    class Spent(Exception):
        pass

    def objective(x):
        if len(history) >= req.budget:
            raise Spent
        x = np.clip(x, lo, hi)
        p = P._evaluate(req.materials, list(x), req.substrate)["p_net_w_m2"]
        if p > best["p"]:
            best.update(p=p, x=[round(float(v), 1) for v in x])
        history.append({"evaluation": len(history) + 1, "p_net_w_m2": p, "best_w_m2": best["p"]})
        return -p

    try:
        minimize(objective, x0, method="Powell", bounds=[(lo, hi)] * len(req.materials),
                 options={"maxfev": req.budget, "xtol": 0.5, "ftol": 1e-4})
    except Spent:
        pass
    result = evaluate(Design(materials=req.materials, thicknesses_nm=best["x"], substrate=req.substrate))
    return {"best": result, "thicknesses_nm": best["x"], "evaluations": len(history), "history": history,
            "method": "bounded Powell from a seeded random start (scipy), physics-only evaluations"}


@router.get("/materials")
def materials() -> list[dict]:
    lam = np.geomspace(0.3, 25.0, 240)
    out = []
    for name in (*P.ALLOWED_MATERIALS, *REFERENCE_MATERIALS, *P.ALLOWED_SUBSTRATES):
        nk = _mat.refractive_index(name, lam)
        out.append({
            "name": name,
            "role": "mirror" if name in P.ALLOWED_SUBSTRATES else "film",
            "in_search_space": name in P.ALLOWED_MATERIALS or name in P.ALLOWED_SUBSTRATES,
            "sources": [{"file": f, "from_um": a, "to_um": b} for f, a, b in _mat._SOURCES[name]],
            "wavelength_um": [round(float(x), 4) for x in lam],
            "n": [round(float(v.real), 4) for v in nk],
            "k": [round(float(v.imag), 5) for v in nk],
        })
    return out


@router.get("/control")
def control() -> dict:
    path = ROOT / "results" / "control.json"
    if not path.exists():
        raise HTTPException(404, "results/control.json not found; run python -m lab.control")
    return json.loads(path.read_text(encoding="utf-8"))


def _find_runs() -> dict[str, Path]:
    runs: dict[str, Path] = {}
    for base in RUNS_DIRS:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.jsonl")):
            run_id = p.parent.name if p.name == "record.jsonl" else p.stem
            runs.setdefault(run_id, p)
    return runs


def _load_record(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@router.get("/runs")
def runs() -> list[dict]:
    out = []
    for run_id, path in _find_runs().items():
        entries = _load_record(path)
        results = [e["content"].get("p_net_w_m2") for e in entries if e.get("kind") == "result"]
        totals = [e["content"].get("evaluations_total") for e in entries if e.get("kind") == "result"]
        out.append({
            "id": run_id,
            "entries": len(entries),
            "fake": any(e.get("_fake") for e in entries),
            "best_p_net": max((r for r in results if isinstance(r, (int, float))), default=None),
            "simulations": max((t for t in totals if isinstance(t, int)), default=None),
            "refuted": sum(1 for e in entries if e.get("kind") == "verdict" and e["content"].get("status") == "refuted"),
            "approvals": sum(1 for e in entries if e.get("kind") == "approval"),
            "modified": path.stat().st_mtime,
        })
    return sorted(out, key=lambda r: (r["fake"], -r["modified"]))


def _run_path(run_id: str) -> Path:
    path = _find_runs().get(run_id)
    if path is None:
        raise HTTPException(404, f"run {run_id!r} not found")
    return path


@router.get("/runs/{run_id}/record")
def run_record(run_id: str) -> list[dict]:
    return _load_record(_run_path(run_id))


@router.get("/runs/{run_id}/spectra")
def run_spectra(run_id: str) -> dict:
    from analysis.export_spectra import build

    exps = [e for e in _load_record(_run_path(run_id)) if e.get("kind") == "experiment"]
    return build(exps, P) if exps else {"designs": {}}


@router.get("/benchmark")
def benchmark() -> dict:
    from analysis.speedup import BenchmarkError, analyze, load_benchmark

    path = ROOT / "results" / "benchmark.json"
    if not path.exists():
        raise HTTPException(404, "results/benchmark.json not found")
    try:
        bench = load_benchmark(path)
        focus = next((m for m in ("agent_lab", "scripted_oracle") if m in bench.methods), next(iter(bench.methods)))
        result = analyze(bench, focus=focus, source="results/benchmark.json")
    except BenchmarkError as exc:
        raise HTTPException(422, str(exc)) from exc
    result.pop("colors", None)
    has_agents = "agent_lab" in bench.methods
    result["caveats"] = [
        ("agent_lab entries come from runs of the LLM agents." if has_agents else
         "No LLM agent-lab runs are in this benchmark yet. scripted_oracle is a scripted reference that knows "
         "the best material family in advance; it is an upper bound, not the agent lab."),
        "Medians use the evaluations by which half of the runs reached the target; failed runs count as not reached.",
        "Same simulator, search space and budget for every method; 95% CI by bootstrap over runs.",
    ]
    return result


@router.get("/sample")
def sample(n: int = 36, seed: int = 7) -> dict:
    """n random designs from the shared search space, simulated now (physics only, metrics without spectra).
    Used by the landing page to show what a search space looks like."""
    n = max(1, min(n, 120))
    rng = np.random.default_rng(seed)
    lo, hi = P.THICKNESS_BOUNDS_NM
    out = []
    for _ in range(n):
        k = int(rng.integers(P.MIN_LAYERS, P.MAX_LAYERS + 1))
        mats = [str(m) for m in rng.choice(P.ALLOWED_MATERIALS, k)]
        d = [round(float(x), 1) for x in rng.uniform(lo, hi, k)]
        sub = str(rng.choice(P.ALLOWED_SUBSTRATES))
        r = P._evaluate(mats, d, sub)
        out.append({"materials": mats, "thicknesses_nm": d, "substrate": sub, "p_net_w_m2": r["p_net_w_m2"],
                    "solar_reflectance": r["solar_reflectance"], "window_emissivity": r["window_emissivity"]})
    return {"seed": seed, "designs": out, "conditions": conditions()}
