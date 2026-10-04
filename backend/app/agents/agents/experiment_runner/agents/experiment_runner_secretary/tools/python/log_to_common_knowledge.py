"""Tool for Department Secretaries to log findings into Common Knowledge."""

from omnigent_client import tool
from lab.tools import log_to_common_knowledge as _log_to_common_knowledge


@tool
def log_to_common_knowledge(department: str, payload: dict) -> dict:
    """Record an accepted scientific finding, hypothesis, or verdict into Common Knowledge.

    Args:
        department: Creating department ('literature', 'hypothesis', 'planning', 'analysis', 'review_safety').
        payload: Structured dictionary of the finding, hypothesis, or verdict.

    Returns:
        Confirmation dictionary with updated cycle count and status.
    """
    return _log_to_common_knowledge(department=department, payload=payload)
