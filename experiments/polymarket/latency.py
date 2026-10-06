"""Test 5: the 15-minute Bitcoin latency bot, replayed on recorded Polymarket order books with fees and delays."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import product

import duckdb
import numpy as np
import pandas as pd

from lab import polymarket as pm
from lab.data import REPO_ROOT
from lab.ledger import append, check_preregistration

from fetch_data import BOOK_DAYS, BOOK_DAYS_BEFORE_TWAP

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
BOOKS = REPO_ROOT / "data" / "polymarket" / "books"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "latency.json"

DELAYS_MS = [100, 300, 1000]
MARGINS = [0.01, 0.03]
SHARES = 10.0
VOL_WINDOW_S = 900
HORIZON_MS = {"15m": 900_000, "5m": 300_000}
ALPHA = 0.05 / 6


def table(day: str, name: str) -> str:
    return f"read_parquet('{BOOKS / day}/dataset={name}/**/*.parquet', union_by_name=true)"


def windows(day: str) -> pd.DataFrame:
    """Windows with a resolution record flagged usable for backtests (the latest such record per market).

    A window's first record is often written before the settlement price is captured and marked unusable; a later
    record carries the settlement and the flag.
    """
    return duckdb.sql(f"""
        SELECT window_key, condition_id, horizon, outcome_direction
        FROM {table(day, 'resolution')}
        WHERE horizon IN ('15m', '5m') AND usable_for_backtest AND outcome_direction IN ('UP', 'DOWN')
        QUALIFY row_number() OVER (PARTITION BY condition_id ORDER BY revision DESC, emitted_at_ts DESC) = 1
    """).df()


def binance(day: str) -> pd.DataFrame:
    """Binance last trade price at every snapshot, plus 1-second volatility over the previous 15 minutes."""
    px = duckdb.sql(f"""
        SELECT timestamp_ms, last_trade_price AS price FROM {table(day, 'external_100ms')}
        WHERE exchange = 'binance' AND last_trade_price > 0 ORDER BY timestamp_ms
    """).df().drop_duplicates("timestamp_ms", keep="last")
    seconds = px[px["timestamp_ms"] % 1000 == 0].copy()
    seconds["sigma"] = np.log(seconds["price"]).diff().rolling(VOL_WINDOW_S, min_periods=VOL_WINDOW_S // 3).std()
    px = pd.merge_asof(px, seconds[["timestamp_ms", "sigma"]], on="timestamp_ms", direction="backward")
    px["sigma"] = px["sigma"].clip(lower=1e-6)
    return px


def snapshots(day: str, condition_ids: list[str]) -> pd.DataFrame:
    """Order-book snapshots while each market is open. Joined on condition_id: the features table's window_key is
    the start time in seconds without the horizon, so 5- and 15-minute markets starting together would collide."""
    quoted = ", ".join(f"'{c}'" for c in condition_ids)
    return duckdb.sql(f"""
        SELECT condition_id, timestamp_ms, time_to_start_ms, time_to_deadline_ms,
               up_side_asks, up_ask_sizes, down_side_asks, down_ask_sizes
        FROM {table(day, 'polymarket_features_100ms')}
        WHERE condition_id IN ({quoted}) AND time_to_start_ms <= 0 AND time_to_deadline_ms > 0
        ORDER BY condition_id, timestamp_ms
    """).df()


def replay_day(day: str) -> list[dict]:
    w = windows(day)
    if w.empty:
        return []
    px = binance(day)
    snaps = snapshots(day, w["condition_id"].tolist())
    snaps = pd.merge_asof(snaps.sort_values("timestamp_ms"), px, on="timestamp_ms", direction="backward")
    rows = []
    for cid, g in snaps.groupby("condition_id"):
        meta = w[w["condition_id"] == cid].iloc[0]
        key = meta["window_key"]
        g = g.sort_values("timestamp_ms")
        start = int(float(key.split(":")[1]))
        end = start + HORIZON_MS[meta["horizon"]]
        open_px = px.loc[px["timestamp_ms"] <= start, "price"]
        if open_px.empty or g["price"].isna().all():
            continue
        s0 = float(open_px.iloc[-1])
        ts = g["timestamp_ms"].to_numpy()
        deadline = int((ts + g["time_to_deadline_ms"].to_numpy()).min())
        fair = pm.fair_up(np.log(g["price"].to_numpy() / s0), g["sigma"].to_numpy(), (end - ts) / 1000)
        books = (g["up_side_asks"].tolist(), g["up_ask_sizes"].tolist(),
                 g["down_side_asks"].tolist(), g["down_ask_sizes"].tolist())
        best = {"best_up": pm.best_asks(books[0]), "best_down": pm.best_asks(books[2])}
        up_wins = meta["outcome_direction"] == "UP"
        base = {"day": day, "window": key, "horizon": meta["horizon"], "snapshots": int(len(g)),
                "regime": "before_twap" if day in BOOK_DAYS_BEFORE_TWAP else "after_twap"}
        runs = [(f"delay={d}ms, margin={m:.2f}", d, m, pm.CRYPTO_FEE_RATE, True)
                for d, m in product(DELAYS_MS, MARGINS)]
        runs += [(f"delay={d}ms, margin={m:.2f}, no fees", d, m, 0.0, False) for d, m in product(DELAYS_MS, MARGINS)]
        runs += [(f"no delay, margin={m:.2f}", 0, m, pm.CRYPTO_FEE_RATE, False) for m in MARGINS]
        for name, delay, margin, rate, trial in runs:
            fill = pm.simulate_window(ts, fair, *books, deadline_ms=deadline, delay_ms=delay, margin=margin,
                                      fee_rate_=rate, shares=SHARES, **best)
            row = {**base, "variant": name, "trial": trial, "traded": fill is not None}
            if fill is not None:
                payout = 1.0 if (fill.side == "up") == up_wins else 0.0
                cost = fill.avg_price + fill.fee_per_share
                row.update(side=fill.side, price=fill.avg_price, fee=fill.fee_per_share, shares=fill.shares,
                           won=payout == 1.0, ret=payout / cost - 1, profit=fill.shares * (payout - cost),
                           wait_ms=fill.fill_ms - fill.signal_ms)
            rows.append(row)
    return rows


def summarise(trades: pd.DataFrame, windows_seen: int) -> dict:
    out = {"windows": windows_seen, "traded": int(len(trades))}
    if len(trades) == 0:
        return out
    boot = pm.bootstrap_mean(trades["ret"].to_numpy())
    out.update(hit_rate=float(trades["won"].mean()), avg_price=float(trades["price"].mean()),
               mean_return=float(trades["ret"].mean()), lo95=float(np.quantile(boot, 0.025)),
               hi95=float(np.quantile(boot, 0.975)), one_sided_lower=float(np.quantile(boot, ALPHA)),
               total_profit=float(trades["profit"].sum()))
    return out


def main() -> None:
    check_preregistration(PREREG)
    rows = []
    for day in BOOK_DAYS:
        day_rows = replay_day(day)
        rows += day_rows
        n = len({r["window"] for r in day_rows})
        print(f"{day}: {n} usable windows replayed", flush=True)
    df = pd.DataFrame(rows)
    result = {"definitions": {"fair": "Phi(ln(S_t/S_0) / (sigma sqrt(tau))) on Binance last trade, 1 s vol over 15 min",
                              "order": f"{SHARES:.0f} shares, limit at the signal's best ask, one entry per window",
                              "rule": "works for retail if a delay >= 300 ms variant has mean return > 0 with the "
                                      "one-sided 1 - 0.05/6 lower bound above zero, before and after the TWAP switch"},
              "results": defaultdict(dict)}
    for (horizon, variant, regime), g in df.groupby(["horizon", "variant", "regime"]):
        traded = g[g["traded"]]
        result["results"][f"{horizon} | {variant}"][regime] = summarise(traded, int(g["window"].nunique()))
    verdict = {}
    for d, m in product(DELAYS_MS, MARGINS):
        name = f"15m | delay={d}ms, margin={m:.2f}"
        r = result["results"][name]
        passes = all(r.get(x, {}).get("one_sided_lower", -1) > 0 for x in ["before_twap", "after_twap"])
        verdict[name] = {"passes": passes, "eligible": d >= 300}
        append({"event": "run", "study": "polymarket", "test": "latency", "variant": name, "counts_as_trial": True,
                **{f"{x}_mean_return": r.get(x, {}).get("mean_return") for x in ["before_twap", "after_twap"]},
                "passes": passes})
    result["verdict"] = verdict
    result["works_for_retail"] = any(v["passes"] and v["eligible"] for v in verdict.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    for name, regimes in sorted(result["results"].items()):
        for regime, s in regimes.items():
            if s.get("traded"):
                print(f"{name:42s} {regime:12s} windows {s['windows']:4d} traded {s['traded']:4d} "
                      f"hit {s['hit_rate']:.0%} price {s['avg_price']:.2f} return/$ {s['mean_return']:+.3f} "
                      f"[{s['lo95']:+.3f}, {s['hi95']:+.3f}] profit ${s['total_profit']:+,.0f}")
    print("\nWorks for retail:", result["works_for_retail"])
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
