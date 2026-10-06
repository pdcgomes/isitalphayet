import { BandBars } from "../charts/BandBars";
import { Calibration } from "../charts/Calibration";
import { GroupedBars } from "../charts/GroupedBars";
import { LineChart } from "../charts/LineChart";
import { RangeDots } from "../charts/RangeDots";
import { ShareBars } from "../charts/ShareBars";
import { Stat } from "../components/Shell";
import { REPO_URL } from "../config";
import { longDate, moneyShort, pct, signedPct } from "../lib/format";
import type { BondRun, Polymarket } from "../lib/types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monthLabel = (ym: string) => `${MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(2, 4)}`;
const PEAK = ["2026-01", "2026-02", "2026-03"];

function sum(months: Polymarket["viral"]["wallets"][number]["months"], key: "volume" | "trading_profit" | "trades", pick: (m: string) => boolean) {
  return months.filter((m) => pick(m.month)).reduce((n, m) => n + m[key], 0);
}

function StudyNote({ pm }: { pm: Polymarket }) {
  const report = REPO_URL ? `${REPO_URL}/blob/main/experiments/polymarket/REPORT.md` : undefined;
  return (
    <p className="caption">
      Part of one Polymarket study, pre-registered {longDate(pm.preregistered_at)} (SHA-256{" "}
      <code>{pm.preregistration_sha256.slice(0, 12)}</code>, {pm.preregistration_changes} logged clarification
      {pm.preregistration_changes === 1 ? "" : "s"}); {pm.trials} strategy versions tried, all counted. Today's taker fees
      are applied throughout. UK residents can't open positions on Polymarket: it geoblocks the UK, and the Gambling
      Commission and FCA treat it as off-limits to retail. No account was opened and no money was used.
      {report && (
        <>
          {" "}
          <a href={report}>Full write-up and code</a>.
        </>
      )}
    </p>
  );
}

export function LatencySection({ pm }: { pm: Polymarket }) {
  const months = [...new Set(pm.viral.wallets.flatMap((w) => w.months.map((m) => m.month)))].sort();
  const [dxd, copied] = pm.viral.wallets;
  const trades = sum(dxd.months, "trades", (m) => PEAK.includes(m));
  const after = (m: string) => m >= "2026-04";
  const markers = Object.entries(pm.viral.fee_changes).map(([d, label]) => ({
    at: months.indexOf(d.slice(0, 7)) + (Number(d.slice(8, 10)) - 1) / 31,
    label: `${longDate(d)}: ${label}`,
  }));
  const colors = ["var(--honest)", "var(--cheat)", "var(--good)"];
  const v = pm.latency.variants;
  const fc = pm.latency.forecast;
  const ten = fc[fc.length - 1];
  return (
    <section className="family">
      <h2>The wallets behind the screenshots</h2>
      <div className="stats">
        <Stat value={moneyShort(sum(dxd.months, "trading_profit", (m) => PEAK.includes(m)))} label="0x8dxd's trading profit, Jan to Mar 2026" />
        <Stat value={`${Math.round(trades / (90 * 24 * 60))} a minute`} label={`Trades, around the clock (${(trades / 1e6).toFixed(1)} million)`} />
        <Stat value={moneyShort(sum(dxd.months, "volume", after))} label={`Traded from April on, against ${moneyShort(sum(dxd.months, "volume", (m) => PEAK.includes(m)))} in Jan to Mar`} />
      </div>
      <GroupedBars
        categories={months.map(monthLabel)}
        series={pm.viral.wallets.map((w, i) => ({ name: w.label[0].toUpperCase() + w.label.slice(1), color: colors[i], values: months.map((m) => w.months.find((x) => x.month === m)?.volume ?? 0) }))}
        markers={markers}
        yFormat={moneyShort}
        ariaLabel="Monthly trading volume of the viral bot wallets, which fell to almost nothing from April 2026."
      />
      <p className="caption">
        Monthly trading volume from Polymarket's public data. Dotted lines: fees on 15-minute crypto markets (5 Jan), on all
        crypto markets (6 Mar) and on most other categories (30 Mar 2026). The "$68 into $1.5M" account made{" "}
        {moneyShort(sum(copied.months, "trading_profit", (m) => PEAK.includes(m)))} from January to March and has not traded since.
      </p>
      <p className="prose">
        These were real, high-frequency operations, not a laptop and $68. Both stopped within weeks of fees reaching every
        crypto market. Polymarket designed those fees to blunt exactly this kind of bot.
      </p>

      <h2>Replaying the bot</h2>
      <p className="prose">
        We rebuilt the strategy and ran it against recorded Polymarket order books, every 100 ms, on ten days drawn at random:
        five before and five after the 7 August switch to averaged settlement prices. At each tick the bot works out the
        chance of "Up" from Binance's move since the window opened, and buys when a side is cheaper than that by more than
        the fee plus a margin. The order reaches the book after a delay and only fills at prices no worse than when it fired.
      </p>
      <RangeDots
        rows={v.map((r) => ({
          label: r.name,
          points: [
            { value: r.before.mean_return, lo: r.before.lo95, hi: r.before.hi95, color: "var(--honest)" },
            { value: r.after.mean_return, lo: r.after.lo95, hi: r.after.hi95, color: "var(--cheat)" },
          ],
        }))}
        format={(x) => signedPct(x, 0)}
        legend={[
          { label: "Before the 7 Aug change", color: "var(--honest)" },
          { label: "After it", color: "var(--cheat)" },
        ]}
        ariaLabel="Return per dollar of six versions of the latency bot, before and after the settlement change. Every interval includes zero."
      />
      <p className="caption">
        Return per $1 staked on 15-minute Bitcoin markets after today's crypto taker fee, with 95% ranges.{" "}
        {v[0].before.windows + v[0].after.windows} market windows; one entry of 10 shares per window. To count, a version at
        retail speed (300 ms or slower) had to make money with confidence both before and after the change. None did.
      </p>
      <h3>The market already knew</h3>
      <GroupedBars
        categories={fc.map((f) => (f.seconds_left >= 60 ? `${f.seconds_left / 60} min left` : `${f.seconds_left} s left`))}
        series={[
          { name: "The bot's Binance model", color: "var(--hold)", values: fc.map((f) => f.model) },
          { name: "Polymarket's own price", color: "var(--honest)", values: fc.map((f) => f.market) },
        ]}
        yFormat={(x) => x.toFixed(2)}
        height={240}
        ariaLabel="Forecast error of the bot's model and of Polymarket's price at four points in the window; the market's is lower at every point."
      />
      <p className="caption">
        Forecast error (Brier score: 0 is perfect, a coin flip scores 0.25). Ten seconds before the close the market scored{" "}
        {ten.market.toFixed(3)} and the bot's model {ten.model.toFixed(3)}. The gaps the bot traded on were mostly its own
        mistakes, not the market lagging.
      </p>
      <StudyNote pm={pm} />
    </section>
  );
}

function BondTable({ pm }: { pm: Polymarket }) {
  const rows: [string, BondRun][] = [
    ["Due within 7 days, as registered", pm.bonds.registered["D=7"]],
    ["Due within 30 days, as registered", pm.bonds.registered["D=30"]],
    ["Due within 7 days, market still open at day end", pm.bonds.open_at_end_of_day["D=7"]],
    ["Due within 30 days, market still open at day end", pm.bonds.open_at_end_of_day["D=30"]],
  ];
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th>Version</th>
            <th className="num">Bets</th>
            <th className="num">Won</th>
            <th className="num">A year</th>
            <th className="num">95% range</th>
            <th className="num">Worst drop</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, r]) => (
            <tr key={label}>
              <td>{label}</td>
              <td className="num">{r.positions.toLocaleString("en-GB")}</td>
              <td className="num">{pct(r.win_rate, 1)}</td>
              <td className="num">{signedPct(r.cagr)}</td>
              <td className="num">
                {signedPct(r.cagr_lo, 0)} to {signedPct(r.cagr_hi, 0)}
              </td>
              <td className="num">{pct(r.max_drawdown)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BondsSection({ pm }: { pm: Polymarket }) {
  const c = pm.calibration;
  const under5 = c.scheduled_end[0];
  const b = pm.bonds;
  const robust = b.open_at_end_of_day["D=30"];
  const registered = b.registered["D=30"];
  const cash = b.weeks.map((_, i) => 1000 * (1 + b.cash_rate) ** ((i * 7) / 365));
  return (
    <section className="family">
      <h2>Are Polymarket's odds fair?</h2>
      <p className="prose">
        For {c.markets.toLocaleString("en-GB")} resolved two-outcome markets, we took each side's price a week before the end
        and checked how often it won.
      </p>
      <div className="grid grid-2">
        <div>
          <Calibration
            series={[
              { name: "A week before the scheduled end", color: "var(--cheat)", points: c.scheduled_end },
              { name: "A week before the actual close", color: "var(--honest)", points: c.recorded_close },
            ]}
            ariaLabel="Price paid against the share that won: both lines sit close to the diagonal."
          />
        </div>
        <div>
          <BandBars
            bars={c.scheduled_end.map((x) => ({ label: `${x.band.split("-")[0]}¢`, value: x.after, lo: x.lo, hi: x.hi }))}
            ariaLabel="Return per dollar by price band after fees and spread: no band is reliably above zero."
          />
          <p className="caption">Return per $1 after today's fees and one tick of spread, by price band, with 95% ranges.</p>
        </div>
      </div>
      <p className="prose">
        Prices are close to the real odds, which is why there are no spare cents to collect. The worst buys are long shots:
        shares under 5¢ won {pct(under5.won, 1)} of the time at an average price of {(under5.price * 100).toFixed(1)}¢, losing{" "}
        {pct(-under5.before_fees)} of the stake before fees and {pct(-under5.after)} after. Measured from the actual close,
        that bias disappears, because markets that closed early often did so <em>because</em> the long shot happened, which
        nobody knew a week before.
      </p>

      <h2>The bond portfolio</h2>
      <div className="stats">
        <Stat value={pct(robust.win_rate)} label="Of bets won" />
        <Stat value={`${signedPct(robust.cagr)} a year`} label={`Against ${pct(b.cash_rate, 2)} cash`} />
        <Stat value={pct(robust.max_drawdown)} label="Worst drop on the way" />
      </div>
      <LineChart
        dates={b.weeks}
        yFormat={moneyShort}
        series={[
          { name: "registered", values: registered.equity_weekly, color: "var(--hold)", dash: "6 4", endLabel: moneyShort, legend: "As registered (includes markets that closed that day)" },
          { name: "robust", values: robust.equity_weekly, color: "var(--honest)", width: 2.2, endLabel: moneyShort, legend: "Only markets still open at the end of the day" },
          { name: "cash", values: cash, color: "var(--ink)", dash: "2 4", endLabel: moneyShort, legend: `Cash at ${pct(b.cash_rate, 2)}` },
        ]}
        ariaLabel="$1,000 in the bond strategy from January 2024 to March 2026, compared with cash."
      />
      <p className="caption">
        $1,000 buying every outcome priced 95-99¢ that was due within 30 days, 2% per bet and at most 10% of a day's volume,
        January 2024 to March 2026, after today's fees and a tick of spread.
      </p>
      <BondTable pm={pm} />
      <p className="prose">
        As registered, it looked better than cash, though not by enough to pass. Most of that was an artefact of daily prices.
        For a market that closes during the day, its "daily price" is the last trade before it settled, and knowing that it
        was the last trade is hindsight. Buying only when the market was still open at the end of the day (a check we added
        after seeing the results, and counted as extra trials), it made {signedPct(robust.cagr)} a year. About one bet in{" "}
        {Math.round(robust.positions / robust.losses)} lost the whole stake; sports "certainties" alone lost{" "}
        {moneyShort(-robust.sports_pnl)} of the $1,000.
      </p>
      <StudyNote pm={pm} />
    </section>
  );
}

export function CopySection({ pm }: { pm: Polymarket }) {
  const g = pm.wallets.groups;
  const p = pm.persistence;
  const copied = pm.viral.wallets[1];
  const lastTrade = [...copied.months].reverse().find((m) => m.volume > 1000)?.month;
  return (
    <section className="family">
      <h2>Who wins and who loses</h2>
      <div className="stats">
        <Stat value={pct(g.all.share_loss)} label={`Of ${(g.all.wallets / 1e6).toFixed(2)} million wallets lost money`} />
        <Stat value={moneyShort(g.human.total)} label="People, in total" />
        <Stat value={`+${moneyShort(g.automated.total)}`} label="Bots, in total" />
        <Stat value={pct(g.all.top_1pct_share_of_profit)} label="Of all profit went to the top 1%" />
      </div>
      <ShareBars
        rows={[
          { label: "Everyone who traded $100 or more", short: "Everyone", value: g.all.share_loss },
          { label: "Bots (1,000+ trades a week)", short: "Bots", value: g.automated.share_loss },
          { label: "People", short: "People", value: g.human.share_loss },
          { label: "People who mostly post limit orders", short: "Limit orders", value: g.human_maker_heavy.share_loss, sub: true },
          { label: "People who mostly take the posted price", short: "Take the price", value: g.human_taker_heavy.share_loss, sub: true },
          ...pm.wallets.by_volume.map((b) => ({ label: `People who traded ${b.band}`, short: b.band, value: b.share_loss, sub: true })),
        ]}
        ariaLabel="Share of wallets that lost money, by group: most groups are above half."
      />
      <p className="caption">
        Share of wallets with a loss, November 2022 to March 2026, after fees. Data: the dataset behind Akey, Grégoire, Harvie
        and Martineau (2026), "Who Wins and Who Loses in Prediction Markets?"; groups and figures are our own.
      </p>
      <p className="prose">
        The money flows from people to bots, almost dollar for dollar. People who take the posted price, which is what a copier
        does, did worst. Even people who traded more than $1M lost more often than not.
      </p>

      <h2>Do winners keep winning?</h2>
      <p className="prose">
        If winning were skill, each half-year's top 1% would beat equally large losers in the next half-year. We compared them
        with what 1,000 random shuffles produce.
      </p>
      <RangeDots
        rows={p.splits.map((s) => ({
          label: s.label,
          band: [s.null_p025, s.null_p975],
          points: [{ value: s.top_mean_next, color: s.beats_null ? "var(--good)" : "var(--cheat)" }],
          note: moneyShort(s.top_mean_next),
        }))}
        format={moneyShort}
        legend={[
          { label: "Top 1%'s average profit next half-year", color: "var(--cheat)" },
          { label: "What luck alone produces (95%)", color: "var(--rule)", shaded: true },
        ]}
        ariaLabel={`The top 1% beat the luck range in ${p.splits_beating_null} of ${p.splits.length} half-years.`}
      />
      <p className="caption">
        People only (bots excluded). Green: beat the luck range. The rank correlation between one half-year's profit and the
        next was {p.splits.map((s) => s.spearman.toFixed(2)).join(", ")}: close to none.
      </p>
      <p className="prose">
        They beat luck in {p.splits_beating_null} of {p.splits.length} half-years; we required 3. And a copier can only do worse
        than the wallet they copy, buying after it at worse prices. The account the $499 bot copies last traded in{" "}
        {lastTrade ? monthLabel(lastTrade) : "early 2026"}.
      </p>
      <StudyNote pm={pm} />
    </section>
  );
}
