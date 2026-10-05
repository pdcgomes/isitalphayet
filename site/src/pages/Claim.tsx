import { useState } from "react";
import { CoinFlips } from "../charts/CoinFlips";
import { LineChart } from "../charts/LineChart";
import { Shell, Stat, Verdict } from "../components/Shell";
import { data, story } from "../lib/data";
import { longDate, moneyShort, pct, signedPct } from "../lib/format";
import { variantName, variantPhrase } from "../lib/names";
import { Link } from "../lib/router";
import type { Ai, Audit, Call, Claim, FamilyBlock, FeeKey, Story } from "../lib/types";
import NotFound from "./NotFound";

const FEE_LABEL: Record<FeeKey, string> = {
  article: "0.08% a trade (the X article)",
  kraken_maker: "0.45% (Kraken maker)",
  kraken_taker: "0.85% (Kraken taker)",
};
const GATE_KEYS = ["out_of_sample", "deflated_sharpe", "walk_forward", "eth_holdout"] as const;

function PassFail({ ok }: { ok: boolean }) {
  return <span className={ok ? "pass" : "fail"}>{ok ? "Passed" : "Failed"}</span>;
}

function FeeToggle({ value, onChange }: { value: FeeKey; onChange: (f: FeeKey) => void }) {
  return (
    <div className="toggle-row" role="group" aria-label="Fee per trade">
      {(Object.keys(FEE_LABEL) as FeeKey[]).map((f) => (
        <button key={f} className="toggle" aria-pressed={f === value} onClick={() => onChange(f)}>
          {FEE_LABEL[f]}
        </button>
      ))}
    </div>
  );
}

function FamilySection({ family }: { family: FamilyBlock }) {
  const [fee, setFee] = useState<FeeKey>("kraken_taker");
  const bh = story.buy_and_hold;
  const gateDetail: Record<(typeof GATE_KEYS)[number], string> = {
    out_of_sample: `Sharpe ${family.test.sharpe.toFixed(2)} vs ${family.test_benchmark.sharpe.toFixed(2)}; Calmar ${family.test.calmar.toFixed(2)} vs ${family.test_benchmark.calmar.toFixed(2)}`,
    deflated_sharpe: `${family.deflated_sharpe.toFixed(2)}, needs 0.95 (lenient version: ${family.lenient_deflated_sharpe.toFixed(2)})`,
    walk_forward: `${pct(family.positive_fold_share)} of six-month periods made money, needs 60%`,
    eth_holdout: `Sharpe ${family.eth_sharpe.toFixed(2)} vs ${family.eth_benchmark_sharpe.toFixed(2)} for holding Ether`,
  };
  return (
    <section className="family">
      <h2>{family.name}</h2>
      <p className="prose muted">
        The best version on 2017-2022 data was {variantPhrase(family.selected)}. It made {family.trades} trades, and at real
        fees they cost about {pct(family.annual_fee_drag)} of the pot every year.
      </p>
      <FeeToggle value={fee} onChange={setFee} />
      <LineChart
        dates={story.weeks}
        log
        yFormat={moneyShort}
        series={[
          { name: "strategy", values: family.growth_weekly[fee], color: "var(--honest)", width: 2.2, endLabel: moneyShort, legend: variantName(family.selected) },
          { name: "hold", values: bh.growth_weekly, color: "var(--ink)", dash: "6 4", endLabel: moneyShort, legend: "Just holding Bitcoin" },
        ]}
        ariaLabel={`$1,000 in ${variantName(family.selected)} at ${FEE_LABEL[fee]} compared with buying and holding Bitcoin.`}
      />
      <p className="caption">
        Value of $1,000 from Aug 2017 to Sep 2026, log scale, at {FEE_LABEL[fee]}. Source: Binance BTCUSDT candles; fills at the
        next bar's open.
      </p>

      <h3>The four tests</h3>
      <table className="data">
        <thead>
          <tr>
            <th>Test</th>
            <th>Result</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {GATE_KEYS.map((k, i) => (
            <tr key={k}>
              <td>{data.method.gates[i]?.name ?? k}</td>
              <td>{gateDetail[k]}</td>
              <td>
                <PassFail ok={family.gates[k]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="grid grid-2 tables">
        <div>
          <h3>Every version we tried</h3>
          <table className="data">
            <thead>
              <tr>
                <th>Version</th>
                <th className="num">Trades</th>
                <th className="num">0.08%</th>
                <th className="num">0.45%</th>
                <th className="num">0.85%</th>
              </tr>
            </thead>
            <tbody>
              {family.variants.map((v) => (
                <tr key={v.name}>
                  <td>{variantName(v.name)}</td>
                  <td className="num">{v.trades}</td>
                  <td className="num">{signedPct(v.cagr.article, 0)}</td>
                  <td className="num">{signedPct(v.cagr.kraken_maker, 0)}</td>
                  <td className="num">{signedPct(v.cagr.kraken_taker, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="caption">Average yearly growth, Aug 2017 to Sep 2026, at each fee per trade. Holding Bitcoin: {signedPct(bh.cagr, 0)}.</p>
        </div>
        <div>
          <h3>Six months at a time</h3>
          <table className="data">
            <thead>
              <tr>
                <th>Period</th>
                <th className="num">Strategy</th>
                <th className="num">Holding</th>
              </tr>
            </thead>
            <tbody>
              {family.walk_forward.map((w) => (
                <tr key={w.start}>
                  <td>
                    {longDate(w.start)} to {longDate(w.end)}
                  </td>
                  <td className="num">{signedPct(w.return, 0)}</td>
                  <td className="num">{signedPct(w.benchmark_return, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="caption">At each period's start, the version with the best record so far was chosen, using only earlier data. Real fees.</p>
        </div>
      </div>
    </section>
  );
}

function outcomeText(c: Call): string {
  if (c.outcome === "pending") return "Settles later";
  if (c.outcome === "no call") return "No direction";
  return c.outcome === "right" ? "Right" : "Wrong";
}

function TradingAgentsSection({ ai }: { ai: Ai }) {
  const calls = ai.weekly_calls.filter((c) => c.outcome === "right" || c.outcome === "wrong");
  return (
    <section className="family">
      <h2>What happened</h2>
      <div className="stats">
        <Stat value={`${ai.hits} of ${ai.calls}`} label="Bitcoin and Ether calls right" />
        <Stat value={`p = ${ai.p_value.toFixed(2)}`} label={`Chance a coin does this well; skill needed ${ai.needed_for_significance} right`} />
        <Stat value={`$${ai.usd_per_decision.toFixed(3)}`} label={`Per decision, ${ai.minutes_per_decision.toFixed(1)} minutes each`} />
      </div>
      <CoinFlips calls={calls.map((c) => c.outcome === "right")} coins={ai.coin_flips} seed={ai.coin_seed} />

      <h3>Did its calls add anything?</h3>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Ratings</th>
              <th className="num">Average exposure</th>
              <th className="num">Agent</th>
              <th className="num">Buy and hold</th>
              <th className="num">Same exposure, held</th>
              <th className="num">Timing skill</th>
              <th className="num">Calls right</th>
            </tr>
          </thead>
          <tbody>
            {ai.assets.map((a) => (
              <tr key={a.ticker}>
                <td>{a.ticker}</td>
                <td>
                  {Object.entries(a.ratings)
                    .map(([k, v]) => `${v} ${k}`)
                    .join(", ")}
                </td>
                <td className="num">{pct(a.average_exposure)}</td>
                <td className="num">{signedPct(a.agent_return)}</td>
                <td className="num">{signedPct(a.buy_and_hold_return)}</td>
                <td className="num">{signedPct(a.constant_exposure_return)}</td>
                <td className="num">{signedPct(a.timing_skill)}</td>
                <td className="num">
                  {a.hits} of {a.calls}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">
        {ai.assets.reduce((n, a) => n + a.settled, 0)} settled weeks, {longDate(ai.window[0])} to {longDate(ai.window[1])}.
        Ratings set the share of money in the asset for the next 7 days (Buy 100%, Overweight 75%, Hold 50%, Underweight
        25%, Sell 0%), after 0.85% fees. Timing skill is the agent's return minus holding its average exposure all along.
      </p>
      {ai.repeat_ratings.length > 0 && (
        <p>
          Run {ai.repeat_ratings.length} times on identical inputs ({ai.repeat_cell.split(" ")[0]},{" "}
          {longDate(ai.repeat_cell.split(" ")[1])}), it answered {ai.repeat_ratings.join(", ")}: consistent, but consistency is
          not skill.
        </p>
      )}

      <h3>Every weekly call</h3>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Week of</th>
              <th>Asset</th>
              <th>Rating</th>
              <th className="num">Next 7 days</th>
              <th>Call</th>
            </tr>
          </thead>
          <tbody>
            {ai.weekly_calls.map((c) => (
              <tr key={`${c.ticker}-${c.date}`}>
                <td>{longDate(c.date)}</td>
                <td>{c.ticker}</td>
                <td>{c.rating}</td>
                <td className="num">{c.return === null ? "–" : signedPct(c.return)}</td>
                <td className={c.outcome === "right" ? "pass" : c.outcome === "wrong" ? "fail" : "muted"}>{outcomeText(c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AuditSection({ audit, lookAhead }: { audit: Audit; lookAhead: Story["look_ahead"] }) {
  const gate = audit.deflated_sharpe_gate;
  const wf = audit.walk_forward_defaults;
  const c = audit.costs;
  return (
    <section className="family">
      <h2>Three problems with the published code</h2>
      <h3>1. Its luck test is calibrated wrongly</h3>
      <p className="prose">
        Its deflated-Sharpe function puts a yearly Sharpe ratio into a formula built for daily ones, and leaves out how much
        the trials differ from each other. With the article's own example of {audit.trials} variations, it approves a strategy
        above a roughly fixed Sharpe ratio, whatever the length of the record. The correct test depends on how much data there is:
      </p>
      <table className="data narrow">
        <thead>
          <tr>
            <th>Length of record</th>
            <th className="num">Article's test passes from</th>
            <th className="num">Correct test passes from</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(gate).map(([len, g]) => (
            <tr key={len}>
              <td>{len}</td>
              <td className="num">Sharpe {g.article.toFixed(2)}</td>
              <td className="num">Sharpe {g.correct.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="prose">
        The article itself says a Sharpe ratio above 2 on daily crypto data usually means the backtest is leaking. Its own
        gate can only approve strategies in that range.
      </p>
      <h3>2. Its walk-forward function crashes on its own defaults</h3>
      <p className="prose">
        Test windows are {wf.test_days} days, but its metrics function refuses anything under {wf.metrics_minimum_observations}{" "}
        observations. Every window returns an error, and the summary step fails with <code>{wf.error}</code>.
      </p>
      <h3>3. Its costs are far too low</h3>
      <p className="prose">
        It charges {pct(c.article_per_side, 2)} a trade. A small UK account at Kraken pays {pct(c.kraken_taker_per_side, 2)}{" "}
        including slippage, {c.ratio.toFixed(1)} times as much.
      </p>
      <h3>What one day of peeking does</h3>
      <div className="stats">
        <Stat value={`${pct(lookAhead.honest.cagr)} to ${pct(lookAhead.leaky.cagr)}`} label="Yearly growth, honest then peeking" />
        <Stat value={`${lookAhead.honest.sharpe.toFixed(2)} to ${lookAhead.leaky.sharpe.toFixed(2)}`} label="Sharpe ratio" />
        <Stat value={`${pct(lookAhead.honest.max_drawdown)} to ${pct(lookAhead.leaky.max_drawdown)}`} label="Worst drop" />
      </div>
      <p className="caption">
        The 200-day trend filter on Bitcoin at real fees, honest versus filled at the open of the day whose close produced the
        signal.
      </p>
    </section>
  );
}

function plainTitle(claim: Claim): string {
  return claim.title.replace(/[“”"]/g, "");
}

export default function ClaimPage({ slug }: { slug: string }) {
  const claim = data.claims.find((c) => c.slug === slug);
  if (!claim) return <NotFound />;
  return (
    <Shell title={plainTitle(claim)}>
      <p className="small">
        <Link to="/claims">All claims</Link>
      </p>
      <div className="claim-card-top">
        <Verdict verdict={claim.verdict} />
        <span className="muted small">
          {claim.kind} · tested {longDate(claim.tested_on)}
        </span>
      </div>
      <h1>{claim.title}</h1>
      <p className="claim-headline big">{claim.headline}</p>
      <div className="grid grid-2">
        <section>
          <h3>The claim</h3>
          <blockquote>{claim.claim}</blockquote>
          <p className="small muted">
            Source: {claim.source_url ? <a href={claim.source_url}>{claim.source}</a> : claim.source}
          </p>
        </section>
        <section>
          <h3>What we tested</h3>
          <p>{claim.what_we_tested}</p>
          <h3>What we found</h3>
          <p>{claim.summary}</p>
        </section>
      </div>
      <hr className="rule" />
      {claim.experiment === "backtest" && claim.families?.map((f) => <FamilySection key={f.family} family={f} />)}
      {claim.experiment === "tradingagents" && claim.ai && <TradingAgentsSection ai={claim.ai} />}
      {claim.experiment === "article_audit" && claim.audit && claim.look_ahead && (
        <AuditSection audit={claim.audit} lookAhead={claim.look_ahead} />
      )}
    </Shell>
  );
}
