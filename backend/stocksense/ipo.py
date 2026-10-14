"""
IPOs: open and upcoming issues with live demand, and how recent listings have
done since. Parsing and judgement only — fetching lives in sources/nse_ipo.py.

Demand reads the subscription numbers the way experienced IPO investors do:
institutional (QIB) demand is the most informed signal, so it weighs most.
It describes demand so far; it is not a recommendation to apply.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

# NSE category rows (srNo) → our field names.
CATEGORY_ROWS = {"1": "qib", "2": "nii", "3": "retail", "4": "employees"}


def parse_number(text) -> float | None:
    """'3.31', '1.8420492E7', '  75', '' → float or None."""
    if text is None:
        return None
    text = str(text).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_band(text: str | None) -> tuple[float, float] | None:
    """'Rs.275 to Rs.289' → (275, 289); 'Rs.1000' → (1000, 1000); '-' → None."""
    prices = [float(p.replace(",", "")) for p in re.findall(r"[\d,]+(?:\.\d+)?", text or "")]
    if not prices:
        return None
    return min(prices), max(prices)


def parse_date(text: str | None) -> date | None:
    """'14-Oct-2026' or '05-OCT-2026' → date."""
    try:
        return datetime.strptime((text or "").strip().title(), "%d-%b-%Y").date()
    except ValueError:
        return None


@dataclass
class Subscription:
    """Times subscribed per category (2.5 = bids for 2.5× the shares on offer)."""

    qib: float | None = None
    nii: float | None = None
    retail: float | None = None
    employees: float | None = None
    total: float | None = None
    updated_at: str | None = None


def parse_subscription(payload: dict) -> Subscription:
    sub = Subscription(updated_at=payload.get("updateTime"))
    for row in payload.get("dataList", []):
        sr, times = row.get("srNo"), parse_number(row.get("noOfTotalMeant"))
        if sr in CATEGORY_ROWS:
            setattr(sub, CATEGORY_ROWS[sr], times)
        elif (row.get("category") or "").strip().lower() == "total":
            sub.total = times
    return sub


@dataclass
class Demand:
    level: str  # strong | moderate | weak | early
    summary: str


def assess_demand(sub: Subscription, status: str) -> Demand:
    if status == "upcoming":
        return Demand("early", "Bidding hasn't started yet.")
    qib, total = sub.qib, sub.total
    if total is None:
        return Demand("early", "No bids reported yet.")
    parts = [f"{name} {value:.1f}×" for name, value in (("Institutions", qib), ("HNIs", sub.nii), ("Retail", sub.retail)) if value is not None]
    detail = ", ".join(parts) if parts else f"overall {total:.1f}×"
    if (qib or 0) >= 10 and total >= 10:
        return Demand("strong", f"Heavily oversubscribed with strong institutional demand ({detail}).")
    if (qib or 0) >= 2 or total >= 3:
        return Demand("moderate", f"Oversubscribed so far ({detail}).")
    if status == "open":
        return Demand("early" if total < 1 else "weak", f"Demand is still building ({detail}). Institutions often bid on the last day.")
    return Demand("weak", f"Lukewarm demand ({detail}).")


@dataclass
class Issue:
    symbol: str
    name: str
    board: str  # mainboard | sme
    status: str  # open | upcoming | closed
    opens: str | None
    closes: str | None
    price_low: float | None
    price_high: float | None
    shares_offered: float | None
    size_crore: float | None
    subscription: Subscription
    demand: Demand

    def to_dict(self) -> dict:
        return asdict(self)


def build_issue(raw: dict, subscription: Subscription | None = None, today: date | None = None) -> Issue:
    today = today or date.today()
    opens, closes = parse_date(raw.get("issueStartDate")), parse_date(raw.get("issueEndDate"))
    status = (
        "upcoming" if opens and today < opens
        else "closed" if closes and today > closes
        else "open"
    )
    band = parse_band(raw.get("issuePrice"))
    shares = parse_number(raw.get("issueSize")) or parse_number(raw.get("noOfSharesOffered"))
    sub = subscription or Subscription(total=parse_number(raw.get("noOfTime")))
    return Issue(
        symbol=raw.get("symbol", ""),
        name=raw.get("companyName", ""),
        board="sme" if (raw.get("series") or "").upper() == "SME" else "mainboard",
        status=status,
        opens=opens.isoformat() if opens else None,
        closes=closes.isoformat() if closes else None,
        price_low=band[0] if band else None,
        price_high=band[1] if band else None,
        shares_offered=shares,
        size_crore=round(shares * band[1] / 1e7, 1) if shares and band else None,
        subscription=sub,
        demand=assess_demand(sub, status),
    )


def recent_listings(past: list[dict], prices: dict[str, float], days: int = 90, today: date | None = None) -> list[dict]:
    """
    Equity IPOs that listed in the last `days` days, with the return from the issue
    price to the latest price. `prices` maps NSE symbol → latest price.
    """
    today = today or date.today()
    rows = []
    for p in past:
        if (p.get("securityType") or "").upper() not in {"EQ", "BE", "SME"}:
            continue
        listed = parse_date(p.get("listingDate"))
        if not listed or (today - listed).days > days or listed > today:
            continue
        issue_price = parse_number(p.get("issuePrice"))
        band = parse_band(p.get("priceRange"))
        if issue_price is None and band:
            issue_price = band[1]
        current = prices.get((p.get("symbol") or "").strip().upper())
        rows.append(
            {
                "symbol": (p.get("symbol") or "").strip().upper(),
                "name": p.get("company", ""),
                "board": "sme" if (p.get("securityType") or "").upper() == "SME" else "mainboard",
                "listed": listed.isoformat(),
                "issue_price": issue_price,
                "price": current,
                "return_pct": round((current - issue_price) / issue_price * 100, 2) if current and issue_price else None,
            }
        )
    return sorted(rows, key=lambda r: r["listed"], reverse=True)
