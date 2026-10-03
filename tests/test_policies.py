"""Tests for Omnigent safety policies and human approval boundaries."""

from physics_lab.policies import experiment_gate


class MockCall:
    def __init__(self, tool: str, arguments: dict):
        self.tool = tool
        self.arguments = arguments


def test_policy_allows_normal_simulation():
    call = MockCall(
        tool="run_experiment",
        arguments={
            "experiment_spec": {
                "conditions": [{"label": "test", "params": {"initial_velocity": 30.0, "mass": 0.145, "gravity": 9.81}}]
            }
        },
    )
    assert experiment_gate(call) == "ALLOW"


def test_policy_denies_invalid_physics():
    call = MockCall(
        tool="run_experiment",
        arguments={
            "experiment_spec": {
                "conditions": [{"label": "test", "params": {"initial_velocity": -10.0, "mass": 0.145, "gravity": 9.81}}]
            }
        },
    )
    assert experiment_gate(call) == "DENY"


def test_policy_asks_for_human_on_budget_exceeded():
    # 20 conditions * 25 sims = 500 sims > 400
    conditions = [{"label": f"cond_{i}", "params": {"initial_velocity": 30.0, "mass": 0.145, "gravity": 9.81}} for i in range(20)]
    call = MockCall(
        tool="run_experiment",
        arguments={"experiment_spec": {"conditions": conditions}},
    )
    assert experiment_gate(call) == "ASK"


def test_policy_denies_agent_self_approval():
    """An agent claiming human_approved=True must be intercepted by the human gate (ASK)."""
    call = MockCall(
        tool="run_experiment",
        arguments={
            "human_approved": True,
            "experiment_spec": {
                "conditions": [{"label": "test", "params": {"initial_velocity": 30.0, "mass": 0.145, "gravity": 9.81}}]
            },
        },
    )
    assert experiment_gate(call) == "ASK"
