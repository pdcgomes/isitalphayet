"""Run the pre-registered backtests and apply the gates.

Usage: uv run python experiments/run_backtests.py
"""

from __future__ import annotations

import json

import pandas as pd

from lab import ledger
from lab.backtest import buy_and_hold, monthly_buying, simulate
from lab.costs import FEE_SCENARIOS, GATE_SCENARIO
from lab.data import REPO_ROOT, binance_klines
from lab.metrics import daily_returns, summarize, trading_stats
from lab.stats import bootstrap_sharpe_gap, deflated_sharpe, expected_max_z, probabilistic_sharpe
from lab.strategies import FAMILIES, LEAKY_DEMO, PREREGISTERED, Variant
from lab.validate import by_regime, evaluate_gates, regime_labels, walk_forward

RESULTS = REPO_ROOT / "experiments" / "results"
DESIGN = slice("2017-08-17", "2022-12-31")
TEST = slice("2023-01-01", "2026-09-30")


def run(variant: Variant, bars: dict[str, pd.DataFrame], fee: str, lag: int = 1):
    candles = bars[variant.interval]
    result = simulate(candles, variant.target(candles), FEE_SCENARIOS[fee], band=variant.band, lag=lag)
    return result, daily_returns(result)


def run_record(variant: Variant, asset: str, fee: str, result, returns: pd.Series, counts_as_trial: bool) -> dict:
    return {
        "event": "run",
        "variant": variant.name,
        "family": variant.family,
        "asset": asset,
        "fee": fee,
        "counts_as_trial": counts_as_trial,
        "sharpe_daily_full": float(returns.mean() / returns.std(ddof=1)),
        "full": summarize(returns),
        "design": summarize(returns.loc[DESIGN]),
        "test": summarize(returns.loc[TEST]),
        **trading_stats(result),
    }


def lenient_dsr(returns: pd.Series, n_trials: int) -> float:
    """Post-hoc, not a gate: deflate only for estimation noise (trial variance 1/T), not for trial dispersion."""
    sr = returns.mean() / returns.std(ddof=1)
    noise_best = expected_max_z(n_trials) / len(returns) ** 0.5
    return probabilistic_sharpe(sr, len(returns), returns.skew(), returns.kurt() + 3, noise_best)


def growth_curve(returns: pd.Series) -> pd.Series:
    return (1000 * (1 + returns).cumprod()).resample("W").last()


def main() -> None:
    ledger.check_preregistration()
    btc = {interval: binance_klines("BTC", interval) for interval in ("1d", "4h")}
    eth = {interval: binance_klines("ETH", interval) for interval in ("1d", "4h")}
    taker = GATE_SCENARIO

    benchmarks = {fee: daily_returns(buy_and_hold(btc["1d"], FEE_SCENARIOS[fee])) for fee in FEE_SCENARIOS}
    monthly = daily_returns(monthly_buying(btc["1d"], FEE_SCENARIOS[taker]))

    # 1. Every pre-registered variant on BTC under every fee scenario, each run logged.
    runs: dict[tuple[str, str], tuple] = {}
    for variant in PREREGISTERED:
        for fee in FEE_SCENARIOS:
            result, returns = run(variant, btc, fee)
            runs[variant.name, fee] = (result, returns)
            ledger.append(run_record(variant, "BTC", fee, result, returns, counts_as_trial=True))
    trial_sharpes = list(ledger.trial_sharpes("BTC", taker).values())

    # 2. In each family, keep the variant with the best design-period Sharpe after taker fees.
    selected = {
        family: max(
            (v for v in PREREGISTERED if v.family == family),
            key=lambda v: summarize(runs[v.name, taker][1].loc[DESIGN])["sharpe"],
        )
        for family in FAMILIES
    }

    # 3. Gates 1-3 on BTC.
    labels = regime_labels(btc["1d"]["close"])
    bench = benchmarks[taker]
    report: dict[str, dict] = {}
    for family, variant in selected.items():
        result, returns = runs[variant.name, taker]
        folds = walk_forward(
            {v.name: runs[v.name, taker][1] for v in PREREGISTERED if v.family == family}, bench
        )
        report[family] = {
            "selected": variant.name,
            "test": summarize(returns.loc[TEST]),
            "test_benchmark": summarize(bench.loc[TEST]),
            "full": summarize(returns),
            "deflated_sharpe": deflated_sharpe(returns, trial_sharpes),
            "post_hoc_lenient_dsr": lenient_dsr(returns, len(trial_sharpes)),
            "sharpe_gap_ci_vs_buy_and_hold": bootstrap_sharpe_gap(returns, bench.reindex(returns.index)),
            "walk_forward": folds.to_dict(orient="records"),
            "positive_fold_share": float((folds["sharpe"] > 0).mean()),
            "regimes": by_regime(returns, labels),
            "by_fee": {fee: summarize(runs[variant.name, fee][1]) for fee in FEE_SCENARIOS},
            **trading_stats(result),
        }

    # 4. Only now, the ETH holdout for each family's selected variant.
    eth_bench = daily_returns(buy_and_hold(eth["1d"], FEE_SCENARIOS[taker]))
    for family, variant in selected.items():
        result, returns = run(variant, eth, taker)
        ledger.append(run_record(variant, "ETH", taker, result, returns, counts_as_trial=False))
        entry = report[family]
        entry["eth"] = summarize(returns)
        entry["eth_benchmark"] = summarize(eth_bench)
        entry["gates"] = evaluate_gates(
            entry["test"], entry["test_benchmark"], entry["deflated_sharpe"]["dsr"],
            entry["positive_fold_share"], entry["eth"], entry["eth_benchmark"],
        )

    # Leakage demonstration: the same 200-day trend filter, filled before its signal was knowable.
    honest = runs[LEAKY_DEMO.name, taker][1]
    leaky_result, leaky = run(LEAKY_DEMO, btc, taker, lag=0)
    ledger.append({**run_record(LEAKY_DEMO, "BTC", taker, leaky_result, leaky, False), "demo": "look_ahead"})

    passers = [f for f in FAMILIES if report[f]["gates"]["all_passed"]]
    best = passers[0] if passers else max(FAMILIES, key=lambda f: report[f]["deflated_sharpe"]["dsr"])
    summary = {
        "trials_logged": len(trial_sharpes),
        "benchmarks": {
            "buy_and_hold": {fee: {"full": summarize(r), "design": summarize(r.loc[DESIGN]), "test": summarize(r.loc[TEST])}
                             for fee, r in benchmarks.items()},
            "monthly_buying": {"full": summarize(monthly), "test": summarize(monthly.loc[TEST])},
            "eth_buy_and_hold": summarize(eth_bench),
            "buy_and_hold_regimes": by_regime(bench, labels),
        },
        "families": report,
        "all_variants": {
            f"{name} | {fee}": {"full": summarize(r), "design": summarize(r.loc[DESIGN]), "test": summarize(r.loc[TEST]),
                                **trading_stats(res)}
            for (name, fee), (res, r) in runs.items()
        },
        "look_ahead_demo": {"honest": summarize(honest), "leaky": summarize(leaky)},
        "paper_candidate": {
            "family": best,
            "variant": report[best]["selected"],
            "label": "passed all gates" if passers else "plumbing test (no strategy passed the gates)",
        },
    }

    curves = {"buy_and_hold": growth_curve(bench), "monthly_buying": growth_curve(monthly), "leaky_trend_200": growth_curve(leaky)}
    for family, variant in selected.items():
        for fee in FEE_SCENARIOS:
            curves[f"{variant.name} | {fee}"] = growth_curve(runs[variant.name, fee][1])

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "backtest_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.DataFrame(curves).to_csv(RESULTS / "growth_of_1000_weekly.csv", index_label="week")

    print(f"Trials logged on BTC: {len(trial_sharpes)}\n")
    bh_test = summary["benchmarks"]["buy_and_hold"][taker]["test"]
    print(f"BTC buy-and-hold, test period: Sharpe {bh_test['sharpe']:.2f}, Calmar {bh_test['calmar']:.2f}, "
          f"max drawdown {bh_test['max_drawdown']:.0%}")
    for family in FAMILIES:
        e = report[family]
        g = e["gates"]
        print(
            f"{e['selected']:<28} test Sharpe {e['test']['sharpe']:5.2f}  Calmar {e['test']['calmar']:5.2f}  "
            f"DSR {e['deflated_sharpe']['dsr']:.2f} (lenient {e['post_hoc_lenient_dsr']:.2f})  "
            f"folds+ {e['positive_fold_share']:.0%}  "
            f"ETH Sharpe {e['eth']['sharpe']:5.2f} vs {e['eth_benchmark']['sharpe']:.2f}  "
            f"gates {'PASS' if g['all_passed'] else 'fail'} "
            f"[{' '.join('Y' if g[k] else 'n' for k in ('out_of_sample', 'deflated_sharpe', 'walk_forward', 'eth_holdout'))}]"
        )
    demo = summary["look_ahead_demo"]
    print(f"\nLook-ahead demo, trend(n=200): honest Sharpe {demo['honest']['sharpe']:.2f} vs leaky {demo['leaky']['sharpe']:.2f}")
    print(f"Paper-trading candidate: {summary['paper_candidate']}")


if __name__ == "__main__":
    main()
