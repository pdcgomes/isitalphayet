"""Test 1: who wins and who loses on Polymarket (pre-registered, descriptive)."""

from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from lab.data import REPO_ROOT
from lab.ledger import append, check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
WALLETS = REPO_ROOT / "data" / "polymarket" / "wallets"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "wallets.json"

AUTOMATED_TRADES_PER_WEEK = 1000
MAKER_HEAVY = 0.5
MIN_VOLUME = 100
VOLUME_BANDS = [(100, 1e3, "$100-1K"), (1e3, 1e4, "$1K-10K"), (1e4, 1e5, "$10K-100K"), (1e5, 1e6, "$100K-1M"),
                (1e6, np.inf, "over $1M")]


def load() -> pd.DataFrame:
    return duckdb.sql(f"""
        SELECT p.user_address, p.pnl_total, p.pnl_resolved_total, p.pnl_no_fee_total,
               f.total_volume, f.trades_per_week, f.frac_maker_volume, f.n_trades
        FROM '{WALLETS / "user_pnl_summary.parquet"}' p
        JOIN '{WALLETS / "user_features.parquet"}' f USING (user_address)
    """).df()


def top_share(pnl: np.ndarray, fraction: float) -> float:
    """Share of all positive profit earned by the top `fraction` of wallets (ranked by profit)."""
    positive = pnl[pnl > 0].sum()
    k = max(1, int(round(len(pnl) * fraction)))
    top = np.sort(pnl)[::-1][:k]
    return float(top[top > 0].sum() / positive) if positive > 0 else float("nan")


def describe(pnl: pd.Series) -> dict:
    x = pnl.to_numpy(dtype=float)
    q = np.quantile(x, [0.01, 0.10, 0.5, 0.90, 0.99])
    return {
        "wallets": int(len(x)),
        "share_loss": float((x < 0).mean()), "share_profit": float((x > 0).mean()), "share_zero": float((x == 0).mean()),
        "p1": float(q[0]), "p10": float(q[1]), "median": float(q[2]), "p90": float(q[3]), "p99": float(q[4]),
        "total": float(x.sum()), "total_profits": float(x[x > 0].sum()), "total_losses": float(x[x < 0].sum()),
        "top_1pct_share_of_profit": top_share(x, 0.01), "top_01pct_share_of_profit": top_share(x, 0.001),
    }


def main() -> None:
    check_preregistration(PREREG)
    df = load()
    assert df["user_address"].is_unique
    df["automated"] = df["trades_per_week"] >= AUTOMATED_TRADES_PER_WEEK
    df["maker_heavy"] = df["frac_maker_volume"] >= MAKER_HEAVY
    main_pop = df[df["total_volume"] >= MIN_VOLUME]
    human = main_pop[~main_pop["automated"]]
    groups = {
        "all": main_pop,
        "automated": main_pop[main_pop["automated"]],
        "human": human,
        "human_maker_heavy": human[human["maker_heavy"]],
        "human_taker_heavy": human[~human["maker_heavy"]],
        "dust_10_to_100": df[(df["total_volume"] >= 10) & (df["total_volume"] < MIN_VOLUME)],
    }
    result = {"definitions": {"min_volume": MIN_VOLUME, "automated_trades_per_week": AUTOMATED_TRADES_PER_WEEK,
                              "maker_heavy_frac": MAKER_HEAVY, "profit": "pnl_total, after fees actually paid"},
              "wallets_in_dataset": int(len(df)), "groups": {}, "human_by_volume": {}, "variants": {}}
    for name, g in groups.items():
        result["groups"][name] = describe(g["pnl_total"])
    for lo, hi, label in VOLUME_BANDS:
        band = human[(human["total_volume"] >= lo) & (human["total_volume"] < hi)]
        result["human_by_volume"][label] = describe(band["pnl_total"])
    for column in ["pnl_resolved_total", "pnl_no_fee_total"]:
        result["variants"][column] = {name: describe(groups[name][column].fillna(0))
                                      for name in ["all", "automated", "human"]}
    h = result["groups"]["human"]
    result["expectations"] = {
        "most_human_wallets_lose": h["share_loss"] > 0.5,
        "top_1pct_take_over_half_of_profit": result["groups"]["all"]["top_1pct_share_of_profit"] > 0.5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    append({"event": "analysis", "study": "polymarket", "test": "wallets", "counts_as_trial": False,
            "human_share_loss": h["share_loss"], "all_top_1pct_share": result["groups"]["all"]["top_1pct_share_of_profit"]})

    table = pd.DataFrame({**{k: v for k, v in result["groups"].items()},
                          **{f"human {k}": v for k, v in result["human_by_volume"].items()}}).T
    cols = ["wallets", "share_loss", "share_profit", "median", "p10", "p90", "total", "top_1pct_share_of_profit"]
    with pd.option_context("display.width", 200, "display.float_format", "{:,.3f}".format):
        print(table[cols].to_string())
    print("\nExpectations:", result["expectations"])
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
