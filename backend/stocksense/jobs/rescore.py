"""
Rescore job — recomputes every stored composite score from the metrics already
in the database: 70% versus sector peers + 30% fixed curves (stocksense/blend.py).
No Yahoo requests, so it takes seconds. The fundamentals and ownership jobs end
with it, because each stock's score depends on all its peers.

    python -m stocksense rescore
"""

from __future__ import annotations

from ..blend import rescore_rows
from ..db import Store, supabase_client
from ..log import get_logger

log = get_logger(__name__)


def run(store: Store) -> None:
    client = supabase_client()
    rows: list[dict] = []
    for offset in range(0, 10_000, 1000):
        page = client.table("stocks").select("*").range(offset, offset + 999).execute().data
        rows.extend(page)
        if len(page) < 1000:
            break

    changed = []
    for row, score in zip(rows, rescore_rows(rows)):
        if row.get("composite_score") != score.composite or row.get("score_coverage") != score.coverage:
            changed.append({**row, "composite_score": score.composite, "score_coverage": score.coverage})

    log.info(f"{len(rows)} stocks checked, {len(changed)} scores changed")
    store.upsert_stocks(changed)
