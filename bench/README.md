# bench — speed-up benchmark (Person 1)

Measures how many simulator calls each method needs to reach the target cooling power, on one shared search space, and reports a speed-up only with a 95% confidence interval.

## Run

```bash
pip install optuna pytest
python -m pytest bench
python -m bench.run_all --seeds 100 --agent-seeds 20 --budget 2000 \
  --objective lab.physics:simulate_stack \
  --counter lab.physics:evaluation_count \
  --target <Stanford P_net in our simulator> \
  --target-source "Stanford 7-layer control, lab.physics, <date>" \
  --agent lab.bench_entry:run_agent \
  --ablation lab.bench_entry:run_agent_no_analyst
```

Without `--objective` it uses a placeholder score and writes `results/benchmark.placeholder.json` with `measured: false`. Never quote numbers from that file.

## Methods

| Method | What it is | Role in the claim |
| --- | --- | --- |
| `random` | Random materials, order, thicknesses, metal | Floor |
| `alternating` | High/low-index pairs on silver: the textbook design a human expert tries first | Expert-heuristic baseline |
| `tpe` | Optuna TPE (Bayesian optimization) on the same space | Strong automated baseline |
| `ga` | Genetic algorithm (tournament selection, layer crossover, thickness/material/layer mutations, elitism) | The standard method in the multilayer radiative-cooling literature |
| `agent` | Omnigent lab (Person 3) | Method under test |
| `ablation` | Same lab with the analyst feedback off | Proves the learning loop matters |

Literature using genetic algorithms for this problem: [Applied Optics 2023, daytime radiative cooling multilayers designed by ML and a genetic algorithm](https://opg.optica.org/ao/abstract.cfm?uri=ao-62-16-4359); review: [Optical multilayer thin film inverse design, from optimization to deep learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC11995089/).

## Rules that keep the number honest

- **Unit:** unique simulator calls. A repeated design is free. Calls inside thickness optimization count.
- **One search space** (`space.py`): 1–5 layers of SiO2, Al2O3, Si3N4, TiO2, MgF2, thickness 10–1000 nm (log scale, matches lab.physics), on Ag or Al. The agent can only submit `Stack` objects, so it cannot use anything the baselines cannot.
- **Budget is enforced:** a runner that tries to go over is cut off.
- **Bypass check:** with `--counter`, if the simulator ran more times than the bench saw, the run is marked `invalid` and every comparison is blocked.
- **Failed runs are kept.** Primary statistic: restricted mean evaluations to target (each run capped at the budget). Secondary: median, where a method miss counts as never.
- **Claim = low end of the 95% bootstrap interval.** If a baseline missed the target, the true speed-up is larger and the result is flagged `lower_bound_only`.
- **Provenance** is written into every result: command, versions, git commit, and a hash of every bench file.

## Seeds (why 100 and 20)

Search times vary a lot from seed to seed. Simulated on known distributions, 10 vs 10 seeds proves a true 3x speed-up only about half the time. With 100 baseline seeds (cheap) and 20 agent seeds, a true 3x gives a claim around 2x and is above 1x in essentially every trial. Use at least that.

## Output for Person 2 (`results/benchmark.json`)

- `rows`: every run, with `trajectory` (best P_net after each call), `evaluations_to_target`, `wall_seconds`, `llm_calls`.
- `summary`: per method success rate, restricted mean and median evaluations, best P_net, time, LLM calls.
- `curves.<method>.success`: share of runs that reached the target vs evaluations (the key chart).
- `curves.<method>.best_so_far`: median best P_net vs evaluations.
- `speedup.<method>.vs_<baseline>`: point, `ci95_low`, `ci95_high`, `claim`, misses, `median_based`.
- `headline`: ready-to-read sentences, only when `measured` is true.

## Interfaces needed from the team

**Person 4** — `lab/physics.py`:

```python
def simulate_stack(materials: list[str], thicknesses_nm: list[float], substrate: str = "Ag") -> dict:
    return {"p_net_w_m2": float, "valid": bool, ...}

def evaluation_count() -> int:
    ...
```

Plus: the Stanford target value and confirmation of the thickness bounds.

**Person 3** — `lab/bench_entry.py`:

```python
def run_agent(*, evaluate, seed: int, budget: int, target: float | None) -> dict:
    ...
    return {"llm_calls": n, "record_path": "runs/<run_id>/record.jsonl"}
```

Every simulation, including thickness tuning, must go through `evaluate(Stack(...))`. See `example_runner.py` for the shape (it is not an agent and is never reported as one).
