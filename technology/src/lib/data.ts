// Loads the three files the UI replays. Defaults point at the FAKE demo data in
// public/demo; pass ?record=…&speedup=…&spectra=… to replay a real run.

import { parseRecord, type RecordEntry } from "./record";

export interface Speedup {
  fake: boolean;
  target_w_m2: number;
  budget: number;
  focus: string;
  method_order: string[];
  colors: Record<string, string>;
  methods: Record<string, {
    label: string; runs: number; reached: number; success_rate: number;
    median_evals: number | null; median_censored: boolean; best_w_m2_median: number; best_w_m2_max: number;
  }>;
  speedups: { focus: string; baseline: string; point: number; ci95: [number, number]; supported: boolean;
              baseline_censored: boolean; claim: string }[];
  curves: Record<string, [number, number][]>;
}

export interface Spectra {
  _fake?: boolean;
  _source?: string;
  wavelength_um: number[];
  bands: { solar: [number, number]; window: [number, number] };
  ideal: number[];
  sky_transmittance?: number[];
  sky_model?: string;
  designs: Record<string, { label: string; emissivity: number[]; p_net_w_m2?: number }>;
}

export interface LabData {
  entries: RecordEntry[];
  speedup: Speedup;
  spectra: Spectra;
  fake: boolean;
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.text();
}

export async function loadLabData(search = window.location.search): Promise<LabData> {
  const q = new URLSearchParams(search);
  const base = import.meta.env.BASE_URL;
  const [recordText, speedupText, spectraText] = await Promise.all([
    fetchText(q.get("record") ?? `${base}demo/record.jsonl`),
    fetchText(q.get("speedup") ?? `${base}demo/speedup.json`),
    fetchText(q.get("spectra") ?? `${base}demo/spectra.json`),
  ]);
  const entries = parseRecord(recordText);
  const speedup = JSON.parse(speedupText) as Speedup;
  const spectra = JSON.parse(spectraText) as Spectra;
  return { entries, speedup, spectra, fake: entries.some((e) => e._fake) || speedup.fake || Boolean(spectra._fake) };
}
