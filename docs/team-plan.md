# Team Plan — Radiative Cooling AI Lab

**Date:** Oct 3, 2026  
**Author:** @Zafar  

Four people, two tracks: Persons 1–2 prove the speed-up and then build the UI; Persons 3–4 build the Omnigent lab and everything else. Everyone reads the research primer first (15 minutes).

---

## Team split at a glance

Person 4's simulator comes first because everyone else depends on it. The arrows are the shared files each person hands over, defined in **Shared contracts** below.

```
Track A: prove the speed-up, then UI          Track B: build the lab
+--------------------------------------+      +--------------------------------------+
| Person 1 · Benchmark lead            | ---> | Person 4 · Physics bench + report    |
| Random search, Bayesian opt, 10 seeds|bench | tmm simulator, Stanford control, tools|
| Speed-up experiment, one command     |+targ | Then README, report, demo script     |
+--------------------------------------+      +--------------------------------------+
                   |                                             |
                   | benchmark.json                              | simulator tools
                   v                                             v
+--------------------------------------+      +--------------------------------------+
| Person 2 · Proof analyst, then UI    | <--- | Person 3 · Omnigent lead             |
| Stats, confidence interval, key chart|record| 5 agents + supervisor, handoffs      |
| Then the replay UI for the demo      |.jsonl| Policies: budget, control, human gate|
+--------------------------------------+      +--------------------------------------+
                   \                                             /
                    \                                           /
                     +-----------------------------------------+
                     | Submission: repo, agent specs,          |
                     | cited report, 2-min demo                |
                     +-----------------------------------------+
```

*team split · 2 tracks, 4 people, 4 handoffs*

---

## Research primer (everyone reads this)

We are building an AI lab that designs a thin coating that stays cooler than the surrounding air in full sunlight, using no electricity. Our goal: match the famous Stanford coating with fewer layers and cheaper materials, and show the AI lab gets there faster than standard search.

### The physics in four sentences

1. **Every warm surface radiates heat as infrared light.** Around 8–13 µm wavelength the atmosphere is almost transparent (the "atmospheric window"), so that heat escapes to cold outer space (about 3 K).
2. **A good cooling coating must do two things at once:** emit strongly at 8–13 µm, and reflect almost all sunlight (0.3–2.5 µm).
3. **A coating is a stack of very thin layers** (tens to thousands of nanometres) on a silver or aluminum mirror. Which materials, in what order, and how thick decide its color across all wavelengths.
4. **The transfer-matrix method computes exactly how a flat layer stack reflects and absorbs each wavelength.** One design takes milliseconds, so it is our "lab bench".

### The one number that decides everything: net cooling power

$$P_{\text{net}}(T) = P_{\text{rad}}(T) - P_{\text{atm}}(T_{\text{amb}}) - P_{\text{sun}} - P_{\text{cond+conv}}$$

- **$P_{\text{rad}}$:** heat the coating radiates out (depends on its emissivity at each wavelength and angle).
- **$P_{\text{atm}}$:** heat the sky radiates back onto it.
- **$P_{\text{sun}}$:** sunlight the coating absorbs (from the AM1.5 solar spectrum).
- **$P_{\text{cond+conv}}$:** heat leaking in from warm air. At $T = T_{\text{amb}}$ this term is zero, which is how papers report "cooling power".

Higher $P_{\text{net}}$ (in $\text{W/m}^2$) is better. Positive at $T = T_{\text{amb}}$ means it cools below air temperature.

### The benchmark we must reproduce, then beat under constraints

**Raman et al., Nature 2014:** 7 alternating layers of $\text{HfO}_2$ and $\text{SiO}_2$ on silver; reflects 97% of sunlight; 4.9 °C below ambient under sunlight above $850\text{ W/m}^2$; cooling power $40.1\text{ W/m}^2$ at ambient temperature.

### Our constraint (what makes our result new)

At most 5 layers, only cheap common materials (candidates: $\text{SiO}_2$, $\text{Al}_2\text{O}_3$, $\text{Si}_3\text{N}_4$, $\text{TiO}_2$, $\text{MgF}_2$) on $\text{Ag}$ or $\text{Al}$. $\text{HfO}_2$ is excluded because it is expensive.

### Glossary

| Term | Meaning |
|---|---|
| **Emissivity $\varepsilon(\lambda)$** | How strongly the coating emits (= absorbs) at wavelength $\lambda$, from 0 to 1 |
| **Solar reflectance** | Share of sunlight reflected; target $\ge 95\%$ |
| **Atmospheric window** | 8–13 µm band where the sky is transparent |
| **AM1.5** | Standard solar spectrum at the ground (ASTM G173) |
| **$n, k$** | Refractive index and absorption of a material per wavelength (refractiveindex.info) |
| **TMM** | Transfer-matrix method: exact optics of flat multilayer stacks (`tmm` Python package) |
| **Control** | Reproducing the Stanford result first, to prove our simulator is right |
| **Evaluation** | One simulation of one design = one "experiment"; the unit we count for speed-up |

---

## Shared contracts (agree in the first 30 minutes, then do not change)

These three interfaces let all four people work in parallel without waiting on each other. Person 4 owns the simulator API; Person 3 owns the record schema; Person 1 owns the benchmark output.

### 1. Simulator API (`lab/physics.py`, Person 4)

```python
def simulate_stack(materials: list[str], thicknesses_nm: list[float],
                   substrate: str = "Ag") -> dict:
    return {
        "p_net_w_m2": float,
        "solar_reflectance": float,
        "window_emissivity": float,
        "n_layers": int,
        "valid": bool,
        "reason": str,
    }

def optimize_thicknesses(materials: list[str], substrate: str = "Ag", budget:
                         int = 50, seed: int = 0) -> dict:
    return {
        "best": dict,
        "thicknesses_nm": list[float],
        "evaluations": int
    }
```

Every call to `simulate_stack` increments a global evaluation counter. That counter is the unit of the speed-up claim.

### 2. Research record (`runs/<run_id>/record.jsonl`, Person 3), one JSON object per line:

```json
{"id": "H2", "kind": "hypothesis", "agent": "hypothesis_agent", "t": 1759532000.1, "based_on": ["L1", "R3"], "content": {"claim": "Al2O3 plus SiO2 covers 8-13 um", "status": "proposed"}}
```

- **Kinds:** `literature`, `hypothesis`, `plan`, `experiment`, `result`, `verdict`, `approval`.
- **Status values:** `proposed`, `supported`, `refuted`, `inconclusive`. The UI reads only this file.

### 3. Benchmark output (`results/benchmark.json`, Person 1):

```json
{
  "target_w_m2": "<Stanford P_net in our simulator>",
  "budget": 2000,
  "seeds": 10,
  "methods": {
    "random": {
      "evals_to_target": [1520, 1890, null],
      "best_w_m2": [41.2, 39.8, 38.9]
    },
    "bayes_opt": {},
    "agent_lab": {}
  }
}
```

`null` means the method never reached the target within the budget. Never drop those runs.

---

## Person 1 — Benchmark lead (speed-up experiment)

**Mission:** produce the speed-up number and make it impossible to argue with. Same simulator, same constraints, same budget, many seeds, every run kept.

What "faster" means for us: the number of simulator evaluations needed to reach the target cooling power, under the 5-layer, cheap-materials constraint. Wall-clock time and human decisions are secondary metrics.

The target: the Stanford 7-layer design's $P_{\text{net}}$ computed in *our* simulator (not the paper's $40.1\text{ W/m}^2$), so every method is judged on the same bench. Person 4 gives you this number after the control passes.

### Tasks
- [ ] Write `bench/random_search.py`: random materials (from the allowed list), random order, random thicknesses within bounds; 1–5 layers.
- [ ] Write `bench/bayes_opt.py` using Optuna (TPE sampler): same search space, same bounds, same budget.
- [ ] Write `bench/run_all.py`: runs each method for 10 seeds with the same budget (start with 2,000 evaluations); writes `results/benchmark.json` in the shared format.
- [ ] Add an agent-lab entry: Person 3's lab runs the same 10 seeds; you read evaluation counts from its record.
- [ ] Add one ablation: the agent lab with the analyst's feedback turned off. If it gets slower, that proves the learning loop matters.
- [ ] Log wall-clock time and number of LLM calls per agent run, so cost is reported honestly too.
- [ ] Hand `benchmark.json` to Person 2 by the second checkpoint.

**Done when:** `python bench/run_all.py` reproduces every number from scratch in one command, with a fixed seed list.

### Watch out for
- Same search space for all methods: if the agent can pick a material that the baselines cannot, the comparison is unfair.
- Count the evaluations used inside thickness optimization. They are real experiments too.
- If the agent lab does not beat Bayesian optimization, report it. A plain, honest result still scores on rigor.

---

## Person 2 — Proof analyst, then UI/UX lead

**Mission, part 1 (proof):** turn Person 1's raw runs into a claim a judge can check in 10 seconds.  
**Part 2 (UI):** build the screen the demo is recorded on.

### Part 1 tasks: the statistics
- [ ] Compute per method: median evaluations-to-target, success rate (share of seeds that hit the target), best $P_{\text{net}}$ reached.
- [ ] $\text{Speed-up} = \text{median evaluations (baseline)} \div \text{median evaluations (agent lab)}$. Report it against both random search and Bayesian optimization.
- [ ] Add a 95% bootstrap confidence interval on the speed-up (resample seeds 10,000 times). Claim only what the lower bound supports: if the interval is 1.8×–3.4×, say "about 2.5×, at least 1.8×".
- [ ] Make the key chart: share of runs that reached the target vs evaluations used, one line per method. The method whose line rises first is faster; failed runs stay visible as a line that never reaches 100%.
- [ ] Write the one-paragraph "Measured improvement" text for the submission, with the exact command that reproduces it.

### Part 2 tasks: the UI (starts once the record format is fixed)
The UI replays `record.jsonl`; it never calls the agents itself. Reuse the existing Vite + React frontend.
- [ ] **Timeline:** every record entry in order, color-coded by agent, with `based_on` links so you can click from a verdict back to the evidence.
- [ ] **Hypothesis board:** each hypothesis with its status (`proposed`, `supported`, `refuted`) and the result that decided it.
- [ ] **Spectrum view:** emissivity vs wavelength for the best design vs the Stanford design, with the 8–13 µm window and the solar band shaded.
- [ ] **Speed-up panel:** the chart from part 1 plus the headline number and its interval.
- [ ] **Approval moment:** show the human-approval request and who approved it.
- [ ] Replay speed control so the demo video shows the whole loop in about 40 seconds.

**Done when:** a judge with no context opens the UI and can answer: what was asked, what failed, what changed, what was found, and how much faster.

---

## Person 3 — Omnigent lead (agents, handoffs, policies)

**Mission:** make the agents really run the science inside Omnigent. This is 30% of the score, the biggest single criterion.

### The agents (5 + supervisor)

| Agent | Decision it owns | Tools |
|---|---|---|
| **Supervisor (lab director)** | What happens next; when to stop | All sub-agents, `read_record` |
| **Literature agent** | Known designs, benchmark numbers, citations | `search_papers`, `write_record` |
| **Hypothesis agent** | Which materials, in what order, and why | `list_materials`, `material_properties`, `write_record` |
| **Planner** | Which of 2+ candidate tests to run, within budget | `read_record`, `budget_left`, `write_record` |
| **Analyst** | Supported or refuted; where to go next | `read_record`, `compare_to_benchmark`, `write_record` |
| **Safety / reviewer** | Needs human approval? Are claims backed by records? | `read_record`, `propose_fabrication` (gated) |

The simulator is a tool (`simulate_stack`, `optimize_thicknesses`), not an agent.

### Tasks
- [ ] Install Omnigent in WSL (Windows needs it: Python 3.12+, Node 22, tmux). Run `omni setup`, then `omni debby` to check it works.
- [ ] First milestone (about 1 hour): supervisor plus one sub-agent plus `write_record`, visible in the Omnigent web session.
- [ ] Write `lab/config.yaml` with all five sub-agents as `type: agent` tools, and Person 4's functions as `type: function` tools.
- [ ] Write one prompt file per agent in `lab/prompts/`. Each prompt says: the decision you own, what to read from the record, what to write, and "cite the record IDs you based this on".
- [ ] Make the planner always write 2+ candidate tests with expected gain and cost, then pick one and say why.
- [ ] Write `lab/policies.py`: `budget_cap` (DENY after the budget), `control_first` (DENY simulations until the control passed), `fabrication_gate` (ASK a human).
- [ ] Support a `--seed` and `--budget` flag so Person 1 can run the lab 10 times in the benchmark.
- [ ] *(Optional, worth points)* The planner launches 2–3 simulations in parallel for competing designs.

**Done when:** one command runs the full loop end to end, writes a complete `record.jsonl`, and at least one hypothesis is refuted and replaced in that record.

**Watch out for:** a Python loop making the real decisions while the LLMs only narrate. Judges will check that the choices come from agents.

---

## Person 4 — Physics bench, tools, report, and micro-VM sandboxes (Current Role)

**Mission:** build the trustworthy "lab bench" everyone else depends on, set up the micro-VM sandboxes (`sbx` docker) for isolated research execution that reports back to Person 3's Omnigent orchestration, and own the submission package.

### Infrastructure & Sandbox Architecture
- [ ] **Docker Sandbox (`sbx`) / Micro-VM setup:** Configure lightweight micro-VM sandboxes using `docker`/`sbx` to run isolated simulation and agent research execution.
- [ ] **Omnigent Orchestration Bridge:** Dynamic sandbox spawning and lifecycle management. The number of micro-VMs spawned will be dynamically determined and orchestrated by Person 3 (Omnigent lead).
- [ ] **State & Record Synchronization:** Micro-VMs report execution results and research telemetry back to the shared Omnigent research record.

### Tasks: the bench (first, fastest)
- [ ] `pip install tmm numpy scipy` and pull n, k data for Ag, Al, SiO2, Al2O3, Si3N4, TiO2, MgF2, HfO2 from the refractiveindex.info database (GitHub). Use only materials with data covering 0.3–25 µm.
- [ ] Load the AM1.5 solar spectrum (ASTM G173) and an atmospheric transmittance model for the sky. Write the assumption down.
- [ ] Implement `simulate_stack` and `optimize_thicknesses` exactly as in the shared contract, with the evaluation counter.
- [ ] **Control:** rebuild the Stanford 7-layer HfO2/SiO2 design. Check solar reflectance is about 97% and that cooling power is close to the published 40.1 W/m². Record the gap honestly and give Person 1 the computed target.
- [ ] **Unit tests:** a bare silver mirror reflects most sunlight; a design with no layers emits little at 8–13 µm; vacuum-like edge cases do not crash.
- [ ] Write `search_papers` (OpenAlex API) and `material_properties` tools for the agents.

### Tasks: the submission (from the middle block on)
- [ ] README: question, how to run, results table, limitations.
- [ ] Agent specs and policies doc (from Person 3's config and prompts).
- [ ] Final report: cited evidence, the record of one full run, measured improvement (from Person 2), next experiment (fabricate and test outdoors).
- [ ] Write and record the 2-minute demo script with Person 2's UI.

**Done when:** the control passes with a stated tolerance, tests pass, and the bench is handed off by the first checkpoint.

**Watch out for:** units. Wavelengths in µm vs nm and intensities per µm vs per nm are the most common bugs in this kind of code.

---

## Checkpoints

Short syncs where the whole team checks these gates. If a gate fails, fix it before building more.

1. **Sync 1 — contracts agreed:** The three shared formats are fixed; everyone has the repo running.
2. **Sync 2 — bench and handoff work:** The control passes; the Stanford $P_{\text{net}}$ in our simulator is known; one Omnigent handoff writes to the record; random search runs.
3. **Sync 3 — one full loop:** The lab runs end to end, with at least one refuted hypothesis that changes the next step. Bayesian optimization runs.
4. **Sync 4 — numbers frozen:** 10 seeds per method done; `benchmark.json` and the speed-up with its interval are final. No more changes to the lab after this.
5. **Sync 5 — submission:** UI replays a real run; README, report and agent specs done; 2-minute video recorded.

*Map these onto the brief's split: syncs 1–2 in the first 4 hours, sync 3 in the middle 14, syncs 4–5 in the final 6.*

---

## Rules for honest claims

The brief says the strength of the evidence matters more than the size of the multiplier. These rules apply to the README, the video and anything said on stage.

- **Every number has a command.** If we say "2.5×", one command in the repo reproduces it.
- **Claim the lower bound.** Say the speed-up with its confidence interval, never just the best seed.
- **Keep failures.** Runs that never hit the target stay in the data and the chart.
- **Label AI-generated hypotheses as hypotheses** until a simulation supports them.
- **Cite factual claims with links** (Nature 2014 benchmark, material data source, prior ML work).
- **State the assumptions:** flat ideal layers, a simplified sky model, simulated not fabricated.
- **Say what is still needed:** fabricate the best design and measure it outdoors before any real-world claim.

---

## Sources

- Raman et al., *Passive radiative cooling below ambient air temperature under direct sunlight*, Nature 2014
- Omnigent on GitHub
- Omnigent agent YAML spec
- Omnigent custom policies
- Omnigent install guide
- Radiative cooling technology with artificial intelligence (review)
- Hack-Nation 7th Global AI Hackathon, Agentic Scientific Discovery challenge brief
