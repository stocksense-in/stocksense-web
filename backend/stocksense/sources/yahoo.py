"""
Yahoo Finance via yfinance — fundamentals, ownership, revenue growth and prices.

Unit conventions returned by this module (Yahoo's raw units differ, see notes):
  roe, net_margin, promoter_holding, revenue_cagr_3yr, price_change_pct → percent (31.2 = 31.2%)
  debt_equity → ratio (0.08 = 0.08×). Yahoo reports it as a percentage (8.0).
  market_cap  → ₹ crore
"""

from __future__ import annotations

import math

import yfinance as yf

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


def _info(ticker: str) -> dict | None:
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:  # yfinance raises a zoo of exception types
        log.debug(f"{ticker}: info failed: {exc}")
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
    try:
        fin = yf.Ticker(sym.yahoo).financials
    except Exception:
        return None
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
