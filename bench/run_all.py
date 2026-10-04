"""Benchmark runner for radiative cooling baselines and AI lab.

Writes results to `results/benchmark.json` matching the shared contract:
{
  "target_w_m2": <float>,
  "budget": <int>,
  "seeds": <int>,
  "methods": {
    "random": {
      "evals_to_target": [...],
      "best_w_m2": [...]
    },
    "bayes_opt": {},
    "agent_lab": {}
  }
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from bench.random_search import get_default_target, run_random_search

RESULTS_DIR = WORKSPACE_ROOT / "results"
BENCHMARK_PATH = RESULTS_DIR / "benchmark.json"


def run_benchmark(
    seeds: List[int],
    budget: int = 20,
    target_w_m2: float = None,
    output_path: Path = BENCHMARK_PATH,
) -> Dict[str, Any]:
    """Execute benchmark across given seeds and write results/benchmark.json."""
    if target_w_m2 is None:
        target_w_m2 = get_default_target()

    random_evals: List[Any] = []
    random_best: List[Any] = []

    for s in seeds:
        res = run_random_search(seed=s, budget=budget, target_w_m2=target_w_m2)
        random_evals.append(res["evals_to_target"])  # None becomes null in json
        random_best.append(res["best_w_m2"])

    benchmark_data: Dict[str, Any] = {
        "target_w_m2": target_w_m2,
        "budget": budget,
        "seeds": len(seeds),
        "methods": {
            "random": {
                "evals_to_target": random_evals,
                "best_w_m2": random_best,
            },
            "bayes_opt": {},
            "agent_lab": {},
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    return benchmark_data


def main():
    parser = argparse.ArgumentParser(description="Run radiative cooling benchmark suite.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0], help="Seed(s) to run (default: [0])")
    parser.add_argument("--budget", type=int, default=20, help="Per-seed evaluation budget (default: 20)")
    parser.add_argument("--target", type=float, default=None, help="Target net cooling power W/m^2")
    parser.add_argument("--out", type=str, default=str(BENCHMARK_PATH), help="Output json path")
    args = parser.parse_args()

    data = run_benchmark(
        seeds=args.seeds,
        budget=args.budget,
        target_w_m2=args.target,
        output_path=Path(args.out),
    )
    print(f"Benchmark results written to {args.out}:")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
