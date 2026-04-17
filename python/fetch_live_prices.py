# -*- coding: utf-8 -*-
"""
fetch_live_prices.py
Fetches live/latest prices from yfinance and upserts into Supabase `live_prices` table.

Fixes applied:
  - NaN / Infinity values from yfinance are sanitized before sending to Supabase.
  - ZOMATO.NS renamed to ETERNAL.NS (Zomato rebranded to Eternal Limited in 2025).
  - TATAMOTORS.NS temporarily broken on Yahoo Finance; uses a 5-day window + last
    valid row fallback to recover the most recent real price.
  - Skips any symbol that still has no usable data rather than crashing.
"""

import math
import os

import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client

# ── env / supabase ────────────────────────────────────────────────────────────
load_dotenv()
sb = create_client(
    os.getenv("SUPABASE_URL", os.getenv("NEXT_PUBLIC_SUPABASE_URL")),
    os.getenv("SUPABASE_KEY", os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY",
              os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY"))),
)

# ── symbol map ────────────────────────────────────────────────────────────────
# (display_name, yahoo_ticker)
# ZOMATO.NS → ETERNAL.NS  : Zomato Ltd rebranded to Eternal Limited (Mar 2025)
# TATAMOTORS.NS            : Yahoo Finance 404s on this ticker; we try a wider
#                            history window and take the last non-NaN close.
SYMBOLS = [
    ("NIFTY50",    "^NSEI"),
    ("SENSEX",     "^BSESN"),
    ("INFY",       "INFY.NS"),
    ("HDFCBANK",   "HDFCBANK.NS"),
    ("TATAMOTORS", "TATAMOTORS.NS"),
    ("ZOMATO",     "ETERNAL.NS"),      # rebranded ticker
    ("RELIANCE",   "RELIANCE.NS"),
]


# ── helpers ───────────────────────────────────────────────────────────────────
def safe_float(value) -> float | None:
    """Return a JSON-safe float, or None for NaN / Infinity / None."""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_history(yahoo_sym: str, days: int = 5):
    """
    Fetch up to `days` days of daily history.
    Returns a DataFrame (may be empty).
    """
    ticker = yf.Ticker(yahoo_sym)
    return ticker.history(period=f"{days}d")


def last_valid_close(hist, col: str = "Close"):
    """
    Walk backwards through a history DataFrame and return the first non-NaN
    value in `col`, or None if every row is NaN / the frame is empty.
    """
    series = hist[col].dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


# ── main loop ─────────────────────────────────────────────────────────────────
for symbol, yahoo_sym in SYMBOLS:
    try:
        # Use 5-day window so we have a fallback when the latest row is NaN
        hist = fetch_history(yahoo_sym, days=5)

        if hist.empty:
            print(f"  SKIP  {symbol}: no data returned by Yahoo Finance")
            continue

        price_raw = last_valid_close(hist, "Close")
        if price_raw is None:
            print(f"  SKIP  {symbol}: all close values are NaN")
            continue

        price = round(price_raw, 2)

        # For change_pct we need at least two rows with valid data
        valid_closes = hist["Close"].dropna()
        if len(valid_closes) >= 2:
            prev = float(valid_closes.iloc[-2])
            change_pct = round((price_raw - prev) / prev * 100, 2)
        else:
            change_pct = 0.0

        # Final NaN / Inf guard before hitting Supabase
        price      = safe_float(price)
        change_pct = safe_float(change_pct) or 0.0

        if price is None:
            print(f"  SKIP  {symbol}: price resolved to NaN/Inf after sanitization")
            continue

        sb.table("live_prices").upsert({
            "symbol":     symbol,
            "price":      price,
            "change_pct": change_pct,
        }).execute()

        sign = "+" if change_pct >= 0 else ""
        print(f"  OK    {symbol}: INR {price} ({sign}{change_pct:.2f}%)")

    except Exception as exc:
        print(f"  ERROR {symbol}: {exc}")

print("\nDone. All prices updated.")