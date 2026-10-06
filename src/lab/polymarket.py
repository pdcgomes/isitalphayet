"""Polymarket costs, statistics and the order-book fill simulator, as fixed in experiments/polymarket/preregistration.md."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

FEE_RATES = {"crypto": 0.07, "sports": 0.05, "culture": 0.05, "weather": 0.05, "other": 0.05,
             "politics": 0.04, "finance": 0.04, "tech": 0.04}
CRYPTO_FEE_RATE = FEE_RATES["crypto"]
SEED = 2026


def fee_rate(category: str | None) -> float:
    return FEE_RATES.get((category or "other").lower(), FEE_RATES["other"])


def taker_fee(price, rate):
    """Fee per share for a taker buying at `price`: rate x p x (1 - p)."""
    price = np.asarray(price, dtype=float)
    return rate * price * (1 - price)


def tick(price):
    price = np.asarray(price, dtype=float)
    return np.where((price > 0.96) | (price < 0.04), 0.001, 0.01)


def buy_price(price):
    """The observed price plus one tick, capped below $1."""
    price = np.asarray(price, dtype=float)
    return np.minimum(price + tick(price), 0.999)


def return_per_dollar(cost_per_share, payout):
    """Return on $1 spent on shares costing `cost_per_share` (price plus fee) that pay `payout` each."""
    return np.asarray(payout, dtype=float) / np.asarray(cost_per_share, dtype=float) - 1


def price_band(price, width: float = 0.05):
    """Index of the price band: 0 for 0-5¢ up to 19 for 95-100¢."""
    n = int(round(1 / width))
    return np.clip(np.floor(np.asarray(price, dtype=float) * n), 0, n - 1).astype(int)


def cluster_bootstrap_mean(values, clusters, n: int = 1000, seed: int = SEED, level: float = 0.95):
    """Mean of `values` and a percentile interval from resampling whole clusters (events) with replacement."""
    values = np.asarray(values, dtype=float)
    _, idx = np.unique(np.asarray(clusters), return_inverse=True)
    sums = np.bincount(idx, weights=values)
    counts = np.bincount(idx).astype(float)
    rng = np.random.default_rng(seed)
    k = len(sums)
    stats = np.empty(n)
    for b in range(n):
        w = np.bincount(rng.integers(0, k, k), minlength=k)
        stats[b] = (w @ sums) / (w @ counts)
    tail = (1 - level) / 2
    return float(values.mean()), float(np.quantile(stats, tail)), float(np.quantile(stats, 1 - tail))


def bootstrap_mean(values, n: int = 1000, seed: int = SEED):
    """Bootstrap distribution of the mean (each value its own cluster)."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    return np.array([values[rng.integers(0, len(values), len(values))].mean() for _ in range(n)])


def stratified_permutation_null(evaluation, strata, selected, n: int = 1000, seed: int = SEED):
    """Mean evaluation profit of the selected wallets when evaluation profits are shuffled within strata.

    Under pure luck, being a big winner says nothing about next period beyond size, so the selected wallets should do
    no better than equally large losers.
    """
    evaluation = np.asarray(evaluation, dtype=float)
    strata = np.asarray(strata)
    selected = np.asarray(selected, dtype=bool)
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(strata == s) for s in np.unique(strata[selected])]
    out = np.empty(n)
    for b in range(n):
        total, count = 0.0, 0
        for g in groups:
            picks = selected[g].sum()
            total += rng.choice(evaluation[g], size=picks, replace=False).sum()
            count += picks
        out[b] = total / count
    return out


def cagr(equity, days: float) -> float:
    return float((equity[-1] / equity[0]) ** (365 / days) - 1)


def block_bootstrap_cagr(daily_returns, block: int = 30, n: int = 1000, seed: int = SEED):
    """CAGRs of series rebuilt from randomly drawn blocks of consecutive days."""
    r = np.asarray(daily_returns, dtype=float)
    rng = np.random.default_rng(seed)
    starts_max = len(r) - block
    out = np.empty(n)
    for b in range(n):
        picks = []
        while sum(len(p) for p in picks) < len(r):
            s = rng.integers(0, starts_max + 1)
            picks.append(r[s:s + block])
        sample = np.concatenate(picks)[: len(r)]
        out[b] = np.prod(1 + sample) ** (365 / len(r)) - 1
    return out


def fair_up(log_return, sigma, seconds_left):
    """Chance the price ends at or above the open, for a driftless random walk with per-second volatility `sigma`."""
    spread = np.asarray(sigma, dtype=float) * np.sqrt(np.maximum(np.asarray(seconds_left, dtype=float), 1e-9))
    return norm.cdf(np.asarray(log_return, dtype=float) / spread)


def best_asks(levels) -> np.ndarray:
    """Lowest ask at each snapshot, NaN where the book side is empty."""
    return np.array([min(a) if a is not None and len(a) else np.nan for a in levels], dtype=float)


def walk_book(ask_prices, ask_sizes, limit: float, shares: float) -> tuple[float, float]:
    """Buy up to `shares` at asks no higher than `limit`, cheapest first. Returns (shares filled, dollars paid)."""
    filled = paid = 0.0
    for px, sz in sorted(zip(ask_prices, ask_sizes)):
        if px > limit + 1e-12 or filled >= shares:
            break
        take = min(sz, shares - filled)
        filled += take
        paid += take * px
    return filled, paid


@dataclass(frozen=True)
class Fill:
    side: str          # "up" or "down"
    signal_ms: int
    fill_ms: int
    shares: float
    avg_price: float
    fee_per_share: float


def simulate_window(ts_ms, fair, up_asks, up_sizes, down_asks, down_sizes, deadline_ms: int, delay_ms: int,
                    margin: float, fee_rate_: float = CRYPTO_FEE_RATE, shares: float = 10.0,
                    retry_ms: int = 1000, best_up=None, best_down=None) -> Fill | None:
    """Replay one market window: signal on each snapshot, execute against the first snapshot at or after the delay.

    `up_asks[i]` / `up_sizes[i]` are the ask levels at snapshot i (lists). `fair[i]` is the fair chance of "Up" using
    only information up to `ts_ms[i]`. At most one filled entry per window; a missed order waits `retry_ms`.
    """
    ts_ms = np.asarray(ts_ms)
    fair = np.asarray(fair, dtype=float)
    best_up = best_asks(up_asks) if best_up is None else np.asarray(best_up, dtype=float)
    best_down = best_asks(down_asks) if best_down is None else np.asarray(best_down, dtype=float)
    edge_up = fair - best_up - taker_fee(best_up, fee_rate_)
    edge_down = (1 - fair) - best_down - taker_fee(best_down, fee_rate_)
    edge_up, edge_down = np.nan_to_num(edge_up, nan=-np.inf), np.nan_to_num(edge_down, nan=-np.inf)
    signals = np.flatnonzero((np.maximum(edge_up, edge_down) > margin) & (ts_ms <= deadline_ms))
    next_try = -np.inf
    for i in signals:
        t = ts_ms[i]
        if t < next_try:
            continue
        side, limit = ("up", best_up[i]) if edge_up[i] >= edge_down[i] else ("down", best_down[i])
        j = int(np.searchsorted(ts_ms, t + delay_ms, side="left"))
        if j >= len(ts_ms) or ts_ms[j] > deadline_ms:
            break
        asks, sizes = (up_asks[j], up_sizes[j]) if side == "up" else (down_asks[j], down_sizes[j])
        got, paid = walk_book(asks if asks is not None else [], sizes if sizes is not None else [], limit, shares)
        if got > 0:
            avg = paid / got
            return Fill(side, int(t), int(ts_ms[j]), got, avg, float(taker_fee(avg, fee_rate_)))
        next_try = t + retry_ms
    return None
