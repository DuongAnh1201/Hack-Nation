import { animate, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

/** Animates a number from its previous value to the new one. */
export function useCountUp(value: number, duration = 0.9): number {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    if (reduce) { setShown(value); from.current = value; return; }
    const controls = animate(from.current, value, {
      duration, ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setShown(v),
      onComplete: () => { from.current = value; },
    });
    return () => { from.current = value; controls.stop(); };
  }, [value, duration, reduce]);
  return shown;
}
