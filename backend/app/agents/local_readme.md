# Agents: Radiative Cooling Lab

The Omnigent bundle for the lab. The LLM agents make every scientific decision. Python tools only
run deterministic work (simulation, record I/O, budget counting) and never choose what to do next.
Do not add a LangChain, LangGraph or Python loop that decides for the agents.

## Hierarchy

```
radiative-cooling-lab (Lab Director / Supervisor)
|
+-- literature          Literature Lead        -> literature_search, literature_evidence
+-- hypothesis          Hypothesis Lead        -> hypothesis_physics, hypothesis_materials
+-- planning            Planning Lead          -> planning_exploration, planning_budget
+-- analysis            Analysis Lead          -> analysis_performance, analysis_failure
+-- review_safety       Review Lead            -> review_evidence_auditor, review_safety_approval
+-- knowledge_memory    Knowledge Lead         -> knowledge_archivist, knowledge_curator, knowledge_synthesizer
```

1 Lab Director, 6 Department Leads, 13 specialists. The Director only talks to Leads, and each Lead
only talks to its own specialists. Knowledge & Memory turns the other departments' results into
common knowledge for the next reasoning cycle.

## Folder layout

Every agent is a folder with two files. The folder nesting is the reporting line.

```
agents/                      <- this folder is the Lab Director's bundle
  config.yaml                Director: which departments it may call
  prompt.md                  Director instructions
  agents/
    literature/              Department Lead
      config.yaml            which specialists it may call
      prompt.md
      agents/
        literature_search/   Specialist (no sub-agents)
          config.yaml
          prompt.md
```

Why prompts sit next to each config: Omnigent finds sub-agents at `agents/<name>/config.yaml`, and
`instructions: prompt.md` is only read from inside that agent's own folder. A path like
`../prompts/x.md` falls back to literal text, so a shared `prompts/` folder does not work.

Folder names are globally unique (`<department>_<role>`), so logs and the record show which
department an agent belongs to. Keep the folder name and the `name:` in `config.yaml` the same.

## Rollout status

We bring the hierarchy up one department at a time, and only after nested delegation is proven.

| Step | Wired | Check |
|---|---|---|
| 1 | Director -> `literature` -> its 2 specialists | Specialists' output reaches the Director in the Omnigent web session |
| 2 | + `hypothesis`, `planning`, `analysis` | One full loop with a refuted hypothesis |
| 3 | + `review_safety` | Fabrication proposals ask a human |
| 4 | + `knowledge_memory` | Next cycle reads common knowledge |

**Current: step 1.** All folders exist, but only the departments listed in the Director's
`tools.agents` can be called. The rest are commented out in [config.yaml](config.yaml).

## Common changes

**Enable a department:** uncomment its line under `tools.agents` in [config.yaml](config.yaml).

**Disable a specialist:** comment out its line under `tools.agents` in its Lead's `config.yaml`.
The folder stays and can be turned back on later.

**Add a specialist:**
1. Copy any specialist folder, e.g. `agents/literature/agents/literature_search/`, to a new folder
   name in the same department.
2. Set `name:` and `description:` in the copy's `config.yaml`, and rewrite its `prompt.md`.
3. Add the folder name to the Lead's `tools.agents`.

**Remove a specialist:** delete its folder and its line in the Lead's `tools.agents`.

**Move a specialist to another department:** move the folder, then move its line between the two
Leads' `tools.agents`.

None of these change the Director or the other departments.

## Prompt template

Every `prompt.md` has the same sections, as the team plan requires:

- **Decision you own:** the one decision this agent makes.
- **What to read from the record:** which entries in `runs/<run_id>/record.jsonl` it reads.
- **What to write:** which record kinds it writes (`literature`, `hypothesis`, `plan`,
  `experiment`, `result`, `verdict`, `approval`).
- **Rules:** always "Cite the record IDs you based this on."

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

The simulator (`simulate_stack`, `optimize_thicknesses`) and the record tools (`read_record`,
`write_record`) are tools, not agents. Omnigent finds local tools in `tools/python/*.py` inside each
agent's folder. [tools/literature_review.py](tools/literature_review.py) is not in that path yet, so
Omnigent does not load it. Its location will be decided when the tools are wired up.
