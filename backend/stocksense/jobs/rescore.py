"""
Rescore job — recomputes every stored composite score from the metrics already
in the database: 70% versus sector peers + 30% fixed curves (stocksense/blend.py).
No Yahoo requests, so it takes seconds. The fundamentals and ownership jobs end
with it, because each stock's score depends on all its peers.

    python -m stocksense rescore
    python -m stocksense rescore --fundamentals filings           # compare only, nothing saved
    python -m stocksense rescore --fundamentals filings --apply   # publish filing-based scores

With `--fundamentals filings`, net margin, 3-year revenue growth, ROE, debt to equity
and promoter holding come from the companies' own filings (stocksense/filing_metrics.py) wherever the lake has
them. It prints Yahoo-based and filing-based scores side by side and saves nothing
unless `--apply` is given — and even then only if every filing-based figure is recent.
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


def compare(rows: list[dict], metrics: pd.DataFrame, only: list[str] | None = None) -> pd.DataFrame:
    """Yahoo-based vs filing-based inputs and scores for the companies the filings cover."""
    swapped, _ = filing_metrics.overlay(rows, metrics, only)
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
                    "promoter_yahoo": old.get("promoter_holding"), "promoter_filings": new.get("promoter_holding"),
                    "score_yahoo": s0.composite, "score_filings": s1.composite})
    df = pd.DataFrame(out)
    if len(df):
        df["score_move"] = df["score_filings"] - df["score_yahoo"]
    return df


def filing_inputs(lake, only: list[str] | None = None) -> pd.DataFrame:
    """Filing-based inputs per company. Promoter-only reads just the shareholding patterns, so
    its `as_of` is the pattern's quarter and companies without results are included."""
    present = set(lake.datasets())
    empty = pd.DataFrame(columns=["symbol", "as_of"])
    needs_results = not only or set(only) - {"promoter"}
    metrics = (filing_metrics.latest(lake.query("select * from financial_results"))
               if needs_results and "financial_results" in present else empty)
    if "shareholding" in present and (not only or "promoter" in only):
        metrics = filing_metrics.with_promoter(metrics, lake.query("select * from shareholding"))
    return metrics


def run(store: Store, fundamentals: str = "yahoo", apply: bool = False, only: list[str] | None = None) -> None:
    rows = load_rows()
    if fundamentals == "filings":
        from ..lake import Lake

        metrics = filing_inputs(Lake.from_settings(), only)
        report = compare(rows, metrics, only)
        with pd.option_context("display.width", 160, "display.max_rows", 500):
            log.info("Yahoo vs filings:\n" + report.to_string(index=False))
        if len(report):
            moves = report["score_move"].dropna().abs()
            log.info(f"{len(report)} companies; median score move {moves.median():.0f}, largest {moves.max():.0f}")
        if not apply:
            log.info("Comparison only — nothing saved (add --apply to publish these scores).")
            return
        old = set(filing_metrics.stale(metrics))
        if old:  # those keep their current values; everyone else switches
            log.info(f"{len(old)} companies' filing figures are over {filing_metrics.MAX_AGE_DAYS} days old; "
                     "they keep their current values.")
            metrics = metrics[~metrics["symbol"].isin(old)]
        rows, replaced = filing_metrics.overlay(rows, metrics, only)
        log.info(f"Using filing-based {', '.join(only or filing_metrics.COLUMNS)} for {replaced} companies")

    changed = []
    for row, score in zip(rows, rescore_rows(rows)):
        if row.get("composite_score") != score.composite or row.get("score_coverage") != score.coverage:
            changed.append({**row, "composite_score": score.composite, "score_coverage": score.coverage})

    log.info(f"{len(rows)} stocks checked, {len(changed)} scores changed")
    store.upsert_stocks(changed)
