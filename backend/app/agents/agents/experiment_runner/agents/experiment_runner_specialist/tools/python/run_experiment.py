from omnigent_client import tool
from lab.tools import run_experiment as _run_experiment

@tool
def run_experiment(experiment_id: str, run_id: str = "default", timeout_s: int = 600) -> dict:
    """Run the run.py you wrote in runs/<run_id>/experiments/<experiment_id>/ and save its output to output.log.

    Returns the exit code, whether it timed out, the file paths, and the number of rows in results.csv.
    """
    return _run_experiment(experiment_id=experiment_id, run_id=run_id, timeout_s=timeout_s)
