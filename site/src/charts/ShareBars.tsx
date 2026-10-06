import { pct } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { linearScale } from "./scale";

export interface ShareRow {
  label: string;
  /** Used on narrow screens. */
  short: string;
  value: number;
  /** Indented under the row above. */
  sub?: boolean;
}

interface Props {
  rows: ShareRow[];
  ariaLabel: string;
}

/** Horizontal bars from 0 to 100%, with a line at half. Red where more than half. */
export function ShareBars({ rows, ariaLabel }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const rowH = 28;
  const m = { top: 22, right: 44, bottom: 6, left: narrow ? 128 : 260 };
  const height = m.top + rows.length * rowH + m.bottom;
  const x = linearScale(0, 1, m.left, width - m.right);
  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        <line x1={x(0.5)} x2={x(0.5)} y1={m.top - 6} y2={height - m.bottom} strokeDasharray="4 4" style={{ stroke: "var(--hold)" }} />
        <text x={x(0.5)} y={m.top - 10} textAnchor="middle" fontSize={11} style={{ fill: "var(--hold)" }}>
          Half
        </text>
        {rows.map((r, i) => {
          const yTop = m.top + i * rowH + 5;
          const h = rowH - 10;
          const color = r.value > 0.5 ? "var(--cheat)" : "var(--honest)";
          return (
            <g key={r.label}>
              <text x={m.left - 10} y={yTop + h / 2} dy="0.32em" textAnchor="end" fontSize={narrow ? 11.5 : 12.5} style={{ fill: r.sub ? "var(--muted)" : "var(--ink-2)" }}>
                {narrow ? r.short : r.label}
              </text>
              <rect x={x(0)} y={yTop} width={x(r.value) - x(0)} height={h} style={{ fill: color }} opacity={r.sub ? 0.75 : 1} />
              <text x={x(r.value) + 5} y={yTop + h / 2} dy="0.32em" fontSize={12} fontWeight={600} style={{ fill: color }}>
                {pct(r.value)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
