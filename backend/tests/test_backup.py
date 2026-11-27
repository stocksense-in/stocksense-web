import json
import os
from datetime import date, datetime

import pandas as pd
import pytest

from stocksense.jobs import backup
from stocksense.lake import Lake


@pytest.fixture
def lake(tmp_path):
    lake = Lake(tmp_path / "lake").ensure()
    for d in (date(2026, 11, 25), date(2026, 11, 26)):
        lake.write_parquet(pd.DataFrame({"symbol": ["TCS", "INFY"], "close": [3000.0 + d.day, 1500.0]}), "prices", day=d)
    lake.write_table(pd.DataFrame({"series": ["repo_rate"], "value": [5.5]}), "india_macro")
    (lake.raw_dir("nse_deals", date(2026, 11, 26)) / "bulk.csv").write_text("Date,Symbol\n", encoding="utf-8")
    return lake


def test_backup_copies_only_what_changed(lake, tmp_path):
    dest = tmp_path / "backup"
    first = backup.backup(lake, dest, now=datetime(2026, 11, 27, 22, 0))
    assert first["copied_files"] == 4 and first["backup_files"] == 4 and first["failed_count"] == 0
    assert not (dest / "lake" / "catalog.duckdb").exists()  # rebuilt from clean/, never copied
    assert json.loads((dest / "manifests" / "2026-11-27-2200.json").read_text())["copied_files"] == 4

    again = backup.backup(lake, dest, now=datetime(2026, 11, 28, 22, 0))
    assert again["copied_files"] == 0  # nothing new

    lake.write_parquet(pd.DataFrame({"symbol": ["TCS"], "close": [3100.0]}), "prices", day=date(2026, 11, 27))
    third = backup.backup(lake, dest, now=datetime(2026, 11, 29, 22, 0))
    assert third["copied_files"] == 1 and third["backup_files"] == 5


def test_deleted_lake_files_stay_in_the_backup(lake, tmp_path):
    dest = tmp_path / "backup"
    backup.backup(lake, dest)
    gone = lake.clean / "prices" / "date=2026-11-25" / "part-0.parquet"
    os.remove(gone)
    backup.backup(lake, dest)
    assert (dest / "lake" / "clean" / "prices" / "date=2026-11-25" / "part-0.parquet").exists()


def test_restore_check_matches_row_for_row(lake, tmp_path):
    dest = tmp_path / "backup"
    backup.backup(lake, dest)
    results = backup.check(lake, dest)
    assert {r["dataset"] for r in results} == {"prices", "india_macro"}
    assert all(r["match"] for r in results) and results[1]["rows"] == 4
    assert not [p for p in dest.iterdir() if p.name.startswith("restore-check-")]  # temp lake cleaned up

    # live data and backup differ: caught
    lake.write_parquet(pd.DataFrame({"symbol": ["TCS", "INFY"], "close": [1.0, 1500.0]}), "prices",
                       day=date(2026, 11, 26))
    bad = backup.check(lake, dest, ["prices"])
    assert bad[0]["match"] is False


def test_full_restore_rebuilds_a_queryable_lake(lake, tmp_path):
    dest = tmp_path / "backup"
    backup.backup(lake, dest)
    restored = backup.restore(dest, tmp_path / "restored")
    assert restored.query("select count(*) from prices").iloc[0, 0] == 4
    assert (restored.raw / "nse_deals" / "2026-11-26" / "bulk.csv").exists()


def test_backup_folder_must_be_given(monkeypatch):
    monkeypatch.delenv("STOCKSENSE_BACKUP_DIR", raising=False)
    with pytest.raises(SystemExit):
        backup.backup_dir(None)
