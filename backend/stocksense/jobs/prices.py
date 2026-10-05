"""
Prices job — latest price and day change for every stock and the main indices.

Uses Yahoo by default (no login needed, ~15 min delayed). Pass --source upstox
for real-time quotes once you've run `upstox-login` today.

Replaces fetch_live_prices.py, fetch_price.py and upstox_live.py.

    python -m stocksense prices                    # all NSE stocks, Yahoo
    python -m stocksense prices --source upstox --symbols INFY RELIANCE
"""

from __future__ import annotations

from ..db import Store, now_iso
from ..log import get_logger
from ..sources import upstox, yahoo
from ..symbols import chunks, select

log = get_logger(__name__)

YAHOO_INDICES = {
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "INDIAVIX": "^INDIAVIX",
}


def _yahoo_rows(targets, batch_size: int):
    indices = yahoo.index_quotes(list(YAHOO_INDICES.values()))
    yield [
        {"symbol": symbol, "price": indices[ticker][0], "change_pct": indices[ticker][1]}
        for symbol, ticker in YAHOO_INDICES.items()
        if ticker in indices
    ]
    pairs = [(t.symbol, t.yahoo) for t in targets]
    for batch in chunks(pairs, batch_size):
        quotes = yahoo.latest_prices([ticker for _, ticker in batch])
        yield [
            {"symbol": symbol, "price": quotes[ticker][0], "change_pct": quotes[ticker][1]}
            for symbol, ticker in batch
            if ticker in quotes
        ]


def _upstox_rows(targets):
    key_to_symbol = {key: symbol for symbol, key in upstox.INDEX_KEYS.items()}
    key_to_symbol.update({upstox.equity_key(t.isin): t.symbol for t in targets if t.isin})
    quotes = upstox.ltp_quotes(list(key_to_symbol))
    yield [{"symbol": key_to_symbol[key], **quote} for key, quote in quotes.items() if key in key_to_symbol]


def run(
    store: Store,
    symbols: list[str] | None = None,
    limit: int | None = None,
    source: str = "yahoo",
    batch_size: int = 200,
    refresh_symbols: bool = False,
) -> None:
    targets = select(symbols, limit, refresh_symbols)
    log.info(f"Prices for {len(targets)} stocks + indices via {source}")
    batches = _upstox_rows(targets) if source == "upstox" else _yahoo_rows(targets, batch_size)

    total = 0
    for rows in batches:
        stamp = now_iso()
        for row in rows:
            row["updated_at"] = stamp
        store.upsert_prices(rows)
        total += len(rows)
    log.info(f"Done — {total} prices saved.")
