"""Speed-up statistics for the benchmark (Person 2).

Input:  results/benchmark.json in the shared contract (README, "Data contracts").
Output: results/speedup.json       numbers for the UI speed-up panel
        results/speedup.md         the "Measured improvement" text and tables
        results/speedup_chart.svg  the key chart

Definitions, identical for every method so the comparison is fair:

* evaluations-to-target, one value per run; null means the run did not reach the
  target within the budget. Failed runs are never dropped.
* median evaluations = the number of evaluations by which half of the runs had
  reached the target: the ceil(n/2)-th smallest value (for 10 runs, the 5th).
  If fewer than half the runs reached the target, the median lies beyond the
  budget ("censored").
* speed-up of the focus method over a baseline = median(baseline) / median(focus).
  A censored baseline median is replaced by the budget, which can only understate
  the speed-up, so that result is reported as "at least". A censored focus median
  gives a speed-up of 0 (no claim).
* 95% CI: percentile bootstrap, resampling runs with replacement within each
  method independently (runs are not paired across methods), 10,000 resamples,
  fixed RNG seed. We claim the lower bound.

Run:  python -m analysis.speedup results/benchmark.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOTSTRAP = 10_000
DEFAULT_SEED = 12345
DEFAULT_FOCUS = "agent_lab"

LABELS = {
    "agent_lab": "Agent lab",
    "scripted_oracle": "Scripted oracle (upper bound)",
    "bayes_opt": "Bayesian optimization",
    "random": "Random search",
}
SHORT = {
    "agent_lab": "Agent lab",
    "scripted_oracle": "Scripted oracle",
    "bayes_opt": "Bayesian opt.",
    "random": "Random search",
}
# Fixed colour per method (validated categorical slots 1-4); colour follows the method, never its rank.
COLORS = {
    "agent_lab": "#2a78d6",
    "scripted_oracle": "#7048e8",
    "bayes_opt": "#eb6834",
    "random": "#1baf7a",
}
EXTRA_COLORS = ["#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


class BenchmarkError(ValueError):
    pass


@dataclass
class MethodRuns:
    name: str
    evals_to_target: list[int | None]
    best_w_m2: list[float]

    @property
    def n(self) -> int:
        return len(self.evals_to_target)

    def evals_array(self) -> np.ndarray:
        """Evaluations-to-target with failed runs as +inf."""
        return np.array([math.inf if e is None else float(e) for e in self.evals_to_target])


@dataclass
class Benchmark:
    target_w_m2: float
    budget: int
    seeds: int
    methods: dict[str, MethodRuns]
    fake: bool = False
    warnings: list[str] = field(default_factory=list)
    sha256: str = ""


def _is_ablation(name: str) -> bool:
    return "ablation" in name or "no_feedback" in name


def label(name: str) -> str:
    if name in LABELS:
        return LABELS[name]
    if _is_ablation(name):
        return "Agent lab, no analyst feedback (ablation)"
    return name.replace("_", " ").capitalize()


def phrase(name: str) -> str:
    """How the method reads inside a sentence."""
    if name == "agent_lab":
        return "the agent lab"
    if name == "random":
        return "random search"
    if _is_ablation(name):
        return "the ablation without analyst feedback"
    return label(name)


def short_label(name: str) -> str:
    """Compact name for direct labels on the chart."""
    if name in SHORT:
        return SHORT[name]
    if _is_ablation(name):
        return "Ablation"
    full = label(name)
    return full if len(full) <= 16 else full[:15] + "…"


def color_map(names: list[str]) -> dict[str, str]:
    extra = iter(EXTRA_COLORS)
    return {n: COLORS.get(n) or next(extra, "#898781") for n in names}


# --------------------------------------------------------------------- loading
def parse_benchmark(raw: dict[str, Any]) -> Benchmark:
    for key in ("target_w_m2", "budget", "methods"):
        if key not in raw:
            raise BenchmarkError(f"missing '{key}'")
    target = raw["target_w_m2"]
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        raise BenchmarkError(
            f"target_w_m2 must be a number, got {target!r}. Fill it with the Stanford design's "
            "P_net computed in our simulator (Person 4's control run)."
        )
    budget = raw["budget"]
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise BenchmarkError(f"budget must be a positive integer, got {budget!r}")
    if not isinstance(raw["methods"], dict) or not raw["methods"]:
        raise BenchmarkError("methods must be a non-empty object")

    warnings: list[str] = []
    methods: dict[str, MethodRuns] = {}
    for name, m in raw["methods"].items():
        if not m:
            warnings.append(f"method '{name}' has no runs yet; skipped")
            continue
        evals, best = m.get("evals_to_target"), m.get("best_w_m2")
        if not isinstance(evals, list) or not isinstance(best, list):
            raise BenchmarkError(f"{name}: needs lists 'evals_to_target' and 'best_w_m2'")
        if len(evals) != len(best):
            raise BenchmarkError(f"{name}: {len(evals)} evals_to_target values but {len(best)} best_w_m2 values")
        if not evals:
            warnings.append(f"method '{name}' has no runs yet; skipped")
            continue
        for i, e in enumerate(evals):
            if e is None:
                continue
            if isinstance(e, bool) or not isinstance(e, (int, float)) or e != int(e) or not 0 < e <= budget:
                raise BenchmarkError(f"{name} run {i}: evals_to_target must be null or an integer in 1..{budget}, got {e!r}")
            if best[i] < target - 1e-9:
                warnings.append(f"{name} run {i}: reached the target at {e} evaluations but best_w_m2 "
                                f"{best[i]} < target {target}; check the benchmark output")
        for i, b in enumerate(best):
            if b is None or isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b):
                raise BenchmarkError(f"{name} run {i}: best_w_m2 must be a finite number, got {b!r}")
        methods[name] = MethodRuns(name, [None if e is None else int(e) for e in evals], [float(b) for b in best])

    seeds = raw.get("seeds", 0)
    for m in methods.values():
        if seeds and m.n != seeds:
            warnings.append(f"{m.name}: {m.n} runs but seeds = {seeds}")
    if len({m.n for m in methods.values()}) > 1:
        warnings.append("methods have different numbers of runs: " +
                        ", ".join(f"{m.name}={m.n}" for m in methods.values()))
    return Benchmark(float(target), budget, int(seeds or 0), methods, bool(raw.get("_fake")), warnings)


def load_benchmark(path: str | Path) -> Benchmark:
    data = Path(path).read_bytes()
    try:
        raw = json.loads(data)
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"{path}: not valid JSON ({exc})") from exc
    bench = parse_benchmark(raw)
    bench.sha256 = hashlib.sha256(data).hexdigest()
    return bench


# ------------------------------------------------------------------ statistics
def median_evals(values: np.ndarray) -> float:
    """Evaluations by which half the runs had reached the target (inf if fewer than half did)."""
    k = math.ceil(len(values) / 2) - 1
    return float(np.sort(values)[k])


def bootstrap_medians(values: np.ndarray, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    n = len(values)
    k = math.ceil(n / 2) - 1
    idx = rng.integers(0, n, size=(n_boot, n))
    return np.sort(values[idx], axis=1)[:, k]


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(m: MethodRuns) -> dict[str, Any]:
    ev = m.evals_array()
    reached = int(np.isfinite(ev).sum())
    med = median_evals(ev)
    lo, hi = wilson_interval(reached, m.n)
    best = np.array(m.best_w_m2)
    return {
        "label": label(m.name),
        "runs": m.n,
        "reached": reached,
        "success_rate": reached / m.n,
        "success_rate_ci95": [lo, hi],
        "median_evals": None if math.isinf(med) else med,
        "median_censored": math.isinf(med),
        "best_w_m2_median": float(np.median(best)),
        "best_w_m2_max": float(best.max()),
    }


def _ratio(baseline_med: np.ndarray, focus_med: np.ndarray, budget: int) -> np.ndarray:
    b = np.where(np.isinf(baseline_med), float(budget), baseline_med)
    with np.errstate(divide="ignore", invalid="ignore"):
        return b / focus_med  # focus inf -> 0


def speedup(focus: MethodRuns, baseline: MethodRuns, budget: int, n_boot: int, seed: int) -> dict[str, Any]:
    f, b = focus.evals_array(), baseline.evals_array()
    point = float(_ratio(np.array([median_evals(b)]), np.array([median_evals(f)]), budget)[0])
    rng = np.random.default_rng(seed)
    ratios = _ratio(bootstrap_medians(b, n_boot, rng), bootstrap_medians(f, n_boot, rng), budget)
    lo, hi = (float(x) for x in np.percentile(ratios, [2.5, 97.5]))
    out = {
        "focus": focus.name,
        "baseline": baseline.name,
        "point": point,
        "ci95": [lo, hi],
        "baseline_censored": math.isinf(median_evals(b)),
        "focus_censored": math.isinf(median_evals(f)),
        "bootstrap": {"resamples": n_boot, "seed": seed, "method": "percentile, independent resampling per method"},
    }
    out["claim"] = claim_text(out, budget)
    out["supported"] = (not out["focus_censored"]) and lo > 1.0
    return out


def fmt_x(v: float) -> str:
    if math.isinf(v):
        return "∞"
    return f"{v:.1f}×" if v < 10 else f"{v:.0f}×"


def claim_text(s: dict[str, Any], budget: int) -> str:
    focus, base = phrase(s["focus"]), phrase(s["baseline"])
    Focus = focus[:1].upper() + focus[1:]
    lo, hi = s["ci95"]
    p = s["point"]
    if s["focus_censored"]:
        return f"No speed-up claimed over {base}: {focus} reached the target in fewer than half of its runs."
    prefix = "about "
    note = (f" {base[:1].upper() + base[1:]} reached the target in fewer than half of its runs, so its median "
            f"is capped at the budget of {budget} and the true speed-up is larger.") if s["baseline_censored"] else ""
    if lo > 1.0:
        return (f"{Focus} needed {prefix}{fmt_x(p)} fewer evaluations than {base} "
                f"(95% CI {fmt_x(lo)}–{fmt_x(hi)}); we claim at least {fmt_x(lo)}.{note}")
    if p > 1.0:
        return (f"{Focus} needed {fmt_x(p)} fewer evaluations than {base} in the point estimate, but the 95% CI "
                f"({fmt_x(lo)}–{fmt_x(hi)}) includes no speed-up, so no speed-up is claimed.{note}")
    slower = (1 / p) if p > 0 else math.inf
    return f"No speed-up: {focus} needed {fmt_x(slower)} as many evaluations as {base} (median)."


def reach_curve(m: MethodRuns, budget: int) -> list[list[float]]:
    """Share of runs that had reached the target by each evaluation count (a step function)."""
    pts = [[0, 0.0]]
    done = sorted(e for e in m.evals_to_target if e is not None)
    for i, e in enumerate(done, start=1):
        pts.append([e, i / m.n])
    pts.append([budget, len(done) / m.n])
    return pts


def analyze(bench: Benchmark, focus: str = DEFAULT_FOCUS, n_boot: int = DEFAULT_BOOTSTRAP,
            seed: int = DEFAULT_SEED, source: str = "results/benchmark.json") -> dict[str, Any]:
    if focus not in bench.methods:
        if focus == DEFAULT_FOCUS and "scripted_oracle" in bench.methods:
            focus = "scripted_oracle"
        else:
            raise BenchmarkError(f"focus method '{focus}' not in benchmark (have: {sorted(bench.methods)})")
    names = [focus] + [n for n in bench.methods if n != focus]
    comparisons = [speedup(bench.methods[focus], bench.methods[n], bench.budget, n_boot, seed) for n in names[1:]]
    return {
        "fake": bench.fake,
        "source": source,
        "source_sha256": bench.sha256,
        "command": f"python -m analysis.speedup {source}",
        "target_w_m2": bench.target_w_m2,
        "budget": bench.budget,
        "focus": focus,
        "method_order": names,
        "colors": color_map(names),
        "methods": {n: summarize(bench.methods[n]) for n in names},
        "speedups": comparisons,
        "curves": {n: reach_curve(bench.methods[n], bench.budget) for n in names},
        "warnings": bench.warnings,
        "definitions": {
            "median_evals": "evaluations by which half of the runs had reached the target (ceil(n/2)-th smallest; "
                            "failed runs count as not reached)",
            "speedup": "median(baseline) / median(focus); censored baseline median replaced by the budget "
                       "(understates the speed-up)",
            "ci95": f"percentile bootstrap, {n_boot} resamples, seed {seed}, runs resampled within each method",
        },
    }


# ------------------------------------------------------------------- rendering
def measured_improvement(r: dict[str, Any]) -> str:
    f = r["methods"][r["focus"]]
    parts = []
    for name in r["method_order"]:
        m = r["methods"][name]
        med = f"> {r['budget']}" if m["median_censored"] else f"{m['median_evals']:.0f}"
        parts.append(f"{phrase(name)} {med} ({m['reached']}/{m['runs']} runs reached it)")
    text = (f"On the same simulator, search space and budget ({r['budget']} evaluations per run, "
            f"{f['runs']} runs per method), the median number of evaluations needed to reach the target "
            f"net cooling power of {r['target_w_m2']:g} W/m² (the Stanford design in our simulator) was: "
            + "; ".join(parts) + ". ")
    text += " ".join(s["claim"] for s in r["speedups"])
    return text + " Failed runs are included in every number."


def render_markdown(r: dict[str, Any]) -> str:
    lines = ["# Measured improvement", ""]
    if r["fake"]:
        lines += ["> **FAKE DATA, for development only. Do not cite any number on this page.**", ""]
    lines += [measured_improvement(r), "",
              f"Reproduce: `{r['command']}` (input sha256 `{r['source_sha256'][:12]}`).", "",
              "## Per method", "",
              "| Method | Runs that reached the target | Median evaluations to target | Best P_net, median / max (W/m²) |",
              "|---|---|---|---|"]
    for name in r["method_order"]:
        m = r["methods"][name]
        lo, hi = m["success_rate_ci95"]
        med = f"> {r['budget']} (censored)" if m["median_censored"] else f"{m['median_evals']:.0f}"
        lines.append(f"| {m['label']} | {m['reached']}/{m['runs']} ({m['success_rate']:.0%}, 95% CI {lo:.0%}–{hi:.0%}) "
                     f"| {med} | {m['best_w_m2_median']:.1f} / {m['best_w_m2_max']:.1f} |")
    lines += ["", "## Speed-up", "", "| Comparison | Point estimate | 95% CI | We claim |", "|---|---|---|---|"]
    for s in r["speedups"]:
        lo, hi = s["ci95"]
        claim = f"at least {fmt_x(lo)}" if s["supported"] else "no speed-up"
        if s["supported"] and s["baseline_censored"]:
            claim += " (baseline capped at budget)"
        lines.append(f"| {label(s['focus'])} vs {phrase(s['baseline'])} | {fmt_x(s['point'])} | "
                     f"{fmt_x(lo)}–{fmt_x(hi)} | {claim} |")
    lines += ["", "![Share of runs that reached the target vs simulator evaluations](speedup_chart.svg)", "",
              "## Definitions", ""] + [f"- **{k}**: {v}" for k, v in r["definitions"].items()]
    lines += ["- With few runs per method the bootstrap interval is coarse; more seeds narrow it."]
    if r["warnings"]:
        lines += ["", "## Input warnings", ""] + [f"- {w}" for w in r["warnings"]]
    return "\n".join(lines) + "\n"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _nice_step(span: float, target_ticks: int = 5) -> float:
    raw = span / target_ticks
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def render_svg(r: dict[str, Any]) -> str:
    W, H = 760, 460
    left, right, top, bottom = 64, 190, 140, 58
    pw, ph = W - left - right, H - top - bottom
    budget = r["budget"]
    sx = lambda v: left + pw * v / budget  # noqa: E731
    sy = lambda p: top + ph * (1 - p)      # noqa: E731
    ink, ink2, muted, grid, axis, surface = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    font = 'font-family="system-ui, -apple-system, Segoe UI, sans-serif"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="t d">',
           f'<title id="t">Share of runs that reached the target vs simulator evaluations</title>',
           f'<desc id="d">{_esc(measured_improvement(r))}</desc>',
           f'<rect width="{W}" height="{H}" fill="{surface}"/>']
    title = "Share of runs that reached the target cooling power"
    out.append(f'<text x="{left}" y="30" {font} font-size="16" font-weight="600" fill="{ink}">{_esc(title)}</text>')
    sub = (f"target {r['target_w_m2']:g} W/m² (Stanford design in our simulator) · budget {budget:,} evaluations · "
           f"{r['methods'][r['focus']]['runs']} runs per method")
    sub2 = "Dots mark each method's median (where its line crosses 50%). Failed runs keep a line below 100%."
    out.append(f'<text x="{left}" y="50" {font} font-size="12" fill="{ink2}">{_esc(sub)}</text>')
    out.append(f'<text x="{left}" y="68" {font} font-size="12" fill="{ink2}">{_esc(sub2)}</text>')
    if r["fake"]:
        out.append(f'<rect x="{W - 214}" y="14" width="200" height="24" rx="4" fill="#d03b3b"/>'
                   f'<text x="{W - 114}" y="31" {font} font-size="12" font-weight="600" fill="#ffffff" '
                   f'text-anchor="middle">⚠ FAKE DATA · do not cite</text>')

    # legend (always present for 2+ series); wraps to a second row when it does not fit
    lx, ly = left, 94
    for name in r["method_order"]:
        lab = r["methods"][name]["label"]
        width = 24 + 6.6 * len(lab) + 22
        if lx > left and lx + width > W - 16:
            lx, ly = left, ly + 20
        out.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 18}" y2="{ly}" stroke="{r["colors"][name]}" '
                   f'stroke-width="2.5" stroke-linecap="round"/>')
        out.append(f'<text x="{lx + 24}" y="{ly + 4}" {font} font-size="12" fill="{ink2}">{_esc(lab)}</text>')
        lx += width

    # grid, axes, ticks
    for p in (0, 0.25, 0.5, 0.75, 1.0):
        y = sy(p)
        dash = ' stroke-dasharray="4 4"' if p == 0.5 else ""
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + pw}" y2="{y:.1f}" stroke="{axis if p == 0 else grid}" '
                   f'stroke-width="1"{dash}/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" {font} font-size="11" fill="{muted}" text-anchor="end">'
                   f'{p:.0%}</text>')
    step = _nice_step(budget)
    v = 0.0
    while v <= budget + 1e-9:
        x = sx(v)
        out.append(f'<line x1="{x:.1f}" y1="{top + ph}" x2="{x:.1f}" y2="{top + ph + 4}" stroke="{axis}"/>')
        out.append(f'<text x="{x:.1f}" y="{top + ph + 18}" {font} font-size="11" fill="{muted}" text-anchor="middle">'
                   f'{v:,.0f}</text>')
        v += step
    out.append(f'<text x="{left + pw / 2:.1f}" y="{H - 14}" {font} font-size="12" fill="{ink2}" text-anchor="middle">'
               f'Simulator evaluations used</text>')
    out.append(f'<text transform="translate(16 {top + ph / 2:.1f}) rotate(-90)" {font} font-size="12" fill="{ink2}" '
               f'text-anchor="middle">Runs that reached the target</text>')

    # step lines: surface ring under each, then the 2px coloured line; focus drawn last (on top)
    ends = []
    for name in reversed(r["method_order"]):
        pts = r["curves"][name]
        d = f"M{sx(pts[0][0]):.1f},{sy(pts[0][1]):.1f}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d += f" H{sx(x1):.1f} V{sy(y1):.1f}"
        out.append(f'<path d="{d}" fill="none" stroke="{surface}" stroke-width="6" stroke-linejoin="round"/>')
        out.append(f'<path d="{d}" fill="none" stroke="{r["colors"][name]}" stroke-width="2" stroke-linejoin="round" '
                   f'stroke-linecap="round"/>')
        ends.append([sy(pts[-1][1]), name])

    # median markers on top of every line, so no line can hide them
    for name in reversed(r["method_order"]):
        m = r["methods"][name]
        if not m["median_censored"]:
            mx, my = sx(m["median_evals"]), sy(0.5)
            out.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="5" fill="{r["colors"][name]}" stroke="{surface}" '
                       f'stroke-width="2"><title>{_esc(m["label"])}: median {m["median_evals"]:.0f} evaluations'
                       f'</title></circle>')

    # direct labels at the right end, nudged apart so they never collide
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 30)
    for y, name in ends:
        m = r["methods"][name]
        x = left + pw + 10
        out.append(f'<line x1="{x}" y1="{y:.1f}" x2="{x + 12}" y2="{y:.1f}" stroke="{r["colors"][name]}" '
                   f'stroke-width="2.5" stroke-linecap="round"/>')
        out.append(f'<text x="{x + 18}" y="{y + 4:.1f}" {font} font-size="12" font-weight="600" fill="{ink}">'
                   f'{_esc(short_label(name))}</text>')
        med = f"> {budget}" if m["median_censored"] else f"{m['median_evals']:.0f}"
        out.append(f'<text x="{x + 18}" y="{y + 18:.1f}" {font} font-size="11" fill="{ink2}">'
                   f'{m["reached"]}/{m["runs"]} reached · median {med}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m analysis.speedup", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("benchmark", nargs="?", default="results/benchmark.json")
    ap.add_argument("--focus", default=DEFAULT_FOCUS, help="method whose speed-up is claimed (default agent_lab)")
    ap.add_argument("--out", help="output directory (default: next to the input file)")
    ap.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args(argv)

    try:
        bench = load_benchmark(args.benchmark)
        result = analyze(bench, args.focus, args.bootstrap, args.seed, source=Path(args.benchmark).as_posix())
    except (BenchmarkError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else Path(args.benchmark).parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "speedup.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "speedup.md").write_text(render_markdown(result), encoding="utf-8")
    (out / "speedup_chart.svg").write_text(render_svg(result), encoding="utf-8")
    if result["fake"]:
        print("FAKE DATA: outputs are stamped and must not be cited.")
    for w in result["warnings"]:
        print(f"warning: {w}")
    print(measured_improvement(result))
    print(f"\nwrote {out / 'speedup.json'}, {out / 'speedup.md'}, {out / 'speedup_chart.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
