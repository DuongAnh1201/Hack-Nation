// Small drawings that repeat the physics across the site, so every page carries the same idea:
// the sun lives at short wavelengths, the roof's heat at long ones, and the sky lets 8-13 um through.

import { formula, materialInfo } from "../lib/materials";

const HC_K = 14388; // hc/k in um*K
const planck = (um: number, T: number) => um ** -5 / (Math.exp(HC_K / (um * T)) - 1);

/** A log-wavelength ruler with the sun's and the roof's blackbody curves and the sky window. */
export function SpectrumRule({ height = 64 }: { height?: number }) {
  const W = 1000, H = height, L0 = Math.log(0.3), L1 = Math.log(25);
  const x = (um: number) => ((Math.log(um) - L0) / (L1 - L0)) * W;
  const grid = Array.from({ length: 160 }, (_, i) => Math.exp(L0 + ((L1 - L0) * i) / 159));
  const curve = (T: number) => {
    const v = grid.map((l) => planck(l, T)), m = Math.max(...v);
    return `M0,${H} ` + grid.map((l, i) => `L${x(l).toFixed(1)},${(H - 6 - (H - 18) * (v[i] / m)).toFixed(1)}`).join(" ") + ` L${W},${H} Z`;
  };
  const pc = (um: number) => `${(x(um) / W) * 100}%`;
  return (
    <div className="spectrum-rule" aria-hidden>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ height }}>
        <rect x={x(8)} y={0} width={x(13) - x(8)} height={H} className="win" />
        <path d={curve(5778)} className="sun" />
        <path d={curve(300)} className="heat" />
        <line x1={0} x2={W} y1={H - 0.5} y2={H - 0.5} className="axis" />
      </svg>
      {[0.3, 0.5, 1, 2, 5, 10, 20].map((t) => <span key={t} className="tick" style={{ left: pc(t) }}>{t} µm</span>)}
      <span className="lbl sun-t" style={{ left: pc(0.55) }}>sunlight</span>
      <span className="lbl win-t" style={{ left: pc(10.2) }}>sky window</span>
      <span className="lbl heat-t" style={{ left: pc(15.5), top: 18 }}>roof heat</span>
    </div>
  );
}

/** A coating drawn as a core sample: sky side on the left, mirror on the right, widths in true nm. */
export function LayerStrip({ materials, thicknesses, substrate }: { materials: string[]; thicknesses: number[]; substrate: string }) {
  const total = thicknesses.reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="layer-strip">
      <div className="ls-bar">
        {materials.map((m, i) => (
          <span key={i} style={{ flexGrow: thicknesses[i] / total, background: materialInfo(m).color }} title={`${m} ${thicknesses[i]} nm`}>
            <em>{formula(m)}</em><b className="mono">{Math.round(thicknesses[i])}</b>
          </span>
        ))}
        <i className="ls-mirror">{substrate}</i>
      </div>
      <div className="ls-cap"><span>sky ↑</span><span className="mono">{Math.round(total)} nm total</span><span>mirror</span></div>
    </div>
  );
}

/** The balance every page is about, typeset with live numbers when we have them. */
export function Equation({ rad, atm, sun, net }: { rad?: number; atm?: number; sun?: number; net?: number }) {
  const f = (v?: number) => (v === undefined ? "" : v.toFixed(1));
  return (
    <div className="equation" role="math" aria-label="P net equals P rad minus P atm minus P sun">
      <span><i>P</i><sub>net</sub><small className="mono">{f(net)}</small></span><b>=</b>
      <span><i>P</i><sub>rad</sub><small className="mono">{f(rad)}</small></span><b>−</b>
      <span><i>P</i><sub>atm</sub><small className="mono">{f(atm)}</small></span><b>−</b>
      <span><i>P</i><sub>sun</sub><small className="mono">{f(sun)}</small></span>
    </div>
  );
}
