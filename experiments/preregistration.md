# Pre-registration

Written 2026-10-05, before any backtest or TradingAgents run. The SHA-256 of this file is written to `trials.jsonl` before the first run. Any later edit is logged as a new event rather than silently replacing these rules.

## Questions

1. Do simple, well-known crypto strategies beat buy-and-hold after realistic UK retail costs, once we correct for the number of things tried?
2. Does TradingAgents (v0.6.0, OpenAI defaults) show any timing skill on BTC and ETH, on dates its models cannot have seen?

## Data

- BTCUSDT and ETHUSDT daily and 4-hour candles from Binance's public data (`data.binance.vision`), 2017-08-17 to 2026-09-30.
- Kraken `XBTGBP` candles for paper trading.
- Design period: 2017-08-17 to 2022-12-31. Test period: 2023-01-01 to 2026-09-30.
- ETH is a holdout: it is not looked at until the BTC evaluation is final.

## Execution and costs

- Signals are computed on a closed bar and filled at the next bar's open.
- Long-only spot: the weight in the asset is between 0 and 1. No leverage, no shorting.
- Starting capital: 1,000.
- Fees per side, including 0.05% slippage for the Kraken scenarios:
  - `article`: 0.08% (what the X article assumes)
  - `kraken_maker`: 0.45% (Kraken Pro tier 1 maker)
  - `kraken_taker`: 0.85% (Kraken Pro tier 1 taker); **all gates use this one**
- Sharpe: daily returns, annualised with 365 days, risk-free rate 0. Calmar: annual growth rate divided by the size of the maximum drawdown.
- 4-hour strategies are scored on daily returns (equity at each day's last 4-hour close), so every trial shares one frequency for the deflated Sharpe.

## Benchmarks (not trials)

- Buy-and-hold: bought at the first bar's open, paying one taker fee.
- Monthly buying (DCA): the starting capital invested in 12 equal monthly purchases, then held.

## Strategies and variants: 13 trials, cap 20

1. **Trend filter** (daily): long when close is above its n-day simple moving average, otherwise cash. n = 50, 100, 200.
2. **Time-series momentum** (daily): long when today's close is above the close L days ago. L = 14, 28, 56.
3. **Volatility-targeted trend** (daily): the 200-day trend filter, with weight = min(1, target volatility / 30-day realised volatility, annualised). Rebalances only when the target weight is more than 0.10 away from the current weight. Target = 40%, 60%.
4. **RSI mean reversion** (4-hour): 14-bar Wilder RSI. Buy when RSI falls below X; sell when RSI rises above 50. X = 20, 25, 30.
5. **Grid bot** (4-hour): every 30 days, centre a range of plus or minus R% on the current close, with 10 levels. Target weight = share of grid levels above the current price, so it holds more as the price falls. R = 10%, 20%.

Every run is appended to `trials.jsonl`. A trial is a distinct variant run on BTC. Adding a variant adds a trial, and the deflated Sharpe's trial count rises with it. No more variants once the ledger reaches 20.

## Protocol

1. Run every variant on BTC under all three fee scenarios and log every run.
2. In each family, select the variant with the best design-period Sharpe after taker fees.
3. Judge each family's selected variant against the gates.
4. Only once step 3 is final, run the selected variants on ETH.

## Gates (all four required, all after taker fees)

1. **Out of sample:** over the test period, Sharpe or Calmar is higher than BTC buy-and-hold's.
2. **Deflated Sharpe ≥ 0.95:** on full-period BTC daily returns. N = every BTC variant logged. The variance term is the spread of their Sharpe ratios (Bailey and López de Prado, 2014).
3. **Walk-forward:** 6-month folds starting 2019-07-01, so the first fold has two years of history behind it. At each fold boundary, the family's variant with the best Sharpe on all earlier data is chosen. That choice must have a positive Sharpe in at least 60% of folds.
4. **ETH holdout:** over ETH's full period, Sharpe or Calmar is higher than ETH buy-and-hold's.

Reported but not used as gates:

- A 95% block-bootstrap interval for the Sharpe difference against buy-and-hold (20-day blocks, 2,000 resamples).
- A bull/bear/sideways regime split, based on the 200-day moving average and its 20-day slope.
- Results under the other two fee scenarios.

## Leakage demonstration (not a trial)

The 200-day trend filter is also run with the order filled at the open of the same bar whose close produced the signal. That is look-ahead bias. It should look far better, which shows why the one-bar delay matters. It is excluded from the trial count.

## TradingAgents protocol

- **Version and models:** TradingAgents v0.6.0 on OpenAI, `gpt-6-luna` for the quick tier and `gpt-6-sol` for the deep tier. Every other setting is left at its default.
- **Clean window:** weekly analysis dates, every Monday from 2026-06-01 to 2026-09-28 (18 dates). All are after both models' knowledge cutoffs (2026-05-18 and 2026-04-20).
- **Tickers:** `BTC-USD` and `ETH-USD`. `NVDA` only if the budget allows.
- **Budget:** $35 hard stop in code (about £27), under your £30 dashboard cap.
- **Cost probe first:** one `BTC-USD` decision dated 2026-06-01. It counts as part of the grid.
- **Rating to exposure:** Buy 1.0, Overweight 0.75, Hold 0.5, Underweight 0.25, Sell 0. Each exposure is held for 7 days until the next decision. Taker fees apply on exposure changes.
- **Scoring:**
  - Return of the rating-driven exposure against buy-and-hold over the same weeks.
  - Timing skill: return against a constant exposure equal to the agent's average exposure.
  - Hit rate: Buy and Overweight are hits if the 7-day return is above 0; Sell and Underweight are hits if it is below 0; Hold is excluded.
  - Cost per decision, in USD.
- **Evidence of skill:** a one-sided binomial p-value below 0.05 on the hit rate, and positive timing skill after fees. With about 36 directional calls, that needs a hit rate of roughly 64% or more.
- **Repeatability:** `BTC-USD` dated 2026-09-28, run 3 times, each with a fresh memory log. Report how often the rating differs.
- **Forward test:** every Monday from 2026-10-05 to 2026-11-23 (8 dates) on `BTC-USD` and `ETH-USD`, scored the same way.

## Paper trading

- **Start:** 2026-10-05, with 1,000 GBP of paper capital, on Kraken `XBTGBP` candles. Runs for 8 weeks.
- **Strategy:** the family that passed all gates. If none did, the one with the highest deflated Sharpe, labelled a plumbing test.
- **Mechanics:** the same signal code as the backtest. Fills at the next open, with taker fee and slippage.
- **Ledger:** append-only. Each row stores the signal as computed that day, so it can later be compared with a fresh recomputation over the same candles.

## Live friction test (only with your explicit go-ahead)

- **Preconditions:**
  - A strategy passed all four gates.
  - Paper trading showed live signals matching the recomputed ones.
  - You decided to go ahead.
- **Setup:**
  - A personal machine and an exchange on the FCA register.
  - Spot only, at most 250 GBP.
  - An API key that can trade but not withdraw, restricted to your IP address.
- **Stop immediately if any of these happens:**
  - The drawdown exceeds the smaller of 1.5 times the backtest maximum drawdown and 30%.
  - Across the first 5 fills, live fill prices differ from the paper fill prices by more than 0.5% on average.
  - Any order, balance or permission appears that the strategy did not intend.
- **Duration:** stop after 8 weeks regardless, then review.
- **Benchmark:** buy-and-hold, calculated from prices rather than bought.
- **Records:** every fill exported for HMRC.

## What would change our conclusions

- A strategy passing all four gates becomes a genuine paper-trading candidate.
- TradingAgents meeting the evidence-of-skill bar in both the clean window and the forward test would justify a longer forward test, though it would still be far from proven.
