"""Audit the code published in the viral "$200,000 quant stack" X Article (30 Aug 2026).

The article's functions are reproduced as published so their behaviour can be checked:
its deflated-Sharpe gate, its walk-forward function and its cost assumption.

Usage: uv run python experiments/article_audit.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

from lab.costs import FEE_SCENARIOS
from lab.data import REPO_ROOT, binance_klines
from lab.stats import expected_max_z, probabilistic_sharpe

RESULTS = REPO_ROOT / "experiments" / "results"


# ---- As published in the article (unchanged apart from formatting) ----

@dataclass
class Config:
    initial_capital: float = 10_000
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    max_leverage: float = 1.0
    periods_per_year: int = 365


def article_backtest(prices, signal, cfg):
    position = signal.shift(1).fillna(0).clip(-cfg.max_leverage, cfg.max_leverage)
    returns = np.log(prices / prices.shift(1)).fillna(0)
    gross = position * returns
    turnover = position.diff().abs().fillna(0)
    costs = turnover * (cfg.fee_bps + cfg.slippage_bps) / 1e4
    net = gross - costs
    equity = cfg.initial_capital * np.exp(net.cumsum())
    return pd.DataFrame({"position": position, "gross": gross, "costs": costs, "net": net, "equity": equity})


def article_metrics(net, cfg):
    r = net.dropna()
    if len(r) < 100:
        return {"error": "insufficient_data"}
    ann_return = r.mean() * cfg.periods_per_year
    ann_vol = r.std() * np.sqrt(cfg.periods_per_year)
    return {"sharpe": round(ann_return / ann_vol if ann_vol > 0 else 0, 2)}


def article_walk_forward(prices, strategy_fn, cfg, train_days=180, test_days=60):
    results = []
    i = 0
    while i + train_days + test_days <= len(prices):
        train = prices.iloc[i: i + train_days]
        test = prices.iloc[i + train_days: i + train_days + test_days]
        params = strategy_fn(train)
        signal = params["signal_fn"](test)
        bt = article_backtest(test, signal, cfg)
        results.append({"start": test.index[0], **article_metrics(bt["net"], cfg)})
        i += test_days
    df = pd.DataFrame(results)
    return {
        "folds": df,
        "mean_sharpe": round(df["sharpe"].mean(), 2),
        "positive_folds": f"{(df['sharpe'] > 0).sum()}/{len(df)}",
        "worst_fold": round(df["sharpe"].min(), 2),
    }


def article_deflated_sharpe(sharpe, n_trials, n_obs, skew=0.0, kurtosis=3.0):
    euler = 0.5772156649
    expected_max = (1 - euler) * norm.ppf(1 - 1 / n_trials) + euler * norm.ppf(1 - 1 / (n_trials * np.e))
    denom = np.sqrt(1 - skew * sharpe + ((kurtosis - 1) / 4) * sharpe**2)
    return norm.cdf((sharpe - expected_max) * np.sqrt(n_obs - 1) / denom)


# ---- The audit ----

def correct_deflated_sharpe(annual_sharpe: float, n_trials: int, n_obs: int) -> float:
    """Bailey & López de Prado with per-period Sharpe and, under the null, trial-Sharpe spread of 1/sqrt(T)."""
    sr = annual_sharpe / np.sqrt(365)
    return probabilistic_sharpe(sr, n_obs, 0.0, 3.0, expected_max_z(n_trials) / np.sqrt(n_obs))


def lowest_passing_sharpe(dsr_fn, n_trials: int, n_obs: int) -> float:
    grid = np.round(np.arange(0.0, 6.0, 0.01), 2)
    return float(next(s for s in grid if dsr_fn(s, n_trials, n_obs) > 0.95))


def main() -> None:
    trials = 80  # the article's own example: "You tested 80 variations"
    lengths = {"1 year": 365, "4 years": 4 * 365, "8 years": 8 * 365}
    gate = {
        name: {"article": lowest_passing_sharpe(article_deflated_sharpe, trials, n),
               "correct": lowest_passing_sharpe(correct_deflated_sharpe, trials, n)}
        for name, n in lengths.items()
    }

    close = binance_klines("BTC", "1d")["close"]
    always_long = {"signal_fn": lambda prices: pd.Series(1.0, index=prices.index)}
    try:
        article_walk_forward(close, lambda train: always_long, Config())
        walk_forward = {"crashes": False, "error": None}
    except KeyError as exc:
        walk_forward = {"crashes": True, "error": f"KeyError: {exc}"}

    article_cost = (Config.fee_bps + Config.slippage_bps) / 1e4
    data = {
        "trials": trials,
        "deflated_sharpe_gate": gate,
        "walk_forward_defaults": {"train_days": 180, "test_days": 60, "metrics_minimum_observations": 100, **walk_forward},
        "costs": {
            "article_per_side": article_cost,
            "kraken_taker_per_side": FEE_SCENARIOS["kraken_taker"],
            "ratio": FEE_SCENARIOS["kraken_taker"] / article_cost,
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "article_audit.json").write_text(json.dumps(data, indent=2))
    for name, g in gate.items():
        print(f"{name} of data, {trials} trials: article's gate passes from Sharpe {g['article']:.2f}; correct gate from {g['correct']:.2f}")
    print("Walk-forward with its own defaults:", walk_forward)
    print(f"Costs: article {article_cost:.2%} per side vs Kraken taker {FEE_SCENARIOS['kraken_taker']:.2%} "
          f"({data['costs']['ratio']:.1f}x)")


if __name__ == "__main__":
    main()
