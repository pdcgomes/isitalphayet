"""Sharpe-ratio statistics that account for luck and for the number of strategies tried."""

from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis, norm, skew

EULER_GAMMA = 0.5772156649015329


def expected_max_z(n_trials: int) -> float:
    """Expected best z-score among n_trials independent noise strategies (Bailey & López de Prado, 2014)."""
    if n_trials < 2:
        return 0.0
    return float(
        (1 - EULER_GAMMA) * norm.ppf(1 - 1 / n_trials)
        + EULER_GAMMA * norm.ppf(1 - 1 / (n_trials * np.e))
    )


def probabilistic_sharpe(sr: float, n_obs: int, skewness: float, kurt: float, benchmark: float = 0.0) -> float:
    """Probability that the true Sharpe beats `benchmark`. Sharpes are per period; kurtosis is non-excess."""
    denom = np.sqrt(1 - skewness * sr + (kurt - 1) / 4 * sr**2)
    return float(norm.cdf((sr - benchmark) * np.sqrt(n_obs - 1) / denom))


def deflated_sharpe(returns, trial_sharpes) -> dict:
    """Probabilistic Sharpe against the best Sharpe that len(trial_sharpes) noise strategies would reach.

    `trial_sharpes` holds the per-period Sharpe of every strategy tried, this one included.
    """
    r = np.asarray(returns, dtype=float)
    trials = np.asarray(trial_sharpes, dtype=float)
    sr = r.mean() / r.std(ddof=1)
    noise_best = trials.std(ddof=1) * expected_max_z(len(trials)) if len(trials) > 1 else 0.0
    return {
        "dsr": probabilistic_sharpe(sr, len(r), float(skew(r)), float(kurtosis(r, fisher=False)), noise_best),
        "sharpe_daily": float(sr),
        "noise_best_daily": float(noise_best),
        "n_trials": len(trials),
    }


def bootstrap_sharpe_gap(a, b, block: int = 20, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval for annualised Sharpe(a) minus Sharpe(b), circular block bootstrap over paired days."""
    x = np.column_stack([np.asarray(a, dtype=float), np.asarray(b, dtype=float)])
    t = len(x)
    rng = np.random.default_rng(seed)
    n_blocks = -(-t // block)
    gaps = np.empty(n_boot)
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(n_boot):
            starts = rng.integers(0, t, n_blocks)
            sample = x[((starts[:, None] + np.arange(block)) % t).ravel()[:t]]
            sr = sample.mean(axis=0) / sample.std(axis=0, ddof=1) * np.sqrt(365)
            gaps[k] = sr[0] - sr[1]
    lo, hi = np.nanpercentile(gaps, [2.5, 97.5])
    return float(lo), float(hi)
