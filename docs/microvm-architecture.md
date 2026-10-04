# Micro-VM Sandbox Architecture & Knowledge Memory Feedback Loop

## 1. Overview & Architecture

Following the design from **Person 3 (Omnigent Lead)**, the research workflow is structured around 5 active execution departments, a supervisor (Lab Director), and a central **Knowledge & Memory Department** that continuously consolidates findings into **Common Knowledge**, which in turn feeds into subsequent reasoning cycles.

```
                            LAB DIRECTOR
                             Supervisor
                                 |
     +-------------+-------------+-------------+-------------+
     |             |             |             |             |
     v             v             v             v             v
Literature     Hypothesis     Planning      Analysis     Review & Safety
Department     Department     Department    Department    Department
     |             |             |             |             |
     +-------------+-------------+------+------+-------------+
                                         |
                                         v
                                Knowledge & Memory
                                    Department
                                         |
                                         v
                                  Common Knowledge
                                         |
                                         +----> next reasoning cycle
```

---

## 2. Department Breakdown & Roles

### Execution Departments (5)
1. **Literature Department:**
   - *Lead:* `literature_lead`
   - *Specialists:* `search_agent`, `citation_agent`, `benchmark_agent`
   - *Responsibility:* Queries scientific literature (OpenAlex), material databases, and optical constants.
2. **Hypothesis Department:**
   - *Lead:* `hypothesis_lead`
   - *Specialists:* `physics_agent`, `material_agent`, `design_agent`
   - *Responsibility:* Develops theoretical models, proposes layer stacks, and defines falsifiable predictions.
3. **Planning Department:**
   - *Lead:* `planning_lead`
   - *Specialists:* `cost_agent`, `explore_agent`, `exploit_agent`
   - *Responsibility:* Optimizes simulation budget, ranks candidate experiments, and dispatches evaluations.
4. **Analysis Department:**
   - *Lead:* `analysis_lead`
   - *Specialists:* `stats_agent`, `compare_agent`, `failure_agent`
   - *Responsibility:* Evaluates simulation data, computes cooling power metrics, and issues hypothesis verdicts (`supported`, `refuted`).
5. **Review & Safety Department:**
   - *Lead:* `review_safety_lead`
   - *Specialists:* `evidence_agent`, `claim_agent`, `approval_agent`
   - *Responsibility:* Enforces budget ceilings, controls unapproved simulations, and gates fabrication proposals.

### Central Memory Hub (1)
6. **Knowledge & Memory Department:**
   - *Lead:* `memory_lead`
   - *Specialists:* `consolidation_agent`, `epistemic_agent`, `retrieval_agent`
   - *Responsibility:* Consolidates findings from all departments into the persistent **Common Knowledge** state, tracks epistemic statuses, and prepares the structured context for the **next reasoning cycle**.

---

## 3. Micro-VM Sandbox Deployment Modes (`sbx` Docker)

Because Person 3 determines the total number of micro-VMs dynamically, [`MicroVMManager`](file:///home/koiisme/code/Phys.io/lab/sandbox.py) supports four deployment modes:

### Mode 1: Hub-and-Spoke Topology (Recommended)
- **1 Dedicated Knowledge & Memory Hub Micro-VM:** Hosts the persistent state, epistemic graph, and research record.
- **$K$ Execution Worker Micro-VMs:** Elastic worker sandboxes executing simulations, OpenAlex searches, and calculations in isolated micro-VMs.
```python
from lab.sandbox import get_manager

mgr = get_manager()
# Person 3 decides K workers:
vms = mgr.spawn_sandboxes(count=4) # 1 Knowledge Hub + 3 Workers
```

### Mode 2: Departmental Mesh (6 Micro-VMs)
- **5 Micro-VMs:** One dedicated micro-VM per execution department.
- **1 Micro-VM:** Dedicated Knowledge & Memory Hub micro-VM.
```python
vms = mgr.spawn_sandboxes(count=6)
```

### Mode 3: Specialist Mode (18 Micro-VMs)
- Complete isolation for each of the 15 execution specialists + 3 memory specialists.
```python
vms = mgr.spawn_sandboxes(count=18)
```

### Mode 4: Unified Sandbox (1 Micro-VM)
- Single micro-VM combining all department functions for low-resource or local fallback testing.

---

## 4. Common Knowledge Feedback Loop

The cycle transitions operate as follows:

1. **Cycle Start:** The Lab Director receives the context from [`get_context_for_next_cycle()`](file:///home/koiisme/code/Phys.io/lab/sandbox.py#L200), including open hypotheses, current best cooling power $P_{\text{net}}$, and target status ($11.83\text{ W/m}^2$).
2. **Department Execution:** Departments execute tasks inside their designated micro-VM sandboxes.
3. **Simulation Recording:** Every simulation executed inside a sandbox automatically pipes results into [`CommonKnowledgeHub`](file:///home/koiisme/code/Phys.io/lab/sandbox.py#L140).
4. **Cycle Consolidation:** The Knowledge & Memory Department evaluates the cycle's progress, updates hypothesis statuses (`supported`, `refuted`), and advances the cycle via [`advance_cycle()`](file:///home/koiisme/code/Phys.io/lab/sandbox.py#L530).
5. **Next Cycle Seed:** Distilled insights and active candidate designs are piped into cycle $N+1$.

---

## 5. Storage & Volume Configuration

In Docker Sandboxes (`sbx --cloud`):
- Persistent volume: `common-knowledge-vol` mounted to `/home/agent/workspace/runs`.
- Ledger file: `LAB_EVAL_LEDGER` written at `/home/agent/workspace/runs/eval_ledger.jsonl`.
- Common Knowledge file, one per run (a whole research project): `/home/agent/workspace/runs/<run_id>/common_knowledge.json`.
- Research record: `/home/agent/workspace/runs/record.jsonl`.
