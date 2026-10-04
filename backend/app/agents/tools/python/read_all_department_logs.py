"""Reader for every department's department-level log. Specialist logs are not included."""

from omnigent_client import tool
from lab.tools import read_all_department_logs as _read_all_department_logs


@tool
def read_all_department_logs(run_id: str = "default") -> dict:
    """Read the department log of every department: the Leads' decisions and reports.

    Specialist logs are not included; ask the department's Lead for that detail.
    """
    return _read_all_department_logs(run_id=run_id)
