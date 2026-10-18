"""
F&O ingest job — NSE's end-of-day futures & options file into the data lake.

    python -m stocksense ingest-fno                       # 2010 → today: download, then build
    python -m stocksense ingest-fno --start 2026-10-01
    python -m stocksense ingest-fno --build-only --rebuild --workers 12

1. Download: raw/nse_fno_bhavcopy/<day>/<NSE file name>, one zip per trading day.
2. Build, one partition per day:
   • clean/fno_prices  — every contract: prices, settlement, contracts, turnover, OI
   • clean/fno_summary — one row per underlying: near-month future, futures OI,
     put/call ratios (OI and volume, all expiries and nearest), max-OI strikes
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
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


def _build_day(root: str, f: RawFile) -> tuple[date, str | None]:
    """Runs in a worker process: parse one raw file and write both partitions."""
    lake = Lake(root)
    try:
        df = fno_bhavcopy.parse(raw_path(lake, SOURCE, f).read_bytes())
        lake.write_parquet(df, PRICES, day=f.day, refresh=False)
        lake.write_parquet(fno_bhavcopy.summarise(df, f.day), SUMMARY, day=f.day, refresh=False)
        return f.day, None
    except Exception as exc:  # a corrupt archive file: report it, keep going
        return f.day, f"{type(exc).__name__}: {exc}"


def build(lake: Lake, start: date, end: date, rebuild: bool = False, workers: int = 1) -> int:
    """Parse downloaded days into fno_prices / fno_summary. `workers` > 1 builds days in parallel processes."""
    todo = [f for f in planned_files(start, end)
            if raw_path(lake, SOURCE, f).exists() and (rebuild or not lake.partition_path(SUMMARY, f.day).exists())]
    written = 0
    if workers > 1 and len(todo) > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_build_day, [str(lake.root)] * len(todo), todo, chunksize=8))
    else:
        results = [_build_day(str(lake.root), f) for f in todo]
    for day, error in results:
        if error:
            log.warning(f"{SOURCE}: could not build {day}: {error}")
        else:
            written += 1
    lake.refresh_catalog()
    log.info(f"{SOURCE}: built {written} new day(s)")
    return written


def run(start: date | None = None, end: date | None = None, *, download_only: bool = False,
        build_only: bool = False, rebuild: bool = False, workers: int = 8, lake: Lake | None = None) -> None:
    lake = lake or Lake.from_settings()
    start, end = start or DEFAULT_START, end or date.today()
    if not build_only:
        download_all(lake, SOURCE, planned_files(start, end), headers=fno_bhavcopy.HEADERS, per_second=3, workers=2)
    if not download_only:
        build(lake, start, end, rebuild=rebuild, workers=workers)
