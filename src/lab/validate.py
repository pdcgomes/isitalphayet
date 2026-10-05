"""Out-of-sample checks: walk-forward selection, market-regime split and the pre-registered gates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import DAYS_PER_YEAR


def _sharpe(r: pd.Series) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(DAYS_PER_YEAR)) if sd > 0 else 0.0


def walk_forward(
    variant_returns: dict[str, pd.Series],
    benchmark: pd.Series,
    start: str = "2019-07-01",
    months: int = 6,
) -> pd.DataFrame:
    """At each fold boundary pick the variant with the best Sharpe on all earlier days, then score it on the fold."""
    frame = pd.DataFrame(variant_returns).dropna()
    index = frame.index
    starts = pd.date_range(pd.Timestamp(start).tz_localize(index.tz), index[-1], freq=f"{months}MS")
    rows = []
    for k, fold_start in enumerate(starts):
        fold_end = starts[k + 1] if k + 1 < len(starts) else index[-1] + pd.Timedelta(days=1)
        past = frame[index < fold_start]
        in_fold = (index >= fold_start) & (index < fold_end)
        chosen = (past.mean() / past.std(ddof=1)).idxmax()
        r = frame.loc[in_fold, chosen]
        b = benchmark.reindex(r.index)
        rows.append({
            "fold_start": str(fold_start.date()),
            "fold_end": str((fold_end - pd.Timedelta(days=1)).date()),
            "chosen": chosen,
            "sharpe": _sharpe(r),
            "return": float((1 + r).prod() - 1),
            "benchmark_return": float((1 + b).prod() - 1),
        })
    return pd.DataFrame(rows)


def regime_labels(close: pd.Series) -> pd.Series:
    """Bull, bear or sideways from the 200-day average and its 20-day slope, as known at the previous close."""
    sma = close.rolling(200).mean()
    slope = sma.diff(20)
    label = pd.Series("sideways", index=close.index, dtype=object)
    label[(close > sma) & (slope > 0)] = "bull"
    label[(close < sma) & (slope < 0)] = "bear"
    return label.where(sma.notna()).shift(1)


def by_regime(returns: pd.Series, labels: pd.Series) -> dict[str, dict]:
    aligned = labels.reindex(returns.index)
    return {
        regime: {"days": len(r), "annual_return": float(r.mean() * DAYS_PER_YEAR), "sharpe": _sharpe(r)}
        for regime, r in returns.groupby(aligned)
    }


def _beats(strategy: dict, benchmark: dict) -> bool:
    return strategy["sharpe"] > benchmark["sharpe"] or strategy["calmar"] > benchmark["calmar"]


def evaluate_gates(
    test: dict,
    test_benchmark: dict,
    dsr: float,
    positive_fold_share: float,
    eth: dict | None = None,
    eth_benchmark: dict | None = None,
) -> dict:
    gates = {
        "out_of_sample": _beats(test, test_benchmark),
        "deflated_sharpe": dsr >= 0.95,
        "walk_forward": positive_fold_share >= 0.60,
        "eth_holdout": None if eth is None else _beats(eth, eth_benchmark),
    }
    gates["all_passed"] = all(v is True for v in gates.values())
    return gates
