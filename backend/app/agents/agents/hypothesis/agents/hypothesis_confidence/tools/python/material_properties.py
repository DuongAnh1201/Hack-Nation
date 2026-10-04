from omnigent_client import tool
from lab.tools import material_properties as _material_properties

@tool
def material_properties(material: str) -> dict:
    """Return physical optical and engineering properties for a coating material."""
    return _material_properties(material=material)
