"""
Snapshot job — copies a curated set of stocks from Supabase into
frontend/data/snapshot.json, the file the website uses when it has no database.

    python -m stocksense snapshot                 # the default ~70 large caps
    python -m stocksense snapshot --symbols INFY TCS
"""

from __future__ import annotations

import json

from ..config import FRONTEND_SNAPSHOT
from ..db import fetch_stock_rows, now_iso, supabase_client
from ..log import get_logger

log = get_logger(__name__)

# Large, well-known companies across sectors — enough to make every page useful offline.
DEFAULT_SYMBOLS = """
RELIANCE TCS HDFCBANK ICICIBANK INFY BHARTIARTL SBIN ITC LT HINDUNILVR KOTAKBANK AXISBANK
BAJFINANCE MARUTI SUNPHARMA HCLTECH TITAN NTPC ONGC ASIANPAINT ULTRACEMCO WIPRO POWERGRID
TMPV ETERNAL ADANIENT ADANIPORTS JSWSTEEL TATASTEEL COALINDIA NESTLEIND BAJAJFINSV TECHM
HINDALCO GRASIM DRREDDY CIPLA BRITANNIA EICHERMOT HEROMOTOCO APOLLOHOSP TATACONSUM DIVISLAB
BPCL INDUSINDBK HAL BEL MTARTECH KAYNES RADICO TRENT DMART PIDILITIND HDFCLIFE SBILIFE M&M
DIXON POLYCAB PERSISTENT LTIM IRCTC PAYTM NYKAA JIOFIN VBL HAVELLS TATAPOWER BAJAJ-AUTO
SHRIRAMFIN CHOLAFIN
""".split()

INDICES = ["NIFTY50", "SENSEX", "BANKNIFTY", "INDIAVIX"]


def run(symbols: list[str] | None = None, path=FRONTEND_SNAPSHOT) -> None:
    wanted = [s.upper() for s in symbols] if symbols else DEFAULT_SYMBOLS
    stocks = fetch_stock_rows(wanted)
    prices = (
        supabase_client()
        .table("live_prices")
        .select("*")
        .in_("symbol", wanted + INDICES)
        .execute()
        .data
    )
    missing = sorted(set(wanted) - set(stocks))
    if missing:
        log.warning(f"Not in Supabase, skipped: {' '.join(missing)}")

    data = {
        "generated_at": now_iso(),
        "stocks": sorted(stocks.values(), key=lambda r: r["symbol"]),
        "prices": sorted(prices, key=lambda r: r["symbol"]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info(f"Wrote {len(stocks)} stocks and {len(prices)} prices to {path}")
