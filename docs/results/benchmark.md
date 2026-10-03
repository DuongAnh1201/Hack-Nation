# Benchmark: AI lab vs manual protocol

Target: theta*(beta) over beta in [0.01, 100] with max error <= 0.1 deg, scored on 30 random test points.

## Single optimum (10 conditions)

| Method | Simulations per optimum | Max error (deg) |
|---|---|---|
| Manual sweep (1 deg, then 0.1 deg) | 110 | 0.049 |
| Adaptive bracket + golden section | 22.0 | 0.0020 |

## Whole curve

| Method | Simulations | Human decisions | Max error (deg) | RMSE (deg) |
|---|---|---|---|---|
| Manual grid, 5 points + interpolation | 550 | 5 | 0.508 | 0.249 |
| Manual grid, 9 points + interpolation | 990 | 9 | 0.175 | 0.084 |
| Manual grid, 17 points + interpolation | 1870 | 17 | 0.038 | 0.020 |
| Manual grid, 33 points + interpolation | 3630 | 33 | 0.047 | 0.022 |
| Manual grid, 65 points + interpolation | 7150 | 65 | 0.043 | 0.024 |
| AI lab (autonomous, law `cot(theta*) = 1 + a*ln(1 + c*beta)`) | 651 | 0 | 0.033 | 0.017 |

**Measured:** the cheapest manual grid that meets the target needs 1870 simulations; the AI lab used 651 (2.9x fewer), and produced a closed-form law instead of a lookup table.

**Caveats**

- Reference values come from a separate high-precision search (tol 1e-4 deg) not visible to either arm.
- The baseline is given the beta reduction for free; without it, it would have to grid 6 raw inputs.
- The AI-lab count includes controls, invariance tests and hold-out validation the baseline does not do.
- A smarter baseline (splines, adaptive refinement) would need fewer points; this is a manual protocol.
