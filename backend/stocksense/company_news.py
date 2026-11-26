"""
News about one company: which headlines are really about it.

A search feed returns loose matches ("Infosys" also finds "Infosys founder backs startup"),
so each headline must name the company by its everyday name or its NSE symbol. The
everyday name drops legal suffixes ("Limited"), a trailing "India" and a leading "The",
and uses the short forms headlines use ("Pharmaceuticals" → "Pharma").
"""
from __future__ import annotations

import re

from .sources.news import Headline

# Social posts aren't reporting; the search feed sometimes includes them.
_SOCIAL = {"facebook", "youtube", "instagram", "x", "twitter", "linkedin", "reddit", "threads", "quora"}

_LEGAL = re.compile(r"[\s,.]*\b(limited|ltd|pvt|private)\b\.?\s*$", re.I)
_TRAILING_INDIA = re.compile(r"\s+\(?india\)?\s*$", re.I)
_SHORT_FORMS = [(re.compile(r"\bpharmaceuticals?\b", re.I), "Pharma"),
                (re.compile(r"\btechnologies\b", re.I), "Tech"),
                (re.compile(r"\bcorporation\b", re.I), "Corp")]


def everyday_name(name: str) -> str:
    """'Maruti Suzuki India Limited' → 'Maruti Suzuki'; 'The Ramco Cements Limited' → 'Ramco Cements'."""
    n = re.sub(r"\s+", " ", name or "").strip()
    for _ in range(2):  # "XYZ (India) Pvt. Ltd."
        n = _LEGAL.sub("", n).strip()
    n = _TRAILING_INDIA.sub("", n).strip()
    n = re.sub(r"^the\s+", "", n, flags=re.I)
    return n


def aliases(name: str, symbol: str) -> tuple[list[str], str | None]:
    """Names a headline may use (matched without case) and the symbol (matched exactly)."""
    base = everyday_name(name)
    names = [base] if base else []
    for pattern, short in _SHORT_FORMS:
        alt = pattern.sub(short, base)
        if alt != base and alt not in names:
            names.append(alt)
    sym = (symbol or "").upper()
    # Short or wordy symbols ("LT", "SBIN") rarely appear in headlines and would match noise.
    exact = sym if len(sym) >= 3 and sym.isalpha() and len(sym) <= 6 else None
    return names, exact


def mentions(title: str, names: list[str], symbol: str | None) -> bool:
    for n in names:
        if re.search(rf"(?<![\w&]){re.escape(n)}(?![\w&])", title, re.I):
            return True
    return bool(symbol) and re.search(rf"(?<![\w&]){re.escape(symbol)}(?![\w&])", title) is not None


def company_news(headlines: list[Headline], name: str, symbol: str, limit: int = 20) -> list[dict]:
    """Headlines that name the company, de-duplicated, newest first as given."""
    names, sym = aliases(name, symbol)
    seen: set[str] = set()
    out = []
    for h in headlines:
        title = re.sub(r"\s+-\s+[^-]{2,60}$", "", h.title).strip()  # Google adds " - Publisher"
        key = re.sub(r"[^a-z0-9]", "", title.lower())[:80]
        publisher = h.title[len(title):].strip(" -") or h.source
        if key in seen or publisher.strip().lower() in _SOCIAL or not mentions(title, names, sym):
            continue
        seen.add(key)
        out.append({"title": title, "link": h.link, "source": publisher,
                    "published": h.published.isoformat() if h.published else None})
        if len(out) >= limit:
            break
    return out
