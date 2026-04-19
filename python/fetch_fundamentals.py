"""
fetch_fundamentals.py
=====================
Fetches fundamental data (PE, ROE, D/E, margin) from yfinance for ALL
NSE-listed equity stocks and upserts into Supabase `stocks` table.

The full NSE symbol list is loaded dynamically from nse_symbols.py.

Usage:
    python fetch_fundamentals.py               # all NSE stocks
    python fetch_fundamentals.py --limit 30    # test run
    python fetch_fundamentals.py --symbols INFY TCS
"""

import os
import time
import argparse
import math
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

# ── Sector → scoring category map ─────────────────────────────────────────────
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


# ── Scoring ───────────────────────────────────────────────────────────────────

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

    composite = (
        pe_score       * 0.20 +
        roe_score      * 0.20 +
        de_score       * 0.15 +
        margin_score   * 0.20 +
        promoter_score * 0.10 +
        cagr_score     * 0.15
    )
    return round(composite)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(val, multiplier: float = 1.0, decimals: int = 1):
    """Convert yfinance field to a clean float, or None on NaN/missing."""
    if val is None:
        return None
    try:
        f = float(val) * multiplier
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    symbols:         list[str] | None = None,
    limit:           int | None       = None,
    refresh_symbols: bool              = False,
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

    print(f"Fetching fundamentals for {len(target)} stocks …\n", flush=True)
    ok = fail = 0

    for stock in target:
        sym       = stock["symbol"]
        yf_ticker = stock["yf"]
        name      = stock.get("name", sym)
        print(f"Fetching {sym} ({yf_ticker}) …", flush=True)

        try:
            ticker = yf.Ticker(yf_ticker)
            info   = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                print(f"  SKIP {sym}: no market data", flush=True)
                fail += 1
                continue

            pe     = _safe(info.get("trailingPE"))
            roe    = _safe(info.get("returnOnEquity"),    multiplier=100, decimals=1)
            de     = _safe(info.get("debtToEquity"))
            margin = _safe(info.get("profitMargins"),     multiplier=100, decimals=1)

            # Sector from yfinance
            yf_sec = (info.get("sector") or "").lower()
            sector = YF_SECTOR_MAP.get(yf_sec, "general")

            # Promoter + CAGR not reliably available from yfinance — fetch_nse.py fills these
            promoter = None
            cagr     = None

            score = score_stock(pe, roe, de, margin, promoter, cagr, sector)

            row = {
                "symbol":           sym,
                "name":             name,
                "sector":           sector,
                "pe_ratio":         pe,
                "roe":              roe,
                "debt_equity":      de,
                "net_margin":       margin,
                "promoter_holding": promoter,
                "revenue_cagr_3yr": cagr,
                "composite_score":  score,
            }
            # Remove None values to avoid overwriting existing data
            row_clean = {k: v for k, v in row.items() if v is not None}
            row_clean["symbol"] = sym

            sb.table("stocks").upsert(row_clean).execute()
            print(f"  OK   {sym}: PE={pe}, ROE={roe}%, Score={score}", flush=True)
            ok += 1

        except Exception as e:
            print(f"  ERROR {sym}: {e}", flush=True)
            fail += 1

        time.sleep(0.3)   # polite rate-limiting

    print(f"\nDone — {ok} succeeded, {fail} failed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense fundamentals pipeline — all NSE stocks"
    )
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="Specific NSE symbols (default: all NSE equities)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Only process first N stocks (for testing)",
    )
    parser.add_argument(
        "--refresh-symbols", action="store_true",
        help="Force re-download of NSE equity list",
    )
    args = parser.parse_args()
    run(symbols=args.symbols, limit=args.limit, refresh_symbols=args.refresh_symbols)
