"""
NSE shareholding — promoter holding by quarter and promoter pledges (M1.3).

  • GET /api/corporate-share-holdings-master?index=equities&symbol=<S>
    every quarterly shareholding pattern a company filed (about five years): promoter &
    promoter group %, public %, employee trusts %, and a link to the full XBRL.
  • GET /api/corporate-pledgedata?index=equities&symbol=<S>
    the latest pledge position: promoter shares pledged (from SAST disclosures) and the
    shares shown as encumbered in the last shareholding pattern. Only the current
    figure is served, so history builds up from regular snapshots.

Promoter holding here is what Indian filings mean by it — the founders/parent and their
group — unlike Yahoo's "insiders", which the score has been using as a stand-in.
"""

from __future__ import annotations

from datetime import date, datetime

import httpx

from .nse_results import BASE, HEADERS


def client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True)


def fetch_master(c: httpx.Client, symbol: str) -> list[dict]:
    resp = c.get(f"{BASE}/corporate-share-holdings-master", params={"index": "equities", "symbol": symbol})
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])


def fetch_pledges(c: httpx.Client, symbol: str) -> list[dict]:
    resp = c.get(f"{BASE}/corporate-pledgedata", params={"index": "equities", "symbol": symbol})
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", []) if isinstance(data, dict) else data


def _date(value: str | None, fmt: str = "%d-%b-%Y") -> date | None:
    try:
        return datetime.strptime(value.strip().title(), fmt).date()
    except (AttributeError, ValueError):
        return None


def _float(value) -> float | None:
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def holdings(rows: list[dict]) -> list[dict]:
    """Master list → one row per quarter (the latest submission if a pattern was revised)."""
    out: dict[date, dict] = {}
    for r in rows:
        quarter = _date(r.get("date"))
        if quarter is None:
            continue
        row = {
            "symbol": (r.get("symbol") or "").upper(),
            "quarter_end": quarter,
            "promoter_pct": _float(r.get("pr_and_prgrp")),
            "public_pct": _float(r.get("public_val")),
            "employee_trusts_pct": _float(r.get("employeeTrusts")),
            "submitted": _date(r.get("submissionDate")),
            "revised": (r.get("revisedData") or "N") == "Y",
            "record_id": str(r.get("recordId") or ""),
            "xbrl": r.get("xbrl"),
        }
        kept = out.get(quarter)
        if kept is None or (row["submitted"] or date.min) >= (kept["submitted"] or date.min):
            out[quarter] = row
    return sorted(out.values(), key=lambda r: r["quarter_end"])


def pledge(rows: list[dict], symbol: str, fetched: date) -> dict | None:
    """The latest pledge position, as percentages of the promoters' holding and of all shares."""
    if not rows:
        return None
    r = rows[0]
    promoter_shares = _float(r.get("totPromoterHolding"))
    pledged = _float(r.get("numSharesPledged"))
    total = _float(r.get("totIssuedShares"))
    return {
        "symbol": symbol.upper(),
        "fetched": fetched,
        "shp_quarter_end": _date(r.get("shp")),
        "promoter_pct": _float(r.get("percPromoterHolding")),
        # From SAST disclosures (current): pledged shares ÷ promoters' shares.
        "pledged_pct_of_promoter": round(100 * pledged / promoter_shares, 2) if pledged is not None and promoter_shares else None,
        "pledged_pct_of_total": round(100 * pledged / total, 2) if pledged is not None and total else None,
        # As shown in the last shareholding pattern (quarter end).
        "encumbered_pct_of_promoter_shp": _float(r.get("percPromoterShares")),
        "shares_pledged": pledged,
        "promoter_shares": promoter_shares,
    }
