import { useMeasure } from "../lib/useMeasure";
import { linearScale } from "./scale";

export interface CalibrationSeries {
  name: string;
  color: string;
  points: { price: number; won: number }[];
}

interface Props {
  series: CalibrationSeries[];
  ariaLabel: string;
}

const TICKS = [0, 0.25, 0.5, 0.75, 1];
const cents = (v: number) => `${Math.round(v * 100)}¢`;
const percent = (v: number) => `${Math.round(v * 100)}%`;

/** Price paid against the share that won. On the dashed diagonal, prices are the real odds. */
export function Calibration({ series, ariaLabel }: Props) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const size = Math.min(width, 440);
  const m = { top: 12, right: 12, bottom: 40, left: 48 };
  const x = linearScale(0, 1, m.left, size - m.right);
  const y = linearScale(0, 1, size - m.bottom, m.top);
  return (
    <figure className="chart" ref={ref}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={ariaLabel}>
        <title>{ariaLabel}</title>
        {TICKS.map((t) => (
          <g key={t}>
            <line x1={x(0)} x2={x(1)} y1={y(t)} y2={y(t)} style={{ stroke: "var(--rule)" }} />
            <text x={m.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} style={{ fill: "var(--muted)" }}>
              {percent(t)}
            </text>
            <text x={x(t)} y={size - m.bottom + 16} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
              {cents(t)}
            </text>
          </g>
        ))}
        <text x={(x(0) + x(1)) / 2} y={size - 6} textAnchor="middle" fontSize={11} style={{ fill: "var(--muted)" }}>
          Price paid
        </text>
        <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} strokeDasharray="5 5" style={{ stroke: "var(--hold)" }} />
        {series.map((s) => (
          <g key={s.name}>
            <path
              d={s.points.map((p, i) => `${i ? "L" : "M"}${x(p.price).toFixed(1)},${y(p.won).toFixed(1)}`).join("")}
              fill="none"
              strokeWidth={1.8}
              style={{ stroke: s.color }}
            />
            {s.points.map((p) => (
              <circle key={p.price} cx={x(p.price)} cy={y(p.won)} r={3} style={{ fill: s.color }}>
                <title>{`${s.name}: paid ${cents(p.price)}, won ${percent(p.won)}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <figcaption className="legend">
        {series.map((s) => (
          <span key={s.name}>
            <i style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
        <span>
          <i style={{ background: "var(--hold)" }} />
          Price equals the real odds
        </span>
      </figcaption>
    </figure>
  );
}
