"""
Yahoo Finance via yfinance — fundamentals, ownership, revenue growth and prices.

Unit conventions returned by this module (Yahoo's raw units differ, see notes):
  roe, net_margin, promoter_holding, revenue_cagr_3yr, price_change_pct → percent (31.2 = 31.2%)
  debt_equity → ratio (0.08 = 0.08×). Yahoo reports it as a percentage (8.0).
  market_cap  → ₹ crore
"""

from __future__ import annotations

import math
import threading
import time

import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from ..log import get_logger
from ..sectors import sector_code
from ..symbols import Symbol

log = get_logger(__name__)


def _num(value) -> float | None:
    """Float, or None for missing / NaN / infinite values."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _pct(fraction) -> float | None:
    f = _num(fraction)
    return round(f * 100, 2) if f is not None else None


class _RateLimiter:
    """Spaces out requests across all threads. Yahoo starts returning HTTP 429 after ~900 fast requests."""

    def __init__(self, per_second: float):
        self._interval = 1 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self._interval
        if delay > 0:
            time.sleep(delay)


_limiter = _RateLimiter(per_second=2.5)
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_PAUSE_SECONDS = 60


def _with_backoff(call, label: str):
    """Run a Yahoo request; on HTTP 429 pause and retry instead of failing the stock."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        _limiter.wait()
        try:
            return call()
        except YFRateLimitError:
            if attempt == RATE_LIMIT_RETRIES:
                log.warning(f"{label}: still rate-limited after {attempt} retries, skipping")
                return None
            pause = RATE_LIMIT_PAUSE_SECONDS * (attempt + 1)
            log.warning(f"Yahoo rate limit hit — pausing {pause}s")
            time.sleep(pause)
        except Exception as exc:  # yfinance raises a zoo of exception types
            log.debug(f"{label}: {exc}")
            return None
    return None


def _info(ticker: str) -> dict | None:
    info = _with_backoff(lambda: yf.Ticker(ticker).info, ticker)
    if not info:
        return None
    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    return info if price else None


def fundamentals(sym: Symbol) -> dict | None:
    """
    One `stocks` row for this symbol, or None if Yahoo has no data.
    Tries the NSE ticker first, then BSE (some small caps only resolve there).
    """
    info = _info(sym.yahoo) or _info(sym.yahoo_bse)
    if info is None:
        return None

    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    prev_close = _num(info.get("regularMarketPreviousClose")) or _num(info.get("previousClose"))
    change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else None

    debt_equity = _num(info.get("debtToEquity"))
    market_cap = _num(info.get("marketCap"))

    return {
        "symbol": sym.symbol,
        "name": info.get("longName") or sym.name,
        "isin": sym.isin or None,
        "sector": sector_code(info.get("sector"), info.get("industry")),
        "industry": info.get("industry"),
        "market_cap": round(market_cap / 1e7) if market_cap else None,
        "pe_ratio": _round(_num(info.get("trailingPE")), 2),
        "pb_ratio": _round(_num(info.get("priceToBook")), 2),
        "roe": _pct(info.get("returnOnEquity")),
        "debt_equity": round(debt_equity / 100, 3) if debt_equity is not None else None,
        "net_margin": _pct(info.get("profitMargins")),
        "dividend_yield": _round(_num(info.get("dividendYield")), 2),
        "promoter_holding": _pct(info.get("heldPercentInsiders")),
        "price": round(price, 2),
        "price_change_pct": change_pct,
        "week52_high": _round(_num(info.get("fiftyTwoWeekHigh")), 2),
        "week52_low": _round(_num(info.get("fiftyTwoWeekLow")), 2),
    }


def _round(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def revenue_cagr(sym: Symbol) -> float | None:
    """Compound annual revenue growth across the annual statements Yahoo has (usually 3–4 years)."""
    fin = _with_backoff(lambda: yf.Ticker(sym.yahoo).financials, f"{sym.symbol} financials")
    if fin is None or fin.empty:
        return None
    for label in ("Total Revenue", "Operating Revenue"):
        if label in fin.index:
            # Columns are newest → oldest.
            revenues = [v for v in (_num(x) for x in fin.loc[label].values) if v and v > 0]
            if len(revenues) >= 2:
                years = len(revenues) - 1
                return round(((revenues[0] / revenues[-1]) ** (1 / years) - 1) * 100, 1)
    return None


def latest_prices(tickers: list[str]) -> dict[str, tuple[float, float]]:
    """
    {yahoo_ticker: (last_close, change_pct)} for many tickers in one request.
    Uses 5 days of daily candles so the previous close is always available.
    """
    if not tickers:
        return {}
    try:
        frame = yf.download(
            tickers=tickers,
            period="5d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        log.error(f"Batch price download failed: {exc}")
        return {}

    result: dict[str, tuple[float, float]] = {}
    for ticker in tickers:
        try:
            closes = (frame[ticker]["Close"] if len(tickers) > 1 else frame["Close"]).dropna()
        except KeyError:
            continue
        if hasattr(closes, "columns"):  # newer yfinance keeps a ticker level on single downloads
            closes = closes.iloc[:, 0]
        if closes.empty:
            continue
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else last
        change = (last - prev) / prev * 100 if prev else 0.0
        result[ticker] = (round(last, 2), round(change, 2))
    return result
