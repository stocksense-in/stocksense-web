"""
NSE index closing values — one public file a day with open/high/low/close,
turnover and valuation (P/E, P/B, dividend yield) for every NSE index:
https://nsearchives.nseindia.com/content/indices/ind_close_all_<DDMMYYYY>.csv

Coverage grows over time (~47 indices in 2015, ~165 in 2026). NSE renamed its
"CNX …" indices to "Nifty …" in late 2015, so names are normalised to stable
codes (CNX Bank and Nifty Bank are both NIFTY_BANK).
"""

from __future__ import annotations

import io
import re
from datetime import date

import pandas as pd

from ..symbols import _HEADERS as HEADERS

ARCHIVE = "https://nsearchives.nseindia.com/content/indices"

# Old names whose new name isn't just "CNX" → "Nifty".
_RENAMED = {
    "cnx nifty": "nifty 50", "s&p cnx nifty": "nifty 50", "cnx nifty junior": "nifty next 50",
    "cnx midcap": "nifty midcap 100", "cnx smallcap": "nifty smallcap 100", "cnx finance": "nifty financial services",
    "cnx consumption": "nifty india consumption", "cnx service sector": "nifty services sector",
    "cnx infrastructure": "nifty infrastructure", "cnx nifty dividend": "nifty50 dividend points",
    "nifty healthcare index": "nifty healthcare",
}


def file_name(day: date) -> str:
    return f"ind_close_all_{day:%d%m%Y}.csv"


def url_for(day: date) -> str:
    return f"{ARCHIVE}/{file_name(day)}"


def index_code(name: str) -> str:
    """'CNX Bank' / 'Nifty Bank' → 'NIFTY_BANK'; 'India VIX' → 'INDIA_VIX'."""
    n = re.sub(r"\s+", " ", name.strip().lower())
    n = _RENAMED.get(n, n)
    if n.startswith("cnx "):
        n = "nifty " + n[4:]
    return re.sub(r"[^a-z0-9]+", "_", n).strip("_").upper()


def parse(content: bytes) -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    raw.columns = [c.strip() for c in raw.columns]
    num = lambda col: pd.to_numeric(raw[col].str.replace(",", ""), errors="coerce")  # noqa: E731
    df = pd.DataFrame({
        "index": raw["Index Name"].map(index_code).astype("string"),
        "name": raw["Index Name"].str.strip().astype("string"),
        "open": num("Open Index Value"), "high": num("High Index Value"),
        "low": num("Low Index Value"), "close": num("Closing Index Value"),
        "change_pct": num("Change(%)"), "volume": num("Volume"),
        "turnover_cr": num("Turnover (Rs. Cr.)"),
        "pe": num("P/E"), "pb": num("P/B"), "div_yield": num("Div Yield"),
    })
    df = df[df["close"].notna() & (df["close"] > 0)]
    return df.drop_duplicates(subset=["index"], keep="first").reset_index(drop=True)
