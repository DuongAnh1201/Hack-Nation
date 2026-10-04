"""Research record read tool for Omnigent agents."""

from omnigent_client import tool
from lab.tools import read_record as _read_record


@tool
def read_record(entry_id: str = "", run_id: str = "default") -> dict:
    """Read a specific entry or full summary from the shared research record (record.jsonl).

    Args:
        entry_id: Optional ID of the record entry to inspect (e.g. 'L1', 'H2').
                  If omitted or empty, returns summary metrics and all entries.
        run_id: Identifier of the lab experiment session (default 'default').

    Returns:
        Dictionary containing entry details or overall research record summary.
    """
    return _read_record(entry_id=entry_id, run_id=run_id)
