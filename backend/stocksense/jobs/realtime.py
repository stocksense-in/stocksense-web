"""
Realtime job — streams live prices from the Upstox WebSocket into `live_prices`.

Ticks are buffered and written once per second (latest price per symbol), so
the database sees at most one write per second however busy the market is.
Reconnects automatically with backoff.

Replaces realtime_ws.py.

    python -m stocksense realtime                  # all NSE stocks + indices
    python -m stocksense realtime --symbols INFY TCS
"""

from __future__ import annotations

import asyncio
import json
import time

import websockets

from ..db import Store, now_iso
from ..log import get_logger
from ..sources import upstox
from ..sources.upstox_feed import decode
from ..symbols import chunks, select

log = get_logger(__name__)

FLUSH_EVERY_SECONDS = 1.0
SUBSCRIBE_CHUNK = 500


async def _stream(store: Store, key_to_symbol: dict[str, str]) -> None:
    url = upstox.websocket_url()
    async with websockets.connect(url, max_size=None) as ws:
        for index, batch in enumerate(chunks(list(key_to_symbol), SUBSCRIBE_CHUNK)):
            await ws.send(
                json.dumps(
                    {
                        "guid": f"stocksense-{index}",
                        "method": "sub",
                        "data": {"mode": "ltpc", "instrumentKeys": batch},
                    }
                ).encode()
            )
        log.info(f"Subscribed to {len(key_to_symbol)} instruments")

        pending: dict[str, dict] = {}
        last_flush = time.monotonic()
        async for message in ws:
            if isinstance(message, bytes):
                for key, (ltp, prev_close) in decode(message).items():
                    symbol = key_to_symbol.get(key)
                    if symbol:
                        change = (ltp - prev_close) / prev_close * 100 if prev_close else 0.0
                        pending[symbol] = {
                            "symbol": symbol,
                            "price": round(ltp, 2),
                            "change_pct": round(change, 2),
                        }

            if pending and time.monotonic() - last_flush >= FLUSH_EVERY_SECONDS:
                stamp = now_iso()
                rows = [{**row, "updated_at": stamp} for row in pending.values()]
                store.upsert_prices(rows)
                pending.clear()
                last_flush = time.monotonic()


async def _run_forever(store: Store, key_to_symbol: dict[str, str]) -> None:
    delay = 5
    while True:
        try:
            await _stream(store, key_to_symbol)
            delay = 5
        except Exception as exc:
            log.warning(f"Feed disconnected ({exc}); reconnecting in {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 120)


def run(store: Store, symbols: list[str] | None = None, limit: int | None = None) -> None:
    targets = select(symbols, limit)
    key_to_symbol = {key: symbol for symbol, key in upstox.INDEX_KEYS.items()}
    key_to_symbol.update({upstox.equity_key(t.isin): t.symbol for t in targets if t.isin})
    try:
        asyncio.run(_run_forever(store, key_to_symbol))
    except KeyboardInterrupt:
        log.info("Stopped.")
