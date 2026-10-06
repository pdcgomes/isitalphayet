import { useMeasure } from "../lib/useMeasure";
import { linearScale, niceTicks } from "./scale";

export interface RangePoint {
  value: number;
  lo?: number;
  hi?: number;
  color: string;
}

export interface RangeRow {
  label: string;
  points: RangePoint[];
  /** A shaded range drawn behind the points, e.g. what luck alone produces. */
  band?: [number, number];
  /** Text after the row, e.g. the point's value. */
  note?: string;
}

interface Props {
  rows: RangeRow[];
  ariaLabel: string;
  format: (v: number) => string;
  legend?: { label: string; color: string; shaded?: boolean }[];
}

/** One row per item: a dot for the estimate, a line for its interval, an optional shaded band behind. */
export function RangeDots({ rows, ariaLabel, format, legend }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const perPoint = 14;
  // On phones each label sits above its row, so long labels never get cut off.
  const labelH = narrow ? 18 : 0;
  const rowH = Math.max(34, rows.reduce((n, r) => Math.max(n, r.points.length), 1) * perPoint + 18) + labelH;
  const m = { top: 8, right: narrow ? 52 : 72, bottom: 28, left: narrow ? 8 : 168 };
  const height = m.top + rows.length * rowH + m.bottom;
  const all = rows.flatMap((r) => [...r.points.flatMap((p) => [p.value, p.lo ?? p.value, p.hi ?? p.value]), ...(r.band ?? [])]);
  const lo = Math.min(0, ...all);
  const hi = Math.max(0, ...all);
  const pad = (hi - lo) * 0.04;
  const x = linearScale(lo - pad, hi + pad, m.left, width - m.right);
  const ticks = niceTicks(lo, hi, narrow ? 3 : 5).map((t) => (Math.abs(t) < 1e-12 ? 0 : t));
  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={m.top} y2={height - m.bottom} style={{ stroke: "var(--rule)" }} />
            <text x={x(t)} y={height - 8} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
              {format(t)}
            </text>
          </g>
        ))}
        <line x1={x(0)} x2={x(0)} y1={m.top} y2={height - m.bottom} style={{ stroke: "var(--ink-2)" }} />
        {rows.map((r, i) => {
          const mid = m.top + i * rowH + labelH + (rowH - labelH) / 2;
          const offset = (k: number) => (k - (r.points.length - 1) / 2) * perPoint;
          return (
            <g key={r.label}>
              {narrow ? (
                <text x={m.left} y={m.top + i * rowH + 12} fontSize={11.5} fontWeight={600} style={{ fill: "var(--ink-2)" }}>
                  {r.label}
                </text>
              ) : (
                <text x={m.left - 10} y={mid} dy="0.32em" textAnchor="end" fontSize={12.5} style={{ fill: "var(--ink-2)" }}>
                  {r.label}
                </text>
              )}
              {r.band && (
                <rect x={x(r.band[0])} y={mid - 7} width={Math.max(x(r.band[1]) - x(r.band[0]), 2)} height={14} rx={7} style={{ fill: "var(--rule)" }} />
              )}
              {r.points.map((p, k) => (
                <g key={k}>
                  {p.lo !== undefined && p.hi !== undefined && (
                    <line x1={x(p.lo)} x2={x(p.hi)} y1={mid + offset(k)} y2={mid + offset(k)} strokeWidth={2} strokeLinecap="round" opacity={0.55} style={{ stroke: p.color }} />
                  )}
                  <circle cx={x(p.value)} cy={mid + offset(k)} r={5} style={{ fill: p.color }} />
                </g>
              ))}
              {r.note && (
                <text x={width - m.right + 8} y={mid} dy="0.32em" fontSize={12} fontWeight={600} style={{ fill: "var(--ink-2)" }}>
                  {r.note}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {legend && (
        <figcaption className="legend">
          {legend.map((l) => (
            <span key={l.label}>
              <i style={{ background: l.color, borderRadius: l.shaded ? 3 : "50%" }} />
              {l.label}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
