import { createContext, useContext, useEffect, useState, type RefObject } from "react";
import { clamp01 } from "../lib/format";

/** The film renders into a fixed frame, so charts size from that frame rather than from the window. */
export const FrameHeight = createContext<number | null>(null);

export function useReducedMotion(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const update = () => setReduced(mq.matches);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return reduced;
}

/** 0 when a tall section's top reaches the top of the screen, 1 when its bottom reaches the bottom. */
export function useSectionProgress(ref: RefObject<HTMLElement | null>, enabled: boolean): number {
  const [progress, setProgress] = useState(enabled ? 0 : 1);
  useEffect(() => {
    if (!enabled) {
      setProgress(1);
      return;
    }
    let frame = 0;
    const update = () => {
      frame = 0;
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const span = rect.height - window.innerHeight;
      setProgress(span <= 0 ? (rect.top <= 0 ? 1 : 0) : clamp01(-rect.top / span));
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      cancelAnimationFrame(frame);
    };
  }, [enabled, ref]);
  return progress;
}

/** Chart height that leaves room for the copy inside a one-screen panel. */
export function useChartHeight(share = 0.4, min = 200, max = 360): number {
  const frame = useContext(FrameHeight);
  const [viewport, setViewport] = useState(() => window.innerHeight);
  useEffect(() => {
    if (frame !== null) return;
    const update = () => setViewport(window.innerHeight);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [frame]);
  return Math.round(Math.min(max, Math.max(min, (frame ?? viewport) * share)));
}
