"""
Ownership job — promoter holding and 3-year revenue CAGR, then re-scores the stock.

Each metric tries, in order: Yahoo Finance → Screener.in → the hardcoded
large-cap table in sources/fallbacks.py. Slower than `fundamentals` (one
Screener page per gap), so run it daily rather than intraday.

Replaces the old fetch_nse.py.

    python -m stocksense ownership --symbols INFY TCS
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from ..db import Store, now_iso
from ..log import get_logger
from ..scoring import score_row
from ..sources import screener, yahoo
from ..sources.fallbacks import FALLBACKS
from ..symbols import Symbol, chunks, select

log = get_logger(__name__)


def _ownership(sym: Symbol, stored: dict) -> dict:
    promoter = stored.get("promoter_holding")  # fundamentals job already tried Yahoo
    if promoter is None:
        promoter = screener.promoter_holding(sym.symbol)
    if promoter is None:
        promoter = FALLBACKS.get(sym.symbol, {}).get("promoter")

    cagr = yahoo.revenue_cagr(sym)
    if cagr is None:
        cagr = screener.sales_cagr_3yr(sym.symbol)
    if cagr is None:
        cagr = FALLBACKS.get(sym.symbol, {}).get("cagr")

    return {"promoter_holding": promoter, "revenue_cagr_3yr": cagr}


def run(
    store: Store,
    symbols: list[str] | None = None,
    limit: int | None = None,
    workers: int = 4,
    batch_size: int = 50,
    refresh_symbols: bool = False,
) -> None:
    targets = select(symbols, limit, refresh_symbols)
    log.info(f"Ownership + growth for {len(targets)} stocks")
    stored = store.existing_stocks([t.symbol for t in targets])

    for number, batch in enumerate(chunks(targets, batch_size), start=1):
        log.info(f"Batch {number}: {batch[0].symbol} … {batch[-1].symbol}")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda s: _ownership(s, stored.get(s.symbol, {})), batch))

        rows = []
        for sym, found in zip(batch, results):
            base = stored.get(sym.symbol, {"symbol": sym.symbol, "name": sym.name})
            row = {**base, **{k: v for k, v in found.items() if v is not None}}
            score = score_row(row)
            row["composite_score"] = score.composite
            row["score_coverage"] = score.coverage
            row["last_updated"] = now_iso()
            rows.append(row)
            log.info(
                f"  {sym.symbol:<12} promoter={found['promoter_holding']}  "
                f"cagr={found['revenue_cagr_3yr']}  score={score.composite}"
            )
        store.upsert_stocks(rows)
        time.sleep(1)  # be polite to Screener.in between batches

    log.info("Done.")
