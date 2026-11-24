"""
The StockSense score: six fundamentals, each mapped to 0–100, then weighted.

These are the fixed curves: the published score blends them 30/70 with each
company's standing among its sector peers (stocksense/blend.py).

    metric             weight   curve (0 = worst, 100 = best)
    P/E                 20%     lower is better; banks use a tighter band; new-age gets a flat 40
    ROE                 20%     0% → 0, 50%+ → 100
    Debt / Equity       15%     lower is better; banks are expected to carry leverage
    Net margin          20%     0% → 0, 38%+ → 100
    Promoter holding    10%     0% → 0, 80%+ → 100
    Revenue CAGR (3y)   15%     0% → 0, 55%+ → 100

Missing metrics are skipped and the remaining weights are re-normalised, so a
stock is not punished for data Yahoo doesn't publish. A composite is only
produced when at least MIN_METRICS metrics are known AND at least one
balance-sheet metric (ROE or D/E) is among them — Yahoo omits both when a
company's equity is negative, and scoring on profit metrics alone would then
rate a distressed company highly.

A P/E below 4 almost always comes from a one-off gain (asset sale, write-back),
so it scores a neutral 50 instead of the maximum.
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
BALANCE_SHEET = {"roe", "de"}
SUSPICIOUS_PE = 4

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
        if value < SUSPICIOUS_PE:  # usually inflated by one-off profits
            return 50.0
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
    if len(parts) < MIN_METRICS or not BALANCE_SHEET & parts.keys():
        return ScoreResult(composite=None, parts=parts, coverage=len(parts))

    total_weight = sum(WEIGHTS[key] for key in parts)
    composite = sum(parts[key] * WEIGHTS[key] for key in parts) / total_weight
    return ScoreResult(composite=round(composite), parts=parts, coverage=len(parts))


# ── teaching layer: what each metric means and what range is healthy ─────────
#
# The ranges are not a separate opinion: they're the scoring curves above read
# backwards. "Strong" is where a metric scores STRONG_SCORE or more, "fair" from
# FAIR_SCORE up, "weak" below — so an explanation can never disagree with the score.

STRONG_SCORE = 70
FAIR_SCORE = 40

GUIDE: dict[str, dict] = {
    "pe": {"label": "P/E ratio", "unit": "x", "higher_is_better": False,
           "measures": "how many rupees investors pay for each rupee of yearly profit — lower means cheaper"},
    "roe": {"label": "Return on equity", "unit": "%", "higher_is_better": True,
            "measures": "profit earned each year on every ₹100 of shareholders' money"},
    "de": {"label": "Debt to equity", "unit": "x", "higher_is_better": False,
           "measures": "how much the company has borrowed for every rupee shareholders own"},
    "margin": {"label": "Net profit margin", "unit": "%", "higher_is_better": True,
               "measures": "profit kept from every ₹100 of sales after all costs and tax"},
    "promoter": {"label": "Promoter holding", "unit": "%", "higher_is_better": True,
                 "measures": "share of the company owned by its founders/promoters — their own money at stake"},
    "cagr": {"label": "Revenue growth (3-yr CAGR)", "unit": "%", "higher_is_better": True,
             "measures": "how fast sales have grown each year over the last three years"},
}


def _value_at(metric: str, sector: str, score: float) -> float | None:
    """The metric value that scores `score` on its curve (None if the metric isn't judged for this sector)."""
    s = score / 100
    if metric == "pe":
        if sector in NEWAGE_SECTORS:
            return None
        return 8 + (1 - s) * (30 if sector in BANK_SECTORS else 42)
    if metric == "de":
        return 3 + (1 - s) * 12 if sector in BANK_SECTORS else (1 - s) * 3.5
    full = {"roe": 50, "margin": 38, "promoter": 80, "cagr": 55}[metric]
    return s * full


def _fmt(metric: str, value: float) -> str:
    if metric == "de":
        return f"{value:.1f}"
    return f"{value:.0f}%" if GUIDE[metric]["unit"] == "%" else f"{value:.0f}"


def verdict_for(score: float) -> str:
    return "strong" if score >= STRONG_SCORE else "fair" if score >= FAIR_SCORE else "weak"


def healthy_range(metric: str, sector: str) -> dict | None:
    """
    Strong / fair / weak bands for a metric in a sector, as numbers and as one line
    of text. None when the metric isn't judged for that sector (P/E for new-age).
    """
    strong, fair = _value_at(metric, sector, STRONG_SCORE), _value_at(metric, sector, FAIR_SCORE)
    if strong is None or fair is None:
        return None
    bare = lambda v: _fmt(metric, v).rstrip("%")  # noqa: E731 — "20–35%", not "20%–35%"
    if GUIDE[metric]["higher_is_better"]:
        text = (f"Strong: {_fmt(metric, strong)} or more · Fair: {bare(fair)}–{_fmt(metric, strong)}"
                f" · Weak: below {_fmt(metric, fair)}")
    else:
        text = (f"Strong: {_fmt(metric, strong)} or less · Fair: {bare(strong)}–{_fmt(metric, fair)}"
                f" · Weak: above {_fmt(metric, fair)}")
    return {"strong_from": round(strong, 2), "fair_from": round(fair, 2),
            "higher_is_better": GUIDE[metric]["higher_is_better"], "text": text}


def explain(metric: str, value: float, sector: str) -> dict:
    """
    Plain-language reading of one metric for a beginner: what it measures, how this
    company's value compares with the healthy range for its sector, and any caveat.
    """
    guide = GUIDE[metric]
    score = metric_score(metric, value, sector)
    bands = healthy_range(metric, sector)
    note = None
    if metric == "pe" and sector in NEWAGE_SECTORS:
        verdict, note = "not judged", "Young platform companies often have little or no profit yet, so P/E isn't used for them."
    elif metric == "pe" and value <= 0:
        verdict, note = "weak", "The company made a loss, so P/E has no meaning here."
    elif metric == "pe" and value < SUSPICIOUS_PE:
        verdict, note = "unclear", "A P/E this low usually comes from a one-off gain (like selling an asset), not lasting profit."
    else:
        verdict = verdict_for(score)
    if metric == "de" and sector in BANK_SECTORS:
        note = "Banks and NBFCs lend borrowed money as their business, so higher debt is normal for them."
    if metric == "pe" and sector in BANK_SECTORS and note is None:
        note = "Lenders are valued on a tighter P/E band than other companies."
    return {
        "label": guide["label"],
        "measures": guide["measures"],
        "verdict": verdict,
        "healthy_range": bands["text"] if bands else None,
        "note": note,
    }


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
