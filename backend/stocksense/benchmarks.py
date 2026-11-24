"""
Context for every metric: what's normal for this kind of company, right now.

There's no single "healthy range" for a metric — median P/E runs from ~8 for energy
companies to 50+ for FMCG; lenders carry far more debt than IT firms. So each metric
is read in layers (PLAN.md, rule 6 "Teach, don't tip"):

  1. Sector peers (`build`, `peer_context`) — quartiles of the metric across the
     company's sector, from the whole stock universe. Sectors with fewer than
     MIN_PEERS usable values fall back to the whole market.
  2. Company stage (`stage`, `stage_note`) — a fast-growing company deserves a higher
     P/E than a mature one; a loss-making one can't be judged on P/E at all. P/E is
     also read against growth (P/E ÷ revenue growth, a PEG-style ratio; revenue growth
     stands in for earnings growth, which we don't have yet).
  3. Market and time — the sector's own valuation today against its history; see
     stocksense/valuation.py.

Plus `guardrails`: a few absolute warnings that hold whatever peers do (losses,
heavy debt for a company that isn't a lender).

Pure functions over market.Stock, no I/O.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable
from dataclasses import dataclass

from .scoring import BANK_SECTORS, GUIDE, NEWAGE_SECTORS
from .sectors import SECTOR_LABELS

METRICS = ("pe", "roe", "de", "margin", "promoter", "cagr")
MIN_PEERS = 10
MARKET = "market"
HIGH_GROWTH = 20.0  # % a year of revenue growth
HEAVY_DEBT = 2.0  # debt/equity, for companies that aren't lenders

# Values outside these bounds are data errors or meaningless for comparison
# (a P/E of 900 from near-zero profit), so they're left out of the benchmarks.
_VALID = {
    "pe": (0.0, 300.0),  # losses (P/E ≤ 0) are judged separately, not ranked
    "roe": (-100.0, 150.0),
    "de": (0.0, 40.0),
    "margin": (-100.0, 100.0),
    "promoter": (0.0, 100.0),
    "cagr": (-100.0, 300.0),
}


def _usable(metric: str, value: float | None) -> bool:
    if value is None or not math.isfinite(value):
        return False
    lo, hi = _VALID[metric]
    return lo < value <= hi if metric == "pe" else lo <= value <= hi


@dataclass(frozen=True)
class Benchmark:
    metric: str
    group: str  # sector code, or MARKET
    values: tuple[float, ...]  # sorted

    @property
    def n(self) -> int:
        return len(self.values)

    def quantile(self, q: float) -> float:
        v = self.values
        pos = q * (len(v) - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        return v[lo] + (v[hi] - v[lo]) * (pos - lo)

    def share_below(self, value: float) -> float:
        """Share of peers (0–100) with a lower value; ties count half."""
        lo, hi = bisect.bisect_left(self.values, value), bisect.bisect_right(self.values, value)
        return 100 * (lo + (hi - lo) / 2) / len(self.values)


Benchmarks = dict[tuple[str, str], Benchmark]


def build(stocks: Iterable) -> Benchmarks:
    """Benchmarks per (sector, metric) and per (MARKET, metric) from Stock objects."""
    by_group: dict[tuple[str, str], list[float]] = {}
    for s in stocks:
        for metric in METRICS:
            value = getattr(s, metric)
            if _usable(metric, value):
                by_group.setdefault((s.sector or "general", metric), []).append(value)
                by_group.setdefault((MARKET, metric), []).append(value)
    return {key: Benchmark(key[1], key[0], tuple(sorted(vals))) for key, vals in by_group.items() if vals}


def benchmark_for(benchmarks: Benchmarks, sector: str, metric: str) -> Benchmark | None:
    """The sector's benchmark, or the whole market's when the sector is too small."""
    own = benchmarks.get((sector, metric))
    if own is not None and own.n >= MIN_PEERS:
        return own
    return benchmarks.get((MARKET, metric))


def _fmt(metric: str, value: float) -> str:
    if metric == "de":
        return f"{value:.1f}"
    return f"{value:.0f}%" if GUIDE[metric]["unit"] == "%" else f"{value:.0f}"


def _group_label(group: str) -> str:
    return "all NSE companies" if group == MARKET else f"{SECTOR_LABELS.get(group, group)} companies"


def standing(better_than: float) -> str:
    return ("top quarter" if better_than >= 75 else "above median" if better_than >= 50
            else "below median" if better_than >= 25 else "bottom quarter")


def peer_context(metric: str, value: float | None, sector: str, benchmarks: Benchmarks) -> dict | None:
    """
    Where a value sits among peers: the peer group's quartiles, the share of peers this
    company beats (direction-aware: a lower P/E or debt "beats" a higher one) and a
    one-line reading. None when there's nothing to compare.
    """
    bench = benchmark_for(benchmarks, sector, metric)
    if bench is None or value is None or not math.isfinite(value):
        return None
    p25, median, p75 = bench.quantile(0.25), bench.quantile(0.5), bench.quantile(0.75)
    out = {"group": _group_label(bench.group), "peers": bench.n, "p25": round(p25, 2), "median": round(median, 2),
           "p75": round(p75, 2), "typical_range": f"{_fmt(metric, p25)}–{_fmt(metric, p75)}"}
    if not _usable(metric, value):  # e.g. loss-making P/E: shown with the range, not ranked
        return {**out, "better_than_pct": None, "standing": None,
                "text": f"Typical for {out['group']}: {out['typical_range']} (median {_fmt(metric, median)})."}
    below = bench.share_below(value)
    better = below if GUIDE[metric]["higher_is_better"] else 100 - below
    return {**out, "better_than_pct": round(better), "standing": standing(better),
            "text": (f"Better than {better:.0f}% of {bench.n} {out['group']} on this measure "
                     f"(typical range {out['typical_range']}, median {_fmt(metric, median)}).")}


# ── layer 2: company stage ──────────────────────────────────────────────────

def stage(stock) -> str:
    """'loss-making', 'high growth', 'steady' or 'unknown' — how to read the other metrics."""
    if (stock.pe is not None and stock.pe <= 0) or (stock.margin is not None and stock.margin < 0):
        return "loss-making"
    if stock.cagr is None:
        return "unknown"
    return "high growth" if stock.cagr >= HIGH_GROWTH else "steady"


STAGE_TEXT = {
    "loss-making": "The company is currently making a loss, so profit-based measures like P/E can't be read in the usual way.",
    "high growth": "Sales are growing fast, so investors usually pay a higher P/E than for a mature company.",
    "steady": "A steady business: compare its valuation mostly with mature peers.",
    "unknown": None,
}


def growth_adjusted_pe(stock) -> dict | None:
    """P/E ÷ yearly revenue growth (PEG-style): ~1 or less is cheap for the growth, above 2 is expensive."""
    if stock.pe is None or stock.cagr is None or stock.pe <= 0 or stock.cagr <= 0 or stock.sector in NEWAGE_SECTORS:
        return None
    ratio = stock.pe / stock.cagr
    reading = "cheap for its growth" if ratio <= 1 else "reasonable for its growth" if ratio <= 2 else "expensive for its growth"
    return {"ratio": round(ratio, 2), "reading": reading,
            "text": (f"P/E {stock.pe:.0f} ÷ {stock.cagr:.0f}% yearly sales growth = {ratio:.1f}: {reading} "
                     "(around 1 or less is cheap, above 2 is expensive).")}


def stage_note(metric: str, stock) -> str | None:
    """What the company's stage means for reading this metric."""
    st = stage(stock)
    if metric == "pe":
        if st == "loss-making":
            return STAGE_TEXT[st]
        peg = growth_adjusted_pe(stock)
        if peg and st == "high growth":
            return f"{STAGE_TEXT[st]} {peg['text']}"
        return peg["text"] if peg else None
    if metric == "cagr" and st == "high growth":
        return "Fast growth — check that margins and debt keep up."
    return None


# ── guardrails ──────────────────────────────────────────────────────────────

def guardrails(metric: str, stock) -> str | None:
    """Absolute warnings that hold whatever the peers look like."""
    value = getattr(stock, metric)
    if value is None:
        return None
    if metric == "de" and stock.sector not in BANK_SECTORS and value > HEAVY_DEBT:
        return f"Debt above {HEAVY_DEBT:.0f}× equity is heavy for a company that isn't a lender, whatever its peers carry."
    if metric == "margin" and value < 0:
        return "The company is losing money on its sales."
    if metric == "roe" and value < 0:
        return "Negative ROE: the company lost money for its shareholders this year."
    return None
