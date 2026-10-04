// Research record (runs/<run_id>/record.jsonl) and the lab state at each replay step.
// Top-level fields follow the README contract; per-kind `content` fields follow
// analysis/fake_record.py (Person 2's proposal, to agree with Person 3).

export type Kind = "literature" | "hypothesis" | "plan" | "experiment" | "result" | "verdict" | "approval";
export type HypothesisStatus = "proposed" | "testing" | "supported" | "refuted" | "inconclusive";

export type Content = Record<string, any>;

export interface RecordEntry {
  id: string;
  kind: Kind;
  agent: string;
  t: number;
  based_on: string[];
  content: Content;
  _fake?: boolean;
}

export interface Design {
  experimentId: string;
  type: "control" | "design";
  hypothesis?: string;
  materials: string[];
  thicknessesNm: number[];
  substrate: string;
}

export interface DesignResult extends Design {
  resultId: string;
  pNet: number;
  solarReflectance: number;
  windowEmissivity?: number;
}

export interface HypothesisCard {
  id: string;
  claim: string;
  status: HypothesisStatus;
  decidedBy?: string;
}

export interface KeyMoment {
  index: number;
  type: "control" | "refuted" | "supported" | "changed" | "approval";
  label: string;
}

export interface LabState {
  index: number;
  shown: RecordEntry[];
  current?: RecordEntry;
  hypotheses: HypothesisCard[];
  design?: Design;
  designResult?: DesignResult;
  control?: DesignResult;
  best?: DesignResult;
  evaluations: number;
  approvals: number;
  firstRefuted?: number;
  firstChange?: number;
  firstFound?: number;
}

const KINDS: Kind[] = ["literature", "hypothesis", "plan", "experiment", "result", "verdict", "approval"];

export function parseRecord(text: string): RecordEntry[] {
  const out: RecordEntry[] = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const e = JSON.parse(line) as RecordEntry;
    if (typeof e.id !== "string" || !KINDS.includes(e.kind) || !Array.isArray(e.based_on) || typeof e.content !== "object") {
      throw new Error(`Invalid record line: ${line.slice(0, 80)}`);
    }
    out.push(e);
  }
  return out;
}

function toDesign(e: RecordEntry): Design {
  const c = e.content;
  return {
    experimentId: e.id,
    type: c.type === "control" ? "control" : "design",
    hypothesis: c.hypothesis ?? undefined,
    materials: c.materials ?? [],
    thicknessesNm: c.thicknesses_nm ?? [],
    substrate: c.substrate ?? "Ag",
  };
}

export function labState(entries: RecordEntry[], index: number): LabState {
  const i = Math.max(-1, Math.min(index, entries.length - 1));
  const shown = entries.slice(0, i + 1);
  const byId = new Map(entries.map((e) => [e.id, e]));
  const cards = new Map<string, HypothesisCard>();
  const refuting = new Set<string>();
  const state: LabState = { index: i, shown, current: shown[shown.length - 1], hypotheses: [], evaluations: 0, approvals: 0 };

  shown.forEach((e, k) => {
    const c = e.content;
    switch (e.kind) {
      case "hypothesis":
        cards.set(e.id, { id: e.id, claim: String(c.claim ?? ""), status: (c.status ?? "proposed") as HypothesisStatus });
        break;
      case "experiment": {
        state.design = toDesign(e);
        state.designResult = undefined;
        const h = c.hypothesis && cards.get(c.hypothesis);
        if (h && h.status === "proposed") h.status = "testing";
        break;
      }
      case "result": {
        const exp = byId.get(c.experiment);
        if (!exp) break;
        const r: DesignResult = {
          ...toDesign(exp),
          resultId: e.id,
          pNet: Number(c.p_net_w_m2),
          solarReflectance: Number(c.solar_reflectance),
          windowEmissivity: c.window_emissivity,
        };
        if (exp.id === state.design?.experimentId) state.designResult = r;
        if (r.type === "control") state.control = r;
        else if (c.valid !== false && (!state.best || r.pNet > state.best.pNet)) state.best = r;
        if (typeof c.evaluations_total === "number") state.evaluations = c.evaluations_total;
        break;
      }
      case "verdict": {
        const h = cards.get(c.hypothesis);
        if (h) Object.assign(h, { status: c.status, decidedBy: e.id });
        if (c.status === "refuted") {
          refuting.add(e.id);
          state.firstRefuted ??= k;
        }
        const exp = [...shown].reverse().find((x) => x.kind === "experiment" && x.content.hypothesis === c.hypothesis);
        if (c.status === "supported" && exp?.content.type === "design") state.firstFound ??= k;
        break;
      }
      case "approval":
        if (c.decision === "approved" || c.decision === "denied") state.approvals += 1;
        break;
    }
    if ((e.kind === "hypothesis" || e.kind === "plan") && e.based_on.some((r) => refuting.has(r))) {
      state.firstChange ??= k;
    }
  });
  state.hypotheses = [...cards.values()];
  return state;
}

export function keyMoments(entries: RecordEntry[]): KeyMoment[] {
  const end = labState(entries, entries.length - 1);
  const out: KeyMoment[] = [];
  entries.forEach((e, k) => {
    if (e.kind === "verdict") {
      const isControl = entries.some((x) => x.kind === "experiment" && x.content.type === "control" && x.content.hypothesis === e.content.hypothesis);
      if (isControl && e.content.status === "supported") out.push({ index: k, type: "control", label: "Control passed" });
      else if (e.content.status === "refuted") out.push({ index: k, type: "refuted", label: `${e.content.hypothesis} refuted` });
      else if (e.content.status === "supported") out.push({ index: k, type: "supported", label: `${e.content.hypothesis} supported` });
    } else if (e.kind === "approval") {
      out.push({ index: k, type: "approval", label: `Human ${e.content.decision}` });
    }
  });
  if (end.firstChange !== undefined) out.push({ index: end.firstChange, type: "changed", label: "Plan changed" });
  return out.sort((a, b) => a.index - b.index);
}

export const AGENTS: Record<string, { name: string; color: string }> = {
  supervisor: { name: "Supervisor", color: "#7aa2ff" },
  literature_agent: { name: "Literature", color: "#b794f6" },
  hypothesis_agent: { name: "Hypothesis", color: "#f472b6" },
  planner: { name: "Planner", color: "#fbbf24" },
  analyst: { name: "Analyst", color: "#2dd4bf" },
  safety: { name: "Safety", color: "#fb923c" },
};

export function agentInfo(agent: string) {
  return AGENTS[agent] ?? { name: agent, color: "#94a3b8" };
}

const short = (s: string, n = 140) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
const uniq = (xs: string[]) => [...new Set(xs)];

/** One plain-language sentence per record entry, used as the replay subtitle. */
export function caption(e: RecordEntry): string {
  const c = e.content;
  switch (e.kind) {
    case "literature":
      return `Literature: ${short(String(c.claim))}`;
    case "hypothesis":
      return `New idea ${e.id}: ${short(String(c.claim))}`;
    case "plan": {
      const n = Array.isArray(c.candidates) ? c.candidates.length : 0;
      return `The planner weighs ${n} tests and picks ${c.chosen}: ${short(String(c.why), 110)}`;
    }
    case "experiment":
      return c.type === "control"
        ? `Control: rebuild the Stanford design (${(c.materials ?? []).length} layers) to check our simulator`
        : `Experiment ${e.id}: test ${c.hypothesis} with ${(c.materials ?? []).length} layers of ${uniq(c.materials ?? []).join(" + ")}`;
    case "result":
      return `Result: ${Number(c.p_net_w_m2).toFixed(1)} W/m² cooling, reflects ${(Number(c.solar_reflectance) * 100).toFixed(1)}% of sunlight`;
    case "verdict":
      return c.status === "refuted"
        ? `✗ ${c.hypothesis} refuted: ${short(String(c.reason), 150)}. Next: ${short(String(c.next ?? ""), 80)}`
        : `${c.status === "supported" ? "✓" : "?"} ${c.hypothesis} ${c.status}: ${short(String(c.reason), 110)}`;
    case "approval":
      return `Human ${c.decision}: ${short(String(c.request), 110)}`;
  }
}
