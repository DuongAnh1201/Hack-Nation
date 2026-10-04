# Omnigent Agent Specifications & Policies

## 1. Supervisor-Specialist Architecture

The lab is orchestrated through an Omnigent graph consisting of a Lab Director (Supervisor) and 7 distinct departments:

```
radiative-cooling-lab (Lab Director / Supervisor)
 ├── literature_agent        [Literature Lead  -> literature_specialist,       literature_secretary]
 ├── hypothesis_agent        [Hypothesis Lead  -> hypothesis_specialist,       hypothesis_secretary]
 ├── planning_agent          [Planning Lead    -> planning_specialist,         planning_secretary]
 ├── experiment_runner       [Runner Lead      -> experiment_runner_specialist, experiment_runner_secretary]
 ├── analysis_agent          [Analysis Lead    -> analysis_specialist,         analysis_secretary]
 ├── review_safety           [Review Lead      -> review_safety_specialist,    review_safety_secretary]
 └── knowledge_memory        [Knowledge Lead   -> knowledge_memory_specialist, knowledge_memory_secretary]
```

## 2. Decision Ownership

- **Specialist:** Investigates and computes. Advises the Lead and writes nothing directly to the research record or persistent database.
- **Lead:** Makes the department's scientific decision, writes the entry to the shared research record (`runs/<run_id>/record.jsonl`), and reports back to the Lab Director.
- **Secretary:** Writes to the department and specialist logs, tracking cycle numbers and repeat investigations.
- **Lab Director (Supervisor):** Decides which department acts next and when the research loop concludes. It does not override department scientific decisions.

## 3. Log Permissions & Access Matrix

Enforced strictly in code, not prompts:

| Agent Role | Department Log | Specialist Log | Research Record |
| :--- | :---: | :---: | :---: |
| **Lab Director** | Read (All) | No Access | Read / Write |
| **Department Lead** | Read / Write (Own) | Read (Own) | Read / Write |
| **Secretary** | Write (Own) | Write (Own) | Append Log |
| **Specialist** | No Access | No Access | Read Inputs Only |

## 4. Invariant Policies (Enforced in Code)

1. **`policy: control_first`**
   - Prohibits candidate design simulations until the published Stanford 2014 control passes verification ($\bar{R}_\text{solar} \ge 97\%$).
2. **`policy: budget_cap`**
   - Hard execution gate preventing any agent or script from exceeding the configured physical evaluation budget (default: 100 simulator calls, hard limit: 400).
3. **`policy: fabrication_gate`**
   - Hard safety gate requiring explicit human approval (`status: pending_human_review`) before any design can be proposed for thin-film PVD deposition or outdoor rooftop testing. Agents cannot self-claim human authorization.
