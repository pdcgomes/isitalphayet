"""Collect every result the canvas shows into one compact JSON document on stdout.

Usage: uv run python experiments/build_canvas_data.py > experiments/results/canvas_data.json
"""

import csv
import json

import pandas as pd

from lab.costs import FEE_SCENARIOS
from lab.data import REPO_ROOT
from lab.ledger import read as read_ledger

RESULTS = REPO_ROOT / "experiments" / "results"
TA_SCORES = REPO_ROOT / "experiments" / "tradingagents" / "results" / "scores.json"
PAPER = REPO_ROOT / "paper"


def r(x, digits=3):
    return None if x is None or x != x else round(float(x), digits)


def main() -> None:
    summary = json.loads((RESULTS / "backtest_summary.json").read_text())
    families = summary["families"]
    selected = {f: v["selected"] for f, v in families.items()}

    curves = pd.read_csv(RESULTS / "growth_of_1000_weekly.csv", index_col="week", parse_dates=True)
    quarterly = curves.resample("QE").last()
    growth = {"quarters": [f"{d.year} Q{d.quarter}" for d in quarterly.index], "series": {}}
    for fee in FEE_SCENARIOS:
        growth["series"][fee] = {"Buy and hold": [round(v) for v in quarterly["buy_and_hold"]]}
        for name in selected.values():
            growth["series"][fee][name] = [round(v) for v in quarterly[f"{name} | {fee}"]]

    bh = summary["benchmarks"]["buy_and_hold"]["kraken_taker"]
    gates = []
    for family, e in families.items():
        gates.append({
            "family": family, "variant": e["selected"],
            "test_sharpe": r(e["test"]["sharpe"], 2), "test_calmar": r(e["test"]["calmar"], 2),
            "bh_test_sharpe": r(e["test_benchmark"]["sharpe"], 2), "bh_test_calmar": r(e["test_benchmark"]["calmar"], 2),
            "dsr": r(e["deflated_sharpe"]["dsr"], 2), "lenient_dsr": r(e["post_hoc_lenient_dsr"], 2),
            "positive_folds": r(e["positive_fold_share"], 2),
            "eth_sharpe": r(e["eth"]["sharpe"], 2), "eth_bh_sharpe": r(e["eth_benchmark"]["sharpe"], 2),
            "full_cagr": r(e["full"]["cagr"]), "full_max_dd": r(e["full"]["max_drawdown"]),
            "trades": e["trades"], "annual_fee_drag": r(e["annual_fee_drag"]),
            "gates": {k: v for k, v in e["gates"].items()},
            "sharpe_gap_ci": [r(x, 2) for x in e["sharpe_gap_ci_vs_buy_and_hold"]],
        })

    variants = sorted({k.split(" | ")[0] for k in summary["all_variants"]})
    fee_table = []
    for v in variants:
        row = {"variant": v, "trades": summary["all_variants"][f"{v} | kraken_taker"]["trades"]}
        for fee in FEE_SCENARIOS:
            full = summary["all_variants"][f"{v} | {fee}"]["full"]
            row[fee] = {"cagr": r(full["cagr"]), "sharpe": r(full["sharpe"], 2)}
        fee_table.append(row)

    trend = families["trend"]
    data = {
        "meta": {
            "data": "Binance BTCUSDT and ETHUSDT, daily and 4-hour candles, 2017-08-17 to 2026-09-30",
            "design_period": "2017-08-17 to 2022-12-31", "test_period": "2023-01-01 to 2026-09-30",
            "trials": summary["trials_logged"],
            "preregistration_sha256": next(e["sha256"] for e in read_ledger() if e.get("event") == "preregistration")[:12],
        },
        "benchmarks": {
            "btc_full": {k: r(bh["full"][k]) for k in ("cagr", "sharpe", "max_drawdown", "longest_drawdown_days")},
            "btc_test": {k: r(bh["test"][k]) for k in ("cagr", "sharpe", "calmar", "max_drawdown")},
            "monthly_buying_full": {k: r(summary["benchmarks"]["monthly_buying"]["full"][k]) for k in ("cagr", "sharpe", "max_drawdown")},
            "eth_full": {k: r(summary["benchmarks"]["eth_buy_and_hold"][k]) for k in ("cagr", "sharpe", "max_drawdown")},
        },
        "growth": growth,
        "gates": gates,
        "fee_table": fee_table,
        "look_ahead": {k: {m: r(v[m]) for m in ("cagr", "sharpe", "max_drawdown")} for k, v in summary["look_ahead_demo"].items()},
        "regimes": {
            "buy_and_hold": {k: r(v["annual_return"]) for k, v in summary["benchmarks"]["buy_and_hold_regimes"].items()},
            trend["selected"]: {k: r(v["annual_return"]) for k, v in trend["regimes"].items()},
        },
        "walk_forward": [{"fold": f["fold_start"][:7], "return": r(f["return"]), "bh_return": r(f["benchmark_return"]),
                          "chosen": f["chosen"]} for f in trend["walk_forward"]],
        "paper_candidate": summary["paper_candidate"],
    }

    if TA_SCORES.exists():
        scores = json.loads(TA_SCORES.read_text())
        ta = {"cost": scores["cost"], "pooled": scores.get("grid_pooled"),
              "repeatability": scores.get("repeatability"), "summary": [], "weeks": []}
        for run in ("grid", "grid_nvda", "forward"):
            for ticker, s in scores.get(run, {}).items():
                ta["summary"].append({
                    "run": run, "ticker": ticker, "settled": s["settled"], "pending": s["pending"],
                    "ratings": s["ratings"], "exposure": r(s.get("average_exposure"), 2),
                    "agent": r(s.get("agent_return")), "buy_and_hold": r(s.get("buy_and_hold_return")),
                    "constant": r(s.get("constant_exposure_return")), "timing": r(s.get("timing_skill")),
                    "hits": s.get("hits"), "calls": s.get("directional_calls"), "p": r(s.get("p_value"), 2),
                })
                ta["weeks"] += [{"run": run, "ticker": ticker, "date": d["date"], "rating": d["rating"],
                                 "ret": r(d["week_return"])} for d in s["decisions"]]
        data["tradingagents"] = ta

    config = json.loads((PAPER / "config.json").read_text())
    with (PAPER / "ledger.csv").open() as f:
        ledger = list(csv.DictReader(f))
    data["paper"] = {"config": config, "rows": len(ledger), "latest": ledger[-1]}

    print(json.dumps(data, separators=(",", ":")))


if __name__ == "__main__":
    main()
