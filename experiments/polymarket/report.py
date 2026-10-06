"""Charts and the plain-English write-up for the Polymarket study, built from experiments/polymarket/results/*.json."""

from __future__ import annotations

import json
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from lab.data import REPO_ROOT  # noqa: E402
from lab.ledger import read  # noqa: E402

HERE = REPO_ROOT / "experiments" / "polymarket"
RESULTS = HERE / "results"
INK, MUTED, RED, BLUE, GREEN, GRID = "#1f1f1f", "#7a7a7a", "#c0392b", "#2c5d8f", "#2e7d4f", "#e6e2da"


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text())


def style(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=MUTED)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name: str) -> str:
    path = RESULTS / f"{name}.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"results/{name}.png"


def money(x: float) -> str:
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e6:
        return f"{sign}${x / 1e6:,.0f}M" if x >= 1e7 else f"{sign}${x / 1e6:,.1f}M"
    if x >= 1e3:
        return f"{sign}${x / 1e3:,.1f}K"
    return f"{sign}${x:,.2f}"


def pct(x: float, digits: int = 0) -> str:
    text = f"{x * 100:.{digits}f}%"
    return text.lstrip("-") if float(text[:-1]) == 0 else text


def variant_words(name: str) -> str:
    """'15m | delay=300ms, margin=0.03' -> '300 ms delay, 3¢ margin'."""
    delay, margin = name.split("| ")[1].split(", ")
    return f"{delay.split('=')[1].replace('ms', ' ms')} delay, {float(margin.split('=')[1]) * 100:.0f}¢ margin"


def tex_safe(label: str) -> str:
    """Matplotlib reads text between two dollar signs as maths."""
    return label.replace("$", r"\$")


def chart_who_wins(w: dict) -> str:
    g, v = w["groups"], w["human_by_volume"]
    rows = [("Everyone ($100+ traded)", g["all"]), ("Bots (1,000+ trades a week)", g["automated"]),
            ("People", g["human"]), ("  People who mostly post limit orders", g["human_maker_heavy"]),
            ("  People who mostly take the posted price", g["human_taker_heavy"])]
    rows += [(f"  People who traded {k}", s) for k, s in v.items()]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [2.2, 1]})
    labels = [r[0] for r in rows][::-1]
    shares = [r[1]["share_loss"] for r in rows][::-1]
    a.barh(labels, shares, color=[RED if s > 0.5 else BLUE for s in shares], height=0.62)
    a.axvline(0.5, color=MUTED, linestyle="--", linewidth=1)
    for i, s in enumerate(shares):
        a.text(s + 0.01, i, pct(s), va="center", fontsize=9, color=INK)
    a.set_xlim(0, 1)
    a.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    style(a, "Most wallets lose money", "Share of wallets with a loss, Nov 2022 to Mar 2026")
    totals = [("People", g["human"]["total"]), ("Bots", g["automated"]["total"])]
    b.bar([t[0] for t in totals], [t[1] / 1e6 for t in totals], color=[RED, GREEN], width=0.55)
    for i, (_, t) in enumerate(totals):
        b.text(i, t / 2e6, ("+" if t > 0 else "") + money(t), ha="center", va="center", fontsize=11, color="white",
               fontweight="bold")
    b.axhline(0, color=MUTED, linewidth=1)
    b.set_ylabel("Total profit ($M)", fontsize=9, color=MUTED)
    style(b, "Money flows from people to bots", "Total profit of each group")
    b.grid(axis="y", color=GRID)
    b.grid(axis="x", visible=False)
    return save(fig, "who_wins")


def chart_persistence(p: dict) -> str:
    fig, ax = plt.subplots(figsize=(10, 4.4))
    keys = list(p["splits"])
    for i, k in enumerate(keys):
        s = p["splits"][k]["human"]
        ax.plot([s["null_p025"], s["null_p975"]], [i, i], color=MUTED, linewidth=6, alpha=0.35, solid_capstyle="round")
        ax.plot(s["top_mean_next"], i, "o", color=GREEN if s["beats_null"] else RED, markersize=9)
        ax.text(max(s["top_mean_next"], s["null_p975"]) + 600, i, money(s["top_mean_next"]), va="center", fontsize=9)
    ax.set_yticks(range(len(keys)), [k.replace(" -> ", " then ") for k in keys])
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: money(x)))
    style(ax, "Last period's top 1% didn't reliably beat equally big losers",
          "Dot: next-period average profit of the top 1% of people. Grey: the range luck alone gives (95%).")
    return save(fig, "persistence")


def chart_calibration(c: dict) -> str:
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5))
    primary = c["horizons"]["7"]["bands"]
    sens = c["sensitivity_scheduled_expiration"]["bands"]
    for bands, color, label in [(primary, BLUE, "7 days before the recorded close"),
                                (sens, RED, "7 days before the scheduled date")]:
        x = [r["avg_price"] for r in bands if r["tokens"]]
        y = [r["win_rate"] for r in bands if r["tokens"]]
        a.plot(x, y, "o-", color=color, markersize=4, linewidth=1.4, label=label)
    a.plot([0, 1], [0, 1], color=MUTED, linestyle="--", linewidth=1)
    a.set_xlabel("Price paid", fontsize=9, color=MUTED)
    a.set_ylabel("Share that won", fontsize=9, color=MUTED)
    a.legend(frameon=False, fontsize=9)
    style(a, "Prices are close to the real odds", "On the dashed line, a 30¢ share wins 30% of the time")
    a.grid(axis="y", color=GRID)
    labels = [r["band"] for r in sens]
    means = [r["ret_after_fees_tick"]["mean"] for r in sens]
    los = [r["ret_after_fees_tick"]["lo"] for r in sens]
    his = [r["ret_after_fees_tick"]["hi"] for r in sens]
    xs = np.arange(len(labels))
    b.bar(xs, means, color=[RED if m < 0 else GREEN for m in means], width=0.7)
    b.errorbar(xs, means, yerr=[np.array(means) - los, np.array(his) - means], fmt="none", ecolor=INK, linewidth=0.8)
    b.axhline(0, color=MUTED, linewidth=1)
    b.set_xticks(xs[::2], [l.split("-")[0] + "¢" for l in labels[::2]])
    b.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    b.set_xlabel("Price band", fontsize=9, color=MUTED)
    style(b, "No price band pays after fees", "Return per $1 after today's fees and one tick, with 95% range")
    b.grid(axis="y", color=GRID)
    b.grid(axis="x", visible=False)
    return save(fig, "calibration")


def chart_bonds(bonds: dict) -> str:
    fig, ax = plt.subplots(figsize=(10, 4.6))
    reg = bonds["variants"]["D=30"]["equity_weekly"]
    rob = bonds["robustness_open_at_end_of_day"]["D=30"]["equity_weekly"]
    weeks = np.arange(len(reg))
    cash = 1000 * (1 + bonds["definitions"]["cash_rate"]) ** (weeks * 7 / 365)
    ax.plot(weeks, reg, color=BLUE, linewidth=1.6, label="As registered (daily prices, includes markets that closed that day)")
    ax.plot(weeks, rob, color=RED, linewidth=1.6, label="Only markets still open at the end of the day")
    ax.plot(weeks, cash, color=MUTED, linestyle="--", linewidth=1.2, label="Cash at 3.75%")
    ticks = [0, 52, 104]
    ax.set_xticks(ticks, ["Jan 2024", "Jan 2025", "Jan 2026"])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    style(ax, "\"Bonds\": 98% of bets win, and it still doesn't beat cash",
          "$1,000 buying outcomes priced 95-99¢ that are due within 30 days, after today's fees")
    ax.grid(axis="y", color=GRID)
    return save(fig, "bonds")


def chart_latency(lat: dict, diag: dict) -> str:
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
    names = [k for k in lat["verdict"]]
    for j, (regime, color, offset) in enumerate([("before_twap", BLUE, -0.15), ("after_twap", RED, 0.15)]):
        for i, k in enumerate(names):
            s = lat["results"][k][regime]
            a.plot([s["lo95"], s["hi95"]], [i + offset] * 2, color=color, linewidth=2, alpha=0.6)
            a.plot(s["mean_return"], i + offset, "o", color=color, markersize=6,
                   label=("Before the 7 Aug settlement change" if regime == "before_twap" else "After it") if i == 0 else None)
    a.axvline(0, color=MUTED, linewidth=1)
    a.set_yticks(range(len(names)), [variant_words(k) for k in names])
    a.invert_yaxis()
    a.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    a.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    style(a, "The latency bot's results are indistinguishable from luck",
          "Return per $1 on 15-minute Bitcoin markets after fees, 95% range")
    lefts = sorted(diag, key=int, reverse=True)
    xs = np.arange(len(lefts))
    b.bar(xs - 0.18, [diag[k]["brier_model"] for k in lefts], width=0.36, color=MUTED, label="Bot's Binance model")
    b.bar(xs + 0.18, [diag[k]["brier_market"] for k in lefts], width=0.36, color=BLUE, label="Polymarket's own price")
    b.set_xticks(xs, [f"{int(k) // 60} min" if int(k) >= 60 else f"{k} s" for k in lefts])
    b.set_xlabel("Time left in the window", fontsize=9, color=MUTED)
    b.legend(frameon=False, fontsize=9)
    style(b, "The market already knew", "Forecast error (lower is better)")
    b.grid(axis="y", color=GRID)
    b.grid(axis="x", visible=False)
    return save(fig, "latency")


def chart_viral(v: dict) -> str:
    fig, ax = plt.subplots(figsize=(10, 4.4))
    months = sorted({m["month"] for w in v["wallets"] for m in w["months"]})
    xs = np.arange(len(months))
    colors = [BLUE, RED, GREEN]
    width = 0.27
    for i, w in enumerate(v["wallets"]):
        by = {m["month"]: m["volume"] for m in w["months"]}
        ax.bar(xs + (i - 1) * width, [by.get(m, 0) / 1e6 for m in months], width=width, color=colors[i],
               label=tex_safe(w["label"][0].upper() + w["label"][1:]))
    for d, label in v["fee_changes"].items():
        x = months.index(d[:7]) + (int(d[8:]) - 15) / 30
        ax.axvline(x, color=MUTED, linestyle=":", linewidth=1)
    ax.set_xticks(xs, [m[2:] for m in months], fontsize=8)
    ax.set_ylabel("Monthly volume ($M)", fontsize=9, color=MUTED)
    ax.legend(frameon=False, fontsize=8.5)
    style(ax, "The viral bots stopped trading when the fees arrived",
          "Monthly trading volume; dotted lines mark the fee changes of 5 Jan, 6 Mar and 30 Mar 2026")
    ax.grid(axis="y", color=GRID)
    ax.grid(axis="x", visible=False)
    return save(fig, "viral_wallets")


def trials() -> list[str]:
    seen = []
    for e in read():
        if e.get("study") == "polymarket" and e.get("counts_as_trial") and e["variant"] not in seen:
            seen.append(e["variant"])
    return seen


def main() -> None:
    w, p, c, bonds = load("wallets"), load("persistence"), load("calibration"), load("bonds")
    lat, diag, v = load("latency"), load("latency_diagnostics"), load("viral_wallets")
    charts = {"who": chart_who_wins(w), "persist": chart_persistence(p), "calib": chart_calibration(c),
              "bonds": chart_bonds(bonds), "latency": chart_latency(lat, diag), "viral": chart_viral(v)}
    g = w["groups"]
    human_wins = sum(p["splits"][k]["human"]["beats_null"] for k in p["splits"])
    h7, sens = c["horizons"]["7"], c["sensitivity_scheduled_expiration"]
    sb = {b["band"]: b for b in sens["bands"]}
    reg30, rob30 = bonds["variants"]["D=30"], bonds["robustness_open_at_end_of_day"]["D=30"]
    reg7, rob7 = bonds["variants"]["D=7"], bonds["robustness_open_at_end_of_day"]["D=7"]
    best = max((k for k in lat["verdict"] if lat["verdict"][k]["eligible"]),
               key=lambda k: lat["results"][k]["after_twap"]["mean_return"])
    bs = lat["results"][best]
    wallets = {x["address"]: x for x in v["wallets"]}
    dxd = wallets["0x63ce342161250d705dc0b16df89036c8e5f9ba9a"]
    k9 = wallets["0xd0d6053c3c37e727402d84c14069780d360993aa"]
    vendor = wallets["0xdf4c6a942bd95bf903d6066b4ba7051e6f914f22"]

    def total(wal, field, months=None):
        return sum(m[field] for m in wal["months"] if months is None or m["month"] in months)

    peak = ["2026-01", "2026-02", "2026-03"]
    after = [m["month"] for m in dxd["months"] if m["month"] >= "2026-04"]
    d10, d60 = diag["10"], diag["60"]
    n_trials = len(trials())

    text = f"""# Polymarket: is it alpha yet?

Generated {date.today().isoformat()} by `experiments/polymarket/report.py` from the files in `results/`. Rules fixed in
advance in [preregistration.md](preregistration.md) (SHA-256 logged in `experiments/trials.jsonl` before any outcome data
was downloaded, with one logged clarification). {n_trials} strategy versions were tried, all counted.

**Short answer: no.** Prices on Polymarket are close to the real odds, most wallets lose, the money flows from people to
bots, last period's winners don't reliably keep winning, and neither of the two strategies the viral posts sell (buying
"sure things" at 95-99¢, or racing Binance on 15-minute Bitcoin markets) beat cash or luck in our replays. The viral
bots were real, industrial-scale operations, and they stopped trading when Polymarket's fees arrived.

UK residents can't open positions on Polymarket anyway: it geoblocks the UK, and the Gambling Commission and FCA treat
it as off-limits to retail. No account was opened and no money was used.

| Question | Answer |
|---|---|
| Who wins? | {pct(g['all']['share_loss'])} of wallets that traded $100 or more lost money. People lost {money(-g['human']['total'])} in total; bots made {money(g['automated']['total'])}. |
| Luck or skill? | Mostly luck. The top 1% of people beat equally large losers in {human_wins} of 4 half-years. |
| Are the odds fair? | Yes, closely. After today's fees, no price band pays reliably; long shots lose heavily. |
| Do "bonds" (95-99¢) work? | No. {pct(rob30['win_rate'], 1)} of bets win, but the portfolio made {pct(rob30['cagr'], 1)} a year against 3.75% cash. |
| Does the latency bot work? | No. No version beat luck; the market's own price forecast the outcome better than the bot's model. |
| The viral wallets? | Real, huge and automated, and they stopped trading in March 2026, when fees reached all crypto markets. |

## 1. Who wins and who loses

![Who wins]({charts['who']})

Data: profit for every Polymarket wallet from November 2022 to 29 March 2026, from the dataset behind Akey, Grégoire,
Harvie and Martineau (2026), "Who Wins and Who Loses in Prediction Markets?". We re-derived the headline figures with our
own definitions.

- **{pct(g['all']['share_loss'], 1)}** of the {g['all']['wallets']:,} wallets that traded at least $100 lost money. The
  median wallet lost {money(-g['all']['median'])}; a wallet at the 10th percentile lost {money(-g['all']['p10'])}.
- **People lost {money(-g['human']['total'])}; bots made {money(g['automated']['total'])}.** It's close to a straight
  transfer. "Bot" here means 1,000 or more trades a week, sustained.
- People who mostly **take the posted price** did worst: {pct(g['human_taker_heavy']['share_loss'])} lost, and together
  they lost {money(-g['human_taker_heavy']['total'])}. People who mostly post limit orders roughly broke even.
- **The top 1% of wallets took {pct(g['all']['top_1pct_share_of_profit'])} of all profit**; the top 0.1% took
  {pct(g['all']['top_01pct_share_of_profit'])}.
- Even people who traded more than $1M lost more often than not ({pct(w['human_by_volume']['over $1M']['share_loss'])}).

These match independent analyses (Galaxy Research, Oct 2026: 69.2% of 2.9M accounts below break-even).

## 2. Luck or skill

![Persistence]({charts['persist']})

If winning were skill, last half-year's top winners would keep beating everyone of similar size. We compared the top 1%
of people by profit in one half-year with equally large *losers* of the previous half-year, using 1,000 shuffles to see
what luck alone produces.

- The top 1% beat that luck range in **{human_wins} of 4** half-years, below the 3 required. In the 2024 election half-year
  they lost {money(-p['splits']['2024H1 -> 2024H2']['human']['top_mean_next'])} each on average.
- The rank correlation between one half-year's profit and the next is close to zero
  ({', '.join(f"{p['splits'][k]['human']['spearman']:+.2f}" for k in p['splits'])}).
- Copying winners would be worse still: a copier buys later, at worse prices, so their own next-period result is the best
  a copier could hope for.

## 3. Are the odds fair

![Calibration]({charts['calib']})

For {h7['markets']:,} resolved two-outcome markets, we took each side's price a week before the close and checked how
often it won.

- **Prices are close to the real odds.** Across the middle bands the share that won is within a few points of the price.
- **Long shots are a bad bet.** Measured from the date a buyer knows (the scheduled end), shares under 5¢ won
  {pct(sb['0-5c']['win_rate'], 1)} of the time at an average price of {sb['0-5c']['avg_price'] * 100:.1f}¢: a loss of
  {pct(-sb['0-5c']['ret_before_fees']['mean'])} before any fees, {pct(-sb['0-5c']['ret_after_fees_tick']['mean'])} after.
- **Measured from the recorded close, the long-shot bias disappears.** That version quietly includes markets that closed
  early *because the long shot happened*, which is information nobody had a week before.
- **After today's fees and one tick of spread, no price band makes a reliable profit** in either version.

## 4. "Bonds": buying near-certain outcomes at 95-99¢

![Bonds]({charts['bonds']})

The pitch: buy outcomes priced 95-99¢ that resolve soon, collect the last few cents, repeat. We ran it on every eligible
market from January 2024 to March 2026 with $1,000, 2% per position, at most 10% of a day's volume, today's fees and a
tick of spread.

- As registered, it looked good: {pct(reg30['win_rate'], 1)} of {reg30['positions']:,} bets won and it made
  {pct(reg30['cagr'], 1)} a year (seven-day version: {pct(reg7['cagr'], 1)}). Even so, the 95% range
  ({pct(reg30['cagr_lo'], 1)} to {pct(reg30['cagr_hi'], 1)}) wasn't clear of cash, so it **failed the registered test**.
- **Most of that was an artefact.** For a market that closes during the day, its "daily price" is the last trade before it
  resolved, and knowing it was the last trade is hindsight. Buying only when the market was still open at the end of the
  day (added after seeing the results, and counted as extra trials), it made **{pct(rob30['cagr'], 1)} a year**
  (seven-day: {pct(rob7['cagr'], 1)}), against 3.75% cash, with a worst fall of {pct(-rob30['max_drawdown'])}.
- It is picking up pennies in front of a steamroller: about 1 bet in {round(rob30['positions'] / rob30['losses'])} loses
  the whole stake, and sports "certainties" alone lost {money(-rob30['pnl_by_category'].get('Sports', 0))} of the
  $1,000.

## 5. The 15-minute Bitcoin latency bot

![Latency]({charts['latency']})

The pitch: Binance moves first, Polymarket lags, so a bot buys the side Binance says is now likely. We replayed that bot
on recorded Polymarket order books (every 100 ms) for ten days drawn at random, five before and five after the 7 August
2026 switch to averaged settlement prices. Each order executes against the book after a delay of 100 ms, 300 ms or 1 s,
only at prices no worse than when the signal fired, and pays today's crypto taker fee.

- **No version passed.** The best retail-speed version ({variant_words(best)}) averaged
  {pct(bs['after_twap']['mean_return'], 1)} per $1 after the change and {pct(bs['before_twap']['mean_return'], 1)} before,
  but its ranges ({pct(bs['after_twap']['lo95'], 1)} to {pct(bs['after_twap']['hi95'], 1)} after) are what luck produces.
  It traded almost every window and won about half.
- **The market already knew.** Ten seconds before the close, Polymarket's own price forecast the outcome better than the
  bot's Binance model (error {d10['brier_market']:.3f} against {d10['brier_model']:.3f}; a coin scores 0.250). One minute
  out: {d60['brier_market']:.3f} against {d60['brier_model']:.3f}. The gaps the bot traded on were its own mistakes.
- The 57 days of order books we didn't draw are untouched. They are a clean holdout if anyone wants to test a specific
  version properly.

## 6. The viral wallets

![Viral wallets]({charts['viral']})

- **0x8dxd**, the "$313 into $414K in a month" bot: {money(total(dxd, 'trading_profit', peak))} of trading profit from
  January to March 2026 on {money(total(dxd, 'volume', peak))} of volume and {total(dxd, 'trades', peak):,.0f} trades
  (about {total(dxd, 'trades', peak) / (90 * 24 * 60):,.0f} a minute, around the clock). From April to October it
  traded {money(total(dxd, 'volume', after))} in total, against {money(total(dxd, 'volume', peak))} in the three months
  before.
- **The "$68 into $1.5M" account** that a $499 bot advertises copying: {money(total(k9, 'trading_profit', peak))} from
  January to March on {money(total(k9, 'volume', peak))} of volume. Since April: nothing.
- **That vendor's own bot**: {money(total(vendor, 'trading_profit'))} of trading profit since May on
  {money(total(vendor, 'volume'))} of volume, plus {money(total(vendor, 'rebates_rewards_referrals'))} of rebates and
  rewards that a new retail account wouldn't get.

These were professional, high-frequency operations, not a laptop and $68. Fees on all crypto markets started on 6 March;
both stopped within weeks.

## Limitations

- Wallet profits end on 29 March 2026, just before fees reached most categories. Everything else applies today's fees to
  past prices: it answers "what would this earn now".
- Daily prices can't show the spread; we charge one tick. Real fills on thin markets would often be worse.
- The latency replay covers ten days and one fair-value model. Professional bots use faster feeds and post their own
  orders (makers pay no fees and earn rebates), which we didn't model.
- "Bot" is a trading-rate threshold, not a label. Some fast people count as bots and some slow bots as people.

## Reproduce

```bash
uv run python experiments/polymarket/fetch_data.py wallets && uv run python experiments/polymarket/fetch_data.py books
for t in wallets persistence calibration bonds latency latency_diagnostics viral_wallets report; do
  uv run python experiments/polymarket/$t.py
done
```
"""
    (HERE / "REPORT.md").write_text(text)
    print(f"Wrote {(HERE / 'REPORT.md').relative_to(REPO_ROOT)} and {len(charts)} charts")


if __name__ == "__main__":
    main()
