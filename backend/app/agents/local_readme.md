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
+-- analysis            Analysis Lead    -> analysis_specialist,         analysis_secretary
+-- review_safety       Review Lead      -> review_safety_specialist,    review_safety_secretary
+-- knowledge_memory    Knowledge Lead   -> knowledge_memory_specialist, knowledge_memory_secretary
```

1 Lab Director, 7 Leads, 7 specialists, 7 secretaries. The Director only talks to Leads, and each
Lead only talks to its own specialist and secretary.

## Cycles

A cycle is one pass through the departments, from new evidence to a reviewed verdict. The Director
numbers the cycles and gives the cycle number in every task; every log entry records it.

- **Analysis** and **Review & Safety** look only at the current cycle.
- **Knowledge & Memory** merges all cycles so far. The Director calls it at the end of a cycle and
  before stopping, and uses its report to plan the next cycle and to decide whether to stop.

## Run output: one folder, downloaded as a zip

The log database is set aside for now. Everything a run produces is a file in one run folder, and
at the end the user downloads that folder as a zip.

```
runs/<run_id>/
  record.jsonl                      the research record (shared contract)
  logs/<department>/department.jsonl   Lead decisions and reports
  logs/<department>/specialist.jsonl   specialist results
  experiments/<experiment_id>/      run.py, results.csv, output.log
  knowledge/merge.py                code that merges every results.csv
  knowledge/all_results.csv         all experiments' data in one table
  knowledge/cycle_<n>.md            Knowledge & Memory report per cycle
  final_report.md                   written by Knowledge & Memory on the final call, for the user
```

At the end of the process:

1. The Director decides to stop and calls Knowledge & Memory for the final merged report.
2. A packaging tool zips `runs/<run_id>/` into `runs/<run_id>.zip`. This is deterministic Python:
   it copies files and makes no decisions.
3. The Director tells the user the run is finished, gives a short summary, and prompts them to
   download the zip.

Not decided yet: how Omnigent offers the zip for download (a link in the web session, or a path on
disk). The prompts do not mention the zip yet; add it to the Director's prompt once the packaging
tool exists.

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

Each department has two log levels, stored as files in the run folder:

- **Department log:** the Lead's decisions and reports (`logs/<department>/department.jsonl`).
- **Specialist log:** the specialist's results (`logs/<department>/specialist.jsonl`).

| Agent | Department log | Specialist log |
|---|---|---|
| Lab Director | Read, all departments | No access |
| Lead | Read, own department | Read, own department |
| Knowledge Lead | Read, all departments (to merge cycles) | Read, own department |
| Secretary | Write, own department | Write, own department |
| Specialist | No access | No access |

No agent can read another department's specialist log. The Director gets detail by asking a Lead.
These limits must be enforced by the log tools, not just by the prompts: each agent gets only the
log tools its row allows, and each tool opens only the files its row allows. The downloaded zip
contains every log, because it is for the user, not for the agents.

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

1. `experiment_runner_specialist` writes the code (`run.py`, listing its inputs, tools, packages,
   outputs and the command to reproduce it), runs it, and saves the code, `results.csv` (one row
   per simulation, failed designs kept) and `output.log` together in one experiment folder. Code is
   never changed after it produced data; a fix gets a new experiment folder.
2. The Lead checks that the run followed the plan, finished, and produced a complete CSV, then
   writes `experiment` and `result` records. It runs only plans marked `runnable_by: agents`.
3. `experiment_runner_secretary` logs where the files are (experiment ID, experiment folder, row
   count, status), not the data itself.
4. The Lead reports to the Director. Whether the result supports the hypothesis is Analysis's
   decision.

**Analysis:** decides the verdict on this cycle's hypothesis, from this cycle's results only.

1. `analysis_specialist` reads this cycle's CSV files, compares the best valid design with the
   benchmark (cooling power, solar reflectance, 8–13 µm emissivity) and with the hypothesis's
   prediction, explains failures, and says whether the evidence is enough.
2. The Lead writes a `verdict` record: `supported`, `refuted` or `inconclusive` (with what data is
   missing).
3. `analysis_secretary` logs the specialist's result and the Lead's decision.
4. The Lead reports the verdict and a recommendation for where to go next to the Director.

**Review & Safety:** decides whether this cycle's claims stand and whether actions need a human.

1. `review_safety_specialist` checks this cycle's records: citations exist and support the claims,
   numbers match the CSV files, hypotheses are labeled as hypotheses, designs respect the
   constraint, and which actions need approval.
2. The Lead writes an `approval` record with `needs_human: yes` or `no`, plus a message for the user
   when it is `yes`. Fabrication, anything outside simulation, and spending beyond the budget always
   need a human.
3. The Lead never fixes another department's record. It reports the problem, and the Director
   decides who fixes it.

**Knowledge & Memory:** collects the data of all cycles, processes it, and reports to the
Director. Called at the end of every cycle, and once more as the final call before the lab stops.

1. `knowledge_memory_specialist` collects `record.jsonl`, every experiment's `results.csv`, and the
   department logs the Lead passes on. It writes and runs `knowledge/merge.py`, which builds
   `knowledge/all_results.csv` (all rows, with `cycle` and `experiment_id` columns, failed designs
   kept), and computes the best design and evaluations used per cycle. It then merges findings,
   tracks how hypotheses changed, finds conflicts, and drafts the report.
2. The Lead checks that every experiment is included and row counts match the `result` entries,
   decides what becomes common knowledge, and writes `knowledge/cycle_<n>.md` (Established,
   Refuted, Best so far, Progress, Conflicts, Open questions). Outdated findings are marked, never
   deleted.
3. On the final call the Lead also writes `final_report.md` for the user: the question, findings,
   best design against the benchmark, refuted hypotheses, limitations, and the next experiment.
   That file goes into the downloaded zip.
4. `knowledge_memory_secretary` logs where the files are.
5. The Lead sends the Director a summary and the file locations.

Files from runs: see "Run output" above. Each experiment can be rerun with `python run.py` from
its folder.

Open questions:
- The Experiment Runner specialist runs code it writes itself. Give it a sandbox in its
  `config.yaml` (`os_env.sandbox`: write only to `runs/`, no network) before enabling it.
- The log tools and the packaging tool are not built yet. Until the log tools exist, the
  secretaries return their log entries to the Lead as text. The prompts still say "lab log
  database"; update them when the log tools exist.
- The shared record has no field for the cycle number or kind for common knowledge. For now the
  cycle number goes in each entry's `content`, and the knowledge report is a file.
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
