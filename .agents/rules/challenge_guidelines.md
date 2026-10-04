# Hackathon Challenge Compliance & Architectural Rules
*Databricks × Hack-Nation: Agentic Scientific Discovery Challenge 03*

## 1. Prime Directive: Discovery Lab, Not Just a Chatbot
- **Goal:** Build an autonomous scientific AI lab capable of Nobel Prize-caliber discovery acceleration.
- **Identity Alignment:** The system is **Phys.io**, an Agentic Scientific Discovery platform. While interactive courses and visualizations exist for users, the underlying engine MUST be an authentic scientific discovery lab powered by **Omnigent**.
- **Do not** reduce agent orchestration to a simple conversational LLM wrapper or generic study tutor. The agents must formulate hypotheses, design experiments, evaluate numerical simulations, and update decisions based on evidence.

---

## 2. Omnigent Orchestration (30% Hackathon Weight)
- All agent interactions must follow the Omnigent multi-agent architecture.
- **Specialist Roles:**
  1. `research_planner` (Supervisor): Controls the discovery agenda, manages simulation budgets, writes decisions and conclusions.
  2. `literature_agent`: Searches papers (OpenAlex, arXiv) and records verified facts with citations.
  3. `hypothesis_agent`: Proposes mathematical functional forms and falsifiable predictions.
  4. `experiment_planner`: Selects optimal experimental conditions ($\beta$, planets, velocities) to discriminate between competing hypotheses.
  5. `simulation_runner`: Executes physics simulations via RK4 numerical solver.
  6. `analysis_agent`: Performs Leave-One-Out (LOO) cross-validation, fits nonlinear laws, and identifies maximum model disagreement.
  7. `safety_agent`: Evaluates safety policies and enforces human-in-the-loop gates.
- **Shared Research Record:** Agents MUST communicate by reading from and writing to a structured, persistent research record (`ResearchRecord`). Every entry must have a unique ID (`H1`, `E1`, `R1`, `D1`, etc.) and cite antecedent records in `refs`.

---

## 3. Scope of Assigned Issues

### Issue #7: Courses Requirements (Physics & Components)
- Must implement the **4 Major Scientific Pillars**:
  1. **Kinematics & Vacuum Motion (Control Baseline):** Parabolic motion, $45^\circ$ theoretical maximum range in vacuum ($R = v_0^2/g$).
  2. **Fluid Dynamics & Drag Forces (Empirical Perturbation):** Quadratic drag ($F_D = \frac{1}{2}\rho C_d A v^2$), asymmetric trajectories, shift to $\theta^* < 45^\circ$.
  3. **Work, Energy & Momentum Dissipation (Numerical Rigor):** Energy balance checks (KE + PE + Drag Work = 0), verification against numerical drift.
  4. **Dimensional Analysis & Scaling Laws (Discovery Core):** Buckingham $\Pi$ collapse of 6 parameters ($v_0, m, A, C_d, \rho, g$) into the dimensionless parameter $\beta = \frac{\rho C_d A v_0^2}{2mg}$.
- Must implement the **3 Interactive Demo Classes**:
  1. **Demo 1: The Vacuum vs. Atmosphere Experiment ($E_1 / E_2$):** Demonstrating the refutation of the $45^\circ$ rule under atmospheric drag.
  2. **Demo 2: Multi-Planet Parameter Invariance ($E_3 / E_4$):** Demonstrating that identical $\beta$ produces identical $\theta^*$ across Earth, Mars, and Venus.
  3. **Demo 3: Live Autonomous Law Discovery ($E_5 \to E_8$):** The live agent loop fitting candidate laws ($\cot \theta^* = 1 + a\ln(1 + c\beta)$), identifying model disagreements, and validating on hold-out conditions.

### Issue #8: Agent Orchestration Pipeline
- Deliverables:
  1. `omnigent/physics_lab.yaml`: Omnigent multi-agent configuration with sub-agents, tool whitelists, and model harness.
  2. `physics_lab/tools.py`: Omnigent-compatible function tools using bare primitive type annotations (`str`, `int`, `float`, `bool`, `list`, `dict`).
  3. `physics_lab/policies.py`: Omnigent policy (`experiment_gate`) enforcing run limits and human approval checks.
  4. `physics_lab/record.py`: Full research record state manager with export/replay.
  5. `physics_lab/agents/autopilot.py`: Deterministic discovery orchestrator serving as zero-API-key fallback and benchmark arm.

---

## 4. Scientific Rigor & Epistemic Rules (15% Weight)
- Every entry in the research record MUST carry an epistemic tag:
  - `established_fact`: Must cite a verified source/DOI/URL.
  - `literature`: External published academic findings.
  - `assumption`: Explicitly stated modeling simplifications (e.g. flat ground, constant $C_d$, no Magnus effect).
  - `ai_hypothesis`: Proposed hypothesis or mathematical law.
  - `ai_prediction`: Logged strictly **before** the experiment runs to demonstrate prospective predictive power.
  - `simulation_result`: Direct measurements from numerical experiments.
  - `analysis`: Statistical evaluations, LOO RMSE scores, residual analysis.
  - `decision`: Causal justification of why the next step was taken based on prior evidence.
  - `conclusion`: Always tagged `pending_human_review`.

---

## 5. Safety, Guardrails & Human Approval (10% Weight)
- Enforce strict compute budgets:
  - Max 400 simulations per single experiment without explicit human sign-off.
  - Max 5,000 simulations per total discovery session.
- Prevent agent self-approval: Any tool call declaring `human_approved=true` must be intercepted and validated by the Omnigent policy gate (`experiment_gate`).
- Physical validity bounds:
  - Speed $v_0 > 250\text{ m/s}$: Warn that air compressibility/shockwaves are not modeled.
  - $\beta > 100$: Warn of extreme turbulent boundary conditions.

---

## 6. Discovery Acceleration (20% Weight)
- The discovery acceleration must be measurable and honest.
- Do not claim an unsupported $10\times$ speedup without evidence. Report observed empirical benchmarks (e.g., 2.9× reduction in simulations: 651 vs. 1,870 on manual grids, with 0 vs. 17 human interventions).
- Every discovery milestone must state the **recommended next experiment** (e.g. extending to non-zero launch height $h_0 > 0$ and the second dimensionless parameter $\eta = \frac{gh_0}{v_0^2}$).
