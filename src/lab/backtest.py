"""Long-only spot simulator: a signal decided on a bar's close is filled at the next bar's open."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Weights that differ by less than this are equal; rounding can leave a fully invested weight at 1.0000000000000002.
MIN_REBALANCE = 1e-9


@dataclass(frozen=True)
class Result:
    capital: float
    equity: pd.Series  # marked to market at each bar's close
    weight: pd.Series  # asset weight at each bar's close
    fees: float  # total fees paid, in currency
    trades: int  # number of fills


def simulate(
    bars: pd.DataFrame,
    target: pd.Series,
    fee: float,
    capital: float = 1000.0,
    band: float = 0.0,
    lag: int = 1,
) -> Result:
    """Trade towards `target`, an asset weight between 0 and 1 decided on each bar's close.

    Orders only go through when the target is more than `band` away from the current weight.
    A NaN target leaves the position unchanged. lag=1 fills at the next bar's open, the only
    honest choice; lag=0 fills at the open of the bar whose close produced the signal, which
    exists solely to demonstrate look-ahead bias.
    """
    opens = bars["open"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    goals = target.reindex(bars.index).to_numpy(dtype=float)
    n = len(bars)
    cash, units, fees, trades = capital, 0.0, 0.0, 0
    equity = np.empty(n)
    weight = np.empty(n)
    for i in range(n):
        j = i - lag
        if j >= 0 and not np.isnan(goals[j]):
            price = opens[i]
            value = cash + units * price
            current = units * price / value
            goal = min(max(goals[j], 0.0), 1.0)
            if abs(goal - current) > max(band, MIN_REBALANCE):
                if goal > current:
                    spend = min((goal - current) * value, cash / (1 + fee))
                    units += spend / price
                    cash -= spend * (1 + fee)
                    fees += spend * fee
                else:
                    proceeds = units * price if goal == 0.0 else (current - goal) * value
                    units = 0.0 if goal == 0.0 else units - proceeds / price
                    cash += proceeds * (1 - fee)
                    fees += proceeds * fee
                trades += 1
        equity[i] = cash + units * closes[i]
        weight[i] = units * closes[i] / equity[i]
    return Result(
        capital=capital,
        equity=pd.Series(equity, index=bars.index, name="equity"),
        weight=pd.Series(weight, index=bars.index, name="weight"),
        fees=fees,
        trades=trades,
    )


def buy_and_hold(bars: pd.DataFrame, fee: float, capital: float = 1000.0) -> Result:
    """Fully invested from the first bar's open; a constant target carries no look-ahead."""
    return simulate(bars, pd.Series(1.0, index=bars.index), fee, capital, lag=0)


def monthly_buying(bars: pd.DataFrame, fee: float, capital: float = 1000.0, months: int = 12) -> Result:
    """Invest `capital` in equal purchases at the first open of each of the first `months` months, then hold."""
    opens = bars["open"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    month = bars.index.tz_localize(None).to_period("M")
    first_of_month = np.r_[True, month[1:] != month[:-1]]
    buy_bars = set(np.flatnonzero(first_of_month)[:months].tolist())
    tranche = capital / months
    cash, units, fees = capital, 0.0, 0.0
    equity = np.empty(len(bars))
    weight = np.empty(len(bars))
    for i in range(len(bars)):
        if i in buy_bars:
            spend = tranche / (1 + fee)
            units += spend / opens[i]
            cash -= tranche
            fees += spend * fee
        equity[i] = cash + units * closes[i]
        weight[i] = units * closes[i] / equity[i]
    return Result(
        capital=capital,
        equity=pd.Series(equity, index=bars.index, name="equity"),
        weight=pd.Series(weight, index=bars.index, name="weight"),
        fees=fees,
        trades=len(buy_bars),
    )
