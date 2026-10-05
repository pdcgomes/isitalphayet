import numpy as np
import pandas as pd
import pytest

from lab.backtest import buy_and_hold, monthly_buying, simulate
from lab.metrics import daily_returns, summarize
from lab.strategies import grid, trend


def random_walk(days: int = 2000, seed: int = 7, vol: float = 0.03) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0, vol, days)))
    open_ = np.r_[100.0, close[:-1]]
    index = pd.date_range("2018-01-01", periods=days, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": np.maximum(open_, close), "low": np.minimum(open_, close), "close": close, "volume": 1.0},
        index=index,
    )


def test_buy_and_hold_without_fees_tracks_the_price():
    bars = random_walk()
    result = buy_and_hold(bars, fee=0.0)
    assert result.equity.iloc[-1] == pytest.approx(1000 * bars["close"].iloc[-1] / bars["open"].iloc[0])


def test_a_round_trip_costs_two_fees():
    bars = random_walk()
    bars[["open", "high", "low", "close"]] = 100.0
    target = pd.Series(np.nan, index=bars.index)
    target.iloc[10], target.iloc[20] = 1.0, 0.0
    result = simulate(bars, target, fee=0.01)
    assert result.trades == 2
    assert result.equity.iloc[-1] == pytest.approx(1000 / 1.01 * 0.99)


def test_rounding_error_never_counts_as_a_trade():
    bars = random_walk(days=3000, seed=11)
    result = simulate(bars, pd.Series(1.0, index=bars.index), fee=0.0085)
    assert result.trades == 1


def test_a_signal_is_filled_at_the_next_open_not_before():
    bars = random_walk()
    target = pd.Series(np.nan, index=bars.index)
    target.iloc[5] = 1.0
    result = simulate(bars, target, fee=0.0)
    assert result.weight.iloc[5] == 0.0
    assert result.weight.iloc[6] == pytest.approx(1.0)


def test_look_ahead_inflates_results_even_on_pure_noise():
    bars = random_walk(days=3000)
    target = trend(bars["close"], 20)
    honest = summarize(daily_returns(simulate(bars, target, fee=0.0)))["sharpe"]
    leaky = summarize(daily_returns(simulate(bars, target, fee=0.0, lag=0)))["sharpe"]
    assert abs(honest) < 3 * np.sqrt(365 / 3000)  # within three standard errors of zero
    assert leaky > honest + 1.0


def test_monthly_buying_invests_everything_within_twelve_months():
    bars = random_walk(days=800)
    result = monthly_buying(bars, fee=0.0)
    assert result.trades == 12
    assert result.weight.iloc[400] == pytest.approx(1.0)


def test_grid_holds_more_as_the_price_falls():
    # Levels sit at 91, 93, ..., 109 around a centre of 100.
    close = pd.Series([100.0, 95.5, 90.0, 85.0, 104.5, 111.0], index=pd.RangeIndex(6))
    weights = grid(close, half_range=0.10, recentre_bars=1000).tolist()
    assert weights == [0.5, 0.7, 1.0, 1.0, 0.3, 0.0]
