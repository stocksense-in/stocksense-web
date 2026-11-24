"""
The StockSense score as published: 70% "how the company compares with its sector
peers" + 30% the fixed curves in scoring.py (decided 25 Nov 2026, PLAN.md).

Fixed curves alone misjudge whole sectors — they inflated NBFCs by ~12 points and
penalised industrials (ml/reports/score-comparison-2026-11-24.md). A purely relative
score would make every sector average ~50 and hide that some industries are better
businesses, so 30% of the absolute view stays.

Per metric:
    peer part      share of sector peers this company beats (direction-aware; whole
                   market when the sector has fewer than benchmarks.MIN_PEERS values)
    absolute part  scoring.metric_score (the fixed curve)
    sub-score      RELATIVE_WEIGHT × peer + (1 − RELATIVE_WEIGHT) × absolute

Special cases keep their meaning: a loss-making P/E scores 0 in both parts, a P/E
below 4 (usually one-off gains) stays a neutral 50, and new-age companies' P/E stays
on its flat value. Weights, re-normalisation and coverage rules are scoring.py's.

Because the peer part needs every stock, scores are computed for the whole universe
at once (`rescore_rows`, used by `python -m stocksense rescore`).
"""

from __future__ import annotations

from types import SimpleNamespace

from . import benchmarks as bm
from .scoring import (BALANCE_SHEET, COLUMN_FOR_METRIC, MIN_METRICS, NEWAGE_SECTORS, SUSPICIOUS_PE, WEIGHTS,
                      ScoreResult, metric_score)

RELATIVE_WEIGHT = 0.7


def metric_parts(stock, benches: bm.Benchmarks) -> dict[str, dict]:
    """{metric: {"peer": 0–100 or None, "absolute": 0–100, "score": blended 0–100}} for known metrics."""
    parts = {}
    for metric in WEIGHTS:
        value = getattr(stock, metric)
        if value is None:
            continue
        absolute = metric_score(metric, value, stock.sector)
        peer = None
        if metric == "pe" and stock.sector in NEWAGE_SECTORS:
            pass  # flat value on the curve; not ranked against peers
        elif metric == "pe" and value <= 0:
            peer = 0.0  # loss-making: no P/E to compare
        elif metric == "pe" and value < SUSPICIOUS_PE:
            peer = 50.0  # one-off profits make it look cheap; stay neutral
        else:
            ctx = bm.peer_context(metric, value, stock.sector, benches)
            if ctx and ctx["better_than_pct"] is not None:
                peer = float(ctx["better_than_pct"])
        blended = absolute if peer is None else RELATIVE_WEIGHT * peer + (1 - RELATIVE_WEIGHT) * absolute
        parts[metric] = {"peer": None if peer is None else round(peer, 1), "absolute": round(absolute, 1),
                         "score": round(blended, 1)}
    return parts


def blended_score(stock, benches: bm.Benchmarks) -> ScoreResult:
    """The published composite for one stock, given benchmarks over the whole universe."""
    parts = {k: v["score"] for k, v in metric_parts(stock, benches).items()}
    if len(parts) < MIN_METRICS or not BALANCE_SHEET & parts.keys():
        return ScoreResult(composite=None, parts=parts, coverage=len(parts))
    total = sum(WEIGHTS[k] for k in parts)
    composite = sum(parts[k] * WEIGHTS[k] for k in parts) / total
    return ScoreResult(composite=round(composite), parts=parts, coverage=len(parts))


def as_stock(row: dict) -> SimpleNamespace:
    """A `stocks` table row as the attribute object benchmarks and blend expect."""
    return SimpleNamespace(sector=row.get("sector") or "general",
                           **{metric: row.get(column) for metric, column in COLUMN_FOR_METRIC.items()})


def rescore_rows(rows: list[dict]) -> list[ScoreResult]:
    """Blended scores for every row, with peer benchmarks built from the same rows."""
    stocks = [as_stock(r) for r in rows]
    benches = bm.build(stocks)
    return [blended_score(s, benches) for s in stocks]
