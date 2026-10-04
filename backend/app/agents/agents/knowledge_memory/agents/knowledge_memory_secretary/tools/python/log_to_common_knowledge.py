"""Department log tool for the knowledge_memory secretary. The department is fixed, so it can only write its own log."""

from omnigent_client import tool
from lab.tools import log_to_common_knowledge as _log_to_common_knowledge


@tool
def log_to_common_knowledge(payload: dict, level: str = "department", run_id: str = "default", repeat_of: str = "") -> dict:
    """Append an entry to the knowledge_memory department's log.

    Args:
        payload: What the Lead asked you to log.
        level: "specialist" for the specialist's results, "department" for the Lead's decisions and reports.
        run_id: The run this belongs to.
        repeat_of: ID of the earlier entry this repeats, when the Lead says it is a repeat; otherwise "".

    Returns:
        The new entry's ID and log path.
    """
    return _log_to_common_knowledge(department="knowledge_memory", payload=payload, level=level, run_id=run_id, repeat_of=repeat_of)
