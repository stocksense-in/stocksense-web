"""
The StockSense score: six fundamentals, each mapped to 0–100, then weighted.

This is the single source of truth for scoring. The frontend mirrors the same
curves in frontend/lib/scoring.ts — change both together.

    metric             weight   curve (0 = worst, 100 = best)
    P/E                 20%     lower is better; banks use a tighter band; new-age gets a flat 40
    ROE                 20%     0% → 0, 50%+ → 100
    Debt / Equity       15%     lower is better; banks are expected to carry leverage
    Net margin          20%     0% → 0, 38%+ → 100
    Promoter holding    10%     0% → 0, 80%+ → 100
    Revenue CAGR (3y)   15%     0% → 0, 55%+ → 100

Missing metrics are skipped and the remaining weights are re-normalised, so a
stock is not punished for data Yahoo doesn't publish. A composite is only
produced when at least MIN_METRICS metrics are known.
"""

from __future__ import annotations

from dataclasses import dataclass

WEIGHTS: dict[str, float] = {
    "pe": 0.20,
    "roe": 0.20,
    "de": 0.15,
    "margin": 0.20,
    "promoter": 0.10,
    "cagr": 0.15,
}

MIN_METRICS = 4

BANK_SECTORS = {"bank", "nbfc"}
NEWAGE_SECTORS = {"newage"}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def metric_score(metric: str, value: float, sector: str) -> float:
    """Map one raw metric value to 0–100."""
    if metric == "pe":
        if sector in NEWAGE_SECTORS:
            return 40.0
        if value <= 0:  # loss-making: P/E is meaningless, treat as poor
            return 0.0
        band = 30 if sector in BANK_SECTORS else 42
        return _clamp(100 - (value - 8) / band * 100)
    if metric == "roe":
        return _clamp(value / 50 * 100)
    if metric == "de":
        if sector in BANK_SECTORS:
            return _clamp(100 - (value - 3) / 12 * 100)
        return _clamp(100 - value / 3.5 * 100)
    if metric == "margin":
        return _clamp(value / 38 * 100)
    if metric == "promoter":
        return _clamp(value / 80 * 100)
    if metric == "cagr":
        return _clamp(value / 55 * 100)
    raise ValueError(f"Unknown metric: {metric}")


@dataclass(frozen=True)
class ScoreResult:
    composite: int | None
    parts: dict[str, float]
    coverage: int  # how many of the six metrics were available


def score_stock(metrics: dict[str, float | None], sector: str) -> ScoreResult:
    """
    metrics uses the short keys from WEIGHTS: pe, roe, de, margin, promoter, cagr.
    None means "not available".
    """
    parts = {
        key: round(metric_score(key, value, sector), 1)
        for key, value in metrics.items()
        if key in WEIGHTS and value is not None
    }
    if len(parts) < MIN_METRICS:
        return ScoreResult(composite=None, parts=parts, coverage=len(parts))

    total_weight = sum(WEIGHTS[key] for key in parts)
    composite = sum(parts[key] * WEIGHTS[key] for key in parts) / total_weight
    return ScoreResult(composite=round(composite), parts=parts, coverage=len(parts))


# Column names in the `stocks` table ↔ short metric keys used above.
COLUMN_FOR_METRIC = {
    "pe": "pe_ratio",
    "roe": "roe",
    "de": "debt_equity",
    "margin": "net_margin",
    "promoter": "promoter_holding",
    "cagr": "revenue_cagr_3yr",
}


def score_row(row: dict) -> ScoreResult:
    """Score a `stocks` table row (uses the database column names)."""
    metrics = {key: row.get(column) for key, column in COLUMN_FOR_METRIC.items()}
    return score_stock(metrics, row.get("sector") or "general")
