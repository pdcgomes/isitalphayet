import numpy as np
import pandas as pd
import pytest

from lab.stats import deflated_sharpe, expected_max_z, probabilistic_sharpe
from lab.validate import walk_forward


def test_expected_best_of_80_noise_trials_matches_the_article_example():
    assert expected_max_z(80) == pytest.approx(2.45, abs=0.01)


def test_matches_the_worked_example_in_bailey_and_lopez_de_prado():
    # Annualised Sharpe 2.5 over 1,250 daily observations, 100 trials whose Sharpes have
    # annualised variance 0.5, skew -3 and kurtosis 10: the paper reports DSR = 0.9004.
    days = 252
    noise_best = np.sqrt(0.5 / days) * expected_max_z(100)
    dsr = probabilistic_sharpe(2.5 / np.sqrt(days), 1250, -3.0, 10.0, noise_best)
    assert dsr == pytest.approx(0.9004, abs=0.002)


def test_zero_mean_returns_give_even_odds():
    returns = np.tile([0.01, -0.01], 500)
    assert deflated_sharpe(returns, [0.0])["dsr"] == pytest.approx(0.5)


def test_the_best_of_many_random_strategies_fails_the_gate():
    rng = np.random.default_rng(1)
    market = rng.normal(0.0, 0.03, 3000)
    trials = [market * rng.integers(0, 2, 3000) for _ in range(13)]
    sharpes = [t.mean() / t.std(ddof=1) for t in trials]
    best = trials[int(np.argmax(sharpes))]
    assert deflated_sharpe(best, sharpes)["dsr"] < 0.95


def test_a_genuine_edge_passes_the_gate():
    rng = np.random.default_rng(2)
    noise = [rng.normal(0.0, 0.03, 3000) for _ in range(12)]
    edge = rng.normal(0.003, 0.03, 3000)
    sharpes = [t.mean() / t.std(ddof=1) for t in [*noise, edge]]
    assert deflated_sharpe(edge, sharpes)["dsr"] > 0.95


def test_walk_forward_follows_the_variant_that_did_best_so_far():
    index = pd.date_range("2018-01-01", "2021-12-31", freq="D", tz="UTC")
    rng = np.random.default_rng(3)
    good = pd.Series(rng.normal(0.002, 0.01, len(index)), index=index)
    bad = pd.Series(rng.normal(-0.002, 0.01, len(index)), index=index)
    folds = walk_forward({"good": good, "bad": bad}, benchmark=good)
    assert (folds["chosen"] == "good").all()
    assert folds["fold_start"].tolist() == ["2019-07-01", "2020-01-01", "2020-07-01", "2021-01-01", "2021-07-01"]
