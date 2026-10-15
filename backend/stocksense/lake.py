"""
Local data lake on the engine machine (the college PC): Parquet files plus a
DuckDB catalogue. Long histories (bhavcopy, GDELT, filings) live here; only the
publishable results go to Supabase.

The root comes from STOCKSENSE_LAKE_DIR (backend/.env) and must be outside the repo.

    <root>/
      raw/<source>/<YYYY-MM-DD>/...                     files exactly as downloaded (csv, zip, json, pdf)
      clean/<dataset>/date=<YYYY-MM-DD>/part-0.parquet  typed tables, one folder per day
      clean/<dataset>/data.parquet                      small tables not split by day (reference data)
      features/<name>/...                             model inputs built from clean/
      models/<name>/<version>/...                       weights, metrics, eval reports
      catalog.duckdb                                    one view per clean dataset

    lake = Lake.from_settings()
    lake.write_parquet(df, "prices", day=date(2026, 10, 14))
    lake.query("select count(*) from prices where date = ?", [date(2026, 10, 14)])

Writing a day again replaces that day's partition, so jobs can be rerun safely.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

from .config import REPO_DIR, get_settings
from .log import get_logger

log = get_logger(__name__)

PARTITION = "date"  # hive-style partition key: clean/<dataset>/date=YYYY-MM-DD/
TABLE_FILE = "data.parquet"  # an unpartitioned table: clean/<dataset>/data.parquet
CATALOG_FILE = "catalog.duckdb"
# Dataset and source names become folder names and DuckDB view names.
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class LakeNotConfigured(RuntimeError):
    pass


def _check_name(kind: str, name: str) -> str:
    if not _NAME.match(name):
        raise ValueError(f"{kind} name {name!r}: use lowercase letters, digits and _, starting with a letter")
    return name


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _sql_string(path: Path) -> str:
    """A path as a DuckDB string literal (forward slashes work on Windows too)."""
    return "'" + path.as_posix().replace("'", "''") + "'"


def _atomic_parquet(df: pd.DataFrame, target: Path) -> None:
    """Write via a temp file and rename: readers see the old file or the new one, never half."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".tmp-{uuid.uuid4().hex}"
    df.to_parquet(tmp, index=False)
    tmp.replace(target)


class Lake:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()

    @classmethod
    def from_settings(cls) -> Lake:
        lake_dir = get_settings().lake_dir
        if not lake_dir:
            raise LakeNotConfigured(
                "STOCKSENSE_LAKE_DIR is not set. Add it to backend/.env (see backend/.env.example)."
            )
        lake = cls(lake_dir)
        repo = REPO_DIR.resolve()
        if lake.root == repo or repo in lake.root.parents:
            raise LakeNotConfigured(f"STOCKSENSE_LAKE_DIR ({lake.root}) must be outside the git repo.")
        return lake

    # ── layout ──────────────────────────────────────────────────────────────

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def clean(self) -> Path:
        return self.root / "clean"

    @property
    def features(self) -> Path:
        return self.root / "features"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def catalog_path(self) -> Path:
        return self.root / CATALOG_FILE

    def ensure(self) -> Lake:
        """Create the top-level folders if they don't exist yet."""
        for folder in (self.raw, self.clean, self.features, self.models):
            folder.mkdir(parents=True, exist_ok=True)
        return self

    def raw_dir(self, source: str, day: date | datetime | str) -> Path:
        """raw/<source>/<YYYY-MM-DD>/, created. Downloads go here untouched."""
        folder = self.raw / _check_name("source", source) / _as_date(day).isoformat()
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def features_dir(self, name: str) -> Path:
        folder = self.features / _check_name("feature set", name)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def model_dir(self, name: str, version: str) -> Path:
        folder = self.models / _check_name("model", name) / version
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def datasets(self) -> list[str]:
        """Clean datasets that hold at least one Parquet file."""
        if not self.clean.exists():
            return []
        return sorted(
            d.name
            for d in self.clean.iterdir()
            if d.is_dir() and _NAME.match(d.name) and (any(d.glob("*/*.parquet")) or (d / TABLE_FILE).exists())
        )

    # ── writing ─────────────────────────────────────────────────────────────

    def write_parquet(
        self,
        df: pd.DataFrame,
        dataset: str,
        *,
        day: date | datetime | str | None = None,
        date_col: str | None = None,
        refresh: bool = True,
    ) -> list[Path]:
        """
        Save `df` under clean/<dataset>/date=YYYY-MM-DD/, replacing whatever that
        day held before. Give either `day` (every row belongs to one day, e.g. a
        daily snapshot) or `date_col` (split rows by that column's UTC date).
        Bulk loads pass refresh=False and call refresh_catalog() once at the end.
        Returns the files written.
        """
        _check_name("dataset", dataset)
        if (day is None) == (date_col is None):
            raise ValueError("give exactly one of day= or date_col=")
        if df.empty:
            log.warning(f"Nothing to write to {dataset}: empty DataFrame")
            return []

        if day is not None:
            groups = [(_as_date(day), df)]
        else:
            days = pd.to_datetime(df[date_col], utc=True).dt.date
            groups = list(df.groupby(days, sort=True))

        written = []
        for d, part in groups:
            # The folder name carries the date; a column of the same name would clash with it.
            part = part.drop(columns=[PARTITION], errors="ignore")
            target = self.partition_path(dataset, d)
            _atomic_parquet(part, target)
            for old in target.parent.glob("*.parquet"):
                if old != target:
                    old.unlink()
            written.append(target)

        if refresh:
            self.refresh_catalog()
            log.info(f"Lake: wrote {len(df)} rows to clean/{dataset} ({len(written)} day partition(s))")
        return written

    def write_table(self, df: pd.DataFrame, dataset: str, *, refresh: bool = True) -> Path:
        """
        Save a whole small table (not split by day) as clean/<dataset>/data.parquet,
        replacing the previous version. For reference data such as corporate actions.
        """
        _check_name("dataset", dataset)
        folder = self.clean / dataset
        if any(folder.glob("*/*.parquet")):
            raise ValueError(f"clean/{dataset} already holds day partitions")
        target = folder / TABLE_FILE
        _atomic_parquet(df, target)
        if refresh:
            self.refresh_catalog()
        log.info(f"Lake: wrote {len(df)} rows to clean/{dataset}/{TABLE_FILE}")
        return target

    def partition_path(self, dataset: str, day: date | datetime | str) -> Path:
        """The file write_parquet uses for one day of a dataset (it may not exist yet)."""
        return self.clean / _check_name("dataset", dataset) / f"{PARTITION}={_as_date(day).isoformat()}" / "part-0.parquet"

    def connect(self, read_only: bool = True, wait_seconds: float = 120) -> duckdb.DuckDBPyConnection:
        """
        Open catalog.duckdb. DuckDB lets one process write the file at a time; jobs
        running side by side (and queries meanwhile) wait for the lock instead of failing.
        """
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                return duckdb.connect(str(self.catalog_path), read_only=read_only)
            except duckdb.IOException as exc:
                if "lock" not in str(exc).lower() or time.monotonic() > deadline:
                    raise
                time.sleep(0.5)

    def refresh_catalog(self) -> None:
        """(Re)create one view per clean dataset in catalog.duckdb."""
        self.ensure()
        with self.connect(read_only=False) as con:
            for name in self.datasets():
                table = self.clean / name / TABLE_FILE
                if table.exists():
                    source = f"read_parquet({_sql_string(table)})"
                else:
                    files = self.clean / name / "*" / "*.parquet"
                    source = f"read_parquet({_sql_string(files)}, hive_partitioning = true, union_by_name = true)"
                con.execute(f"create or replace view {name} as select * from {source}")

    # ── reading ─────────────────────────────────────────────────────────────

    def query(self, sql: str, params: list | None = None, frames: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
        """
        Run SQL against the catalogue (each clean dataset is a view) and return a
        DataFrame. `frames` makes in-memory DataFrames joinable by name for this query.
        """
        if not self.catalog_path.exists():
            self.refresh_catalog()
        with self.connect() as con:
            for name, frame in (frames or {}).items():
                con.register(name, frame)
            return con.execute(sql, params or []).df()

    def execute(self, sql: str) -> None:
        """Run a statement that changes the catalogue (e.g. create a derived view)."""
        self.ensure()
        with self.connect(read_only=False) as con:
            con.execute(sql)
