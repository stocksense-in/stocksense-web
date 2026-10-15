"""
GDELT 1.0 daily event files — every news-reported event worldwide, coded with
who did what to whom (CAMEO codes), where, how intense (Goldstein scale), how
widely covered (mentions, articles) and the coverage's tone. One file per day
since 1 Apr 2013: https://data.gdeltproject.org/events/<YYYYMMDD>.export.CSV.zip

A day's file holds the events *added* that day, including reports about older
events. We date everything by the file day (the day it was known), never by the
event's own SQLDATE, so features built from it can't look into the future.

`parse` reads the columns we use; `daily_aggregates` and `salient_events` turn a
day into the two clean datasets (see stocksense/jobs/ingest_gdelt.py).
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

import numpy as np
import pandas as pd

BASE = "https://data.gdeltproject.org/events"
FIRST_DAY = date(2013, 4, 1)
HEADERS = {"User-Agent": "Mozilla/5.0 (StockSense research; GDELT bulk download)"}

# GDELT 1.0 event codebook: 58 tab-separated columns, no header row.
COLUMNS = [
    "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode", "Actor1EthnicCode",
    "Actor1Religion1Code", "Actor1Religion2Code", "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode", "Actor2EthnicCode",
    "Actor2Religion1Code", "Actor2Religion2Code", "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode", "QuadClass", "GoldsteinScale",
    "NumMentions", "NumSources", "NumArticles", "AvgTone",
    "Actor1Geo_Type", "Actor1Geo_FullName", "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code",
    "Actor1Geo_Lat", "Actor1Geo_Long", "Actor1Geo_FeatureID",
    "Actor2Geo_Type", "Actor2Geo_FullName", "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code",
    "Actor2Geo_Lat", "Actor2Geo_Long", "Actor2Geo_FeatureID",
    "ActionGeo_Type", "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_Lat", "ActionGeo_Long", "ActionGeo_FeatureID",
    "DATEADDED", "SOURCEURL",
]
USED = {
    "GLOBALEVENTID": "event_id", "SQLDATE": "event_date",
    "Actor1Name": "actor1", "Actor1CountryCode": "actor1_country",
    "Actor2Name": "actor2", "Actor2CountryCode": "actor2_country",
    "IsRootEvent": "is_root", "EventCode": "event_code", "EventRootCode": "root",
    "QuadClass": "quad", "GoldsteinScale": "goldstein", "NumMentions": "mentions",
    "NumSources": "sources", "NumArticles": "articles", "AvgTone": "tone",
    "ActionGeo_FullName": "place", "ActionGeo_CountryCode": "country", "SOURCEURL": "url",
}

# CAMEO root codes (two digits). QuadClass: 1 verbal cooperation, 2 material
# cooperation, 3 verbal conflict, 4 material conflict.
CAMEO_ROOTS = {
    "01": "public statement", "02": "appeal", "03": "intent to cooperate", "04": "consult",
    "05": "diplomatic cooperation", "06": "material cooperation", "07": "provide aid",
    "08": "yield", "09": "investigate", "10": "demand", "11": "disapprove", "12": "reject",
    "13": "threaten", "14": "protest", "15": "military posture", "16": "reduce relations",
    "17": "coerce", "18": "assault", "19": "fight", "20": "mass violence",
}
# Hostile roots: threats, protest, force posture, sanctions/cutting ties, coercion, violence.
CONFLICT_ROOTS = {"13", "14", "15", "16", "17", "18", "19", "20"}
INDIA = "IND"  # CAMEO actor country code (actors); FIPS "IN" for places


def file_name(day: date) -> str:
    return f"{day:%Y%m%d}.export.CSV.zip"


def url_for(day: date) -> str:
    return f"{BASE}/{file_name(day)}"


def parse(content: bytes) -> pd.DataFrame:
    """One day's zip → the columns in USED, typed. Malformed rows are skipped."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        raw = pd.read_csv(
            z.open(z.namelist()[0]), sep="\t", header=None, names=COLUMNS, usecols=list(USED),
            dtype=str, keep_default_na=False, quoting=3, on_bad_lines="skip", encoding_errors="replace",
        )
    df = raw.rename(columns=USED)
    # Truncated lines parse with empty trailing fields; a real event has an id and a CAMEO code.
    df = df[df["event_id"].str.isdigit() & (df["root"].str.len() > 0)].copy()
    for col in ("goldstein", "tone"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
    for col in ("mentions", "sources", "articles", "quad", "is_root"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int32")
    df["root"] = df["root"].str.zfill(2)
    return df


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    ok = values.notna() & (weights > 0)
    return float(np.average(values[ok], weights=weights[ok])) if ok.any() else float("nan")


def daily_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    One day's events → one row per (country, root, quad, india): event count, total
    mentions and articles, and mention-weighted Goldstein and tone. `country` is
    where it happened (FIPS code, "" if unknown); `india` is True when an Indian
    actor is involved.
    """
    df = df.assign(
        india=(df["actor1_country"] == INDIA) | (df["actor2_country"] == INDIA),
        w_gold=df["goldstein"].astype("float64") * df["mentions"],
        w_tone=df["tone"].astype("float64") * df["mentions"],
    )
    keys = ["country", "root", "quad", "india"]
    g = df.groupby(keys, sort=True, dropna=False)
    out = g.agg(events=("event_id", "size"), root_events=("is_root", "sum"),
                mentions=("mentions", "sum"), articles=("articles", "sum"),
                w_gold=("w_gold", "sum"), w_tone=("w_tone", "sum")).reset_index()
    weight = out["mentions"].where(out["mentions"] > 0)
    out["goldstein"] = (out.pop("w_gold") / weight).astype("float32")
    out["tone"] = (out.pop("w_tone") / weight).astype("float32")
    for col in ("events", "root_events", "mentions", "articles"):
        out[col] = out[col].astype("int32")
    out["quad"] = out["quad"].astype("int8")
    return out


def salient_events(df: pd.DataFrame, min_articles: int = 10) -> pd.DataFrame:
    """
    Widely covered events worth keeping individually, with their source URL as
    evidence: root events with at least `min_articles` articles that are hostile
    (CONFLICT_ROOTS) or involve India.
    """
    india = (df["actor1_country"] == INDIA) | (df["actor2_country"] == INDIA) | (df["country"] == "IN")
    keep = (df["is_root"] == 1) & (df["articles"] >= min_articles) & (df["root"].isin(CONFLICT_ROOTS) | india)
    cols = ["event_id", "event_date", "actor1", "actor1_country", "actor2", "actor2_country",
            "event_code", "root", "quad", "goldstein", "mentions", "sources", "articles", "tone",
            "place", "country", "url"]
    out = df.loc[keep, cols].copy()
    out["india"] = india[keep].to_numpy()
    out["event_id"] = pd.to_numeric(out["event_id"], errors="coerce").astype("Int64")
    out["event_date"] = pd.to_datetime(out["event_date"], format="%Y%m%d", errors="coerce").dt.date
    return out.reset_index(drop=True)
