"""
Market and world news from public RSS feeds (Economic Times, Livemint,
Business Standard, Google News). Only headlines, links and dates are used.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from ..log import get_logger

log = get_logger(__name__)

FEEDS: dict[str, str] = {
    "Economic Times — Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Economic Times — Economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "Livemint — Markets": "https://www.livemint.com/rss/markets",
    "Business Standard — Markets": "https://www.business-standard.com/rss/markets-106.rss",
    "Google News — World & India": (
        "https://news.google.com/rss/search?q=(war+OR+crude+OR+tariff+OR+sanctions+OR+RBI+OR+Fed)"
        "+India+market&hl=en-IN&gl=IN&ceid=IN:en"
    ),
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (StockSense news reader)"}


@dataclass(frozen=True)
class Headline:
    title: str
    link: str
    source: str
    published: datetime | None


def _clean(text: str | None) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_rss(xml: str, source: str) -> list[Headline]:
    """Headlines from one RSS 2.0 document. Malformed feeds yield nothing rather than raising."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    items = []
    for item in root.iter("item"):
        title = _clean(item.findtext("title"))
        # Google News appends " - Publisher" to every title.
        publisher = _clean(item.findtext("source"))
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]
        if title:
            items.append(
                Headline(
                    title=title,
                    link=(item.findtext("link") or "").strip(),
                    source=publisher or source,
                    published=_date(item.findtext("pubDate")),
                )
            )
    return items


def _fetch(source: str, url: str) -> list[Headline]:
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning(f"News feed failed ({source}): {exc}")
        return []
    return parse_rss(resp.text, source)


def fetch_headlines(feeds: dict[str, str] = FEEDS) -> list[Headline]:
    """All feeds in parallel, de-duplicated by title, newest first."""
    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        batches = pool.map(lambda item: _fetch(*item), feeds.items())
    seen: set[str] = set()
    unique: list[Headline] = []
    for headline in (h for batch in batches for h in batch):
        key = re.sub(r"[^a-z0-9]", "", headline.title.lower())[:80]
        if key not in seen:
            seen.add(key)
            unique.append(headline)
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(unique, key=lambda h: h.published or oldest, reverse=True)
