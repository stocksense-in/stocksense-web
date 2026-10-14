"""
The NSE equity universe, from NSE's official EQUITY_L.csv.

The list is cached in backend/_nse_symbols_cache.json for 24 hours. The cache
is committed to git so the pipeline still works when NSE blocks the download
(it often rejects requests from cloud IPs).
"""

from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import asdict, dataclass

import requests

from .config import BACKEND_DIR
from .log import get_logger

log = get_logger(__name__)

NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
CACHE_FILE = BACKEND_DIR / "_nse_symbols_cache.json"
CACHE_TTL_SECONDS = 24 * 60 * 60

# EQ = regular equity, BE/BZ = trade-for-trade, SM/ST = SME platform.
INCLUDE_SERIES = {"EQ", "BE", "BZ", "SM", "ST"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,*/*;q=0.8",
    "Referer": "https://www.nseindia.com/",
}


@dataclass(frozen=True)
class Symbol:
    symbol: str  # NSE trading symbol, e.g. "INFY"
    name: str  # e.g. "Infosys Limited"
    series: str
    isin: str  # e.g. "INE009A01021" — Upstox instrument keys use this

    @property
    def yahoo(self) -> str:
        return f"{self.symbol}.NS"

    @property
    def yahoo_bse(self) -> str:
        return f"{self.symbol}.BO"


def _download() -> list[Symbol]:
    log.info("Downloading NSE equity list…")
    resp = requests.get(NSE_EQUITY_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()

    symbols = []
    for raw in csv.DictReader(io.StringIO(resp.text)):
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        if row.get("SYMBOL") and row.get("SERIES") in INCLUDE_SERIES:
            symbols.append(
                Symbol(
                    symbol=row["SYMBOL"],
                    name=row.get("NAME OF COMPANY", ""),
                    series=row["SERIES"],
                    isin=row.get("ISIN NUMBER", ""),
                )
            )
    return symbols


def _read_cache() -> list[Symbol]:
    data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return [Symbol(d["symbol"], d["name"], d["series"], d.get("isin", "")) for d in data]


def _write_cache(symbols: list[Symbol]) -> None:
    CACHE_FILE.write_text(
        json.dumps([asdict(s) for s in symbols], ensure_ascii=False), encoding="utf-8"
    )


def all_symbols(force_refresh: bool = False) -> list[Symbol]:
    cache_fresh = (
        CACHE_FILE.exists() and time.time() - CACHE_FILE.stat().st_mtime < CACHE_TTL_SECONDS
    )
    if cache_fresh and not force_refresh:
        return _read_cache()

    try:
        symbols = _download()
    except requests.RequestException as exc:
        if CACHE_FILE.exists():
            log.warning(f"NSE download failed ({exc}); using the cached list.")
            return _read_cache()
        raise
    _write_cache(symbols)
    log.info(f"Fetched {len(symbols)} NSE symbols.")
    return symbols


def select(
    symbols: list[str] | None = None,
    limit: int | None = None,
    force_refresh: bool = False,
) -> list[Symbol]:
    """Pick the stocks a job should process: specific symbols, the first N, or everything."""
    universe = all_symbols(force_refresh)
    if symbols:
        wanted = {s.upper() for s in symbols}
        chosen = [s for s in universe if s.symbol in wanted]
        missing = wanted - {s.symbol for s in chosen}
        if missing:
            log.warning(f"Not in the NSE list, skipped: {', '.join(sorted(missing))}")
    else:
        chosen = universe
    return chosen[:limit] if limit else chosen


def chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]
