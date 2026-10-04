"""Log reader for the analysis Lead. The department is fixed, so it can only read its own logs."""

from omnigent_client import tool
from lab.tools import read_department_logs as _read_department_logs


@tool
def read_department_logs(level: str = "department", run_id: str = "default") -> list:
    """Read the analysis department's log.

    Args:
        level: "specialist" for your specialist's results, "department" for your own decisions and reports.
        run_id: The run to read.
    """
    return _read_department_logs(department="analysis", level=level, run_id=run_id)
