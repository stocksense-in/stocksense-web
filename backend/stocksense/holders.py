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
# From each quarter's pattern, as % of the promoters' own holding: pledges alone (patterns from 2024 on),
# and pledges plus non-disposal undertakings and other encumbrances (every pattern).
PLEDGE_HISTORY = ("promoter_pledged_pct", "promoter_encumbered_pct")
PLEDGE_MOVE = 5.0    # percentage points of the promoters' stake over a year that count as a change
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
                     **{c: _num(r.get(c)) for c in SPLIT + PLEDGE_HISTORY}}
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
    """A guardrail for the promoter metric when promoters have pledged much of their stake: the latest
    pledge position, else the latest quarterly pattern's pledges."""
    pledged = ((entry or {}).get("pledge") or {}).get("pledged_pct_of_promoter")
    if pledged is None:
        quarters = (entry or {}).get("quarters") or []
        pledged = quarters[-1].get("promoter_pledged_pct") if quarters else None
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


def _pct(value: float) -> str:
    return f"{value:.1f}%" if 0 < value < 1 else f"{value:.0f}%"


def _quarter(quarter_end: str) -> str:
    return date.fromisoformat(quarter_end).strftime("%b %Y")


def _pledge_quarters(entry: dict | None) -> list[dict]:
    return [q for q in (entry or {}).get("quarters", [])
            if q.get("promoter_encumbered_pct") is not None and (q.get("promoter_pct") or 0) >= 1]


def pledged_now(entry: dict | None) -> float | None:
    """The share of the promoters' stake pledged: the latest pledge position, else the latest pattern's
    pledged-or-encumbered figure; 0 for a company with no promoter group; None when unknown."""
    snapshot = ((entry or {}).get("pledge") or {}).get("pledged_pct_of_promoter")
    if snapshot is not None:
        return snapshot
    quarters = (entry or {}).get("quarters") or []
    if quarters and quarters[-1].get("promoter_pct") is not None and quarters[-1]["promoter_pct"] < 1:
        return 0.0
    pattern = _pledge_quarters(entry)
    return pattern[-1]["promoter_encumbered_pct"] if pattern else None


def pledges_rising(entry: dict | None) -> bool:
    """Promoters pledged or tied up PLEDGE_MOVE points more of their stake over the past year."""
    quarters = _pledge_quarters(entry)
    if len(quarters) < 2:
        return False
    now = quarters[-1]
    year_ago = [q for q in quarters if q["quarter_end"] <= _year_before(now["quarter_end"])]
    return bool(year_ago) and now["promoter_encumbered_pct"] - year_ago[-1]["promoter_encumbered_pct"] >= PLEDGE_MOVE


def pledge_note(entry: dict | None) -> str | None:
    """How much of the promoters' stake is pledged or otherwise tied up (the pattern's "pledged or
    otherwise encumbered"), and how that moved over the past year. None without the history."""
    quarters = _pledge_quarters(entry)
    if len(quarters) < 2:
        return None
    now = quarters[-1]
    if max(q["promoter_encumbered_pct"] for q in quarters) == 0:
        return (f"Promoters haven't pledged or otherwise tied up any of their shares in any quarter since "
                f"{_quarter(quarters[0]['quarter_end'])}.")
    year_ago = [q for q in quarters if q["quarter_end"] <= _year_before(now["quarter_end"])]
    if not year_ago:
        return None
    before, after = year_ago[-1]["promoter_encumbered_pct"], now["promoter_encumbered_pct"]
    move = after - before
    if move >= PLEDGE_MOVE:
        return (f"Promoters pledged or otherwise tied up more of their stake over the past year: {_pct(before)} → "
                f"{_pct(after)}. Rising pledges usually mean promoters are borrowing more against their shares.")
    if move <= -PLEDGE_MOVE:
        return (f"Promoters freed up shares over the past year: pledged or otherwise tied up {_pct(before)} → "
                f"{_pct(after)} of their stake." + (" None are pledged now." if after == 0 else ""))
    if after >= PLEDGE_WARN:
        return f"About {_pct(after)} of the promoters' stake has stayed pledged or otherwise tied up over the past year."
    if after == 0:
        return "None of the promoters' stake is pledged now, as a year ago."
    return f"Only {_pct(after)} of the promoters' stake is pledged or otherwise tied up, much as a year ago."


INSTITUTIONS = (("fii_pct", "Foreign investors"), ("mutual_funds_pct", "Mutual funds"),
                ("dii_pct", "Domestic institutions"))
INSTITUTION_MOVE = 1.0  # percentage points over a year: worth a line


def _year_before(quarter_end: str) -> str:
    d = date.fromisoformat(quarter_end)
    return d.replace(year=d.year - 1).isoformat()


def _year_of_split(entry: dict | None) -> tuple[dict, dict] | None:
    """(latest full pattern, the latest one at least a year older), or None without a year of the split."""
    quarters = [q for q in (entry or {}).get("quarters", []) if q.get("fii_pct") is not None]
    if len(quarters) < 2:
        return None
    now = quarters[-1]
    year_ago = [q for q in quarters if q["quarter_end"] <= _year_before(now["quarter_end"])]
    return (now, year_ago[-1]) if year_ago else None


def _moves(now: dict, then: dict) -> dict[str, float]:
    return {key: now[key] - then[key] for key, _ in INSTITUTIONS if now.get(key) is not None and then.get(key) is not None}


def funds_buying(entry: dict | None) -> bool:
    """Foreign investors or mutual funds raised their stake by a point or more over the past year,
    and the two together didn't shrink."""
    pair = _year_of_split(entry)
    if not pair:
        return False
    moves = _moves(*pair)
    fii, mf = moves.get("fii_pct", 0.0), moves.get("mutual_funds_pct", 0.0)
    return (fii >= INSTITUTION_MOVE or mf >= INSTITUTION_MOVE) and fii + mf > 0


def institutions_note(entry: dict | None) -> str | None:
    """How foreign investors, mutual funds and domestic institutions moved their stakes over the past
    year (latest full pattern vs the latest one at least a year older); None without a year of the split."""
    pair = _year_of_split(entry)
    if not pair:
        return None
    now, then = pair
    moved = _moves(now, then)
    moves = []
    for key, who in INSTITUTIONS:
        move = moved.get(key)
        if move is not None and abs(move) >= INSTITUTION_MOVE:
            moves.append(f"{who if not moves else who.lower()} {'raised' if move > 0 else 'cut'} their stake "
                         f"from {then[key]:.1f}% to {now[key]:.1f}%")
    if not moves:
        if now.get("dii_pct") is None:
            return None
        return (f"Institutions' stakes barely moved over the past year (foreign investors {now['fii_pct']:.1f}%, "
                f"domestic institutions {now['dii_pct']:.1f}%).")
    return ("; ".join(moves) + " over the past year. Big funds building a stake over several quarters is a vote of "
            "confidence; a steady exit is worth understanding.")


def write(lake, output: Path = OUTPUT) -> dict:
    present = set(lake.datasets())
    doc = build(lake.query("select * from shareholding"),
                lake.query("select * from pledges") if "pledges" in present else None)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")  # compact: ~1,400+ companies
    return doc
