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
+-- planning            Planning Lead    -> planning_specialist,         planning_secretary          (placeholder)
+-- analysis            Analysis Lead    -> analysis_specialist,         analysis_secretary          (placeholder)
+-- review_safety       Review Lead      -> review_safety_specialist,    review_safety_secretary     (placeholder)
+-- knowledge_memory    Knowledge Lead   -> knowledge_memory_specialist, knowledge_memory_secretary  (placeholder)
```

1 Lab Director, 6 Leads, 6 specialists, 6 secretaries. The Director only talks to Leads, and each
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

Open questions:
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
| 2 | + `hypothesis`, `planning`, `analysis` | One full loop with a refuted hypothesis |
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

Run this from this folder. It parses the whole tree with Omnigent's own loader and prints who can
call whom:

```bash
~/.local/share/uv/tools/omnigent/bin/python3 -c "
from pathlib import Path
from omnigent.spec.parser import parse
def show(s, d=0):
    print('  '*d + s.name, '->', s.tools.agents if s.tools else [])
    for c in s.sub_agents: show(c, d+1)
show(parse(Path('.')))"
```

A malformed `config.yaml` makes this fail and names the file. If an agent prints its prompt path
instead of the prompt text, its `prompt.md` is missing or misnamed.

## Tools

The simulator (`simulate_stack`, `optimize_thicknesses`), the record tools (`read_record`,
`write_record`) and the log tools are tools, not agents. Omnigent finds local tools in
`tools/python/*.py` inside each agent's folder, which is also how log permissions are enforced:
an agent can only call the tools in its own folder. [tools/literature_review.py](tools/literature_review.py)
is not in that path yet, so Omnigent does not load it.
