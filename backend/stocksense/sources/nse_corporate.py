"""
NSE corporate actions and symbol changes — the reference data that keeps a long
price history honest.

  • Corporate actions (www.nseindia.com/api/corporates-corporateActions): every
    dividend, bonus, split, rights issue, demerger… with its ex-date. One request
    returns the whole range (~35k rows since 2010).
  • Symbol changes (nsearchives.nseindia.com/content/equities/symbolchange.csv):
    old symbol → new symbol with the effective date (ZOMATO → ETERNAL, 2025-04-09).

`share_multiplier` reads how many shares one old share became from the action's
wording, which NSE writes in ~120 different ways ("Bonus 3:1", "Face Value Split
(Sub-Division) - From Rs10/- Per Share To Re 1/- Per Share", both at once, …).
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

import httpx
import pandas as pd

from ..symbols import _HEADERS as ARCHIVE_HEADERS
from .nse_ipo import _HEADERS as API_HEADERS

ACTIONS_URL = "https://www.nseindia.com/api/corporates-corporateActions"
SYMBOL_CHANGES_URL = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"

_NUM = r"(\d+(?:\.\d+)?)"
_RUPEES = r"(?:rs\.?|re\.?|₹)?\s*"
# Bonus on something other than ordinary equity shares doesn't change the share count.
_NOT_EQUITY_BONUS = re.compile(r"debenture|preference|ncrps|dvr", re.I)
_BONUS = re.compile(rf"bonus\D{{0,30}}?{_NUM}\s*:\s*{_NUM}", re.I)
_SPLIT = re.compile(rf"(?:split|sub-?\s?division).*?{_RUPEES}{_NUM}\s*(?:/-)?.*?\bto\b\s*(?:face value\s*)?{_RUPEES}{_NUM}", re.I)
_CONSOLIDATION = re.compile(rf"consolidation\D*?{_RUPEES}{_NUM}\D*?\bto\b\s*{_RUPEES}{_NUM}", re.I)
_DIVIDEND = re.compile(rf"dividend\D{{0,25}}?{_RUPEES}{_NUM}", re.I)


def classify(subject: str) -> str:
    s = subject.lower()
    if "consolidat" in s:
        return "consolidation"
    if "split" in s or "sub-division" in s or "sub division" in s:
        return "split" if "bonus" not in s or _NOT_EQUITY_BONUS.search(s) else "bonus_split"
    if "bonus" in s and not _NOT_EQUITY_BONUS.search(s):
        return "bonus"
    if "dividend" in s:
        return "dividend"
    if "rights" in s:
        return "rights"
    if "demerger" in s or "arrangement" in s or "amalgamation" in s:
        return "restructuring"
    return "other"


def share_multiplier(subject: str) -> float | None:
    """
    Shares held after the action per share held before: Bonus 3:1 → 4.0, split
    Rs10 → Re1 → 10.0, consolidation Re1 → Rs10 → 0.1, bonus 1:1 plus split
    Rs10 → Rs5 → 4.0. None when the action doesn't change the share count (or the
    wording can't be read; the ex-date price jump is then the fallback).
    """
    m = 1.0
    found = False
    if not _NOT_EQUITY_BONUS.search(subject):
        if b := _BONUS.search(subject):
            new, held = float(b.group(1)), float(b.group(2))
            if new > 0 and held > 0:
                m *= (new + held) / held
                found = True
    if s := _SPLIT.search(subject):
        old_fv, new_fv = float(s.group(1)), float(s.group(2))
        if 0 < new_fv < old_fv:
            m *= old_fv / new_fv
            found = True
    if c := _CONSOLIDATION.search(subject):
        old_fv, new_fv = float(c.group(1)), float(c.group(2))
        if 0 < old_fv < new_fv:
            m *= old_fv / new_fv
            found = True
    return round(m, 6) if found else None


_RIGHTS = re.compile(rf"rights\D{{0,12}}?{_NUM}\s*:\s*{_NUM}(?:.*?prem\w*\D{{0,12}}?{_RUPEES}{_NUM})?", re.I)


def rights_terms(subject: str) -> tuple[float, float, float] | None:
    """'Rights 19:67 @ Premium Rs 215 Per Share' → (19 new, for 67 held, premium 215). None if not a rights issue."""
    if re.search(r"ncd|warrant|debenture|entitlement", subject, re.I):
        return None
    r = _RIGHTS.search(subject)
    if not r:
        return None
    new, held = float(r.group(1)), float(r.group(2))
    premium = float(r.group(3)) if r.group(3) else 0.0
    return (new, held, premium) if new > 0 and held > 0 else None


def dividend_per_share(subject: str) -> float | None:
    d = _DIVIDEND.search(subject)
    return float(d.group(1)) if d else None


def _date(value: str | None) -> date | None:
    if not value or value.strip() in ("-", ""):
        return None
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def fetch_actions(start: date, end: date, client: httpx.Client | None = None) -> list[dict]:
    """Raw API rows for equity corporate actions with ex-dates in [start, end]."""
    params = {"index": "equities", "from_date": f"{start:%d-%m-%Y}", "to_date": f"{end:%d-%m-%Y}"}
    own = client is None
    client = client or httpx.Client(headers=API_HEADERS, timeout=120, follow_redirects=True)
    try:
        resp = client.get(ACTIONS_URL, params=params)
        resp.raise_for_status()
        return resp.json()
    finally:
        if own:
            client.close()


def actions_frame(rows: list[dict]) -> pd.DataFrame:
    """API rows → typed table with kind, share multiplier and dividend per share."""
    df = pd.DataFrame(
        [
            {
                "symbol": (r.get("symbol") or "").strip().upper(),
                "series": (r.get("series") or "").strip().upper(),
                "isin": (r.get("isin") or "").strip().upper(),
                "company": (r.get("comp") or "").strip(),
                "ex_date": _date(r.get("exDate")),
                "record_date": _date(r.get("recDate")),
                "face_value": pd.to_numeric(r.get("faceVal"), errors="coerce"),
                "subject": (r.get("subject") or "").strip(),
            }
            for r in rows
        ],
        columns=["symbol", "series", "isin", "company", "ex_date", "record_date", "face_value", "subject"],
    )
    df["kind"] = df["subject"].map(classify)
    df["multiplier"] = df["subject"].map(share_multiplier).astype("float64")
    df["dividend"] = df["subject"].map(dividend_per_share).astype("float64")
    df = df.dropna(subset=["ex_date"]).drop_duplicates(subset=["symbol", "series", "ex_date", "subject"])
    return df.sort_values(["ex_date", "symbol"]).reset_index(drop=True)


def fetch_symbol_changes(client: httpx.Client | None = None) -> bytes:
    own = client is None
    client = client or httpx.Client(headers=ARCHIVE_HEADERS, timeout=60, follow_redirects=True)
    try:
        resp = client.get(SYMBOL_CHANGES_URL)
        resp.raise_for_status()
        return resp.content
    finally:
        if own:
            client.close()


def symbol_changes_frame(content: bytes) -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    raw.columns = [c.strip().upper() for c in raw.columns]
    df = pd.DataFrame({
        "company": raw["NAME OF THE COMPANY"].str.strip(),
        "old_symbol": raw["OLD SYMBOL"].str.strip().str.upper(),
        "new_symbol": raw["NEW SYMBOL"].str.strip().str.upper(),
        "effective_date": raw["EFFECTIVE DATE"].map(_date),
    })
    df = df[(df["old_symbol"] != "") & (df["new_symbol"] != "") & df["effective_date"].notna()]
    return df.drop_duplicates().sort_values("effective_date").reset_index(drop=True)
