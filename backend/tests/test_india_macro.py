from datetime import date

import httpx
import pandas as pd

from stocksense.jobs import ingest_india_macro as job
from stocksense.lake import Lake
from stocksense.sources import india_macro as im

BIS = """FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE
D,IN,2025-06-05,6.0
D,IN,2025-06-06,5.5
D,IN,2025-06-08,NaN
D,IN,2025-06-09,5.5
D,IN,2025-10-19,5.5
"""

CPI = {"data": [
    {"baseyear": "2012", "year": 2025, "month": "December", "state": "All India", "sector": "Combined", "group": "General",
     "subgroup": "General-Overall", "index": "198.0", "inflation": "1.33", "status": "F"},
    {"baseyear": "2012", "year": 2025, "month": "December", "state": "All India", "sector": "Rural", "group": "General",
     "index": "199.1", "inflation": "1.1"},
], "meta_data": {"page": 1, "totalPages": 1}}

IIP = {"data": [
    {"base_year": "2022-23", "year": 2026, "month": "September", "type": "General", "category": "General", "index": "124.3", "growth_rate": "6.7"},
    {"base_year": "2022-23", "year": 2026, "month": "September", "type": "Sectoral", "category": "Mining", "index": "99", "growth_rate": "1"},
], "meta_data": {"page": 1, "totalPages": 1}}

FRED = "observation_date,TRESEGINM052N\n2026-08-01,630000.5\n2026-09-01,.\n"


def test_policy_rate_keeps_only_changes():
    rows = im.parse_policy_csv(BIS)
    assert [(r["period"], r["value"]) for r in rows] == [(date(2025, 6, 5), 6.0), (date(2025, 6, 6), 5.5)]
    assert rows[1]["available_from"] == date(2025, 6, 6)


def test_cpi_takes_the_all_india_combined_index_released_on_the_12th():
    rows = im.parse_cpi(CPI["data"])
    assert {(r["series"], r["value"]) for r in rows} == {("cpi", 198.0), ("cpi_inflation", 1.33)}
    assert rows[0]["period"] == date(2025, 12, 31) and rows[0]["available_from"] == date(2026, 1, 12)


def test_iip_general_index_released_45_days_later():
    rows = im.parse_iip(IIP["data"])
    assert {(r["series"], r["value"]) for r in rows} == {("iip", 124.3), ("iip_growth", 6.7)}
    assert rows[0]["available_from"] == date(2026, 11, 14) and im.iip_base(2022) == "2011-12"


def test_fred_monthly_rows_skip_missing_values():
    rows = im.parse_fred_csv(FRED, "fx_reserves", "US$ million", 45, "TRESEGINM052N")
    assert [(r["period"], r["value"]) for r in rows] == [(date(2026, 8, 31), 630000.5)]
    assert rows[0]["available_from"] == date(2026, 10, 15)


def test_job_saves_what_it_can_and_answers_as_of_questions(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "stats.bis.org" in url:
            return httpx.Response(200, text=BIS)
        if "cpi/getCPIIndex" in url:
            return httpx.Response(200, json=CPI if "year=2025" in url else {"data": [], "meta_data": {"totalPages": 1}})
        if "iip/getIIPMonthly" in url:
            return httpx.Response(200, json=IIP if "year=2026" in url else {"data": []})
        if "TRESEGINM052N" in url:
            return httpx.Response(200, text=FRED)
        return httpx.Response(503)  # the bond yield feed is down: skipped, the rest saved

    lake = Lake(tmp_path)
    df = job.run(lake=lake, today=date(2026, 11, 27), transport=httpx.MockTransport(handler))
    assert set(df["series"]) == {"repo_rate", "cpi", "cpi_inflation", "iip", "iip_growth", "fx_reserves"}
    saved = pd.read_parquet(tmp_path / "clean" / "india_macro" / "data.parquet")
    assert len(saved) == len(df)
    assert job.as_of(df, "repo_rate", date(2025, 6, 5)) == 6.0
    assert job.as_of(df, "repo_rate", date(2025, 7, 1)) == 5.5
    assert job.as_of(df, "cpi_inflation", date(2026, 1, 11)) is None  # December CPI not out yet
    assert job.as_of(df, "cpi_inflation", date(2026, 1, 12)) == 1.33
