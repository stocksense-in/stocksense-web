"""
Geopolitics engine: tags news headlines with the macro topics they are about,
maps each topic to the Indian sectors it usually moves, and rolls recent news
up into a per-sector exposure reading.

Everything is a readable rule below — no model. A headline can hit several
topics. To tune the engine, edit TOPICS; tests in tests/test_geo.py pin the
behaviour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .sources.news import Headline

# Effect of a topic on a sector.
RISK, OPPORTUNITY, HAVEN, WATCH = "risk", "opportunity", "haven", "watch"
EFFECT_LABEL = {RISK: "At risk", OPPORTUNITY: "Opportunity", HAVEN: "Safe haven", WATCH: "Watch"}

# Sector display name → StockSense sector code (for links into the screener), when one exists.
SECTOR_CODES: dict[str, str | None] = {
    "Oil & Gas": "energy",
    "Aviation": None,
    "Defence & Aerospace": "defence",
    "Gold & Silver": None,
    "IT Services": "it",
    "Pharma": "pharma",
    "Banking": "bank",
    "NBFC": "nbfc",
    "Real Estate": "realestate",
    "Automobile": "auto",
    "Metals & Materials": "materials",
    "Paints & Chemicals": "materials",
    "FMCG": "fmcg",
    "Electronics": "electronics",
}


@dataclass(frozen=True)
class Topic:
    name: str
    pattern: re.Pattern
    effects: dict[str, str]  # sector → effect


def _words(*terms: str) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(terms) + r")\b", re.IGNORECASE)


TOPICS: list[Topic] = [
    Topic(
        "Conflict",
        _words(r"(?<!trade )(?<!price )(?<!tariff )wars?", r"missiles?", r"air ?strikes?", r"drone attacks?", r"military", r"troops",
               r"border clash(es)?", r"armed conflict", r"hostilities", r"escalat\w*", r"Hormuz", r"Red Sea", r"Houthis?",
               r"attacks? on"),
        {"Oil & Gas": RISK, "Aviation": RISK, "Defence & Aerospace": OPPORTUNITY, "Gold & Silver": HAVEN},
    ),
    Topic(
        "Ceasefire",
        _words(r"ceasefire", r"truce", r"peace (deal|talks|agreement)", r"de-?escalat\w*"),
        {"Aviation": OPPORTUNITY, "Oil & Gas": WATCH, "Gold & Silver": WATCH},
    ),
    Topic(
        "Oil",
        _words(r"crude", r"brent", r"oil prices?", r"OPEC\+?", r"petrol", r"diesel", r"fuel prices?"),
        {"Oil & Gas": WATCH, "Aviation": RISK, "Paints & Chemicals": RISK},
    ),
    Topic(
        "Trade",
        _words(r"tariffs?", r"trade (deal|pact|war|talks|agreement)", r"import duty", r"export curbs?",
               r"sanctions?", r"H-1B", r"anti-dumping"),
        {"IT Services": WATCH, "Pharma": WATCH, "Metals & Materials": WATCH},
    ),
    Topic(
        "Interest rates",
        _words(r"RBI", r"repo rate", r"rate (cut|hike)s?", r"monetary policy", r"inflation", r"CPI",
               r"US Fed", r"Federal Reserve", r"bond yields?", r"MPC"),
        {"Banking": WATCH, "NBFC": WATCH, "Real Estate": WATCH, "Automobile": WATCH},
    ),
    Topic(
        "Currency",
        _words(r"rupee", r"dollar index", r"forex", r"FII outflows?", r"FPI outflows?"),
        {"IT Services": OPPORTUNITY, "Oil & Gas": RISK, "Electronics": RISK},
    ),
    Topic(
        "Commodities",
        _words(r"gold", r"silver", r"copper", r"aluminium", r"steel prices?", r"metal prices?"),
        {"Gold & Silver": HAVEN, "Metals & Materials": WATCH},
    ),
    Topic(
        "Defence",
        _words(r"defence", r"defense", r"DRDO", r"Tejas", r"Rafale", r"Agniveer", r"warships?",
               r"Hindustan Aeronautics", r"Bharat Electronics"),
        {"Defence & Aerospace": OPPORTUNITY},
    ),
    Topic(
        "China",
        _words(r"China", r"Chinese", r"Beijing"),
        {"Metals & Materials": WATCH, "Pharma": WATCH, "Electronics": WATCH},
    ),
    Topic(
        "Monsoon",
        _words(r"monsoon", r"rainfall", r"kharif", r"rabi", r"crop output", r"El Ni[nñ]o"),
        {"FMCG": WATCH, "Automobile": WATCH},
    ),
]


@dataclass
class Event:
    title: str
    link: str
    source: str
    published: datetime | None
    topics: list[str] = field(default_factory=list)
    sectors: dict[str, str] = field(default_factory=dict)  # sector → effect

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "published": self.published.isoformat() if self.published else None,
            "topics": self.topics,
            "sectors": [
                {"sector": s, "code": SECTOR_CODES.get(s), "effect": e, "label": EFFECT_LABEL[e]}
                for s, e in self.sectors.items()
            ],
        }


def classify(headline: Headline) -> Event:
    """Topics and sector effects for one headline. When topics disagree on a sector, the strongest effect wins."""
    event = Event(headline.title, headline.link, headline.source, headline.published)
    strength = {RISK: 3, OPPORTUNITY: 3, HAVEN: 2, WATCH: 1}
    for topic in TOPICS:
        if topic.pattern.search(headline.title):
            event.topics.append(topic.name)
            for sector, effect in topic.effects.items():
                current = event.sectors.get(sector)
                if current is None or strength[effect] > strength[current]:
                    event.sectors[sector] = effect
    return event


def relevant_events(headlines: list[Headline]) -> list[Event]:
    """Only headlines that touch at least one macro topic."""
    return [e for e in (classify(h) for h in headlines) if e.topics]


HALF_LIFE_HOURS = 48  # a two-day-old headline counts half as much as a fresh one


def _weight(published: datetime | None, now: datetime) -> float:
    if published is None:
        return 0.5
    age_hours = max(0.0, (now - published).total_seconds() / 3600)
    return 0.5 ** (age_hours / HALF_LIFE_HOURS)


def exposure(events: list[Event], now: datetime | None = None) -> list[dict]:
    """
    Per-sector reading from recent events, most exposed first:
      sensitivity 0–100 — share of recent macro news that concerns the sector (recency-weighted)
      effect — the dominant effect across those headlines
      headlines — how many relevant headlines mention it
    """
    now = now or datetime.now(timezone.utc)
    totals: dict[str, dict] = {}
    all_weight = sum(_weight(e.published, now) for e in events) or 1.0
    for event in events:
        w = _weight(event.published, now)
        for sector, effect in event.sectors.items():
            t = totals.setdefault(sector, {"weight": 0.0, "count": 0, "effects": {}})
            t["weight"] += w
            t["count"] += 1
            t["effects"][effect] = t["effects"].get(effect, 0.0) + w

    rows = []
    for sector, t in totals.items():
        effect = max(t["effects"], key=t["effects"].get)
        rows.append(
            {
                "sector": sector,
                "code": SECTOR_CODES.get(sector),
                "sensitivity": round(100 * t["weight"] / all_weight),
                "effect": effect,
                "label": EFFECT_LABEL[effect],
                "headlines": t["count"],
            }
        )
    return sorted(rows, key=lambda r: r["sensitivity"], reverse=True)
