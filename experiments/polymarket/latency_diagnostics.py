"""Descriptive check for Test 5: who forecasts the outcome better, our Binance-based model or the market's own price?"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lab import polymarket as pm
from lab.data import REPO_ROOT

from fetch_data import BOOK_DAYS, BOOK_DAYS_BEFORE_TWAP
from latency import HORIZON_MS, binance, snapshots, windows

OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "latency_diagnostics.json"
SECONDS_LEFT = [600, 300, 60, 10]


def sample(day: str) -> list[dict]:
    w = windows(day)
    w = w[w["horizon"] == "15m"]
    if w.empty:
        return []
    px = binance(day)
    snaps = snapshots(day, w["condition_id"].tolist())
    snaps = pd.merge_asof(snaps.sort_values("timestamp_ms"), px, on="timestamp_ms", direction="backward")
    out = []
    for cid, g in snaps.groupby("condition_id"):
        meta = w[w["condition_id"] == cid].iloc[0]
        start = int(float(meta["window_key"].split(":")[1]))
        end = start + HORIZON_MS["15m"]
        open_px = px.loc[px["timestamp_ms"] <= start, "price"]
        if open_px.empty:
            continue
        g = g.sort_values("timestamp_ms")
        for left in SECONDS_LEFT:
            row = g[g["timestamp_ms"] <= end - left * 1000].tail(1)
            if row.empty:
                continue
            r = row.iloc[0]
            up_ask, down_ask = pm.best_asks([r["up_side_asks"]])[0], pm.best_asks([r["down_side_asks"]])[0]
            if not (np.isfinite(up_ask) and np.isfinite(down_ask)):
                continue
            market = (up_ask + (1 - down_ask)) / 2
            model = float(pm.fair_up(np.log(r["price"] / float(open_px.iloc[-1])), r["sigma"], left))
            out.append({"day": day, "regime": "before_twap" if day in BOOK_DAYS_BEFORE_TWAP else "after_twap",
                        "seconds_left": left, "model": model, "market": float(market),
                        "up": 1.0 if meta["outcome_direction"] == "UP" else 0.0})
    return out


def main() -> None:
    df = pd.DataFrame([r for day in BOOK_DAYS for r in sample(day)])
    result = {}
    for left, g in df.groupby("seconds_left"):
        result[str(left)] = {
            "windows": int(len(g)),
            "brier_model": float(((g["model"] - g["up"]) ** 2).mean()),
            "brier_market": float(((g["market"] - g["up"]) ** 2).mean()),
            "brier_coin": 0.25,
            "model_vs_market_correlation": float(g[["model", "market"]].corr().iloc[0, 1]),
            "mean_abs_gap": float((g["model"] - g["market"]).abs().mean()),
        }
        r = result[str(left)]
        print(f"{left:>4}s left: {r['windows']} windows; Brier model {r['brier_model']:.3f}, market "
              f"{r['brier_market']:.3f}, coin 0.250; corr {r['model_vs_market_correlation']:.2f}, "
              f"mean gap {r['mean_abs_gap']:.3f}")
    OUT.write_text(json.dumps(result, indent=1))
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
