"""
Cleanup job — finds stocks in the database that are no longer on NSE's equity
list (delisted, merged or renamed) and whose data has stopped updating.

Lists them by default. Rows are only deleted with --apply.

    python -m stocksense cleanup            # show what would be removed
    python -m stocksense cleanup --apply    # delete them from stocks and live_prices
"""

from __future__ import annotations

from ..db import supabase_client
from ..log import get_logger
from ..market import INDEX_SYMBOLS, MarketData
from ..symbols import all_symbols

log = get_logger(__name__)


def candidates() -> list[dict]:
    listed = {s.symbol for s in all_symbols()}
    return [
        {"symbol": s.symbol, "name": s.name, "updated_at": s.updated_at}
        for s in MarketData().stocks()
        if s.stale and s.symbol not in listed and s.symbol not in INDEX_SYMBOLS
    ]


def run(apply: bool = False) -> None:
    rows = candidates()
    for r in sorted(rows, key=lambda r: r["symbol"]):
        log.info(f"  {r['symbol']:<14} last updated {r['updated_at']}  {r['name']}")
    if not rows:
        log.info("Nothing to clean up.")
        return
    if not apply:
        log.info(f"{len(rows)} delisted/renamed stocks found. Re-run with --apply to delete them.")
        return
    client = supabase_client()
    symbols = [r["symbol"] for r in rows]
    for table in ("stocks", "live_prices"):
        client.table(table).delete().in_("symbol", symbols).execute()
    log.info(f"Deleted {len(symbols)} stocks from `stocks` and `live_prices`.")
