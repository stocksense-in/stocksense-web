"""
Local data lake on the engine machine (the college PC): Parquet files plus a
DuckDB catalogue. Long histories (bhavcopy, GDELT, filings) live here; only the
publishable results go to Supabase.

The root comes from STOCKSENSE_LAKE_DIR (backend/.env) and must be outside the repo.

    <root>/
      raw/<source>/<YYYY-MM-DD>/...                     files exactly as downloaded (csv, zip, json, pdf)
      clean/<dataset>/date=<YYYY-MM-DD>/part-0.parquet  typed tables, one folder per day
      features/<name>/...                               model inputs built from clean/
      models/<name>/<version>/...                       weights, metrics, eval reports
      catalog.duckdb                                    one view per clean dataset

    lake = Lake.from_settings()
    lake.write_parquet(df, "prices", day=date(2026, 10, 14))
    lake.query("select count(*) from prices where date = ?", [date(2026, 10, 14)])

Writing a day again replaces that day's partition, so jobs can be rerun safely.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

from .config import REPO_DIR, get_settings
from .log import get_logger

log = get_logger(__name__)

PARTITION = "date"  # hive-style partition key: clean/<dataset>/date=YYYY-MM-DD/
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
            if d.is_dir() and _NAME.match(d.name) and any(d.glob("*/*.parquet"))
        )

    # ── writing ─────────────────────────────────────────────────────────────

    def write_parquet(
        self,
        df: pd.DataFrame,
        dataset: str,
        *,
        day: date | datetime | str | None = None,
        date_col: str | None = None,
    ) -> list[Path]:
        """
        Save `df` under clean/<dataset>/date=YYYY-MM-DD/, replacing whatever that
        day held before. Give either `day` (every row belongs to one day, e.g. a
        daily snapshot) or `date_col` (split rows by that column's UTC date).
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
            folder = self.clean / dataset / f"{PARTITION}={d.isoformat()}"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / "part-0.parquet"
            tmp = folder / f".tmp-{uuid.uuid4().hex}"
            part.to_parquet(tmp, index=False)
            tmp.replace(target)  # atomic: readers see the old day or the new one, never half
            for old in folder.glob("*.parquet"):
                if old != target:
                    old.unlink()
            written.append(target)

        self.refresh_catalog()
        log.info(f"Lake: wrote {len(df)} rows to clean/{dataset} ({len(written)} day partition(s))")
        return written

    def refresh_catalog(self) -> None:
        """(Re)create one view per clean dataset in catalog.duckdb."""
        self.ensure()
        with duckdb.connect(str(self.catalog_path)) as con:
            for name in self.datasets():
                files = self.clean / name / "*" / "*.parquet"
                con.execute(
                    f"create or replace view {name} as select * from read_parquet("
                    f"{_sql_string(files)}, hive_partitioning = true, union_by_name = true)"
                )

    # ── reading ─────────────────────────────────────────────────────────────

    def query(self, sql: str, params: list | None = None) -> pd.DataFrame:
        """Run SQL against the catalogue (each clean dataset is a view) and return a DataFrame."""
        if not self.catalog_path.exists():
            self.refresh_catalog()
        with duckdb.connect(str(self.catalog_path), read_only=True) as con:
            return con.execute(sql, params or []).df()
