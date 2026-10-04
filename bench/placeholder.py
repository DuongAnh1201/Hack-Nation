"""Stand-in score used only until Person 4 connects simulate_stack.

The number is not a cooling power. It is higher for alternating high/low
index layers on silver with thicknesses near 100 nm, so the benchmark
pipeline can be tested before the simulator exists.
"""

from __future__ import annotations

import math

from bench.space import HIGH_INDEX, Stack

PLACEHOLDER_NAME = "bench.placeholder.placeholder_p_net"
PLACEHOLDER_WARNING = (
    "Placeholder score for pipeline tests. Not a measured cooling power. "
    "Do not report it as a result."
)


def placeholder_p_net(stack: Stack) -> float:
    score = 5.0 if stack.metal == "Ag" else 0.0
    for index, layer in enumerate(stack.layers):
        want_high = index % 2 == 0
        is_high = layer.material in HIGH_INDEX
        if is_high == want_high:
            score += 3.0
        log_error = math.log(layer.thickness_nm) - math.log(100.0)
        score += 2.0 * math.exp(-(log_error**2) / 0.5)
    return score
