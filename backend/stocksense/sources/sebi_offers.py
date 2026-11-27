"""
SEBI's register of offer documents: "Red Herring Documents filed with ROC" (sebi.gov.in →
Filings → Public Issues), the final prospectus of every public issue since 2004, each on its
own page with the full PDF. Used for the prospectus study (M3.7): which disclosures actually
preceded weak listings.

The listing's first page is a plain GET; later pages come from the same AJAX call the site's
own pager makes (sebiweb/ajax/home/getnewslistinfo.jsp, 25 records a page, newest first).
"""

from __future__ import annotations

from html import unescape
import re
from datetime import date, datetime

import httpx

BASE = "https://www.sebi.gov.in"
LISTING = f"{BASE}/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=11"
AJAX = f"{BASE}/sebiweb/ajax/home/getnewslistinfo.jsp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
PAGE_SIZE = 25

_ROW = re.compile(r"<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td><a href=['\"]([^'\"]+)['\"][^>]*?title=\"([^\"]*)\"",
                  re.S)
_TOTAL = re.compile(r"of (\d+) records")
_FULL_PDF = re.compile(r"file=(https://www\.sebi\.gov\.in/sebi_data/attachdocs/[^'\"&]+?\.pdf)", re.I)
_ANY_PDF = re.compile(r"(https://www\.sebi\.gov\.in/sebi_data/[^'\"]+?\.pdf)", re.I)
_NOT_THE_RHP = re.compile(r"addendum|corrigend|abridged|price band|notice|advert|erratum|clarification", re.I)
_SUFFIX = re.compile(r"\s*[-–:]?\s*(?:updated\s+)?(?:rhp|red herring prospectus|pdf|prospectus)\s*$", re.I)


def client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=120, follow_redirects=True)


def parse_listing(html: str) -> tuple[list[dict], int | None]:
    """[{date, title, url}] and the total number of records, from a listing page or AJAX reply."""
    rows = []
    for day, url, title in _ROW.findall(html):
        title = re.sub(r"\s+", " ", unescape(title.split("<")[0])).strip()
        rows.append({"date": datetime.strptime(day, "%b %d, %Y").date().isoformat(), "title": title, "url": url})
    total = _TOTAL.search(html)
    return rows, int(total.group(1)) if total else None


def listing_page(c: httpx.Client, page: int) -> tuple[list[dict], int | None]:
    """Page 0 is the plain listing (which also starts the session the AJAX pager needs)."""
    if page == 0:
        resp = c.get(LISTING)
    else:
        body = ("nextValue=1&next=n&search=&fromDate=&toDate=&fromYear=&toYear=&deptId=-1&sid=3&ssid=15&smid=11"
                "&ssidhidden=15&intmid=-1&sText=Filings&ssText=Public Issues"
                f"&smText=Red Herring Documents filed with ROC&doDirect={page}")
        resp = c.post(AJAX, content=body.encode(), headers={
            "Content-Type": "application/x-www-form-urlencoded", "Referer": LISTING, "X-Requested-With": "XMLHttpRequest"})
    resp.raise_for_status()
    return parse_listing(resp.text)


def is_prospectus(title: str) -> bool:
    """The RHP itself, not an addendum, corrigendum, price-band notice or abridged version."""
    return not _NOT_THE_RHP.search(title)


def company_of(title: str) -> str:
    """'Monomark Engineering (India) Limited - RHP' -> 'Monomark Engineering (India) Limited'."""
    return _SUFFIX.sub("", title).strip(" -–:")


def pdf_url(html: str) -> str | None:
    """The full prospectus on a filing page (the viewer's file= link), else any SEBI PDF that
    isn't the abridged prospectus."""
    full = _FULL_PDF.search(html)
    if full:
        return full.group(1)
    for url in _ANY_PDF.findall(html):
        if "prospectus_p.pdf" not in url.lower():
            return url
    return None


_NOISE = re.compile(r"\b(limited|ltd|private|pvt|the|india|and|co|company|corporation|corp)\b")


def name_key(name: str) -> str:
    """A company name reduced for matching SEBI titles to NSE's issue list."""
    name = name.lower().replace("&", " and ")
    name = re.sub(r"\([^)]*\)", " ", name)       # (India), (formerly …)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", _NOISE.sub(" ", name)).strip()


def nse_day(value: str | None) -> date | None:
    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime((value or "").strip().title(), fmt).date()
        except ValueError:
            continue
    return None
