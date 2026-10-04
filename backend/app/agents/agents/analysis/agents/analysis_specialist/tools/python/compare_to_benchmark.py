from omnigent_client import tool
from lab.tools import compare_to_benchmark as _compare_to_benchmark

@tool
def compare_to_benchmark(
    p_net_w_m2: float,
    solar_reflectance: float | None = None,
    window_emissivity: float | None = None,
) -> dict:
    """Compare cooling metrics against Stanford 2014 benchmark in our simulator (Issue #48)."""
    return _compare_to_benchmark(
        p_net_w_m2=p_net_w_m2,
        solar_reflectance=solar_reflectance,
        window_emissivity=window_emissivity,
    )

