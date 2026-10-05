import csv
import importlib.util

import numpy as np
import pandas as pd
import pytest

from lab.data import REPO_ROOT

spec = importlib.util.spec_from_file_location("paper_trader", REPO_ROOT / "paper" / "paper_trader.py")
paper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paper)

CONFIG = {"variant": "trend(n=50)", "label": "test", "pair": "XBTGBP", "capital_gbp": 1000.0, "fee_per_side": 0.0}


@pytest.fixture
def ledger_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paper, "LEDGER", tmp_path / "ledger.csv")
    return tmp_path


def rising_candles(days: int) -> pd.DataFrame:
    close = 100 * np.exp(np.linspace(0, 0.5, days))
    index = pd.date_range("2026-01-01", periods=days, freq="D", tz="UTC")
    return pd.DataFrame({"open": np.r_[100.0, close[:-1]], "close": close}, index=index)


def rows():
    with paper.LEDGER.open() as f:
        return list(csv.DictReader(f))


def test_a_timely_decision_fills_at_the_next_open(ledger_dir):
    candles = rising_candles(80)
    first_close = candles.index[-2] + pd.Timedelta(days=1)
    paper.run(CONFIG, candles.iloc[:-1], now=first_close + pd.Timedelta(minutes=5))
    paper.run(CONFIG, candles, now=first_close + pd.Timedelta(days=1, minutes=5))
    last = rows()[-1]
    assert last["trade"] == "buy"
    assert float(last["fill_price"]) == pytest.approx(candles["open"].iloc[-1])


def test_a_late_decision_waits_for_a_later_open(ledger_dir):
    candles = rising_candles(80)
    first_close = candles.index[-2] + pd.Timedelta(days=1)
    paper.run(CONFIG, candles.iloc[:-1], now=first_close + pd.Timedelta(hours=15))
    paper.run(CONFIG, candles, now=first_close + pd.Timedelta(days=1, minutes=5))
    last = rows()[-1]
    assert last["trade"] == "waiting"
    assert last["fill_price"] == ""


def test_running_twice_adds_nothing(ledger_dir):
    candles = rising_candles(80)
    now = candles.index[-1] + pd.Timedelta(days=1, minutes=5)
    paper.run(CONFIG, candles, now=now)
    paper.run(CONFIG, candles, now=now + pd.Timedelta(minutes=1))
    assert len(rows()) == 1
