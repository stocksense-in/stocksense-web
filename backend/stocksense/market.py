"""
Read side of the database: every stock with its latest price, as typed objects.

The API and any read-only consumer go through MarketData. It reads Supabase's
REST endpoint (read-only anon key when available), caches results briefly, and
falls back to backend/data/snapshot.json when Supabase isn't configured or
can't be reached — so the API keeps answering during an outage.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import httpx

from .config import SNAPSHOT_PATH, get_settings
from .log import get_logger

log = get_logger(__name__)

STOCKS_TTL_SECONDS = 300  # fundamentals change daily
PRICES_TTL_SECONDS = 30  # prices change by the minute
PAGE_SIZE = 1000  # PostgREST's default maximum rows per request
# A stock whose data is this much older than the latest pipeline run is treated as
# stale — usually delisted or renamed (e.g. merged companies). Relative to the
# newest row, so a paused pipeline doesn't make every stock stale at once.
STALE_AFTER_DAYS = 7
INDEX_SYMBOLS = {
    "NIFTY50": "NIFTY 50",
    "SENSEX": "SENSEX",
    "BANKNIFTY": "BANK NIFTY",
    "INDIAVIX": "India VIX",
}


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_pct: float | None
    updated_at: str | None


@dataclass(frozen=True)
class Stock:
    """
    One NSE stock. Percent fields are percentages (31.2 = 31.2%); `de` is a ratio
    (0.4 = 0.4×); `market_cap` is ₹ crore. Any field may be None.
    """

    symbol: str
    name: str
    sector: str
    industry: str | None
    market_cap: float | None
    price: float | None
    change_pct: float | None
    week52_high: float | None
    week52_low: float | None
    pe: float | None
    pb: float | None
    roe: float | None
    de: float | None
    margin: float | None
    dividend_yield: float | None
    promoter: float | None
    cagr: float | None
    score: int | None
    updated_at: str | None
    stale: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stock_from_row(row: dict, stale: bool = False) -> Stock:
    """Database row (column names from schema.sql) → Stock."""
    score = _num(row.get("composite_score"))
    return Stock(
        symbol=row["symbol"],
        name=row.get("name") or row["symbol"],
        sector=row.get("sector") or "general",
        industry=row.get("industry"),
        market_cap=_num(row.get("market_cap")),
        price=_num(row.get("price")),
        change_pct=_num(row.get("price_change_pct")),
        week52_high=_num(row.get("week52_high")),
        week52_low=_num(row.get("week52_low")),
        pe=_num(row.get("pe_ratio")),
        pb=_num(row.get("pb_ratio")),
        roe=_num(row.get("roe")),
        de=_num(row.get("debt_equity")),
        margin=_num(row.get("net_margin")),
        dividend_yield=_num(row.get("dividend_yield")),
        promoter=_num(row.get("promoter_holding")),
        cagr=_num(row.get("revenue_cagr_3yr")),
        score=int(score) if score is not None else None,
        updated_at=row.get("last_updated"),
        stale=stale,
    )


def quote_from_row(row: dict) -> Quote:
    return Quote(
        symbol=row["symbol"],
        price=float(row["price"]),
        change_pct=_num(row.get("change_pct")),
        updated_at=row.get("updated_at"),
    )


def _timestamp(iso: str | None) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def with_quote(stock: Stock, quote: Quote | None) -> Stock:
    """Use the live price when it is newer than the fundamentals job's price."""
    if quote is None:
        return stock
    if stock.price is not None and _timestamp(stock.updated_at) > _timestamp(quote.updated_at):
        return stock
    return Stock(**{**stock.to_dict(), "price": quote.price, "change_pct": quote.change_pct if quote.change_pct is not None else stock.change_pct})


class TTLCache:
    """Caches one value per key for a fixed time. Thread-safe; the API serves from a thread pool."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, object]] = {}

    def get(self, key: str, ttl: float, load: Callable[[], object]):
        with self._lock:
            hit = self._items.get(key)
            if hit and time.monotonic() - hit[0] < ttl:
                return hit[1]
        value = load()  # outside the lock: a slow load must not block other keys
        with self._lock:
            self._items[key] = (time.monotonic(), value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class MarketData:
    """
    Source of stocks and quotes. Construct with no arguments in production;
    tests pass `rows` / `price_rows` to run without a network.
    """

    def __init__(
        self,
        rows: list[dict] | None = None,
        price_rows: list[dict] | None = None,
        snapshot_path: Path = SNAPSHOT_PATH,
    ):
        self._static = rows is not None
        self._rows = rows or []
        self._price_rows = price_rows or []
        self._snapshot_path = snapshot_path
        self._cache = TTLCache()
        settings = get_settings()
        self._url = settings.supabase_url
        self._key = settings.supabase_anon_key or settings.supabase_service_key
        self.source = "fixture" if self._static else ("supabase" if self._url and self._key else "snapshot")

    # ── public ──────────────────────────────────────────────────────────────

    def quotes(self) -> dict[str, Quote]:
        rows = self._cache.get("prices", PRICES_TTL_SECONDS, lambda: self._load("live_prices", "symbol,price,change_pct,updated_at", "prices"))
        return {r["symbol"]: quote_from_row(r) for r in rows if r.get("price") is not None}

    def stocks(self) -> list[Stock]:
        """Every stock, including stale ones (flagged). Use fresh_stocks() for lists and rankings."""
        rows = self._cache.get("stocks", STOCKS_TTL_SECONDS, lambda: self._load("stocks", "*", "stocks"))
        quotes = self.quotes()
        latest = max((_timestamp(r.get("last_updated")) for r in rows), default=0.0)
        cutoff = latest - STALE_AFTER_DAYS * 86_400
        return [
            with_quote(stock_from_row(r, stale=_timestamp(r.get("last_updated")) < cutoff), quotes.get(r["symbol"]))
            for r in rows
        ]

    def fresh_stocks(self) -> list[Stock]:
        return [s for s in self.stocks() if not s.stale]

    def stock(self, symbol: str) -> Stock | None:
        wanted = symbol.upper()
        return next((s for s in self.stocks() if s.symbol == wanted), None)

    def indices(self) -> list[dict]:
        quotes = self.quotes()
        return [
            {"symbol": symbol, "label": label, **_quote_fields(quotes[symbol])}
            for symbol, label in INDEX_SYMBOLS.items()
            if symbol in quotes
        ]

    def refresh(self) -> None:
        """Drop cached data so the next request reads fresh rows."""
        self._cache.clear()

    # ── loading ─────────────────────────────────────────────────────────────

    def _load(self, table: str, columns: str, snapshot_key: str) -> list[dict]:
        if self._static:
            return self._rows if table == "stocks" else self._price_rows
        if self.source == "supabase":
            try:
                return self._select_all(table, columns)
            except httpx.HTTPError as exc:
                log.warning(f"Supabase unavailable ({exc}); serving the snapshot for `{table}`")
        return self._snapshot().get(snapshot_key, [])

    def _select_all(self, table: str, columns: str) -> list[dict]:
        headers = {"apikey": self._key, "Authorization": f"Bearer {self._key}"}
        rows: list[dict] = []
        with httpx.Client(base_url=f"{self._url}/rest/v1", headers=headers, timeout=20) as client:
            for offset in range(0, 100_000, PAGE_SIZE):
                resp = client.get(
                    f"/{table}",
                    params={"select": columns, "order": "symbol"},
                    headers={"Range": f"{offset}-{offset + PAGE_SIZE - 1}"},
                )
                resp.raise_for_status()
                page = resp.json()
                rows.extend(page)
                if len(page) < PAGE_SIZE:
                    break
        return rows

    def _snapshot(self) -> dict:
        if not self._snapshot_path.exists():
            return {}
        return json.loads(self._snapshot_path.read_text(encoding="utf-8"))


def _quote_fields(q: Quote) -> dict:
    return {"price": q.price, "change_pct": q.change_pct, "updated_at": q.updated_at}
