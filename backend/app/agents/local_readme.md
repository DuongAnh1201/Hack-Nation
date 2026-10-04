# Agents: Radiative Cooling Lab

The Omnigent bundle for the lab. The LLM agents make every scientific decision. Python tools only
run deterministic work (simulation, record I/O, logging, budget counting) and never choose what to
do next. Do not add a LangChain, LangGraph or Python loop that decides for the agents.

## Hierarchy

Every department has exactly three agents: a Lead, a specialist and a secretary.

```
radiative-cooling-lab (Lab Director / Supervisor)
|
+-- literature          Literature Lead  -> literature_specialist,       literature_secretary
+-- hypothesis          Hypothesis Lead  -> hypothesis_specialist,       hypothesis_secretary
+-- planning            Planning Lead    -> planning_specialist,         planning_secretary
+-- experiment_runner   Runner Lead      -> experiment_runner_specialist, experiment_runner_secretary
+-- analysis            Analysis Lead    -> analysis_specialist,         analysis_secretary          (placeholder)
+-- review_safety       Review Lead      -> review_safety_specialist,    review_safety_secretary     (placeholder)
+-- knowledge_memory    Knowledge Lead   -> knowledge_memory_specialist, knowledge_memory_secretary  (placeholder)
```

1 Lab Director, 7 Leads, 7 specialists, 7 secretaries. The Director only talks to Leads, and each
Lead only talks to its own specialist and secretary. Placeholder departments have their decision
defined but not their details.

## Decision ownership

- **The specialist** investigates and advises. It returns its result to the Lead and writes nothing
  to the record or the logs.
- **The Lead** makes the department's decision, writes it to the record, and reports to the
  Director.
- **The secretary** writes the department's log entries. It logs what the Lead sends and never
  changes it.
- **The Lab Director** decides which department acts next and when the research stops. It does not
  make the departments' scientific decisions.
- **Every Lead reports back to the Director** when its department finishes: the decision and its
  record IDs. Leads never call another department, so every handoff goes through the Director.
- **Only the Director talks to the user.** When a Lead needs a human (e.g. a plan the agents cannot
  run), it puts a message for the user in its report, and the Director sends it and passes the
  answer back.

## Log permissions

Each department has two log levels in the lab log database:

- **Department log:** the Lead's decisions and reports.
- **Specialist log:** the specialist's results.

| Agent | Department log | Specialist log |
|---|---|---|
| Lab Director | Read, all departments | No access |
| Lead | Read, own department | Read, own department |
| Secretary | Write, own department | Write, own department |
| Specialist | No access | No access |

No agent can read another department's specialist log. The Director gets detail by asking a Lead.
These limits must be enforced by the log tools, not just by the prompts: each agent gets only the
log tools its row allows.

## Repeated results

When a specialist returns a result that is already in the specialist log:

1. The secretary logs it again, marked as a repeat of the earlier entry.
2. The Lead decides whether a rerun could give a different result, e.g. the inputs, the evidence or
   the search query changed since the earlier run.
3. **Yes:** the Lead reruns the specialist and says what is different. A rerun with the same inputs
   is not allowed.
4. **No:** the Lead reports the repeat to the Director, and the lab moves to the next cycle.

The Lead checks its own decisions against the department log the same way. The Director applies
the same logic one level up: if a department's report repeats its department log, the Director
calls it again only if something changed elsewhere in the lab; otherwise it moves to the next cycle.

## Defined departments

**Literature:** decides which published evidence the lab accepts.

1. `literature_specialist` searches Springer, Nature, IEEE and arXiv, filters the articles against
   the problem statement, and extracts claims, numbers with units, and conditions.
2. The Lead checks for repeats, then accepts or rejects findings and writes `literature` records.
3. `literature_secretary` logs the specialist's result and the Lead's decision.
4. The Lead reports to the Director, who decides which department acts next (usually Hypothesis).

**Hypothesis:** decides which hypothesis the lab tests next.

1. `hypothesis_specialist` checks earlier hypotheses against the new literature (consistent,
   conflicting or no bearing), scores each from 0 to 1, and proposes new candidates.
2. The Lead checks for repeats, then keeps, revises or replaces hypotheses and writes `hypothesis`
   records (status `proposed`).
3. `hypothesis_secretary` logs the specialist's result and the Lead's decision.
4. The Lead reports to the Director.

**Planning:** decides which experiment tests the hypothesis, why, and who can run it.

1. `planning_specialist` reasons from what the hypothesis predicts, to the measurement that would
   confirm or refute it, to the kind of experiment that produces it. It proposes at least 2
   candidates, each with why, expected gain, cost in simulator evaluations, steps, feasibility and
   cited sources.
2. If the methodology lacks literature support, the Lead reports the gap to the Director, who
   decides whether Literature collects more first.
3. The Lead picks one experiment and decides whether the agents can script and run it with the
   lab's tools. It writes a `plan` record with `runnable_by: agents` or `runnable_by: human`; for
   `human` it adds a message for the user, which the Director sends.
4. `planning_secretary` logs the specialist's result and the Lead's decision.

**Experiment Runner:** decides whether a run went as planned and its data is accepted.

1. `experiment_runner_specialist` writes the script (listing its inputs, tools, packages and
   outputs), runs it, and saves one CSV row per simulation, keeping failed designs.
2. The Lead checks that the run followed the plan, finished, and produced a complete CSV, then
   writes `experiment` and `result` records. It runs only plans marked `runnable_by: agents`.
3. `experiment_runner_secretary` logs where the files are (experiment ID, script path, CSV path,
   row count, status), not the data itself.
4. The Lead reports to the Director. Whether the result supports the hypothesis is Analysis's
   decision.

Files from runs:
- Scripts: `runs/<run_id>/scripts/<experiment_id>.py`
- Data: `runs/<run_id>/data/<experiment_id>.csv`

Open questions:
- The Experiment Runner specialist runs code it writes itself. Give it a sandbox in its
  `config.yaml` (`os_env.sandbox`: write only to `runs/`, no network) before enabling it.
- The lab log database and its tools are not built yet. Until they are, the secretaries return
  their log entries to the Lead as text.
- How the lab log relates to common knowledge: the Knowledge & Memory department needs to read the
  logs, which the table above does not allow yet.
- Reruns have no hard limit. A budget policy could cap them.

## Folder layout

Every agent is a folder with two files. The folder nesting is the reporting line.

```
agents/                          <- this folder is the Lab Director's bundle
  config.yaml                    Director: which departments it may call
  prompt.md                      Director instructions
  agents/
    literature/                  Department Lead
      config.yaml                its specialist and secretary
      prompt.md
      agents/
        literature_specialist/   (no sub-agents)
          config.yaml
          prompt.md
        literature_secretary/    (no sub-agents)
          config.yaml
          prompt.md
```

Why prompts sit next to each config: Omnigent finds sub-agents at `agents/<name>/config.yaml`, and
`instructions: prompt.md` is only read from inside that agent's own folder. A path like
`../prompts/x.md` falls back to literal text, so a shared `prompts/` folder does not work.

Folder names are globally unique (`<department>_specialist`, `<department>_secretary`), so logs and
the record show which department an agent belongs to. Keep the folder name and the `name:` in
`config.yaml` the same.

## Rollout status

We bring the hierarchy up one department at a time, and only after nested delegation is proven.

| Step | Wired | Check |
|---|---|---|
| 1 | Director -> `literature` -> its specialist and secretary | The Lead's report reaches the Director in the Omnigent web session |
| 2 | + `hypothesis`, `planning`, `experiment_runner`, `analysis` | One full loop with a refuted hypothesis |
| 3 | + `review_safety` | Fabrication proposals ask a human |
| 4 | + `knowledge_memory` | Next cycle reads common knowledge |

**Current: step 1.** All folders exist, but only the departments listed in the Director's
`tools.agents` can be called. The rest are commented out in [config.yaml](config.yaml).

## Common changes

**Enable a department:** uncomment its line under `tools.agents` in [config.yaml](config.yaml).

**Change what a specialist does:** edit its `prompt.md`. Nothing else changes.

**Add an agent to a department:**
1. Copy the department's specialist folder, e.g. `agents/literature/agents/literature_specialist/`,
   to a new folder name in the same department.
2. Set `name:` and `description:` in the copy's `config.yaml`, and rewrite its `prompt.md`.
3. Add the folder name to the Lead's `tools.agents`, and mention it in the Lead's `prompt.md`.

**Remove an agent:** delete its folder and its line in the Lead's `tools.agents`.

None of these change the Director or the other departments.

## Prompt template

Lead prompts have: Decision you own, How you work, What to read from the record, What to write,
Logs, Repeated results, Rules. Specialist and secretary prompts state what they do, their log
access, and their rules. Every agent that writes to the record must "Cite the record IDs you based
this on."

Record kinds (shared contract): `literature`, `hypothesis`, `plan`, `experiment`, `result`,
`verdict`, `approval`.

## Check the bundle

Run this from the repo root or this folder to verify the entire hierarchy and discovered tools:

```bash
python3 -c "
from pathlib import Path
from omnigent.spec.parser import parse
def show(s, d=0):
    lt = [t.name for t in s.local_tools]
    ag = s.tools.agents if s.tools else []
    print('  '*d + s.name, '->', ag, f'[local tools: {lt}]')
    for c in s.sub_agents: show(c, d+1)
show(parse(Path('backend/app/agents')))"
```

A malformed `config.yaml` makes this fail and names the file. If an agent prints its prompt path
instead of the prompt text, its `prompt.md` is missing or misnamed.

The simulator (`simulate_stack`, `optimize_thicknesses`), the record tools (`read_record`,
`write_record`), paper search (`search_papers`), material properties (`list_materials`, `material_properties`),
and knowledge logging tools (`log_to_common_knowledge`, `read_common_knowledge`) are deterministic tools
implemented in [lab/tools.py](../../../../lab/tools.py).

Omnigent finds local tools in `tools/python/*.py` inside each agent's folder, which is also how tool
permissions are enforced:
- **Specialists** carry domain execution tools (e.g. `literature_specialist` uses `search_papers`, `hypothesis_specialist` uses `list_materials`/`material_properties`, `analysis_specialist` uses `simulate_stack`/`optimize_thicknesses`).
- **Secretaries** carry logging tools (`log_to_common_knowledge`, `write_record`) and act as internal briefing officers for Department Leads.
- **Department Leads & Director** coordinate delegation and review via `read_record`.

