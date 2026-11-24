"""
Layer 3 of metric context: market and time. Is the company's whole sector — and the
market — expensive or cheap right now compared with its own history?

NSE publishes each index's P/E every day; the lake holds it since 2012
(clean/index_prices). Only history from April 2021 is used: that's when NSE moved index
P/E to consolidated earnings, and older values aren't comparable. `build` summarises it per sector index (today's P/E, its
historical median and quartiles, and the share of past days it was cheaper), and
`python -m stocksense valuation-context` writes the result to
backend/data/valuation_context.json, which the API serves. The public API never
needs the engine machine; rerun the job (weekly is plenty) to refresh it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DATA_DIR
from .sectors import SECTOR_LABELS

OUTPUT = DATA_DIR / "valuation_context.json"
MARKET_INDEX = "NIFTY_50"
MIN_YEARS = 3
# NSE switched index P/E from standalone to consolidated earnings on 1 Apr 2021: NIFTY's
# P/E fell 17.9% on 31 Mar 2021 while the index moved 1%. Earlier P/Es aren't comparable,
# so "usual level" is judged on history from this date only.
HISTORY_FROM = pd.Timestamp("2021-04-01")  # an index needs this much P/E history to say anything about "usual"

# StockSense sector code → the NSE index whose P/E best represents it.
SECTOR_INDEX = {
    "it": "NIFTY_IT", "bank": "NIFTY_BANK", "nbfc": "NIFTY_FINANCIAL_SERVICES",
    "finance": "NIFTY_FINANCIAL_SERVICES", "auto": "NIFTY_AUTO", "pharma": "NIFTY_PHARMA",
    "fmcg": "NIFTY_FMCG", "materials": "NIFTY_METAL", "energy": "NIFTY_ENERGY",
    "realestate": "NIFTY_REALTY", "consumer": "NIFTY_INDIA_CONSUMPTION",
    "industrial": "NIFTY_INFRASTRUCTURE", "telecom": "NIFTY_MEDIA", "defence": "NIFTY_INDIA_DEFENCE",
}


def summarise(pe: pd.Series) -> dict | None:
    """pe: index P/E by date. Today's value against its own history."""
    s = pe.dropna()
    s = s[(s > 0) & (s.index >= HISTORY_FROM)].sort_index()
    if s.empty:
        return None
    years = (s.index[-1] - s.index[0]).days / 365.25
    if years < MIN_YEARS:
        return None
    latest = float(s.iloc[-1])
    cheaper_days = float((s < latest).mean() * 100)
    reading = ("expensive by its own history" if cheaper_days >= 80 else "above its usual level" if cheaper_days >= 60
               else "around its usual level" if cheaper_days > 40 else "below its usual level" if cheaper_days > 20
               else "cheap by its own history")
    return {
        "as_of": str(s.index[-1].date()), "since": str(s.index[0].date()), "years": round(years, 1),
        "pe": round(latest, 1), "median_pe": round(float(s.median()), 1),
        "p25_pe": round(float(s.quantile(0.25)), 1), "p75_pe": round(float(s.quantile(0.75)), 1),
        "higher_than_pct_of_days": round(cheaper_days), "reading": reading,
    }


def build(index_pe: pd.DataFrame) -> dict:
    """index_pe: columns date, index, pe (from clean/index_prices). Returns the publishable document."""
    df = index_pe.assign(date=pd.to_datetime(index_pe["date"]))
    wanted = {MARKET_INDEX, *SECTOR_INDEX.values()}
    indices = {}
    for code, g in df[df["index"].isin(wanted)].groupby("index"):
        summary = summarise(g.set_index("date")["pe"])
        if summary:
            indices[code] = summary
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "NSE daily index closing file (P/E), via the engine's data lake",
        "market_index": MARKET_INDEX,
        "sector_index": {sector: idx for sector, idx in SECTOR_INDEX.items() if idx in indices},
        "indices": indices,
    }


def sector_note(sector: str, doc: dict | None) -> str | None:
    """One line on how the company's sector — or the market — is valued today versus its history."""
    if not doc:
        return None
    idx = doc.get("sector_index", {}).get(sector)
    who = f"The {SECTOR_LABELS.get(sector, sector)} sector" if idx else "The market as a whole"
    summary = doc.get("indices", {}).get(idx or doc.get("market_index"))
    if not summary:
        return None
    return (f"{who} trades at a P/E of {summary['pe']:.0f} today against a median of {summary['median_pe']:.0f} "
            f"since {summary['since'][:4]} — {summary['reading']} (higher than on {summary['higher_than_pct_of_days']}% "
            "of days). Valuations everywhere move with interest rates and the economic cycle.")


def write(lake, output: Path = OUTPUT) -> dict:
    """Build from the lake and write the JSON the API serves."""
    doc = build(lake.query("select date, index, pe from index_prices where pe is not null"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc
