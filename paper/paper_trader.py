"""Paper-trade the pre-registered candidate on Kraken's public prices, one closed bar at a time.

Each run processes every bar that has closed since the last run: it fills the pending decision at
the bar's open (taker fee and slippage included), marks the position at the close, and records the
next decision exactly as computed now. A decision is only filled at an open no earlier than the
moment it was recorded (within LATE_AFTER), so a late or catch-up run never trades at a past price.
The ledger is append-only, so it can later be checked against a fresh recomputation with --verify.

Usage (from the repo root):
    uv run python paper/paper_trader.py            # run once; safe to repeat, catches up missed bars
    uv run python paper/paper_trader.py --verify   # recompute every logged decision from fresh candles

PAPER_DATA_DIR overrides where the config and ledger live (default: this folder).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lab.backtest import MIN_REBALANCE
from lab.costs import FEE_SCENARIOS, GATE_SCENARIO
from lab.data import REPO_ROOT, kraken_ohlc
from lab.strategies import PREREGISTERED

DATA_DIR = Path(os.environ.get("PAPER_DATA_DIR", Path(__file__).resolve().parent))
CONFIG = DATA_DIR / "config.json"
LEDGER = DATA_DIR / "ledger.csv"
SUMMARY = REPO_ROOT / "experiments" / "results" / "backtest_summary.json"
LATE_AFTER = pd.Timedelta(hours=1)
FIELDS = [
    "bar_open", "open", "close", "executed_target", "fill_price", "trade", "units", "cash",
    "fees_paid", "equity", "buy_and_hold_equity", "decided_target", "computed_at",
]


def load_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    candidate = json.loads(SUMMARY.read_text())["paper_candidate"]
    config = {
        "variant": candidate["variant"],
        "label": candidate["label"],
        "pair": "XBTGBP",
        "capital_gbp": 1000.0,
        "fee_per_side": FEE_SCENARIOS[GATE_SCENARIO],
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2))
    return config


def read_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    with LEDGER.open() as f:
        return list(csv.DictReader(f))


def append_rows(rows: list[dict]) -> None:
    new_file = not LEDGER.exists()
    with LEDGER.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def run(config: dict, candles: pd.DataFrame | None = None, now: pd.Timestamp | None = None) -> None:
    variant = next(v for v in PREREGISTERED if v.name == config["variant"])
    if candles is None:
        candles = kraken_ohlc(config["pair"], variant.interval)
    targets = variant.target(candles)  # trailing indicators: each value uses only bars up to its own
    ledger = read_ledger()
    now = now or pd.Timestamp.now(tz="UTC")
    fee = config["fee_per_side"]

    if not ledger:
        first = candles.index[-1]
        append_rows([{
            "bar_open": first.isoformat(), "open": candles.at[first, "open"], "close": candles.at[first, "close"],
            "executed_target": "", "fill_price": "", "trade": "start", "units": 0.0, "cash": config["capital_gbp"],
            "fees_paid": 0.0, "equity": config["capital_gbp"], "buy_and_hold_equity": config["capital_gbp"],
            "decided_target": targets.at[first], "computed_at": now.isoformat(),
        }])
        ledger = read_ledger()

    last = ledger[-1]
    units, cash, fees = float(last["units"]), float(last["cash"]), float(last["fees_paid"])
    pending, pending_at = float(last["decided_target"]), pd.Timestamp(last["computed_at"])
    bh_entered = [r for r in ledger if r["trade"] not in ("start", "waiting")]
    bh_units = float(bh_entered[0]["buy_and_hold_equity"]) / float(bh_entered[0]["close"]) if bh_entered else None
    rows = []
    for bar in candles.index[candles.index > pd.Timestamp(last["bar_open"])]:
        price, close = candles.at[bar, "open"], candles.at[bar, "close"]
        fillable = pending_at <= bar + LATE_AFTER
        if fillable and bh_units is None:  # buy-and-hold enters at the strategy's first fillable open
            bh_units = config["capital_gbp"] / (price * (1 + fee))
        value = cash + units * price
        current = units * price / value
        trade = "none" if fillable else "waiting"
        if fillable and abs(pending - current) > max(variant.band, MIN_REBALANCE):
            if pending > current:
                spend = min((pending - current) * value, cash / (1 + fee))
                units, cash, fees, trade = units + spend / price, cash - spend * (1 + fee), fees + spend * fee, "buy"
            else:
                proceeds = units * price if pending == 0.0 else (current - pending) * value
                units = 0.0 if pending == 0.0 else units - proceeds / price
                cash, fees, trade = cash + proceeds * (1 - fee), fees + proceeds * fee, "sell"
        decided = float(targets.at[bar])
        rows.append({
            "bar_open": bar.isoformat(), "open": price, "close": close,
            "executed_target": pending if fillable else "", "fill_price": price if fillable else "",
            "trade": trade, "units": units, "cash": cash, "fees_paid": fees, "equity": cash + units * close,
            "buy_and_hold_equity": bh_units * close if bh_units else config["capital_gbp"],
            "decided_target": decided, "computed_at": now.isoformat(),
        })
        pending, pending_at = decided, now
    append_rows(rows)

    latest = read_ledger()[-1]
    print(f"{config['variant']} on {config['pair']} ({config['label']}): {len(rows)} new bar(s); "
          f"last bar {latest['bar_open'][:10]}, equity £{float(latest['equity']):,.2f} vs buy-and-hold "
          f"£{float(latest['buy_and_hold_equity']):,.2f}; next target weight {float(latest['decided_target']):.2f}")


def verify(config: dict) -> None:
    variant = next(v for v in PREREGISTERED if v.name == config["variant"])
    candles = kraken_ohlc(config["pair"], variant.interval)
    targets = variant.target(candles)
    mismatches, worst_close_gap = [], 0.0
    for row in read_ledger():
        bar = pd.Timestamp(row["bar_open"])
        if bar not in candles.index:
            continue
        worst_close_gap = max(worst_close_gap, abs(candles.at[bar, "close"] / float(row["close"]) - 1))
        if float(targets.at[bar]) != float(row["decided_target"]):
            mismatches.append((row["bar_open"], row["decided_target"], float(targets.at[bar])))
    print(f"Decisions that differ on recomputation: {len(mismatches)} {mismatches[:5]}")
    print(f"Largest revision to a logged close: {worst_close_gap:.4%}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    config = load_config()
    if parser.parse_args().verify:
        verify(config)
    else:
        run(config)


if __name__ == "__main__":
    main()
