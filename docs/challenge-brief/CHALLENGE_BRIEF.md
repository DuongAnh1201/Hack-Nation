# Challenge 03: Agentic Scientific Discovery
**7th Global AI Hackathon (Databricks × Hack-Nation)**  
*In collaboration with MIT Club of Northern California and MIT Club of Germany*  
**Powered by Databricks · Build with Omnigent**  
*Required for every challenge submission · 24-hour scientific discovery challenge*

---

## 1. Goals and Motivation

### Build an Agentic AI Lab for Scientific Breakthroughs
- **Required Platform:** **Omnigent** (managed on Databricks or open source on GitHub).
- AI has already helped unlock Nobel Prize-winning science. By 2024, AlphaFold2 had enabled predictions for almost 200 million protein structures; its creators shared the Nobel Prize in Chemistry. That scale of discovery is the inspiration for this challenge.
- **The Moonshot:** Build the Omnigent AI lab behind the next Nobel Prize-caliber breakthrough and help make scientific discovery **10× faster**.
- In the next 24 hours, build a working scientific lab around one problem you care deeply about. Show how coordinated agents generate insight, formulate hypotheses, design experiments, run computational tests or analyses, interpret results and decide what to investigate next.

---

## 2. Choose Any Science Domain You Are Passionate About

- Your project can address any area of science: biology, medicine, materials, energy, climate, agriculture, chemistry, physics, AI research, neuroscience, astronomy or something entirely different. Choose one specific scientific question your prototype can meaningfully investigate within 24 hours.
- Choose a question that can be tested with existing scientific datasets, published literature, APIs, simulations, models, computational experiments, benchmark tasks or data you generate yourself.
- **Examples:** Discover a promising therapeutic mechanism, identify a new material, explore an energy system, test an AI research idea, investigate a climate or agriculture question, or bring a scientific frontier of your own.
- **Focus:** Focus on a question where your prototype can produce evidence, learn from it and make a better next scientific decision.

---

## 3. Orchestrate Your Scientific Lab with Omnigent

> **Mandatory for every submission: Build with Omnigent**  
> Omnigent must orchestrate the live discovery workflow. Demonstrate multiple specialist agents exchanging outputs, using tools, and adapting their plan after an experimental result.

### AI Builders — How to Get Started with Omnigent
- **Choose Your Setup:** Use managed Databricks or open-source Omnigent from GitHub. A Databricks account is only required for the managed Databricks route.
- **Launch Omnigent:**
  - *Databricks:* sign in → open `<workspace-url>/omnigent` → New session → Sandbox.
  - *GitHub:* `install Omnigent` → run `omnigent` → select your model or agent harness.
- **Build + Demo the Discovery Loop:** Connect your data and tools, define specialist-agent handoffs, run an experiment, and show how the result changes what the agents investigate next.

---

## 4. Multi-Agent Discovery Loop & Handoffs

```
                      +-----------------------------+
                      |      Literature Agent       |
                      |   Find evidence and gaps    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |        Insight Agent        |
                      |    Propose testable ideas   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     Experiment Planner      |
                      |    Choose revealing tests   |
                      +--------------+--------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                       Omnigent Orchestration                            |
|                     Tasks, tools and handoffs                           |
+------------------------------------+------------------------------------+
       |                             |                             |
       v                             v                             v
+-------------+             +-----------------+             +-------------+
| Knowledge   |             |    Analysis     |             | Experiment  |
| Graph Agent |             |      Agent      |             |   Runner    |
| Update links|             |Learn from result|             |Run code/sims|
+-------------+             +-----------------+             +-------------+
```

- **Specialist Agent Roles:**
  - *Literature Agent:* Find evidence and gaps.
  - *Insight Agent / Hypothesis Agent:* Propose testable ideas.
  - *Experiment Planner:* Choose revealing tests.
  - *Experiment Runner:* Run code or simulations.
  - *Analysis Agent:* Learn from results.
  - *Knowledge Graph / Record Agent:* Update evidence and links.
  - *Safety Agent:* Flag risks and route decisions for human approval.
- **Design the Handoffs that Accelerate Discovery:**
  - For each agent, specify the scientific decision it owns, the tools it can use, its inputs and its output.
  - Pass structured evidence, candidate IDs, experiment specifications, and results between agents.
  - Keep a shared research record so every decision can be reconstructed.
  - Run independent searches or experiments in parallel. Let surprising results reopen an earlier assumption.
  - Give the planner a budget and make it choose between competing tests.
- **Human Approval:**
  - Scientists set the objective and approve consequential actions.
  - Safety agent flags risks and requests approval; enforce boundary through tool permissions and Omnigent policies.

---

## 5. Run an Experiment that Changes the Next Decision

- Start with a clear question and a measurable scientific outcome.
- Use literature, structured data, simulations, models, or generated data to develop a hypothesis.
- Design at least two possible tests and choose one using expected learning, feasibility, and cost.
- Run the test, interpret the result, and use what you learned to determine the next step.
- **What Counts as an Experiment:**
  - Simulation, computational screening experiment, benchmark evaluation, model comparison, analysis of an existing experimental dataset, sensitivity or counterfactual analysis, or reproducible computational test.
  - Critical requirement: **Produces evidence that changes the next scientific decision.**

### Connect the Sources Your Science Needs
- *Across Disciplines:* OpenAlex (connects publications, citations, research communities).
- *Drug Discovery and Biology:* Europe PMC, PubChem.
- *Materials and Energy:* Materials Project, NIST JARVIS.
- *AI Research:* arXiv, OpenML.

---

## 6. Show Progress Toward 10× Faster Discovery

- Identify one bottleneck in scientific discovery and demonstrate how your agentic lab helps compress, automate, or improve it.
- **Define What Faster Discovery Means:**
  - Screening more candidates within the same time or compute budget.
  - Shortening the path from literature to a testable hypothesis.
  - Evaluating more hypotheses in parallel.
  - Reducing human effort.
  - Improving how quickly new evidence changes the next decision.
- **Report the Improvement Actually Observed:** (1.5×, 3×, 5×, 10×). Strength of evidence matters more than claiming the largest multiplier.
- **One Complete Discovery Loop:**
  $$\text{Question} \longrightarrow \text{Evidence} \longrightarrow \text{Hypothesis} \longrightarrow \text{Experiment} \longrightarrow \text{Result} \longrightarrow \text{Updated Decision}$$

---

## 7. What Success Looks Like

- **Required: Build with Omnigent:** Show purposeful collaboration between specialist agents.
- **Scientific Progress:** An ambitious question and a meaningful, reproducible result.
- **Discovery Acceleration and Learning:** Identify a meaningful bottleneck, demonstrate measurable progress, and justify the next experiment from what the lab learned.
- **Scientific Rigor:** Require citations for factual claims. Attach source evidence or run records, label agent-generated hypotheses, preserve uncertainty, document controls and human approval gates, and state validation still needed before real-world use.

---

## 8. Evaluation Criteria and Submission

### Rubric Breakdown
| Weight | Criterion | Focus |
|---|---|---|
| **30%** | **Omnigent Orchestration** | Specialist agent collaboration, tool use, dynamic plan adaptation |
| **25%** | **Breakthrough Potential** | Ambition and depth of scientific inquiry and discovery |
| **20%** | **Discovery Acceleration and Learning** | Measured bottleneck improvement and justified next experiment |
| **15%** | **Scientific Rigor** | Epistemic labeling, controls, uncertainty, citations, validation |
| **10%** | **Creativity and Responsibility** | Safety policies, human approval gates, limitations transparency |

### Submission Requirements
1. The repository
2. Agent specifications and policies
3. A two-minute demo video
4. Cited evidence
5. Experiment code and results
6. Measured improvement
7. Next experiment
