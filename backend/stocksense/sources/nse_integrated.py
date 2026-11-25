"""
NSE integrated filings — quarterly results from Mar 2025 on, when SEBI's "Integrated
Filing" replaced the old results feed (nse_results.py, which stops at Dec 2024).

  • GET /api/integrated-filing-results?index=equities&symbol=<S>&type=Integrated Filing- Financials
    lists the filings (quarter end, standalone/consolidated, links).
  • Each filing's `xbrl` link is the XBRL instance on nsearchives: the quarter's P&L,
    and at half-year ends the balance sheet too.

XBRL amounts are in rupees; `normalise` returns the same ₹-crore columns as
nse_results.normalise, plus equity / borrowings / total assets when the filing has a
balance sheet. Four taxonomies: Ind-AS companies, NBFCs (same P&L tags), banks
(InterestEarned, InterestExpended, …) and insurers (_LI_ / _GI_: total income and
shareholders' profit) — the file name says which.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime

import httpx

from .nse_results import BASE, HEADERS, net_revenue

RUPEES_PER_CRORE = 1e7
FILING_TYPE = "Integrated Filing- Financials"
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True)


def fetch_filings(c: httpx.Client, symbol: str) -> list[dict]:
    resp = c.get(f"{BASE}/integrated-filing-results",
                 params={"index": "equities", "symbol": symbol, "type": FILING_TYPE})
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", []) if isinstance(data, dict) else data


def fetch_xbrl(c: httpx.Client, filing: dict) -> str:
    resp = c.get(filing["xbrl"])
    resp.raise_for_status()
    return resp.text


def _d(value: str | None) -> date | None:
    try:
        return datetime.strptime(value.strip().title(), "%d-%b-%Y").date()
    except (AttributeError, ValueError):
        return None


def kind(filing: dict) -> str:
    name = (filing.get("xbrl") or "").upper()
    if "BANKING" in name:
        return "bank"
    if "NBFC" in name:
        return "finance"
    if "INSURANCE" in name or "_LI_" in name or "_GI_" in name:
        return "insurance"
    return "company"


def facts(xml: str, quarter_end: date) -> tuple[dict, dict]:
    """(quarter figures, balance-sheet figures at quarter end) — plain contexts only, no dimensions."""
    root = ET.fromstring(xml)
    quarter, instant = set(), set()
    for ctx in root.iter():
        if not ctx.tag.endswith("}context") or any(m.tag.endswith("explicitMember") for m in ctx.iter()):
            continue
        period = {p.tag.split("}")[1]: p.text for p in ctx.iter() if p.tag.split("}")[-1] in ("startDate", "endDate", "instant")}
        try:
            if "instant" in period and date.fromisoformat(period["instant"]) == quarter_end:
                instant.add(ctx.get("id"))
            elif "endDate" in period and date.fromisoformat(period["endDate"]) == quarter_end:
                days = (quarter_end - date.fromisoformat(period["startDate"])).days
                if 80 <= days <= 100:
                    quarter.add(ctx.get("id"))
        except (KeyError, TypeError, ValueError):
            continue
    flow, stock = {}, {}
    for el in root:
        ref, text = el.get("contextRef"), (el.text or "").strip()
        if ref is None or not _NUMBER.match(text):
            continue
        name = el.tag.split("}")[-1]
        if ref in quarter:
            flow.setdefault(name, float(text))
        elif ref in instant:
            stock.setdefault(name, float(text))
    return flow, stock


def _cr(fields: dict, *names: str) -> float | None:
    for name in names:
        if name in fields:
            return fields[name] / RUPEES_PER_CRORE
    return None


def _first(fields: dict, *names: str) -> float | None:
    for name in names:
        if name in fields:
            return fields[name]
    return None


def normalise(filing: dict, xml: str) -> dict:
    """One integrated filing → the same row shape as nse_results.normalise (₹ crore)."""
    end = _d(filing.get("qe_Date"))
    f, b = facts(xml, end) if end else ({}, {})
    k = kind(filing)
    if k == "insurance":  # no "revenue from operations": premiums + investment income = total income
        f = {**f, "RevenueFromOperations": f["Income"]} if "Income" in f and "RevenueFromOperations" not in f else f
    row = {
        "symbol": (filing.get("symbol") or "").upper(),
        "period_from": None,
        "period_end": end,
        "consolidated": filing.get("consolidated") == "Consolidated",
        "audited": filing.get("audited") == "Audited",
        "ind_as": k != "bank",
        "kind": k,
        "bank": k == "bank",
        "filed_at": filing.get("broadcast_Date"),
        "seq": str(filing.get("seq_Id") or ""),
        "revenue": _cr(f, "RevenueFromOperations", "InterestEarned"),
        "other_income": _cr(f, "OtherIncome"),
        "total_income": _cr(f, "Income"),
        "total_expenses": _cr(f, "Expenses", "ExpenditureExcludingProvisionsAndContingencies"),
        "depreciation": _cr(f, "DepreciationDepletionAndAmortisationExpense"),
        "finance_cost": _cr(f, "FinanceCosts", "InterestExpended"),
        "profit_before_tax": _cr(f, "ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax", "ProfitLossBeforeTax"),
        "tax": _cr(f, "TaxExpense"),
        # Owners' share where the filing splits it out (consolidated), else the period's profit.
        "net_profit": _cr(f, "ProfitOrLossAttributableToOwnersOfParent",
                          "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates",
                          "ProfitLossForPeriod", "ProfitLossForThePeriod", "ProfitLossAfterTaxAndExtraordinaryItems"),
        "eps": _first(f, "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                      "BasicEarningsLossPerShareFromContinuingOperations",
                      "BasicEarningsPerShareBeforeExtraordinaryItems"),
        "paid_up_capital": _cr(f, "PaidUpValueOfEquityShareCapital"),
        "face_value": _first(f, "FaceValueOfEquityShareCapital"),
        # Balance sheet: half-year and year ends only.
        "equity": _cr(b, "EquityAttributableToOwnersOfParent", "Equity"),
        "borrowings": (None if not {"BorrowingsNoncurrent", "BorrowingsCurrent"} & b.keys() else
                       ((b.get("BorrowingsNoncurrent") or 0) + (b.get("BorrowingsCurrent") or 0)) / RUPEES_PER_CRORE),
        "total_assets": _cr(b, "Assets"),
    }
    row["net_profit"] = _owners_profit(f, row["net_profit"])
    row["net_revenue"] = net_revenue(row)
    return row


def _owners_profit(f: dict, owners: float | None) -> float | None:
    """Owners' + minority share must add up to the period's profit. When they don't, the
    split was mis-tagged (Adani Ports, Jun 2025: its OCI split, ₹53 + ₹48 crore, filed as
    the profit split) and the period's total profit is the better figure."""
    total = _cr(f, "ProfitLossForPeriod")
    minority = _cr(f, "ProfitOrLossAttributableToNonControllingInterests")
    if owners is None or total is None or minority is None or "ProfitOrLossAttributableToOwnersOfParent" not in f:
        return owners
    if abs(owners + minority - total) > 0.05 * max(abs(total), 1):
        return total
    return owners
