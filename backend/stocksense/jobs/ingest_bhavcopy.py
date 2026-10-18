"""
Bhavcopy ingest job — NSE's official end-of-day prices into the data lake.

    python -m stocksense ingest-bhavcopy                      # 2010 → today: download, then build
    python -m stocksense ingest-bhavcopy --start 2026-10-01   # a short range
    python -m stocksense ingest-bhavcopy --download-only      # just fill raw/
    python -m stocksense ingest-bhavcopy --build-only --rebuild

1. Download: raw/nse_bhavcopy/<day>/<NSE file name>, one zip per trading day,
   untouched. Resumable; holidays are remembered (see stocksense/downloads.py).
2. Build: clean/eod_prices/date=<day>/ — every security on the file, as traded
   (unadjusted). Only days not built yet, unless --rebuild.
"""

from __future__ import annotations

from datetime import date

from ..downloads import RawFile, days_between, download_all, raw_path
from ..lake import Lake
from ..log import get_logger
from ..sources import bhavcopy

log = get_logger(__name__)

SOURCE = "nse_bhavcopy"
DATASET = "eod_prices"
DEFAULT_START = date(2010, 1, 1)


def planned_files(start: date, end: date) -> list[RawFile]:
    # Every calendar day: NSE has held Saturday special sessions and Sunday Muhurat trading.
    return [RawFile(d, bhavcopy.url_for(d), bhavcopy.file_name(d)) for d in days_between(start, end)]


def download(lake: Lake, start: date, end: date, workers: int = 2, per_second: float = 3.0):
    return download_all(lake, SOURCE, planned_files(start, end), headers=bhavcopy.HEADERS,
                        per_second=per_second, workers=workers)


def build(lake: Lake, start: date, end: date, rebuild: bool = False) -> int:
    """Parse downloaded days into clean/eod_prices. Returns the number of days written."""
    written = 0
    for f in planned_files(start, end):
        path = raw_path(lake, SOURCE, f)
        if not path.exists():
            continue
        if not rebuild and lake.partition_path(DATASET, f.day).exists():
            continue
        try:
            df = bhavcopy.parse(path.read_bytes())
        except Exception as exc:  # a corrupt or truncated archive file: report it, keep going
            log.warning(f"{SOURCE}: could not parse {path.name}: {exc}")
            continue
        lake.write_parquet(df, DATASET, day=f.day, refresh=False)
        written += 1
        if written % 500 == 0:
            log.info(f"{DATASET}: built {written} days (up to {f.day})")
    lake.refresh_catalog()
    log.info(f"{DATASET}: built {written} new day(s)")
    return written


def run(start: date | None = None, end: date | None = None, *, download_only: bool = False,
        build_only: bool = False, rebuild: bool = False, lake: Lake | None = None) -> None:
    lake = lake or Lake.from_settings()
    start, end = start or DEFAULT_START, end or date.today()
    if not build_only:
        download(lake, start, end)
    if not download_only:
        build(lake, start, end, rebuild=rebuild)
