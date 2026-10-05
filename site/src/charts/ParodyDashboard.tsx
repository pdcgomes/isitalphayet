import { easeOut, moneyFull, pct } from "../lib/format";
import type { Step } from "../lib/types";
import { LineChart } from "./LineChart";

interface Props {
  step: Step;
  dates: string[];
  /** 0 to 1: the count-up and the equity curve both follow it. */
  progress?: number;
  chartHeight?: number;
  /** Fixes the ticker position (0 to 1) instead of animating it, for frame-by-frame film rendering. */
  marquee?: number;
}

const STRATEGY_LABELS: Record<string, string> = {
  "tsmom(lookback=14)": "AI MOMENTUM ENGINE · 14D",
  "trend(n=50)": "AI TREND ENGINE · 50D",
};

/** The kind of dashboard the bot accounts post. Every number on it is real; the trick is how it was made. */
export function ParodyDashboard({ step, dates, progress = 1, chartHeight = 190, marquee }: Props) {
  const t = easeOut(progress);
  // Count up geometrically, so the climb from $1,000 to millions feels like the chart.
  const value = 1000 * Math.pow(step.final_value / 1000, t);
  return (
    <div className="parody" aria-label={`Parody trading-bot dashboard: $1,000 grows to ${moneyFull(step.final_value)}.`}>
      <div className="parody-bar">
        <span className="parody-brand">ALPHA·BOT 9000</span>
        <span className="parody-live">
          <i /> LIVE BACKTEST
        </span>
        <span className="parody-dim">{STRATEGY_LABELS[step.variant] ?? step.variant.toUpperCase()}</span>
      </div>
      <div className="parody-hero">
        <div className="parody-from">$1,000 since {dates[0].slice(0, 4)}</div>
        <div className="parody-value neon">{moneyFull(value)}</div>
        <div className="parody-gain neon-gold">+{Math.round((value / 1000 - 1) * 100).toLocaleString("en-GB")}%</div>
      </div>
      <div className="parody-tiles">
        <div>
          <b className="neon">{`+${pct(step.cagr)}`}</b>
          <span>per year</span>
        </div>
        <div>
          <b className="neon-cyan">{step.sharpe.toFixed(2)}</b>
          <span>Sharpe</span>
        </div>
        <div>
          <b className="neon">{pct(step.win_rate)}</b>
          <span>win rate</span>
        </div>
        <div>
          <b className="neon-red">{pct(step.max_drawdown)}</b>
          <span>worst drop</span>
        </div>
      </div>
      <LineChart
        dates={dates}
        series={[{ name: "Bot", values: step.growth_weekly, color: "var(--neon)", width: 2.4, glow: true, legend: null }]}
        ariaLabel="The bot's equity curve, rising almost straight up on a log scale."
        log
        height={chartHeight}
        progress={t}
        mood="hype"
        yFormat={(v) => (v >= 1e6 ? `$${v / 1e6}M` : v >= 1e3 ? `$${v / 1e3}K` : `$${v}`)}
      />
      <div className="parody-marquee" aria-hidden="true">
        <span style={marquee === undefined ? undefined : { animation: "none", transform: `translateX(${-50 * marquee}%)` }}>
          FULL CODE IN BIO · COPY IT TONIGHT · {pct(step.win_rate)} WIN RATE · SHARPE {step.sharpe.toFixed(2)} · NOT FINANCIAL ADVICE ·
          FULL CODE IN BIO · COPY IT TONIGHT · {pct(step.win_rate)} WIN RATE · SHARPE {step.sharpe.toFixed(2)} · NOT FINANCIAL ADVICE ·
        </span>
      </div>
    </div>
  );
}
