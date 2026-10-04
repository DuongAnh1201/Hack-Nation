// Typed client for the lab API (backend/app/api/lab.py). In dev, Vite proxies /api to :8000.

import type { Speedup, Spectra } from "./data";
import { parseRecord, type RecordEntry } from "./record";

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new ApiError("Cannot reach the lab API. Is the backend running?");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    throw new ApiError(typeof detail === "string" ? detail : `HTTP ${res.status}`);
  }
  return body as T;
}

export interface SampleDesign { materials: string[]; thicknesses_nm: number[]; substrate: string; p_net_w_m2: number }

export interface Design { materials: string[]; thicknesses_nm: number[]; substrate: string }

export interface SimResult {
  p_net_w_m2: number; p_rad_w_m2: number; p_atm_w_m2: number; p_sun_w_m2: number;
  solar_reflectance: number; window_emissivity: number;
  design: Design; in_search_space: boolean; search_space_note: string | null;
  conditions: { t_ambient_k: number; sun: string; sky: string; solar_band_um: [number, number]; window_band_um: [number, number] };
  spectrum: { wavelength_um: number[]; emissivity: number[]; sky_transmittance: number[] };
}

export interface OptimizeResult {
  best: SimResult; thicknesses_nm: number[]; evaluations: number; method: string;
  history: { evaluation: number; p_net_w_m2: number; best_w_m2: number }[];
}

export interface Material {
  name: string; role: "film" | "mirror"; in_search_space: boolean;
  sources: { file: string; from_um: number | null; to_um: number | null }[];
  wavelength_um: number[]; n: number[]; k: number[];
}

export interface RunSummary {
  id: string; entries: number; fake: boolean; best_p_net: number | null;
  simulations: number | null; refuted: number; approvals: number; modified: number;
}

export type Benchmark = Speedup & { caveats: string[]; command: string; source_sha256: string; definitions: Record<string, string> };

export const api = {
  simulate: (d: Design) => call<SimResult>("/api/simulate", { method: "POST", body: JSON.stringify(d) }),
  optimize: (r: { materials: string[]; substrate: string; budget: number; seed: number }) =>
    call<OptimizeResult>("/api/optimize", { method: "POST", body: JSON.stringify(r) }),
  materials: () => call<Material[]>("/api/materials"),
  control: () => call<Record<string, unknown>>("/api/control"),
  runs: () => call<RunSummary[]>("/api/runs"),
  record: async (id: string): Promise<RecordEntry[]> => {
    const rows = await call<RecordEntry[]>(`/api/runs/${encodeURIComponent(id)}/record`);
    return parseRecord(rows.map((r) => JSON.stringify(r)).join("\n"));
  },
  runSpectra: (id: string) => call<Spectra>(`/api/runs/${encodeURIComponent(id)}/spectra`),
  benchmark: () => call<Benchmark>("/api/benchmark"),
  sample: (n = 36, seed = 7) => call<{ seed: number; designs: SampleDesign[] }>(`/api/sample?n=${n}&seed=${seed}`),
};

/** Wrap one simulate result as a Spectra object the SpectrumChart understands. */
export function toSpectra(results: { id: string; label: string; r: SimResult }[]): Spectra | undefined {
  const first = results[0]?.r;
  if (!first) return undefined;
  const lam = first.spectrum.wavelength_um;
  const [wLo, wHi] = first.conditions.window_band_um;
  return {
    wavelength_um: lam,
    bands: { solar: first.conditions.solar_band_um, window: first.conditions.window_band_um },
    ideal: lam.map((x) => (x >= wLo && x <= wHi ? 1 : 0)),
    sky_transmittance: first.spectrum.sky_transmittance,
    sky_model: first.conditions.sky,
    designs: Object.fromEntries(results.map(({ id, label, r }) => [id, { label, emissivity: r.spectrum.emissivity, p_net_w_m2: r.p_net_w_m2 }])),
  };
}

export function downloadFile(name: string, text: string, type = "application/json") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
