import type { Design } from "./api";

export const FILM_MATERIALS = ["SiO2", "Al2O3", "Si3N4", "TiO2", "MgF2"] as const;
export const REFERENCE_MATERIALS = ["HfO2"] as const;
export const SUBSTRATES = ["Ag", "Al"] as const;
export const T_MIN = 10, T_MAX = 1000, MAX_LAYERS = 5;

export const PRESETS: { id: string; label: string; note: string; design: Design }[] = [
  { id: "si3n4", label: "Si3N4/SiO2, 4 layers", note: "strong cheap design found while exploring the bench",
    design: { materials: ["Si3N4", "SiO2", "Si3N4", "SiO2"], thicknesses_nm: [424, 406, 606, 72], substrate: "Ag" } },
  { id: "stanford", label: "Stanford 2014 reference", note: "7 layers HfO2/SiO2, outside the search space",
    design: { materials: ["SiO2", "HfO2", "SiO2", "HfO2", "SiO2", "HfO2", "SiO2"], thicknesses_nm: [230, 485, 688, 13, 73, 34, 54], substrate: "Ag" } },
  { id: "silica", label: "Single silica layer", note: "simplest possible emitter",
    design: { materials: ["SiO2"], thicknesses_nm: [800], substrate: "Ag" } },
];

export function encodeDesign(d: Design): string {
  return btoa(JSON.stringify([d.materials, d.thicknesses_nm.map((t) => Math.round(t * 10) / 10), d.substrate]));
}

export function decodeDesign(s: string | null): Design | null {
  if (!s) return null;
  try {
    const [materials, thicknesses_nm, substrate] = JSON.parse(atob(s));
    if (Array.isArray(materials) && Array.isArray(thicknesses_nm) && typeof substrate === "string") return { materials, thicknesses_nm, substrate };
  } catch { /* invalid link: fall back to the default design */ }
  return null;
}

const KEY = "physio.designs.v1";
export interface Saved { name: string; design: Design; p_net_w_m2: number; saved: number }

export function loadSaved(): Saved[] {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; }
}
export function storeSaved(list: Saved[]) {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* storage unavailable: keep in memory */ }
}
