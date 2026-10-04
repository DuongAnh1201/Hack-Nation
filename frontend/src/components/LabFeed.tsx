import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { BookOpen, ClipboardList, FlaskConical, Gauge, Lightbulb, Scale, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { formula, materialInfo } from "../lib/materials";
import { agentInfo, type HypothesisCard, type Kind, type RecordEntry } from "../lib/record";
import { StatusPill } from "./HypothesisBoard";

const KIND_ICON: Record<Kind, typeof BookOpen> = {
  literature: BookOpen, hypothesis: Lightbulb, plan: ClipboardList, experiment: FlaskConical,
  result: Gauge, verdict: Scale, approval: ShieldCheck,
};

export function LabFeed({ shown, currentId, hypotheses, target }: {
  shown: RecordEntry[]; currentId?: string; hypotheses: HypothesisCard[]; target: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const nodes = useRef(new Map<string, HTMLDivElement>());
  const [hover, setHover] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const reduce = useReducedMotion();
  const byId = useMemo(() => new Map(shown.map((e) => [e.id, e])), [shown]);
  const evidence = new Set(hover ? byId.get(hover)?.based_on ?? [] : flash ? [flash] : []);

  useEffect(() => { // keep the newest entry in view
    const el = currentId ? nodes.current.get(currentId) : undefined;
    if (el && box.current) box.current.scrollTo({ top: el.offsetTop - box.current.clientHeight + el.offsetHeight + 24 });
  }, [currentId, shown.length]);

  const jump = (id: string) => {
    const el = nodes.current.get(id);
    if (el && box.current) box.current.scrollTo({ top: el.offsetTop - 40 });
    setFlash(id);
    window.setTimeout(() => setFlash((f) => (f === id ? null : f)), 1400);
  };

  return (
    <div className="feed" ref={box} aria-live="polite">
      <AnimatePresence initial={false}>
        {shown.map((e) => {
          const a = agentInfo(e.agent);
          const Icon = KIND_ICON[e.kind];
          const verdict = e.kind === "verdict" ? e.content.status : undefined;
          const cls = ["entry", e.id === currentId && "current", evidence.has(e.id) && "evidence",
            hover && !evidence.has(e.id) && e.id !== hover && "dim", verdict === "refuted" && "refuted",
            verdict === "supported" && "supported"].filter(Boolean).join(" ");
          return (
            <motion.div key={e.id} ref={(el: HTMLDivElement | null) => { if (el) nodes.current.set(e.id, el); else nodes.current.delete(e.id); }}
              className={cls} layout={!reduce}
              initial={{ opacity: 0, y: 14, scale: 0.98 }}
              animate={verdict === "refuted" && !reduce
                ? { opacity: 1, y: 0, scale: 1, x: [0, -7, 7, -4, 4, 0] }
                : { opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              onMouseEnter={() => setHover(e.id)} onMouseLeave={() => setHover(null)}>
              <div className="avatar" style={{ color: a.color, borderColor: `${a.color}55`, background: `${a.color}14` }}>
                <Icon size={17} />
              </div>
              <div>
                <div className="top">
                  <span className="id">{e.id}</span>
                  <span className="kind">{e.kind}</span>
                  <span>· {a.name}</span>
                  {e.kind === "hypothesis" && (
                    <StatusPill status={hypotheses.find((h) => h.id === e.id)?.status ?? "proposed"} />
                  )}
                </div>
                <Body e={e} target={target} />
                {e.based_on.length > 0 && (
                  <div className="refs" aria-label="Based on">
                    {e.based_on.map((r) => (
                      <button key={r} className="chip" onClick={() => jump(r)} title={`Show evidence ${r}`}>↳ {r}</button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

function Body({ e, target }: { e: RecordEntry; target: number }) {
  const c = e.content;
  switch (e.kind) {
    case "literature":
      return <div className="body">{c.claim} <div className="metric">{c.url ? <a href={c.url} target="_blank" rel="noreferrer">{c.source}</a> : c.source}</div></div>;
    case "hypothesis":
      return <div className="body">{c.claim}<div className="metric">{c.rationale}</div></div>;
    case "plan":
      return (
        <div className="body">
          Weighs {c.candidates.length} tests:
          <div className="options">
            {c.candidates.map((o: { test: string; description: string; cost_evals?: number }) => (
              <div key={o.test} className={`option${o.test === c.chosen ? " chosen" : ""}`}>
                <b>{o.test === c.chosen ? "✓ " : ""}{o.test}</b> · {o.description}
                {o.cost_evals !== undefined && <span className="mono"> · {o.cost_evals} sims</span>}
              </div>
            ))}
          </div>
          <div className="metric" style={{ marginTop: 6 }}>Why {c.chosen}: {c.why}</div>
        </div>
      );
    case "experiment":
      return (
        <div className="body">
          {c.type === "control" ? "Control run: rebuild the Stanford design" : `Test ${c.hypothesis}`} on {c.substrate}
          <div className="refs">
            {c.materials.map((m: string, i: number) => (
              <span key={i} className="chip" style={{ cursor: "default", color: materialInfo(m).color, borderColor: `${materialInfo(m).color}55` }}>
                {formula(m)} {c.thicknesses_nm?.[i]} nm
              </span>
            ))}
          </div>
        </div>
      );
    case "result": {
      const p = Number(c.p_net_w_m2);
      const ok = p >= target;
      return (
        <div className="metrics">
          <div className="metric">Net cooling<b className="mono" style={{ color: ok ? "var(--supported)" : "var(--heat)" }}>{p.toFixed(1)} W/m²</b>
            <div className="bar"><i style={{ width: `${Math.min(100, (p / (target * 1.15)) * 100)}%`, background: ok ? "var(--supported)" : "var(--heat)" }} />
              <span className="goal" style={{ left: `${100 / 1.15}%` }} title={`target ${target} W/m²`} /></div>
          </div>
          <div className="metric">Sunlight reflected<b className="mono" style={{ color: "var(--sun)" }}>{(Number(c.solar_reflectance) * 100).toFixed(1)}%</b></div>
          {c.window_emissivity !== undefined && <div className="metric">Emits in window<b className="mono" style={{ color: "var(--ice)" }}>{(Number(c.window_emissivity) * 100).toFixed(0)}%</b></div>}
          <div className="metric">Simulations<b className="mono">{c.evaluations}</b></div>
        </div>
      );
    }
    case "verdict":
      return (
        <div className="body">
          <StatusPill status={c.status} /> <b>{c.hypothesis}</b>: {c.reason}
          {c.next && <div className="metric" style={{ marginTop: 4 }}>Next → {c.next}</div>}
        </div>
      );
    case "approval":
      return (
        <div className="body">
          <span className={`status ${c.decision === "approved" ? "supported" : c.decision === "denied" ? "refuted" : "testing"}`}>
            {c.decision === "approved" ? "✓" : c.decision === "denied" ? "✗" : "…"} {c.decision}
          </span>{" "}
          by {c.approver ?? "human"} · {c.request}
        </div>
      );
  }
}
