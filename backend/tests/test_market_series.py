from datetime import date, datetime, timezone

import httpx
import pytest

from stocksense.downloads import RawFile, raw_path
from stocksense.jobs import ingest_market
from stocksense.lake import Lake
from stocksense.sources import nse_indices, yahoo_history

CSV_2015 = (
    "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,"
    "Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
    "CNX Nifty,02-01-2015,8272.80,8294.70,8248.75,8284.00,2.90,0.04,124924760,5845.04,22.54,3.53,1.25\n"
    "CNX Bank,02-01-2015,18961.70,19080.10,18876.75,19057.80,98.55,0.52,30404577,1849.94,18.2,2.9,1.0\n"
    "CNX Finance,02-01-2015,6702.10,6760.20,6670.25,6748.65,46.55,0.69,-,-,-,-,-\n"
)
CSV_2026 = (
    "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,"
    "Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
    "Nifty 50,14-10-2026,22700.10,22780.00,22590.30,22622.70,-100.00,-0.44,300000000,30000.5,21.1,3.3,1.3\n"
    "Nifty Bank,14-10-2026,55400.00,55600.00,55200.00,55316.00,-166.0,-0.30,1,2,3,4,5\n"
)


@pytest.mark.parametrize("name, code", [
    ("CNX Nifty", "NIFTY_50"), ("Nifty 50", "NIFTY_50"), ("CNX Bank", "NIFTY_BANK"), ("Nifty Bank", "NIFTY_BANK"),
    ("CNX Finance", "NIFTY_FINANCIAL_SERVICES"), ("Nifty Financial Services", "NIFTY_FINANCIAL_SERVICES"),
    ("CNX Nifty Junior", "NIFTY_NEXT_50"), ("CNX Midcap", "NIFTY_MIDCAP_100"), ("NIFTY Midcap 100", "NIFTY_MIDCAP_100"),
    ("Nifty Oil & Gas", "NIFTY_OIL_GAS"), ("India VIX", "INDIA_VIX"), ("Nifty Healthcare Index", "NIFTY_HEALTHCARE"),
])
def test_index_codes_survive_the_cnx_rename(name, code):
    assert nse_indices.index_code(name) == code


def test_parse_index_file():
    df = nse_indices.parse(CSV_2015.encode())
    assert df["index"].tolist() == ["NIFTY_50", "NIFTY_BANK", "NIFTY_FINANCIAL_SERVICES"]
    nifty = df.iloc[0]
    assert (nifty.close, nifty.change_pct, nifty.pe) == (8284.0, 0.04, 22.54)
    assert df.iloc[2][["volume", "pe"]].isna().all()  # "-" → missing


def test_indices_job_builds_partitions(tmp_path):
    lake = Lake(tmp_path)
    for day, csv in ((date(2015, 1, 2), CSV_2015), (date(2026, 10, 14), CSV_2026)):
        f = RawFile(day, nse_indices.url_for(day), nse_indices.file_name(day))
        path = raw_path(lake, "nse_indices", f)
        path.parent.mkdir(parents=True)
        path.write_text(csv)
    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    import stocksense.jobs.ingest_market as job

    orig = job.download_all
    job.download_all = lambda *a, **k: orig(*a, **{**k, "transport": transport, "per_second": 1000})
    try:
        assert ingest_market.run_indices(date(2015, 1, 2), date(2015, 1, 2), lake=lake) == 1
        assert ingest_market.run_indices(date(2026, 10, 14), date(2026, 10, 14), lake=lake) == 1
    finally:
        job.download_all = orig
    df = lake.query("select strftime(date, '%Y') as y, close from index_prices where index = 'NIFTY_BANK' order by y")
    assert df.values.tolist() == [["2015", 19057.8], ["2026", 55316.0]]


def chart(timestamps, closes, offset=19800):
    return {"chart": {"result": [{"meta": {"gmtoffset": offset}, "timestamp": timestamps,
                                  "indicators": {"quote": [{"open": closes, "high": closes, "low": closes,
                                                            "close": closes, "volume": [0] * len(closes)}]}}]}}


def test_yahoo_frame_uses_exchange_local_dates_and_drops_gaps():
    # 2026-10-13 18:45 UTC is already 14 Oct 00:15 in India: the IST trading date counts.
    late = int(datetime(2026, 10, 13, 18, 45, tzinfo=timezone.utc).timestamp())
    df = yahoo_history.to_frame("NIFTY50_YF", chart([late, late + 86400], [22622.7, None]))
    assert df[["series", "date", "close"]].values.tolist() == [["NIFTY50_YF", date(2026, 10, 14), 22622.7]]
    assert yahoo_history.to_frame("X", {"chart": {"result": None}}).empty


def test_macro_job_writes_one_table(tmp_path):
    lake = Lake(tmp_path)
    payload = chart([1792035900], [100.0], offset=0)
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    table = ingest_market.run_macro(lake=lake, today=date(2026, 10, 16), transport=transport)
    assert set(table["series"]) == set(yahoo_history.SERIES)
    assert lake.query("select count(*) from macro_prices").iloc[0, 0] == len(yahoo_history.SERIES)
