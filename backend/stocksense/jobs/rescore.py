"""
Rescore job — recomputes every stored composite score from the metrics already
in the database: 70% versus sector peers + 30% fixed curves (stocksense/blend.py).
No Yahoo requests, so it takes seconds. The fundamentals and ownership jobs end
with it, because each stock's score depends on all its peers.

    python -m stocksense rescore
    python -m stocksense rescore --fundamentals filings   # margin + growth from NSE filings (M1.2)

With `--fundamentals filings`, net margin, 3-year revenue growth, ROE and debt to
equity come from the companies' own quarterly filings (stocksense/filing_metrics.py) wherever the lake has
them. It prints Yahoo-based and filing-based scores side by side, and writes only if
every filing-based figure is recent — otherwise it is a comparison, nothing saved.
"""

from __future__ import annotations

import pandas as pd

from .. import filing_metrics
from ..blend import rescore_rows
from ..db import Store, supabase_client
from ..log import get_logger

log = get_logger(__name__)


def load_rows() -> list[dict]:
    client = supabase_client()
    rows: list[dict] = []
    for offset in range(0, 10_000, 1000):
        page = client.table("stocks").select("*").range(offset, offset + 999).execute().data
        rows.extend(page)
        if len(page) < 1000:
            break
    return rows


def compare(rows: list[dict], metrics: pd.DataFrame) -> pd.DataFrame:
    """Yahoo-based vs filing-based inputs and scores for the companies the filings cover."""
    swapped, _ = filing_metrics.overlay(rows, metrics)
    before, after = rescore_rows(rows), rescore_rows(swapped)
    covered = set(metrics["symbol"]) if len(metrics) else set()
    as_of = metrics.set_index("symbol")["as_of"].to_dict() if len(metrics) else {}
    out = []
    for old, new, s0, s1 in zip(rows, swapped, before, after):
        if old.get("symbol") not in covered:
            continue
        out.append({"symbol": old["symbol"], "as_of": as_of[old["symbol"]],
                    "margin_yahoo": old.get("net_margin"), "margin_filings": new.get("net_margin"),
                    "cagr_yahoo": old.get("revenue_cagr_3yr"), "cagr_filings": new.get("revenue_cagr_3yr"),
                    "roe_yahoo": old.get("roe"), "roe_filings": new.get("roe"),
                    "de_yahoo": old.get("debt_equity"), "de_filings": new.get("debt_equity"),
                    "score_yahoo": s0.composite, "score_filings": s1.composite})
    df = pd.DataFrame(out)
    if len(df):
        df["score_move"] = df["score_filings"] - df["score_yahoo"]
    return df


def run(store: Store, fundamentals: str = "yahoo") -> None:
    rows = load_rows()
    if fundamentals == "filings":
        from ..lake import Lake

        metrics = filing_metrics.latest(Lake.from_settings().query("select * from financial_results"))
        report = compare(rows, metrics)
        with pd.option_context("display.width", 160, "display.max_rows", 500):
            log.info("Yahoo vs filings:\n" + report.to_string(index=False))
        if len(report):
            moves = report["score_move"].dropna().abs()
            log.info(f"{len(report)} companies; median score move {moves.median():.0f}, largest {moves.max():.0f}")
        old = filing_metrics.stale(metrics)
        if old:
            log.info(f"Not saved: {len(old)} companies' filing figures are over "
                     f"{filing_metrics.MAX_AGE_DAYS} days old (latest {metrics['as_of'].max()}).")
            return
        rows, _ = filing_metrics.overlay(rows, metrics)

    changed = []
    for row, score in zip(rows, rescore_rows(rows)):
        if row.get("composite_score") != score.composite or row.get("score_coverage") != score.coverage:
            changed.append({**row, "composite_score": score.composite, "score_coverage": score.coverage})

    log.info(f"{len(rows)} stocks checked, {len(changed)} scores changed")
    store.upsert_stocks(changed)
