"""
Market series job — the daily index and macro history the event study and models use.

    python -m stocksense ingest-indices          # NSE index closes, 2012 → today (daily)
    python -m stocksense ingest-macro            # crude, gold, rupee, US rates… full history (daily)

• NSE indices: raw/nse_indices/<day>/ind_close_all_<DDMMYYYY>.csv → clean/index_prices
  (one partition per day; every NSE index with OHLC, turnover, P/E, P/B, yield).
• Macro: raw/yahoo_chart/<today>/<code>.json → clean/macro_prices (one table, all
  series, rewritten each run — the full history is a single small request per series).
"""

from __future__ import annotations

import json
import time
from datetime import date

import httpx
import pandas as pd

from ..downloads import RawFile, days_between, download_all, raw_path
from ..lake import Lake
from ..log import get_logger
from ..sources import nse_indices, yahoo_history

log = get_logger(__name__)

INDEX_SOURCE, INDEX_DATASET = "nse_indices", "index_prices"
MACRO_SOURCE, MACRO_DATASET = "yahoo_chart", "macro_prices"
INDEX_START = date(2012, 1, 1)


def index_files(start: date, end: date) -> list[RawFile]:
    return [RawFile(d, nse_indices.url_for(d), nse_indices.file_name(d)) for d in days_between(start, end)]


def run_indices(start: date | None = None, end: date | None = None, *, rebuild: bool = False,
                lake: Lake | None = None) -> int:
    lake = lake or Lake.from_settings()
    start, end = start or INDEX_START, end or date.today()
    files = index_files(start, end)
    download_all(lake, INDEX_SOURCE, files, headers=nse_indices.HEADERS, per_second=3, workers=2)
    built = 0
    for f in files:
        path = raw_path(lake, INDEX_SOURCE, f)
        if not path.exists() or (not rebuild and lake.partition_path(INDEX_DATASET, f.day).exists()):
            continue
        try:
            df = nse_indices.parse(path.read_bytes())
        except Exception as exc:  # a malformed file: report it, keep going
            log.warning(f"{INDEX_SOURCE}: could not parse {path.name}: {exc}")
            continue
        if not df.empty:
            lake.write_parquet(df, INDEX_DATASET, day=f.day, refresh=False)
            built += 1
    lake.refresh_catalog()
    log.info(f"{INDEX_DATASET}: built {built} new day(s)")
    return built


def run_macro(lake: Lake | None = None, today: date | None = None, transport: httpx.BaseTransport | None = None) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    folder = lake.raw_dir(MACRO_SOURCE, today or date.today())
    frames = []
    with httpx.Client(headers=yahoo_history.HEADERS, timeout=60, transport=transport) as client:
        for code, (ticker, _) in yahoo_history.SERIES.items():
            try:
                payload = yahoo_history.fetch(ticker, client)
            except httpx.HTTPError as exc:
                log.warning(f"{MACRO_SOURCE}: {code} ({ticker}) failed: {exc}")
                continue
            (folder / f"{code}.json").write_text(json.dumps(payload), encoding="utf-8")
            df = yahoo_history.to_frame(code, payload)
            log.info(f"{MACRO_SOURCE}: {code} {len(df)} days" + (f" from {df['date'].min()}" if len(df) else ""))
            frames.append(df)
            time.sleep(0.4 if transport is None else 0)  # be gentle with Yahoo
    if not frames:
        raise RuntimeError("No macro series could be fetched")
    table = pd.concat(frames, ignore_index=True)
    lake.write_table(table, MACRO_DATASET)
    return table
