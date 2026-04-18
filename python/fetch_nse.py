"""
fetch_nse.py
Fetches promoter holding & revenue CAGR.
Strategy (in order of preference):
  1. Try yfinance with a short timeout
  2. Fall back to Screener.in page scrape (plain requests, no new deps)
  3. Fall back to hardcoded well-known values (updated Apr 2025)
Upserts results into Supabase `stocks` table.
"""

import os
import sys
import math
import time
import json
import re
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


# ── Load .env.local / .env ────────────────────────────────────────────────────
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

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase env vars missing. "
        "Check .env.local has NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_SERVICE_KEY."
    )

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Stock definitions ─────────────────────────────────────────────────────────
# fallback_promoter: publicly known promoter holdings (% as of Q3 FY25)
# fallback_cagr:     3-yr revenue CAGR approximate (%)
STOCKS = [
    {"symbol": "INFY",       "yahoo": "INFY.NS",       "screener": "INFY",       "fallback_promoter": 14.76, "fallback_cagr": 9.8},
    {"symbol": "HDFCBANK",   "yahoo": "HDFCBANK.NS",   "screener": "HDFCBANK",   "fallback_promoter": 0.0,  "fallback_cagr": 16.2},
    {"symbol": "TATAMOTORS", "yahoo": "TATAMOTORS.NS", "screener": "TATAMOTORS", "fallback_promoter": 42.58, "fallback_cagr": 28.4},
    {"symbol": "ZOMATO",     "yahoo": "ETERNAL.NS",    "screener": "ZOMATO",     "fallback_promoter": 0.0,  "fallback_cagr": 68.5},
    {"symbol": "RELIANCE",   "yahoo": "RELIANCE.NS",   "screener": "RELIANCE",   "fallback_promoter": 50.33, "fallback_cagr": 7.6},
]

TIMEOUT = 15   # seconds per network call


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


# ── Source 2: Screener.in (plain HTTP, no extra deps) ─────────────────────────
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
    """Scrape promoter holding % from Screener.in company page."""
    url = f"https://www.screener.in/company/{screener_sym}/consolidated/"
    resp = _screener_session().get(url, timeout=TIMEOUT)
    if resp.status_code != 200:
        return None
    # Look for "Promoters" in the shareholding section
    match = re.search(
        r'Promoters[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*%',
        resp.text
    )
    if match:
        return round(float(match.group(1)), 2)
    # Alternative pattern
    match = re.search(r'"promoter[^"]*"[^>]*>([\d.]+)%', resp.text, re.IGNORECASE)
    if match:
        return round(float(match.group(1)), 2)
    return None


def screener_cagr(screener_sym: str) -> float | None:
    """Get revenue CAGR from Screener.in company ratios page."""
    url = f"https://www.screener.in/company/{screener_sym}/consolidated/"
    resp = _screener_session().get(url, timeout=TIMEOUT)
    if resp.status_code != 200:
        return None
    # Look for Sales/Revenue CAGR pattern in key metrics table
    match = re.search(
        r'Sales\s+CAGR[^<]*<[^>]+>\s*([\d.]+)%',
        resp.text, re.IGNORECASE
    )
    if match:
        return round(float(match.group(1)), 1)
    return None


# ── Main fetch with fallback chain ────────────────────────────────────────────
def fetch_data(stock: dict) -> tuple[float | None, float | None]:
    sym      = stock["symbol"]
    yahoo    = stock["yahoo"]
    screener = stock["screener"]

    # --- Promoter ---
    print(f"  Trying yfinance for promoter...", flush=True)
    promoter = run_with_timeout(lambda: yf_promoter(yahoo), f"yf_promoter/{sym}")

    if promoter is None:
        print(f"  Trying Screener.in for promoter...", flush=True)
        promoter = run_with_timeout(lambda: screener_promoter(screener), f"screener_promoter/{sym}")

    if promoter is None:
        promoter = stock["fallback_promoter"]
        if promoter is not None:
            print(f"  Using fallback promoter: {promoter}%", flush=True)

    # --- Revenue CAGR ---
    print(f"  Trying yfinance for CAGR...", flush=True)
    cagr = run_with_timeout(lambda: yf_cagr(yahoo), f"yf_cagr/{sym}")

    if cagr is None:
        print(f"  Trying Screener.in for CAGR...", flush=True)
        cagr = run_with_timeout(lambda: screener_cagr(screener), f"screener_cagr/{sym}")

    if cagr is None:
        cagr = stock["fallback_cagr"]
        if cagr is not None:
            print(f"  Using fallback CAGR: {cagr}%", flush=True)

    return promoter, cagr


# ── Main ──────────────────────────────────────────────────────────────────────
print("Fetching NSE fundamentals...\n", flush=True)

for stock in STOCKS:
    sym = stock["symbol"]
    print(f"--- {sym} ---", flush=True)

    promoter, cagr = fetch_data(stock)

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
        print(f"  [SKIP] No data", flush=True)

    print(flush=True)
    time.sleep(1)

print("Done.", flush=True)