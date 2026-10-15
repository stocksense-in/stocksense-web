from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from stocksense import lake as lake_module
from stocksense.config import REPO_DIR
from stocksense.jobs import lake_prices
from stocksense.lake import Lake, LakeNotConfigured

DAY = date(2026, 10, 14)


@pytest.fixture
def lake(tmp_path):
    return Lake(tmp_path / "lake")


def prices(*symbols, price=100.0):
    return pd.DataFrame({"symbol": list(symbols), "price": [price] * len(symbols)})


def test_layout(lake):
    lake.ensure()
    for folder in ("raw", "clean", "features", "models"):
        assert (lake.root / folder).is_dir()
    assert lake.raw_dir("gdelt", DAY) == lake.root / "raw" / "gdelt" / "2026-10-14"
    assert lake.raw_dir("gdelt", "2026-10-14").is_dir()
    assert lake.model_dir("geo_classifier", "v1") == lake.root / "models" / "geo_classifier" / "v1"
    assert lake.catalog_path == lake.root / "catalog.duckdb"


@pytest.mark.parametrize("bad", ["Prices", "1prices", "pri-ces", "../x", "x;drop"])
def test_rejects_unsafe_names(lake, bad):
    with pytest.raises(ValueError):
        lake.write_parquet(prices("TCS"), bad, day=DAY)
    with pytest.raises(ValueError):
        lake.raw_dir(bad, DAY)


def test_write_and_query_one_day(lake):
    files = lake.write_parquet(prices("TCS", "INFY"), "prices", day=DAY)
    assert files == [lake.root / "clean" / "prices" / "date=2026-10-14" / "part-0.parquet"]
    assert lake.datasets() == ["prices"]

    df = lake.query("select symbol, price, typeof(date) as date_type, date from prices order by symbol")
    assert df["symbol"].tolist() == ["INFY", "TCS"]
    assert df["date_type"].tolist() == ["DATE", "DATE"]  # the partition folder becomes a typed column
    assert df["date"].dt.date.tolist() == [DAY, DAY]


def test_rewriting_a_day_replaces_it(lake):
    lake.write_parquet(prices("TCS", "INFY"), "prices", day=DAY)
    lake.write_parquet(prices("TCS", price=200.0), "prices", day=DAY)
    df = lake.query("select symbol, price from prices")
    assert df.to_dict("records") == [{"symbol": "TCS", "price": 200.0}]
    assert len(list((lake.clean / "prices" / "date=2026-10-14").iterdir())) == 1  # no temp files left


def test_split_by_date_column(lake):
    df = pd.DataFrame({
        "symbol": ["TCS", "TCS", "INFY"],
        "close": [1.0, 2.0, 3.0],
        "ts": ["2026-10-13T10:00:00+00:00", "2026-10-14T10:00:00+00:00", "2026-10-14T11:00:00+00:00"],
    })
    files = lake.write_parquet(df, "bars", date_col="ts")
    assert [f.parent.name for f in files] == ["date=2026-10-13", "date=2026-10-14"]
    counts = lake.query("select strftime(date, '%Y-%m-%d') as d, count(*) as n from bars group by d order by d")
    assert counts.to_dict("records") == [{"d": "2026-10-13", "n": 1}, {"d": "2026-10-14", "n": 2}]


def test_query_params_and_new_columns(lake):
    lake.write_parquet(prices("TCS"), "prices", day="2026-10-13")
    lake.write_parquet(prices("TCS").assign(change_pct=1.5), "prices", day=DAY)  # schema grew
    df = lake.query("select change_pct from prices where date = ?", [DAY])
    assert df["change_pct"].tolist() == [1.5]
    older = lake.query("select change_pct from prices where date = ?", [date(2026, 10, 13)])
    assert older["change_pct"].isna().all()


def test_needs_exactly_one_partitioning(lake):
    with pytest.raises(ValueError):
        lake.write_parquet(prices("TCS"), "prices")
    with pytest.raises(ValueError):
        lake.write_parquet(prices("TCS"), "prices", day=DAY, date_col="symbol")
    assert lake.write_parquet(prices("TCS").iloc[0:0], "prices", day=DAY) == []


def test_from_settings(monkeypatch, tmp_path):
    def settings(lake_dir):
        monkeypatch.setattr(lake_module, "get_settings", lambda: SimpleNamespace(lake_dir=lake_dir))

    settings("")
    with pytest.raises(LakeNotConfigured, match="STOCKSENSE_LAKE_DIR"):
        Lake.from_settings()

    settings(str(REPO_DIR / "data-lake"))
    with pytest.raises(LakeNotConfigured, match="outside"):
        Lake.from_settings()

    settings(str(tmp_path / "lake"))
    assert Lake.from_settings().root == (tmp_path / "lake").resolve()


def test_lake_prices_job(lake):
    rows = [
        {"symbol": "TCS", "price": 2114.4, "change_pct": 2.0, "updated_at": "2026-10-14T09:00:00+00:00"},
        {"symbol": "NIFTY50", "price": 22721, "change_pct": None, "updated_at": "2026-10-14T09:00:00+00:00"},
    ]
    # 20:00 UTC on the 13th is already the 14th in India: the partition follows IST.
    now = datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)
    files = lake_prices.run(lake=lake, rows=rows, now=now)
    assert files[0].parent.name == "date=2026-10-14"

    df = lake.query("select * from prices order by symbol")
    assert df["symbol"].tolist() == ["NIFTY50", "TCS"]
    assert df["price"].tolist() == [22721.0, 2114.4]
    assert pd.isna(df.loc[0, "change_pct"])
    assert {"updated_at", "snapshot_at", "date"} <= set(df.columns)
