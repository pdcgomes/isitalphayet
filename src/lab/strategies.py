"""The pre-registered strategies. Each turns candles into a target asset weight decided at every close."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def trend(close: pd.Series, n: int) -> pd.Series:
    sma = close.rolling(n).mean()
    return (close > sma).astype(float).where(sma.notna())


def tsmom(close: pd.Series, lookback: int) -> pd.Series:
    past = close.shift(lookback)
    return (close > past).astype(float).where(past.notna())


def vol_target(close: pd.Series, target_vol: float) -> pd.Series:
    realised = close.pct_change().rolling(30).std() * np.sqrt(365)
    return trend(close, 200) * (target_vol / realised).clip(upper=1.0)


def wilder_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + gain / loss)


def rsi_reversion(close: pd.Series, entry: float, exit_level: float = 50.0) -> pd.Series:
    rsi = wilder_rsi(close).to_numpy()
    out = np.full(len(rsi), np.nan)
    holding = 0.0
    for i, value in enumerate(rsi):
        if np.isnan(value):
            continue
        if holding == 0.0 and value < entry:
            holding = 1.0
        elif holding == 1.0 and value > exit_level:
            holding = 0.0
        out[i] = holding
    return pd.Series(out, index=close.index)


def grid(close: pd.Series, half_range: float, levels: int = 10, recentre_bars: int = 180) -> pd.Series:
    """Share of grid levels above the price; the grid re-centres on the close every `recentre_bars` bars."""
    prices = close.to_numpy()
    centre = prices[(np.arange(len(prices)) // recentre_bars) * recentre_bars]
    upper = centre * (1 + half_range)
    step = centre * 2 * half_range / levels
    # Levels sit at the middle of each step, so this counts the levels strictly above the price.
    above = np.clip(np.ceil((upper - prices) / step - 0.5), 0, levels)
    return pd.Series(above / levels, index=close.index)


_FAMILIES = {"trend": trend, "tsmom": tsmom, "vol_target": vol_target, "rsi": rsi_reversion, "grid": grid}


@dataclass(frozen=True)
class Variant:
    family: str
    params: tuple[tuple[str, float], ...]
    interval: str
    band: float = 0.0

    @property
    def name(self) -> str:
        return f"{self.family}({', '.join(f'{k}={v:g}' for k, v in self.params)})"

    def target(self, bars: pd.DataFrame) -> pd.Series:
        return _FAMILIES[self.family](bars["close"], **dict(self.params))


def _variant(family: str, interval: str, band: float = 0.0, **params: float) -> Variant:
    return Variant(family, tuple(params.items()), interval, band)


FAMILIES = ["trend", "tsmom", "vol_target", "rsi", "grid"]

PREREGISTERED = [
    *[_variant("trend", "1d", n=n) for n in (50, 100, 200)],
    *[_variant("tsmom", "1d", lookback=days) for days in (14, 28, 56)],
    *[_variant("vol_target", "1d", band=0.10, target_vol=t) for t in (0.4, 0.6)],
    *[_variant("rsi", "4h", entry=x) for x in (20, 25, 30)],
    # A band of half a grid step trades only when a level is crossed, not on drift within a level.
    *[_variant("grid", "4h", band=0.05, half_range=r) for r in (0.10, 0.20)],
]

LEAKY_DEMO = _variant("trend", "1d", n=200)
