export const MATERIALS: Record<string, { color: string; name: string; cheap: boolean }> = {
  SiO2: { color: "#7dd3fc", name: "silica", cheap: true },
  Al2O3: { color: "#c4b5fd", name: "alumina", cheap: true },
  Si3N4: { color: "#f9a8d4", name: "silicon nitride", cheap: true },
  TiO2: { color: "#fde68a", name: "titania", cheap: true },
  MgF2: { color: "#86efac", name: "magnesium fluoride", cheap: true },
  HfO2: { color: "#f59e0b", name: "hafnia (expensive)", cheap: false },
  Ag: { color: "#d9e2ec", name: "silver mirror", cheap: true },
  Al: { color: "#cbd5e1", name: "aluminium mirror", cheap: true },
};

export function materialInfo(m: string) {
  return MATERIALS[m] ?? { color: "#94a3b8", name: m, cheap: true };
}

const SUB = "₀₁₂₃₄₅₆₇₈₉";
/** SiO2 -> SiO₂ */
export function formula(m: string): string {
  return m.replace(/\d/g, (d) => SUB[Number(d)]);
}

// Method colours for the speed-up race: validated categorical slots (dark-mode steps), fixed per method.
const METHOD_COLORS: Record<string, string> = {
  agent_lab: "#3987e5",
  bayes_opt: "#d95926",
  random: "#199e70",
};
const EXTRA = ["#c98500", "#d55181", "#9085e9", "#e66767"];

export function methodColors(names: string[]): Record<string, string> {
  let k = 0;
  return Object.fromEntries(names.map((n) => [n, METHOD_COLORS[n] ?? EXTRA[k++ % EXTRA.length]]));
}
