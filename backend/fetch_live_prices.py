# -*- coding: utf-8 -*-
"""
fetch_live_prices.py
====================
Fetches live/latest prices from yfinance for ALL NSE-listed equity stocks
plus the major indices (NIFTY50, SENSEX) and upserts into the Supabase
`live_prices` table.

Optimizations vs. original:
  - Uses yf.download() for batch fetching (1 request per chunk, not N)
  - Accumulates results and upserts to DB in bulk (1 DB call per batch)
  - Removed unnecessary inter-batch sleep

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
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows
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


def bulk_upsert(rows: list[dict]) -> None:
    """Upsert a list of price rows in a single Supabase call."""
    if not rows:
        return
    sb.table("live_prices").upsert(rows).execute()


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    symbols:         list[str] | None = None,
    limit:           int | None       = None,
    batch_size:      int               = 200,   # larger batches = fewer yf.download calls
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
        print(f"-- Batch {batch_num}/{total_batches} ({len(batch)} symbols) --", flush=True)

        # Map yahoo_sym -> nse_sym for lookup after download
        yf_to_nse: dict[str, str] = {yahoo: sym for sym, yahoo in batch}
        yahoo_tickers = list(yf_to_nse.keys())

        # ── Single yf.download() call for the whole batch ──────────────────
        try:
            raw = yf.download(
                tickers=yahoo_tickers,
                period="5d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,       # yfinance internal threading
            )
        except Exception as exc:
            print(f"  ERROR downloading batch: {exc}")
            fail_count += len(batch)
            continue

        # ── Parse results & accumulate rows ───────────────────────────────
        upsert_rows: list[dict] = []

        for yahoo_sym, nse_sym in yf_to_nse.items():
            try:
                # With group_by="ticker", multi-ticker download uses MultiIndex columns
                if len(yahoo_tickers) == 1:
                    closes = raw["Close"].dropna() if "Close" in raw.columns else None
                else:
                    closes = raw[yahoo_sym]["Close"].dropna() if yahoo_sym in raw.columns.get_level_values(0) else None

                if closes is None or len(closes) == 0:
                    print(f"  SKIP  {nse_sym}: no data")
                    fail_count += 1
                    continue

                price_raw = float(closes.iloc[-1])
                price = safe_float(round(price_raw, 2))
                if price is None:
                    fail_count += 1
                    continue

                change_pct = 0.0
                if len(closes) >= 2:
                    prev = float(closes.iloc[-2])
                    change_pct = safe_float(round((price_raw - prev) / prev * 100, 2)) or 0.0

                sign = "+" if change_pct >= 0 else ""
                print(f"  OK    {nse_sym:<14s} ₹{price:>10.2f}  ({sign}{change_pct:.2f}%)")
                upsert_rows.append({
                    "symbol":     nse_sym,
                    "price":      price,
                    "change_pct": change_pct,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                ok_count += 1

            except Exception as exc:
                print(f"  ERROR {nse_sym}: {exc}")
                fail_count += 1

        # ── Single bulk DB upsert for the entire batch ─────────────────────
        if upsert_rows:
            try:
                bulk_upsert(upsert_rows)
                print(f"  → Upserted {len(upsert_rows)} rows to Supabase", flush=True)
            except Exception as exc:
                print(f"  ERROR bulk upsert: {exc}")
                fail_count += len(upsert_rows)
                ok_count   -= len(upsert_rows)

    print(f"\nDone — {ok_count} updated, {fail_count} skipped/failed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense live price pipeline — all NSE stocks (optimized)"
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
        "--batch-size", type=int, default=200, metavar="N",
        help="Symbols per yf.download() batch (default: 200)",
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
        refresh_symbols=args.refresh_symbols,
    )