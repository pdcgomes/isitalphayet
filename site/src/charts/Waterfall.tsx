import { clamp01, moneyShort } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { logScale, logTicks } from "./scale";

export interface WaterfallBar {
  label: string;
  value: number;
  color: string;
}

interface Props {
  bars: WaterfallBar[];
  ariaLabel: string;
  /** How many bars are shown; fractions grow the next bar. */
  revealed?: number;
  reference?: { value: number; label: string; color: string };
  height?: number;
  start?: number;
}

/** Final value of 1,000 at each step, on a log scale so $296M and $20K fit on one chart. */
export function Waterfall({ bars, ariaLabel, revealed = bars.length, reference, height = 360, start = 1000 }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const m = { top: 30, right: 16, bottom: narrow ? 64 : 54, left: narrow ? 46 : 60 };
  const innerW = width - m.left - m.right;
  const innerH = height - m.top - m.bottom;
  const hi = Math.max(...bars.map((b) => b.value), reference?.value ?? 0) * 1.5;
  const y = logScale(start, hi, m.top + innerH, m.top);
  const slot = innerW / bars.length;
  const barW = Math.min(slot * 0.62, 120);

  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        {logTicks(start, hi).map((t) => (
          <g key={t}>
            <line x1={m.left} x2={m.left + innerW} y1={y(t)} y2={y(t)} style={{ stroke: "var(--rule)" }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} style={{ fill: "var(--muted)" }}>
              {moneyShort(t)}
            </text>
          </g>
        ))}
        {bars.map((b, i) => {
          const grow = clamp01(revealed - i);
          if (grow <= 0) return null;
          // Grow on the log scale, so each bar rises like the money it represents.
          const v = Math.exp(Math.log(start) + (Math.log(b.value) - Math.log(start)) * grow);
          const cx = m.left + slot * (i + 0.5);
          const top = y(v);
          return (
            <g key={b.label}>
              <rect x={cx - barW / 2} y={top} width={barW} height={m.top + innerH - top} rx={3} style={{ fill: b.color }} />
              <text x={cx} y={top - 8} textAnchor="middle" fontSize={narrow ? 13 : 15} fontWeight={700} style={{ fill: "var(--ink)" }}>
                {moneyShort(v)}
              </text>
              <foreignObject x={cx - slot / 2} y={m.top + innerH + 6} width={slot} height={m.bottom - 6}>
                <div className="bar-label">{b.label}</div>
              </foreignObject>
            </g>
          );
        })}
        {reference && (
          <line
            x1={m.left}
            x2={m.left + innerW}
            y1={y(reference.value)}
            y2={y(reference.value)}
            strokeDasharray="6 5"
            strokeWidth={1.5}
            style={{ stroke: reference.color }}
          />
        )}
      </svg>
      {reference && (
        <figcaption className="legend">
          <span>
            <i className="dash" style={{ borderColor: reference.color }} />
            {reference.label}
          </span>
        </figcaption>
      )}
    </figure>
  );
}
