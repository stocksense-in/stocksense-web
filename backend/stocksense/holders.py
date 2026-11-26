"""
Who owns the company — promoter holding over time and promoter pledges, from the
shareholding filings (clean/shareholding, clean/pledges; M1.3) — written to
backend/data/holders.json, which the API serves. The public API never reads the lake.

    python -m stocksense holders-export

Also the two plain-language notes the score breakdown shows on the promoter metric:
a pledge warning (pledged shares can be sold by lenders if the price falls) and how
the promoters' stake has moved over the past year.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from .config import DATA_DIR

OUTPUT = DATA_DIR / "holders.json"
QUARTERS = 12
PLEDGE_WARN = 10.0   # % of the promoters' stake pledged: worth knowing
PLEDGE_HIGH = 25.0   # a real risk in a falling market
SPLIT = ("fii_pct", "dii_pct", "mutual_funds_pct", "insurance_pct", "small_retail_pct", "government_pct")
STAKE_MOVE = 2.0     # percentage points over a year that count as a change
LONG_DRIFT = 3.0     # percentage points over the whole history shown that count as a slow trend


def _num(value, digits: int = 2):
    return None if value is None or pd.isna(value) else round(float(value), digits)


def build(shareholding: pd.DataFrame, pledges: pd.DataFrame | None = None, today: date | None = None) -> dict:
    sh = shareholding.copy()
    sh["quarter_end"] = pd.to_datetime(sh["quarter_end"]).dt.date
    latest_pledge = {}
    if pledges is not None and len(pledges):
        p = pledges.copy()
        p["fetched"] = pd.to_datetime(p["fetched"]).dt.date
        latest_pledge = p.sort_values("fetched").groupby("symbol").last().to_dict("index")
    companies = {}
    for symbol, g in sh.sort_values("quarter_end").groupby("symbol"):
        quarters = [{"quarter_end": r["quarter_end"].isoformat(), "promoter_pct": _num(r["promoter_pct"]),
                     "public_pct": _num(r["public_pct"]), "employee_trusts_pct": _num(r["employee_trusts_pct"]),
                     **{c: _num(r.get(c)) for c in SPLIT}}
                    for r in g.tail(QUARTERS).to_dict("records")]
        entry = {"quarters": quarters, "pledge": None}
        pl = latest_pledge.get(symbol)
        if pl:
            entry["pledge"] = {"as_of": pl["fetched"].isoformat(),
                               "pledged_pct_of_promoter": _num(pl.get("pledged_pct_of_promoter")),
                               "pledged_pct_of_total": _num(pl.get("pledged_pct_of_total")),
                               "all_pledges_pct_of_total": _num(pl.get("all_pledges_pct_of_total"))}
        companies[symbol] = entry
    return {"generated": (today or date.today()).isoformat(),
            "source": "Shareholding patterns and pledge disclosures filed with NSE", "companies": companies}


def pledge_warning(entry: dict | None) -> str | None:
    """A guardrail for the promoter metric when promoters have pledged much of their stake."""
    pledged = ((entry or {}).get("pledge") or {}).get("pledged_pct_of_promoter")
    if pledged is None or pledged < PLEDGE_WARN:
        return None
    if pledged >= PLEDGE_HIGH:
        return (f"Promoters have pledged {pledged:.0f}% of their stake. If the share price falls, lenders can sell "
                "those shares, which can push the price down further.")
    return (f"Promoters have pledged {pledged:.0f}% of their stake as loan security — worth watching: lenders can "
            "sell pledged shares if the price falls a lot.")


def trend_note(entry: dict | None) -> str | None:
    """How the promoters' stake moved over the past year (latest pattern vs four quarters earlier)."""
    quarters = [q for q in (entry or {}).get("quarters", []) if q.get("promoter_pct") is not None]
    if len(quarters) < 5:
        return None
    now, then = quarters[-1], quarters[-5]
    if now["promoter_pct"] < 1:
        return "No promoter group: the company is owned by institutions and the public."
    move = now["promoter_pct"] - then["promoter_pct"]
    if abs(move) < STAKE_MOVE:
        first = quarters[0]
        years = (len(quarters) - 1) / 4
        drift = now["promoter_pct"] - first["promoter_pct"]
        if years >= 2 and abs(drift) >= LONG_DRIFT:
            way = "up" if drift > 0 else "down"
            return (f"Steady over the past year ({now['promoter_pct']:.1f}%), but {way} from "
                    f"{first['promoter_pct']:.1f}% {years:.0f} years ago.")
        return f"Promoters' stake has held steady over the past year ({now['promoter_pct']:.1f}%)."
    direction = "raised" if move > 0 else "cut"
    return (f"Promoters {direction} their stake from {then['promoter_pct']:.1f}% to {now['promoter_pct']:.1f}% "
            "over the past year." + ("" if move > 0 else " Selling can be routine (funding, estate, a stake sale "
                                     "to institutions), but a steady decline is worth understanding."))


def write(lake, output: Path = OUTPUT) -> dict:
    present = set(lake.datasets())
    doc = build(lake.query("select * from shareholding"),
                lake.query("select * from pledges") if "pledges" in present else None)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")  # compact: ~1,400+ companies
    return doc
