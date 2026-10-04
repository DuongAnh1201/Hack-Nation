import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Activity, Box, ListTree, Rocket, Waves } from "lucide-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { HypothesisBoard } from "../components/HypothesisBoard";
import { LabFeed } from "../components/LabFeed";
import { Header, StatTiles, StoryProgress } from "../components/Overview";
import { ReplayBar } from "../components/ReplayBar";
import { SpectrumChart } from "../components/SpectrumChart";
import { SpeedupRace } from "../components/SpeedupRace";
import type { LabData } from "../lib/data";
import { formula, materialInfo } from "../lib/materials";
import { keyMoments, labState, type RecordEntry } from "../lib/record";
import { useReplay } from "../lib/useReplay";
import type { Stack } from "../scenes/CoatingScene";

// three.js is most of the bundle: load the 3D scene in its own chunk so the page appears first.
const CoatingScene = lazy(() => import("../scenes/CoatingScene").then((m) => ({ default: m.CoatingScene })));

const QUESTION = "Can an AI lab design a coating with at most 5 layers of cheap materials that matches or beats the cooling " +
  "power of Stanford's 7-layer design, using fewer simulations than standard automated search?";

function toStack(e?: RecordEntry): Stack | undefined {
  if (!e) return undefined;
  return { materials: e.content.materials ?? [], thicknessesNm: e.content.thicknesses_nm ?? [], substrate: e.content.substrate ?? "Ag" };
}

export function RunView({ data }: { data: LabData }) {
  const { entries, speedup, spectra, fake } = data;
  const replay = useReplay(entries.length);
  const reduce = useReducedMotion() ?? false;
  const [compare, setCompare] = useState(false);
  const state = useMemo(() => labState(entries, replay.index), [entries, replay.index]);
  const moments = useMemo(() => keyMoments(entries), [entries]);
  const controlIdx = entries.findIndex((e) => e.kind === "experiment" && e.content.type === "control");
  const reference = controlIdx >= 0 && replay.index >= controlIdx ? toStack(entries[controlIdx]) : undefined;
  const target = speedup.target_w_m2;
  const current = state.current;
  const mood = current?.kind === "verdict" && current.content.status === "refuted" ? "refuted"
    : current?.kind === "verdict" && current.content.status === "supported" ? "supported" : "neutral";
  const stack = state.design ? { materials: state.design.materials, thicknessesNm: state.design.thicknessesNm, substrate: state.design.substrate } : undefined;
  const r = state.designResult;

  return (
    <div>
      <Header fake={fake} entries={entries} question={QUESTION} />
      <StoryProgress state={state} entries={entries} speedup={speedup} onSeek={(i) => { replay.pause(); replay.seek(i); }} />
      <StatTiles state={state} speedup={speedup} />

      <div className="grid">
        <section className="panel">
          <div className="panel-head">
            <Box size={16} color="var(--ice)" /><h2>The coating</h2>
            <span className="hint">{state.design ? `${state.design.experimentId} · ${state.design.type === "control" ? "Stanford control" : `testing ${state.design.hypothesis}`}` : "no design yet"} · drag to rotate</span>
            <span className="spacer" />
            <div className="seg" role="group" aria-label="Comparison">
              <button aria-pressed={!compare} onClick={() => setCompare(false)}>This design</button>
              <button aria-pressed={compare} onClick={() => setCompare(true)} disabled={!reference}>vs Stanford</button>
            </div>
          </div>
          <div className="stage">
            <Suspense fallback={<div className="scene-loading">Loading 3D view…</div>}>
              <CoatingScene stack={stack} reference={reference} compare={compare} mood={mood} animate={!reduce} />
            </Suspense>
            <AnimatePresence>
              {mood !== "neutral" && (
                <motion.div key={current?.id} className="stage-flash" initial={{ opacity: 0 }} animate={{ opacity: [0, 1, 0.35] }} exit={{ opacity: 0 }}
                  transition={{ duration: 1.1 }}
                  style={{ background: `radial-gradient(circle at 50% 55%, ${mood === "refuted" ? "rgba(255,45,74,0.28)" : "rgba(25,211,138,0.24)"}, transparent 65%)` }} />
              )}
            </AnimatePresence>
            {stack && (
              <div className="stage-legend">
                <div className="cap">Layers, top to bottom</div>
                {[...stack.materials].map((m, i) => ({ m, t: stack.thicknessesNm[i] })).reverse().map(({ m, t }, i) => (
                  <div className="row" key={i}><span className="sw" style={{ background: materialInfo(m).color }} />{formula(m)}
                    {!materialInfo(m).cheap && <span style={{ color: "var(--sun)", fontSize: 11 }}>· expensive</span>}
                    <span className="t mono">{t} nm</span></div>
                ))}
                <div className="row"><span className="sw" style={{ background: materialInfo(stack.substrate).color }} />{stack.substrate} mirror</div>
              </div>
            )}
            <div className="scene-tags" aria-hidden="true">
              <span className="scene-tag" style={{ color: "#ffb547" }}>☀ sunlight bounces off</span>
              <span className="scene-tag" style={{ color: "#ff8a7a" }}>heat escapes to space · 8–13 µm</span>
              {compare && reference && <span className="scene-tag" style={{ color: "#a4b1cc" }}>ghost = Stanford 2014 (7 layers) · solid = this design</span>}
            </div>
            <div className="stage-metric">
              {r ? (
                <>
                  <div className="big mono" style={{ color: r.pNet >= target ? "var(--supported)" : "var(--heat)" }}>{r.pNet.toFixed(1)} W/m²</div>
                  <div className="small">{r.pNet >= target ? "✓ meets" : "✗ below"} target {target.toFixed(1)} · reflects {(r.solarReflectance * 100).toFixed(1)}% sunlight</div>
                </>
              ) : (
                <div className="small">{stack ? "simulating…" : "the lab is reading the literature"}</div>
              )}
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <Waves size={16} color="var(--ice)" /><h2>Spectrum</h2>
            <span className="hint">how strongly the coating emits at each wavelength</span>
          </div>
          <div className="spectrum-cap"><SpectrumChart spectra={spectra} currentId={state.design?.experimentId} referenceId={reference ? entries[controlIdx].id : undefined} /></div>
        </section>
      </div>

      <div className="grid even">
        <section className="panel">
          <div className="panel-head">
            <Activity size={16} color="var(--ice)" /><h2>Lab feed</h2>
            <span className="hint">every agent step, in order · hover a card to light up its evidence</span>
          </div>
          <LabFeed shown={state.shown} currentId={current?.id} hypotheses={state.hypotheses} target={target} />
        </section>
        <section className="panel">
          <div className="panel-head">
            <ListTree size={16} color="var(--ice)" /><h2>Hypotheses</h2>
            <span className="hint">cards move as evidence arrives</span>
          </div>
          <HypothesisBoard hypotheses={state.hypotheses} />
        </section>
      </div>

      <section className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-head"><Rocket size={16} color="var(--sun)" /><h2>Measured speed-up</h2>
          <span className="hint">same simulator, search space and budget for every method · we claim the lower bound</span></div>
        <SpeedupRace speedup={speedup} />
      </section>

      <ReplayBar entries={entries} index={replay.index} playing={replay.playing} speed={replay.speed} moments={moments}
                 onPlay={replay.play} onPause={replay.pause} onSeek={replay.seek} onRestart={replay.restart} onSpeed={replay.setSpeed} />
    </div>
  );
}
