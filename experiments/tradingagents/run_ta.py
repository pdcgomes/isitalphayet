"""Run TradingAgents v0.6.0 under the pre-registered protocol, with per-decision cost tracking and a hard budget.

Usage (from the repo root):
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py probe
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py grid [--tickers BTC-USD,ETH-USD]
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py grid --tickers NVDA --asset-type stock --run grid_nvda
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py repeat
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py forward [--date YYYY-MM-DD]
    experiments/tradingagents/.venv/bin/python experiments/tradingagents/run_ta.py spend
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
# This machine's shell points OpenAI clients at another provider (OPENAI_API_BASE) with its own key,
# so .env must win and the base-URL overrides must go. Both precede the tradingagents import,
# which reads TRADINGAGENTS_* at import time.
load_dotenv(REPO_ROOT / ".env", override=True)
for var in ("OPENAI_API_BASE", "OPENAI_BASE_URL"):
    os.environ.pop(var, None)
OPENAI_ENDPOINT = "https://api.openai.com/v1"

from langchain_core.callbacks import UsageMetadataCallbackHandler  # noqa: E402
from tradingagents.default_config import DEFAULT_CONFIG  # noqa: E402
from tradingagents.graph.trading_graph import TradingAgentsGraph  # noqa: E402

STATE = HERE / "state"
RESULTS = HERE / "results"
DECISIONS = RESULTS / "decisions.jsonl"

BUDGET_USD = 35.0
CRYPTO_ANALYSTS = ("market", "social", "news")
STOCK_ANALYSTS = ("market", "social", "news", "fundamentals")
GRID_DATES = [(date(2026, 6, 1) + timedelta(weeks=k)).isoformat() for k in range(18)]  # Mondays to 2026-09-28
REPEAT_CELL = ("BTC-USD", "2026-09-28")
FORWARD_TICKERS = ("BTC-USD", "ETH-USD")

# USD per million tokens, from developers.openai.com on 2026-10-05.
PRICES = {
    "gpt-6-luna": {"input": 0.10, "cached": 0.01, "output": 0.50},
    "gpt-6-sol": {"input": 2.00, "cached": 0.20, "output": 10.00},
}
# Cache writes are billed at 1.25x input and usage does not say which inputs were written,
# so every uncached input token is priced as a write. This overstates cost, never understates it.
CACHE_WRITE_MULTIPLIER = 1.25


def price(usage: dict[str, dict]) -> float:
    total = 0.0
    for model, u in usage.items():
        rates = next((p for name, p in PRICES.items() if model.startswith(name)), None)
        if rates is None:
            raise RuntimeError(f"No price for model {model!r}; refusing to run without a cost estimate")
        cached = (u.get("input_token_details") or {}).get("cache_read", 0)
        uncached = u.get("input_tokens", 0) - cached
        total += (uncached * rates["input"] * CACHE_WRITE_MULTIPLIER + cached * rates["cached"]
                  + u.get("output_tokens", 0) * rates["output"]) / 1e6
    return total


def usage_delta(after: dict, before: dict) -> dict:
    delta = {}
    for model, u in after.items():
        b = before.get(model, {})
        cached = (u.get("input_token_details") or {}).get("cache_read", 0)
        cached_before = (b.get("input_token_details") or {}).get("cache_read", 0)
        delta[model] = {
            "input_tokens": u.get("input_tokens", 0) - b.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0) - b.get("output_tokens", 0),
            "input_token_details": {"cache_read": cached - cached_before},
        }
    return delta


def read_decisions() -> list[dict]:
    if not DECISIONS.exists():
        return []
    return [json.loads(line) for line in DECISIONS.read_text().splitlines() if line.strip()]


def spent() -> float:
    return sum(d["cost_usd"] for d in read_decisions())


class Session:
    """One TradingAgents graph with its own memory log, plus the bookkeeping the protocol needs."""

    def __init__(self, run: str, asset_type: str = "crypto"):
        self.run = run
        self.asset_type = asset_type
        run_dir = STATE / "runs" / run
        self.config = {
            **copy.deepcopy(DEFAULT_CONFIG),
            "results_dir": str(run_dir),
            "data_cache_dir": str(STATE / "cache"),
            "memory_log_path": str(run_dir / "trading_memory.md"),
            "backend_url": OPENAI_ENDPOINT,
        }
        assert self.config["llm_provider"] == "openai", "the protocol fixes OpenAI; check .env"
        self.usage = UsageMetadataCallbackHandler()
        analysts = CRYPTO_ANALYSTS if asset_type == "crypto" else STOCK_ANALYSTS
        self.graph = TradingAgentsGraph(analysts, config=self.config, callbacks=[self.usage])

    def done(self) -> set[tuple[str, str]]:
        return {(e["ticker"], e["date"]) for e in self.graph.memory_log.load_entries()}

    def decide(self, ticker: str, trade_date: str) -> dict:
        prior = [d["cost_usd"] for d in read_decisions()]
        expected = max(prior) if prior else 1.0
        if sum(prior) + expected > BUDGET_USD:
            raise SystemExit(f"Budget stop: ${sum(prior):.2f} spent, next decision could cost ${expected:.2f}")
        before = copy.deepcopy(self.usage.usage_metadata)
        started = time.time()
        final_state, rating = self.graph.propagate(ticker, trade_date, asset_type=self.asset_type)
        usage = usage_delta(self.usage.usage_metadata, before)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run": self.run,
            "ticker": ticker,
            "date": trade_date,
            "rating": rating,
            "seconds": round(time.time() - started, 1),
            "cost_usd": round(price(usage), 4),
            "usage": usage,
            "decision_excerpt": (final_state.get("final_trade_decision") or "")[:1500],
        }
        RESULTS.mkdir(parents=True, exist_ok=True)
        with DECISIONS.open("a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"{self.run}: {ticker} {trade_date} -> {rating}  ({record['seconds']:.0f}s, ${record['cost_usd']:.3f}, "
              f"total ${spent():.2f})", flush=True)
        return record

    def settle(self, tickers) -> None:
        before = copy.deepcopy(self.usage.usage_metadata)
        for ticker in tickers:
            self.graph.settle_pending(ticker)
        cost = price(usage_delta(self.usage.usage_metadata, before))
        with DECISIONS.open("a") as f:
            f.write(json.dumps({"run": self.run, "ticker": "settlement", "date": None, "rating": None,
                                "cost_usd": round(cost, 4)}) + "\n")


def run_cells(session: Session, cells: list[tuple[str, str]]) -> None:
    done = session.done()
    for ticker, trade_date in cells:
        if (ticker, trade_date) not in done:
            session.decide(ticker, trade_date)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["probe", "grid", "repeat", "forward", "spend"])
    parser.add_argument("--tickers", default="BTC-USD,ETH-USD")
    parser.add_argument("--asset-type", default="crypto", choices=["crypto", "stock"])
    parser.add_argument("--run", default="grid")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    if args.command == "spend":
        print(f"Estimated spend so far: ${spent():.2f} of ${BUDGET_USD:.2f}")
    elif args.command == "probe":
        run_cells(Session("grid"), [("BTC-USD", GRID_DATES[0])])
    elif args.command == "grid":
        session = Session(args.run, args.asset_type)
        tickers = args.tickers.split(",")
        run_cells(session, [(t, d) for t in tickers for d in GRID_DATES])
        session.settle(tickers)
    elif args.command == "repeat":
        for k in (1, 2, 3):
            run_cells(Session(f"repeat_{k}"), [REPEAT_CELL])
    elif args.command == "forward":
        session = Session("forward")
        run_cells(session, [(t, args.date) for t in FORWARD_TICKERS])
        session.settle(FORWARD_TICKERS)
    print(f"Estimated spend so far: ${spent():.2f} of ${BUDGET_USD:.2f}")


if __name__ == "__main__":
    main()
