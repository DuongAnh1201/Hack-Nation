from omnigent_client import tool
from lab.tools import simulate_stack_tool as _simulate_stack

@tool
def simulate_stack(materials: list, thicknesses_nm: list, substrate: str = 'Ag') -> dict:
    """Simulate multilayer coating net cooling power using the transfer-matrix method (TMM)."""
    return _simulate_stack(materials=materials, thicknesses_nm=thicknesses_nm, substrate=substrate)
