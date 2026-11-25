"""
Dividends and capital actions for the company page, from NSE's corporate actions
(clean/corporate_actions) — written to backend/data/dividends.json, which the API serves.

    python -m stocksense dividends-export

Per company: dividend per share for each of the last five fiscal years (April–March, by
ex-date), the trailing twelve months, how many years in a row it has paid, and its last
splits, bonuses, rights issues and demergers. Amounts are per share as declared (not
adjusted for later splits — the actions list says when one happened).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import DATA_DIR

OUTPUT = DATA_DIR / "dividends.json"
YEARS = 5
ACTIONS = 6
CAPITAL_KINDS = ("split", "bonus", "bonus_split", "rights", "restructuring", "consolidation")


def _fy(d: date) -> int:
    return d.year + 1 if d.month > 3 else d.year


def build(actions: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    a = actions.dropna(subset=["ex_date"]).copy()
    a["ex_date"] = pd.to_datetime(a["ex_date"]).dt.date
    a = a[a["ex_date"] <= today]  # declared but not yet ex isn't paid history
    current_fy = _fy(today)
    first_fy = _fy(a["ex_date"].min()) + 1 if len(a) else current_fy  # first fiscal year the data fully covers
    companies = {}
    for symbol, g in a.groupby("symbol"):
        div = g[(g["kind"] == "dividend") & g["dividend"].notna()]
        caps = g[g["kind"].isin(CAPITAL_KINDS)].sort_values("ex_date").tail(ACTIONS)
        if div.empty and caps.empty:
            continue
        by_year = div.assign(fy=div["ex_date"].map(_fy)).groupby("fy")["dividend"].sum()
        years = [{"fiscal_year": int(fy), "per_share": round(float(by_year.get(fy, 0.0)), 2)}
                 for fy in range(current_fy - YEARS, current_fy)]
        streak = 0
        for fy in range(current_fy - 1, first_fy - 1, -1):
            if by_year.get(fy, 0) > 0:
                streak += 1
            else:
                break
        ttm = div[div["ex_date"] > today - timedelta(days=365)]["dividend"].sum()
        companies[symbol] = {
            "years": years,
            "ttm_per_share": round(float(ttm), 2),
            "paid_years_in_a_row": streak,
            # The streak runs back to where the data starts, so the real one may be longer.
            "streak_since_data_start": streak > 0 and streak == current_fy - first_fy,
            "data_from_fiscal_year": first_fy,
            "last_dividend": (None if div.empty else
                              {"ex_date": div["ex_date"].max().isoformat(),
                               "per_share": round(float(div.loc[div["ex_date"].idxmax(), "dividend"]), 2)}),
            "capital_actions": [{"ex_date": r.ex_date.isoformat(), "kind": r.kind, "subject": r.subject}
                                for r in caps.itertuples()],
        }
    return {"generated": today.isoformat(), "source": "NSE corporate actions", "companies": companies}


def note(entry: dict | None, price: float | None = None) -> str | None:
    """One line a beginner can read: the habit, and the yield at today's price."""
    if not entry:
        return None
    streak, ttm = entry.get("paid_years_in_a_row", 0), entry.get("ttm_per_share") or 0
    if ttm <= 0 and streak == 0:
        return "No dividends in recent years: profits are kept in the business (common for growing companies)."
    if entry.get("streak_since_data_start") and streak >= 2:
        first = [f"Paid a dividend every year since FY{entry['data_from_fiscal_year']} (as far back as this data goes)."]
    else:
        first = None
    parts = first or [f"Paid a dividend every year for the last {streak} years." if streak >= 2 else
             "Paid a dividend last year." if streak == 1 else "No dividend in the last full year."]
    if ttm > 0:
        line = f"₹{ttm:g} per share over the past 12 months"
        if price and price > 0:
            line += f", a {100 * ttm / price:.1f}% yield at ₹{price:,.0f}"
        parts.append(line + ".")
    return " ".join(parts)


def write(lake, output: Path = OUTPUT) -> dict:
    doc = build(lake.query("select symbol, ex_date, kind, dividend, subject from corporate_actions"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return doc
