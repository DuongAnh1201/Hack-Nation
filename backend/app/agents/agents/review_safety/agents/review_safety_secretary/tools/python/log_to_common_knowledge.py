"""Department log tool for the review_safety secretary. The department is fixed, so it can only write its own log."""

from omnigent_client import tool
from lab.tools import log_to_common_knowledge as _log_to_common_knowledge


# strict=False: in strict mode a `dict` parameter becomes an object with no allowed
# properties, so every field the agent sends is rejected.
@tool(strict=False)
def log_to_common_knowledge(payload: dict, level: str = "department", run_id: str = "default", repeat_of: str = "") -> dict:
    """Append an entry to the review_safety department's log.

    Args:
        payload: What the Lead asked you to log.
        level: "specialist" for the specialist's results, "department" for the Lead's decisions and reports.
        run_id: The run this belongs to.
        repeat_of: ID of the earlier entry this repeats, when the Lead says it is a repeat; otherwise "".

    Returns:
        The new entry's ID and log path.
    """
    return _log_to_common_knowledge(department="review_safety", payload=payload, level=level, run_id=run_id, repeat_of=repeat_of)
