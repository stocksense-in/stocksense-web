"""
NSE shareholding — promoter holding by quarter and promoter pledges (M1.3).

  • GET /api/corporate-share-holdings-master?index=equities&symbol=<S>
    every quarterly shareholding pattern a company filed (about five years): promoter &
    promoter group %, public %, employee trusts %, and a link to the full XBRL.
  • GET /api/corporate-pledgedata?index=equities&symbol=<S>
    the latest pledge position: promoter shares pledged/encumbered (totPromoterShares,
    percPromoterShares — % of the promoters' holding), and separately every pledge
    recorded at the depository by any shareholder (numSharesPledged — mostly margin
    pledges, not a promoter signal: ITC, with no promoter, shows 2% of its shares). Only
    the current figure is served, so history builds up from regular snapshots.

Promoter holding here is what Indian filings mean by it — the founders/parent and their
group — unlike Yahoo's "insiders", which the score has been using as a stand-in.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
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


# Shareholding-pattern XBRL categories → our columns (percent of all shares).
CATEGORIES = {
    "InstitutionsForeignMember": "fii_pct",
    "InstitutionsDomesticMember": "dii_pct",
    "MutualFundsOrUTIMember": "mutual_funds_pct",
    "InsuranceCompaniesMember": "insurance_pct",
    "ResidentIndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakhMember": "small_retail_pct",
    "NonInstitutionsMember": "non_institutions_pct",
    "GovernmentsMember": "government_pct",
    "ShareholdingOfPromoterAndPromoterGroupMember": "promoter_pct_pattern",  # cross-check with the summary
}
PERCENT_TAG = "ShareholdingAsAPercentageOfTotalNumberOfShares"


def fetch_xbrl(c: httpx.Client, url: str) -> bytes:
    resp = c.get(url)
    resp.raise_for_status()
    return resp.content


def categories(xml: bytes | str) -> dict:
    """Who holds the rest: foreign and domestic institutions, mutual funds, insurers, small
    retail, government — percent of all shares, from the pattern's XBRL (2023+ format)."""
    root = ET.fromstring(xml)
    member_of = {}
    for ctx in root.iter():
        if ctx.tag.endswith("}context"):
            members = [m.text.split(":")[-1] for m in ctx.iter() if m.tag.endswith("explicitMember")]
            if len(members) == 1:
                member_of[ctx.get("id")] = members[0]
    out = {}
    for el in root:
        if el.tag.split("}")[-1] != PERCENT_TAG:
            continue
        column = CATEGORIES.get(member_of.get(el.get("contextRef")))
        if column and column not in out:
            try:
                out[column] = round(100 * float(el.text), 2)
            except (TypeError, ValueError):
                continue
    return out


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
    promoter_pct = _float(r.get("percPromoterHolding"))
    has_promoter = promoter_pct is not None and promoter_pct > 0
    return {
        "symbol": symbol.upper(),
        "fetched": fetched,
        "shp_quarter_end": _date(r.get("shp")),
        "promoter_pct": promoter_pct,
        "promoter_shares": _float(r.get("totPromoterHolding")),
        "promoter_shares_pledged": _float(r.get("totPromoterShares")) if has_promoter else None,
        # The red-flag number: how much of the promoters' own stake is pledged.
        "pledged_pct_of_promoter": _float(r.get("percPromoterShares")) if has_promoter else None,
        "pledged_pct_of_total": _float(r.get("percTotShares")) if has_promoter else None,
        # Every depository pledge, by anyone (context, not a promoter signal).
        "all_pledges_pct_of_total": _float(r.get("percSharesPledged")),
    }
