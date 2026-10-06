"""Test 2: luck or skill. Do the biggest winners of one half-year beat equally large losers in the next?"""

from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from lab import polymarket as pm
from lab.data import REPO_ROOT
from lab.ledger import append, check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
WALLETS = REPO_ROOT / "data" / "polymarket" / "wallets"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "persistence.json"

SPLITS = [("2023H2", "2024H1"), ("2024H1", "2024H2"), ("2024H2", "2025H1"), ("2025H1", "2025H2")]
AUTOMATED_TRADES_PER_WEEK = 1000
TOP = 0.01


def half_year(label: str) -> list[str]:
    year, half = int(label[:4]), label[-1]
    months = range(1, 7) if half == "1" else range(7, 13)
    return [f"{year}-{m:02d}" for m in months]


def month_labels(values: pd.Series) -> pd.Series:
    """The month a change happened in. The dataset labels each month by its end (1 Feb holds January)."""
    return (pd.to_datetime(values, utc=True) - pd.Timedelta(days=1)).dt.strftime("%Y-%m")


def load() -> pd.DataFrame:
    df = duckdb.sql(f"SELECT user_address, month, pnl_change FROM '{WALLETS / 'pnl_change_monthly.parquet'}'").df()
    df["month"] = month_labels(df["month"])
    return df


def evaluate(form: pd.Series, evaluation: pd.Series, n_null: int) -> dict:
    form_x = form.to_numpy(dtype=float)
    eval_x = evaluation.to_numpy(dtype=float)
    k = max(1, int(round(len(form_x) * TOP)))
    order = np.argsort(-form_x)
    selected = np.zeros(len(form_x), dtype=bool)
    selected[order[:k]] = True
    strata = pd.qcut(pd.Series(np.abs(form_x)).rank(method="first"), 10, labels=False).to_numpy()
    null = pm.stratified_permutation_null(eval_x, strata, selected, n=n_null)
    top_eval = eval_x[selected]
    rho = spearmanr(form_x, eval_x).statistic
    return {
        "wallets": int(len(form_x)), "top_wallets": int(k),
        "spearman": float(rho),
        "top_share_profitable_next": float((top_eval > 0).mean()),
        "all_share_profitable_next": float((eval_x > 0).mean()),
        "top_mean_next": float(top_eval.mean()), "top_median_next": float(np.median(top_eval)),
        "top_mean_formation": float(form_x[selected].mean()),
        "null_mean": float(null.mean()), "null_p025": float(np.quantile(null, 0.025)),
        "null_p975": float(np.quantile(null, 0.975)),
        "beats_null": bool(top_eval.mean() > np.quantile(null, 0.975)),
    }


def main(n_null: int = 1000) -> None:
    check_preregistration(PREREG)
    monthly = load()
    automated = set(duckdb.sql(
        f"SELECT user_address FROM '{WALLETS / 'user_features.parquet'}' "
        f"WHERE trades_per_week >= {AUTOMATED_TRADES_PER_WEEK}").df()["user_address"])
    monthly["segment"] = np.where(monthly["user_address"].isin(automated), "automated", "human")
    result = {"definitions": {"top": TOP, "null": "evaluation profit shuffled within deciles of |formation profit|",
                              "rule": "skill persists if the top 1% beat the null's 97.5th percentile in >= 3 of 4 splits"},
              "months_in_data": [monthly["month"].min(), monthly["month"].max()], "splits": {}}
    for form_label, eval_label in SPLITS:
        f_months, e_months = half_year(form_label), half_year(eval_label)
        form = monthly[monthly["month"].isin(f_months)].groupby(["segment", "user_address"])["pnl_change"].sum()
        evaluation = monthly[monthly["month"].isin(e_months)].groupby(["segment", "user_address"])["pnl_change"].sum()
        key = f"{form_label} -> {eval_label}"
        result["splits"][key] = {}
        for segment in ["human", "automated"]:
            f = form.loc[segment]
            f = f[f != 0]
            e = evaluation.reindex(pd.MultiIndex.from_product([[segment], f.index])).fillna(0).droplevel(0)
            stats = evaluate(f, e, n_null)
            result["splits"][key][segment] = stats
            print(f"{key} {segment:9s} n={stats['wallets']:>9,} rho={stats['spearman']:+.3f} "
                  f"top1% next: mean {stats['top_mean_next']:>10,.0f} (null 97.5% {stats['null_p975']:>9,.0f}), "
                  f"profitable {stats['top_share_profitable_next']:.0%} vs all {stats['all_share_profitable_next']:.0%}")
    result["verdict"] = {}
    for segment in ["human", "automated"]:
        wins = sum(result["splits"][k][segment]["beats_null"] for k in result["splits"])
        result["verdict"][segment] = {"splits_beating_null": wins, "skill_persists": wins >= 3}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    append({"event": "analysis", "study": "polymarket", "test": "persistence", "counts_as_trial": False,
            "verdict": result["verdict"]})
    print("\nVerdict:", result["verdict"])
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
