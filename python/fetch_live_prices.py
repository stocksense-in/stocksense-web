# -*- coding: utf-8 -*-
"""
fetch_live_prices.py
====================
Fetches live/latest prices from yfinance for ALL NSE-listed equity stocks
plus the major indices (NIFTY50, SENSEX) and upserts into the Supabase
`live_prices` table.

The full NSE symbol list is loaded dynamically from nse_symbols.py
(which caches NSE's EQUITY_L.csv for 24 hours).

Usage:
    python fetch_live_prices.py                     # all NSE stocks
    python fetch_live_prices.py --limit 50          # test run
    python fetch_live_prices.py --symbols INFY TCS  # specific symbols
    python fetch_live_prices.py --refresh-symbols   # force NSE list refresh
    python fetch_live_prices.py --workers 8         # more concurrency
"""

import math
import os
import sys
import time
import argparse
import concurrent.futures
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client

from nse_symbols import get_all_symbols

# ── Env / Supabase ────────────────────────────────────────────────────────────

def _load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(4):
        for name in (".env.local", ".env"):
            candidate = search / name
            if candidate.exists():
                load_dotenv(candidate, override=True)
                return
        search = search.parent
    load_dotenv()

_load_env()

sb = create_client(
    os.getenv("SUPABASE_URL", os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")),
    os.getenv("SUPABASE_KEY",
        os.getenv("SUPABASE_SERVICE_KEY",
            os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY",
                os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")))),
)

# ── Index symbols (always included — not in EQUITY_L.csv) ─────────────────────
INDEX_SYMBOLS = [
    ("NIFTY50", "^NSEI"),
    ("SENSEX",  "^BSESN"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_float(value) -> float | None:
    """Return a JSON-safe float, or None for NaN / Infinity / None."""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_price(symbol: str, yahoo_sym: str) -> tuple[str, float | None, float | None]:
    """
    Fetch latest close + change % for a single ticker.
    Returns (symbol, price, change_pct) — any value can be None on failure.
    """
    try:
        ticker = yf.Ticker(yahoo_sym)
        hist = ticker.history(period="5d")

        if hist.empty:
            return symbol, None, None

        valid_closes = hist["Close"].dropna()
        if valid_closes.empty:
            return symbol, None, None

        price_raw = float(valid_closes.iloc[-1])
        price = safe_float(round(price_raw, 2))

        if len(valid_closes) >= 2:
            prev = float(valid_closes.iloc[-2])
            change_pct = safe_float(round((price_raw - prev) / prev * 100, 2)) or 0.0
        else:
            change_pct = 0.0

        return symbol, price, change_pct

    except Exception as exc:
        print(f"  ERROR {symbol} ({yahoo_sym}): {exc}")
        return symbol, None, None


def upsert_price(symbol: str, price: float, change_pct: float) -> None:
    sb.table("live_prices").upsert({
        "symbol":     symbol,
        "price":      price,
        "change_pct": change_pct,
    }).execute()


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    symbols:         list[str] | None = None,
    limit:           int | None       = None,
    batch_size:      int               = 50,
    workers:         int               = 8,
    delay_between:   float             = 0.2,
    refresh_symbols: bool              = False,
) -> None:
    # Always include indices
    all_targets: list[tuple[str, str]] = list(INDEX_SYMBOLS)

    # Load all NSE equities
    print("Loading NSE symbol list …", flush=True)
    all_nse = get_all_symbols(force_refresh=refresh_symbols)

    if symbols:
        sym_set = {s.upper() for s in symbols}
        nse_targets = [(s["symbol"], s["yf"]) for s in all_nse if s["symbol"] in sym_set]
    else:
        nse_targets = [(s["symbol"], s["yf"]) for s in all_nse]

    if limit:
        nse_targets = nse_targets[:limit]

    all_targets.extend(nse_targets)
    print(f"Fetching prices for {len(all_targets)} symbols "
          f"(including {len(INDEX_SYMBOLS)} indices) …\n", flush=True)

    ok_count = fail_count = 0

    for batch_start in range(0, len(all_targets), batch_size):
        batch = all_targets[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(all_targets) + batch_size - 1) // batch_size
        print(f"-- Batch {batch_num}/{total_batches} --", flush=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
            futures = {exe.submit(fetch_price, sym, yahoo): (sym, yahoo) for sym, yahoo in batch}

            for future in concurrent.futures.as_completed(futures):
                sym, price, change_pct = future.result()

                if price is None:
                    print(f"  SKIP  {sym}: no usable price data")
                    fail_count += 1
                    continue

                try:
                    upsert_price(sym, price, change_pct or 0.0)
                    sign = "+" if (change_pct or 0) >= 0 else ""
                    print(f"  OK    {sym:<14s} ₹{price:>10.2f}  ({sign}{change_pct:.2f}%)")
                    ok_count += 1
                except Exception as exc:
                    print(f"  ERROR {sym}: Supabase upsert failed — {exc}")
                    fail_count += 1

        if batch_start + batch_size < len(all_targets):
            time.sleep(delay_between)

    print(f"\nDone — {ok_count} updated, {fail_count} skipped/failed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense live price pipeline — all NSE stocks"
    )
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="Specific NSE symbols (default: all NSE equities)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Only process first N equity stocks (testing)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, metavar="N",
        help="Symbols per batch (default: 50)",
    )
    parser.add_argument(
        "--workers", type=int, default=8, metavar="N",
        help="Concurrent yfinance threads per batch (default: 8)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.2, metavar="SEC",
        help="Sleep between batches in seconds (default: 0.2)",
    )
    parser.add_argument(
        "--refresh-symbols", action="store_true",
        help="Force re-download of NSE equity list",
    )
    args = parser.parse_args()

    run(
        symbols=args.symbols,
        limit=args.limit,
        batch_size=args.batch_size,
        workers=args.workers,
        delay_between=args.delay,
        refresh_symbols=args.refresh_symbols,
    )