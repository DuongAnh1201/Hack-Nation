from omnigent_client import tool
from lab.tools import budget_left as _budget_left

@tool
def budget_left(run_id: str = 'default', max_budget: int = 2000) -> dict:
    """Check remaining simulation evaluation budget for the active session."""
    return _budget_left(run_id=run_id, max_budget=max_budget)
