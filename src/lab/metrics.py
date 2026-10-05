"""Headline metrics, always on daily returns so strategies of any bar frequency compare like for like."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import Result

DAYS_PER_YEAR = 365


def daily_returns(result: Result) -> pd.Series:
    """Simple returns between the last marks of consecutive UTC days, starting from the initial capital."""
    daily = result.equity.resample("1D").last().dropna()
    previous = daily.shift(1)
    previous.iloc[0] = result.capital
    return (daily / previous - 1).rename("return")


def summarize(returns: pd.Series) -> dict:
    """Growth, risk and drawdown statistics for a series of daily simple returns."""
    r = returns.to_numpy(dtype=float)
    growth = np.cumprod(1 + r)
    peaks = np.maximum.accumulate(np.r_[1.0, growth])[1:]
    drawdown = growth / peaks - 1
    cagr = growth[-1] ** (DAYS_PER_YEAR / len(r)) - 1
    sd = r.std(ddof=1)
    max_dd = float(drawdown.min())
    longest = run = 0
    for underwater in drawdown < 0:
        run = run + 1 if underwater else 0
        longest = max(longest, run)
    return {
        "total_return": float(growth[-1] - 1),
        "cagr": float(cagr),
        "volatility": float(sd * np.sqrt(DAYS_PER_YEAR)),
        "sharpe": float(r.mean() / sd * np.sqrt(DAYS_PER_YEAR)) if sd > 0 else 0.0,
        "max_drawdown": max_dd,
        "calmar": float(cagr / abs(max_dd)) if max_dd < 0 else float("nan"),
        "longest_drawdown_days": longest,
        "days": len(r),
    }


def trading_stats(result: Result) -> dict:
    """How much the strategy traded and what it paid for the privilege."""
    years = (result.equity.index[-1] - result.equity.index[0]).days / DAYS_PER_YEAR
    return {
        "trades": result.trades,
        "fees_paid": result.fees,
        "annual_fee_drag": float(result.fees / result.equity.mean() / years),
        "average_exposure": float(result.weight.mean()),
    }
