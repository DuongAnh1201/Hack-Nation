from omnigent_client import tool
from lab.tools import execute_experiment_script as _execute_experiment_script

@tool
def execute_experiment_script(
    experiment_id: str,
    materials: list[str],
    thicknesses_nm: list[float] | None = None,
    substrate: str = "Ag",
    budget: int = 40,
    run_id: str = "default",
) -> dict:
    """Generate reproducible simulation script, run optical simulations, and save CSV dataset (Issue #26)."""
    return _execute_experiment_script(
        experiment_id=experiment_id,
        materials=materials,
        thicknesses_nm=thicknesses_nm,
        substrate=substrate,
        budget=budget,
        run_id=run_id,
    )
