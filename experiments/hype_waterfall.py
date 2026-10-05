"""How a viral backtest is made: the pitch's numbers with every cheat on, then each cheat removed.

Every step reuses the pre-registered variants and the same simulator; nothing here is a new trial.
Runs are logged to the ledger as demonstrations so they can never inflate the trial count.

Usage: uv run python experiments/hype_waterfall.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lab import ledger
from lab.backtest import Result, buy_and_hold, simulate
from lab.costs import FEE_SCENARIOS
from lab.data import REPO_ROOT, binance_klines
from lab.metrics import daily_returns, summarize
from lab.strategies import PREREGISTERED, Variant

RESULTS = REPO_ROOT / "experiments" / "results"
TEST = slice("2023-01-01", "2026-09-30")
RANDOM_SEED = 0
RANDOM_STRATEGIES = 13  # as many as the pre-registered trials
RANDOM_SWITCH_CHANCE = 1 / 20  # flips between holding and cash about every 20 days, like the real strategies


def run(variant: Variant, bars: dict[str, pd.DataFrame], fee: str, lag: int) -> Result:
    candles = bars[variant.interval]
    return simulate(candles, variant.target(candles), FEE_SCENARIOS[fee], band=variant.band, lag=lag)


def win_rate(result: Result) -> tuple[float, int]:
    """Share of holding spells that ended in profit, for strategies that are either fully in or out."""
    r = daily_returns(result)
    held = result.weight.resample("1D").last().reindex(r.index).fillna(0) > 0.5
    spell = (held != held.shift(fill_value=False)).cumsum()[held]
    per_spell = (1 + r[held]).groupby(spell).prod() - 1
    return float((per_spell > 0).mean()), int(len(per_spell))


def weekly_growth(returns: pd.Series) -> list[float]:
    return [round(float(v), 2) for v in (1000 * (1 + returns).cumprod()).resample("W").last()]


def best_of_13(bars: dict[str, pd.DataFrame], fee: str, lag: int) -> tuple[Variant, Result]:
    runs = {v.name: (v, run(v, bars, fee, lag)) for v in PREREGISTERED}
    for name, (v, result) in runs.items():
        ledger.append({"event": "demo_run", "demo": "hype_waterfall", "variant": name, "asset": "BTC", "fee": fee,
                       "lag": lag, "counts_as_trial": False, "final_value": float(result.equity.iloc[-1])})
    return max(runs.values(), key=lambda vr: vr[1].equity.iloc[-1])


def step(label: str, variant: Variant, result: Result, explain: str) -> dict:
    r = daily_returns(result)
    stats = summarize(r)
    wins, spells = win_rate(result)
    return {
        "label": label,
        "variant": variant.name,
        "final_value": round(float(result.equity.iloc[-1]), 2),
        "total_return": stats["total_return"],
        "cagr": stats["cagr"],
        "sharpe": stats["sharpe"],
        "max_drawdown": stats["max_drawdown"],
        "win_rate": wins,
        "holding_spells": spells,
        "trades": result.trades,
        "explain": explain,
        "growth_weekly": weekly_growth(r),
    }


def random_strategies(daily: pd.DataFrame, fee: str) -> list[dict]:
    rng = np.random.default_rng(RANDOM_SEED)
    out = []
    for k in range(RANDOM_STRATEGIES):
        flips = rng.random(len(daily)) < RANDOM_SWITCH_CHANCE
        holding = (np.cumsum(flips) % 2 == 1).astype(float)
        result = simulate(daily, pd.Series(holding, index=daily.index), FEE_SCENARIOS[fee])
        r = daily_returns(result)
        out.append({"name": f"coin-flip strategy {k + 1}", "final_value": round(float(result.equity.iloc[-1]), 2),
                    "sharpe": summarize(r)["sharpe"], "growth_weekly": weekly_growth(r)})
    ledger.append({"event": "demo_run", "demo": "random_strategies", "asset": "BTC", "fee": fee, "seed": RANDOM_SEED,
                   "counts_as_trial": False, "final_values": [s["final_value"] for s in out]})
    return out


def main() -> None:
    ledger.check_preregistration()
    btc = {interval: binance_klines("BTC", interval) for interval in ("1d", "4h")}
    summary = json.loads((RESULTS / "backtest_summary.json").read_text())
    trend = summary["families"]["trend"]

    bh_article = buy_and_hold(btc["1d"], FEE_SCENARIOS["article"])
    bh_taker = buy_and_hold(btc["1d"], FEE_SCENARIOS["kraken_taker"])

    v0, r0 = best_of_13(btc, "article", lag=0)
    v1, r1 = best_of_13(btc, "article", lag=1)
    v2, r2 = best_of_13(btc, "kraken_taker", lag=1)
    selected = next(v for v in PREREGISTERED if v.name == trend["selected"])
    r3 = run(selected, btc, "kraken_taker", lag=1)

    test_strategy = daily_returns(r3).loc[TEST]
    test_hold = daily_returns(bh_taker).loc[TEST]

    data = {
        "since": str(btc["1d"].index[0].date()),
        "until": str(btc["1d"].index[-1].date()),
        "weeks": [str(d.date()) for d in (1 + daily_returns(r0)).cumprod().resample("W").last().index],
        "buy_and_hold": {
            "final_value": round(float(bh_taker.equity.iloc[-1]), 2),
            "final_value_article_fees": round(float(bh_article.equity.iloc[-1]), 2),
            **{k: summarize(daily_returns(bh_taker))[k] for k in ("cagr", "sharpe", "max_drawdown", "longest_drawdown_days")},
            "growth_weekly": weekly_growth(daily_returns(bh_taker)),
        },
        "steps": [
            step("Every cheat on", v0, r0,
                 "Best of 13 strategies picked after seeing the results, trading on each day's closing price before it was known, at the X article's 0.08% fee."),
            step("Peeking switched off", v1, r1,
                 "Same hindsight pick and fantasy fee, but every trade now waits for information that actually existed."),
            step("Real fees switched on", v2, r2,
                 "Kraken's 0.85% retail taker fee per trade, including slippage, instead of 0.08%."),
        ],
        "hindsight": {
            "variant": selected.name,
            "explain": "The strategy is chosen using 2017-2022 only, then judged on 2023 to Sep 2026, data it never saw.",
            "test_period": [TEST.start, TEST.stop],
            "strategy_final_value": round(float(1000 * (1 + test_strategy).prod()), 2),
            "buy_and_hold_final_value": round(float(1000 * (1 + test_hold).prod()), 2),
            "strategy_sharpe": summarize(test_strategy)["sharpe"],
            "buy_and_hold_sharpe": summarize(test_hold)["sharpe"],
            "strategy_growth_weekly": weekly_growth(test_strategy),
            "buy_and_hold_growth_weekly": weekly_growth(test_hold),
            "weeks": [str(d.date()) for d in (1 + test_hold).cumprod().resample("W").last().index],
        },
        "luck": {
            "deflated_sharpe": trend["deflated_sharpe"]["dsr"],
            "lenient_deflated_sharpe": trend["post_hoc_lenient_dsr"],
            "trials": summary["trials_logged"],
            "seed": RANDOM_SEED,
            "fee": "article",
            "strategy_final_value_article_fees": round(float(run(selected, btc, "article", lag=1).equity.iloc[-1]), 2),
            "random": random_strategies(btc["1d"], "article"),
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "hype_waterfall.json").write_text(json.dumps(data, indent=1, default=float))

    print(f"Buy and hold: 1,000 -> {data['buy_and_hold']['final_value']:,.0f}")
    for s in data["steps"]:
        print(f"{s['label']:<24} {s['variant']:<28} 1,000 -> {s['final_value']:>16,.0f}  CAGR {s['cagr']:>8.0%}  "
              f"Sharpe {s['sharpe']:.2f}  max DD {s['max_drawdown']:.0%}  wins {s['win_rate']:.0%} of {s['holding_spells']}")
    h = data["hindsight"]
    print(f"No hindsight, {h['variant']} on 2023-2026: 1,000 -> {h['strategy_final_value']:,.0f} vs hold {h['buy_and_hold_final_value']:,.0f}")
    finals = sorted(s["final_value"] for s in data["luck"]["random"])
    print(f"13 coin-flip strategies at 0.08% fees: best {finals[-1]:,.0f}, median {finals[6]:,.0f}, worst {finals[0]:,.0f}; "
          f"our pick {data['luck']['strategy_final_value_article_fees']:,.0f}")


if __name__ == "__main__":
    main()
