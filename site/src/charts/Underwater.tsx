import { useId } from "react";
import { clamp01, pct } from "../lib/format";
import { useMeasure } from "../lib/useMeasure";
import { linearScale, safeId, spacedYearTicks } from "./scale";

interface Props {
  dates: string[];
  /** Fall from the previous peak, 0 to -1, one value per date. */
  values: number[];
  ariaLabel: string;
  progress?: number;
  height?: number;
}

/** How far below its previous high the investment sat, week by week. */
export function Underwater({ dates, values, ariaLabel, progress = 1, height = 220 }: Props) {
  const id = safeId(useId());
  const [ref, width] = useMeasure<HTMLDivElement>();
  const narrow = width < 520;
  const m = { top: 12, right: 14, bottom: 28, left: narrow ? 46 : 60 };
  const innerW = width - m.left - m.right;
  const worst = Math.min(...values);
  const worstAt = values.indexOf(worst);
  const x = linearScale(0, values.length - 1, m.left, m.left + innerW);
  const y = linearScale(Math.min(-1, worst), 0, height - m.bottom, m.top);
  const shown = clamp01(progress);
  const area =
    `M${x(0)},${y(0)}` + values.map((v, i) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("") + `L${x(values.length - 1)},${y(0)}Z`;
  const years = spacedYearTicks(dates, x, narrow ? 52 : 44);

  return (
    <figure className="chart" ref={ref}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        <defs>
          <clipPath id={`uw-${id}`}>
            <rect x={0} y={0} width={m.left + innerW * shown + 1} height={height} />
          </clipPath>
        </defs>
        {[0, -0.25, -0.5, -0.75, -1].map((t) => (
          <g key={t}>
            <line x1={m.left} x2={m.left + innerW} y1={y(t)} y2={y(t)} style={{ stroke: "var(--rule)" }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} style={{ fill: "var(--muted)" }}>
              {pct(t)}
            </text>
          </g>
        ))}
        {years.map((t) => (
          <text key={t.label} x={x(t.index)} y={height - 8} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
            {t.label}
          </text>
        ))}
        <path d={area} clipPath={`url(#uw-${id})`} style={{ fill: "var(--cheat)", opacity: 0.78 }} />
        {shown * (values.length - 1) >= worstAt && (
          <text x={x(worstAt)} y={y(worst) + 16} textAnchor="middle" fontSize={13} fontWeight={700} style={{ fill: "var(--cheat)" }}>
            {pct(worst)}
          </text>
        )}
      </svg>
    </figure>
  );
}
