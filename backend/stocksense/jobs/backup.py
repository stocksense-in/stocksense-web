"""
Lake backup (M0.4): an incremental copy of the data lake to another folder, and a restore
test that reads datasets back from that copy.

    python -m stocksense backup --dest F:\\stocksense-backup     # or set STOCKSENSE_BACKUP_DIR
    python -m stocksense backup --check                          # restore test: sample datasets
    python -m stocksense backup --restore-to D:\\lake-restored   # rebuild a lake from the copy

What's copied: raw/, clean/, features/ and models/, but only files that are new or changed
since the last run (by size and modified time), so a nightly run copies a day's worth, not
the whole lake. Each file lands as <name>.part and is renamed when complete, so an
interrupted run never leaves a half-written file under its real name. catalog.duckdb is
skipped: it is rebuilt from clean/ (`Lake.refresh_catalog`).

Files deleted from the lake stay in the backup. A bad run that drops partitions can't take
the good copies with it; clean up the backup by hand if it ever needs to shrink.

Each run writes manifests/<date>-<time>.json to the backup (files and bytes copied, totals).

The destination is any folder: an external drive, or a folder a sync client uploads to
cloud storage (Google Drive for desktop, OneDrive, an rclone mount). Off this machine is
the point: a reimaged lab PC takes the lake with it.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from ..lake import Lake
from ..log import get_logger

log = get_logger(__name__)

FOLDERS = ("raw", "clean", "features", "models")
MTIME_SLACK = 2.0  # seconds: FAT/exFAT drives store modified times to 2 s
CHECK_SAMPLE = 5   # datasets the restore test reads back


def backup_dir(dest: str | Path | None = None) -> Path:
    dest = dest or os.getenv("STOCKSENSE_BACKUP_DIR")
    if not dest:
        raise SystemExit("No backup folder: pass --dest or set STOCKSENSE_BACKUP_DIR in backend/.env.")
    return Path(dest).expanduser().resolve()


def _same(src: os.stat_result, dst: Path) -> bool:
    try:
        d = dst.stat()
    except FileNotFoundError:
        return False
    return d.st_size == src.st_size and abs(d.st_mtime - src.st_mtime) <= MTIME_SLACK


def changed(root: Path, mirror: Path, folders: tuple[str, ...] = FOLDERS) -> Iterator[tuple[Path, Path, int]]:
    """(source, target, size) for every file under `folders` that the mirror lacks or holds an older copy of."""
    for folder in folders:
        base = root / folder
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.name.endswith(".part"):
                continue
            target = mirror / p.relative_to(root)
            st = p.stat()
            if not _same(st, target):
                yield p, target, st.st_size


def _copy(src: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    shutil.copy2(src, part)  # copy2 keeps the modified time, which the next run compares
    os.replace(part, target)


def backup(lake: Lake, dest: Path, now: datetime | None = None) -> dict:
    """Copy what's new or changed into <dest>/lake/ and write a manifest."""
    now = now or datetime.now()
    mirror = dest / "lake"
    copied, size, failed = 0, 0, []
    for src, target, n in changed(lake.root, mirror):
        try:
            _copy(src, target)
        except OSError as exc:  # a file being rewritten right now, a full disk: report, keep going
            failed.append(f"{src.relative_to(lake.root)}: {exc}")
            continue
        copied += 1
        size += n
        if copied % 5000 == 0:
            log.info(f"backup: {copied:,} files, {size / 1e9:.1f} GB so far")
    files = sum(1 for f in FOLDERS if (mirror / f).exists() for p in (mirror / f).rglob("*") if p.is_file())
    manifest = {"at": now.isoformat(timespec="seconds"), "lake": str(lake.root), "copied_files": copied,
                "copied_bytes": size, "backup_files": files, "failed": failed[:50], "failed_count": len(failed)}
    folder = dest / "manifests"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{now:%Y-%m-%d-%H%M}.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log.info(f"backup: copied {copied:,} files ({size / 1e9:.2f} GB) to {mirror}; "
             f"{files:,} files in the backup" + (f"; {len(failed)} failed" if failed else ""))
    return manifest


def restore(dest: Path, to: Path, datasets: list[str] | None = None) -> Lake:
    """Rebuild a lake at `to` from the backup: everything, or only these clean datasets."""
    mirror = dest / "lake"
    if not (mirror / "clean").exists():
        raise SystemExit(f"No backup at {mirror}")
    to = to.expanduser().resolve()
    if datasets:
        for name in datasets:
            src = mirror / "clean" / name
            for p in src.rglob("*"):
                if p.is_file() and not p.name.endswith(".part"):
                    _copy(p, to / p.relative_to(mirror))
    else:
        for src, target, _ in changed(mirror, to):
            _copy(src, target)
    lake = Lake(to)
    lake.refresh_catalog()
    return lake


def fingerprint(lake: Lake, dataset: str) -> tuple[int, str]:
    """(rows, a sum of every row's hash): equal only if the data is the same, row for row.
    The sum comes back as text: it's a 128-bit integer, which pandas would round through float."""
    rows, digest = lake.query(f"select count(*), cast(coalesce(sum(hash(t)), 0) as varchar) from {dataset} t").iloc[0]
    return int(rows), str(digest)


def check(lake: Lake, dest: Path, datasets: list[str] | None = None, sample: int = CHECK_SAMPLE,
          seed: int | None = None) -> list[dict]:
    """The restore test: restore some datasets from the backup into a temporary lake and
    compare every row with the live lake. Run it right after a backup, before jobs write again."""
    backed = {p.name for p in (dest / "lake" / "clean").iterdir() if p.is_dir()} if (dest / "lake" / "clean").exists() else set()
    names = datasets or sorted(set(lake.datasets()) & backed)
    if not datasets and len(names) > sample:
        names = sorted(random.Random(seed).sample(names, sample))
    out = []
    # restored onto the backup's own drive: a big dataset shouldn't fill the system drive
    with tempfile.TemporaryDirectory(prefix="restore-check-", dir=dest) as tmp:
        restored = restore(dest, Path(tmp), names)
        for name in names:
            live, back = fingerprint(lake, name), fingerprint(restored, name)
            out.append({"dataset": name, "rows": live[0], "restored_rows": back[0], "match": live == back})
            log.info(f"restore check: {name} — {back[0]:,} of {live[0]:,} rows, "
                     + ("identical" if live == back else "DIFFERENT"))
    return out


def run(dest: str | None = None, lake: Lake | None = None, check_after: bool = True) -> dict:
    lake = lake or Lake.from_settings()
    target = backup_dir(dest)
    manifest = backup(lake, target)
    if check_after:
        manifest["check"] = check(lake, target)
    return manifest
