# Hack-Nation 7th: Physics AI Lab

An AI-run physics laboratory for the **Agentic Scientific Discovery** challenge. Specialist
agents, orchestrated by **Omnigent**, investigate one physics question on a simulator. They
form hypotheses, design and run experiments, grade results, and **change their next experiment
because of what they measured**:

```
Question -> Evidence -> Hypothesis -> Experiment -> Result -> Updated decision -> Next experiment
```

**Question.** For a projectile with quadratic air drag, how does the range-maximising launch
angle θ\* depend on speed, mass, size, drag coefficient, air density and gravity? Is there a
compact law that predicts θ\* for unseen conditions within 0.1°?

**What the lab finds in one autonomous run** (≈2 s, 651 simulations; [full report](docs/results/example-run/report.md)):

| Step | Evidence | Decision it caused |
|---|---|---|
| Vacuum control | θ\* = 45.000°, range error 5e-15 | simulator trusted → test drag |
| Drag probe | θ\* = 43.5°, 40.9°, 37.4° for C_d = 0.1, 0.35, 1.0 | H1 "always 45°" **refuted** → look for a parameter reduction |
| Dimensional test | 5 objects on Earth/Mars/Venus, speeds 10–218 m/s, same β → identical θ\*; same speed → 14.5° spread | 6 inputs collapse to one number β = ρC_dA v0²/(2mg) |
| Prediction at β = 100 | best simple law missed by 2.2° | **escalate** to richer laws |
| Model discrimination | `cot θ* = 1 + 0.2565·ln(1 + 0.80β)` predicts the next two experiments before they run | stop scanning |
| Hold-out | 10 random unseen physical conditions, max error 0.028° | conclusion, **pending human review** |

**Measured speed-up** ([benchmark](docs/results/benchmark.md)): to map θ\*(β) within 0.1°, the
lab used **2.9× fewer simulations** than the cheapest manual grid that meets the target (651 vs
1,870), with 0 human decisions vs 17. One optimum takes 22 simulations instead of 110 for a
manual sweep, and is 25× more precise. The baseline was given the β reduction for free. We
report the measured factor, not a 10× claim.

## Quick start

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
python -m physics_lab discover            # autonomous run, narrated; writes runs/<time>/record.json + report.md
python -m physics_lab simulate --params '{"initial_velocity": 30, "drag_coefficient": 0.4}' --trajectory
python -m physics_lab benchmark           # AI lab vs manual protocol
pytest                                    # 28 tests: physics vs theory, analysis, loop, tools, policy
```

Omnigent (LLM agents, same tools, same record):

```bash
uv pip install -e ".[omnigent]"
omnigent setup                            # credentials (Anthropic API key or Claude subscription)
PYTHONPATH=. omnigent run omnigent/physics_lab.yaml -p "Start the investigation."
```

## Repository layout

| Path | What | Owner |
|---|---|---|
| `physics_lab/physics/` | simulator (RK4, quadratic drag), closed-form controls, presets | science |
| `physics_lab/experiments/` | experiment spec + runners (adaptive angle search, invariance test) | science |
| `physics_lab/analysis/` | candidate laws, leave-one-out ranking, next-experiment selection | science |
| `physics_lab/agents/autopilot.py` | deterministic specialist agents running the full loop (no LLM needed) | science |
| `physics_lab/tools.py`, `policies.py` | Omnigent function tools + human-approval policy | science |
| `physics_lab/record.py` | shared research record (lab notebook) every agent writes to | science |
| `omnigent/physics_lab.yaml` | Omnigent supervisor + 4 specialist sub-agents | science |
| `frontend/` (to add) | 3D world that replays experiments from the record | frontend team |
| `backend/` (to add) | hosting, API around `physics_lab` | Tom |

## Docs

- [docs/science-spec.md](docs/science-spec.md): question, physics model, experiments, measurements, epistemic labels
- [docs/agents.md](docs/agents.md): each agent's decision, tools, inputs and outputs; Omnigent setup
- [docs/interfaces.md](docs/interfaces.md): JSON contracts for the backend and the 3D frontend, plus a 2-minute demo script
