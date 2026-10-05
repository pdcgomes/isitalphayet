import { CoinFlips } from "../charts/CoinFlips";
import { FeeBars } from "../charts/FeeBars";
import { LineChart } from "../charts/LineChart";
import { LuckyLines } from "../charts/LuckyLines";
import { ParodyDashboard } from "../charts/ParodyDashboard";
import { Underwater } from "../charts/Underwater";
import { Waterfall } from "../charts/Waterfall";
import { story } from "../lib/data";
import { moneyShort, pct } from "../lib/format";
import { variantName, variantShortName } from "../lib/names";
/** Every chart at full progress, for checking the chart kit by eye. Not linked from the site. */
export default function Gallery() {
  const directional = story.ai.weekly_calls.filter((c) => c.outcome === "right" || c.outcome === "wrong");
  const bh = story.buy_and_hold;
  return (
    <main className="page">
      <h1>Chart kit</h1>
      <div className="hype" style={{ padding: "1rem", borderRadius: 16 }}>
        <ParodyDashboard step={story.steps[0]} dates={story.weeks} />
      </div>
      <h2>Waterfall</h2>
      <Waterfall
        ariaLabel="test"
        bars={story.steps.map((s, i) => ({ label: s.label, value: s.final_value, color: ["var(--cheat)", "#d9822b", "var(--honest)"][i] }))}
        reference={{ value: bh.final_value, label: `Just holding: ${moneyShort(bh.final_value)}`, color: "var(--ink)" }}
      />
      <h2>Equity</h2>
      <LineChart
        ariaLabel="test"
        dates={story.weeks}
        log
        yFormat={moneyShort}
        series={[
          { name: "Bot with real fees", values: story.steps[2].growth_weekly, color: "var(--honest)", endLabel: moneyShort },
          { name: "Just holding", values: bh.growth_weekly, color: "var(--ink)", dash: "6 4", endLabel: moneyShort },
        ]}
      />
      <h2>Fees</h2>
      <FeeBars
        ariaLabel="test"
        rows={story.fees.variants.map((v) => ({ label: variantName(v.name), short: variantShortName(v.name), trades: v.trades, from: v.cagr_article, to: v.cagr_taker }))}
        reference={{ value: bh.cagr, label: `Holding ${pct(bh.cagr)}` }}
      />
      <h2>Luck</h2>
      <LuckyLines dates={story.weeks} random={story.luck.random} buyAndHold={bh.growth_weekly} />
      <h2>Coins</h2>
      <CoinFlips calls={directional.map((c) => c.outcome === "right")} coins={story.ai.coin_flips} seed={story.ai.coin_seed} />
      <h2>Underwater</h2>
      <Underwater ariaLabel="test" dates={story.weeks} values={bh.underwater_weekly} />
    </main>
  );
}
