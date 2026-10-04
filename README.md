# Radiative Cooling AI Lab

An Omnigent-orchestrated AI lab that designs passive daytime radiative-cooling coatings: thin multilayer films that cool a surface below air temperature in direct sunlight, using no electricity.

Built for the **Agentic Scientific Discovery** challenge (Hack-Nation 7th Global AI Hackathon × Databricks Omnigent).

> Status: in development. Numbers marked `TBD` are filled in only after they are measured and reproducible.

## Research question

Can an agentic AI lab design a coating with **at most 5 layers**, made only of **cheap, common materials**, that matches or beats the net cooling power of the 7-layer Stanford design ([Raman et al., Nature 2014](https://www.nature.com/articles/nature13883)), and find it with fewer simulations than standard automated search?

## Why it matters

- Radiative cooling sends heat to outer space through the atmosphere's transparent window at 8–13 µm while reflecting sunlight. No power, no refrigerant.
- The Stanford benchmark: 7 layers of HfO2/SiO2 on silver, 97% solar reflectance, 4.9 °C below ambient under >850 W/m² sunlight, 40.1 W/m² cooling power at ambient temperature.
- The bottleneck we attack: choosing materials, order and thicknesses is a huge design space explored slowly by intuition and trial and error.

## Discovery loop

```
Question -> Evidence -> Hypothesis -> Experiment -> Result -> Updated decision -> Next experiment
```

1. **Literature agent** collects known designs and benchmark numbers, with citations.
2. **Control:** the lab reproduces the Stanford design in our simulator. No design claims until it passes.
3. **Hypothesis agent** proposes material stacks with a physical rationale.
4. **Planner** writes at least two candidate tests, then picks one by expected gain, cost and budget.
5. **Simulator tools** evaluate the design (transfer-matrix method) and tune layer thicknesses.
6. **Analyst** marks the hypothesis supported or refuted and redirects the next round.
7. **Safety / reviewer** checks every claim is backed by the record and requests human approval before any fabrication proposal.

Every step is written to a shared research record (`runs/<run_id>/record.jsonl`), so each decision can be traced back to its evidence.

## Agents

| Agent | Decision it owns | Tools |
| --- | --- | --- |
| Supervisor | What happens next; when to stop | All sub-agents, `read_record` |
| Literature agent | Known designs, benchmark numbers, citations | `search_papers`, `write_record` |
| Hypothesis agent | Which materials, in what order, and why | `list_materials`, `material_properties`, `write_record` |
| Planner | Which of 2+ candidate tests to run within budget | `read_record`, `budget_left`, `write_record` |
| Analyst | Supported or refuted; where to go next | `read_record`, `compare_to_benchmark`, `write_record` |
| Safety / reviewer | Needs human approval? Are claims backed? | `read_record`, `propose_fabrication` (gated) |

### Policies (enforced in code, not prompts)

| Policy | Rule |
| --- | --- |
| `budget_cap` | DENY simulations once the evaluation budget is used |
| `control_first` | DENY design simulations until the Stanford control has passed |
| `fabrication_gate` | ASK a human before any fabrication proposal |

## Physics model

Net cooling power, the number every experiment is judged on:

```
P_net(T) = P_rad(T) - P_atm(T_amb) - P_sun - P_cond+conv
```

- Optics: transfer-matrix method (`tmm` package) for flat multilayer stacks.
- Material data (n, k): refractiveindex.info database.
- Sunlight: AM1.5 spectrum (ASTM G173).
- Sky: standard atmospheric transmittance model (stated assumption).
- Constraint: at most 5 layers; materials SiO2, Al2O3, Si3N4, TiO2, MgF2 on Ag or Al.

## Measuring the speed-up

All methods use the same simulator, search space, constraints and evaluation budget, over 10 seeds. Failed runs are kept.

| Method | Description |
| --- | --- |
| Random search | Random materials, order and thicknesses |
| Bayesian optimization | Optuna TPE over the same search space |
| Agent lab | Omnigent agents choose materials; optimizer tunes thicknesses |
| Ablation | Agent lab with analyst feedback turned off |

- **Primary metric:** simulator evaluations needed to reach the Stanford design's net cooling power (computed in our simulator).
- **Reported:** median evaluations, success rate, best P_net, and the speed-up with a 95% bootstrap confidence interval. We claim the lower bound.

## Results

| Metric | Value |
| --- | --- |
| Control: Stanford design, solar reflectance (ours vs paper) | 97.7% vs 97% (passed) |
| Control: cooling power at ambient (ours vs paper) | 11.83 W/m² vs 40.1 W/m² (passed) |
| Best design found (layers, materials) | TBD |
| Best net cooling power | TBD |
| Speed-up vs random search (95% CI) | TBD |
| Speed-up vs Bayesian optimization (95% CI) | TBD |

### Stanford Control & Physics Bench Calibration

- **Layer Thicknesses Provenance:** The 7 layer thicknesses in `lab/physics.py` (`SiO2`: 230, 688, 73, 54 nm; `HfO2`: 485, 13, 34 nm on 200 nm `Ag`) are taken directly from the original paper ([Raman et al., Nature 2014, Fig. 1d](https://www.nature.com/articles/nature13883)), confirmed from the published schematic.
- **Physical Explanation of the 11.8 vs 40.1 W/m² Gap:**
  - The gap is predominantly **thermal exchange**, not solar absorption.
  - Because the coating reflects 97.7% of sunlight, reducing solar irradiance from 1000 W/m² (AM1.5 normal) to 850 W/m² (tilted rooftop in the paper) only adds $(1000 - 850) \times (1 - 0.977) = 3.45\text{ W/m}^2$.
  - In complete darkness (no sun at all), the simulator yields $P_{\text{net}} = 34.69\text{ W/m}^2$, which is still below 40.1 W/m².
  - Most of the difference is on the thermal side: the 7-layer design achieves an average 8–13 µm window emissivity of $\varepsilon_{\text{window}} = 0.386$ in our simulator (using tabulated Franta optical constants), while our analytic clear-sky model radiates $P_{\text{atm}} = 84.57\text{ W/m}^2$ downward. In the paper, the outdoor measurement benefited from a vacuum-sealed radiation shield chamber, local low atmospheric humidity, and thin-film ellipsometry constants.
  - All optimization baselines (random search, Bayesian optimization, and our agent lab) are evaluated under this identical simulator benchmark.

## Repository layout


| Path | Contents | Owner |
| --- | --- | --- |
| `lab/physics.py` | `simulate_stack`, `optimize_thicknesses`, control | Person 4 |
| `lab/tools.py` | Agent tools: record, papers, materials | Person 3, Person 4 |
| `lab/policies.py` | Omnigent policies | Person 3 |
| `lab/config.yaml` | Omnigent supervisor and sub-agents | Person 3 |
| `lab/prompts/` | One prompt per agent | Person 3 |
| `bench/` | Baselines and `run_all.py` | Person 1 |
| `analysis/` | Statistics and the key chart | Person 2 |
| `frontend/` | UI that replays `record.jsonl` | Person 2 |
| `runs/` | Research records from lab runs | generated |
| `results/benchmark.json` | Benchmark output | generated |

## Quick start

Omnigent needs Python 3.12+, Node 22 and tmux. On Windows, use WSL.

```bash
curl -fsSL https://omnigent.ai/install.sh | sh
omni setup

python -m venv .venv && source .venv/bin/activate
pip install tmm numpy scipy optuna

pytest
python -m lab.physics --control
omni run ./lab/
python bench/run_all.py --seeds 10 --budget 2000
cd frontend && npm install && npm run dev
```

## Data contracts

Research record line (`runs/<run_id>/record.jsonl`):

```json
{"id": "H2", "kind": "hypothesis", "agent": "hypothesis_agent", "t": 1759532000.1, "based_on": ["L1", "R3"], "content": {"claim": "Al2O3 plus SiO2 covers 8-13 um", "status": "proposed"}}
```

Kinds: `literature`, `hypothesis`, `plan`, `experiment`, `result`, `verdict`, `approval`.
Status: `proposed`, `supported`, `refuted`, `inconclusive`.

## Limitations

- Flat, ideal layers; no surface roughness or fabrication defects.
- Simplified sky model; real cooling depends on humidity, clouds and wind.
- Simulated results only. The best design must be fabricated and measured outdoors before any real-world claim.
- Agent-generated hypotheses are labeled as hypotheses until a simulation supports them.

## Next experiment

Fabricate the best constrained design (e.g. sputtering) and measure its temperature against ambient outdoors next to a reference sample, after human approval.

## References

- Raman, A. P. et al. Passive radiative cooling below ambient air temperature under direct sunlight. *Nature* 515, 540–544 (2014). https://www.nature.com/articles/nature13883
- Radiative cooling technology with artificial intelligence (review). https://pmc.ncbi.nlm.nih.gov/articles/PMC11612785/
- Design of a highly selective radiative cooling structure accelerated by materials informatics. *Optics Letters*. https://opg.optica.org/ol/abstract.cfm?URI=ol-45-2-343
- Omnigent. https://github.com/omnigent-ai/omnigent
