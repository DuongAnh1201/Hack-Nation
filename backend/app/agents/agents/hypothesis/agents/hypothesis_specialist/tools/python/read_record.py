from omnigent_client import tool
from lab.tools import read_record as _read_record

@tool
def read_record(entry_id: str = '', run_id: str = 'default') -> dict:
    """Read a specific entry or full summary from the shared research record (record.jsonl)."""
    return _read_record(entry_id=entry_id, run_id=run_id)
