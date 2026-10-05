"""Price data: Binance public dumps for history, Kraken's public API for recent GBP prices."""

from __future__ import annotations

import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

STUDY_START = "2017-08-17"
STUDY_END = "2026-09-30"

SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
INTERVALS = {"1d": pd.Timedelta(days=1), "4h": pd.Timedelta(hours=4)}

_BINANCE_MONTHLY = "https://data.binance.vision/data/spot/monthly/klines/{s}/{i}/{s}-{i}-{p}.zip"
_BINANCE_DAILY = "https://data.binance.vision/data/spot/daily/klines/{s}/{i}/{s}-{i}-{p}.zip"
_KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
_KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]
_OHLCV = ["open", "high", "low", "close", "volume"]


def _get(url: str, params: dict | None = None, attempts: int = 4) -> requests.Response | None:
    """GET with retries. Returns None on 404, which Binance uses for files not yet published."""
    for attempt in range(attempts):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    return None


def _binance_zip(url: str) -> pd.DataFrame | None:
    resp = _get(url)
    if resp is None:
        return None
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        raw = pd.read_csv(zf.open(zf.namelist()[0]), header=None, names=_KLINE_COLUMNS)
    open_time = pd.to_numeric(raw["open_time"], errors="coerce")
    raw, open_time = raw[open_time.notna()], open_time[open_time.notna()].astype("int64")
    # Binance switched spot dumps from milliseconds to microseconds on 2025-01-01.
    open_time = open_time.where(open_time < 10**14, open_time // 1000)
    frame = raw[_OHLCV].astype(float)
    frame.index = pd.DatetimeIndex(pd.to_datetime(open_time, unit="ms", utc=True), name="time")
    return frame


def _binance_period(symbol: str, interval: str, month: pd.Period) -> pd.DataFrame:
    frame = _binance_zip(_BINANCE_MONTHLY.format(s=symbol, i=interval, p=month.strftime("%Y-%m")))
    if frame is not None:
        return frame
    days = pd.date_range(month.start_time, month.end_time, freq="D")
    parts = [_binance_zip(_BINANCE_DAILY.format(s=symbol, i=interval, p=d.strftime("%Y-%m-%d"))) for d in days]
    parts = [p for p in parts if p is not None]
    if not parts:
        raise RuntimeError(f"{symbol} {interval}: no data published for {month}")
    return pd.concat(parts)


def binance_klines(asset: str, interval: str, refresh: bool = False) -> pd.DataFrame:
    """Study-period candles indexed by open time (UTC), cached as parquet."""
    symbol = SYMBOLS[asset]
    path = DATA_DIR / f"binance_{symbol}_{interval}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    months = pd.period_range(STUDY_START[:7], STUDY_END[:7], freq="M")
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(lambda m: _binance_period(symbol, interval, m), months))
    frame = pd.concat(parts).sort_index()
    frame = frame[~frame.index.duplicated(keep="first")].loc[STUDY_START:STUDY_END]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    return frame


def kraken_ohlc(pair: str = "XBTGBP", interval: str = "1d") -> pd.DataFrame:
    """Kraken's most recent ~720 closed candles (public endpoint, no account needed)."""
    minutes = int(INTERVALS[interval] / pd.Timedelta(minutes=1))
    body = _get(_KRAKEN_OHLC, params={"pair": pair, "interval": minutes}).json()
    if body.get("error"):
        raise RuntimeError(f"Kraken error: {body['error']}")
    rows = next(v for k, v in body["result"].items() if k != "last")
    raw = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
    frame = raw[_OHLCV].astype(float)
    frame.index = pd.DatetimeIndex(pd.to_datetime(raw["time"].astype("int64"), unit="s", utc=True), name="time")
    closed = frame.index + INTERVALS[interval] <= pd.Timestamp.now(tz="UTC")
    return frame[closed]


def check_candles(frame: pd.DataFrame, interval: str) -> dict:
    """Integrity report: duplicate timestamps, missing bars, impossible OHLC values."""
    expected = pd.date_range(frame.index[0], frame.index[-1], freq=INTERVALS[interval])
    missing = expected.difference(frame.index)
    body_high = frame[["open", "close"]].max(axis=1)
    body_low = frame[["open", "close"]].min(axis=1)
    prices = frame[["open", "high", "low", "close"]]
    impossible = (frame["high"] < body_high) | (frame["low"] > body_low) | (prices <= 0).any(axis=1)
    return {
        "bars": len(frame),
        "start": str(frame.index[0]),
        "end": str(frame.index[-1]),
        "duplicates": int(frame.index.duplicated().sum()),
        "missing_bars": len(missing),
        "missing_examples": [str(t) for t in missing[:5]],
        "impossible_ohlc": int(impossible.sum()),
    }


def main() -> None:
    for asset in SYMBOLS:
        for interval in INTERVALS:
            frame = binance_klines(asset, interval, refresh=True)
            print(f"Binance {asset} {interval}:", check_candles(frame, interval))
    for interval in INTERVALS:
        frame = kraken_ohlc("XBTGBP", interval)
        print(f"Kraken XBTGBP {interval}:", check_candles(frame, interval))


if __name__ == "__main__":
    main()
