"""
India macro job (M1.6): RBI repo rate, CPI, IIP, forex reserves and the 10-year yield, each with
the date it became public -> lake table `india_macro` (series, period, value, unit, available_from, source).

    python -m stocksense ingest-india-macro            # refresh everything (a few dozen requests)

Also writes data/economy.json (the dashboard card). Runs weekly in the engine. A source that fails is skipped and the others are still saved.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from .. import economy
from ..lake import Lake
from ..log import get_logger
from ..sources import india_macro as im

log = get_logger(__name__)

DATASET = "india_macro"
SOURCE = "india_macro"
CPI_FROM, IIP_FROM = 2013, 2013  # MoSPI's API serves these series from about here


def collect(client: httpx.Client, today: date, pause: float = 0.5) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    failed: list[str] = []

    def attempt(name: str, fn):
        try:
            got = fn()
            rows.extend(got)
            log.info(f"{SOURCE}: {name} {len(got)} rows")
        except (httpx.HTTPError, ValueError) as exc:
            failed.append(name)
            log.warning(f"{SOURCE}: {name} failed: {exc}")
        time.sleep(pause)

    attempt("repo_rate", lambda: im.fetch_policy_rate(client))
    for year in range(CPI_FROM, today.year + 1):
        attempt(f"cpi {year}", lambda y=year: im.fetch_cpi(client, y))
    for year in range(IIP_FROM, today.year + 1):
        attempt(f"iip {year}", lambda y=year: im.fetch_iip(client, y))
    for series in im.FRED_SERIES:
        attempt(series, lambda s=series: im.fetch_fred(client, s))
    return rows, failed


def frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["series", "period", "value", "unit", "available_from", "source"])
    if not len(df):
        return df
    # One value per series and period (a re-fetched month replaces the earlier copy).
    df = df.drop_duplicates(["series", "period"], keep="last").sort_values(["series", "period"])
    return df.reset_index(drop=True)


def as_of(df: pd.DataFrame, series: str, day: date) -> float | None:
    """The latest value of `series` that was public on `day` (no look-ahead)."""
    known = df[(df["series"] == series) & (pd.to_datetime(df["available_from"]) <= pd.Timestamp(day))]
    if not len(known):
        return None
    return float(known.sort_values("period")["value"].iloc[-1])


def run(lake: Lake | None = None, today: date | None = None, transport: httpx.BaseTransport | None = None,
        economy_output: Path = economy.OUTPUT) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    today = today or date.today()
    with httpx.Client(headers=im.HEADERS, timeout=60, follow_redirects=True, transport=transport) as client:
        rows, failed = collect(client, today, pause=0 if transport else 0.5)
    df = frame(rows)
    if not len(df):
        raise RuntimeError(f"No India macro series could be fetched ({', '.join(failed)})")
    folder = lake.raw_dir(SOURCE, today)
    (folder / "rows.json").write_text(json.dumps(rows, default=str), encoding="utf-8")
    lake.write_table(df, DATASET)
    economy.write(df, economy_output, today=today)
    summary = df.groupby("series")["period"].agg(["min", "max", "count"])
    log.info(f"{SOURCE}: {len(df)} rows\n{summary.to_string()}" + (f"\nfailed: {', '.join(failed)}" if failed else ""))
    return df
