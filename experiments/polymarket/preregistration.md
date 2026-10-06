# Polymarket pre-registration

Written 2026-10-06, before any outcome data (wallet profits, resolved prices, order-book replays) was downloaded or
looked at. Only table schemas, file listings and dataset descriptions had been read. The SHA-256 of this file is written
to `experiments/trials.jsonl` before the first download. Any later edit is logged as a new event, not silently replaced.

Published studies were read beforehand (survey in the conversation of 6 Oct 2026). They report that about 69-84% of
accounts lose money, that profits are concentrated in automated accounts and market makers, and that the viral
latency-arbitrage wallets stopped making money around April 2026. This study checks those findings on the raw data
with our own rules, and tests the strategies the viral posts sell.

## Questions

1. **Who wins?** What share of wallets make money, how concentrated are the profits, and how do automated and
   human-paced wallets differ?
2. **Luck or skill?** Do last period's biggest winners keep winning, compared with equally large losers?
3. **Are the odds fair?** Does a price of p mean a chance of about p, and what does buying at each price return after
   today's fees?
4. **Do "bonds" work?** Does buying near-certain outcomes at 95-99¢ beat cash?
5. **Does the 15-minute Bitcoin latency bot work?** Replayed on real order books, after fees and realistic delays.
6. **What happened to the viral wallets?** Month-by-month profit of the accounts the posts and paid bots point to.

## Data (pinned)

- **D1, wallets and markets.** Hugging Face `vgregoire/polymarket-users`, revision
  `91ddb961b090de18fd79e79edd8fa15f36ca11b9` (Akey, Grégoire, Harvie and Martineau, 2026). Tables: `user_pnl_summary`,
  `user_features`, `pnl_change_monthly`, `markets`, `predictions`, `events`, `ohlcv_1d`. Coverage 2022-11 to
  2026-03-29. Amounts are in USDC; we treat 1 USDC as £1 and ignore exchange-rate effects.
- **D2, 15-minute Bitcoin order books.** Hugging Face `whodisidk/polymarket-btc-updown-exchange-data`, revision
  `03e7d08b585325fa1468001982edae262c69429c`. Ten days drawn with `random.Random(2026)`: five of the 49 dates before
  the 7 Aug 2026 switch to TWAP settlement (`2026-05-31`, `2026-06-01`, `2026-06-14`, `2026-06-27`, `2026-07-06`) and
  five of the 18 dates after it (`2026-08-19`, `2026-08-24`, `2026-08-25`, `2026-08-26`, `2026-08-27`). Archive
  checksums are verified against the dataset's `MANIFEST.txt`.
- **D3, viral wallets.** Polymarket's public Data API, fetched on the run date and saved as raw JSON.
- **Cash benchmark.** Bank of England Bank Rate on 6 Oct 2026: 3.75%.

## Fees (today's schedule, applied to all tests)

- A taker pays, per share bought at price p, `feeRate × p × (1 − p)`. Makers pay nothing.
- feeRate by category: crypto 0.07; sports, culture, weather and other 0.05; politics, finance and tech 0.04. The
  dataset has no geopolitics category, so geopolitical markets (fee 0) are charged as politics: slightly conservative.
- A buy also pays one tick above the observed price: 0.01, or 0.001 when the price is above 0.96 or below 0.04.
- Rebates, rewards and referral income are excluded: they go to makers, high-volume takers and promoters, not to a new
  retail taker.
- Applying today's fees to past prices asks "what would this strategy earn if you ran it now". Results without fees are
  reported alongside, as demonstrations.

## Test 1: who wins (descriptive)

- Population: wallets in `user_pnl_summary` joined to `user_features` with `total_volume` of at least $100. Wallets with
  $10-$100 are reported separately.
- Profit: `pnl_total` (realised plus marked-to-market at sample end, after the fees actually paid). The resolved-only and
  no-fee versions are reported for comparison.
- **Automated**: `trades_per_week` of at least 1,000 (one trade every ten minutes, around the clock). Everyone else is
  **human-paced**. **Maker-heavy**: `frac_maker_volume` of at least 0.5.
- Reported for all wallets, automated, human-paced, human-paced maker-heavy and human-paced taker-heavy, and by
  `total_volume` band ($100-1K, 1K-10K, 10K-100K, 100K-1M, over 1M):
  - share with a loss, share with a profit
  - median profit and the 1st, 10th, 90th and 99th percentiles
  - share of all positive profit going to the top 1% and top 0.1% of wallets
  - total profit of each group
- Expectations, stated in advance: most human-paced wallets lose; positive profit is concentrated, with the top 1% of
  wallets taking more than half.

## Test 2: luck or skill (descriptive, with a null)

- Data: `pnl_change_monthly`. Four non-overlapping splits, each forming on six months and evaluating on the next six:
  2023H2 then 2024H1; 2024H1 then 2024H2; 2024H2 then 2025H1; 2025H1 then 2025H2.
- Wallets: profit change not zero in the formation window. A wallet with no row in the evaluation window counts as zero.
  Segments: human-paced and automated (Test 1 definitions).
- Measures per split and segment:
  - Spearman correlation between formation and evaluation profit.
  - For the top 1% by formation profit: share profitable in evaluation, and mean and median evaluation profit.
- Null: shuffle evaluation profit among wallets in the same decile of absolute formation profit, 1,000 times
  (seed 2026). This compares big winners with big losers of the same size.
- **Skill persists** in a segment if the top 1%'s mean evaluation profit is above the null's 97.5th percentile in at
  least three of the four splits.
- Copying them is never better than their own result: a copier buys later, at worse prices. Their evaluation profit is
  an upper bound on copy-trading.

## Test 3: are the odds fair (descriptive, with confidence intervals)

- Markets: binary (`n_outcomes = 2`) with a recorded winner, closed by 2026-03-29. Both tokens of each market are used.
  If neither token is recorded as the winner, each pays 0.5.
- Price: the daily close (`ohlcv_1d`) on the UTC day H days before the market's close date. That day needs at least 5
  trades. H = 1, 7 and 30; **H = 7 is primary**.
- Bands: 5¢ wide, from 0-5¢ to 95-100¢.
- For each band:
  - average price and share that won
  - return per $1 staked before fees, after fees, and after fees plus one tick
  - 95% intervals from 1,000 bootstrap resamples of events (seed 2026)
- Statements tested at H = 7:
  - (a) Longshot bias: the 0-10¢ return is below the 90-100¢ return, and the bootstrap interval for the difference
    excludes zero.
  - (b) No free lunch for a retail taker: no band has an after-fees-and-tick return with a lower bound above zero. If
    one does, it is reported as a finding and tested in Test 4's style before being called an edge.

## Test 4: "bonds", buying at 95-99¢ (2 trials)

- Period: 2024-01-01 to 2026-03-29, starting with $1,000. Uninvested cash earns nothing.
- Each day, candidates are binary tokens that meet all of these:
  - a daily close between 0.95 and 0.99
  - at least 5 trades that day
  - a market close within D days
  - not already held
- Buy price: close plus one tick, plus the fee.
- Position size: the smallest of 2% of equity, the cash available, and 10% of that token's dollar volume that day.
  Candidates are taken in order of soonest close, then token id.
- Positions are held to resolution and paid out two days after the market's close time (oracle settlement).
- Variants: D = 7 and D = 30.
- Reported: CAGR, maximum drawdown, win rate, worst single loss, and the largest losses.
- **Beats cash** if the CAGR is above 3.75% and the lower bound of a 95% monthly block bootstrap of the CAGR
  (1,000 resamples, seed 2026) is also above 3.75%.

## Test 5: the 15-minute Bitcoin latency bot (6 trials)

- Windows: 15-minute BTC Up/Down markets in D2 flagged `usable_for_backtest`. The 5-minute markets are reported the same
  way as a secondary result.
- Fair chance of "Up" at time t: `Φ(ln(S_t / S_0) / (σ √τ))`, where:
  - S is the Binance BTCUSDT last trade price, and S_0 is the last Binance price at or before the window opens.
  - τ is the seconds left to the close.
  - σ is the standard deviation of 1-second Binance log returns over the previous 15 minutes, with a floor of 1e-6.
- Each 100 ms snapshot from window open until the betting deadline:
  - edge on Up = fair − Up best ask − fee at that ask; edge on Down likewise with 1 − fair.
  - If an edge exceeds the margin M, send a buy for 10 shares with a limit at that ask.
- The order executes against the first book snapshot at or after t + L, filling only at asks no higher than the limit,
  up to 10 shares across levels. Any unfilled part is cancelled. A failed order waits 1 second before retrying, and each
  window allows at most one filled entry.
- Settlement uses the recorded outcome. If none is recorded, Up wins when the Chainlink settlement price is at least the
  opening price.
- Profit per share is the payout minus the price minus the fee (feeRate 0.07).
- Variants: total delay L = 100 ms (London co-location), 300 ms (a fast home connection plus Polymarket's taker delay)
  or 1,000 ms; margin M = 1¢ or 3¢.
- Reported per variant, before and after the TWAP switch: windows traded, hit rate, mean profit per $1 staked,
  95% intervals from a bootstrap over windows (1,000 resamples, seed 2026), and total profit.
- **Works for retail** if a variant with L of at least 300 ms has a positive mean profit per $1, with the lower bound
  of a one-sided interval at level 1 − 0.05/6 above zero, both before and after the TWAP switch.
- Demonstrations, not trials: the same variants with zero fees, and with zero delay (filled at the snapshot that
  triggered the order), to show what a screenshot assumes.

## Test 6: the viral wallets (descriptive)

- Wallets:
  - `0x63ce342161250d705dc0b16df89036c8e5f9ba9a` (0x8dxd, "$313 into $414K")
  - `0xd0d6053c3c37e727402d84c14069780d360993aa` (the "$68 into $1.5M" account a paid bot copies)
  - `0xdf4c6a942bd95bf903d6066b4ba7051e6f914f22` (that vendor's own bot)
- Monthly realised profit from the Data API, plotted against the fee changes of 5 Jan, 6 Mar and 30 Mar 2026.

## Protocol

- 8 strategy trials in total (Tests 4 and 5), cap 12. Every run is logged to `experiments/trials.jsonl` with
  `"study": "polymarket"`.
- Tests 1-3 and 6 are descriptive and are not trials.
- Code that touches outcome data is written and unit-tested on synthetic data first.
- UK residents are geoblocked from opening positions on Polymarket, and the Gambling Commission and FCA treat these
  markets as off-limits to retail. No account is opened and no money is used.

## Clarifications, 2026-10-06, after Tests 1 and 6 and before Tests 2-5 were run

Made after reading the dataset's documentation. No outcome data for Tests 2-5 had been looked at.

- **Test 2:** `pnl_change_monthly` labels each month by its end: a row labelled 1 February holds January's change.
  Labels are shifted back one month, so 2024H1 means January to June 2024.
- **Test 3:** H counts days before the recorded close, as registered. Markets that can close early may close because the
  event happened, so we also report the same table using the scheduled expiration as a sensitivity check.
- **Test 4:** "a market close within D days" uses the scheduled expiration, which a buyer knows on the day. The recorded
  close is only known afterwards, and using it would be look-ahead. Payout is two days after the recorded close.
  "Dollar volume" is shares traded times the daily close.
- **Category "Untagged"** is charged the "other" fee rate of 0.05. Dataset timestamps are in nanoseconds (UTC).

## What would change our conclusions

- A segment of human-paced wallets that is profitable on average and persistent under Test 2.
- A price band with a reliably positive return after fees and a tick (Test 3), confirmed as a tradable portfolio.
- Either trial in Test 4, or any trial in Test 5, passing its rule above.
