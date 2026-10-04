import { ArrowDown, ArrowUp, Download, Link2, Pin, Plus, Save, Trash2, X } from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Notice, PageHead } from "../components/Layout";
import { SpectrumChart } from "../components/SpectrumChart";
import { api, downloadFile, toSpectra, type Design, type SimResult } from "../lib/api";
import { decodeDesign, encodeDesign, FILM_MATERIALS, loadSaved, MAX_LAYERS, PRESETS, REFERENCE_MATERIALS, storeSaved, SUBSTRATES, T_MAX, T_MIN, type Saved } from "../lib/designs";
import { formula, materialInfo } from "../lib/materials";

const CoatingScene = lazy(() => import("../scenes/CoatingScene").then((m) => ({ default: m.CoatingScene })));
const PIN_COLORS = ["#ffb547", "#c4b5fd", "#86efac"];

interface Pinned { id: string; label: string; r: SimResult }

export function DesignerPage() {
  const [params, setParams] = useSearchParams();
  const [design, setDesign] = useState<Design>(() => decodeDesign(params.get("d")) ?? PRESETS[0].design);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pins, setPins] = useState<Pinned[]>([]);
  const [saved, setSaved] = useState<Saved[]>(loadSaved);
  const [target, setTarget] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const seq = useRef(0);

  useEffect(() => { api.benchmark().then((b) => setTarget(b.target_w_m2)).catch(() => setTarget(null)); }, []);

  useEffect(() => { // live simulation, debounced; the newest request wins
    const id = ++seq.current;
    setBusy(true);
    const t = window.setTimeout(() => {
      api.simulate(design)
        .then((r) => { if (id === seq.current) { setResult(r); setError(null); } })
        .catch((e: Error) => { if (id === seq.current) setError(e.message); })
        .finally(() => { if (id === seq.current) setBusy(false); });
    }, 220);
    setParams({ d: encodeDesign(design) }, { replace: true });
    return () => window.clearTimeout(t);
  }, [design, setParams]);

  const setLayer = (i: number, patch: Partial<{ material: string; t: number }>) => setDesign((d) => {
    const materials = [...d.materials], thicknesses_nm = [...d.thicknesses_nm];
    if (patch.material) materials[i] = patch.material;
    if (patch.t !== undefined) thicknesses_nm[i] = Math.max(T_MIN, Math.min(T_MAX, patch.t));
    return { ...d, materials, thicknesses_nm };
  });
  const move = (i: number, dir: -1 | 1) => setDesign((d) => {
    const j = i + dir;
    if (j < 0 || j >= d.materials.length) return d;
    const m = [...d.materials], t = [...d.thicknesses_nm];
    [m[i], m[j]] = [m[j], m[i]]; [t[i], t[j]] = [t[j], t[i]];
    return { ...d, materials: m, thicknesses_nm: t };
  });
  const remove = (i: number) => setDesign((d) => d.materials.length <= 1 ? d :
    ({ ...d, materials: d.materials.filter((_, k) => k !== i), thicknesses_nm: d.thicknesses_nm.filter((_, k) => k !== i) }));
  const add = () => setDesign((d) => ({ ...d, materials: [...d.materials, "SiO2"], thicknesses_nm: [...d.thicknesses_nm, 200] }));

  const label = (d: Design) => `${d.materials.length} layers ${[...new Set(d.materials)].map(formula).join("/")} on ${d.substrate}`;
  const pin = () => {
    if (!result || pins.length >= 3) return;
    setPins((p) => [...p, { id: `pin${Date.now()}`, label: `${label(result.design)} · ${result.p_net_w_m2.toFixed(1)} W/m²`, r: result }]);
  };
  const save = () => {
    if (!result) return;
    const name = window.prompt("Name this design", label(result.design));
    if (!name) return;
    const next = [{ name, design: result.design, p_net_w_m2: result.p_net_w_m2, saved: Date.now() }, ...saved].slice(0, 30);
    setSaved(next); storeSaved(next);
  };
  const share = async () => {
    try { await navigator.clipboard.writeText(window.location.href); setCopied(true); window.setTimeout(() => setCopied(false), 1500); }
    catch { window.prompt("Copy this link", window.location.href); }
  };
  const exportCsv = () => {
    if (!result) return;
    const s = result.spectrum;
    const head = `# ${label(result.design)}\n# materials (sky->mirror): ${result.design.materials.join(" ")}\n# thicknesses_nm: ${result.design.thicknesses_nm.join(" ")}\n` +
      `# p_net_w_m2=${result.p_net_w_m2} solar_reflectance=${result.solar_reflectance} window_emissivity=${result.window_emissivity}\n# conditions: ${JSON.stringify(result.conditions)}\n`;
    const rows = s.wavelength_um.map((l, i) => `${l},${s.emissivity[i]},${s.sky_transmittance[i]}`).join("\n");
    downloadFile("design_spectrum.csv", `${head}wavelength_um,emissivity,sky_transmittance\n${rows}\n`, "text/csv");
  };

  const spectra = useMemo(() => result ? toSpectra([{ id: "cur", label: `This design · ${result.p_net_w_m2.toFixed(1)} W/m²`, r: result }, ...pins]) : undefined, [result, pins]);
  const usesReference = design.materials.some((m) => (REFERENCE_MATERIALS as readonly string[]).includes(m));
  const maxLayers = usesReference ? 7 : MAX_LAYERS;
  const r = result;
  const meets = r && target !== null ? r.p_net_w_m2 >= target : null;

  return (
    <>
      <PageHead kicker="§ 01 · Designer" title="Coating designer" sub="Build a stack of thin films on a mirror. Every change is simulated with the lab's transfer-matrix bench."
        right={<>
          <select className="input" aria-label="Load a preset" value="" onChange={(e) => { const p = PRESETS.find((x) => x.id === e.target.value); if (p) setDesign(p.design); }}>
            <option value="">Load preset…</option>
            {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </>} />

      <div className="grid designer">
        <section className="panel">
          <div className="panel-head"><h2>Stack</h2><span className="hint">top layer faces the sky · {design.materials.length}/{maxLayers} layers</span></div>
          <div className="stack-editor">
            {design.materials.map((m, i) => (
              <div className="layer-row" key={i}>
                <span className="sw" style={{ background: materialInfo(m).color }} />
                <span className="pos mono">{i === 0 ? "sky" : i === design.materials.length - 1 ? "mirror" : i + 1}</span>
                <select className="input" value={m} aria-label={`Layer ${i + 1} material`} onChange={(e) => setLayer(i, { material: e.target.value })}>
                  {FILM_MATERIALS.map((x) => <option key={x} value={x}>{formula(x)}</option>)}
                  {REFERENCE_MATERIALS.map((x) => <option key={x} value={x}>{formula(x)} (reference only)</option>)}
                </select>
                <input type="range" min={T_MIN} max={T_MAX} step={1} value={design.thicknesses_nm[i]} aria-label={`Layer ${i + 1} thickness`}
                       onChange={(e) => setLayer(i, { t: Number(e.target.value) })} />
                <input className="input num" type="number" min={T_MIN} max={T_MAX} value={Math.round(design.thicknesses_nm[i])}
                       aria-label={`Layer ${i + 1} thickness in nm`} onChange={(e) => setLayer(i, { t: Number(e.target.value) })} />
                <span className="unit">nm</span>
                <button className="icon-btn sm" onClick={() => move(i, -1)} aria-label="Move up" disabled={i === 0}><ArrowUp size={14} /></button>
                <button className="icon-btn sm" onClick={() => move(i, 1)} aria-label="Move down" disabled={i === design.materials.length - 1}><ArrowDown size={14} /></button>
                <button className="icon-btn sm" onClick={() => remove(i)} aria-label="Remove layer" disabled={design.materials.length <= 1}><Trash2 size={14} /></button>
              </div>
            ))}
            <div className="row-actions">
              <button className="btn" onClick={add} disabled={design.materials.length >= maxLayers}><Plus size={14} /> Add layer</button>
              <label className="inline">Mirror
                <select className="input" value={design.substrate} onChange={(e) => setDesign((d) => ({ ...d, substrate: e.target.value }))}>
                  {SUBSTRATES.map((s) => <option key={s} value={s}>{s === "Ag" ? "Silver (Ag)" : "Aluminium (Al)"}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="stage small">
            <Suspense fallback={<div className="scene-loading">Loading 3D view…</div>}>
              <CoatingScene stack={{ materials: design.materials, thicknessesNm: design.thicknesses_nm, substrate: design.substrate }}
                            compare={false} mood="neutral" animate
                            photons={r ? { reflectance: r.solar_reflectance, emissivity: r.window_emissivity } : undefined} />
            </Suspense>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head"><h2>Result</h2><span className="hint">{busy ? "simulating…" : r ? `${r.conditions.t_ambient_k} K · AM1.5 · ${r.conditions.sky}` : ""}</span></div>
          {error && <Notice kind="error">{error}</Notice>}
          {r && (
            <div className="result">
              <div className="big-metric">
                <div className="mono" style={{ color: meets === null ? "var(--text)" : meets ? "var(--supported)" : "var(--heat)" }}>{r.p_net_w_m2.toFixed(2)}<small> W/m²</small></div>
                <div className="sub">net cooling power at ambient temperature{target !== null && <> · {meets ? "✓ meets" : "✗ below"} the {target} W/m² benchmark target</>}</div>
              </div>
              <Breakdown r={r} />
              <div className="metrics">
                <div className="metric">Sunlight reflected<b className="mono" style={{ color: "var(--sun)" }}>{(r.solar_reflectance * 100).toFixed(2)}%</b></div>
                <div className="metric">Mean emissivity 8–13 µm<b className="mono" style={{ color: "var(--ice)" }}>{r.window_emissivity.toFixed(3)}</b></div>
                <div className="metric">Search space<b className="mono" style={{ color: r.in_search_space ? "var(--supported)" : "var(--sun)" }}>{r.in_search_space ? "inside" : "outside"}</b></div>
              </div>
              {!r.in_search_space && <Notice kind="warn">Outside the benchmark search space: {r.search_space_note}. Fine for reference, not comparable with benchmark results.</Notice>}
              <div className="row-actions">
                <button className="btn" onClick={pin} disabled={pins.length >= 3}><Pin size={14} /> Pin to compare</button>
                <button className="btn" onClick={save}><Save size={14} /> Save</button>
                <button className="btn" onClick={share}><Link2 size={14} /> {copied ? "Link copied" : "Share link"}</button>
                <button className="btn" onClick={() => downloadFile("design.json", JSON.stringify(r, null, 2))}><Download size={14} /> JSON</button>
                <button className="btn" onClick={exportCsv}><Download size={14} /> CSV</button>
              </div>
            </div>
          )}
          {spectra && <div className="spectrum-cap"><SpectrumChart spectra={spectra} currentId="cur" extras={pins.map((p, i) => ({ id: p.id, color: PIN_COLORS[i] }))} /></div>}
        </section>
      </div>

      {pins.length > 0 && (
        <section className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-head"><h2>Comparison</h2><span className="hint">pinned designs, simulated under identical conditions</span></div>
          <table className="data">
            <thead><tr><th></th><th>Design</th><th>P_net (W/m²)</th><th>P_rad</th><th>P_atm</th><th>P_sun</th><th>Reflectance</th><th>Window ε</th><th></th></tr></thead>
            <tbody>
              {[{ id: "cur", label: "This design", r: r! }, ...pins].filter((p) => p.r).map((p, i) => (
                <tr key={p.id}>
                  <td><i className="dot" style={{ background: i === 0 ? "#5ad1ff" : PIN_COLORS[i - 1] }} /></td>
                  <td>{p.label}<div className="metric mono">{p.r.design.materials.map((m, k) => `${formula(m)} ${Math.round(p.r.design.thicknesses_nm[k])}`).join(" · ")}</div></td>
                  <td className="num">{p.r.p_net_w_m2.toFixed(2)}</td><td className="num">{p.r.p_rad_w_m2.toFixed(1)}</td>
                  <td className="num">{p.r.p_atm_w_m2.toFixed(1)}</td><td className="num">{p.r.p_sun_w_m2.toFixed(1)}</td>
                  <td className="num">{(p.r.solar_reflectance * 100).toFixed(2)}%</td><td className="num">{p.r.window_emissivity.toFixed(3)}</td>
                  <td>{i > 0 && <>
                    <button className="icon-btn sm" aria-label="Load into the editor" onClick={() => setDesign(p.r.design)}>↺</button>
                    <button className="icon-btn sm" aria-label="Unpin" onClick={() => setPins((x) => x.filter((y) => y.id !== p.id))}><X size={14} /></button></>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {saved.length > 0 && (
        <section className="panel">
          <div className="panel-head"><h2>My designs</h2><span className="hint">saved in this browser</span></div>
          <table className="data">
            <thead><tr><th>Name</th><th>Stack</th><th>P_net (W/m²)</th><th>Saved</th><th></th></tr></thead>
            <tbody>
              {saved.map((s, i) => (
                <tr key={s.saved}>
                  <td>{s.name}</td>
                  <td className="mono">{s.design.materials.map((m, k) => `${formula(m)} ${Math.round(s.design.thicknesses_nm[k])}`).join(" · ")} · {s.design.substrate}</td>
                  <td className="num">{s.p_net_w_m2.toFixed(2)}</td>
                  <td>{new Date(s.saved).toLocaleString()}</td>
                  <td><button className="btn sm" onClick={() => setDesign(s.design)}>Open</button>
                    <button className="icon-btn sm" aria-label="Delete" onClick={() => { const n = saved.filter((_, k) => k !== i); setSaved(n); storeSaved(n); }}><Trash2 size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}

function Breakdown({ r }: { r: SimResult }) {
  const max = Math.max(r.p_rad_w_m2, 1);
  const rows = [
    { k: "Radiated out", v: r.p_rad_w_m2, sign: "+", c: "var(--ice)" },
    { k: "Absorbed from the sky", v: r.p_atm_w_m2, sign: "−", c: "var(--testing)" },
    { k: "Absorbed sunlight", v: r.p_sun_w_m2, sign: "−", c: "var(--sun)" },
  ];
  return (
    <div className="breakdown" aria-label="Power balance">
      {rows.map((x) => (
        <div key={x.k} className="b-row">
          <span className="b-k">{x.sign} {x.k}</span>
          <span className="b-bar"><i style={{ width: `${(x.v / max) * 100}%`, background: x.c }} /></span>
          <span className="b-v mono">{x.v.toFixed(1)}</span>
        </div>
      ))}
      <div className="b-row total"><span className="b-k">= Net cooling</span><span className="b-bar" /><span className="b-v mono">{r.p_net_w_m2.toFixed(1)}</span></div>
    </div>
  );
}
