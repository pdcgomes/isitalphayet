import { pct } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { linearScale, niceTicks } from "./scale";

export interface BandBar {
  label: string;
  value: number;
  lo: number;
  hi: number;
}

interface Props {
  bars: BandBar[];
  ariaLabel: string;
  height?: number;
}

/** A vertical bar per band with its 95% interval: green above zero, red below. */
export function BandBars({ bars, ariaLabel, height = 300 }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const m = { top: 12, right: 8, bottom: 28, left: narrow ? 44 : 52 };
  const lo = Math.min(0, ...bars.map((b) => b.lo));
  const hi = Math.max(0, ...bars.map((b) => b.hi));
  const y = linearScale(lo, hi, height - m.bottom, m.top);
  const slot = (width - m.left - m.right) / bars.length;
  const every = narrow ? 4 : 2;
  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        {niceTicks(lo, hi, 5).map((t) => (Math.abs(t) < 1e-12 ? 0 : t)).map((t) => (
          <g key={t}>
            <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} style={{ stroke: "var(--rule)" }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} style={{ fill: "var(--muted)" }}>
              {pct(t)}
            </text>
          </g>
        ))}
        {bars.map((b, i) => {
          const cx = m.left + (i + 0.5) * slot;
          const w = slot * 0.7;
          const color = b.value >= 0 ? "var(--good)" : "var(--cheat)";
          return (
            <g key={b.label}>
              <rect x={cx - w / 2} y={Math.min(y(b.value), y(0))} width={w} height={Math.max(Math.abs(y(b.value) - y(0)), 1)} style={{ fill: color }}>
                <title>{`${b.label}: ${pct(b.value, 1)} per $1 (95% range ${pct(b.lo, 1)} to ${pct(b.hi, 1)})`}</title>
              </rect>
              <line x1={cx} x2={cx} y1={y(b.lo)} y2={y(b.hi)} style={{ stroke: "var(--ink-2)" }} />
              {i % every === 0 && (
                <text x={cx} y={height - 8} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
                  {b.label}
                </text>
              )}
            </g>
          );
        })}
        <line x1={m.left} x2={width - m.right} y1={y(0)} y2={y(0)} style={{ stroke: "var(--ink-2)" }} />
      </svg>
    </figure>
  );
}
