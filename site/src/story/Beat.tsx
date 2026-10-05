import { useRef, type CSSProperties, type ReactNode } from "react";
import { useReducedMotion, useSectionProgress } from "./hooks";

interface Props {
  id: string;
  /** Section height in screens. Above 1, the panel pins and scrolling drives progress. */
  length?: number;
  mood?: "hype" | "calm";
  style?: (progress: number) => CSSProperties;
  children: (progress: number) => ReactNode;
}

export function Beat({ id, length = 2, mood = "calm", style, children }: Props) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();
  const pinned = length > 1 && !reduced;
  const progress = useSectionProgress(ref, pinned);
  const p = pinned ? progress : 1;
  return (
    <section
      ref={ref}
      id={id}
      className={`beat beat-${mood}${pinned ? " beat-pinned" : ""}`}
      style={{ ...(pinned ? { height: `${length * 100}vh` } : {}), ...style?.(p) }}
    >
      <div className="beat-panel" style={style?.(p)}>
        <div className="beat-inner">{children(p)}</div>
      </div>
    </section>
  );
}
