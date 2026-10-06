import { Shell, Stat } from "../components/Shell";
import { REPO_URL } from "../config";
import { data } from "../lib/data";
import { longDate, pct } from "../lib/format";
import { Markdown } from "../lib/markdown";
import { Link } from "../lib/router";

const FEE_DESCRIPTIONS: Record<string, string> = {
  article: "What the viral X Article assumes: 5 basis points of fee plus 3 of slippage",
  kraken_maker: "Kraken Pro entry tier, maker orders (0.40%), plus 0.05% slippage",
  kraken_taker: "Kraken Pro entry tier, taker orders (0.80%), plus 0.05% slippage. All tests use this one",
};

export default function Method() {
  const { meta, method, polymarket: pm } = data;
  return (
    <Shell title="How we tested">
      <header className="page-head">
        <p className="kicker">Method</p>
        <h1>How we tested</h1>
        <p className="prose">
          Write the rules down before testing. Count every attempt. Use real prices and the fees a real person pays. Judge only
          on data the strategy never saw. Publish the code so anyone can check.
        </p>
        <div className="stats">
          <Stat value={longDate(meta.preregistered_at)} label="Rules fixed, before any test ran" />
          <Stat value={meta.trials + meta.polymarket_trials} label="Strategy versions, all counted" />
          <Stat value={meta.runs_logged.toLocaleString("en-GB")} label="Runs in the public ledger" />
        </div>
      </header>

      <h2>The four tests</h2>
      <ol className="prose">
        {method.gates.map((g) => (
          <li key={g.name}>
            <strong>{g.name}.</strong> {g.detail}
          </li>
        ))}
      </ol>

      <h2>Costs</h2>
      <table className="data narrow">
        <thead>
          <tr>
            <th>Scenario</th>
            <th className="num">Per trade</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(meta.fees).map(([k, v]) => (
            <tr key={k}>
              <td>{FEE_DESCRIPTIONS[k] ?? k}</td>
              <td className="num">{pct(v, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Data</h2>
      <p className="prose">
        Binance's public BTCUSDT and ETHUSDT daily and 4-hour candles, {longDate(meta.data_range[0])} to{" "}
        {longDate(meta.data_range[1])}. Strategies were chosen on {meta.design_period} and judged on{" "}
        {meta.test_period}, then on Ether unchanged. Every signal is decided on a closed bar and filled at the next bar's open.
        Long-only spot, no leverage. TradingAgents decisions were scored on Yahoo Finance daily closes, the data source it reads
        itself.
      </p>

      <h2>Prediction markets (Polymarket)</h2>
      <p className="prose">
        The three Polymarket claims share one study with its own pre-registration, fixed on {longDate(pm.preregistered_at)}{" "}
        before any outcome data was downloaded, and {pm.trials} counted strategy versions. Wallet profits and daily prices
        come from the public dataset behind Akey, Grégoire, Harvie and Martineau (2026), November 2022 to March 2026; the
        latency bot is replayed on Polymarket order books recorded every 100 ms between May and August 2026; the viral
        wallets come from Polymarket's own public data. Every test charges today's taker fee, feeRate × p × (1 − p) per
        share (7% for crypto, 4-5% elsewhere), plus a tick of spread. The benchmark is cash at the Bank of England's{" "}
        {pct(pm.bonds.cash_rate, 2)}, or a coin flip. No account was opened: Polymarket geoblocks the UK.
      </p>
      <p className="prose">
        <Link to="/claims/polymarket-latency-bots">Latency bots</Link> · <Link to="/claims/polymarket-bonds">"Bonds"</Link> ·{" "}
        <Link to="/claims/polymarket-copy-trading">Copying winning wallets</Link>
      </p>

      <h2>Limitations</h2>
      <ul className="prose">
        {method.limitations.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>

      <h2>Corrections</h2>
      <ul className="prose">
        {method.corrections.map((c) => (
          <li key={c.text}>
            <strong>{longDate(c.date)}.</strong> {c.text}
          </li>
        ))}
      </ul>

      <h2>Reproduce it</h2>
      <pre className="code-block">{`uv sync
uv run python -m lab.data                      # download and check the price history
uv run python experiments/run_backtests.py     # the pre-registered backtests and gates
uv run python experiments/hype_waterfall.py    # the pitch's numbers, cheat by cheat
uv run python experiments/article_audit.py     # the X Article's own code, as published
uv run python experiments/export_site_data.py  # everything this site shows`}</pre>
      {REPO_URL && (
        <p>
          Code, data and the full trial ledger: <a href={REPO_URL}>{REPO_URL.replace(/^https?:\/\//, "")}</a>
        </p>
      )}

      <h2>The pre-registration, as written before any test ran</h2>
      <p className="small muted">
        SHA-256 <code>{meta.preregistration_sha256}</code>, recorded {new Date(meta.preregistered_at).toUTCString()}.{" "}
        {meta.preregistration_changes === 0 ? "Unchanged since." : `${meta.preregistration_changes} logged changes since.`}
      </p>
      <div className="card prereg">
        <Markdown source={method.preregistration_text} />
      </div>

      <details className="prereg-more">
        <summary>The Polymarket pre-registration</summary>
        <p className="small muted">
          SHA-256 <code>{pm.preregistration_sha256}</code>, recorded {new Date(pm.preregistered_at).toUTCString()}.{" "}
          {pm.preregistration_changes} logged clarification{pm.preregistration_changes === 1 ? "" : "s"}, made before the
          tests it affects were run.
        </p>
        <div className="card prereg">
          <Markdown source={method.polymarket_preregistration_text} />
        </div>
      </details>
    </Shell>
  );
}
