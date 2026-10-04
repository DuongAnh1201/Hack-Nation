"""Command-line interface for the physics laboratory."""

import argparse
import json
import sys
from physics_lab.physics.models import ProjectileParams
from physics_lab.physics.engine import simulate
from physics_lab.agents.autopilot import run_discovery_autopilot
from physics_lab.benchmark import run_benchmark


def main():
    parser = argparse.ArgumentParser(description="Physics AI Lab: Autonomous Scientific Discovery")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover
    discover_parser = subparsers.add_parser("discover", help="Run the autonomous scientific discovery loop")
    discover_parser.add_argument("--record", default="runs/live/record.json", help="Path to save research record")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Simulate a projectile trajectory")
    sim_parser.add_argument("--params", type=str, default="{}", help="JSON string of ProjectileParams")
    sim_parser.add_argument("--trajectory", action="store_true", help="Include trajectory frame vectors")

    # benchmark
    subparsers.add_parser("benchmark", help="Run benchmark comparing AI lab vs manual protocol")

    args = parser.parse_args()

    if args.command == "discover":
        print(f"Starting autonomous discovery run... Saving to {args.record}")
        rec = run_discovery_autopilot(record_path=args.record, narration_callback=print)
        print(f"\nDone! Research record written to: {args.record}")
        print(f"Total simulations: {rec.metrics.get('simulations')}")
    elif args.command == "simulate":
        params_dict = json.loads(args.params)
        params = ProjectileParams.from_dict(params_dict)
        res = simulate(params, record_trajectory=args.trajectory)
        print(json.dumps(res.to_dict(), indent=2))
    elif args.command == "benchmark":
        run_benchmark()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
