# Agent specification

Two runtimes share the same tools and the same research record:

- **Omnigent** (`omnigent/physics_lab.yaml`): LLM agents (Claude Opus 5.5 via the `claude-sdk`
  harness) decide what to do; Python tools do the physics. This is the hackathon submission path.
- **Autopilot** (`physics_lab/agents/autopilot.py`): the same roles as deterministic Python
  classes. Use it as a reproducible reference run, as the benchmark's AI arm, and as a demo
  fallback with no API key or network.

Agents exchange outputs through the **research record** (`ResearchRecord`). Every entry has an id
(H3, E5, R5, P2, D6, ...), and later entries cite earlier ones in `refs`. In Omnigent the sub-agents
also reply to the planner, and those replies quote record ids.

| Agent | Scientific decision it owns | Tools | Inputs | Outputs (record kinds) |
|---|---|---|---|---|
| research_planner (supervisor) | What to do next and when to stop | all; delegates | everything in the record | `question`, `assumption`, `decision`, `conclusion` |
| literature_agent | Which facts and prior work constrain the question | `get_established_facts`, `search_literature` (OpenAlex), `record_note` | question | `fact` (with source), `literature` |
| hypothesis_agent | Which explanations are worth testing | `propose_hypothesis`, `fit_laws` | facts, results, analyses | `hypothesis` with falsifiable prediction (optionally a fittable law expression) |
| experiment_planner | Which conditions test the open hypotheses most efficiently | `review_experiment`, `run_experiment`, `simulate_once`, `suggest_next_experiment` | open hypotheses, model disagreement | `experiment` (with predictions written first), `result` |
| safety agent | May this run, does it need a human | `review_experiment` + Omnigent policy `experiment_gate` | experiment spec, budget used | `approval` (approve / needs human / reject, warnings) |
| simulation agent | None scientifically; executes faithfully | `run_experiment` internals | approved spec | `result` with raw measurements and search traces |
| analysis_agent | What the evidence says; where uncertainty is largest | `fit_laws`, `update_hypothesis`, `suggest_next_experiment` | results, predictions | `analysis`, `prediction`, hypothesis status changes |

## Where the loop adapts (result → changed decision)

1. Control fails → stop (fix the simulator). Control passes → drag experiments.
2. H1 refuted by the drag probe → look for a dimensionless reduction instead of brute-force scanning.
3. H3 supported → scan one variable (β) and **reuse every earlier run as data**. If refuted → recommend a raw-parameter screen.
4. Prediction at β = 100 misses by 2.2° → systematic residuals → **propose a new tier of laws**.
5. Laws disagree → measure where they disagree most. Laws agree → measure where data is sparsest.
6. Two correct predictions before the experiments ran → stop, then hold-out validation.

## Omnigent setup

```bash
uv pip install -e ".[omnigent]"     # Python 3.12+, Node 22; see omnigent docs for tmux/sandbox needs
omnigent setup                       # pick credentials: Anthropic API key or Claude subscription
export PHYSICS_LAB_RECORD=runs/omnigent/record.json
PYTHONPATH=. omnigent run omnigent/physics_lab.yaml -p "Start the investigation."
```

- Change model per run: `omnigent run --model <id> omnigent/physics_lab.yaml`.
- Hosted server: add `policy_modules: [physics_lab.policies]` to the server config so the
  custom `experiment_gate` policy is allowed (local `omnigent run` does not need it).
- Guardrails in the YAML: `experiment_gate` (DENY invalid, ASK for > 400 simulations or any
  self-claimed approval), a 300 tool-call cap, and a $15 cost cap with a check-in at $10.

**Verified so far:** the YAML loads with Omnigent's own parser (`omnigent.inner.loader`); all 13
function tools resolve; each sub-agent gets only its tool subset; the policy passes the
hosted-server allowlist once registered; and the generated tool schemas have correct types and
descriptions. All tools and the policy have tests. **Not yet done:** a live LLM session. It needs
`omnigent setup` with credentials on the host. Run it once before the demo and keep the record.

## Tool notes for anyone editing `tools.py`

- Omnigent builds each tool's schema from **bare** annotations (`str`, `int`, `float`, `bool`,
  `list`, `dict`). Generics such as `list[str]`, or `from __future__ import annotations`, silently
  turn every parameter into `string`. `tests/test_discovery.py::test_tool_signatures_use_plain_types`
  guards this.
- Omnigent does not read docstrings. Tool descriptions live in the YAML.
- Tools are stateless across processes: each call loads and saves the record file.
