"""Tool for Department Secretaries to write entries to the research record."""

from omnigent_client import tool
from lab.tools import write_record as _write_record


@tool
def write_record(kind: str, agent: str, content: dict, based_on: list = None, run_id: str = "default") -> dict:
    """Append a structured epistemic entry to the shared research record (record.jsonl)."""
    return _write_record(kind=kind, agent=agent, content=content, based_on=based_on, run_id=run_id)
