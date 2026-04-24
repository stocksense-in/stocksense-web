"""
fetch_fundamentals.py
=====================
Fetches fundamental data (PE, ROE, D/E, margin) from yfinance for ALL
NSE-listed equity stocks and upserts into Supabase `stocks` table.

Optimizations vs. original:
  - Concurrent fetching via ThreadPoolExecutor (default 16 workers)
  - Bulk DB upsert per batch instead of one call per stock
  - Removed sequential sleep

Usage:
    python fetch_fundamentals.py               # all NSE stocks
    python fetch_fundamentals.py --limit 30    # test run
    python fetch_fundamentals.py --symbols INFY TCS
    python fetch_fundamentals.py --workers 16  # tune concurrency
"""

import os
import argparse
import math
import concurrent.futures
from pathlib import Path

import yfinance as yf
from supabase import create_client
from dotenv import load_dotenv

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
            os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY", ""))),
)

# ── Sector map ────────────────────────────────────────────────────────────────
YF_SECTOR_MAP = {
    "technology":             "it",
    "communication services": "it",
    "financial services":     "bank",
    "healthcare":             "pharma",
    "consumer cyclical":      "auto",
    "consumer defensive":     "fmcg",
    "basic materials":        "materials",
    "industrials":            "industrial",
    "energy":                 "energy",
    "real estate":            "realestate",
    "utilities":              "utilities",
}

BANK_SECTORS   = {"bank", "nbfc"}
NEWAGE_SECTORS = {"newage"}


def _cap(v: float) -> float:
    return max(0.0, min(100.0, v))


def score_stock(pe, roe, de, margin, promoter, cagr, sector: str) -> int:
    if sector in NEWAGE_SECTORS:
        pe_score = 40.0
    elif sector in BANK_SECTORS:
        pe_score = _cap(100 - (pe - 8) / 30 * 100) if pe else 50.0
    else:
        pe_score = _cap(100 - (pe - 8) / 42 * 100) if pe else 50.0

    roe_score      = _cap(roe / 50 * 100)       if roe      else 0.0
    de_score       = _cap(100 - (de / 3.5)*100) if de       else 80.0
    margin_score   = _cap(margin / 38 * 100)    if margin   else 0.0
    promoter_score = _cap(promoter / 80 * 100)  if promoter else 50.0
    cagr_score     = _cap(cagr / 55 * 100)      if cagr     else 0.0

    return round(
        pe_score * 0.20 + roe_score * 0.20 + de_score * 0.15 +
        margin_score * 0.20 + promoter_score * 0.10 + cagr_score * 0.15
    )


def _safe(val, multiplier: float = 1.0, decimals: int = 1):
    if val is None:
        return None
    try:
        f = float(val) * multiplier
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def fetch_one(stock: dict) -> dict | None:
    sym       = stock["symbol"]
    yf_ticker = stock["yf"]
    name      = stock.get("name", sym)
    try:
        info = yf.Ticker(yf_ticker).info
        if not info or info.get("regularMarketPrice") is None:
            print(f"  SKIP {sym}: no market data", flush=True)
            return None

        pe     = _safe(info.get("trailingPE"))
        roe    = _safe(info.get("returnOnEquity"),  multiplier=100)
        de     = _safe(info.get("debtToEquity"))
        margin = _safe(info.get("profitMargins"),   multiplier=100)
        sector = YF_SECTOR_MAP.get((info.get("sector") or "").lower(), "general")
        score  = score_stock(pe, roe, de, margin, None, None, sector)

        row = {
            "symbol": sym, "name": name, "sector": sector,
            "pe_ratio": pe, "roe": roe, "debt_equity": de,
            "net_margin": margin, "composite_score": score,
        }
        row_clean = {k: v for k, v in row.items() if v is not None}
        row_clean["symbol"] = sym
        print(f"  OK   {sym}: PE={pe}, ROE={roe}%, Score={score}", flush=True)
        return row_clean
    except Exception as e:
        print(f"  ERROR {sym}: {e}", flush=True)
        return None


def run(
    symbols:         list[str] | None = None,
    limit:           int | None       = None,
    refresh_symbols: bool              = False,
    workers:         int               = 16,
    batch_size:      int               = 100,
) -> None:
    print("Loading NSE symbol list …", flush=True)
    all_nse = get_all_symbols(force_refresh=refresh_symbols)

    if symbols:
        sym_set = {s.upper() for s in symbols}
        target = [s for s in all_nse if s["symbol"] in sym_set]
    else:
        target = all_nse

    if limit:
        target = target[:limit]

    print(f"Fetching fundamentals for {len(target)} stocks "
          f"({workers} workers, batch_size={batch_size}) …\n", flush=True)
    ok = fail = 0

    for batch_start in range(0, len(target), batch_size):
        batch = target[batch_start : batch_start + batch_size]
        batch_num    = batch_start // batch_size + 1
        total_batches = (len(target) + batch_size - 1) // batch_size
        print(f"-- Batch {batch_num}/{total_batches} ({len(batch)} stocks) --", flush=True)

        upsert_rows: list[dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
            for row in exe.map(fetch_one, batch):
                if row:
                    upsert_rows.append(row)
                    ok += 1
                else:
                    fail += 1

        if upsert_rows:
            try:
                sb.table("stocks").upsert(upsert_rows).execute()
                print(f"  → Upserted {len(upsert_rows)} rows to Supabase", flush=True)
            except Exception as exc:
                print(f"  ERROR bulk upsert: {exc}", flush=True)

    print(f"\nDone — {ok} succeeded, {fail} failed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense fundamentals pipeline — optimized"
    )
    parser.add_argument("--symbols", nargs="*", metavar="SYM")
    parser.add_argument("--limit",      type=int,   default=None)
    parser.add_argument("--workers",    type=int,   default=16)
    parser.add_argument("--batch-size", type=int,   default=100)
    parser.add_argument("--refresh-symbols", action="store_true")
    args = parser.parse_args()
    run(
        symbols=args.symbols, limit=args.limit,
        refresh_symbols=args.refresh_symbols,
        workers=args.workers, batch_size=args.batch_size,
    )
