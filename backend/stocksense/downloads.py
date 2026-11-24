"""
Polite, resumable downloads of archive files into the lake's raw/ folder.

    files = [RawFile(day, url, "cm02JAN2015bhav.csv.zip"), ...]
    stats = download_all(lake, "nse_bhavcopy", files, headers=HEADERS, per_second=3, workers=2)

- A file already on disk is skipped, so an interrupted run picks up where it stopped.
- Files are written to a temp name and renamed, so a crash never leaves half a file.
- A 404 for a day more than `settle_days` old is remembered with an empty
  `<name>.missing` marker (a holiday, or a gap in the archive) so reruns don't ask
  again. Recent 404s aren't remembered: the file may simply not be published yet.
- 429 / 5xx / network errors are retried with back-off.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import httpx

from .lake import Lake
from .log import get_logger

log = get_logger(__name__)

RETRIES = 4
BACKOFF_SECONDS = 5.0


class RateLimiter:
    """Spaces requests evenly across all threads."""

    def __init__(self, per_second: float):
        self._interval = 1 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self._interval
        if delay > 0:
            time.sleep(delay)


@dataclass(frozen=True)
class RawFile:
    day: date
    url: str
    name: str


@dataclass
class DownloadStats:
    downloaded: int = 0
    skipped: int = 0
    missing: int = 0
    failed: list[str] = field(default_factory=list)
    bytes: int = 0

    def __str__(self) -> str:
        return (f"{self.downloaded} downloaded ({self.bytes / 1e6:.1f} MB), {self.skipped} already had, "
                f"{self.missing} not published, {len(self.failed)} failed")


def raw_path(lake: Lake, source: str, f: RawFile) -> Path:
    return lake.raw / source / f.day.isoformat() / f.name


def download_all(
    lake: Lake,
    source: str,
    files: Iterable[RawFile],
    *,
    headers: dict | None = None,
    per_second: float = 2.0,
    workers: int = 2,
    settle_days: int = 7,
    today: date | None = None,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    progress_every: int = 250,
) -> DownloadStats:
    """Download every file not already in raw/<source>/<day>/. Tests pass `transport`, `today` and `sleep`."""
    today = today or date.today()
    limiter = RateLimiter(per_second)
    stats = DownloadStats()
    lock = threading.Lock()
    todo = []
    for f in files:
        path = raw_path(lake, source, f)
        if path.exists() or path.with_name(path.name + ".missing").exists():
            stats.skipped += 1
        else:
            todo.append(f)
    if not todo:
        log.info(f"{source}: nothing to download ({stats.skipped} files already present)")
        return stats
    log.info(f"{source}: {len(todo)} files to fetch, {stats.skipped} already present")

    def fetch(client: httpx.Client, f: RawFile) -> None:
        path = raw_path(lake, source, f)
        for attempt in range(1, RETRIES + 1):
            limiter.wait()
            try:
                resp = client.get(f.url)
            except httpx.HTTPError as exc:
                error = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code == 200:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_name(path.name + ".part")
                    tmp.write_bytes(resp.content)
                    tmp.replace(path)
                    with lock:
                        stats.downloaded += 1
                        stats.bytes += len(resp.content)
                    return
                if resp.status_code == 404:
                    if f.day < today - timedelta(days=settle_days):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.with_name(path.name + ".missing").touch()
                    with lock:
                        stats.missing += 1
                    return
                error = f"HTTP {resp.status_code}"
                if resp.status_code not in (429,) and resp.status_code < 500:
                    break  # 403 etc.: retrying won't help
            sleep(BACKOFF_SECONDS * attempt)
        with lock:
            stats.failed.append(f"{f.day} {error}")

    done = 0
    with httpx.Client(headers=headers or {}, timeout=60, follow_redirects=True, transport=transport) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in pool.map(lambda f: fetch(client, f), todo):
                done += 1
                if progress_every and done % progress_every == 0:
                    log.info(f"{source}: {done}/{len(todo)} — {stats}")
    log.info(f"{source}: {stats}")
    for line in stats.failed[:10]:
        log.warning(f"{source}: failed {line}")
    return stats


def days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]
