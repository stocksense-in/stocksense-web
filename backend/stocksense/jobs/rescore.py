"""
Rescore job — recomputes every stored composite score from the metrics already
in the database. No Yahoo requests, so it takes seconds; run it after changing
stocksense/scoring.py.

    python -m stocksense rescore
"""

from __future__ import annotations

from ..db import Store, supabase_client
from ..log import get_logger
from ..scoring import score_row

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
    for row in rows:
        score = score_row(row)
        if row.get("composite_score") != score.composite or row.get("score_coverage") != score.coverage:
            changed.append({**row, "composite_score": score.composite, "score_coverage": score.coverage})

    log.info(f"{len(rows)} stocks checked, {len(changed)} scores changed")
    store.upsert_stocks(changed)
