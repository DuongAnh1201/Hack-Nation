import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw } from "lucide-react";
import type { KeyMoment, RecordEntry } from "../lib/record";
import { caption } from "../lib/record";
import { SPEEDS } from "../lib/useReplay";

const MOMENT_COLOR: Record<KeyMoment["type"], string> = {
  control: "#3ddc97", refuted: "#ff5d73", changed: "#a78bfa", supported: "#5ad1ff", approval: "#ffb547",
};

export function ReplayBar({ entries, index, playing, speed, moments, onPlay, onPause, onSeek, onRestart, onSpeed }: {
  entries: RecordEntry[]; index: number; playing: boolean; speed: number; moments: KeyMoment[];
  onPlay: () => void; onPause: () => void; onSeek: (i: number) => void; onRestart: () => void; onSpeed: (s: (typeof SPEEDS)[number]) => void;
}) {
  const n = entries.length;
  const pct = (i: number) => (n > 1 ? (i / (n - 1)) * 100 : 0);
  const current = entries[index];
  // stagger marker labels over two rows so neighbours never overlap
  const lastInRow = [-Infinity, -Infinity];
  const rows = moments.map((m) => {
    const x = pct(m.index);
    const row = x - lastInRow[0] >= 13 ? 0 : x - lastInRow[1] >= 13 ? 1 : -1;
    if (row >= 0) lastInRow[row] = x;
    return row;
  });
  return (
    <div className="replay" role="region" aria-label="Replay controls">
      <div className="caption">
        <span className="step">{index + 1}/{n}</span>
        <AnimatePresence mode="wait">
          <motion.span key={current?.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                       transition={{ duration: 0.25 }}>
            {current ? caption(current) : ""}
          </motion.span>
        </AnimatePresence>
      </div>
      <div className="controls">
        <button className="icon-btn" onClick={onRestart} title="Restart the story" aria-label="Restart"><RotateCcw size={16} /></button>
        <button className="icon-btn" onClick={() => onSeek(index - 1)} title="Previous step (←)" aria-label="Previous step"><ChevronLeft size={18} /></button>
        <button className="icon-btn primary" onClick={playing ? onPause : onPlay} title="Play / pause (space)" aria-label={playing ? "Pause" : "Play the story"}>
          {playing ? <Pause size={20} /> : <Play size={20} />}
        </button>
        <button className="icon-btn" onClick={() => onSeek(index + 1)} title="Next step (→)" aria-label="Next step"><ChevronRight size={18} /></button>
        <div className="track">
          <div className="rail" />
          <div className="fill" style={{ width: `${pct(index)}%` }} />
          {moments.map((m, k) => (
            <span key={`${m.type}-${m.index}`} title={m.label} style={{ ["--c" as string]: MOMENT_COLOR[m.type] }}>
              <span className="dot" style={{ left: `${pct(m.index)}%` }} />
              {rows[k] >= 0 && <span className={`mark row${rows[k]}`} style={{ left: `${pct(m.index)}%` }}>{m.label}</span>}
            </span>
          ))}
          <div className="knob" style={{ left: `${pct(index)}%` }} />
          <input type="range" min={0} max={n - 1} value={index} aria-label="Replay position"
                 onChange={(e) => { onPause(); onSeek(Number(e.target.value)); }} />
        </div>
        <div className="seg" role="group" aria-label="Replay speed">
          {SPEEDS.map((s) => <button key={s} aria-pressed={speed === s} onClick={() => onSpeed(s)}>{s}×</button>)}
        </div>
      </div>
    </div>
  );
}
