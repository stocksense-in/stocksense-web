"""
Map Yahoo Finance sector/industry strings to StockSense sector codes.

Sector codes change how a stock is scored (see scoring.py): banks and NBFCs are
allowed more leverage, new-age platforms are not judged on P/E.
"""

from __future__ import annotations

# Checked first — Yahoo's "Financial Services" sector mixes banks, NBFCs,
# insurers and brokers, so the industry decides.
_INDUSTRY_CODES: list[tuple[str, str]] = [
    ("banks", "bank"),
    ("credit services", "nbfc"),
    ("mortgage finance", "nbfc"),
    ("internet content", "newage"),
    ("internet retail", "newage"),
    ("aerospace & defense", "defence"),
    ("electronic components", "electronics"),
    ("auto", "auto"),
]

_SECTOR_CODES: dict[str, str] = {
    "technology": "it",
    "communication services": "telecom",
    "financial services": "finance",
    "consumer cyclical": "consumer",
    "consumer defensive": "fmcg",
    "healthcare": "pharma",
    "basic materials": "materials",
    "industrials": "industrial",
    "energy": "energy",
    "real estate": "realestate",
    "utilities": "utilities",
}

# Human-readable names shown in the UI.
SECTOR_LABELS: dict[str, str] = {
    "it": "IT Services",
    "bank": "Banking",
    "nbfc": "NBFC",
    "finance": "Financial Services",
    "newage": "New-age Tech",
    "defence": "Defence",
    "electronics": "Electronics",
    "auto": "Automobile",
    "telecom": "Telecom & Media",
    "consumer": "Consumer Discretionary",
    "fmcg": "FMCG",
    "pharma": "Pharma & Healthcare",
    "materials": "Metals & Materials",
    "industrial": "Industrials",
    "energy": "Energy",
    "realestate": "Real Estate",
    "utilities": "Utilities",
    "general": "Other",
}


def sector_code(yf_sector: str | None, yf_industry: str | None = None) -> str:
    industry = (yf_industry or "").lower()
    for needle, code in _INDUSTRY_CODES:
        if needle in industry:
            return code
    return _SECTOR_CODES.get((yf_sector or "").lower(), "general")
