import { ArrowRight, Download, Play, Plus, Trash2 } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Equation, LayerStrip } from "../components/Decor";
import { Notice, PageHead } from "../components/Layout";
import { LineChart, type Band } from "../components/LineChart";
import { SpeedupRace } from "../components/SpeedupRace";
import { api, downloadFile, type Benchmark, type Material, type OptimizeResult, type RunSummary, type SimResult } from "../lib/api";
import type { LabData } from "../lib/data";
import { encodeDesign, FILM_MATERIALS, MAX_LAYERS, PRESETS, SUBSTRATES } from "../lib/designs";
import { formula, materialInfo } from "../lib/materials";
import type { RecordEntry } from "../lib/record";
import { RunView } from "./RunView";

const CoatingScene = lazy(() => import("../scenes/CoatingScene").then((m) => ({ default: m.CoatingScene })));

/** Load once, with loading and error states handled the same way everywhere. */
function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({ loading: true });
  useEffect(() => {
    let live = true;
    setState({ loading: true });
    fn().then((data) => live && setState({ data, loading: false })).catch((e: Error) => live && setState({ error: e.message, loading: false }));
    return () => { live = false; };
  }, deps);
  return state;
}

function Loading({ what }: { what: string }) { return <div className="loading-line"><span />Loading {what}</div>; }

const BANDS: Band[] = [
  { from: 0.3, to: 2.5, color: "rgba(242,173,69,0.07)", label: "sunlight" },
  { from: 8, to: 13, color: "rgba(143,216,242,0.09)", label: "sky window" },
];

// ------------------------------------------------------------------ overview
const ENTRIES = [
  { to: "/design", title: "Design a coating", text: "Stack up to five films on a mirror. Cooling power, spectrum and the 3D photon view update as you drag.", glyph: "stack" },
  { to: "/optimize", title: "Optimize thicknesses", text: "Fix the materials and their order; watch the optimizer climb, one simulation at a time.", glyph: "climb" },
  { to: "/runs", title: "Read the lab's notebook", text: "Hypotheses, experiments, refutations and approvals, with the evidence behind every verdict.", glyph: "notes" },
  { to: "/benchmark", title: "Check the benchmark", text: "How many simulations each search method needs to reach the target, with honest intervals.", glyph: "race" },
] as const;

function Glyph({ kind }: { kind: (typeof ENTRIES)[number]["glyph"] }) {
  const s = { fill: "none", stroke: "currentColor", strokeWidth: 1.2 } as const;
  return (
    <svg viewBox="0 0 64 48" className="glyph" aria-hidden>
      {kind === "stack" && <>{[0, 1, 2, 3].map((i) => <path key={i} {...s} d={`M10 ${34 - i * 7} l22 -6 l22 6 l-22 6 z`} opacity={0.4 + i * 0.2} />)}<path {...s} d="M32 4 v-4" /></>}
      {kind === "climb" && <><path {...s} d="M6 42 H58 M6 42 V6" opacity={0.4} /><path {...s} d="M8 38 L14 30 L20 31 L26 20 L34 18 L40 12 L50 11 L58 10" /><circle cx="58" cy="10" r="2" fill="currentColor" /></>}
      {kind === "notes" && <><rect {...s} x="12" y="4" width="40" height="40" rx="2" opacity={0.5} />{[14, 22, 30].map((y) => <path key={y} {...s} d={`M20 ${y} H44`} opacity={0.6} />)}<path {...s} d="M20 37 l4 4 l9 -9" /></>}
      {kind === "race" && <>{[10, 20, 30, 40].map((y, i) => <path key={y} {...s} d={`M6 ${y} H${18 + [34, 22, 40, 28][i]}`} strokeWidth={3} opacity={i === 2 ? 1 : 0.45} />)}<path {...s} d="M54 4 V44" strokeDasharray="2 3" /></>}
    </svg>
  );
}

export function OverviewPage() {
  const bench = useLoad(api.benchmark);
  const runs = useLoad(api.runs);
  const featured = useLoad(() => api.simulate(PRESETS[0].design));
  const b = bench.data, f = featured.data;
  const best = b ? Math.max(...Object.values(b.methods).map((m) => m.best_w_m2_max)) : undefined;
  return (
    <>
      <PageHead kicker="§ 00 · Overview" title="The lab at a glance"
        sub="A coating that reflects sunlight and radiates heat through the 8–13 µm sky window cools a surface below air temperature with no electricity. This site simulates such coatings, optimizes them, and shows what our AI lab found." />
      <section className="overview-hero">
        <div>
          <p className="dropcap">Everything here reduces to one balance. A roof radiates heat upward, the air radiates some back, the sun adds its share.
            What is left over is the cooling power. Our best cheap design leaves <b className="mono">{f ? f.p_net_w_m2.toFixed(1) : "…"} W/m²</b> on the table.</p>
          <Link className="text-link" to="/">Watch the story in 3D <ArrowRight size={14} /></Link>
        </div>
        <Equation rad={f?.p_rad_w_m2} atm={f?.p_atm_w_m2} sun={f?.p_sun_w_m2} net={f?.p_net_w_m2} />
      </section>
      <section className="ledger-row">
        <div><span className="k">Benchmark target</span><span className="v mono">{b ? b.target_w_m2 : "—"}<small>W/m²</small></span><span className="s">fixed before the search</span></div>
        <div><span className="k">Best in benchmark</span><span className="v mono">{best?.toFixed(1) ?? "—"}<small>W/m²</small></span><span className="s">across all methods and runs</span></div>
        <div><span className="k">Methods compared</span><span className="v mono">{b ? b.method_order.length : "—"}</span><span className="s">{b ? `${b.methods[b.focus].runs} runs × ${b.budget} sims` : ""}</span></div>
        <div><span className="k">Lab runs</span><span className="v mono">{runs.data?.length ?? "—"}</span><span className="s">{runs.data?.some((r) => r.fake) ? "includes demo data" : "research records"}</span></div>
        <div><span className="k">Simulator</span><span className="v mono">TMM</span><span className="s">300 K · AM1.5 · clear sky</span></div>
      </section>
      {bench.error && <Notice kind="error">{bench.error}</Notice>}
      <ol className="index-list">
        {ENTRIES.map((e, i) => (
          <li key={e.to}>
            <Link to={e.to}>
              <span className="ix mono">{String(i + 1).padStart(2, "0")}</span>
              <Glyph kind={e.glyph} />
              <span className="ix-body"><h2>{e.title}</h2><p>{e.text}</p></span>
              <ArrowRight className="ix-arrow" size={20} strokeWidth={1.2} />
            </Link>
          </li>
        ))}
      </ol>
    </>
  );
}

// ------------------------------------------------------------------ optimizer
export function OptimizerPage() {
  const nav = useNavigate();
  const [materials, setMaterials] = useState<string[]>(["Si3N4", "SiO2", "Si3N4", "SiO2"]);
  const [substrate, setSubstrate] = useState("Ag");
  const [budget, setBudget] = useState(60);
  const [seed, setSeed] = useState(0);
  const [res, setRes] = useState<OptimizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState(0); // how many trials of the history have been replayed

  useEffect(() => {
    if (!res) return;
    setShown(1);
    const n = res.history.length, step = Math.max(1, Math.round(n / 60));
    const id = setInterval(() => setShown((s) => { if (s >= n) { clearInterval(id); return n; } return Math.min(n, s + step); }), 28);
    return () => clearInterval(id);
  }, [res]);

  const run = () => {
    setBusy(true); setError(null);
    api.optimize({ materials, substrate, budget, seed }).then(setRes).catch((e: Error) => setError(e.message)).finally(() => setBusy(false));
  };
  const hist = res ? res.history.slice(0, Math.max(1, shown)) : [];
  const done = res !== null && shown >= res.history.length;
  const cur = hist[hist.length - 1];

  return (
    <>
      <PageHead kicker="§ 02 · Optimizer" title="Thickness optimizer" sub="Choose the materials and their order (top faces the sky). Each trial is one full simulation; the budget caps how many are used." />
      <div className="grid optimizer">
        <section className="panel pad">
          <h2 className="h2">Recipe</h2>
          <div className="chip-stack">
            {materials.map((m, i) => (
              <div className="chip-row" key={i}>
                <span className="pos mono">{i === 0 ? "sky" : String(i + 1).padStart(2, "0")}</span>
                <span className="sw" style={{ background: materialInfo(m).color }} />
                <select className="input" value={m} aria-label={`Layer ${i + 1}`} onChange={(e) => setMaterials((x) => x.map((v, k) => (k === i ? e.target.value : v)))}>
                  {FILM_MATERIALS.map((x) => <option key={x} value={x}>{formula(x)}</option>)}
                </select>
                <button className="icon-btn sm" aria-label="Remove" disabled={materials.length <= 1} onClick={() => setMaterials((x) => x.filter((_, k) => k !== i))}><Trash2 size={14} /></button>
              </div>
            ))}
            <div className="chip-row mirror"><span className="pos mono">base</span><span className="sw metal" />
              <select className="input" value={substrate} aria-label="Mirror" onChange={(e) => setSubstrate(e.target.value)}>{SUBSTRATES.map((s) => <option key={s} value={s}>{s === "Ag" ? "Silver mirror" : "Aluminium mirror"}</option>)}</select>
            </div>
          </div>
          <div className="row-actions">
            <button className="btn" disabled={materials.length >= MAX_LAYERS} onClick={() => setMaterials((x) => [...x, "SiO2"])}><Plus size={14} /> Add layer</button>
            <label className="inline">Budget <input className="input num" type="number" min={5} max={300} value={budget} onChange={(e) => setBudget(Number(e.target.value))} /></label>
            <label className="inline">Seed <input className="input num" type="number" min={0} value={seed} onChange={(e) => setSeed(Number(e.target.value))} /></label>
          </div>
          <button className="btn primary wide" onClick={run} disabled={busy}><Play size={14} /> {busy ? "Optimizing…" : "Run optimizer"}</button>
          {error && <Notice kind="error">{error}</Notice>}
          {res && (
            <div className="result" style={{ marginTop: 18, padding: 0 }}>
              <div className="big-metric"><div className="mono">{(cur?.best_w_m2 ?? 0).toFixed(2)}<small> W/m²</small></div>
                <div className="sub">{done ? `best of ${res.evaluations} simulations · ${res.method}` : `searching… trial ${cur?.evaluation ?? 0}`}</div></div>
              {done && <>
                <LayerStrip materials={res.best.design.materials} thicknesses={res.thicknesses_nm} substrate={res.best.design.substrate} />
                <div className="row-actions">
                  <button className="btn" onClick={() => nav(`/design?d=${encodeDesign(res.best.design)}`)}>Open in designer →</button>
                  <button className="btn" onClick={() => downloadFile("optimization.json", JSON.stringify(res, null, 2))}><Download size={14} /> JSON</button>
                </div>
              </>}
            </div>
          )}
        </section>
        <div className="col">
          <section className="panel">
            <div className="panel-head"><h2>Convergence</h2><span className="hint">each trial, and the best so far</span></div>
            {res ? (
              <LineChart xLabel="Simulation" yLabel="P_net (W/m²)" yFmt={(v) => v.toFixed(1)} series={[
                { key: "trial", label: "Each trial", color: "rgba(242,173,69,0.65)", dash: "2 3", x: hist.map((h) => h.evaluation), y: hist.map((h) => h.p_net_w_m2) },
                { key: "best", label: "Best so far", color: "#8fd8f2", x: hist.map((h) => h.evaluation), y: hist.map((h) => h.best_w_m2) },
              ]} />
            ) : <div className="empty-state"><svg viewBox="0 0 200 80" aria-hidden><path d="M10 70 L40 52 L60 56 L80 34 L110 30 L130 18 L170 15 L190 14" /></svg><p>Run the optimizer to watch the best design improve, one simulation at a time.</p></div>}
          </section>
          {done && (
            <section className="panel">
              <div className="panel-head"><h2>The winner, under the sun</h2><span className="hint">photon shares from the simulation</span></div>
              <div className="stage small">
                <Suspense fallback={<div className="scene-loading">Loading 3D view…</div>}>
                  <CoatingScene stack={{ materials: res.best.design.materials, thicknessesNm: res.thicknesses_nm, substrate: res.best.design.substrate }}
                                compare={false} mood="supported" animate photons={{ reflectance: res.best.solar_reflectance, emissivity: res.best.window_emissivity }} />
                </Suspense>
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ materials
const at = (m: Material, um: number, key: "n" | "k") => {
  let i = 0; while (i < m.wavelength_um.length - 1 && m.wavelength_um[i] < um) i++;
  return m[key][i];
};
const windowK = (m: Material) => {
  const ks = m.wavelength_um.map((l, i) => (l >= 8 && l <= 13 ? m.k[i] : 0));
  return Math.max(...ks);
};

export function MaterialsPage() {
  const { data, error, loading } = useLoad(api.materials);
  const [sel, setSel] = useState("SiO2");
  const m = data?.find((x) => x.name === sel);
  return (
    <>
      <PageHead kicker="§ 03 · Materials" title="The specimen drawer" sub="Optical constants the simulator uses: refractive index n and extinction coefficient k, from the refractiveindex.info database. A strong k inside the sky window is what makes a film emit heat to space." />
      {loading && <Loading what="materials" />}
      {error && <Notice kind="error">{error}</Notice>}
      {data && (
        <>
          <div className="specimens" role="tablist">
            {data.map((x) => (
              <button key={x.name} role="tab" aria-selected={x.name === sel} className={x.name === sel ? "specimen on" : "specimen"} onClick={() => setSel(x.name)}>
                <span className={x.role === "mirror" ? "sw metal" : "sw"} style={x.role === "mirror" ? undefined : { background: materialInfo(x.name).color }} />
                <span className="f">{formula(x.name)}</span>
                <span className="meta mono">n {at(x, 0.55, "n").toFixed(2)}{x.role === "film" && ` · k₁₀ ${windowK(x).toFixed(2)}`}</span>
                <span className="tag">{x.role === "mirror" ? "mirror" : x.in_search_space ? "searchable" : "reference"}</span>
              </button>
            ))}
          </div>
          {m && <MaterialView m={m} />}
        </>
      )}
    </>
  );
}

function MaterialView({ m }: { m: Material }) {
  const color = materialInfo(m.name).color;
  return (
    <div className="grid even" style={{ marginTop: 16 }}>
      <section className="panel">
        <div className="panel-head"><h2>{formula(m.name)} · refractive index <i>n</i></h2></div>
        <LineChart logX bands={BANDS} drawKey={m.name} xLabel="Wavelength (µm)" yLabel="n" series={[{ key: "n", label: "n", color, x: m.wavelength_um, y: m.n }]} />
      </section>
      <section className="panel">
        <div className="panel-head"><h2>Extinction coefficient <i>k</i></h2><span className="hint">peaks inside the window = heat goes to space</span></div>
        <LineChart logX bands={BANDS} drawKey={m.name} xLabel="Wavelength (µm)" yLabel="k" yFmt={(v) => v.toFixed(3)} series={[{ key: "k", label: "k", color: "#ff6a4d", x: m.wavelength_um, y: m.k }]} />
      </section>
      <section className="panel pad specimen-card">
        <div className="big-f">{formula(m.name)}</div>
        <dl>
          <dt>Role</dt><dd>{m.role}{m.in_search_space ? ", allowed in the benchmark search space" : m.role === "film" ? ", reference only (outside the search space)" : ""}</dd>
          <dt>n at 550 nm</dt><dd className="mono">{at(m, 0.55, "n").toFixed(3)}</dd>
          <dt>Peak k in 8–13 µm</dt><dd className="mono">{windowK(m).toFixed(3)}</dd>
          <dt>Cost</dt><dd>{materialInfo(m.name).cheap ? "cheap, common" : "expensive"}</dd>
          <dt>Data</dt><dd className="small">{m.sources.map((s) => `${s.file}${s.from_um || s.to_um ? ` (${s.from_um ?? "…"}–${s.to_um ?? "…"} µm)` : ""}`).join(", ")}</dd>
        </dl>
        <button className="btn" onClick={() => downloadFile(`${m.name}_nk.csv`, `wavelength_um,n,k\n${m.wavelength_um.map((l, i) => `${l},${m.n[i]},${m.k[i]}`).join("\n")}\n`, "text/csv")}><Download size={14} /> CSV</button>
      </section>
    </div>
  );
}

// ------------------------------------------------------------------ runs
export function RunsPage() {
  const { data, error, loading } = useLoad(api.runs);
  return (
    <>
      <PageHead kicker="§ 04 · Notebook" title="Lab runs" sub="Each run is the AI lab's research record: literature, hypotheses, planned tests, simulations, verdicts and human approvals." />
      {loading && <Loading what="runs" />}
      {error && <Notice kind="error">{error}</Notice>}
      {data && data.length === 0 && <Notice>No research records yet. Agent runs write runs/&lt;run_id&gt;/record.jsonl.</Notice>}
      {data && data.length > 0 && (
        <div className="run-cards">
          {data.map((r: RunSummary) => (
            <Link key={r.id} to={`/runs/${encodeURIComponent(r.id)}`} className="run-card">
              {r.fake && <span className="stamp">demo data</span>}
              <span className="date mono">{new Date(r.modified * 1000).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })}</span>
              <h2>{r.id.replace(/_/g, " ")}</h2>
              <div className="rc-best"><span className="mono">{r.best_p_net?.toFixed(2) ?? "—"}</span><small>W/m² best</small></div>
              <div className="rc-stats mono">
                <span><b>{r.entries}</b> entries</span><span><b>{r.simulations ?? "—"}</b> sims</span>
                <span><b>{r.refuted}</b> refuted</span><span><b>{r.approvals}</b> approvals</span>
              </div>
              <span className="rc-open">Open notebook <ArrowRight size={14} /></span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

export function RunPage() {
  const { id = "" } = useParams();
  const state = useLoad(async (): Promise<LabData & { raw: RecordEntry[] }> => {
    const [entries, spectra, speedup] = await Promise.all([api.record(id), api.runSpectra(id), api.benchmark()]);
    return { entries, spectra, speedup, raw: entries, fake: entries.some((e) => e._fake) };
  }, [id]);
  if (state.loading) return <Loading what={`run ${id}`} />;
  if (state.error || !state.data) return <Notice kind="error">{state.error}</Notice>;
  const d = state.data;
  return (
    <>
      <div className="row-actions" style={{ marginBottom: 10 }}>
        <Link to="/runs" className="btn">← All runs</Link>
        <button className="btn" onClick={() => downloadFile(`${id}_record.jsonl`, d.raw.map((e) => JSON.stringify(e)).join("\n") + "\n", "application/x-ndjson")}><Download size={14} /> record.jsonl</button>
      </div>
      <RunView data={d} />
    </>
  );
}

// ------------------------------------------------------------------ benchmark
export function BenchmarkPage() {
  const { data, error, loading } = useLoad(api.benchmark);
  return (
    <>
      <PageHead kicker="§ 05 · Benchmark" title="Who finds it first?" sub="Every method gets the same simulator, search space, target and simulation budget. Failed runs are kept."
        right={data && <button className="btn" onClick={() => downloadFile("speedup.json", JSON.stringify(data, null, 2))}><Download size={14} /> Data</button>} />
      {loading && <Loading what="benchmark" />}
      {error && <Notice kind="error">{error}</Notice>}
      {data && (
        <div className="bench-layout">
          <div>
            <section className="panel">
              <div className="panel-head"><h2>Simulations to reach {data.target_w_m2} W/m²</h2><span className="hint">focus method: {data.methods[data.focus].label}</span></div>
              <SpeedupRace speedup={data as Benchmark} />
            </section>
            <section className="panel pad" style={{ marginTop: 14 }}>
              <h2 className="h2">Definitions</h2>
              <dl className="defs">{Object.entries(data.definitions).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
              <p className="muted mono small">Reproduce: {data.command} · input sha256 {data.source_sha256.slice(0, 12)}</p>
            </section>
          </div>
          <aside className="margin-notes" aria-label="Caveats">
            <p className="kicker">Read before quoting</p>
            {data.caveats.map((c, i) => <p key={i} className="note"><span className="mono">{i + 1}</span>{c}</p>)}
          </aside>
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------------ methods
const TOC = [["physics", "Physics model"], ["space", "Search space"], ["control", "Control"], ["limits", "Limitations"], ["bench", "Benchmark"], ["api", "API"]] as const;

export function MethodsPage() {
  const { data } = useLoad(api.control);
  const featured = useLoad<SimResult>(() => api.simulate(PRESETS[0].design));
  const f = featured.data;
  const c = data as undefined | { simulated?: Record<string, number>; published?: Record<string, number>; gap_analysis?: { explanation?: string }; conditions?: Record<string, unknown> };
  return (
    <>
      <PageHead kicker="§ 06 · Methods" title="How every number is made" sub="And what the numbers do not cover." />
      <div className="methods-layout">
        <nav className="toc" aria-label="On this page">
          {TOC.map(([id, label], i) => <a key={id} href={`#${id}`}><span className="mono">{String(i + 1).padStart(2, "0")}</span>{label}</a>)}
        </nav>
        <article className="prose essay">
          <h2 id="physics">Physics model</h2>
          <p className="dropcap">A coating is a flat stack of thin films on an opaque metal mirror. Reflectance at each wavelength and angle comes from the transfer-matrix method,
            averaged over both polarisations. Emissivity equals absorptivity (Kirchhoff). The score is the net cooling power at ambient temperature, with
            conduction and convection zero at T = T<sub>ambient</sub>:</p>
          <Equation rad={f?.p_rad_w_m2} atm={f?.p_atm_w_m2} sun={f?.p_sun_w_m2} net={f?.p_net_w_m2} />
          <p className="caption">Numbers under the symbols: our best cheap design, in W/m², computed live.</p>
          <ul>
            <li><b>P<sub>rad</sub></b>: heat the coating radiates (hemispherical integral, 8-point Gauss–Legendre in sin²θ).</li>
            <li><b>P<sub>atm</sub></b>: sky radiation it absorbs; sky emissivity 1 − t(λ)<sup>1/cosθ</sup> from an analytic clear-sky transmittance.</li>
            <li><b>P<sub>sun</sub></b>: absorbed sunlight from the ASTM G173 AM1.5 global spectrum at normal incidence.</li>
          </ul>
          <h2 id="space">Search space</h2>
          <p>1–5 layers of SiO₂, Al₂O₃, Si₃N₄, TiO₂ or MgF₂, each 10–1000 nm, on silver or aluminium. HfO₂ appears only in the Stanford reference.</p>
          <LayerStrip materials={PRESETS[0].design.materials} thicknesses={PRESETS[0].design.thicknesses_nm} substrate={PRESETS[0].design.substrate} />
          <h2 id="control">Control: Stanford 2014 design</h2>
          <p>Raman et al., Nature 515, 540–544 (2014): 7 alternating HfO₂/SiO₂ layers on silver.</p>
          {c?.simulated && (
            <table className="data"><thead><tr><th></th><th>Our simulator</th><th>Published</th></tr></thead><tbody>
              <tr><td>Solar reflectance</td><td className="num">{(c.simulated.solar_reflectance * 100).toFixed(1)}%</td><td className="num">{((c.published?.solar_reflectance ?? 0) * 100).toFixed(0)}%</td></tr>
              <tr><td>Cooling power at ambient</td><td className="num">{c.simulated.p_net_w_m2.toFixed(2)} W/m²</td><td className="num">{c.published?.cooling_power_w_m2} W/m²</td></tr>
            </tbody></table>
          )}
          {c?.gap_analysis?.explanation && <blockquote>{c.gap_analysis.explanation}</blockquote>}
          <h2 id="limits">Limitations</h2>
          <ul>
            <li>Flat, ideal layers: no roughness, interdiffusion or fabrication error.</li>
            <li>A simplified clear sky; humidity, clouds and wind change real cooling power.</li>
            <li>Simulated, not fabricated: any design must be built and measured outdoors before a real-world claim.</li>
          </ul>
          <h2 id="bench">Benchmark</h2>
          <p>Search methods are compared on simulations needed to reach a fixed target, with the same budget and seeds. Speed-ups are the ratio of medians;
            we report the lower bound of a 95% bootstrap interval. Details and caveats are on the <Link to="/benchmark">benchmark page</Link>.</p>
          <h2 id="api">API</h2>
          <pre className="api-list">{["POST /api/simulate", "POST /api/optimize", "GET  /api/materials", "GET  /api/control", "GET  /api/runs", "GET  /api/runs/:id/record", "GET  /api/runs/:id/spectra", "GET  /api/benchmark", "GET  /api/sample"].join("\n")}</pre>
        </article>
      </div>
    </>
  );
}
