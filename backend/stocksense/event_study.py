"""
Event study engine (PLAN.md M3.1) — what Indian sectors historically did after
events like a crude spike, a sharp rupee fall, a global risk-off day or a
conflict flare-up. No machine learning: find every past occurrence, measure each
sector's return in excess of NIFTY 50 over the next 1, 3 and 10 trading days,
and summarise with sample sizes and bootstrap confidence intervals.

Timing, so nothing looks into the future:
  • A signal on day s (a macro close, or a GDELT file — what was known by the end
    of day s) is measured from the Indian close on the last trading day ≤ s.
  • Macro series close after the Indian market, so the reaction is in the
    following sessions, which is what the 1/3/10-day windows measure.
  • News spikes are scored against the *previous* 90 days only.
  • Repeat signals within 10 trading days count once (the first), so one
    episode isn't counted many times.

Read the output as "historically, after events like this, X tended to…", never
as a forecast or a recommendation (PLAN.md §1.6). Every figure comes with n.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

HORIZONS = (1, 3, 10)
DECLUSTER_DAYS = 10
MIN_EVENTS = 5  # below this a sector/horizon cell isn't reported
BOOTSTRAP_SAMPLES = 2000


# ── event detection ─────────────────────────────────────────────────────────

def threshold_dates(series: pd.Series, threshold: float, *, change: str = "pct", periods: int = 1) -> pd.DatetimeIndex:
    """
    Days where the series moved by at least `threshold` over `periods` days.
    change="pct": relative change (0.05 = +5%); change="diff": absolute change.
    A negative threshold looks for falls of at least that size.
    """
    s = series.dropna()
    move = s.pct_change(periods) if change == "pct" else s.diff(periods)
    hit = move >= threshold if threshold >= 0 else move <= threshold
    return s.index[hit.fillna(False).to_numpy()]


def spike_dates(series: pd.Series, *, z: float = 3.0, window: int = 90, min_periods: int = 60) -> pd.DatetimeIndex:
    """Days where the value is `z` standard deviations above its trailing `window`-day mean (today excluded)."""
    s = series.dropna()
    past = s.shift(1).rolling(window, min_periods=min_periods)
    score = (s - past.mean()) / past.std()
    return s.index[(score >= z).fillna(False).to_numpy()]


def to_base_dates(signals: pd.DatetimeIndex, calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Each signal day → the last market day on or before it (signals before the calendar are dropped)."""
    pos = calendar.searchsorted(signals, side="right") - 1
    return pd.DatetimeIndex(calendar[pos[pos >= 0]]).unique()


def decluster(base_dates: pd.DatetimeIndex, calendar: pd.DatetimeIndex, gap: int = DECLUSTER_DAYS) -> pd.DatetimeIndex:
    """Keep the first event of each episode: later ones within `gap` market days are dropped."""
    kept, last = [], None
    for d in sorted(base_dates):
        i = calendar.get_loc(d)
        if last is None or i - last > gap:
            kept.append(d)
            last = i
    return pd.DatetimeIndex(kept)


# ── returns ─────────────────────────────────────────────────────────────────

def forward_excess(closes: pd.DataFrame, bench: pd.Series, horizons=HORIZONS) -> dict[int, pd.DataFrame]:
    """
    For every base day and sector: return over the next h market days minus the
    benchmark's over the same days, in percent. Index = base day, columns = sectors.
    """
    out = {}
    for h in horizons:
        sector_ret = closes.shift(-h) / closes - 1
        bench_ret = bench.shift(-h) / bench - 1
        out[h] = sector_ret.sub(bench_ret, axis=0) * 100
    return out


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, samples: int = BOOTSTRAP_SAMPLES,
                 level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap confidence interval for the mean."""
    means = rng.choice(values, size=(samples, len(values)), replace=True).mean(axis=1)
    tail = (1 - level) / 2
    return float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))


def summarise(excess: dict[int, pd.DataFrame], base_dates: pd.DatetimeIndex, seed: int = 7) -> list[dict]:
    """
    One row per sector and horizon: n, mean / median excess return, hit rate (share
    of events with a positive excess return), 95% CI of the mean, and the baseline:
    the average excess return over *all* days in that sector's history. `notable`
    marks cells whose CI excludes the baseline.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for h, table in excess.items():
        for sector in table.columns:
            col = table[sector]
            vals = col.reindex(base_dates).dropna().to_numpy()
            if len(vals) < MIN_EVENTS:
                continue
            baseline = float(col.dropna().mean())
            lo, hi = bootstrap_ci(vals, rng)
            rows.append({
                "sector": sector, "horizon_days": h, "n": int(len(vals)),
                "mean_excess_pct": round(float(vals.mean()), 3),
                "median_excess_pct": round(float(np.median(vals)), 3),
                "hit_rate": round(float((vals > 0).mean()), 3),
                "ci_low_pct": round(lo, 3), "ci_high_pct": round(hi, 3),
                "baseline_pct": round(baseline, 3),
                "notable": bool(lo > baseline or hi < baseline),
            })
    return rows


# ── event catalogue ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EventType:
    code: str
    label: str
    rule: str  # how it's detected, in words, for the API and UI
    detect: Callable[[dict[str, pd.Series]], pd.DatetimeIndex]
    evidence: str | None = None  # which GDELT filter gives evidence links (see jobs/event_study.py)


def _series(inputs: dict[str, pd.Series], name: str) -> pd.Series:
    s = inputs.get(name)
    return s if s is not None else pd.Series(dtype="float64")


EVENT_TYPES: list[EventType] = [
    EventType("crude_spike", "Crude oil spike", "Brent up 5% or more in a day",
              lambda x: threshold_dates(_series(x, "BRENT"), 0.05)),
    EventType("crude_crash", "Crude oil crash", "Brent down 5% or more in a day",
              lambda x: threshold_dates(_series(x, "BRENT"), -0.05)),
    EventType("rupee_fall", "Sharp rupee fall", "USD/INR up 1% or more in a day",
              lambda x: threshold_dates(_series(x, "USDINR"), 0.01)),
    EventType("rupee_rally", "Sharp rupee rally", "USD/INR down 1% or more in a day",
              lambda x: threshold_dates(_series(x, "USDINR"), -0.01)),
    EventType("global_risk_off", "Global risk-off day", "S&P 500 down 3% or more in a day",
              lambda x: threshold_dates(_series(x, "SP500"), -0.03)),
    EventType("vix_jump", "US volatility jump", "CBOE VIX up 30% or more in a day",
              lambda x: threshold_dates(_series(x, "US_VIX"), 0.30)),
    EventType("us_yield_jump", "US yield jump", "US 10-year yield up 0.15 points or more in a day",
              lambda x: threshold_dates(_series(x, "US10Y"), 0.15, change="diff")),
    EventType("gold_spike", "Gold spike", "Gold up 3% or more in a day",
              lambda x: threshold_dates(_series(x, "GOLD"), 0.03)),
    EventType("global_conflict", "Global conflict flare-up",
              "Share of world news coverage about armed conflict 3σ above its 90-day norm",
              lambda x: spike_dates(_series(x, "conflict_share")), evidence="conflict"),
    EventType("india_tension", "India security tension",
              "Share of coverage about hostile acts involving India 3σ above its 90-day norm",
              lambda x: spike_dates(_series(x, "india_hostile_share")), evidence="india"),
    EventType("middle_east_conflict", "Middle East conflict flare-up",
              "Share of coverage about armed conflict in the Middle East 3σ above its 90-day norm",
              lambda x: spike_dates(_series(x, "mideast_share")), evidence="mideast"),
    EventType("sanctions", "Sanctions and cut ties",
              "Share of coverage about sanctions, embargoes and cutting relations 3σ above its 90-day norm",
              lambda x: spike_dates(_series(x, "sanctions_share")), evidence="sanctions"),
]


def run(closes: pd.DataFrame, bench: pd.Series, inputs: dict[str, pd.Series],
        event_types: list[EventType] = EVENT_TYPES) -> list[dict]:
    """
    closes: market-day index × sector columns (adjusted levels); bench: NIFTY 50 on
    the same index; inputs: named daily series the detectors read. Returns one dict
    per event type with its occurrences and per-sector summary.
    """
    calendar = pd.DatetimeIndex(closes.index)
    excess = forward_excess(closes, bench)
    results = []
    for et in event_types:
        signals = et.detect(inputs)
        bases = decluster(to_base_dates(pd.DatetimeIndex(signals), calendar), calendar)
        # An event needs at least the 1-day window to have happened.
        bases = bases[bases < calendar[-1]] if len(calendar) else bases
        results.append({
            "code": et.code, "label": et.label, "rule": et.rule,
            "occurrences": int(len(bases)),
            "first": str(bases.min().date()) if len(bases) else None,
            "last": str(bases.max().date()) if len(bases) else None,
            "dates": [str(d.date()) for d in bases],
            "sectors": summarise(excess, bases),
        })
    return results
