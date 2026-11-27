"""
Company events (M2.3) — what a company has told the exchange over the past year, and what
its promoters and directors did with their own shares — written to backend/data/events.json,
which the API serves at /stocks/{symbol}/events. The public API never reads the lake.

    python -m stocksense events-export

Announcements: NSE files ~180k a year, most of them routine (newspaper copies, trading-window
notices, investor-meet schedules). Only the kinds a beginner should notice are kept, each
tagged with a group:

  warning     defaults, fraud, forensic audits, insolvency, an auditor resigning, trading
              suspended, operations disrupted or closed, results delayed
  legal       regulatory actions, litigation, licences granted or withdrawn
  results     board-meeting outcomes and financial-result filings
  orders      orders and contracts won
  deals       acquisitions, mergers, demergers, disposals, restructuring, tie-ups, open offers
  capital     dividends, bonuses, splits, buybacks, rights, preferential issues, QIPs
  rating      credit ratings
  management  appointments, resignations, changes in directors or auditors
  business    press releases, capacity, new products, monthly business updates
  exchange    the exchange asking about a price or volume spike or a news report

Insider trades: market purchases and sales by promoters, directors and key managers over
the two years to the end of NSE's insider feed in the lake.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .config import DATA_DIR

OUTPUT = DATA_DIR / "events.json"
WINDOW_DAYS = 365        # announcements kept from the past year
PER_COMPANY = 8          # announcements per company (warnings always make the cut)
INSIDER_DAYS = 730       # insider trades over two years
INSIDER_TRADES = 6       # most recent insider trades listed
TITLE_CHARS = 160
RUPEES_PER_CRORE = 1e7
INSIDERS = ("Promoters", "Promoter Group", "Director", "Key Managerial Personnel")
SIDES = {"Market Purchase": "buy", "Market Sale": "sell"}

# First match wins, so the red flags and exchange queries are tested before the broad groups.
GROUPS: list[tuple[str, re.Pattern]] = [(g, re.compile(p, re.I)) for g, p in [
    ("warning", r"default|fraud|forensic|insolvency|resignation of statutory auditor|suspension of trading|"
                r"strikes|disruption of operations|closure of operations|delayed/non-submission|rescission"),
    ("exchange", r"spurt in volume|price movement|verification|clarification"),
    ("legal", r"action\(s\)|litigation|material issue|licenses"),
    ("results", r"outcome of board meeting|financial result|integrated filing- financial|board meeting cancelled|"
                r"revision of financial"),
    ("orders", r"bagging|awarding of order"),
    ("deals", r"acquisition|amalgamation|merger|sale or disposal|scheme of arrangement|diversification|"
              r"restructuring|memorandum of understanding|^agreements$|tie up|open offer|delisting"),
    ("capital", r"dividend|^bonus$|stock split|buy ?back|rights issue|preferential issue|qualified institutional|"
                r"offer for sale|issue of securities"),
    ("rating", r"credit rating"),
    ("management", r"appointment|change in management|resignation|change in director|cessation|retirement|"
                   r"demise|change in auditors"),
    ("business", r"press release|capacity addition|commencement of commercial|product launch|"
                 r"monthly business updates|new line\(s\) of business|postponement of commercial"),
]]

# Routine: a partly paid-up series or a debenture reaching its end is "suspended", which isn't a red flag.
_ROUTINE_SUSPENSION = re.compile(r"partly paid|debenture|commercial paper|bonds?\b|\bNCD", re.I)
LINK_PREFIX = "https://nsearchives.nseindia.com/corporate/"  # the .in mirror's links are kept whole

_QUOTED = re.compile(r"(?:regarding|about|on)\s+'(.+)'\.?\s*$", re.S)
_TITLED = re.compile(r'titled\s+(?:as\s+)?["“](.+?)["”]', re.S)
# NSE's and the companies' wrappers around what actually happened, removed from the front.
_WRAPPERS = [re.compile(p, re.I) for p in (
    r"^.*?has informed the Exchange\s*(?:about|regarding|that|on)?\s*",
    r"^.*?has submitted to the Exchange,?\s*",
    r"^Members of the Exchange are hereby informed that\s*",
    r"^(?:the\s+)?(?:outcome of (?:the\s+)?board meeting\s*[-–:]?\s*)?disclosure (?:under|pursuant to) regulation 30 "
    r"(?:\(\d+\)\s*)?(?:read with [^,]*?)?of (?:the\s+)?SEBI \(Listing Obligations and Disclosure Requirements\) "
    r"Regulations,?\s*2015\s*(?:\(\s*(?:SEBI\s+)?Listing Regulations\s*\)|\(\s*LODR\s*\))?\s*[-–:,]*\s*",
    r"^(?:intimation for submission of\s+)?media release (?:on|for) the subject\s*",
)]


def group_of(category: str | None, summary: str | None = None) -> str | None:
    if category == "Suspension of Trading" and _ROUTINE_SUSPENSION.search(summary or ""):
        return None
    for name, pattern in GROUPS:
        if category and pattern.search(category):
            return name
    return None


def title_of(summary: str | None, category: str) -> str:
    """The announcement's own words without NSE's "X Limited has informed the Exchange regarding" wrapper."""
    text = " ".join((summary or "").split())
    quoted = _QUOTED.search(text)
    if quoted:
        text = quoted.group(1)
    titled = _TITLED.search(text)
    if titled:
        text = titled.group(1)
    for wrapper in _WRAPPERS:
        text = wrapper.sub("", text)
    text = text.strip(" .'-–:,") or category
    text = text[0].upper() + text[1:]
    return text if len(text) <= TITLE_CHARS else text[: TITLE_CHARS - 1].rstrip() + "…"


def short_link(url: str | None) -> str | None:
    """Filing PDFs all live under NSE's archive folder; keep only the file name (the API restores the address)."""
    if not isinstance(url, str) or not url:  # missing attachments come through as NaN
        return None
    return url[len(LINK_PREFIX):] if url.startswith(LINK_PREFIX) else url


def full_link(link: str | None) -> str | None:
    return None if not link else link if link.startswith("http") else LINK_PREFIX + link


def _cr(value) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value) / RUPEES_PER_CRORE, 2)


def money(crore: float) -> str:
    """₹ amounts the way Indian readers say them: lakh under a crore."""
    if 0 < abs(crore) < 1:
        return f"₹{crore * 100:,.1f} lakh".replace(".0 lakh", " lakh")
    return f"₹{crore:,.1f} cr".replace(".0 cr", " cr")


def announcements(df: pd.DataFrame, today: date) -> dict[str, dict]:
    """symbol -> {"items": [...], "counts": {group: n}} over the past year."""
    if not len(df):
        return {}
    df = df.copy()
    df["group"] = [group_of(c, s) for c, s in zip(df["category"], df["summary"])]
    df = df[df["group"].notna() & df["symbol"].notna()]
    df["at"] = pd.to_datetime(df["broadcast_at"])
    df = df[df["at"] >= pd.Timestamp(today - timedelta(days=WINDOW_DAYS))]
    df["title"] = [title_of(s, c) for s, c in zip(df["summary"], df["category"])]
    # NSE sometimes posts the same filing twice a few minutes apart; keep a copy with the PDF.
    df["has_link"] = df["attachment"].map(lambda u: isinstance(u, str) and bool(u))
    df = (df.sort_values(["has_link", "at"], ascending=False).drop_duplicates(["symbol", "title"])
          .sort_values("at", ascending=False))
    out = {}
    for symbol, g in df.groupby("symbol", sort=False):
        warnings = g[g["group"] == "warning"].head(PER_COMPANY // 2)
        rest = g[g["group"] != "warning"].head(PER_COMPANY - len(warnings))
        keep = pd.concat([warnings, rest]).sort_values("at", ascending=False)
        out[symbol] = {
            "items": [{"at": r.at.isoformat(timespec="minutes"), "group": r.group, "category": r.category,
                       "title": r.title, "link": short_link(r.attachment)} for r in keep.itertuples()],
            "counts": {k: int(v) for k, v in g["group"].value_counts().items()},
        }
    return out


def insider_trades(df: pd.DataFrame) -> tuple[dict[str, dict], str | None]:
    """symbol -> {"bought_cr", "sold_cr", "buys", "sells", "trades": [...]}, and the feed's last day."""
    if not len(df):
        return {}, None
    df = df.copy()
    df["day"] = pd.to_datetime(df["date"])
    last = df["day"].max()
    df = df[df["person_category"].isin(INSIDERS) & df["mode"].isin(SIDES) & df["symbol"].notna()
            & (df["day"] > last - pd.Timedelta(days=INSIDER_DAYS))]
    df["side"] = df["mode"].map(SIDES)
    df = df.sort_values("day", ascending=False)
    out = {}
    for symbol, g in df.groupby("symbol", sort=False):
        value = pd.to_numeric(g["value"], errors="coerce")
        out[symbol] = {
            "bought_cr": _cr(value[g["side"] == "buy"].sum()), "sold_cr": _cr(value[g["side"] == "sell"].sum()),
            "buys": int((g["side"] == "buy").sum()), "sells": int((g["side"] == "sell").sum()),
            "trades": [{"date": r.day.date().isoformat(), "person": r.person, "role": r.person_category,
                        "side": r.side, "value_cr": _cr(r.value),
                        "pct_after": None if pd.isna(r.pct_after) else round(float(r.pct_after), 2)}
                       for r in g.head(INSIDER_TRADES).itertuples()],
        }
    return out, last.date().isoformat()


def build(ann: pd.DataFrame, insiders: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    notices = announcements(ann, today)
    trades, insider_until = insider_trades(insiders)
    companies = {s: {"announcements": notices.get(s, {}).get("items", []),
                     "counts": notices.get(s, {}).get("counts", {}),
                     "insiders": trades.get(s)}
                 for s in sorted(set(notices) | set(trades))}
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "NSE corporate announcements and insider-trading disclosures (SEBI PIT)",
            "since": (today - timedelta(days=WINDOW_DAYS)).isoformat(),
            "insiders_until": insider_until, "companies": companies}


def insider_note(entry: dict | None, until: str | None) -> str | None:
    """One plain sentence on what the promoters and directors did, with the usual caution."""
    ins = (entry or {}).get("insiders")
    if not ins or not (ins["buys"] or ins["sells"]):
        return None
    when = f" in the two years to {date.fromisoformat(until).strftime('%b %Y')}" if until else ""
    bought, sold = ins["bought_cr"] or 0, ins["sold_cr"] or 0
    text = (f"Promoters, directors and key managers bought {money(bought)} and sold {money(sold)} "
            f"of shares on the market{when}.")
    if bought > sold:
        return text + " Insiders buying with their own money is one of the clearer signals of confidence."
    return text + (" Insiders sell for many reasons (taxes, spreading their wealth, a family split), "
                   "so selling alone says less than buying.")


def write(lake, output: Path = OUTPUT, today: date | None = None) -> dict:
    today = today or date.today()
    since = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    present = set(lake.datasets())
    ann = (lake.query("select symbol, category, summary, attachment, broadcast_at from announcements "
                      "where date >= ?", [since]) if "announcements" in present else pd.DataFrame())
    ins = (lake.query("select symbol, person, person_category, mode, value, pct_after, date from insider_trades "
                      f"where date >= (select max(date) from insider_trades) - interval {INSIDER_DAYS} day")
           if "insider_trades" in present else pd.DataFrame())
    doc = build(ann, ins, today)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return doc
