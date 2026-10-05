"""Turn the lab's outputs, the claim files and the trials ledger into the one JSON file the site reads.

Usage: uv run python experiments/export_site_data.py
"""

from __future__ import annotations

import csv
import json
import tomllib
from datetime import datetime, timezone

import pandas as pd
from scipy.stats import binomtest

from lab import ledger
from lab.costs import FEE_SCENARIOS
from lab.data import REPO_ROOT

RESULTS = REPO_ROOT / "experiments" / "results"
TA_RESULTS = REPO_ROOT / "experiments" / "tradingagents" / "results"
CLAIMS = REPO_ROOT / "claims"
CONTENT = REPO_ROOT / "content" / "site.toml"
PAPER = REPO_ROOT / "paper"
OUT = REPO_ROOT / "site" / "src" / "data" / "site.json"

FAMILY_NAMES = {
    "trend": "Moving-average trend filter",
    "tsmom": "Momentum",
    "vol_target": "Volatility-targeted trend",
    "rsi": "RSI dip-buying",
    "grid": "Grid bot",
}
DIRECTION = {"Buy": 1, "Overweight": 1, "Hold": 0, "Underweight": -1, "Sell": -1}
COIN_SEED = 2026
U32 = 0xFFFFFFFF


def coin_flips(n: int, seed: int = COIN_SEED) -> list[bool]:
    """Fair coin flips from a small seeded generator (mulberry32), so every page and post shows the same flips."""
    state = seed & U32
    flips = []
    for _ in range(n):
        state = (state + 0x6D2B79F5) & U32
        t = ((state ^ (state >> 15)) * (state | 1)) & U32
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & U32)) & U32)) & U32
        flips.append((t ^ (t >> 14)) / 4294967296 < 0.5)
    return flips


def rnd(x, digits: int = 4):
    if x is None or (isinstance(x, float) and x != x):
        return None
    return round(float(x), digits)


def pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def load_json(path):
    return json.loads(path.read_text())


def outcome(rating: str, ret: float | None) -> str:
    if ret is None:
        return "pending"
    direction = DIRECTION.get(rating, 0)
    if direction == 0:
        return "no call"
    return "right" if direction * ret > 0 else "wrong"


def family_block(family: str, summary: dict, curves: pd.DataFrame) -> dict:
    f = summary["families"][family]
    name = f["selected"]
    variants = sorted({k.split(" | ")[0] for k in summary["all_variants"] if k.startswith(f"{family}(")})
    return {
        "family": family,
        "name": FAMILY_NAMES[family],
        "selected": name,
        "full_cagr": {fee: rnd(f["by_fee"][fee]["cagr"]) for fee in FEE_SCENARIOS},
        "full_max_drawdown": rnd(f["full"]["max_drawdown"]),
        "test": {k: rnd(f["test"][k]) for k in ("cagr", "sharpe", "calmar", "max_drawdown", "total_return")},
        "test_benchmark": {k: rnd(f["test_benchmark"][k]) for k in ("cagr", "sharpe", "calmar", "max_drawdown", "total_return")},
        "deflated_sharpe": rnd(f["deflated_sharpe"]["dsr"], 3),
        "lenient_deflated_sharpe": rnd(f["post_hoc_lenient_dsr"], 3),
        "positive_fold_share": rnd(f["positive_fold_share"], 3),
        "eth_sharpe": rnd(f["eth"]["sharpe"], 3),
        "eth_benchmark_sharpe": rnd(f["eth_benchmark"]["sharpe"], 3),
        "gates": {k: v for k, v in f["gates"].items() if k != "all_passed"},
        "gates_passed": sum(1 for k, v in f["gates"].items() if k != "all_passed" and v),
        "trades": f["trades"],
        "annual_fee_drag": rnd(f["annual_fee_drag"]),
        "growth_weekly": {fee: [round(v, 1) for v in curves[f"{name} | {fee}"]] for fee in FEE_SCENARIOS},
        "walk_forward": [{"start": w["fold_start"], "end": w["fold_end"], "chosen": w["chosen"],
                          "return": rnd(w["return"]), "benchmark_return": rnd(w["benchmark_return"])}
                         for w in f["walk_forward"]],
        "regimes": {k: rnd(v["annual_return"]) for k, v in f["regimes"].items()},
        "variants": [
            {"name": v, "trades": summary["all_variants"][f"{v} | kraken_taker"]["trades"],
             "cagr": {fee: rnd(summary["all_variants"][f"{v} | {fee}"]["full"]["cagr"]) for fee in FEE_SCENARIOS}}
            for v in variants
        ],
    }


def ai_block(scores: dict) -> dict:
    pooled = scores["grid_pooled"]
    calls, hits = pooled["directional_calls"], pooled["hits"]
    needed = next(k for k in range(calls + 1) if binomtest(k, calls, 0.5, alternative="greater").pvalue < 0.05)
    weekly = []
    for ticker in ("BTC-USD", "ETH-USD"):
        for d in scores["grid"][ticker]["decisions"]:
            weekly.append({"date": d["date"], "ticker": ticker, "rating": d["rating"],
                           "return": rnd(d["week_return"]), "outcome": outcome(d["rating"], d["week_return"])})
    wrong = [w for w in weekly if w["outcome"] == "wrong"]
    biggest_miss = max(wrong, key=lambda w: abs(w["return"])) if wrong else None
    assets = []
    for run in ("grid", "grid_nvda"):
        for ticker, s in scores[run].items():
            assets.append({
                "ticker": ticker, "settled": s["settled"], "ratings": s["ratings"],
                "average_exposure": rnd(s["average_exposure"], 3), "agent_return": rnd(s["agent_return"]),
                "buy_and_hold_return": rnd(s["buy_and_hold_return"]),
                "constant_exposure_return": rnd(s["constant_exposure_return"]), "timing_skill": rnd(s["timing_skill"]),
                "hits": s["hits"], "calls": s["directional_calls"], "p_value": rnd(s["p_value"], 3),
            })
    cost = scores["cost"]
    return {
        "calls": calls, "hits": hits, "hit_rate": rnd(pooled["hit_rate"], 3), "p_value": rnd(pooled["p_value"], 3),
        "needed_for_significance": needed,
        "usd_per_decision": rnd(cost["usd_per_decision"]), "minutes_per_decision": rnd(cost["seconds_per_decision"] / 60, 2),
        "total_usd": rnd(cost["total_usd"], 2), "decisions": cost["decisions"],
        "repeat_ratings": scores.get("repeatability", {}).get("ratings", []),
        "repeat_cell": scores.get("repeatability", {}).get("cell", ""),
        "coin_seed": COIN_SEED,
        "coin_flips": coin_flips(calls),
        "assets": assets, "weekly_calls": weekly, "biggest_miss": biggest_miss,
        "window": [scores["grid"]["BTC-USD"]["decisions"][0]["date"], scores["grid"]["BTC-USD"]["decisions"][-1]["date"]],
    }


def headline(claim: dict) -> str:
    if claim["experiment"] == "backtest":
        best = max(claim["families"], key=lambda f: f["full_cagr"]["kraken_taker"])
        cagr = best["full_cagr"]["kraken_taker"]
        if cagr < 0:
            return f"Lost {pct(-cagr)} a year after real fees"
        passed = max(f["gates_passed"] for f in claim["families"])
        return f"At best {pct(cagr)} a year after real fees, about the same as holding; passed {passed} of 4 tests"
    if claim["experiment"] == "tradingagents":
        ai = claim["ai"]
        return f"{ai['hits']} of {ai['calls']} calls right, and no timing skill"
    if claim["experiment"] == "article_audit":
        c = claim["audit"]["costs"]
        return f"Assumes fees of {pct(c['article_per_side'], 2)} a trade; a UK retail account pays {pct(c['kraken_taker_per_side'], 2)}"
    raise ValueError(f"unknown experiment {claim['experiment']}")


def build() -> dict:
    summary = load_json(RESULTS / "backtest_summary.json")
    hype = load_json(RESULTS / "hype_waterfall.json")
    audit = load_json(RESULTS / "article_audit.json")
    scores = load_json(TA_RESULTS / "scores.json")
    content = tomllib.loads(CONTENT.read_text())
    curves = pd.read_csv(RESULTS / "growth_of_1000_weekly.csv", index_col="week", parse_dates=True)
    events = ledger.read()
    registration = next(e for e in events if e.get("event") == "preregistration")
    ai = ai_block(scores)

    bh = hype["buy_and_hold"]
    bh_growth = pd.Series(bh["growth_weekly"])
    underwater = (bh_growth / bh_growth.cummax() - 1).round(4).tolist()
    trend = summary["families"]["trend"]

    story = {
        "since": hype["since"], "until": hype["until"], "weeks": hype["weeks"],
        "buy_and_hold": {**{k: rnd(v) for k, v in bh.items() if k != "growth_weekly"},
                         "growth_weekly": bh["growth_weekly"], "underwater_weekly": underwater},
        "steps": [{k: (rnd(v) if isinstance(v, float) else v) for k, v in s.items()} for s in hype["steps"]],
        "hindsight": hype["hindsight"],
        "luck": hype["luck"],
        "fees": {
            "scenarios": FEE_SCENARIOS,
            "selected": trend["selected"],
            "selected_cagr": {fee: rnd(trend["by_fee"][fee]["cagr"]) for fee in FEE_SCENARIOS},
            "variants": [
                {"name": k.split(" | ")[0], "trades": v["trades"],
                 "cagr_article": rnd(v["full"]["cagr"]),
                 "cagr_taker": rnd(summary["all_variants"][k.replace("| article", "| kraken_taker")]["full"]["cagr"])}
                for k, v in summary["all_variants"].items() if k.endswith("| article")
            ],
        },
        "look_ahead": {k: {m: rnd(v[m]) for m in ("cagr", "sharpe", "max_drawdown")}
                       for k, v in summary["look_ahead_demo"].items()},
        "ai": ai,
        "feed": content["feed"],
        "sources": content["sources"],
    }

    claims = []
    for path in sorted(CLAIMS.glob("*.toml")):
        claim = tomllib.loads(path.read_text())
        if claim["experiment"] == "backtest":
            claim["families"] = [family_block(f, summary, curves) for f in claim["families"]]
        elif claim["experiment"] == "tradingagents":
            claim["ai"] = ai
        elif claim["experiment"] == "article_audit":
            claim["audit"] = audit
            claim["look_ahead"] = story["look_ahead"]
        claim["headline"] = headline(claim)
        claims.append(claim)
    claims.sort(key=lambda c: c["order"])

    forward = []
    for ticker, s in scores.get("forward", {}).items():
        for d in s["decisions"]:
            forward.append({"date": d["date"], "ticker": ticker, "rating": d["rating"],
                            "return": rnd(d["week_return"]), "outcome": outcome(d["rating"], d["week_return"])})
    with (PAPER / "ledger.csv").open() as f:
        paper_rows = list(csv.DictReader(f))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "preregistration_sha256": registration["sha256"],
            "preregistered_at": registration["timestamp"],
            "preregistration_changes": sum(1 for e in events if e.get("event") == "preregistration_changed"),
            "trials": summary["trials_logged"],
            "runs_logged": sum(1 for e in events if e.get("event") in ("run", "demo_run")),
            "fees": FEE_SCENARIOS,
            "design_period": "2017-08-17 to 2022-12-31",
            "test_period": "2023-01-01 to 2026-09-30",
            "data_range": [hype["since"], hype["until"]],
            "claims_tested": len(claims),
            "claims_passed": sum(1 for c in claims if c["verdict"] == "alpha"),
        },
        "story": story,
        "claims": claims,
        "live": {
            "forward_test": {**content["forward_test"], "calls": sorted(forward, key=lambda w: (w["date"], w["ticker"]))},
            "paper": {
                "config": load_json(PAPER / "config.json"),
                "rows": [{k: r[k] for k in ("bar_open", "close", "trade", "equity", "buy_and_hold_equity", "decided_target")}
                         for r in paper_rows],
            },
        },
        "method": {
            "gates": content["gates"],
            "limitations": [x["text"] for x in content["limitations"]],
            "corrections": content["corrections"],
            "preregistration_text": (REPO_ROOT / "experiments" / "preregistration.md").read_text(),
        },
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({OUT.stat().st_size / 1024:.0f} KB): "
          f"{data['meta']['claims_tested']} claims, {data['meta']['claims_passed']} passed")
    for c in data["claims"]:
        print(f"  {c['slug']:<24} {c['headline']}")


if __name__ == "__main__":
    main()
