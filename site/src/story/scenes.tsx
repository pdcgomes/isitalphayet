import type { CSSProperties } from "react";
import { CoinFlips } from "../charts/CoinFlips";
import { FeeBars } from "../charts/FeeBars";
import { LineChart } from "../charts/LineChart";
import { LuckyLines } from "../charts/LuckyLines";
import { ParodyDashboard } from "../charts/ParodyDashboard";
import { Underwater } from "../charts/Underwater";
import { Waterfall, type WaterfallBar } from "../charts/Waterfall";
import { REPO_URL } from "../config";
import { data, story } from "../lib/data";
import { longDate, moneyFull, moneyShort, moneyWords, pct, segment } from "../lib/format";
import { variantName, variantPhrase, variantShortName } from "../lib/names";
import { Link } from "../lib/router";
import { useChartHeight } from "./hooks";

export interface SceneProps {
  /** 0 to 1, from scrolling or from the film clock. */
  p: number;
  /** Shorter copy and bigger type for the recorded video. */
  film?: boolean;
}

const [allCheats, noPeek, realFees] = story.steps;
const bh = story.buy_and_hold;
const meta = data.meta;

export const WATERFALL_BARS: WaterfallBar[] = [
  { label: "Every cheat on", value: allCheats.final_value, color: "var(--cheat)" },
  { label: "No peeking", value: noPeek.final_value, color: "var(--warn)" },
  { label: "Real fees", value: realFees.final_value, color: "var(--honest)" },
];

const holdReference = { value: bh.final_value, label: `Just buying and holding: ${moneyShort(bh.final_value)}`, color: "var(--ink)" };

function fade(p: number, start: number, end = start + 0.12): CSSProperties {
  const t = segment(p, start, end);
  return { opacity: t, transform: `translateY(${((1 - t) * 14).toFixed(1)}px)` };
}

function directionalCalls() {
  return story.ai.weekly_calls.filter((c) => c.outcome === "right" || c.outcome === "wrong");
}

export function PitchScene({ p, film, marquee }: SceneProps & { marquee?: number }) {
  const chartHeight = useChartHeight(film ? 0.22 : 0.2, 110, 190);
  return (
    <div className="scene scene-pitch">
      <div className="pitch-top">
        <span className="pitch-kicker neon-cyan">Backtested on real Bitcoin prices since {story.since.slice(0, 4)}</span>
        {!film && (
          <Link to="/claims" className="pitch-skip">
            Skip the act, see the evidence
          </Link>
        )}
      </div>
      <h1 className="pitch-title neon">This AI trading bot turned $1,000 into {moneyWords(allCheats.final_value)}.</h1>
      <ParodyDashboard step={allCheats} dates={story.weeks} progress={segment(p, 0.04, 0.62)} chartHeight={chartHeight} marquee={marquee} />
      <div className="pitch-cta neon-gold" style={fade(p, 0.66)}>
        Full code. Copy it tonight.
      </div>
    </div>
  );
}

export function PeekScene({ p, film }: SceneProps) {
  const h = useChartHeight(film ? 0.3 : 0.34, 210, 330);
  return (
    <div className="scene">
      <p className="reveal-lead" style={fade(p, 0.02, 0.14)}>
        {film
          ? "Every number on that screen is real. Our code made it from real Bitcoin prices. It also cheats in four ways."
          : `Every number on that dashboard is real: our code produced it from real Bitcoin prices. There's no AI in it, just ${variantPhrase(allCheats.variant)}. And it cheats in four ways.`}
      </p>
      <div style={fade(p, 0.22)}>
        <div className="kicker">Cheat 1 of 4</div>
        <h2>It peeks at tomorrow.</h2>
        <p>
          {film
            ? "It trades at each morning's price using that evening's close."
            : `Each day it decided using that day's closing price, then traded at that morning's opening price, hours before the close existed. Make it wait for information that actually existed, and ${moneyFull(allCheats.final_value)} becomes ${moneyFull(noPeek.final_value)}.`}
        </p>
      </div>
      <div style={fade(p, 0.3)}>
        <Waterfall
          bars={WATERFALL_BARS}
          revealed={1 + segment(p, 0.45, 0.82)}
          height={h}
          ariaLabel={`Final value of $1,000: ${moneyFull(allCheats.final_value)} with every cheat on, ${moneyFull(noPeek.final_value)} without peeking.`}
        />
      </div>
      {!film && noPeek.variant !== allCheats.variant && (
        <p className="caption" style={fade(p, 0.8)}>
          With peeking off, the best of our 13 strategies is a different one, {variantPhrase(noPeek.variant)}. A pitch always
          shows whichever did best.
        </p>
      )}
    </div>
  );
}

export function FeesScene({ p, film }: SceneProps) {
  const h = useChartHeight(film ? 0.3 : 0.36, 210, 340);
  const fees = story.fees.scenarios;
  return (
    <div className="scene">
      <div className="kicker">Cheat 2 of 4</div>
      <h2>It pretends trading is free.</h2>
      <p>
        {film
          ? `It assumes ${pct(fees.article, 2)} a trade. A UK retail account pays ${pct(fees.kraken_taker, 2)}.`
          : `The code charges ${pct(fees.article, 2)} a trade. A small UK account at Kraken pays ${pct(fees.kraken_taker, 2)}, including slippage: more than ${Math.floor(fees.kraken_taker / fees.article)} times as much. At real fees, ${moneyFull(noPeek.final_value)} becomes ${moneyFull(realFees.final_value)}, barely ahead of just buying Bitcoin and holding it (${moneyFull(bh.final_value)}).`}
      </p>
      <Waterfall
        bars={WATERFALL_BARS}
        revealed={2 + segment(p, 0.2, 0.62)}
        reference={holdReference}
        height={h}
        ariaLabel={`With real fees, $1,000 ends at ${moneyFull(realFees.final_value)}; buying and holding ends at ${moneyFull(bh.final_value)}.`}
      />
    </div>
  );
}

export function FeeBarsScene({ p }: SceneProps) {
  const rows = story.fees.variants.map((v) => ({
    label: variantName(v.name),
    short: variantShortName(v.name),
    trades: v.trades,
    from: v.cagr_article,
    to: v.cagr_taker,
  }));
  return (
    <div className="scene">
      <h3>All 13 strategies we tried, before and after real fees</h3>
      <p className="muted small">
        Average yearly growth, Aug 2017 to Sep 2026. The dashed outline is the result at the fantasy fee; the bar slides
        to the real one. The more a strategy trades, the more the exchange takes.
      </p>
      <FeeBars
        rows={rows}
        progress={segment(p, 0.12, 0.72)}
        reference={{ value: bh.cagr, label: `Holding: ${pct(bh.cagr)}` }}
        ariaLabel="Yearly growth of all 13 strategies at a 0.08% fee and at a 0.85% fee."
      />
    </div>
  );
}

export function HindsightScene({ p, film }: SceneProps) {
  const h = useChartHeight(film ? 0.3 : 0.36, 210, 340);
  const hs = story.hindsight;
  return (
    <div className="scene">
      <div className="kicker">Cheat 3 of 4</div>
      <h2>It was picked after the race was run.</h2>
      <p>
        {film
          ? `Picked using 2017 to 2022, then run on 2023 to 2026: $1,000 became ${moneyFull(hs.strategy_final_value)}. Just holding made ${moneyFull(hs.buy_and_hold_final_value)}.`
          : `We tried 13 strategies, and a pitch shows whichever did best over the whole period, which you can only know afterwards. Choose using 2017 to 2022 only, then let it trade January 2023 to September 2026, years it never saw: $1,000 became ${moneyFull(hs.strategy_final_value)}. Just holding Bitcoin made ${moneyFull(hs.buy_and_hold_final_value)}.`}
      </p>
      <LineChart
        dates={hs.weeks}
        series={[
          { name: "strategy", values: hs.strategy_growth_weekly, color: "var(--honest)", width: 2.4, endLabel: moneyShort, legend: `${variantName(hs.variant)}, chosen on 2017-2022` },
          { name: "hold", values: hs.buy_and_hold_growth_weekly, color: "var(--ink)", dash: "6 4", endLabel: moneyShort, legend: "Just holding Bitcoin" },
        ]}
        progress={segment(p, 0.2, 0.85)}
        height={h}
        yFormat={moneyShort}
        ariaLabel={`From January 2023, $1,000 in the strategy became ${moneyFull(hs.strategy_final_value)}; holding became ${moneyFull(hs.buy_and_hold_final_value)}.`}
      />
    </div>
  );
}

export function LuckScene({ p, film }: SceneProps) {
  const h = useChartHeight(film ? 0.3 : 0.36, 210, 340);
  const l = story.luck;
  const finals = l.random.map((r) => r.final_value);
  return (
    <div className="scene">
      <div className="kicker">Cheat 4 of 4</div>
      <h2>Luck looks like skill.</h2>
      <p>
        {film
          ? `${l.random.length} strategies trading on coin flips ended anywhere from ${moneyFull(Math.min(...finals))} to ${moneyFull(Math.max(...finals))}.`
          : `These ${l.random.length} strategies buy and sell on coin flips: no skill at all, same fantasy fee. They ended anywhere from ${moneyFull(Math.min(...finals))} to ${moneyFull(Math.max(...finals))}. Test enough ideas and one of them always looks brilliant.`}
      </p>
      <LuckyLines dates={story.weeks} random={l.random} buyAndHold={bh.growth_weekly} progress={segment(p, 0.2, 0.85)} height={h} />
      {!film && (
        <p className="caption">
          Allowing for all {l.trials} strategies we tried, the odds that our best one has a real edge come out at{" "}
          {pct(l.deflated_sharpe)}. We required 95% before we started.
        </p>
      )}
    </div>
  );
}

export function HoldScene({ p, film }: SceneProps) {
  const h = useChartHeight(0.26, 170, 240);
  const years = (bh.longest_drawdown_days / 365).toFixed(1);
  return (
    <div className="scene">
      <h2>So what beat it? Doing nothing.</h2>
      <p>
        Buying Bitcoin once and never touching it turned $1,000 into {moneyFull(bh.final_value)}: about what the bot made
        after real fees, with no work and no trading.
      </p>
      <p>
        <strong>That isn't a recommendation.</strong> At its worst it was {pct(-bh.max_drawdown)} down, and it once spent{" "}
        {years} years below an earlier peak.
      </p>
      <Underwater
        dates={story.weeks}
        values={bh.underwater_weekly}
        progress={segment(p, 0.2, 0.85)}
        height={h}
        ariaLabel={`Buying and holding Bitcoin fell as far as ${pct(bh.max_drawdown)} below its previous peak.`}
      />
      {!film && <p className="caption">How far below its previous high $1,000 of Bitcoin sat, week by week.</p>}
    </div>
  );
}

export function AiScene({ p, film }: SceneProps) {
  const ai = story.ai;
  const calls = directionalCalls();
  const coins = ai.coin_flips;
  const coinRight = coins.filter(Boolean).length;
  const stars = Math.round(story.sources.tradingagents_stars / 1000) * 1000;
  const allNegative = ai.assets.every((a) => a.timing_skill < 0);
  return (
    <div className="scene">
      <h2>“But mine uses AI.”</h2>
      {film ? (
        <p>
          An AI trading agent with about {stars.toLocaleString("en-GB")} GitHub stars made {ai.calls} weekly calls on Bitcoin
          and Ether.{" "}
          <span style={fade(p, 0.82, 0.92)}>
            It got {ai.hits} right. A coin got {coinRight}.
          </span>
        </p>
      ) : (
        <p>
          TradingAgents is an open-source “trading firm made of AI agents” with about {stars.toLocaleString("en-GB")} GitHub
          stars. We let it make {ai.calls} weekly calls on Bitcoin and Ether, on dates after its models' training data ended.
          It got {ai.hits} right. A fair coin got {coinRight}.
        </p>
      )}
      <CoinFlips calls={calls.map((c) => c.outcome === "right")} coins={coins} progress={segment(p, 0.15, 0.8)} seed={ai.coin_seed} />
      {!film && (
        <p className="caption">
          Its calls added nothing beyond holding less on average
          {allNegative ? ": its timing skill was negative on every asset we tested" : ""}. Each decision cost $
          {ai.usd_per_decision.toFixed(3)} and took {ai.minutes_per_decision.toFixed(1)} minutes.
        </p>
      )}
    </div>
  );
}

export function FeedScene() {
  const feed = story.feed;
  return (
    <div className="scene">
      <h2>If it doesn't work, why is it everywhere?</h2>
      <ol className="reasons">
        <li>
          <strong>They're paid for attention.</strong> The post that sent us down this road reached{" "}
          {(feed.views / 1e6).toFixed(2)} million views from an account with {feed.followers.toLocaleString("en-GB")}{" "}
          followers. X pays creators for engagement, so the bait pays whether or not the bot does.
        </li>
        <li>
          <strong>They're paid when you trade.</strong> Many exchanges give referrers a cut of the fees their sign-ups pay.
          More trading means more income for them, whether you win or lose.
        </li>
        <li>
          <strong>You only see the winners.</strong> Thousands of people try strategies like these. The lucky ones post
          screenshots; the rest go quiet.
        </li>
      </ol>
      <p>
        Making a backtest look good took an evening. Making it honest took a pre-registration, {meta.trials} counted
        attempts and a ledger of {meta.runs_logged.toLocaleString("en-GB")} logged runs.
      </p>
    </div>
  );
}

export function SpotScene() {
  return (
    <div className="scene">
      <h2>How to spot it</h2>
      <ol className="checklist">
        <li>
          <strong>Ask how they make money.</strong> Courses, signal groups, referral links and “collabs” pay them for your
          attention and your trading, not for your returns.
        </li>
        <li>
          <strong>Ask for a real-money record over years,</strong> not a backtest or a screenshot.
        </li>
        <li>
          <strong>Check the fees.</strong> Anything that trades often and assumes tiny fees is fiction.
        </li>
        <li>
          <strong>Distrust smooth curves.</strong> A Sharpe ratio above 2 on crypto usually means the test peeked.
        </li>
        <li>
          <strong>In the UK,</strong> anyone offering crypto leverage or “futures bots” to ordinary customers is, according to
          the FCA, likely to be a scam.
        </li>
      </ol>
    </div>
  );
}

export function VerdictScene({ film }: SceneProps) {
  return (
    <div className="scene verdict">
      <div className="verdict-q">Is it alpha yet?</div>
      <div className="verdict-a">No.</div>
      <p className="verdict-sub">
        {meta.claims_tested} viral claims tested. {meta.claims_passed} passed. We'll keep testing new ones as they spread.
      </p>
      {film ? (
        <p className="verdict-url">isitalphayet.com</p>
      ) : (
        <>
          <nav className="verdict-links">
            <Link to="/claims">Every claim we tested</Link>
            <Link to="/live">The live forward test</Link>
            <Link to="/method">How we tested</Link>
            {REPO_URL && <a href={`${REPO_URL}/issues/new`}>Suggest a claim</a>}
          </nav>
          <p className="small muted">
            Education, not financial advice. Every number here comes from code anyone can rerun. Pre-registered{" "}
            {longDate(meta.preregistered_at)}, SHA-256 <code>{meta.preregistration_sha256.slice(0, 12)}</code>.
          </p>
        </>
      )}
    </div>
  );
}
