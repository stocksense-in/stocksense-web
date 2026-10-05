"""
Fundamentals job — price + P/E, ROE, D/E, margin, ownership for each stock, scored and saved.

Replaces the old fetch_yfinance.py and fetch_fundamentals.py (they did the same
thing with different bugs). Revenue CAGR comes from the separate `ownership`
job because it needs a second, slower Yahoo request per stock.

    python -m stocksense fundamentals --symbols INFY TCS
    python -m stocksense fundamentals --limit 50 --snapshot
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..db import Store, now_iso
from ..log import get_logger
from ..scoring import score_row
from ..sources import yahoo
from ..symbols import chunks, select

log = get_logger(__name__)


def run(
    store: Store,
    symbols: list[str] | None = None,
    limit: int | None = None,
    workers: int = 8,
    batch_size: int = 100,
    refresh_symbols: bool = False,
) -> None:
    targets = select(symbols, limit, refresh_symbols)
    log.info(f"Fundamentals for {len(targets)} stocks ({workers} workers)")
    known = store.existing_stocks([t.symbol for t in targets])
    ok = 0
    failed: list[str] = []

    for number, batch in enumerate(chunks(targets, batch_size), start=1):
        log.info(f"Batch {number}: {batch[0].symbol} … {batch[-1].symbol}")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fetched = list(pool.map(yahoo.fundamentals, batch))

        rows = []
        for sym, row in zip(batch, fetched):
            if row is None:
                failed.append(sym.symbol)
                continue
            # Start from the stored row so a value Yahoo omits today (or revenue CAGR,
            # which only the ownership job fetches) is kept instead of nulled.
            row = {**known.get(sym.symbol, {}), **{k: v for k, v in row.items() if v is not None}}
            score = score_row(row)
            row["composite_score"] = score.composite
            row["score_coverage"] = score.coverage
            row["last_updated"] = now_iso()
            rows.append(row)
            ok += 1

        store.upsert_stocks(rows)

    log.info(f"Done — {ok} saved, {len(failed)} without Yahoo data.")
    if failed:
        log.info(f"No data: {' '.join(failed[:20])}{' …' if len(failed) > 20 else ''}")
