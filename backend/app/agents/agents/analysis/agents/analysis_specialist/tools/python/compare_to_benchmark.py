from omnigent_client import tool
from lab.tools import compare_to_benchmark as _compare_to_benchmark

@tool
def compare_to_benchmark(p_net_w_m2: float) -> dict:
    """Compare cooling power result against Stanford 2014 benchmark in our simulator (11.83 W/m2)."""
    return _compare_to_benchmark(p_net_w_m2=p_net_w_m2)
