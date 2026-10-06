import { useMeasure } from "../lib/useMeasure";
import { linearScale, niceTicks } from "./scale";

export interface BarSeries {
  name: string;
  color: string;
  values: number[];
}

interface Props {
  categories: string[];
  series: BarSeries[];
  ariaLabel: string;
  yFormat: (v: number) => string;
  height?: number;
  /** Vertical dotted markers between categories: `at` is a fractional category index. */
  markers?: { at: number; label: string }[];
  /** Show every nth category label (long time axes on phones). */
  labelEvery?: number;
}

/** Vertical bars, one group per category. */
export function GroupedBars({ categories, series, ariaLabel, yFormat, height = 300, markers = [], labelEvery = 1 }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const m = { top: 14, right: 10, bottom: 28, left: narrow ? 44 : 56 };
  const hi = Math.max(...series.flatMap((s) => s.values), 0) * 1.05 || 1;
  const y = linearScale(0, hi, height - m.bottom, m.top);
  const slot = (width - m.left - m.right) / categories.length;
  const barW = Math.max(2, (slot * 0.78) / series.length);
  const every = narrow ? Math.max(labelEvery, Math.ceil(categories.length / 6)) : labelEvery;
  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        {niceTicks(0, hi, 4).map((t) => (
          <g key={t}>
            <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} style={{ stroke: "var(--rule)" }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} style={{ fill: "var(--muted)" }}>
              {yFormat(t)}
            </text>
          </g>
        ))}
        {markers.map((mk) => (
          <line key={mk.label} x1={m.left + mk.at * slot} x2={m.left + mk.at * slot} y1={m.top} y2={height - m.bottom} strokeDasharray="2 4" style={{ stroke: "var(--muted)" }}>
            <title>{mk.label}</title>
          </line>
        ))}
        {categories.map((c, i) => {
          const left = m.left + i * slot + (slot - barW * series.length) / 2;
          return (
            <g key={c}>
              {series.map((s, k) =>
                s.values[i] > 0 ? (
                  <rect key={s.name} x={left + k * barW} y={y(s.values[i])} width={barW - 1} height={y(0) - y(s.values[i])} style={{ fill: s.color }}>
                    <title>{`${s.name}, ${c}: ${yFormat(s.values[i])}`}</title>
                  </rect>
                ) : null,
              )}
              {i % every === 0 && (
                <text x={m.left + (i + 0.5) * slot} y={height - 8} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
                  {c}
                </text>
              )}
            </g>
          );
        })}
        <line x1={m.left} x2={width - m.right} y1={y(0)} y2={y(0)} style={{ stroke: "var(--ink-2)" }} />
      </svg>
      {series.length > 1 && (
        <figcaption className="legend">
          {series.map((s) => (
            <span key={s.name}>
              <i style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
