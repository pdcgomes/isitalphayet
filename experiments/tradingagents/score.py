"""Score TradingAgents decisions as the pre-registration specifies.

Each rating sets an exposure held for 7 days from the decision date's close, paying Kraken taker fees
on every change. It is compared with buy-and-hold and with a constant exposure equal to the agent's
average, which isolates timing skill.

Usage (from the repo root): uv run python experiments/tradingagents/score.py
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import pandas as pd
import requests
from scipy.stats import binomtest

from lab.backtest import simulate
from lab.costs import FEE_SCENARIOS, GATE_SCENARIO

HERE = Path(__file__).resolve().parent
DECISIONS = HERE / "results" / "decisions.jsonl"
SCORES = HERE / "results" / "scores.json"

EXPOSURE = {"Buy": 1.0, "Overweight": 0.75, "Hold": 0.5, "Underweight": 0.25, "Sell": 0.0}
DIRECTION = {"Buy": 1, "Overweight": 1, "Underweight": -1, "Sell": -1}
HOLD_DAYS = 7


def daily_closes(symbol: str) -> pd.Series:
    """Daily closes from Yahoo Finance, the source TradingAgents itself reads, indexed by local trading date."""
    resp = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "1y", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    resp.raise_for_status()
    chart = resp.json()["chart"]["result"][0]
    tz = chart["meta"]["exchangeTimezoneName"]
    days = pd.to_datetime(chart["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    closes = pd.Series(chart["indicators"]["quote"][0]["close"], index=days, dtype=float).dropna()
    # The last bar can still be forming; only fully closed days count.
    return closes[closes.index < pd.Timestamp.now(tz=tz).normalize().tz_localize(None)]


def close_on_or_before(closes: pd.Series, day: pd.Timestamp) -> float:
    return float(closes.loc[:day].iloc[-1])


def score_ticker(decisions: list[dict], closes: pd.Series) -> dict:
    rows = []
    for d in sorted(decisions, key=lambda d: d["date"]):
        start = pd.Timestamp(d["date"])
        end = start + pd.Timedelta(days=HOLD_DAYS)
        settled = end <= closes.index[-1]
        entry = close_on_or_before(closes, start)
        exit_ = close_on_or_before(closes, end) if settled else None
        rows.append({
            "date": d["date"], "rating": d["rating"], "settled": settled,
            "entry": entry, "exit": exit_, "week_return": (exit_ / entry - 1) if settled else None,
        })
    weeks = pd.DataFrame(rows)
    done = weeks[weeks["settled"]].copy()
    out = {"decisions": rows, "settled": len(done), "pending": int((~weeks["settled"]).sum()),
           "ratings": weeks["rating"].value_counts().to_dict()}
    if done.empty:
        return out

    bars = pd.DataFrame({"open": done["entry"].to_numpy(), "close": done["exit"].to_numpy()},
                        index=pd.to_datetime(done["date"]))
    exposure = done["rating"].map(EXPOSURE).fillna(0.5)
    exposure.index = bars.index
    fee = FEE_SCENARIOS[GATE_SCENARIO]
    # Bar k opens at the decision's own close, so filling on the same bar (lag=0) uses no future price.
    agent = simulate(bars, exposure, fee, lag=0)
    passive = simulate(bars, pd.Series(1.0, index=bars.index), fee, lag=0)
    constant = simulate(bars, pd.Series(exposure.mean(), index=bars.index), fee, lag=0)

    directional = done[done["rating"].isin(DIRECTION)]
    hits = int(sum(DIRECTION[r] * w > 0 for r, w in zip(directional["rating"], directional["week_return"])))
    calls = len(directional)
    out.update({
        "average_exposure": float(exposure.mean()),
        "agent_return": float(agent.equity.iloc[-1] / agent.capital - 1),
        "buy_and_hold_return": float(passive.equity.iloc[-1] / passive.capital - 1),
        "constant_exposure_return": float(constant.equity.iloc[-1] / constant.capital - 1),
        "timing_skill": float((agent.equity.iloc[-1] - constant.equity.iloc[-1]) / agent.capital),
        "directional_calls": calls,
        "hits": hits,
        "hit_rate": hits / calls if calls else None,
        "p_value": binomtest(hits, calls, 0.5, alternative="greater").pvalue if calls else None,
    })
    return out


def main() -> None:
    records = [json.loads(line) for line in DECISIONS.read_text().splitlines() if line.strip()]
    decisions = [r for r in records if r.get("rating")]
    closes = {t: daily_closes(t) for t in sorted({d["ticker"] for d in decisions})}

    scores: dict = {"cost": {
        "total_usd": round(sum(r["cost_usd"] for r in records), 2),
        "decisions": len(decisions),
        "usd_per_decision": round(sum(d["cost_usd"] for d in decisions) / len(decisions), 4),
        "seconds_per_decision": round(sum(d["seconds"] for d in decisions) / len(decisions), 1),
    }}
    for run in ("grid", "grid_nvda", "forward"):
        by_ticker = {}
        for ticker in sorted({d["ticker"] for d in decisions if d["run"] == run}):
            cells = [d for d in decisions if d["run"] == run and d["ticker"] == ticker]
            by_ticker[ticker] = score_ticker(cells, closes[ticker])
        if by_ticker:
            scores[run] = by_ticker

    # Pooled evidence-of-skill test over the crypto clean window.
    crypto = [s for s in scores.get("grid", {}).values() if s.get("directional_calls")]
    calls, hits = sum(s["directional_calls"] for s in crypto), sum(s["hits"] for s in crypto)
    if calls:
        scores["grid_pooled"] = {
            "directional_calls": calls, "hits": hits, "hit_rate": hits / calls,
            "p_value": binomtest(hits, calls, 0.5, alternative="greater").pvalue,
            "timing_skill_positive": all(s["timing_skill"] > 0 for s in crypto),
        }

    repeats = [d["rating"] for d in decisions if d["run"].startswith("repeat_")]
    if repeats:
        pairs = list(combinations(repeats, 2))
        scores["repeatability"] = {
            "cell": "BTC-USD 2026-09-28",
            "ratings": repeats,
            "share_of_pairs_that_disagree": sum(a != b for a, b in pairs) / len(pairs) if pairs else None,
        }

    SCORES.write_text(json.dumps(scores, indent=2, default=float))
    print(json.dumps({k: v for k, v in scores.items() if k in ("cost", "grid_pooled", "repeatability")}, indent=2))
    for run in ("grid", "grid_nvda", "forward"):
        for ticker, s in scores.get(run, {}).items():
            if s.get("settled"):
                print(f"{run:<10} {ticker:<8} settled {s['settled']:>2}  agent {s['agent_return']:+.1%}  "
                      f"buy&hold {s['buy_and_hold_return']:+.1%}  constant {s['constant_exposure_return']:+.1%}  "
                      f"timing {s['timing_skill']:+.1%}  hit rate {s['hits']}/{s['directional_calls']}  "
                      f"p={s['p_value']:.2f}  ratings {s['ratings']}")
            else:
                print(f"{run:<10} {ticker:<8} pending {s['pending']}  ratings {s['ratings']}")


if __name__ == "__main__":
    main()
