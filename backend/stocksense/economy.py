"""
India's economy at a glance — the latest public value of each macro series (M1.6) with a year's
comparison and a plain-language note on why it matters for shares — written to
backend/data/economy.json, which the API serves at /economy.

    python -m stocksense economy-export

Written by the weekly `ingest-india-macro` run too. Only values that were public on the day
are used (`available_from`), so the card never shows a number before its release.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DATA_DIR

OUTPUT = DATA_DIR / "economy.json"
HISTORY_POINTS = 24
CPI_TARGET, CPI_BAND = 4.0, (2.0, 6.0)  # RBI's inflation target and tolerance band

SERIES = {
    "repo_rate": {"label": "RBI repo rate", "unit": "%",
                  "why": "The rate at which the RBI lends to banks. Cuts make loans cheaper, which usually helps banks' "
                         "lending, property and car sales; rises do the opposite."},
    "cpi_inflation": {"label": "Consumer inflation", "unit": "%",
                      "why": f"How fast prices are rising. The RBI aims for {CPI_TARGET:g}% (between {CPI_BAND[0]:g}% and "
                             f"{CPI_BAND[1]:g}%); inflation above that band usually means higher interest rates."},
    "iip_growth": {"label": "Industrial output growth", "unit": "%",
                   "why": "How much more factories, mines and power plants produced than a year earlier: an early read "
                          "on demand for metals, capital goods and energy."},
    "fx_reserves": {"label": "Forex reserves", "unit": "US$ bn",
                    "why": "Foreign currency the RBI holds. A large cushion lets it steady the rupee when money leaves "
                           "the country, which protects importers and companies with dollar debt."},
    "gsec_10y": {"label": "10-year government bond yield", "unit": "%",
                 "why": "What the government pays to borrow for ten years. When it rises, safe bonds compete with "
                        "shares, and share valuations tend to come down."},
}


def _value(series: str, v: float) -> float:
    return round(v / 1000, 1) if series == "fx_reserves" else round(v, 2)  # US$ million -> billion


def _public(df: pd.DataFrame, series: str, today: date) -> pd.DataFrame:
    s = df[(df["series"] == series) & (pd.to_datetime(df["available_from"]) <= pd.Timestamp(today))].copy()
    s["period"] = pd.to_datetime(s["period"])
    return s.sort_values("period")


def _year_ago(s: pd.DataFrame, series: str, latest: pd.Series) -> float | None:
    before = s[s["period"] <= latest["period"] - pd.DateOffset(years=1)]
    if not len(before):
        return None
    return _value(series, float(before["value"].iloc[-1]))


def note(series: str, value: float, year_ago: float | None, s: pd.DataFrame) -> str:
    """One sentence on where the series stands now, for a beginner."""
    if series == "repo_rate":
        if len(s) < 2:
            return f"The repo rate is {value:g}%."
        prev, last = float(s["value"].iloc[-2]), s.iloc[-1]
        move = "cut" if last["value"] < prev else "raised"
        return (f"The RBI last {move} it on {last['period']:%d %b %Y}, from {prev:g}% to {value:g}%"
                + (f"; a year earlier it was {year_ago:g}%." if year_ago is not None else "."))
    if series == "cpi_inflation":
        where = ("below the RBI's band" if value < CPI_BAND[0] else "above the RBI's band" if value > CPI_BAND[1]
                 else "within the RBI's band")
        return f"Prices rose {value:g}% over the year, {where}" + (f" (a year earlier: {year_ago:g}%)." if year_ago is not None else ".")
    if series == "iip_growth":
        state = "grew" if value >= 0 else "shrank"
        return f"Industrial output {state} {abs(value):g}% from a year earlier."
    if series == "fx_reserves":
        if year_ago:
            change = 100 * (value / year_ago - 1)
            return f"Reserves are {'up' if change >= 0 else 'down'} {abs(change):.0f}% from a year earlier."
        return f"Reserves stand at US$ {value:g} bn."
    if series == "gsec_10y":
        if year_ago is not None:
            move = value - year_ago
            return (f"The yield is {abs(move):.2f} points {'higher' if move >= 0 else 'lower'} than a year earlier."
                    if abs(move) >= 0.05 else "The yield is about where it was a year ago.")
        return f"The yield is {value:g}%."
    return ""


def build(df: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    out = []
    for series, meta in SERIES.items():
        s = _public(df, series, today)
        if not len(s):
            continue
        latest = s.iloc[-1]
        value = _value(series, float(latest["value"]))
        year_ago = _year_ago(s, series, latest)
        if series == "repo_rate":  # changes only: the history is a step line from the last few changes
            history = s.tail(HISTORY_POINTS)
        else:
            history = s[s["period"] > latest["period"] - pd.DateOffset(months=HISTORY_POINTS)]
        out.append({"series": series, "label": meta["label"], "unit": meta["unit"], "value": value,
                    "period": latest["period"].date().isoformat(), "year_ago": year_ago,
                    "released": pd.Timestamp(latest["available_from"]).date().isoformat(),
                    "source": str(latest["source"]), "note": note(series, value, year_ago, s), "why": meta["why"],
                    "history": [[p.date().isoformat(), _value(series, float(v))]
                                for p, v in zip(history["period"], history["value"])]})
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "as_of": today.isoformat(), "series": out}


def write(df: pd.DataFrame, output: Path = OUTPUT, today: date | None = None) -> dict:
    doc = build(df, today)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return doc


def write_from_lake(lake, output: Path = OUTPUT, today: date | None = None) -> dict:
    return write(lake.query("select * from india_macro"), output, today)

