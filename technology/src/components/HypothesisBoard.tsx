import { LayoutGroup, motion, useReducedMotion } from "motion/react";
import type { HypothesisCard, HypothesisStatus } from "../lib/record";

const ICON: Record<HypothesisStatus, string> = { proposed: "○", testing: "…", supported: "✓", refuted: "✗", inconclusive: "?" };

export function StatusPill({ status }: { status: HypothesisStatus }) {
  return <span className={`status ${status}`}>{ICON[status]} {status}</span>;
}

const COLUMNS: { key: string; title: string; color: string; has: HypothesisStatus[] }[] = [
  { key: "proposed", title: "Proposed", color: "var(--proposed)", has: ["proposed"] },
  { key: "testing", title: "Testing", color: "var(--testing)", has: ["testing", "inconclusive"] },
  { key: "supported", title: "Supported", color: "var(--supported)", has: ["supported"] },
  { key: "refuted", title: "Refuted", color: "var(--refuted)", has: ["refuted"] },
];

export function HypothesisBoard({ hypotheses }: { hypotheses: HypothesisCard[] }) {
  const reduce = useReducedMotion();
  return (
    <LayoutGroup>
      <div className="board">
        {COLUMNS.map((col) => {
          const cards = hypotheses.filter((h) => col.has.includes(h.status));
          return (
            <div key={col.key} className="col">
              <h3 style={{ color: col.color }}>{ICON[col.has[0]]} {col.title}<span className="n">{cards.length}</span></h3>
              {cards.map((h) => (
                <motion.div key={h.id} layoutId={reduce ? undefined : h.id} className="hcard"
                  style={{ borderColor: h.status === "proposed" ? undefined : `color-mix(in srgb, ${col.color} 45%, transparent)` }}
                  transition={{ type: "spring", stiffness: 260, damping: 28 }}>
                  <div><span className="hid" style={{ color: col.color }}>{h.id}</span>{h.status === "inconclusive" && <> · <StatusPill status="inconclusive" /></>}</div>
                  <p>{h.claim}</p>
                  {h.decidedBy && <div className="by">decided by {h.decidedBy}</div>}
                </motion.div>
              ))}
            </div>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
