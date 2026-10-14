"""
Market questions answered from a list of stocks: screening, movers, sector
moves, breadth, search, peers and score breakdowns.

Pure functions over market.Stock — no I/O — so they are easy to test and the
API routes stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from .market import Stock
from .scoring import COLUMN_FOR_METRIC, WEIGHTS, metric_score
from .sectors import SECTOR_LABELS

# Market-cap bands in ₹ crore, roughly matching SEBI's large/mid/small split.
CAP_BANDS: dict[str, tuple[float, float]] = {
    "large": (100_000, float("inf")),
    "mid": (30_000, 100_000),
    "small": (0, 30_000),
}

# Movers are limited to companies worth at least this much, so illiquid
# micro-caps with 20% circuit moves don't crowd out meaningful names.
MOVER_MIN_CAP = 10_000

SORT_FIELDS = {"score", "market_cap", "change_pct", "pe", "roe", "de", "name"}
ASCENDING_BY_DEFAULT = {"pe", "de", "name"}


# ── Screening ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScreenFilters:
    sector: str | None = None
    cap: str | None = None  # "large" | "mid" | "small"
    min_score: float | None = None
    max_pe: float | None = None
    min_roe: float | None = None
    max_de: float | None = None
    sort: str = "score"
    descending: bool | None = None  # None = the natural direction for `sort`


def screen(stocks: list[Stock], f: ScreenFilters) -> list[Stock]:
    """Stocks passing every filter, sorted. Stocks without a price are excluded."""

    def keep(s: Stock) -> bool:
        if s.price is None:
            return False
        if f.sector and s.sector != f.sector:
            return False
        if f.cap:
            lo, hi = CAP_BANDS[f.cap]
            if s.market_cap is None or not lo <= s.market_cap < hi:
                return False
        if f.min_score is not None and (s.score is None or s.score < f.min_score):
            return False
        if f.max_pe is not None and (s.pe is None or s.pe <= 0 or s.pe > f.max_pe):
            return False
        if f.min_roe is not None and (s.roe is None or s.roe < f.min_roe):
            return False
        if f.max_de is not None and (s.de is None or s.de > f.max_de):
            return False
        return True

    rows = [s for s in stocks if keep(s)]
    descending = f.descending if f.descending is not None else f.sort not in ASCENDING_BY_DEFAULT

    if f.sort == "name":
        return sorted(rows, key=lambda s: s.name.lower(), reverse=descending)
    # Missing values always sort last, whichever the direction.
    present = [s for s in rows if getattr(s, f.sort) is not None]
    missing = [s for s in rows if getattr(s, f.sort) is None]
    return sorted(present, key=lambda s: getattr(s, f.sort), reverse=descending) + missing


# ── Market overview ──────────────────────────────────────────────────────────


def movers(stocks: list[Stock], count: int = 5) -> dict[str, list[Stock]]:
    liquid = [s for s in stocks if s.change_pct is not None and (s.market_cap or 0) >= MOVER_MIN_CAP]
    ranked = sorted(liquid, key=lambda s: s.change_pct, reverse=True)
    return {
        "gainers": [s for s in ranked[:count] if s.change_pct > 0],
        "losers": [s for s in reversed(ranked[-count:]) if s.change_pct < 0],
    }


def breadth(stocks: list[Stock]) -> dict[str, int]:
    changes = [s.change_pct for s in stocks if s.change_pct is not None]
    return {
        "advancers": sum(1 for c in changes if c > 0),
        "decliners": sum(1 for c in changes if c < 0),
        "unchanged": sum(1 for c in changes if c == 0),
    }


def sector_moves(stocks: list[Stock], min_members: int = 3) -> list[dict]:
    """Market-cap-weighted day change per sector, strongest first."""
    groups: dict[str, dict] = {}
    for s in stocks:
        if s.change_pct is None or not s.market_cap or s.sector == "general":
            continue
        g = groups.setdefault(s.sector, {"weighted": 0.0, "cap": 0.0, "up": 0, "down": 0})
        g["weighted"] += s.change_pct * s.market_cap
        g["cap"] += s.market_cap
        g["up"] += s.change_pct > 0
        g["down"] += s.change_pct < 0
    result = [
        {
            "sector": code,
            "label": SECTOR_LABELS.get(code, code),
            "change_pct": round(g["weighted"] / g["cap"], 2),
            "advancers": g["up"],
            "decliners": g["down"],
        }
        for code, g in groups.items()
        if g["up"] + g["down"] >= min_members
    ]
    return sorted(result, key=lambda r: r["change_pct"], reverse=True)


def top_scored(stocks: list[Stock], count: int = 10, min_market_cap: float = 30_000) -> list[Stock]:
    eligible = [s for s in stocks if s.score is not None and (s.market_cap or 0) >= min_market_cap]
    return sorted(eligible, key=lambda s: s.score, reverse=True)[:count]


# ── Single stock ─────────────────────────────────────────────────────────────


def search(stocks: list[Stock], query: str, limit: int = 8) -> list[Stock]:
    """Symbol or name match; exact symbol first, then prefixes, then substrings; ties by market cap."""
    q = query.strip().upper()
    if not q:
        return []

    def rank(s: Stock) -> int | None:
        name = s.name.upper()
        if s.symbol == q:
            return 0
        if s.symbol.startswith(q):
            return 1
        if name.startswith(q):
            return 2
        if q in s.symbol or q in name:
            return 3
        return None

    ranked = [(r, s) for s in stocks if (r := rank(s)) is not None]
    ranked.sort(key=lambda pair: (pair[0], -(pair[1].market_cap or 0)))
    return [s for _, s in ranked[:limit]]


def peers(stocks: list[Stock], stock: Stock, count: int = 6) -> list[Stock]:
    """The largest companies in the same sector, always including `stock` itself."""
    if stock.sector == "general":
        return []
    same = sorted(
        (s for s in stocks if s.sector == stock.sector and s.price is not None and s.market_cap),
        key=lambda s: s.market_cap,
        reverse=True,
    )[:count]
    if all(s.symbol != stock.symbol for s in same):
        same = same[: count - 1] + [stock]
    return same


def score_breakdown(stock: Stock) -> list[dict]:
    """
    How each metric contributed: its 0–100 sub-score, its effective weight after
    re-normalising for missing metrics, and the points it earned. Points sum to the score.
    """
    values = {
        "pe": stock.pe,
        "roe": stock.roe,
        "de": stock.de,
        "margin": stock.margin,
        "promoter": stock.promoter,
        "cagr": stock.cagr,
    }
    known = {k: v for k, v in values.items() if v is not None}
    total_weight = sum(WEIGHTS[k] for k in known) or 1
    parts = []
    for key, value in known.items():
        sub = round(metric_score(key, value, stock.sector), 1)  # same rounding as scoring.score_stock
        weight = WEIGHTS[key] / total_weight
        parts.append(
            {
                "metric": key,
                "column": COLUMN_FOR_METRIC[key],
                "value": value,
                "score": round(sub, 1),
                "weight": round(weight, 4),
                "points": round(sub * weight, 1),
            }
        )
    return parts
