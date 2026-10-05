"""
Screener.in — fallback for promoter holding and sales growth when Yahoo has nothing.

This scrapes public HTML, so it breaks if Screener changes its markup. Keep
requests slow (the ownership job sleeps between stocks) and don't rely on it
for anything but gaps.
"""

from __future__ import annotations

import re
from functools import lru_cache

import requests

TIMEOUT = 15

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
)


@lru_cache(maxsize=256)
def _page(symbol: str) -> str | None:
    try:
        resp = _session.get(
            f"https://www.screener.in/company/{symbol}/consolidated/", timeout=TIMEOUT
        )
    except requests.RequestException:
        return None
    return resp.text if resp.status_code == 200 else None


def promoter_holding(symbol: str) -> float | None:
    html = _page(symbol)
    if not html:
        return None
    match = re.search(r"Promoters[^<]*</(?:td|button)>\s*<td[^>]*>\s*([\d.]+)\s*%", html)
    return round(float(match.group(1)), 2) if match else None


def sales_cagr_3yr(symbol: str) -> float | None:
    html = _page(symbol)
    if not html:
        return None
    # The "Compounded Sales Growth" table has a "3 Years:" row.
    block = re.search(r"Compounded Sales Growth(.*?)</table>", html, re.S)
    if not block:
        return None
    match = re.search(r"3 Years:\s*</td>\s*<td[^>]*>\s*(-?[\d.]+)\s*%", block.group(1))
    return round(float(match.group(1)), 1) if match else None
