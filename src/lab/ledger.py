"""Append-only ledger of every run, so the number of strategies tried can never be understated."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .data import REPO_ROOT

LEDGER = REPO_ROOT / "experiments" / "trials.jsonl"
PREREGISTRATION = REPO_ROOT / "experiments" / "preregistration.md"


def read() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def append(record: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    stamped = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with LEDGER.open("a") as f:
        f.write(json.dumps(stamped, default=float) + "\n")


def check_preregistration(path: Path = PREREGISTRATION) -> str:
    """Return a pre-registration's hash, logging a visible event if it changed since it was registered."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    name = str(path.relative_to(REPO_ROOT))
    registered = [e["sha256"] for e in read()
                  if e.get("event") in ("preregistration", "preregistration_changed") and e.get("file") == name]
    if not registered or registered[-1] != digest:
        event = "preregistration_changed" if registered else "preregistration"
        append({"event": event, "file": name, "sha256": digest})
    return digest


def trial_sharpes(asset: str, fee: str) -> dict[str, float]:
    """Latest full-period daily Sharpe of every distinct variant ever run on `asset` as a trial."""
    latest: dict[str, float] = {}
    for e in read():
        if e.get("event") == "run" and e.get("counts_as_trial") and e["asset"] == asset and e["fee"] == fee:
            latest[e["variant"]] = e["sharpe_daily_full"]
    return latest
