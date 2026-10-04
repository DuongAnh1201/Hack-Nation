import { animate, useReducedMotion } from "motion/react";
import { Play } from "lucide-react";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import type { Speedup } from "../lib/data";
import { methodColors } from "../lib/materials";

const W = 900, H = 300, ML = 52, MR = 190, MT = 14, MB = 40;
const PW = W - ML - MR, PH = H - MT - MB;

function shareAt(curve: [number, number][], x: number): number {
  let s = 0;
  for (const [e, v] of curve) if (e <= x) s = v;
  return s;
}

function stepPath(curve: [number, number][], xs: (v: number) => number, ys: (v: number) => number): string {
  let d = `M${xs(curve[0][0])},${ys(curve[0][1])}`;
  for (let i = 1; i < curve.length; i++) d += ` H${xs(curve[i][0]).toFixed(1)} V${ys(curve[i][1]).toFixed(1)}`;
  return d;
}

const NAMES: Record<string, string> = { agent_lab: "Agent lab", bayes_opt: "Bayesian opt.", random: "Random search" };
const short = (n: string, label: string) => NAMES[n] ?? (n.includes("no_feedback") || n.includes("ablation") ? "Ablation" : label);

export function SpeedupRace({ speedup }: { speedup: Speedup }) {
  const reduce = useReducedMotion();
  const [p, setP] = useState(reduce ? 1 : 0);
  const [view, setView] = useState<"chart" | "table">("chart");
  const [hover, setHover] = useState<number | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const budget = speedup.budget;
  const xs = (v: number) => ML + (PW * v) / budget;
  const ys = (v: number) => MT + PH * (1 - v);
  const order = speedup.method_order;
  const colors = methodColors(order);

  const race = () => {
    if (reduce) return setP(1);
    setP(0);
    animate(0, 1, { duration: 4.2, ease: [0.4, 0, 0.2, 1], onUpdate: setP });
  };

  useEffect(() => { // start the race the first time the chart scrolls into view
    if (reduce || !box.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { race(); io.disconnect(); } }, { threshold: 0.4 });
    io.observe(box.current);
    return () => io.disconnect();
  }, [reduce]);

  const xNow = p * budget;
  const ends = order.map((n) => ({ n, y: ys(shareAt(speedup.curves[n], budget)) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 32);
  const comparisons = [...speedup.speedups].sort((a, b) => (a.baseline === "bayes_opt" ? -1 : b.baseline === "bayes_opt" ? 1 : 0));

  const onMove = (ev: MouseEvent) => {
    const r = svg.current!.getBoundingClientRect();
    const x = ((ev.clientX - r.left) / r.width) * W;
    setHover(x >= ML && x <= ML + PW ? Math.round(((x - ML) / PW) * budget) : null);
  };

  return (
    <div ref={box}>
      <div className="race-head">
        {comparisons.map((s) => (
          <div key={s.baseline} className={`claim${s.supported ? "" : " none"}`}>
            <div className="x mono">{s.supported ? <>≥ {s.ci95[0].toFixed(1)}<small>×</small></> : <small>no speed-up claimed</small>}</div>
            <div className="vs">fewer simulations than <b>{speedup.methods[s.baseline]?.label ?? s.baseline}</b></div>
            <div className="ci">point {s.point.toFixed(1)}× · 95% CI {s.ci95[0].toFixed(1)}–{s.ci95[1].toFixed(1)}×{s.baseline_censored ? " · baseline capped at budget" : ""}</div>
          </div>
        ))}
      </div>
      <div className="panel-head" style={{ paddingTop: 10 }}>
        <span className="hint">Share of runs that reached the target vs simulations used · {speedup.methods[speedup.focus].runs} runs per method · failed runs stay below 100%</span>
        <span className="spacer" />
        <button className="icon-btn" onClick={race} title="Replay the race" aria-label="Replay the race"><Play size={15} /></button>
        <div className="seg" role="group" aria-label="View">
          <button aria-pressed={view === "chart"} onClick={() => setView("chart")}>Chart</button>
          <button aria-pressed={view === "table"} onClick={() => setView("table")}>Table</button>
        </div>
      </div>
      {view === "table" ? (
        <table className="data">
          <thead><tr><th>Method</th><th>Reached target</th><th>Median simulations</th><th>Best P_net (median / max)</th></tr></thead>
          <tbody>
            {order.map((n) => { const m = speedup.methods[n]; return (
              <tr key={n}><td><i style={{ display: "inline-block", width: 10, height: 10, borderRadius: 3, background: colors[n], marginRight: 8 }} />{m.label}</td>
                <td className="num">{m.reached}/{m.runs}</td>
                <td className="num">{m.median_censored ? `> ${budget}` : m.median_evals}</td>
                <td className="num">{m.best_w_m2_median.toFixed(1)} / {m.best_w_m2_max.toFixed(1)} W/m²</td></tr>); })}
          </tbody>
        </table>
      ) : (
        <div className="chart-wrap">
          <div className="legend" style={{ padding: "0 4px 4px" }}>
            {order.map((n) => <span key={n}><i style={{ borderColor: colors[n] }} />{speedup.methods[n].label}</span>)}
          </div>
          <svg ref={svg} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" onMouseMove={onMove} onMouseLeave={() => setHover(null)}
               aria-label="Share of runs reaching the target as simulations are used, per method">
            <defs><clipPath id="race-clip"><rect x={0} y={0} width={xs(xNow) + 3} height={H} /></clipPath></defs>
            {[0, 0.25, 0.5, 0.75, 1].map((v) => (
              <g key={v}>
                <line x1={ML} x2={ML + PW} y1={ys(v)} y2={ys(v)} stroke={v === 0 ? "rgba(148,178,255,0.25)" : "rgba(148,178,255,0.07)"} strokeDasharray={v === 0.5 ? "4 4" : undefined} />
                <text x={ML - 8} y={ys(v) + 4} textAnchor="end" fontSize="11" fill="#6f7c97">{v * 100}%</text>
              </g>
            ))}
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <text key={f} x={xs(f * budget)} y={H - MB + 18} textAnchor="middle" fontSize="11" fill="#6f7c97">{Math.round(f * budget).toLocaleString()}</text>
            ))}
            <text x={ML + PW / 2} y={H - 4} textAnchor="middle" fontSize="11.5" fill="#a4b1cc">Simulations used</text>
            <g clipPath="url(#race-clip)">
              {[...order].reverse().map((n) => (
                <g key={n}>
                  <path d={stepPath(speedup.curves[n], xs, ys)} fill="none" stroke="#0b0a08" strokeWidth={6} />
                  <path d={stepPath(speedup.curves[n], xs, ys)} fill="none" stroke={colors[n]} strokeWidth={n === speedup.focus ? 3 : 2}
                        strokeLinejoin="round" style={n === speedup.focus ? { filter: `drop-shadow(0 0 6px ${colors[n]})` } : undefined} />
                </g>
              ))}
            </g>
            {order.map((n) => {
              const m = speedup.methods[n];
              if (m.median_censored || m.median_evals === null || m.median_evals > xNow) return null;
              return <circle key={n} cx={xs(m.median_evals)} cy={ys(0.5)} r={5} fill={colors[n]} stroke="#0b0a08" strokeWidth={2} />;
            })}
            {p < 1 && <line x1={xs(xNow)} x2={xs(xNow)} y1={MT} y2={MT + PH} stroke="rgba(255,255,255,0.25)" />}
            {p >= 1 && ends.map(({ n, y }) => {
              const m = speedup.methods[n];
              return (
                <g key={n}>
                  <line x1={ML + PW + 8} x2={ML + PW + 20} y1={y} y2={y} stroke={colors[n]} strokeWidth={3} strokeLinecap="round" />
                  <text x={ML + PW + 26} y={y + 4} fontSize="12.5" fontWeight={600} fill="#e8eefc">{short(n, m.label)}</text>
                  <text x={ML + PW + 26} y={y + 19} fontSize="11.5" fill="#a4b1cc">{m.reached}/{m.runs} reached · median {m.median_censored ? `> ${budget}` : m.median_evals}</text>
                </g>
              );
            })}
            {hover !== null && <line x1={xs(hover)} x2={xs(hover)} y1={MT} y2={MT + PH} stroke="rgba(232,238,252,0.35)" pointerEvents="none" />}
          </svg>
          {hover !== null && (
            <div className="tooltip" style={{ left: `calc(${(xs(hover) / W) * 100}% + 14px)`, top: 30 }}>
              <div className="mono">{hover.toLocaleString()} simulations</div>
              {order.map((n) => (
                <div key={n} className="row"><i style={{ width: 10, height: 2, background: colors[n] }} />{speedup.methods[n].label}
                  <b>{Math.round(shareAt(speedup.curves[n], hover) * 100)}%</b></div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
