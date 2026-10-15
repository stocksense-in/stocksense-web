"""
GDELT ingest job — world news events since April 2013 into the data lake.

    python -m stocksense ingest-gdelt                       # 2013-04-01 → today: download, then build
    python -m stocksense ingest-gdelt --start 2026-10-01
    python -m stocksense ingest-gdelt --download-only
    python -m stocksense ingest-gdelt --build-only --workers 12

1. Download: raw/gdelt/<day>/<YYYYMMDD>.export.CSV.zip (~2–8 MB a day, ~37 GB in all).
2. Build, one partition per file day:
   • clean/gdelt_daily  — counts, mentions, Goldstein and tone per (country, CAMEO root,
     quad class, India involved). The input for event studies and models.
   • clean/gdelt_events — widely covered hostile or India-related events, with source
     URLs, for evidence links.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date

from ..downloads import RawFile, days_between, download_all, raw_path
from ..lake import Lake
from ..log import get_logger
from ..sources import gdelt

log = get_logger(__name__)

SOURCE = "gdelt"
DAILY = "gdelt_daily"
EVENTS = "gdelt_events"


def planned_files(start: date, end: date) -> list[RawFile]:
    return [RawFile(d, gdelt.url_for(d), gdelt.file_name(d)) for d in days_between(max(start, gdelt.FIRST_DAY), end)]


def _build_day(root: str, f: RawFile) -> tuple[date, int, str | None]:
    """Runs in a worker process: parse one raw file and write both partitions."""
    lake = Lake(root)
    try:
        df = gdelt.parse(raw_path(lake, SOURCE, f).read_bytes())
        lake.write_parquet(gdelt.daily_aggregates(df), DAILY, day=f.day, refresh=False)
        lake.write_parquet(gdelt.salient_events(df), EVENTS, day=f.day, refresh=False)
        return f.day, len(df), None
    except Exception as exc:  # a corrupt archive file: report it, keep going
        return f.day, 0, f"{type(exc).__name__}: {exc}"


def build(lake: Lake, start: date, end: date, rebuild: bool = False, workers: int = 8) -> int:
    todo = [
        f for f in planned_files(start, end)
        if raw_path(lake, SOURCE, f).exists() and (rebuild or not lake.partition_path(DAILY, f.day).exists())
    ]
    log.info(f"{SOURCE}: building {len(todo)} day(s) with {workers} workers")
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_build_day, str(lake.root), f) for f in todo]
        for fut in as_completed(futures):
            day, rows, error = fut.result()
            if error:
                log.warning(f"{SOURCE}: could not build {day}: {error}")
                continue
            done += 1
            if done % 250 == 0:
                log.info(f"{SOURCE}: built {done}/{len(todo)} days")
    lake.refresh_catalog()
    log.info(f"{SOURCE}: built {done} new day(s)")
    return done


def run(start: date | None = None, end: date | None = None, *, download_only: bool = False,
        build_only: bool = False, rebuild: bool = False, workers: int = 8, lake: Lake | None = None) -> None:
    lake = lake or Lake.from_settings()
    start, end = start or gdelt.FIRST_DAY, end or date.today()
    if not build_only:
        download_all(lake, SOURCE, planned_files(start, end), headers=gdelt.HEADERS,
                     per_second=4, workers=4, settle_days=3)
    if not download_only:
        build(lake, start, end, rebuild=rebuild, workers=workers)
