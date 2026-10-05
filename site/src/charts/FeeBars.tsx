import { clamp01, pct } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { linearScale } from "./scale";

export interface FeeRow {
  label: string;
  /** Used on narrow screens. */
  short: string;
  trades: number;
  from: number;
  to: number;
}

interface Props {
  rows: FeeRow[];
  ariaLabel: string;
  /** 0 shows every bar at the fantasy fee; 1 at the real fee. */
  progress?: number;
  reference?: { value: number; label: string };
}

/** Annual growth per strategy, sliding from the fantasy fee to the real one. The outline marks where it started. */
export function FeeBars({ rows, ariaLabel, progress = 1, reference }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  // Full names only where they fit; short names, with trade counts when there is room for them.
  const labels = narrow ? "short" : width < 760 ? "medium" : "full";
  const rowH = narrow ? 30 : 28;
  const m = { top: 24, right: 52, bottom: 8, left: { short: 104, medium: 176, full: 216 }[labels] };
  const height = m.top + rows.length * rowH + m.bottom;
  const lo0 = Math.min(-0.1, ...rows.map((r) => Math.min(r.from, r.to)));
  const hi = Math.max(0.1, ...rows.map((r) => Math.max(r.from, r.to)), reference?.value ?? 0);
  // Leave room left of the most negative bar for its value label (about 42px).
  const lo = lo0 - ((hi - lo0) * 42) / Math.max(width - m.left - m.right - 42, 1);
  const x = linearScale(lo, hi, m.left, width - m.right);
  const t = clamp01(progress);

  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        <line x1={x(0)} x2={x(0)} y1={m.top - 6} y2={height - m.bottom} style={{ stroke: "var(--ink-2)" }} />
        {(!reference || Math.abs(x(reference.value) - x(0)) > 90) && (
          <text x={x(0)} y={m.top - 10} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
            0%
          </text>
        )}
        {reference && (
          <g>
            <line x1={x(reference.value)} x2={x(reference.value)} y1={m.top - 6} y2={height - m.bottom} strokeDasharray="5 4" style={{ stroke: "var(--hold)" }} />
            <text x={x(reference.value)} y={m.top - 10} textAnchor="middle" fontSize={11} fontWeight={600} style={{ fill: "var(--hold)" }}>
              {reference.label}
            </text>
          </g>
        )}
        {rows.map((r, i) => {
          const yTop = m.top + i * rowH + 5;
          const h = rowH - 10;
          const v = r.from + (r.to - r.from) * t;
          const ghost = [x(Math.min(0, r.from)), x(Math.max(0, r.from))];
          const bar = [x(Math.min(0, v)), x(Math.max(0, v))];
          return (
            <g key={r.label}>
              <text x={m.left - 10} y={yTop + h / 2} dy="0.32em" textAnchor="end" fontSize={narrow ? 11.5 : 12.5} style={{ fill: "var(--ink-2)" }}>
                {labels === "full" ? r.label : r.short}
                <tspan style={{ fill: "var(--muted)" }}>{labels === "short" ? "" : ` · ${r.trades} trades`}</tspan>
              </text>
              <rect x={ghost[0]} y={yTop} width={ghost[1] - ghost[0]} height={h} fill="none" strokeDasharray="3 3" style={{ stroke: "var(--muted)" }} />
              <rect x={bar[0]} y={yTop} width={Math.max(bar[1] - bar[0], 1)} height={h} style={{ fill: v >= 0 ? "var(--honest)" : "var(--cheat)" }} />
              <text x={v >= 0 ? bar[1] + 5 : bar[0] - 5} y={yTop + h / 2} dy="0.32em" textAnchor={v >= 0 ? "start" : "end"} fontSize={12} fontWeight={600} style={{ fill: v >= 0 ? "var(--honest)" : "var(--cheat)" }}>
                {pct(v)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
