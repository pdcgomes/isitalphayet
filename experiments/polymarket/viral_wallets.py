"""Test 6: month-by-month profit of the wallets viral posts and paid bots point to (Polymarket Data API)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import requests

from lab.data import REPO_ROOT
from lab.ledger import check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
RAW = REPO_ROOT / "data" / "polymarket" / "viral"
OUT = REPO_ROOT / "experiments" / "polymarket" / "results" / "viral_wallets.json"
API = "https://data-api.polymarket.com/v2/user-pnl"

WALLETS = {
    "0x63ce342161250d705dc0b16df89036c8e5f9ba9a": "0x8dxd, the \"$313 into $414K\" latency bot",
    "0xd0d6053c3c37e727402d84c14069780d360993aa": "the \"$68 into $1.5M\" account a $499 bot copies",
    "0xdf4c6a942bd95bf903d6066b4ba7051e6f914f22": "that bot vendor's own live bot",
}
FEE_CHANGES = {"2026-01-05": "Taker fees on 15-minute crypto markets",
               "2026-03-06": "Fees on all crypto markets",
               "2026-03-30": "Fees on most other categories"}
# Cumulative fields in each daily point; the monthly change of each is reported.
FIELDS = {"position_pnl": "trading_profit", "wallet_income": "rebates_rewards_referrals", "fees_paid": "fees_paid",
          "volume_usdc": "volume", "trade_count": "trades"}


def fetch(address: str) -> dict:
    r = requests.get(API, params={"user": address, "interval": "all", "fidelity": "1d"}, timeout=60)
    r.raise_for_status()
    payload = r.json()
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{address}.json").write_text(json.dumps(payload))
    return payload["data"]


def monthly(points: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(points)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.set_index("date")[list(FIELDS)].astype(float).ffill().fillna(0)
    end_of_month = df.resample("ME").last()
    change = end_of_month.diff()
    change.iloc[0] = end_of_month.iloc[0]
    change = change.rename(columns=FIELDS)
    change.index = change.index.strftime("%Y-%m")
    return change


def main() -> None:
    check_preregistration(PREREG)
    wallets = []
    for address, label in WALLETS.items():
        data = fetch(address)
        table = monthly(data["points"])
        wallets.append({
            "address": address, "label": label,
            "first_day": datetime.fromtimestamp(data["points"][0]["timestamp"], timezone.utc).date().isoformat(),
            "months": [{"month": m, **{k: round(float(v), 2) for k, v in row.items()}} for m, row in table.iterrows()],
        })
        print(f"\n{label} ({address[:10]}…)")
        print(table.round(0).to_string())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "source": API, "fee_changes": FEE_CHANGES, "wallets": wallets}, indent=1))
    print(f"\nWrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
