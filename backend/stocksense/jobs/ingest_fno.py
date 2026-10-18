"""
F&O ingest job — NSE's end-of-day futures & options file into the data lake.

    python -m stocksense ingest-fno                       # 2010 → today: download, then build
    python -m stocksense ingest-fno --start 2026-10-01
    python -m stocksense ingest-fno --build-only --rebuild

1. Download: raw/nse_fno_bhavcopy/<day>/<NSE file name>, one zip per trading day.
2. Build, one partition per day:
   • clean/fno_prices  — every contract: prices, settlement, contracts, turnover, OI
   • clean/fno_summary — one row per underlying: near-month future, futures OI,
     put/call ratios (OI and volume, all expiries and nearest), max-OI strikes
"""

from __future__ import annotations

from datetime import date

from ..downloads import RawFile, days_between, download_all, raw_path
from ..lake import Lake
from ..log import get_logger
from ..sources import fno_bhavcopy

log = get_logger(__name__)

SOURCE = "nse_fno_bhavcopy"
PRICES, SUMMARY = "fno_prices", "fno_summary"
DEFAULT_START = date(2010, 1, 1)


def planned_files(start: date, end: date) -> list[RawFile]:
    return [RawFile(d, fno_bhavcopy.url_for(d), fno_bhavcopy.file_name(d)) for d in days_between(start, end)]


def build(lake: Lake, start: date, end: date, rebuild: bool = False) -> int:
    written = 0
    for f in planned_files(start, end):
        path = raw_path(lake, SOURCE, f)
        if not path.exists() or (not rebuild and lake.partition_path(SUMMARY, f.day).exists()):
            continue
        try:
            df = fno_bhavcopy.parse(path.read_bytes())
            lake.write_parquet(df, PRICES, day=f.day, refresh=False)
            lake.write_parquet(fno_bhavcopy.summarise(df, f.day), SUMMARY, day=f.day, refresh=False)
        except Exception as exc:  # a corrupt archive file: report it, keep going
            log.warning(f"{SOURCE}: could not build {path.name}: {exc}")
            continue
        written += 1
        if written % 500 == 0:
            log.info(f"{SOURCE}: built {written} days (up to {f.day})")
    lake.refresh_catalog()
    log.info(f"{SOURCE}: built {written} new day(s)")
    return written


def run(start: date | None = None, end: date | None = None, *, download_only: bool = False,
        build_only: bool = False, rebuild: bool = False, lake: Lake | None = None) -> None:
    lake = lake or Lake.from_settings()
    start, end = start or DEFAULT_START, end or date.today()
    if not build_only:
        download_all(lake, SOURCE, planned_files(start, end), headers=fno_bhavcopy.HEADERS, per_second=3, workers=2)
    if not download_only:
        build(lake, start, end, rebuild=rebuild)
