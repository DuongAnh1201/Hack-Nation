"""Run every method on the same seeds, budget, objective, and search space.

Agent and ablation rows stay `not_run` until Person 3 passes --agent / --ablation.
Placeholder scores are marked and must never be quoted as cooling power.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

from bench import space
from bench.placeholder import PLACEHOLDER_WARNING
from bench.plugins import PLACEHOLDER_KEY, load, resolve_objective
from bench.search import BASELINES, SearchResult, not_run, run_external, run_search
from bench.summary import best_so_far_curve, evaluation_grid, speedup_interval, success_curve, summarize_method

METHODS = ("random", "alternating", "tpe", "ga", "agent", "ablation")
CONTRACT_NAMES = {
    "random": "random",
    "alternating": "alternating",
    "tpe": "bayes_opt",
    "ga": "genetic_algorithm",
    "agent": "agent_lab",
    "ablation": "agent_lab_ablation",
}
REFERENCES = ("random", "alternating", "tpe", "ga")
ROOT = Path(__file__).resolve().parent.parent


def run_benchmark(
    *,
    seeds: list[int],
    budget: int,
    target: float | None,
    objective_name: str,
    objective,
    measured: bool,
    agent=None,
    ablation=None,
    counter=None,
    agent_seeds: list[int] | None = None,
    methods: tuple[str, ...] = METHODS,
    resamples: int = 2000,
    target_source: str | None = None,
    progress=None,
) -> dict:
    rows: list[SearchResult] = []
    runners = {"agent": agent, "ablation": ablation}
    for method in methods:
        method_seeds = seeds if method in BASELINES or agent_seeds is None else agent_seeds
        for seed in method_seeds:
            if method in BASELINES:
                row = run_search(method, objective, seed=seed, budget=budget, target=target)
            elif runners.get(method) is None:
                row = not_run(method, seed, budget, f"no --{method} runner given (Person 3)")
            else:
                row = run_external(
                    method, runners[method], objective, seed=seed, budget=budget, target=target, counter=counter
                )
            rows.append(row)
            if progress:
                progress(row)

    by_method = {method: [row for row in rows if row.method == method] for method in methods}
    grid = evaluation_grid(budget)
    summaries = {method: summarize_method(group) for method, group in by_method.items()}
    curves = {
        method: {"success": success_curve(group, grid), "best_so_far": best_so_far_curve(group, grid)}
        for method, group in by_method.items()
    }

    def compare(base_rows: list[SearchResult], other_rows: list[SearchResult]) -> dict:
        primary = speedup_interval(base_rows, other_rows, budget=budget, resamples=resamples)
        secondary = speedup_interval(
            base_rows, other_rows, budget=budget, statistic="median", resamples=resamples
        )
        return {**primary, "median_based": secondary}

    speedups: dict = {}
    for method in methods:
        speedups[method] = {
            f"vs_{reference}": compare(by_method[reference], by_method[method])
            for reference in REFERENCES
            if reference in by_method and reference != method
        }
    if "agent" in by_method and "ablation" in by_method:
        speedups["agent"]["vs_ablation"] = compare(by_method["ablation"], by_method["agent"])

    return {
        "measured": measured and target is not None,
        "objective": objective_name,
        "warning": None if measured else PLACEHOLDER_WARNING,
        "target_p_net": target,
        "target_source": target_source,
        "budget": budget,
        "seeds": seeds,
        "agent_seeds": agent_seeds if agent_seeds is not None else seeds,
        "search_space": {
            "materials": list(space.MATERIALS),
            "metals": list(space.METALS),
            "layers": [space.MIN_LAYERS, space.MAX_LAYERS],
            "thickness_nm": [space.THICKNESS_NM_MIN, space.THICKNESS_NM_MAX],
        },
        "rules": {
            "unit": "unique simulator calls; a repeated design is free",
            "primary_statistic": "restricted mean evaluations to target, every run capped at the budget",
            "secondary_statistic": "median evaluations; a method miss counts as never reaching the target",
            "baseline_miss": "counted at the budget, so the true speed-up can only be larger",
            "claim": "ci95_low of a 95% bootstrap interval",
            "invalid_runs": "any run that bypassed the counter blocks the comparison",
        },
        "rows": [row.to_dict() for row in rows],
        "summary": summaries,
        "curves": {"grid": grid, **curves},
        "speedup": speedups,
        "headline": headline(summaries, speedups, measured and target is not None, len(seeds)),
    }


def headline(summaries: dict, speedups: dict, measured: bool, n_seeds: int | str) -> list[str]:
    if not measured:
        return ["Not measured: placeholder objective or no target. Do not quote any number from this file."]
    lines = []
    for method in ("agent", "ga", "tpe", "alternating"):
        for reference, result in speedups.get(method, {}).items():
            if result.get("claim") is None or reference == f"vs_{method}":
                continue
            bound = "at least " if result["lower_bound_only"] else ""
            lines.append(
                f"{method} {reference.replace('_', ' ')}: {bound}{result['claim']:.2f}x faster to target "
                f"(point {result['speedup']:.2f}x, 95% CI {result['ci95_low']:.2f}-{result['ci95_high']:.2f}, "
                f"runs {result['baseline_runs']} vs {result['method_runs']}, "
                f"misses: {result['baseline_misses']} baseline / {result['method_misses']} {method})"
            )
    for method, summary in summaries.items():
        if summary["attempted"]:
            lines.append(
                f"{method}: reached target in {summary['successes']}/{summary['attempted']} runs, "
                f"median evaluations {summary['median_evaluations_to_target']}"
            )
    return lines


class ContractError(ValueError):
    pass


def to_contract(payload: dict, full_path: str | None = None) -> dict:
    if payload["target_p_net"] is None:
        raise ContractError("no target: pass --target from the Stanford control")
    rows = [row for row in payload["rows"] if row["status"] != "not_run"]
    bad = [f"{row['method']} seed {row['seed']}: {row['status']}" for row in rows if row["status"] in ("invalid", "error")]
    if bad:
        raise ContractError("fix or rerun these runs first: " + "; ".join(bad))
    methods: dict = {}
    for method in payload["summary"]:
        mine = [row for row in rows if row["method"] == method]
        if not mine:
            continue
        missing = [row["seed"] for row in mine if row["best_p_net"] is None]
        if missing:
            raise ContractError(f"{method}: no valid design evaluated for seeds {missing}")
        methods[CONTRACT_NAMES.get(method, method)] = {
            "evals_to_target": [row["evaluations_to_target"] for row in mine],
            "best_w_m2": [round(row["best_p_net"], 4) for row in mine],
        }
    contract = {
        "target_w_m2": payload["target_p_net"],
        "budget": payload["budget"],
        "seeds": len(payload["seeds"]),
        "methods": methods,
        "source": "bench.run_all",
        "objective": payload["objective"],
        "target_source": payload["target_source"],
        "full_results": full_path,
    }
    if not payload["measured"]:
        contract = {
            "_fake": True,
            "_note": "Placeholder objective from bench.run_all for pipeline tests. Not results.",
            **contract,
        }
    return contract


def provenance(argv: list[str]) -> dict:
    files = sorted(Path(__file__).resolve().parent.glob("*.py"))
    info = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "command": "python -m bench.run_all " + " ".join(argv),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "bench_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()[:16] for path in files},
        "git_head": _git_head(),
    }
    try:
        import optuna

        info["optuna"] = optuna.__version__
    except ImportError:
        info["optuna"] = None
    return info


def _git_head() -> str | None:
    head = ROOT / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref: "):
            ref = ROOT / ".git" / text[5:]
            if ref.exists():
                return ref.read_text(encoding="utf-8").strip()
            packed = ROOT / ".git" / "packed-refs"
            for line in packed.read_text(encoding="utf-8").splitlines() if packed.exists() else []:
                if line.endswith(text[5:]):
                    return line.split()[0]
            return None
        return text
    except OSError:
        return None


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="Run the radiative-cooling speed-up benchmark.")
    parser.add_argument("--seeds", type=int, default=1, help="How many seeds for the baselines.")
    parser.add_argument("--agent-seeds", type=int, default=None, help="How many seeds for agent and ablation.")
    parser.add_argument("--seed-start", type=int, default=0, help="First seed.")
    parser.add_argument("--budget", type=int, default=20, help="Unique simulator calls allowed per run.")
    parser.add_argument("--target", type=float, default=None, help="Target P_net (W/m2), from the Stanford control.")
    parser.add_argument("--target-source", default=None, help="Where the target came from, for the record.")
    parser.add_argument("--objective", default=PLACEHOLDER_KEY, help="'placeholder' or 'lab.physics:simulate_stack'.")
    parser.add_argument("--agent", default=None, help="Person 3's runner, e.g. 'lab.bench_entry:run_agent'.")
    parser.add_argument("--ablation", default=None, help="Same runner with the analyst feedback off.")
    parser.add_argument("--counter", default=None, help="Simulator call counter, e.g. 'lab.physics:evaluation_count'.")
    parser.add_argument("--methods", default=",".join(METHODS), help="Comma-separated subset of methods.")
    parser.add_argument("--resamples", type=int, default=2000, help="Bootstrap resamples.")
    parser.add_argument("--out", type=Path, default=None, help="Shared-contract file for analysis/speedup.py.")
    parser.add_argument("--out-full", type=Path, default=None, help="Full results with runs, curves, provenance.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    objective_name, objective, real = resolve_objective(args.objective)
    methods = tuple(method.strip() for method in args.methods.split(",") if method.strip())
    unknown = set(methods) - set(METHODS)
    if unknown:
        parser.error(f"unknown methods: {sorted(unknown)}")

    def progress(row: SearchResult) -> None:
        if args.quiet:
            return
        hit = row.evaluations_to_target if row.success else "-"
        best = "-" if row.best_p_net is None or not math.isfinite(row.best_p_net) else f"{row.best_p_net:.3f}"
        print(f"{row.method:<12} seed {row.seed:<4} {row.status:<8} evals {row.evaluations:<6} hit {hit!s:<6} best {best}")

    payload = run_benchmark(
        seeds=list(range(args.seed_start, args.seed_start + args.seeds)),
        budget=args.budget,
        target=args.target,
        objective_name=objective_name,
        objective=objective,
        measured=real,
        agent=load(args.agent) if args.agent else None,
        ablation=load(args.ablation) if args.ablation else None,
        counter=load(args.counter) if args.counter else None,
        agent_seeds=None
        if args.agent_seeds is None
        else list(range(args.seed_start, args.seed_start + args.agent_seeds)),
        methods=methods,
        resamples=args.resamples,
        target_source=args.target_source,
        progress=progress,
    )
    payload["provenance"] = provenance(argv)
    out = args.out or Path("results/benchmark.json" if payload["measured"] else "results/benchmark.placeholder.json")
    full = args.out_full or out.with_name(out.stem + "_full.json")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    print(f"wrote {full} (full results, measured={str(payload['measured']).lower()})")
    try:
        contract = to_contract(payload, full.as_posix())
    except ContractError as exc:
        print(f"did not write {out}: {exc}")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(contract, indent=2, allow_nan=False), encoding="utf-8")
        print(f"wrote {out} (shared contract for analysis/speedup.py)")
    for line in payload["headline"]:
        print(line)


if __name__ == "__main__":
    main()
