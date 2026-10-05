import { Shell, Stat } from "../components/Shell";
import { data } from "../lib/data";
import { longDate, pct, signedPct } from "../lib/format";
import { variantName } from "../lib/names";

function gbp(v: string | number): string {
  return `£${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function plusDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function Live() {
  const { forward_test: ft, paper } = data.live;
  const decided = Array.from(new Set(ft.calls.map((c) => c.date))).sort();
  const latest = paper.rows[paper.rows.length - 1];
  const plumbing = paper.config.label.startsWith("plumbing");
  return (
    <Shell title="Live forward test">
      <header className="page-head">
        <p className="kicker">Updated weekly</p>
        <h1>The live test, where hindsight is impossible</h1>
        <p className="prose">
          Backtests can be fooled; next week can't. Every Monday from {longDate(ft.start)} to {longDate(ft.end)}, TradingAgents
          makes a fresh call on Bitcoin and Ether, and we score it seven days later. Alongside it, a paper trade runs one of our
          rules on live Kraken prices.
        </p>
      </header>

      <h2>
        TradingAgents: week {decided.length} of {ft.weeks}
      </h2>
      <table className="data">
        <thead>
          <tr>
            <th>Decided</th>
            <th>Asset</th>
            <th>Rating</th>
            <th className="num">Next 7 days</th>
            <th>Call</th>
          </tr>
        </thead>
        <tbody>
          {ft.calls.map((c) => (
            <tr key={`${c.ticker}-${c.date}`}>
              <td>{longDate(c.date)}</td>
              <td>{c.ticker}</td>
              <td>{c.rating}</td>
              <td className="num">{c.return === null ? "–" : signedPct(c.return)}</td>
              <td className={c.outcome === "right" ? "pass" : c.outcome === "wrong" ? "fail" : "muted"}>
                {c.outcome === "pending" ? `Settles ${longDate(plusDays(c.date, 7))}` : c.outcome === "right" ? "Right" : "Wrong"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="caption">Same scoring as the backtest window: a call is right if the asset moved its way over the next seven days.</p>

      <h2>Paper trade</h2>
      <p className="prose">
        {variantName(paper.config.variant)} on {paper.config.pair.replace(/^XBT/, "BTC/")} at Kraken, with{" "}
        {gbp(paper.config.capital_gbp)} of pretend money and {pct(paper.config.fee_per_side, 2)} per trade. Started{" "}
        {longDate(paper.config.started_at)}.
        {plumbing &&
          " No strategy passed our tests, so this is a plumbing check: it shows whether live signals match the backtest code and whether fills and fees behave as modelled, not whether the strategy works."}
      </p>
      <div className="stats">
        <Stat value={gbp(latest.equity)} label="Paper equity" />
        <Stat value={gbp(latest.buy_and_hold_equity)} label="Buy and hold from the same start" />
        <Stat value={pct(Number(latest.decided_target))} label="Target exposure for the next day" />
      </div>
      <table className="data">
        <thead>
          <tr>
            <th>Day</th>
            <th className="num">BTC close</th>
            <th>Trade</th>
            <th className="num">Equity</th>
            <th className="num">Buy and hold</th>
            <th className="num">Next target</th>
          </tr>
        </thead>
        <tbody>
          {[...paper.rows].reverse().map((r) => (
            <tr key={r.bar_open}>
              <td>{longDate(r.bar_open)}</td>
              <td className="num">{gbp(r.close)}</td>
              <td>{r.trade === "start" ? "Started" : r.trade === "waiting" ? "Waiting for a fresh open" : r.trade}</td>
              <td className="num">{gbp(r.equity)}</td>
              <td className="num">{gbp(r.buy_and_hold_equity)}</td>
              <td className="num">{pct(Number(r.decided_target))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}
