from omnigent_client import tool
from lab.tools import optimize_thicknesses_tool as _optimize_thicknesses

@tool
def optimize_thicknesses(materials: list, substrate: str = 'Ag', budget: int = 50, seed: int = 0) -> dict:
    """Optimize layer thicknesses for a material stack to maximize net radiative cooling power."""
    return _optimize_thicknesses(materials=materials, substrate=substrate, budget=budget, seed=seed)
