import { useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import type { Spectra } from "../lib/data";

const W = 580, H = 300, ML = 44, MR = 14, MT = 34, MB = 38;
const PW = W - ML - MR, PH = H - MT - MB;
const L0 = Math.log(0.3), L1 = Math.log(25);
const xs = (l: number) => ML + (PW * (Math.log(l) - L0)) / (L1 - L0);
const ys = (e: number) => MT + PH * (1 - e);
const TICKS = [0.3, 0.5, 1, 2, 5, 10, 20];

function path(lam: number[], v: number[]): string {
  return v.map((e, i) => `${i ? "L" : "M"}${xs(lam[i]).toFixed(1)},${ys(e).toFixed(1)}`).join("");
}

/** Smoothly morphs one series into the next when the design changes. */
function useMorph(target: number[] | undefined, ms = 750): number[] | undefined {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(target);
  const prev = useRef(target);
  useEffect(() => {
    if (!target) { setShown(undefined); prev.current = undefined; return; }
    const from = prev.current;
    if (reduce || !from || from.length !== target.length) { setShown(target); prev.current = target; return; }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / ms);
      const e = 1 - Math.pow(1 - k, 3);
      setShown(target.map((v, i) => from[i] + (v - from[i]) * e));
      if (k < 1) raf = requestAnimationFrame(tick); else prev.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); prev.current = target; };
  }, [target, ms, reduce]);
  return shown;
}

export function SpectrumChart({ spectra, currentId, referenceId, extras = [] }: {
  spectra: Spectra; currentId?: string; referenceId?: string;
  extras?: { id: string; color: string }[];   // pinned designs drawn as thin comparison lines
}) {
  const lam = spectra.wavelength_um;
  const cur = currentId ? spectra.designs[currentId] : undefined;
  const ref = referenceId && referenceId !== currentId ? spectra.designs[referenceId] : undefined;
  const curShown = useMorph(cur?.emissivity);
  const [hover, setHover] = useState<number | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const [sLo, sHi] = spectra.bands.solar, [wLo, wHi] = spectra.bands.window;
  const sky = spectra.sky_transmittance;

  const series = useMemo(() => [
    { key: "ideal", label: "Ideal cooler", color: "rgba(232,238,252,0.35)", dash: "2 4", v: spectra.ideal },
    ...(ref ? [{ key: "ref", label: ref.label, color: "#c6d0e5", dash: "6 5", v: ref.emissivity }] : []),
    ...extras.filter((x) => spectra.designs[x.id]).map((x) => ({
      key: `x-${x.id}`, label: spectra.designs[x.id].label, color: x.color, dash: "4 3", v: spectra.designs[x.id].emissivity })),
    ...(cur && curShown ? [{ key: "cur", label: cur.label, color: "#5ad1ff", dash: undefined, v: curShown }] : []),
  ], [spectra.ideal, spectra.designs, ref, cur, curShown, extras]);

  const onMove = (ev: MouseEvent) => {
    const r = svg.current!.getBoundingClientRect();
    const x = ((ev.clientX - r.left) / r.width) * W;
    if (x < ML || x > W - MR) return setHover(null);
    const l = Math.exp(L0 + ((x - ML) / PW) * (L1 - L0));
    let best = 0;
    lam.forEach((v, i) => { if (Math.abs(Math.log(v / l)) < Math.abs(Math.log(lam[best] / l))) best = i; });
    setHover(best);
  };

  const band = (l: number) => (l >= sLo && l <= sHi ? "sunlight band: should reflect" : l >= wLo && l <= wHi ? "sky window: should emit" : "outside the key bands");

  return (
    <div className="chart-wrap">
      <div className="legend" style={{ padding: "0 4px 6px" }}>
        {series.map((s) => (
          <span key={s.key}><i style={{ borderColor: s.color, borderTopStyle: s.dash ? "dashed" : "solid" }} />{s.label}</span>
        ))}
        {sky && <span title={spectra.sky_model}><i style={{ borderColor: "rgba(90,209,255,0.6)", borderTopWidth: 6, opacity: 0.5 }} />Sky transparency</span>}
      </div>
      {!cur && <div className="legend" style={{ padding: "0 4px 6px", color: "var(--muted)" }}>No spectrum for {currentId ?? "this step"} yet.</div>}
      <svg ref={svg} className="chart" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label="Emissivity vs wavelength for the current design, the Stanford design and an ideal cooler"
           onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect x={xs(sLo)} y={MT} width={xs(sHi) - xs(sLo)} height={PH} fill="rgba(255,181,71,0.14)" />
        <rect x={xs(wLo)} y={MT} width={xs(wHi) - xs(wLo)} height={PH} fill="rgba(90,209,255,0.06)" />
        {sky && <path d={`${path(lam, sky)}L${xs(lam[lam.length - 1])},${ys(0)}L${xs(lam[0])},${ys(0)}Z`} fill="rgba(90,209,255,0.10)" stroke="rgba(90,209,255,0.35)" strokeWidth={1} />}
        <text x={(xs(sLo) + xs(sHi)) / 2} y={MT - 18} textAnchor="middle" fontSize="11.5" fill="#ffb547">☀ Sunlight · reflect it</text>
        <text x={(xs(sLo) + xs(sHi)) / 2} y={MT - 5} textAnchor="middle" fontSize="10.5" fill="#6f7c97">0.3–2.5 µm</text>
        <text x={(xs(wLo) + xs(wHi)) / 2} y={MT - 18} textAnchor="middle" fontSize="11.5" fill="#5ad1ff">✦ Sky window · emit</text>
        <text x={(xs(wLo) + xs(wHi)) / 2} y={MT - 5} textAnchor="middle" fontSize="10.5" fill="#6f7c97">8–13 µm → space</text>
        {[0, 0.25, 0.5, 0.75, 1].map((e) => (
          <g key={e}>
            <line x1={ML} x2={W - MR} y1={ys(e)} y2={ys(e)} stroke={e === 0 ? "rgba(148,178,255,0.25)" : "rgba(148,178,255,0.07)"} />
            <text x={ML - 8} y={ys(e) + 4} textAnchor="end" fontSize="11" fill="#6f7c97">{e}</text>
          </g>
        ))}
        {TICKS.map((t) => (
          <text key={t} x={xs(t)} y={H - MB + 16} textAnchor="middle" fontSize="11" fill="#6f7c97">{t}</text>
        ))}
        <text x={ML + PW / 2} y={H - 4} textAnchor="middle" fontSize="11.5" fill="#a4b1cc">Wavelength (µm, log scale)</text>
        <text transform={`translate(12 ${MT + PH / 2}) rotate(-90)`} textAnchor="middle" fontSize="11.5" fill="#a4b1cc">Emissivity</text>
        {series.map((s) => (
          <path key={s.key} d={path(lam, s.v)} fill="none" stroke={s.color} strokeWidth={s.key === "cur" ? 2.4 : 1.6}
                strokeDasharray={s.dash} strokeLinejoin="round" filter={s.key === "cur" ? "url(#glow)" : undefined} />
        ))}
        {hover !== null && (
          <g pointerEvents="none">
            <line x1={xs(lam[hover])} x2={xs(lam[hover])} y1={MT} y2={MT + PH} stroke="rgba(232,238,252,0.35)" />
            {series.map((s) => <circle key={s.key} cx={xs(lam[hover])} cy={ys(s.v[hover])} r={4} fill={s.color} stroke="#0b0a08" strokeWidth={2} />)}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: `calc(${(xs(lam[hover]) / W) * 100}% + 14px)`, top: 40 }}>
          <div className="mono">{lam[hover].toFixed(2)} µm · {band(lam[hover])}</div>
          {series.map((s) => (
            <div key={s.key} className="row"><i style={{ width: 10, height: 2, background: s.color }} />{s.label}<b>{s.v[hover].toFixed(2)}</b></div>
          ))}
          {sky && lam[hover] >= 2.5 && <div className="row"><i style={{ width: 10, height: 6, background: "rgba(90,209,255,0.4)" }} />Sky transparency<b>{sky[hover].toFixed(2)}</b></div>}
        </div>
      )}
    </div>
  );
}
