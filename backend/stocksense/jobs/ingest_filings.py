"""
Filings & flows job — NSE corporate announcements, insider trades and FII/DII flows
into the data lake.

    python -m stocksense ingest-filings                    # 2015 → this month, then today's FII/DII
    python -m stocksense ingest-filings --start 2026-09-01

Raw copies, one per month: raw/nse_announcements/<YYYY-MM-01>/announcements.json and
raw/nse_insider/<YYYY-MM-01>/insider.json. Past months are fetched once; the latest two
months are fetched again each run (late filings). Clean datasets, one partition per day:
  • announcements   by broadcast date (IST)
  • insider_trades  by disclosure date (IST) — the day the market could know
  • fii_dii         provisional FII/DII cash flows, ₹ crore (history starts when this job first ran)
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta

import pandas as pd

from ..lake import Lake
from ..log import get_logger
from ..sources import nse_filings

log = get_logger(__name__)

START = date(2015, 1, 1)
REFETCH_MONTHS = 2
PAUSE_SECONDS = 1.0  # one request a second to NSE's API


def months(start: date, end: date) -> list[tuple[date, date]]:
    """[(first day, last day)] for every month touching [start, end]."""
    out, d = [], date(start.year, start.month, 1)
    while d <= end:
        nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        out.append((d, min(nxt - timedelta(days=1), end)))
        d = nxt
    return out


def _sync(lake: Lake, source: str, name: str, fetch, frame, dataset: str, date_col: str,
          start: date, end: date, pause: float) -> int:
    windows = months(start, end)
    recent = {m for m, _ in windows[-REFETCH_MONTHS:]}
    rows_written = 0
    with nse_filings.client() as c:
        for first, last in windows:
            path = lake.raw_dir(source, first) / name
            if not path.exists() or first in recent:
                try:
                    rows = fetch(c, first, last)
                except Exception as exc:  # NSE hiccup: keep going, the next run retries
                    log.warning(f"{source}: {first:%Y-%m} failed: {exc}")
                    continue
                path.write_text(json.dumps(rows), encoding="utf-8")
                time.sleep(pause)
            else:
                continue  # already have this (older) month
            df = frame(json.loads(path.read_text(encoding="utf-8")))
            if not df.empty:
                lake.write_parquet(df, dataset, date_col=date_col, refresh=False)
                rows_written += len(df)
            log.info(f"{source}: {first:%Y-%m} — {len(df)} rows")
    lake.refresh_catalog()
    return rows_written


def run_announcements(lake: Lake, start: date, end: date, pause: float = PAUSE_SECONDS) -> int:
    return _sync(lake, "nse_announcements", "announcements.json", nse_filings.fetch_announcements,
                 nse_filings.announcements_frame, "announcements", "broadcast_at", start, end, pause)


def run_insider(lake: Lake, start: date, end: date, pause: float = PAUSE_SECONDS) -> int:
    return _sync(lake, "nse_insider", "insider.json", nse_filings.fetch_insider_trades,
                 nse_filings.insider_frame, "insider_trades", "disclosed_at", start, end, pause)


def run_fii_dii(lake: Lake, today: date | None = None) -> pd.DataFrame:
    with nse_filings.client() as c:
        rows = nse_filings.fetch_fii_dii(c)
    folder = lake.raw_dir("nse_fii_dii", today or date.today())
    (folder / "fii_dii.json").write_text(json.dumps(rows), encoding="utf-8")
    df = nse_filings.fii_dii_frame(rows)
    if not df.empty:
        lake.write_parquet(df, "fii_dii", date_col="date")
    return df


def run(start: date | None = None, end: date | None = None, lake: Lake | None = None) -> None:
    lake = lake or Lake.from_settings()
    start, end = start or START, end or date.today()
    log.info(f"announcements: {run_announcements(lake, start, end)} rows written")
    log.info(f"insider trades: {run_insider(lake, start, end)} rows written")
    df = run_fii_dii(lake)
    log.info(f"FII/DII: {len(df)} rows for {', '.join(sorted({str(d.date()) for d in df['date']}))}")


def show(symbol: str, since: date | None = None, limit: int = 20, lake: Lake | None = None) -> None:
    """Print a company's latest announcements and insider trades from the lake."""
    lake = lake or Lake.from_settings()
    symbol = symbol.upper()
    since = since or date.today() - timedelta(days=365)
    present = set(lake.datasets())
    with pd.option_context("display.width", 200, "display.max_colwidth", 90, "display.max_columns", 12):
        if "announcements" in present:
            ann = lake.query("select broadcast_at, category, summary from announcements "
                             "where symbol = ? and date >= ? order by broadcast_at desc limit ?", [symbol, since, limit])
            print(f"\n{symbol} — announcements since {since} ({len(ann)} shown)")
            print(ann.to_string(index=False) if len(ann) else "  none")
        if "insider_trades" in present:
            ins = lake.query("select disclosed_at, person, person_category, transaction, mode, quantity, value "
                             "from insider_trades where symbol = ? and date >= ? order by disclosed_at desc limit ?",
                             [symbol, since, limit])
            print(f"\n{symbol} — insider trades since {since} ({len(ins)} shown)")
            print(ins.to_string(index=False) if len(ins) else "  none")
