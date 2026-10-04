# AGENTS.md - Repository Agent Guidelines

This repository participates in the **7th Global AI Hackathon (Databricks × Hack-Nation): Challenge 03 — Agentic Scientific Discovery**.

All AI agents operating in this workspace must adhere to the challenge rules and architecture defined in [.agents/rules/challenge_guidelines.md](file://.agents/rules/challenge_guidelines.md) and the official brief in [docs/challenge-brief/CHALLENGE_BRIEF.md](file://docs/challenge-brief/CHALLENGE_BRIEF.md).

## Core Requirements & Invariants

1. **Platform Mandate:** All agentic workflows must be built with or orchestrate through **Omnigent**.
2. **Scientific Objective:** Build an AI lab that automates scientific discovery (hypotheses formulation, experimental design, numerical simulation, prospective validation, and continuous adaptation).
3. **Dual Issue Mandate:**
   - **Issue #7 (Courses Requirements):** 4 major physical pillars (Kinematics baseline, Quadratic drag perturbation, Energy conservation, Dimensional scaling laws) and 3 interactive demo experiments.
   - **Issue #8 (Agent Orchestration):** Omnigent supervisor-specialist multi-agent graph with shared research record, epistemic status labels, and human approval safety gates.
4. **Epistemic Tracking:** Always record epistemic statuses (`established_fact`, `ai_hypothesis`, `ai_prediction`, `simulation_result`, `analysis`, `decision`, `conclusion: pending_human_review`).
5. **Human Approval Gates:** Implement safety gates preventing unapproved simulations over 400 runs or self-claimed human approvals.
