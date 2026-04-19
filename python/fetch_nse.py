"""
fetch_nse.py
============
Fetches promoter holding & revenue CAGR for ALL NSE-listed equity stocks.

Strategy per stock (in order of preference):
  1. yfinance  — heldPercentInsiders / financials
  2. Screener.in — plain HTTP scrape (no new deps)
  3. Hardcoded fallback map — for well-known large-caps

Upserts results into Supabase `stocks` table.

Usage:
    python fetch_nse.py                    # all NSE stocks
    python fetch_nse.py --symbols INFY TCS # specific symbols only
    python fetch_nse.py --limit 50         # test run
    python fetch_nse.py --refresh-symbols  # force NSE list re-download
"""

import os
import sys
import math
import time
import json
import re
import argparse
import concurrent.futures
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from dotenv import load_dotenv
from supabase import create_client

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from nse_symbols import get_all_symbols


# ── Load .env ─────────────────────────────────────────────────────────────────
def _load_env():
    search = Path(__file__).resolve().parent
    for _ in range(5):
        for env_file in (".env.local", ".env"):
            candidate = search / env_file
            if candidate.exists():
                load_dotenv(candidate, override=True)
                print(f"[env] Loaded: {candidate}", flush=True)
                return
        search = search.parent
    load_dotenv()

_load_env()

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase env vars missing. "
        "Check .env.local has NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_SERVICE_KEY."
    )

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Hardcoded fallback map for well-known large-caps ─────────────────────────
# promoter_holding: publicly known values (% as of Q3 FY25)
# cagr:             3-yr revenue CAGR approximate (%)
FALLBACKS: dict[str, dict] = {
    "INFY":       {"promoter": 14.76, "cagr": 9.8},
    "HDFCBANK":   {"promoter": 0.0,   "cagr": 16.2},
    "TATAMOTORS": {"promoter": 42.58, "cagr": 28.4},
    "ZOMATO":     {"promoter": 0.0,   "cagr": 68.5},
    "TCS":        {"promoter": 72.30, "cagr": 11.2},
    "BAJFINANCE": {"promoter": 55.93, "cagr": 28.6},
    "SUNPHARMA":  {"promoter": 54.48, "cagr": 14.3},
    "MTAR":       {"promoter": 56.47, "cagr": 35.2},
    "DIVISLAB":   {"promoter": 51.94, "cagr": 9.5},
    "KALYANKJIL": {"promoter": 60.57, "cagr": 22.8},
    "RELIANCE":   {"promoter": 50.33, "cagr": 7.6},
    "WIPRO":      {"promoter": 72.93, "cagr": 7.3},
    "HCLTECH":    {"promoter": 60.31, "cagr": 12.5},
    "AXISBANK":   {"promoter": 8.22,  "cagr": 20.1},
    "KOTAKBANK":  {"promoter": 26.12, "cagr": 18.7},
    "ICICIBANK":  {"promoter": 0.0,   "cagr": 22.4},
    "SBIN":       {"promoter": 57.54, "cagr": 15.8},
    "MARUTI":     {"promoter": 58.19, "cagr": 18.6},
    "TITAN":      {"promoter": 52.90, "cagr": 24.1},
    "NESTLEIND":  {"promoter": 62.76, "cagr": 13.2},
    "ASIANPAINT": {"promoter": 52.63, "cagr": 8.9},
    "LTIM":       {"promoter": 68.73, "cagr": 21.5},
    "TECHM":      {"promoter": 35.14, "cagr": 8.4},
    "M&M":        {"promoter": 18.97, "cagr": 25.3},
    "POWERGRID":  {"promoter": 51.34, "cagr": 9.3},
    "NTPC":       {"promoter": 51.10, "cagr": 18.2},
    "ONGC":       {"promoter": 58.89, "cagr": 9.1},
    "COALINDIA":  {"promoter": 63.13, "cagr": 11.4},
    "BHARTIARTL": {"promoter": 55.61, "cagr": 19.8},
    "JSWSTEEL":   {"promoter": 44.84, "cagr": 16.3},
    "TATASTEEL":  {"promoter": 33.05, "cagr": 12.7},
    "HINDALCO":   {"promoter": 34.64, "cagr": 14.5},
    "ADANIENT":   {"promoter": 72.61, "cagr": 28.9},
    "ADANIPORTS": {"promoter": 65.87, "cagr": 21.6},
    "ULTRACEMCO": {"promoter": 56.32, "cagr": 9.2},
    "GRASIM":     {"promoter": 43.22, "cagr": 16.7},
    "HEROMOTOCO": {"promoter": 34.75, "cagr": 8.6},
    "BAJAJFINSV": {"promoter": 55.93, "cagr": 22.1},
    "DRREDDY":    {"promoter": 26.66, "cagr": 11.8},
    "CIPLA":      {"promoter": 33.47, "cagr": 10.4},
    "APOLLOHOSP": {"promoter": 29.32, "cagr": 19.5},
    "BPCL":       {"promoter": 52.98, "cagr": 8.7},
    "INDUSINDBK": {"promoter": 16.38, "cagr": 17.9},
    "EICHERMOT":  {"promoter": 49.24, "cagr": 20.8},
    "TATACONSUM": {"promoter": 34.71, "cagr": 12.3},
    "BRITANNIA":  {"promoter": 50.55, "cagr": 9.8},
}

TIMEOUT = 15


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def run_with_timeout(fn, label: str, timeout: int = TIMEOUT):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"    [TIMEOUT] {label}", flush=True)
            return None
        except Exception as e:
            print(f"    [FAIL] {label}: {e}", flush=True)
            return None


# ── Source 1: yfinance ────────────────────────────────────────────────────────

def yf_promoter(yahoo_sym: str) -> float | None:
    if not HAS_YFINANCE:
        return None
    info = yf.Ticker(yahoo_sym).info
    raw = info.get("heldPercentInsiders")
    val = safe_float(raw)
    return round(val * 100, 2) if val is not None else None


def yf_cagr(yahoo_sym: str) -> float | None:
    if not HAS_YFINANCE:
        return None
    fin = yf.Ticker(yahoo_sym).financials
    if fin is None or fin.empty:
        return None
    for label in ("Total Revenue", "Revenue"):
        if label in fin.index:
            revenues = [safe_float(v) for v in fin.loc[label].dropna().values]
            revenues = [v for v in revenues if v is not None]
            if len(revenues) >= 2:
                years = len(revenues) - 1
                return round(((revenues[0] / revenues[-1]) ** (1 / years) - 1) * 100, 1)
    return None


# ── Source 2: Screener.in ─────────────────────────────────────────────────────

_SCREENER_SESSION = None

def _screener_session() -> requests.Session:
    global _SCREENER_SESSION
    if _SCREENER_SESSION:
        return _SCREENER_SESSION
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    _SCREENER_SESSION = s
    return s


def screener_promoter(screener_sym: str) -> float | None:
    url = f"https://www.screener.in/company/{screener_sym}/consolidated/"
    try:
        resp = _screener_session().get(url, timeout=TIMEOUT)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    match = re.search(
        r'Promoters[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*%',
        resp.text
    )
    if match:
        return round(float(match.group(1)), 2)
    match = re.search(r'"promoter[^"]*"[^>]*>([\d.]+)%', resp.text, re.IGNORECASE)
    if match:
        return round(float(match.group(1)), 2)
    return None


def screener_cagr(screener_sym: str) -> float | None:
    url = f"https://www.screener.in/company/{screener_sym}/consolidated/"
    try:
        resp = _screener_session().get(url, timeout=TIMEOUT)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    match = re.search(
        r'Sales\s+CAGR[^<]*<[^>]+>\s*([\d.]+)%',
        resp.text, re.IGNORECASE
    )
    if match:
        return round(float(match.group(1)), 1)
    return None


# ── Fetch with fallback chain ─────────────────────────────────────────────────

def fetch_data(symbol: str, yf_ticker: str) -> tuple[float | None, float | None]:
    fb = FALLBACKS.get(symbol, {})

    # --- Promoter ---
    promoter = run_with_timeout(lambda: yf_promoter(yf_ticker), f"yf_promoter/{symbol}")

    if promoter is None:
        promoter = run_with_timeout(lambda: screener_promoter(symbol), f"screener_promoter/{symbol}")

    if promoter is None and fb.get("promoter") is not None:
        promoter = fb["promoter"]
        print(f"  Using fallback promoter: {promoter}%", flush=True)

    # --- Revenue CAGR ---
    cagr = run_with_timeout(lambda: yf_cagr(yf_ticker), f"yf_cagr/{symbol}")

    if cagr is None:
        cagr = run_with_timeout(lambda: screener_cagr(symbol), f"screener_cagr/{symbol}")

    if cagr is None and fb.get("cagr") is not None:
        cagr = fb["cagr"]
        print(f"  Using fallback CAGR: {cagr}%", flush=True)

    return promoter, cagr


# ── Main ──────────────────────────────────────────────────────────────────────

def run(symbols: list[str] | None = None,
        limit: int | None = None,
        refresh_symbols: bool = False) -> None:

    print("Loading NSE symbol list …", flush=True)
    all_nse = get_all_symbols(force_refresh=refresh_symbols)

    if symbols:
        sym_set = {s.upper() for s in symbols}
        target = [s for s in all_nse if s["symbol"] in sym_set]
    else:
        target = all_nse

    if limit:
        target = target[:limit]

    print(f"Fetching NSE fundamentals for {len(target)} stocks …\n", flush=True)

    for stock in target:
        sym       = stock["symbol"]
        yf_ticker = stock["yf"]
        print(f"--- {sym} ---", flush=True)

        promoter, cagr = fetch_data(sym, yf_ticker)

        print(f"  Promoter holding : {promoter}%", flush=True)
        print(f"  Revenue CAGR     : {cagr}%", flush=True)

        update_row = {"symbol": sym}
        if promoter is not None:
            update_row["promoter_holding"] = promoter
        if cagr is not None:
            update_row["revenue_cagr_3yr"] = cagr

        if len(update_row) > 1:
            try:
                sb.table("stocks").upsert(update_row, on_conflict="symbol").execute()
                print(f"  [OK] Supabase updated", flush=True)
            except Exception as e:
                print(f"  [FAIL] Supabase: {e}", flush=True)
        else:
            print(f"  [SKIP] No data to store", flush=True)

        print(flush=True)
        time.sleep(0.5)   # polite rate-limiting

    print("Done.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StockSense NSE fundamentals pipeline")
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="Specific NSE symbols (default: all NSE equities)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Only process the first N stocks (for testing)",
    )
    parser.add_argument(
        "--refresh-symbols", action="store_true",
        help="Force re-download of NSE equity list",
    )
    args = parser.parse_args()
    run(symbols=args.symbols, limit=args.limit, refresh_symbols=args.refresh_symbols)