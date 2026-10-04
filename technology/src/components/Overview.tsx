import { AlertTriangle, CheckCircle2, Cpu, Gauge, Rocket, ShieldCheck, Snowflake, Target } from "lucide-react";
import type { ReactNode } from "react";
import type { Speedup } from "../lib/data";
import { formula } from "../lib/materials";
import type { LabState, RecordEntry } from "../lib/record";
import { useCountUp } from "../lib/useCountUp";

export function Header({ fake, entries, question }: { fake: boolean; entries: RecordEntry[]; question: string }) {
  const agents = new Set(entries.map((e) => e.agent)).size;
  return (
    <>
      {fake && (
        <div className="fake-banner" role="status">
          <AlertTriangle size={14} /> FAKE DEMO DATA for building the UI. Not results; do not cite any number on this page.
        </div>
      )}
      <header className="header">
        <div className="logo"><Snowflake size={22} /></div>
        <div>
          <h1 className="title">Radiative Cooling AI Lab</h1>
          <p className="subtitle">{question}</p>
        </div>
        <div className="meta">
          <span className="pill"><Cpu size={13} /> Omnigent · <b>{agents}</b> agents</span>
          <span className="pill"><b>{entries.length}</b> record entries</span>
        </div>
      </header>
    </>
  );
}

interface Step { key: string; label: string; text: string; index?: number; color: string }

export function StoryProgress({ state, entries, speedup, onSeek }: {
  state: LabState; entries: RecordEntry[]; speedup: Speedup; onSeek: (i: number) => void;
}) {
  const end = entries.length - 1;
  const refuted = state.firstRefuted !== undefined ? entries[state.firstRefuted] : entries.find((e) => e.kind === "verdict" && e.content.status === "refuted");
  const bo = speedup.speedups.find((s) => s.baseline === "bayes_opt");
  const steps: Step[] = [
    { key: "asked", label: "1 · Asked", text: "Can ≤5 cheap layers beat Stanford's 7?", index: 0, color: "#5ad1ff" },
    { key: "failed", label: "2 · Failed", text: refuted ? `${refuted.content.hypothesis} refuted` : "waiting…",
      index: entries.findIndex((e) => e === refuted), color: "#ff5d73" },
    { key: "changed", label: "3 · Changed", text: "New materials, new plan", index: firstChangeIndex(entries), color: "#a78bfa" },
    { key: "found", label: "4 · Found", text: foundText(entries), index: foundIndex(entries), color: "#3ddc97" },
    { key: "faster", label: "5 · Faster", text: bo?.supported ? `≥ ${bo.ci95[0].toFixed(1)}× fewer simulations than BO` : "no speed-up claimed",
      index: end, color: "#ffb547" },
  ];
  return (
    <nav className="story" aria-label="The discovery in five steps">
      {steps.map((s) => {
        const lit = s.index !== undefined && s.index >= 0 && state.index >= s.index;
        return (
          <button key={s.key} className={`story-step${lit ? " lit" : ""}`} style={{ ["--step-color" as string]: s.color }}
                  onClick={() => s.index !== undefined && s.index >= 0 && onSeek(s.index)} title="Jump to this moment">
            <div className="k">{s.label}</div>
            <div className="v">{s.text}</div>
          </button>
        );
      })}
    </nav>
  );
}

function firstChangeIndex(entries: RecordEntry[]): number {
  const refuting = new Set(entries.filter((e) => e.kind === "verdict" && e.content.status === "refuted").map((e) => e.id));
  return entries.findIndex((e) => (e.kind === "hypothesis" || e.kind === "plan") && e.based_on.some((r) => refuting.has(r)));
}

function foundIndex(entries: RecordEntry[]): number {
  const designHyps = new Set(entries.filter((e) => e.kind === "experiment" && e.content.type === "design").map((e) => e.content.hypothesis));
  return entries.findIndex((e) => e.kind === "verdict" && e.content.status === "supported" && designHyps.has(e.content.hypothesis));
}

function foundText(entries: RecordEntry[]): string {
  const i = foundIndex(entries);
  if (i < 0) return "not yet";
  const h = entries[i].content.hypothesis;
  const exp = entries.find((e) => e.kind === "experiment" && e.content.hypothesis === h);
  return exp ? `${exp.content.materials.length} layers of ${[...new Set<string>(exp.content.materials)].map(formula).join(" + ")}` : `${h} supported`;
}

function Tile({ icon, label, value, unit, decimals = 0, sub, accent }: {
  icon: ReactNode; label: string; value?: number; unit?: string; decimals?: number; sub: string; accent?: string;
}) {
  const shown = useCountUp(value ?? 0);
  return (
    <div className="panel tile">
      <div className="label">{icon}{label}</div>
      <div className="value mono" style={{ color: accent }}>
        {value === undefined ? "—" : shown.toFixed(decimals)}{value !== undefined && unit && <small>{unit}</small>}
      </div>
      <div className="sub">{sub}</div>
    </div>
  );
}

export function StatTiles({ state, speedup }: { state: LabState; speedup: Speedup }) {
  const target = speedup.target_w_m2;
  const best = state.best;
  const hit = best && best.pNet >= target;
  const bo = speedup.speedups.find((s) => s.baseline === "bayes_opt");
  return (
    <section className="tiles" aria-label="Key numbers">
      <Tile icon={<Target size={14} />} label="Benchmark target" value={target} unit=" W/m²" decimals={1}
            sub={state.control ? `Stanford 2014 in our simulator: ${state.control.pNet.toFixed(1)} W/m²` : "fixed before the search"} />
      <Tile icon={hit ? <CheckCircle2 size={14} color="#3ddc97" /> : <Gauge size={14} />} label="Best design so far"
            value={best?.pNet} unit=" W/m²" decimals={1} accent={hit ? "#3ddc97" : undefined}
            sub={best ? `${best.materials.length} layers · ${[...new Set(best.materials)].map(formula).join(" + ")}` : "no design tested yet"} />
      <Tile icon={<Rocket size={14} />} label="Speed-up (claimed)" value={bo?.supported ? bo.ci95[0] : undefined} unit="×" decimals={1}
            sub={bo ? `at least, vs Bayesian optimization · 95% CI` : "benchmark pending"} accent="#ffb547" />
      <Tile icon={<Cpu size={14} />} label="Simulations used" value={state.evaluations} sub="every evaluation counts" />
      <Tile icon={<ShieldCheck size={14} />} label="Human approvals" value={state.approvals} sub="before any fabrication" />
    </section>
  );
}
