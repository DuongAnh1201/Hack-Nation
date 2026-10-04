from omnigent_client import tool
from lab.tools import run_experiment as _run_experiment

@tool
def run_experiment(
    experiment_id: str,
    run_id: str = "default",
) -> dict:
    """Run an agent-written experiment script in runs/<run_id>/experiments/<experiment_id>/ (Issue #48)."""
    return _run_experiment(
        experiment_id=experiment_id,
        run_id=run_id,
    )
