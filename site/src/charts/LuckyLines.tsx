import { moneyShort } from "../lib/format";
import type { RandomStrategy } from "../lib/types";
import { LineChart, type LineSeries } from "./LineChart";

interface Props {
  dates: string[];
  random: RandomStrategy[];
  buyAndHold: number[];
  progress?: number;
  height?: number;
}

/** Thirteen strategies that trade on coin flips. The best of them looks like skill. */
export function LuckyLines({ dates, random, buyAndHold, progress = 1, height = 340 }: Props) {
  const best = random.reduce((a, b) => (b.final_value > a.final_value ? b : a));
  const worst = random.reduce((a, b) => (b.final_value < a.final_value ? b : a));
  const series: LineSeries[] = [
    ...random
      .filter((r) => r !== best && r !== worst)
      .map((r, i) => ({
        name: r.name,
        values: r.growth_weekly,
        color: "var(--hold)",
        width: 1,
        opacity: 0.55,
        legend: i === 0 ? `${random.length - 2} other coin-flip strategies` : null,
      })),
    { name: worst.name, values: worst.growth_weekly, color: "var(--muted)", width: 1.6, legend: "Unluckiest coin flip", endLabel: moneyShort },
    { name: best.name, values: best.growth_weekly, color: "var(--cheat)", width: 2.4, legend: "Luckiest coin flip", endLabel: moneyShort },
    { name: "Buy and hold", values: buyAndHold, color: "var(--ink)", width: 2, dash: "6 4", legend: "Just holding", endLabel: moneyShort },
  ];
  return (
    <LineChart
      dates={dates}
      series={series}
      log
      height={height}
      progress={progress}
      yFormat={moneyShort}
      ariaLabel={`Thirteen coin-flip strategies ended between ${moneyShort(worst.final_value)} and ${moneyShort(best.final_value)}; buying and holding ended at ${moneyShort(buyAndHold[buyAndHold.length - 1])}.`}
    />
  );
}
