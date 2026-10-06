"""Test 3: are the odds fair? Win rates and returns by price band, before and after today's fees."""

from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from lab import polymarket as pm
from lab.data import REPO_ROOT
from lab.ledger import append, check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
WALLETS = REPO_ROOT / "data" / "polymarket" / "wallets"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "calibration.json"
SAMPLE_END = "2026-03-29 23:59:59+00"
HORIZONS = [1, 7, 30]
PRIMARY = 7
MIN_TRADES = 5
N_BOOT = 1000


def resolved_binary_tokens() -> str:
    """SQL for binary-market tokens with a known payout (1, 0, or 0.5 each when neither side won)."""
    return f"""
        WITH tokens AS (
            SELECT p.prediction_id, p.market_id, p.winner, m.category, m.question,
                   coalesce(m.event_id, CAST(m.market_id AS VARCHAR)) AS event_id,
                   m.close_time, m.expiration_time, m.can_close_early
            FROM '{WALLETS / "predictions.parquet"}' p
            JOIN '{WALLETS / "markets.parquet"}' m USING (market_id)
            WHERE p.n_outcomes = 2 AND m.close_time <= TIMESTAMPTZ '{SAMPLE_END}'
        ), per_market AS (
            SELECT market_id, count(winner) AS known, sum(CASE WHEN winner THEN 1 ELSE 0 END) AS wins, count(*) AS n
            FROM tokens GROUP BY market_id
        )
        SELECT t.*, CASE WHEN pm.wins = 1 THEN CASE WHEN t.winner THEN 1.0 ELSE 0.0 END ELSE 0.5 END AS payout
        FROM tokens t JOIN per_market pm USING (market_id)
        WHERE pm.n = 2 AND pm.known = 2 AND pm.wins <= 1
    """


def observations(horizon: int, anchor: str = "close_time") -> pd.DataFrame:
    """One row per token: its daily close `horizon` days before the market's close (or scheduled expiration)."""
    # `can_close_early` is empty in this dataset, so the sensitivity anchors on the scheduled expiration wherever known.
    anchor_sql = "t.close_time" if anchor == "close_time" else "coalesce(t.expiration_time, t.close_time)"
    return duckdb.sql(f"""
        WITH t AS ({resolved_binary_tokens()})
        SELECT t.prediction_id, t.market_id, t.event_id, t.category, t.payout, o.close AS price
        FROM t JOIN '{WALLETS / "ohlcv_1d.parquet"}' o
          ON o.prediction_id = t.prediction_id
         AND date_trunc('day', o.timestamp) = date_trunc('day', {anchor_sql}) - INTERVAL {horizon} DAY
        WHERE o.trade_count >= {MIN_TRADES} AND o.close > 0 AND o.close < 1
    """).df()


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    rates = df["category"].map(pm.fee_rate).to_numpy()
    p = df["price"].to_numpy()
    bp = pm.buy_price(p)
    df["band"] = pm.price_band(p)
    df["ret_before_fees"] = pm.return_per_dollar(p, df["payout"])
    df["ret_after_fees"] = pm.return_per_dollar(p + pm.taker_fee(p, rates), df["payout"])
    df["ret_after_fees_tick"] = pm.return_per_dollar(bp + pm.taker_fee(bp, rates), df["payout"])
    return df


def band_bootstrap(df: pd.DataFrame, column: str, n: int = N_BOOT, seed: int = pm.SEED) -> np.ndarray:
    """Per-band mean of `column` in each bootstrap resample of events (same resample for every band)."""
    _, event = np.unique(df["event_id"].to_numpy(), return_inverse=True)
    band = df["band"].to_numpy()
    values = df[column].to_numpy()
    k = event.max() + 1
    rng = np.random.default_rng(seed)
    out = np.empty((n, 20))
    for b in range(n):
        w = np.bincount(rng.integers(0, k, k), minlength=k)[event].astype(float)
        out[b] = np.bincount(band, weights=w * values, minlength=20) / np.maximum(
            np.bincount(band, weights=w, minlength=20), 1e-12)
    return out


def summarise(df: pd.DataFrame) -> dict:
    bands = []
    boots = {c: band_bootstrap(df, c) for c in ["ret_before_fees", "ret_after_fees", "ret_after_fees_tick"]}
    for b in range(20):
        g = df[df["band"] == b]
        row = {"band": f"{b * 5}-{b * 5 + 5}c", "tokens": int(len(g)), "events": int(g["event_id"].nunique()),
               "avg_price": float(g["price"].mean()) if len(g) else None,
               "win_rate": float(g["payout"].mean()) if len(g) else None}
        for c, boot in boots.items():
            row[c] = {"mean": float(g[c].mean()) if len(g) else None,
                      "lo": float(np.quantile(boot[:, b], 0.025)), "hi": float(np.quantile(boot[:, b], 0.975))}
        bands.append(row)
    return {"tokens": int(len(df)), "events": int(df["event_id"].nunique()), "markets": int(df["market_id"].nunique()),
            "bands": bands, "_boots": boots}


def low_minus_high(df: pd.DataFrame, boot: np.ndarray, column: str) -> dict:
    """Return of 0-10c buys minus return of 90-100c buys, with a bootstrap interval."""
    def pooled(mask_bands):
        g = df[df["band"].isin(mask_bands)]
        return g[column].mean()
    counts = df.groupby("band").size().reindex(range(20), fill_value=0).to_numpy()

    def pooled_boot(bands):
        c = counts[bands]
        return (boot[:, bands] * c).sum(axis=1) / c.sum()
    diff = pooled_boot([0, 1]) - pooled_boot([18, 19])
    return {"low": float(pooled([0, 1])), "high": float(pooled([18, 19])), "difference": float(pooled([0, 1]) - pooled([18, 19])),
            "lo": float(np.quantile(diff, 0.025)), "hi": float(np.quantile(diff, 0.975))}


def main() -> None:
    check_preregistration(PREREG)
    result = {"definitions": {"price": f"daily close H days before close, at least {MIN_TRADES} trades that day",
                              "bootstrap": f"{N_BOOT} resamples of events, seed {pm.SEED}",
                              "fees": "today's schedule, feeRate x p x (1 - p) per share"}, "horizons": {}}
    for h in HORIZONS:
        df = add_returns(observations(h))
        s = summarise(df)
        boots = s.pop("_boots")
        if h == PRIMARY:
            s["longshot_bias"] = low_minus_high(df, boots["ret_before_fees"], "ret_before_fees")
            s["longshot_bias_after_fees"] = low_minus_high(df, boots["ret_after_fees_tick"], "ret_after_fees_tick")
            s["bands_with_reliable_profit_after_fees_tick"] = [
                b["band"] for b in s["bands"] if b["tokens"] and b["ret_after_fees_tick"]["lo"] > 0]
        result["horizons"][str(h)] = s
        print(f"\nH = {h} days: {s['tokens']:,} tokens, {s['markets']:,} markets, {s['events']:,} events")
        for b in s["bands"]:
            if b["tokens"]:
                r = b["ret_after_fees_tick"]
                print(f"  {b['band']:>8}  n={b['tokens']:>7,}  price {b['avg_price']:.3f}  won {b['win_rate']:.3f}  "
                      f"before fees {b['ret_before_fees']['mean']:+.3f}  after fees+tick {r['mean']:+.3f} "
                      f"[{r['lo']:+.3f}, {r['hi']:+.3f}]")
    sens = add_returns(observations(PRIMARY, anchor="expiration"))
    s = summarise(sens)
    s.pop("_boots")
    result["sensitivity_scheduled_expiration"] = s
    primary = result["horizons"][str(PRIMARY)]
    print("\nLongshot bias (0-10c minus 90-100c, before fees):", primary["longshot_bias"])
    print("After fees and a tick:", primary["longshot_bias_after_fees"])
    print("Bands with a reliable profit after fees and a tick:", primary["bands_with_reliable_profit_after_fees_tick"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    append({"event": "analysis", "study": "polymarket", "test": "calibration", "counts_as_trial": False,
            "longshot_bias": primary["longshot_bias"],
            "reliable_bands": primary["bands_with_reliable_profit_after_fees_tick"]})
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
