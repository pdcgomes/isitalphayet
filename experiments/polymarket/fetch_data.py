"""Download the pinned Polymarket datasets named in experiments/polymarket/preregistration.md into data/polymarket/.

    uv run python experiments/polymarket/fetch_data.py wallets   # D1, about 1.7 GB
    uv run python experiments/polymarket/fetch_data.py books     # D2, ten daily archives, about 7 GB
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
from pathlib import Path

import requests

from lab.data import REPO_ROOT
from lab.ledger import check_preregistration

PREREG = REPO_ROOT / "experiments" / "polymarket" / "preregistration.md"
DATA = REPO_ROOT / "data" / "polymarket"

WALLETS_REPO = "vgregoire/polymarket-users"
WALLETS_REVISION = "91ddb961b090de18fd79e79edd8fa15f36ca11b9"
WALLETS_FILES = ["user_pnl_summary.parquet", "user_features.parquet", "pnl_change_monthly.parquet", "markets.parquet",
                 "predictions.parquet", "events.parquet", "ohlcv_1d.parquet"]

BOOKS_REPO = "whodisidk/polymarket-btc-updown-exchange-data"
BOOKS_REVISION = "03e7d08b585325fa1468001982edae262c69429c"
BOOK_DAYS_BEFORE_TWAP = ["2026-05-31", "2026-06-01", "2026-06-14", "2026-06-27", "2026-07-06"]
BOOK_DAYS_AFTER_TWAP = ["2026-08-19", "2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27"]
BOOK_DAYS = BOOK_DAYS_BEFORE_TWAP + BOOK_DAYS_AFTER_TWAP


def hf_url(repo: str, revision: str, name: str) -> str:
    return f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{name}"


def download(url: str, dest: Path) -> Path:
    """Stream to disk, resuming a partial download."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists():
        return dest
    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        if r.status_code == 416:
            part.rename(dest)
            return dest
        r.raise_for_status()
        mode = "ab" if r.status_code == 206 else "wb"
        total = int(r.headers.get("Content-Length", 0)) + (have if mode == "ab" else 0)
        done = have if mode == "ab" else 0
        with part.open(mode) as f:
            for chunk in r.iter_content(chunk_size=8 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {dest.name}: {done / 1e9:.2f} of {total / 1e9:.2f} GB", end="", flush=True)
    print()
    part.rename(dest)
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_wallets() -> None:
    for name in WALLETS_FILES:
        download(hf_url(WALLETS_REPO, WALLETS_REVISION, name), DATA / "wallets" / name)


def manifest() -> dict[str, tuple[str, int]]:
    text = requests.get(hf_url(BOOKS_REPO, BOOKS_REVISION, "MANIFEST.txt"), timeout=60).text
    rows = [line.split() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return {name: (digest, int(size)) for name, digest, size in rows}


def fetch_books() -> None:
    expected = manifest()
    for day in BOOK_DAYS:
        name = f"market_parquet_{day}.tar.gz"
        target = DATA / "books" / day
        if (target / ".complete").exists():
            continue
        archive = download(hf_url(BOOKS_REPO, BOOKS_REVISION, name), DATA / "books" / "archives" / name)
        digest, size = expected[name]
        if archive.stat().st_size != size or sha256(archive) != digest:
            archive.unlink()
            sys.exit(f"{name} failed its checksum; deleted, rerun to download again")
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tar:
            tar.extractall(target, filter="data")
        (target / ".complete").write_text(digest + "\n")
        archive.unlink()
        print(f"  {day}: verified and unpacked")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["wallets", "books"])
    args = parser.parse_args()
    check_preregistration(PREREG)
    fetch_wallets() if args.what == "wallets" else fetch_books()


if __name__ == "__main__":
    main()
