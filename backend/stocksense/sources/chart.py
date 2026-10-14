"""
Price history from Yahoo Finance's public chart endpoint (no key needed).

    history("INFY", "1y")      → [(unix_seconds, close), …]
    history("NIFTY50", "1d")   → 5-minute bars for the latest session
"""

from __future__ import annotations

import httpx

from ..log import get_logger

log = get_logger(__name__)

RANGES = {"1d": "5m", "5d": "15m", "1mo": "1d", "6mo": "1d", "1y": "1d", "5y": "1wk"}
INDEX_TICKERS = {"NIFTY50": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX"}
_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def yahoo_ticker(symbol: str) -> str:
    return INDEX_TICKERS.get(symbol.upper(), f"{symbol.upper()}.NS")


def history(symbol: str, range_: str = "1y") -> list[tuple[int, float]]:
    if range_ not in RANGES:
        raise ValueError(f"range must be one of {', '.join(RANGES)}")
    try:
        resp = httpx.get(
            _URL.format(ticker=yahoo_ticker(symbol)),
            params={"range": range_, "interval": RANGES[range_]},
            headers={"User-Agent": "Mozilla/5.0 (StockSense)"},
            timeout=15,
        )
        resp.raise_for_status()
        result = (resp.json().get("chart", {}).get("result") or [None])[0]
    except (httpx.HTTPError, ValueError) as exc:
        log.warning(f"Chart request failed for {symbol}: {exc}")
        return []
    if not result:
        return []
    times = result.get("timestamp") or []
    closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    return [(t, round(c, 2)) for t, c in zip(times, closes) if c is not None]
