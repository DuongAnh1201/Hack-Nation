"""Research record write tool for Omnigent agents."""

from omnigent_client import tool
from lab.tools import write_record as _write_record


# strict=False: in strict mode a `dict` parameter becomes an object with no allowed
# properties, so every field the agent sends is rejected.
@tool(strict=False)
def write_record(kind: str, agent: str, content: dict, based_on: list = None, run_id: str = "default") -> dict:
    """Append a structured epistemic entry to the shared research record (record.jsonl).

    Args:
        kind: Type of record entry ('literature', 'hypothesis', 'plan', 'experiment', 'result', 'verdict', 'approval').
        agent: Identifier of the creating agent (e.g. 'literature_lead').
        content: Structured payload of the finding, hypothesis, or verdict.
        based_on: List of prior record IDs supporting this entry (e.g. ['L1', 'R2']).
        run_id: Identifier of the lab experiment session (default 'default').

    Returns:
        The created record entry object including its assigned record ID.
    """
    return _write_record(kind=kind, agent=agent, content=content, based_on=based_on, run_id=run_id)
