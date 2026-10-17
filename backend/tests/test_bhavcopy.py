import io
import zipfile
from datetime import date

import httpx
import pandas as pd
import pytest

from stocksense.downloads import RawFile, download_all, raw_path
from stocksense.jobs import ingest_bhavcopy
from stocksense.lake import Lake
from stocksense.sources import bhavcopy

OLD_CSV = (
    "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,\n"
    "TCS,EQ,2500,2550,2480,2540.5,2541,2490,1000,2540500,02-JAN-2015,50,INE467B01029,\n"
    "INFY,EQ,1960,1990,1950,1985,1984,1970,2000,3970000,02-JAN-2015,80,INE009A01021,\n"
)
UDIFF_CSV = (
    "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,"
    "OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,"
    "ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
    "2026-10-14,2026-10-14,CM,NSE,STK,11536,INE467B01029,TCS,EQ,,,,,TATA CONSULTANCY,2274.00,2335.80,2265.60,"
    "2304.90,2305.00,2269.30,,2304.90,,,12145767,27990000000.50,300000,F1,1,,,,,\n"
)


def zipped(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


def test_urls_switch_format_on_8_july_2024():
    assert bhavcopy.url_for(date(2015, 1, 2)) == (
        "https://nsearchives.nseindia.com/content/historical/EQUITIES/2015/JAN/cm02JAN2015bhav.csv.zip")
    assert bhavcopy.url_for(date(2024, 7, 5)).endswith("/2024/JUL/cm05JUL2024bhav.csv.zip")
    assert bhavcopy.url_for(date(2024, 7, 8)) == (
        "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip")


def test_parse_old_format():
    df = bhavcopy.parse(zipped("cm02JAN2015bhav.csv", OLD_CSV))
    assert list(df.columns) == bhavcopy.COLUMNS
    tcs = df[df.symbol == "TCS"].iloc[0]
    assert (tcs.open, tcs.close, tcs.prev_close, tcs.volume, tcs.trades) == (2500, 2540.5, 2490, 1000, 50)
    assert tcs["isin"] == "INE467B01029"  # not tcs.isin: that's pandas' Series.isin method


def test_parse_early_format_without_isin_or_trades():
    early = ("SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,\n"
             "TCS,EQ,750,760,745,755.5,756,748,1000,755500,04-JAN-2010,\n")
    df = bhavcopy.parse(zipped("cm04JAN2010bhav.csv", early))
    assert list(df.columns) == bhavcopy.COLUMNS
    row = df.iloc[0]
    assert (row.symbol, row.close, row.volume) == ("TCS", 755.5, 1000)
    assert pd.isna(row.trades) and row["isin"] == ""


def test_parse_udiff_format_gives_same_columns():
    df = bhavcopy.parse(zipped("BhavCopy.csv", UDIFF_CSV))
    assert list(df.columns) == bhavcopy.COLUMNS
    row = df.iloc[0]
    assert (row.symbol, row.series, row.close, row.prev_close, row.volume) == ("TCS", "EQ", 2304.9, 2269.3, 12145767)
    assert row.turnover == pytest.approx(27990000000.5)


def fake_nse(responses):
    """MockTransport: url → (status, body); unknown URLs 404."""
    calls = []

    def handler(request):
        calls.append(str(request.url))
        status, body = responses.get(str(request.url), (404, b""))
        if isinstance(status, list):  # successive statuses for retries
            status = status.pop(0)
        return httpx.Response(status, content=body)

    return httpx.MockTransport(handler), calls


def test_download_is_resumable_and_remembers_old_holidays(tmp_path):
    lake = Lake(tmp_path)
    friday, saturday, today = date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 16)
    old_holiday = date(2026, 9, 1)
    files = [RawFile(d, bhavcopy.url_for(d), bhavcopy.file_name(d)) for d in (old_holiday, friday, saturday)]
    transport, calls = fake_nse({bhavcopy.url_for(friday): (200, zipped("x.csv", UDIFF_CSV))})

    stats = download_all(lake, "nse_bhavcopy", files, transport=transport, today=today, per_second=1000, sleep=lambda s: None)
    assert (stats.downloaded, stats.missing, stats.failed) == (1, 2, [])
    assert raw_path(lake, "nse_bhavcopy", files[1]).exists()
    # The old 404 is remembered; the recent one (may not be published yet) isn't.
    assert raw_path(lake, "nse_bhavcopy", files[0]).with_suffix(".zip.missing").exists()
    assert not raw_path(lake, "nse_bhavcopy", files[2]).parent.exists()

    calls.clear()
    stats = download_all(lake, "nse_bhavcopy", files, transport=transport, today=today, per_second=1000, sleep=lambda s: None)
    assert calls == [bhavcopy.url_for(saturday)]  # only the unsettled day is asked again
    assert stats.skipped == 2


def test_download_retries_server_errors(tmp_path):
    lake = Lake(tmp_path)
    day = date(2026, 10, 9)
    f = RawFile(day, bhavcopy.url_for(day), bhavcopy.file_name(day))
    transport, calls = fake_nse({f.url: ([503, 429, 200], b"zipdata")})
    stats = download_all(lake, "nse_bhavcopy", [f], transport=transport, today=day, per_second=1000, sleep=lambda s: None)
    assert stats.downloaded == 1 and len(calls) == 3


def test_download_gives_up_on_forbidden(tmp_path):
    lake = Lake(tmp_path)
    day = date(2026, 10, 9)
    f = RawFile(day, bhavcopy.url_for(day), bhavcopy.file_name(day))
    transport, calls = fake_nse({f.url: (403, b"")})
    stats = download_all(lake, "nse_bhavcopy", [f], transport=transport, today=day, per_second=1000, sleep=lambda s: None)
    assert len(stats.failed) == 1 and len(calls) == 1


def test_build_writes_one_partition_per_day(tmp_path):
    lake = Lake(tmp_path)
    old_day, new_day = date(2015, 1, 2), date(2026, 10, 14)
    for day, csv in ((old_day, OLD_CSV), (new_day, UDIFF_CSV)):
        path = raw_path(lake, "nse_bhavcopy", RawFile(day, "", bhavcopy.file_name(day)))
        path.parent.mkdir(parents=True)
        path.write_bytes(zipped("day.csv", csv))
    assert ingest_bhavcopy.build(lake, old_day, new_day) == 2
    assert ingest_bhavcopy.build(lake, old_day, new_day) == 0  # already built
    df = lake.query("select strftime(date, '%Y-%m-%d') as d, symbol, close from eod_prices order by d, symbol")
    assert df.values.tolist() == [["2015-01-02", "INFY", 1985.0], ["2015-01-02", "TCS", 2540.5],
                                  ["2026-10-14", "TCS", 2304.9]]
