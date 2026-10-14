"""
IPO data from NSE's website API: open and upcoming issues, live category-wise
subscription, and past issues with listing dates.

NSE's API expects browser-like headers and sometimes blocks data-centre IPs. If
requests start failing in the cloud, run this from a residential connection or
cache results in Supabase.
"""

from __future__ import annotations

import httpx

from ..log import get_logger

log = get_logger(__name__)

BASE = "https://www.nseindia.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/all-upcoming-issues-ipo",
}


class NseUnavailable(RuntimeError):
    """NSE didn't answer or answered with something other than JSON."""


def _get(path: str):
    try:
        resp = httpx.get(BASE + path, headers=_HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise NseUnavailable(f"NSE request failed for {path}: {exc}") from exc


def current_issues() -> list[dict]:
    """Issues open for bidding today, with overall subscription so far."""
    return _get("/api/ipo-current-issue")


def upcoming_issues() -> list[dict]:
    """Open and forthcoming issues (status "Active" or "Forthcoming")."""
    return _get("/api/all-upcoming-issues?category=ipo")


def category_subscription(symbol: str) -> dict:
    """{"dataList": [...], "updateTime": ...} — rows for QIB (srNo "1"), NII ("2"), retail ("3"), employees ("4"), Total."""
    return _get(f"/api/ipo-active-category?symbol={symbol}")


def past_issues() -> list[dict]:
    """Every past public issue NSE lists (~1,500), newest first."""
    return _get("/api/public-past-issues")
