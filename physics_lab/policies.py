"""Omnigent policy module enforcing human approval gates and simulation quotas."""

import os
from typing import Any, Dict


def experiment_gate(call: Any, context: Any = None) -> Any:
    """Omnigent policy gate for run_experiment and simulate_once.

    Rules:
    1. DENY if parameters are physically impossible.
    2. ASK if simulation count > 400.
    3. ASK if tool call claims human_approved=True (agents cannot self-approve).
    4. ALLOW otherwise.
    """
    # Omnigent calls provide call.tool and call.arguments (or dict representation)
    tool_name = getattr(call, "tool", None) or (call.get("tool") if isinstance(call, dict) else "")
    args = getattr(call, "arguments", None) or (call.get("arguments") if isinstance(call, dict) else {})

    if tool_name not in ("run_experiment", "simulate_once"):
        return "ALLOW"

    # Self-approval check: An agent claiming human_approved must be gated by a human!
    if args.get("human_approved") is True:
        # Prompt human for verification
        return "ASK"

    if tool_name == "simulate_once":
        params = args.get("params", {})
        if params.get("initial_velocity", 1) <= 0 or params.get("mass", 1) <= 0:
            return "DENY"
        return "ALLOW"

    if tool_name == "run_experiment":
        spec = args.get("experiment_spec", {})
        conditions = spec.get("conditions", [])
        if not conditions:
            return "DENY"

        # Check for invalid parameters
        for c in conditions:
            p = c.get("params", {})
            if p.get("initial_velocity", 1) <= 0 or p.get("mass", 1) <= 0 or p.get("gravity", 1) <= 0:
                return "DENY"

        # Est count
        est_sims = len(conditions) * 25
        if est_sims > 400:
            return "ASK"

    return "ALLOW"
