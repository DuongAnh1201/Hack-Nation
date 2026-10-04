import { useRef, useState, type MouseEvent } from "react";

export interface Band { from: number; to: number; color: string; label: string }
export interface Series { key: string; label: string; color: string; x: number[]; y: number[]; dash?: string }

/** Small multi-series line chart with a crosshair tooltip; optional log x axis. */
export function LineChart({ series, xLabel, yLabel, logX = false, height = 260, yFmt = (v) => v.toFixed(2), bands = [], drawKey }: {
  series: Series[]; xLabel: string; yLabel: string; logX?: boolean; height?: number; yFmt?: (v: number) => string;
  bands?: Band[]; drawKey?: string;
}) {
  const W = 620, H = height, ML = 52, MR = 14, MT = 12, MB = 38;
  const PW = W - ML - MR, PH = H - MT - MB;
  const [hx, setHx] = useState<number | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const xs = series.flatMap((s) => s.x), ys = series.flatMap((s) => s.y);
  if (!xs.length) return null;
  const tx = (v: number) => (logX ? Math.log(v) : v);
  const x0 = tx(Math.min(...xs)), x1 = tx(Math.max(...xs));
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const pad = (y1 - y0) * 0.06; y0 -= pad; y1 += pad;
  const sx = (v: number) => ML + (PW * (tx(v) - x0)) / (x1 - x0 || 1);
  const sy = (v: number) => MT + PH * (1 - (v - y0) / (y1 - y0));
  const ticksY = Array.from({ length: 5 }, (_, i) => y0 + ((y1 - y0) * i) / 4);
  const ticksX = logX ? [0.3, 0.5, 1, 2, 5, 10, 20].filter((t) => tx(t) >= x0 && tx(t) <= x1)
    : Array.from({ length: 5 }, (_, i) => Math.round(Math.min(...xs) + ((Math.max(...xs) - Math.min(...xs)) * i) / 4));
  const nearest = (s: Series, x: number) => s.x.reduce((b, v, i) => (Math.abs(tx(v) - tx(x)) < Math.abs(tx(s.x[b]) - tx(x)) ? i : b), 0);

  const onMove = (e: MouseEvent) => {
    const r = svg.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    if (px < ML || px > ML + PW) return setHx(null);
    const t = x0 + ((px - ML) / PW) * (x1 - x0);
    setHx(logX ? Math.exp(t) : t);
  };

  return (
    <div className="chart-wrap">
      <div className="legend" style={{ padding: "0 4px 6px" }}>
        {series.map((s) => <span key={s.key}><i style={{ borderColor: s.color, borderTopStyle: s.dash ? "dashed" : "solid" }} />{s.label}</span>)}
      </div>
      <svg ref={svg} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} vs ${xLabel}`}
           onMouseMove={onMove} onMouseLeave={() => setHx(null)}>
        {bands.map((b) => (
          <g key={b.label} className="band">
            <rect x={sx(b.from)} y={MT} width={sx(b.to) - sx(b.from)} height={PH} fill={b.color} />
            <text x={sx(b.from) + 5} y={MT + 13} fontSize="10.5" fill="#b8b0a2">{b.label}</text>
          </g>
        ))}
        {ticksY.map((v, i) => (
          <g key={i}>
            <line x1={ML} x2={ML + PW} y1={sy(v)} y2={sy(v)} stroke={i === 0 ? "rgba(241,235,224,0.28)" : "rgba(241,235,224,0.06)"} />
            <text x={ML - 8} y={sy(v) + 4} textAnchor="end" fontSize="11" fill="#7c7568">{yFmt(v)}</text>
          </g>
        ))}
        {ticksX.map((t, i) => <text key={i} x={sx(t)} y={H - MB + 16} textAnchor="middle" fontSize="11" fill="#7c7568">{t}</text>)}
        <text x={ML + PW / 2} y={H - 4} textAnchor="middle" fontSize="11.5" fill="#b8b0a2">{xLabel}</text>
        <text transform={`translate(12 ${MT + PH / 2}) rotate(-90)`} textAnchor="middle" fontSize="11.5" fill="#b8b0a2">{yLabel}</text>
        {series.map((s) => (
          <path key={`${s.key}-${drawKey ?? ""}`} className={s.dash ? undefined : "draw"} pathLength={s.dash ? undefined : 1}
                fill="none" stroke={s.color} strokeWidth={s.dash ? 1.2 : 1.8} strokeDasharray={s.dash} strokeLinejoin="round"
                d={s.x.map((x, i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(s.y[i]).toFixed(1)}`).join("")} />
        ))}
        {hx !== null && <line x1={sx(hx)} x2={sx(hx)} y1={MT} y2={MT + PH} stroke="rgba(241,235,224,0.4)" strokeDasharray="2 3" pointerEvents="none" />}
      </svg>
      {hx !== null && (
        <div className="tooltip" style={{ left: `calc(${(sx(hx) / W) * 100}% + 14px)`, top: 30 }}>
          <div className="mono">{xLabel.split(" (")[0]}: {logX ? hx.toFixed(2) : Math.round(hx)}</div>
          {series.map((s) => { const i = nearest(s, hx); return (
            <div key={s.key} className="row"><i style={{ width: 10, height: 2, background: s.color }} />{s.label}<b>{yFmt(s.y[i])}</b></div>); })}
        </div>
      )}
    </div>
  );
}
