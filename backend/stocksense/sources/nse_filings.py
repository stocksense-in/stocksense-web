"""
NSE disclosures and flows — what companies announce, what insiders trade, and how
foreign and domestic institutions bought and sold.

  • Corporate announcements (www.nseindia.com/api/corporate-announcements): every
    filing with its category ("Outcome of Board Meeting", "Press Release", …), a
    one-line summary, the PDF link and broadcast time. A month fits in one request
    (~3k filings a month in 2015, ~17k now).
  • Insider trades under SEBI's PIT regulations (…/api/corporates-pit): who, their
    role, buy/sell, quantity, value, holdings before/after. NSE's endpoint returns
    data from Nov 2015 to May 2026; later months come back empty (a change on NSE's side).
  • FII/DII cash-market flows (…/api/fiidiiTradeReact): today's provisional buy/sell/net
    in ₹ crore. NSE serves only the latest day, so history builds up day by day.

Bulk and block deals are not here: NSE's historical deals API answers 503 to anything
but a browser session (bot protection, PLAN.md §1.5).
"""

from __future__ import annotations

from datetime import date, datetime

import httpx
import pandas as pd

from .nse_ipo import _HEADERS as HEADERS

BASE = "https://www.nseindia.com/api"


def _range(start: date, end: date) -> dict:
    return {"from_date": f"{start:%d-%m-%Y}", "to_date": f"{end:%d-%m-%Y}"}


def _get(client: httpx.Client, path: str, params: dict | None = None):
    resp = client.get(f"{BASE}/{path}", params=params)
    resp.raise_for_status()
    return resp.json()


def client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=120, follow_redirects=True)


def fetch_announcements(c: httpx.Client, start: date, end: date) -> list[dict]:
    data = _get(c, "corporate-announcements", {"index": "equities", **_range(start, end)})
    return data if isinstance(data, list) else data.get("data", [])


def fetch_insider_trades(c: httpx.Client, start: date, end: date) -> list[dict]:
    data = _get(c, "corporates-pit", {"index": "equities", **_range(start, end)})
    return data.get("data", []) if isinstance(data, dict) else data


def fetch_fii_dii(c: httpx.Client) -> list[dict]:
    return _get(c, "fiidiiTradeReact")


def _dt(value, fmts) -> datetime | None:
    if not value or str(value).strip() in ("-", ""):
        return None
    for fmt in fmts:
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    return None


def _num(value) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def announcements_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame([{
        "seq_id": str(r.get("seq_id") or ""),
        "symbol": (r.get("symbol") or "").strip().upper(),
        "company": (r.get("sm_name") or "").strip(),
        "isin": (r.get("sm_isin") or "").strip(),
        "category": (r.get("desc") or "").strip(),
        "summary": (r.get("attchmntText") or "").strip(),
        "attachment": (r.get("attchmntFile") or "").strip(),
        "broadcast_at": _dt(r.get("sort_date"), ("%Y-%m-%d %H:%M:%S",)) or _dt(r.get("an_dt"), ("%d-%b-%Y %H:%M:%S",)),
        "has_xbrl": bool(r.get("hasXbrl")),
    } for r in rows], columns=["seq_id", "symbol", "company", "isin", "category", "summary", "attachment",
                               "broadcast_at", "has_xbrl"])
    df = df.dropna(subset=["broadcast_at"])
    return df.drop_duplicates(subset=["seq_id", "symbol"]).sort_values("broadcast_at").reset_index(drop=True)


def insider_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame([{
        "symbol": (r.get("symbol") or "").strip().upper(),
        "company": (r.get("company") or "").strip(),
        "person": (r.get("acqName") or "").strip(),
        "person_category": (r.get("personCategory") or "").strip(),
        "security_type": (r.get("secType") or "").strip(),
        "transaction": (r.get("tdpTransactionType") or "").strip(),
        "mode": (r.get("acqMode") or "").strip(),
        "quantity": _num(r.get("secAcq")),
        "value": _num(r.get("secVal")),
        "shares_before": _num(r.get("befAcqSharesNo")),
        "shares_after": _num(r.get("afterAcqSharesNo")),
        "pct_before": _num(r.get("befAcqSharesPer")),
        "pct_after": _num(r.get("afterAcqSharesPer")),
        "traded_from": _dt(r.get("acqfromDt"), ("%d-%b-%Y",)),
        "traded_to": _dt(r.get("acqtoDt"), ("%d-%b-%Y",)),
        "intimated": _dt(r.get("intimDt"), ("%d-%b-%Y",)),
        "disclosed_at": _dt(r.get("date"), ("%d-%b-%Y %H:%M", "%d-%b-%Y")),
    } for r in rows])
    if df.empty:
        return df
    df = df.dropna(subset=["disclosed_at"])
    return df.drop_duplicates().sort_values("disclosed_at").reset_index(drop=True)


def fii_dii_frame(rows: list[dict]) -> pd.DataFrame:
    """Values in ₹ crore, as NSE reports them."""
    return pd.DataFrame([{
        "date": _dt(r.get("date"), ("%d-%b-%Y",)),
        "category": "FII" if "FII" in (r.get("category") or "").upper() else (r.get("category") or "").strip().upper(),
        "buy_cr": _num(r.get("buyValue")), "sell_cr": _num(r.get("sellValue")), "net_cr": _num(r.get("netValue")),
    } for r in rows]).dropna(subset=["date"])
