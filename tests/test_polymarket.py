import numpy as np
import pytest

from lab import polymarket as pm


def test_fee_is_rate_times_p_times_one_minus_p():
    assert pm.taker_fee(0.5, 0.07) == pytest.approx(0.0175)
    # As a share of the stake: 3.5% at 50c in crypto, 0.35% at 95c.
    assert pm.taker_fee(0.5, 0.07) / 0.5 == pytest.approx(0.035)
    assert pm.taker_fee(0.95, 0.07) / 0.95 == pytest.approx(0.0035)
    assert pm.fee_rate("Politics") == 0.04 and pm.fee_rate(None) == 0.05 and pm.fee_rate("geopolitics") == 0.05


def test_tick_is_finer_near_the_extremes():
    assert list(pm.tick([0.03, 0.04, 0.5, 0.96, 0.97])) == [0.001, 0.01, 0.01, 0.01, 0.001]
    assert pm.buy_price(0.998) == pytest.approx(0.999)
    assert pm.buy_price(0.5) == pytest.approx(0.51)


def test_return_and_bands():
    assert pm.return_per_dollar(0.5, 1) == pytest.approx(1.0)
    assert pm.return_per_dollar(0.8, 0) == pytest.approx(-1.0)
    assert list(pm.price_band([0.0, 0.049, 0.05, 0.5, 0.999, 1.0])) == [0, 0, 1, 10, 19, 19]


def test_cluster_bootstrap_resamples_whole_events():
    values = np.array([1.0, 1.0, 1.0, -1.0])
    clusters = np.array(["a", "a", "a", "b"])
    mean, lo, hi = pm.cluster_bootstrap_mean(values, clusters, n=500)
    assert mean == pytest.approx(0.5)
    # With only two events the interval must span from all-"b" (-1) to all-"a" (+1).
    assert lo == pytest.approx(-1.0) and hi == pytest.approx(1.0)


def test_permutation_null_detects_persistence_and_not_noise():
    rng = np.random.default_rng(0)
    strata = np.repeat(np.arange(10), 100)
    selected = np.zeros(1000, dtype=bool)
    selected[strata == 9] = np.arange(100) < 10
    noise = rng.normal(size=1000)
    null = pm.stratified_permutation_null(noise, strata, selected, n=300)
    assert np.quantile(null, 0.025) < noise[selected].mean() < np.quantile(null, 0.975)
    skilled = noise.copy()
    skilled[selected] += 5
    null = pm.stratified_permutation_null(skilled, strata, selected, n=300)
    assert skilled[selected].mean() > np.quantile(null, 0.975)


def test_block_bootstrap_of_constant_returns_is_exact():
    out = pm.block_bootstrap_cagr(np.full(365, 0.0001), n=50)
    assert np.allclose(out, (1.0001 ** 365) - 1)


def test_fair_chance_is_half_at_the_open_price():
    assert pm.fair_up(0.0, 1e-4, 600) == pytest.approx(0.5)
    assert pm.fair_up(0.001, 1e-4, 600) > 0.5 > pm.fair_up(-0.001, 1e-4, 600)


def test_walk_book_respects_limit_and_size():
    assert pm.walk_book([0.52, 0.50, 0.51], [4, 3, 5], limit=0.51, shares=10) == pytest.approx((8, 3 * 0.50 + 5 * 0.51))
    assert pm.walk_book([0.53], [100], limit=0.52, shares=10) == (0, 0)


def window(n=50, step=100, up_ask=0.40, fair=0.60):
    ts = np.arange(n) * step
    up_asks = [[up_ask, up_ask + 0.01] for _ in range(n)]
    sizes = [[5.0, 50.0] for _ in range(n)]
    down_asks = [[0.62] for _ in range(n)]
    return ts, np.full(n, fair), up_asks, sizes, down_asks, [[50.0]] * n


def test_no_edge_no_trade():
    ts, fair, ua, us, da, ds = window(fair=0.40)
    assert pm.simulate_window(ts, fair, ua, us, da, ds, deadline_ms=10_000, delay_ms=300, margin=0.01) is None


def test_fill_happens_after_the_delay_at_or_below_the_limit():
    ts, fair, ua, us, da, ds = window()
    fill = pm.simulate_window(ts, fair, ua, us, da, ds, deadline_ms=10_000, delay_ms=300, margin=0.01)
    assert fill.side == "up" and fill.signal_ms == 0 and fill.fill_ms == 300
    # Only the 5 shares at the limit fill; the next level is above it.
    assert fill.shares == 5 and fill.avg_price == pytest.approx(0.40)
    assert fill.fee_per_share == pytest.approx(0.07 * 0.40 * 0.60)


def test_price_moving_away_during_the_delay_means_no_fill_then_a_retry():
    ts, fair, ua, us, da, ds = window()
    for i in range(1, 15):
        ua[i] = [0.55]
    fill = pm.simulate_window(ts, fair, ua, us, da, ds, deadline_ms=10_000, delay_ms=300, margin=0.01, retry_ms=1000)
    # The signal at 0 ms misses (the book at 300 ms is 0.55), so the next attempt waits until 1,000 ms.
    assert fill is not None and fill.signal_ms >= 1000 and fill.fill_ms >= fill.signal_ms + 300


def test_never_fills_past_the_deadline():
    ts, fair, ua, us, da, ds = window()
    assert pm.simulate_window(ts, fair, ua, us, da, ds, deadline_ms=200, delay_ms=300, margin=0.01) is None
