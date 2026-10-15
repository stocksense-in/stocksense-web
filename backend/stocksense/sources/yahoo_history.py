"""
Full daily history of global market series from Yahoo's public chart endpoint:
crude, gold, the rupee, US rates and equities. Internal research use only
(PLAN.md §4: replace before anything is published).

Futures (BZ=F, CL=F, …) are Yahoo's continuous front-month series, so a contract
roll can add a small jump; use multi-day windows rather than single days when it matters.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
import pandas as pd

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0 (StockSense)"}

# StockSense code → (Yahoo ticker, what it is)
SERIES: dict[str, tuple[str, str]] = {
    "BRENT": ("BZ=F", "Brent crude, front-month future, USD/bbl"),
    "WTI": ("CL=F", "WTI crude, front-month future, USD/bbl"),
    "GOLD": ("GC=F", "Gold future, USD/oz"),
    "COPPER": ("HG=F", "Copper future, USD/lb"),
    "NATGAS": ("NG=F", "Henry Hub natural gas future, USD/MMBtu"),
    "USDINR": ("INR=X", "Rupees per US dollar"),
    "DXY": ("DX-Y.NYB", "US dollar index"),
    "US10Y": ("^TNX", "US 10-year Treasury yield, %"),
    "SP500": ("^GSPC", "S&P 500"),
    "US_VIX": ("^VIX", "CBOE volatility index"),
    "NIFTY50_YF": ("^NSEI", "NIFTY 50 (Yahoo; cross-check for NSE files)"),
}


def fetch(ticker: str, client: httpx.Client) -> dict:
    resp = client.get(URL.format(ticker=ticker),
                      params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"})
    resp.raise_for_status()
    return resp.json()


def to_frame(code: str, payload: dict) -> pd.DataFrame:
    """Chart JSON → (series, date, open, high, low, close, volume), one row per trading day."""
    result = (payload.get("chart", {}).get("result") or [None])[0]
    cols = ["series", "date", "open", "high", "low", "close", "volume"]
    if not result or not result.get("timestamp"):
        return pd.DataFrame(columns=cols)
    quote = result["indicators"]["quote"][0]
    offset = (result.get("meta") or {}).get("gmtoffset", 0)  # exchange-local trading date
    df = pd.DataFrame({
        "series": code,
        "date": [datetime.fromtimestamp(t + offset, timezone.utc).date() for t in result["timestamp"]],
        "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
        "close": quote.get("close"), "volume": quote.get("volume"),
    })
    df = df[df["close"].notna()]
    return df.drop_duplicates(subset=["date"], keep="last")[cols].reset_index(drop=True)
