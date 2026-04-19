"""
nse_symbols.py
==============
Fetches the complete list of NSE-listed equity stocks from NSE's official
EQUITY_L.csv endpoint. Results are cached locally for 24 hours so repeated
script runs don't re-download 2000+ rows every time.

Usage (from any other script):
    from nse_symbols import get_all_symbols

    symbols = get_all_symbols()
    # [{"symbol": "INFY", "name": "Infosys Ltd", "yf": "INFY.NS", "series": "EQ"}, ...]

Force a refresh:
    symbols = get_all_symbols(force_refresh=True)
"""

import csv
import io
import json
import time
from pathlib import Path

import requests

# ── Constants ─────────────────────────────────────────────────────────────────

# NSE's official equity list — updated every trading day
NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

# Cache file lives alongside this module
CACHE_FILE = Path(__file__).resolve().parent / "_nse_symbols_cache.json"

# Refresh cache after 24 hours
CACHE_TTL_SECONDS = 86_400

# Series to include — "EQ" = normal equity, "BE" = book-entry (T+2 restricted)
# Keeping both gives maximum coverage; filter downstream if needed.
INCLUDE_SERIES = {"EQ", "BE", "BZ", "SM", "ST"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _cache_is_fresh() -> bool:
    if not CACHE_FILE.exists():
        return False
    age = time.time() - CACHE_FILE.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def _load_cache() -> list[dict]:
    with open(CACHE_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _save_cache(data: list[dict]) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)


def _fetch_from_nse() -> list[dict]:
    """Download EQUITY_L.csv from NSE and parse into a list of dicts."""
    print("  Downloading NSE equity list from archives.nseindia.com …", flush=True)
    try:
        resp = requests.get(NSE_EQUITY_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download NSE equity list: {exc}") from exc

    # NSE CSV columns (as of 2025):
    # SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,
    # MARKET LOT, ISIN NUMBER, FACE VALUE
    stocks: list[dict] = []
    reader = csv.DictReader(io.StringIO(resp.text))

    for row in reader:
        # Strip whitespace from all keys and values — NSE CSVs can have leading spaces
        row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

        symbol = row.get("SYMBOL", "")
        name   = row.get("NAME OF COMPANY", "")
        series = row.get("SERIES", "")
        isin   = row.get("ISIN NUMBER", "")

        if not symbol or series not in INCLUDE_SERIES:
            continue

        stocks.append({
            "symbol": symbol,
            "name":   name,
            "series": series,
            "isin":   isin,
            # yfinance requires the .NS suffix for NSE stocks
            "yf":     f"{symbol}.NS",
            # sector is unknown until yfinance is queried — filled in downstream
            "sector": "general",
        })

    return stocks


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_symbols(force_refresh: bool = False) -> list[dict]:
    """
    Return every NSE equity stock as a list of dicts.

    Each dict has:
        symbol  – NSE trading symbol  (e.g. "INFY")
        name    – Company name        (e.g. "Infosys Limited")
        series  – NSE series          (e.g. "EQ")
        isin    – ISIN code           (e.g. "INE009A01021")
        yf      – yfinance ticker     (e.g. "INFY.NS")
        sector  – "general" by default; overwritten by yfinance fetch

    Results are cached locally for 24 hours.
    Pass force_refresh=True to bypass the cache.
    """
    if not force_refresh and _cache_is_fresh():
        print(f"  Using cached NSE symbol list ({CACHE_FILE.name})", flush=True)
        return _load_cache()

    stocks = _fetch_from_nse()
    _save_cache(stocks)
    print(f"  Fetched {len(stocks)} NSE equity stocks.", flush=True)
    return stocks


def get_symbols_chunked(chunk_size: int = 100, force_refresh: bool = False):
    """
    Generator — yields symbols in chunks of `chunk_size`.
    Useful for batch-processing 2000+ stocks without loading everything at once.

    Example:
        for batch in get_symbols_chunked(50):
            process(batch)
    """
    all_syms = get_all_symbols(force_refresh=force_refresh)
    for i in range(0, len(all_syms), chunk_size):
        yield all_syms[i : i + chunk_size]


if __name__ == "__main__":
    syms = get_all_symbols(force_refresh=True)
    print(f"\nTotal NSE equity stocks fetched: {len(syms)}")
    print("First 10:", [s["symbol"] for s in syms[:10]])
    print("Last  10:", [s["symbol"] for s in syms[-10:]])
