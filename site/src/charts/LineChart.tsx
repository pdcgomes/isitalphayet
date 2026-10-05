import { useId } from "react";
import { clamp01 } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { linearScale, logScale, logTicks, niceTicks, safeId, spacedYearTicks } from "./scale";

export interface LineSeries {
  name: string;
  values: number[];
  color: string;
  width?: number;
  dash?: string;
  opacity?: number;
  /** Text drawn where the line currently ends; receives the value at that point. */
  endLabel?: (value: number) => string;
  /** Legend text; null hides the series from the legend. Defaults to name. */
  legend?: string | null;
  glow?: boolean;
}

interface Props {
  dates: string[];
  series: LineSeries[];
  ariaLabel: string;
  log?: boolean;
  height?: number;
  /** 0 to 1: how much of the time axis is drawn. */
  progress?: number;
  yFormat?: (v: number) => string;
  yDomain?: [number, number];
  reference?: { value: number; label: string; color: string };
  mood?: "calm" | "hype";
  yLabel?: string;
}

export function LineChart({
  dates,
  series,
  ariaLabel,
  log = false,
  height = 340,
  progress = 1,
  yFormat = String,
  yDomain,
  reference,
  mood = "calm",
  yLabel,
}: Props) {
  const id = safeId(useId());
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const labelled = series.filter((s) => s.endLabel);
  const m = { top: 16, right: labelled.length ? (narrow ? 84 : 132) : 14, bottom: 28, left: narrow ? 46 : 60 };
  const innerW = width - m.left - m.right;
  const innerH = height - m.top - m.bottom;

  const values = series.flatMap((s) => s.values).filter((v) => Number.isFinite(v) && (!log || v > 0));
  const lo = yDomain?.[0] ?? Math.min(...values, reference?.value ?? Infinity);
  const hi = yDomain?.[1] ?? Math.max(...values, reference?.value ?? -Infinity);
  const n = dates.length;
  const x = linearScale(0, Math.max(n - 1, 1), m.left, m.left + innerW);
  const y = log ? logScale(lo, hi, m.top + innerH, m.top) : linearScale(lo, hi, m.top + innerH, m.top);
  const yTicks = log ? logTicks(lo, hi) : niceTicks(lo, hi, narrow ? 4 : 5);
  const years = spacedYearTicks(dates, x, narrow ? 52 : 44);
  const shown = clamp01(progress);
  const last = Math.max(0, Math.round((n - 1) * shown));
  const colors =
    mood === "hype"
      ? { grid: "rgba(61, 255, 143, 0.13)", text: "rgba(230, 255, 240, 0.62)" }
      : { grid: "var(--rule)", text: "var(--muted)" };

  const path = (vals: number[]) =>
    vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(log ? Math.max(v, lo) : v).toFixed(1)}`).join("");

  // Nudge end labels apart so they never overlap.
  // Until the lines have some length their end labels would sit on top of each other.
  const ends = (shown < 0.12 ? [] : labelled)
    .map((s) => ({ s, yPos: y(log ? Math.max(s.values[last], lo) : s.values[last]) }))
    .sort((a, b) => a.yPos - b.yPos);
  for (let i = 1; i < ends.length; i++) ends[i].yPos = Math.max(ends[i].yPos, ends[i - 1].yPos + 16);

  const legend = series.filter((s) => s.legend !== null);
  return (
    <figure className={`chart chart-${mood}`} ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        <defs>
          <clipPath id={`clip-${id}`}>
            <rect x={0} y={0} width={m.left + innerW * shown + 1} height={height} />
          </clipPath>
        </defs>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={m.left} x2={m.left + innerW} y1={y(t)} y2={y(t)} style={{ stroke: colors.grid }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={narrow ? 11 : 12} style={{ fill: colors.text }}>
              {yFormat(t)}
            </text>
          </g>
        ))}
        {yLabel && (
          <text x={m.left} y={10} fontSize={11} style={{ fill: colors.text }}>
            {yLabel}
          </text>
        )}
        {years.map((t) => (
          <text key={t.label} x={x(t.index)} y={height - 8} textAnchor="middle" fontSize={narrow ? 11 : 12} style={{ fill: colors.text }}>
            {t.label}
          </text>
        ))}
        {reference && (
          <g>
            <line
              x1={m.left}
              x2={m.left + innerW}
              y1={y(reference.value)}
              y2={y(reference.value)}
              strokeDasharray="5 5"
              style={{ stroke: reference.color }}
            />
            <text x={m.left + 6} y={y(reference.value) - 6} fontSize={12} style={{ fill: reference.color }}>
              {reference.label}
            </text>
          </g>
        )}
        <g clipPath={`url(#clip-${id})`}>
          {series.map((s) => (
            <path
              key={s.name}
              d={path(s.values)}
              fill="none"
              strokeWidth={s.width ?? 2}
              strokeDasharray={s.dash}
              opacity={s.opacity ?? 1}
              strokeLinejoin="round"
              strokeLinecap="round"
              className={s.glow ? "glow-line" : undefined}
              style={{ stroke: s.color }}
            />
          ))}
        </g>
        {ends.map(({ s, yPos }) => (
          <text key={s.name} x={x(last) + 8} y={yPos} dy="0.32em" fontSize={narrow ? 12 : 13} fontWeight={600} style={{ fill: s.color }}>
            {s.endLabel!(s.values[last])}
          </text>
        ))}
      </svg>
      {legend.length > 1 && (
        <figcaption className="legend">
          {legend.map((s) => (
            <span key={s.name}>
              <i style={{ background: s.color }} />
              {s.legend ?? s.name}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
