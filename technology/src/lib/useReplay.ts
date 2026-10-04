import { useCallback, useEffect, useRef, useState } from "react";

export const SPEEDS = [1, 2, 4] as const;
const STEP_MS = 2100; // at 1x, ~19 record entries play in about 40 seconds

export function useReplay(length: number) {
  const [index, setIndex] = useState(length - 1); // open fully revealed; "Play" tells the story
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!playing) return;
    timer.current = window.setTimeout(() => {
      if (index >= length - 1) setPlaying(false);
      else setIndex(index + 1);
    }, STEP_MS / speed);
    return () => window.clearTimeout(timer.current);
  }, [playing, index, speed, length]);

  const play = useCallback(() => {
    if (index >= length - 1) setIndex(0);
    setPlaying(true);
  }, [index, length]);
  const pause = useCallback(() => setPlaying(false), []);
  const seek = useCallback((i: number) => setIndex(Math.max(0, Math.min(length - 1, i))), [length]);
  const restart = useCallback(() => { setIndex(0); setPlaying(true); }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.code === "Space") { e.preventDefault(); setPlaying((p) => !p); }
      if (e.code === "ArrowRight") { setPlaying(false); setIndex((i) => Math.min(length - 1, i + 1)); }
      if (e.code === "ArrowLeft") { setPlaying(false); setIndex((i) => Math.max(0, i - 1)); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [length]);

  return { index, playing, speed, setSpeed, play, pause, seek, restart };
}
