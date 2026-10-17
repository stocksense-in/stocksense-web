from datetime import date

import pandas as pd

from stocksense import lake_checks
from stocksense.lake import Lake

TODAY = date(2026, 10, 16)


def index_day(lake, day, rows):
    lake.write_parquet(pd.DataFrame(rows, columns=["index", "name", "open", "high", "low", "close"]),
                       "index_prices", day=day)


def test_indices_healthy_and_problems(tmp_path):
    lake = Lake(tmp_path)
    for d in ("2026-10-13", "2026-10-14", "2026-10-15"):
        index_day(lake, d, [(i, i, 100, 101, 99, 100) for i in lake_checks.MAIN_INDICES])
    r = lake_checks.check_indices(lake, TODAY)
    assert r["problems"] == [] and r["days"] == 3 and r["indices"] == len(lake_checks.MAIN_INDICES)

    index_day(lake, "2026-10-15", [("NIFTY_50", "x", 100, 99, 101, -5)])  # replaces the day: bad row, others missing
    r = lake_checks.check_indices(lake, date(2026, 11, 30))
    text = " | ".join(r["problems"])
    assert "close <= 0 or low > high" in text and "more than 5 days old" in text


def test_macro_staleness_and_allowed_negatives(tmp_path):
    lake = Lake(tmp_path)
    lake.write_table(pd.DataFrame({
        "series": ["BRENT", "BRENT", "WTI", "GOLD"],
        "date": [date(2026, 10, 14), date(2026, 10, 15), date(2020, 4, 20), date(2026, 9, 1)],
        "close": [100.0, 101.0, -37.63, 2000.0],
    }), "macro_prices")
    r = lake_checks.check_macro(lake, TODAY)
    assert r["series"]["BRENT"]["days"] == 2
    assert any("GOLD latest value" in p for p in r["problems"])
    assert not any("non-positive" in p for p in r["problems"])  # WTI's -37.63 is real


def test_gdelt_missing_and_thin_days(tmp_path):
    lake = Lake(tmp_path)
    for i, d in enumerate(pd.date_range("2026-08-01", "2026-10-15")):
        if d.date() == date(2026, 9, 10):
            continue  # GDELT didn't publish this day
        events = 10 if d.date() == date(2026, 9, 20) else 1000
        lake.write_parquet(pd.DataFrame({"country": ["IN"], "root": ["19"], "quad": [4], "india": [True],
                                         "events": [events], "mentions": [events]}),
                           "gdelt_daily", day=d.date(), refresh=False)
    lake.refresh_catalog()
    r = lake_checks.check_gdelt(lake, TODAY)
    assert r["missing_days"] == ["2026-09-10"] and r["thin_days"] == ["2026-09-20"] and r["problems"] == []


def test_check_all_skips_absent_datasets(tmp_path):
    assert lake_checks.check_all(Lake(tmp_path), TODAY) == {}
