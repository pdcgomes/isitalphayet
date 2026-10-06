"""Test 4: "bonds". Buy near-certain outcomes at 95-99c every day and hold them to resolution. Does it beat cash?"""

from __future__ import annotations

import json
from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd

from lab import polymarket as pm
from lab.data import REPO_ROOT
from lab.ledger import append, check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
WALLETS = REPO_ROOT / "data" / "polymarket" / "wallets"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "bonds.json"

START, END = pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2026-03-29", tz="UTC")
BAND = (0.95, 0.99)
MIN_TRADES = 5
CAPITAL = 1000.0
POSITION_FRACTION = 0.02
VOLUME_FRACTION = 0.10
MIN_SHARES = 5
SETTLEMENT_DAYS = 2
CASH_RATE = 0.0375
VARIANTS = [7, 30]


def candidates(max_days: int, open_at_end_of_day: bool = False) -> pd.DataFrame:
    """Every (day, token) a bond buyer could have bought, using only the schedule known on that day.

    With `open_at_end_of_day`, a buy at the daily close needs the market to still be trading when the day ends. For a
    market that closed during the day, its "daily close" is the last trade before it resolved, and knowing that it was
    the last one is hindsight.
    """
    from calibration import resolved_binary_tokens  # same resolved-token definition as Test 3

    still_open = "AND t.close_time >= date_trunc('day', o.timestamp) + INTERVAL 1 DAY" if open_at_end_of_day else ""
    return duckdb.sql(f"""
        WITH t AS ({resolved_binary_tokens()})
        SELECT date_trunc('day', o.timestamp) AS day, t.prediction_id, t.market_id, t.category, t.question,
               t.payout, t.close_time, t.expiration_time, o.close AS price, o.volume * o.close AS dollar_volume
        FROM t JOIN '{WALLETS / "ohlcv_1d.parquet"}' o ON o.prediction_id = t.prediction_id
        WHERE o.close BETWEEN {BAND[0]} AND {BAND[1]} AND o.trade_count >= {MIN_TRADES}
          AND o.timestamp >= TIMESTAMPTZ '{START}' AND o.timestamp <= TIMESTAMPTZ '{END}'
          AND t.expiration_time IS NOT NULL
          AND t.expiration_time > date_trunc('day', o.timestamp)
          AND t.expiration_time <= date_trunc('day', o.timestamp) + INTERVAL {max_days} DAY
          {still_open}
        ORDER BY day, t.expiration_time, t.prediction_id
    """).df()


def simulate(cands: pd.DataFrame, fees: bool = True) -> dict:
    cash, open_positions, held_markets, trades = CAPITAL, [], set(), []
    days = pd.date_range(START, END, freq="D")
    by_day = {d: g for d, g in cands.groupby("day")}
    equity_curve, invested_share = [], []
    for day in days:
        still_open = []
        for pos in open_positions:
            if pos["pays_on"] <= day:
                cash += pos["shares"] * pos["payout"]
                held_markets.discard(pos["market_id"])
            else:
                still_open.append(pos)
        open_positions = still_open
        equity = cash + sum(p["cost"] for p in open_positions)
        for row in (by_day.get(day, pd.DataFrame()).itertuples(index=False)):
            if row.market_id in held_markets:
                continue
            price = float(pm.buy_price(row.price))
            fee = float(pm.taker_fee(price, pm.fee_rate(row.category))) if fees else 0.0
            per_share = price + fee
            stake = min(POSITION_FRACTION * equity, cash, VOLUME_FRACTION * row.dollar_volume)
            if stake < MIN_SHARES * per_share:
                continue
            shares = stake / per_share
            cash -= stake
            pays_on = (row.close_time + timedelta(days=SETTLEMENT_DAYS)).floor("D")
            pos = {"market_id": row.market_id, "shares": shares, "cost": stake, "payout": row.payout,
                   "pays_on": pays_on}
            open_positions.append(pos)
            held_markets.add(row.market_id)
            trades.append({"day": day.date().isoformat(), "question": row.question, "category": row.category,
                           "price": price, "fee": fee,
                           "stake": stake, "payout": row.payout, "pnl": shares * row.payout - stake,
                           "days_held": (pays_on - day).days})
        invested = sum(p["cost"] for p in open_positions)
        equity_curve.append(cash + invested)
        invested_share.append(invested / (cash + invested))
    # Positions still open at the end are valued at cost: their outcome is known, but they had not paid out yet.
    equity = np.array(equity_curve)
    daily = equity[1:] / equity[:-1] - 1
    t = pd.DataFrame(trades)
    years = (END - START).days
    boot = pm.block_bootstrap_cagr(daily, block=30)
    peak = np.maximum.accumulate(equity)
    return {
        "final_equity": float(equity[-1]), "cagr": pm.cagr(equity, years),
        "cagr_lo": float(np.quantile(boot, 0.025)), "cagr_hi": float(np.quantile(boot, 0.975)),
        "max_drawdown": float((equity / peak - 1).min()),
        "positions": int(len(t)), "win_rate": float((t["payout"] == 1).mean()),
        "half_payouts": int((t["payout"] == 0.5).sum()), "losses": int((t["payout"] == 0).sum()),
        "mean_return_per_position": float((t["pnl"] / t["stake"]).mean()),
        "median_days_held": float(t["days_held"].median()),
        "average_invested_share": float(np.mean(invested_share)),
        "worst_losses": t.nsmallest(5, "pnl")[["day", "question", "price", "stake", "pnl"]].to_dict("records"),
        # Exploratory breakdowns, not part of the registered rule.
        "pnl_by_year": t.groupby(t["day"].str[:4])["pnl"].sum().round(2).to_dict(),
        "pnl_by_category": t.groupby("category")["pnl"].sum().round(2).to_dict(),
        "positions_by_category": t.groupby("category").size().to_dict(),
        "beats_cash": bool(pm.cagr(equity, years) > CASH_RATE and np.quantile(boot, 0.025) > CASH_RATE),
        "equity_weekly": [round(float(x), 2) for x in equity[::7]],
    }


def main() -> None:
    check_preregistration(PREREG)
    result = {"definitions": {"band": BAND, "period": [str(START.date()), str(END.date())], "capital": CAPITAL,
                              "cash_rate": CASH_RATE, "position": "min(2% of equity, cash, 10% of day's $ volume)",
                              "schedule": "scheduled expiration within D days (known on the day)",
                              "settlement": f"recorded close + {SETTLEMENT_DAYS} days"}, "variants": {}, "demos": {}}
    for d in VARIANTS:
        cands = candidates(d)
        res = simulate(cands)
        nofee = simulate(cands, fees=False)
        result["variants"][f"D={d}"] = {"candidates": int(len(cands)), **res}
        result["demos"][f"D={d}, no fees"] = {k: nofee[k] for k in ["final_equity", "cagr", "positions", "win_rate"]}
        append({"event": "run", "study": "polymarket", "test": "bonds", "variant": f"bonds(D={d})",
                "counts_as_trial": True, "cagr": res["cagr"], "cagr_lo": res["cagr_lo"], "beats_cash": res["beats_cash"]})
        print(f"D={d}: {len(cands):,} candidate days; {res['positions']:,} positions, won {res['win_rate']:.1%}, "
              f"lost {res['losses']}, CAGR {res['cagr']:+.2%} [{res['cagr_lo']:+.2%}, {res['cagr_hi']:+.2%}], "
              f"max drawdown {res['max_drawdown']:.1%}, final ${res['final_equity']:,.0f}; "
              f"no fees: CAGR {nofee['cagr']:+.2%}; beats cash: {res['beats_cash']}")
        for w in res["worst_losses"][:3]:
            print(f"    lost ${-w['pnl']:,.2f} on {w['day']} at {w['price']:.3f}: {w['question'][:90]}")
        print(f"    invested on average {res['average_invested_share']:.0%}; median {res['median_days_held']:.0f} days held; "
              f"by year {res['pnl_by_year']}")
        print(f"    by category {res['pnl_by_category']} positions {res['positions_by_category']}")
    # Added after seeing the registered results: the same rule, buying only while the market is still open at day end.
    result["robustness_open_at_end_of_day"] = {}
    for d in VARIANTS:
        cands = candidates(d, open_at_end_of_day=True)
        res = simulate(cands)
        result["robustness_open_at_end_of_day"][f"D={d}"] = {"candidates": int(len(cands)), **res}
        append({"event": "run", "study": "polymarket", "test": "bonds", "variant": f"bonds(D={d}, open_at_end_of_day)",
                "counts_as_trial": True, "added_after_results": True, "cagr": res["cagr"], "cagr_lo": res["cagr_lo"],
                "beats_cash": res["beats_cash"]})
        print(f"Robustness D={d} (market still open at day end): {res['positions']:,} positions, won {res['win_rate']:.1%}, "
              f"CAGR {res['cagr']:+.2%} [{res['cagr_lo']:+.2%}, {res['cagr_hi']:+.2%}], max drawdown "
              f"{res['max_drawdown']:.1%}; by category {res['pnl_by_category']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, default=str))
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
