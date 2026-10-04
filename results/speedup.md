# Measured improvement

On the same simulator, search space and budget (100 evaluations per run, 5 runs per method), the median number of evaluations needed to reach the target net cooling power of 50 W/m² (the Stanford design in our simulator) was: Scripted oracle (upper bound) 34 (4/5 runs reached it); random search > 100 (2/5 runs reached it); Alternating 27 (4/5 runs reached it); Bayesian optimization 45 (5/5 runs reached it); Genetic algorithm 99 (3/5 runs reached it); Scripted oracle no analyst > 100 (0/5 runs reached it). Scripted oracle (upper bound) needed 2.9× fewer evaluations than random search in the point estimate, but the 95% CI (0.0×–3.6×) includes no speed-up, so no speed-up is claimed. Random search reached the target in fewer than half of its runs, so its median is capped at the budget of 100 and the true speed-up is larger. No speed-up: Scripted oracle (upper bound) needed 1.3× as many evaluations as Alternating (median). Scripted oracle (upper bound) needed 1.3× fewer evaluations than Bayesian optimization in the point estimate, but the 95% CI (0.0×–1.6×) includes no speed-up, so no speed-up is claimed. Scripted oracle (upper bound) needed 2.9× fewer evaluations than Genetic algorithm in the point estimate, but the 95% CI (0.0×–3.5×) includes no speed-up, so no speed-up is claimed. Scripted oracle (upper bound) needed 2.9× fewer evaluations than Scripted oracle no analyst in the point estimate, but the 95% CI (0.0×–3.6×) includes no speed-up, so no speed-up is claimed. Scripted oracle no analyst reached the target in fewer than half of its runs, so its median is capped at the budget of 100 and the true speed-up is larger. Failed runs are included in every number.

Reproduce: `python -m analysis.speedup results/benchmark.json` (input sha256 `d2b3f18012ac`).

## Per method

| Method | Runs that reached the target | Median evaluations to target | Best P_net, median / max (W/m²) |
|---|---|---|---|
| Scripted oracle (upper bound) | 4/5 (80%, 95% CI 38%–96%) | 34 | 53.6 / 56.9 |
| Random search | 2/5 (40%, 95% CI 12%–77%) | > 100 (censored) | 48.1 / 54.0 |
| Alternating | 4/5 (80%, 95% CI 38%–96%) | 27 | 50.9 / 52.1 |
| Bayesian optimization | 5/5 (100%, 95% CI 57%–100%) | 45 | 51.9 / 53.5 |
| Genetic algorithm | 3/5 (60%, 95% CI 23%–88%) | 99 | 50.8 / 52.7 |
| Scripted oracle no analyst | 0/5 (0%, 95% CI 0%–43%) | > 100 (censored) | 31.5 / 34.8 |

## Speed-up

| Comparison | Point estimate | 95% CI | We claim |
|---|---|---|---|
| Scripted oracle (upper bound) vs random search | 2.9× | 0.0×–3.6× | no speed-up |
| Scripted oracle (upper bound) vs Alternating | 0.8× | 0.0×–2.9× | no speed-up |
| Scripted oracle (upper bound) vs Bayesian optimization | 1.3× | 0.0×–1.6× | no speed-up |
| Scripted oracle (upper bound) vs Genetic algorithm | 2.9× | 0.0×–3.5× | no speed-up |
| Scripted oracle (upper bound) vs Scripted oracle no analyst | 2.9× | 0.0×–3.6× | no speed-up |

![Share of runs that reached the target vs simulator evaluations](speedup_chart.svg)

## Definitions

- **median_evals**: evaluations by which half of the runs had reached the target (ceil(n/2)-th smallest; failed runs count as not reached)
- **speedup**: median(baseline) / median(focus); censored baseline median replaced by the budget (understates the speed-up)
- **ci95**: percentile bootstrap, 10000 resamples, seed 12345, runs resampled within each method
- With few runs per method the bootstrap interval is coarse; more seeds narrow it.
