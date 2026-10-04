from omnigent_client import tool
from lab.tools import list_materials as _list_materials

@tool
def list_materials() -> list:
    """Return allowed candidate dielectric materials and substrates under project constraints."""
    return _list_materials()
