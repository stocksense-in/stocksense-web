import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from stocksense.downloads import RawFile, raw_path
from stocksense.jobs import ingest_fno
from stocksense.lake import Lake
from stocksense.sources import fno_bhavcopy as fno

OLD = (
    "INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,OPEN_INT,CHG_IN_OI,TIMESTAMP,\n"
    "FUTIDX,NIFTY,25-Jul-2024,0,XX,24300,24400,24250,24379.4,24379.4,230381,1400814.91,14171325,-371200,05-JUL-2024,\n"
    "FUTIDX,NIFTY,29-Aug-2024,0,XX,24400,24500,24350,24497.25,24497.25,19025,116282.77,1387175,27600,05-JUL-2024,\n"
    "OPTIDX,NIFTY,11-Jul-2024,24000,PE,50,60,40,45,45,1000,6000,500000,1000,05-JUL-2024,\n"
    "OPTIDX,NIFTY,11-Jul-2024,23900,PE,30,40,20,25,25,800,4000,700000,1000,05-JUL-2024,\n"
    "OPTIDX,NIFTY,11-Jul-2024,25000,CE,10,12,8,9,9,1200,7000,900000,1000,05-JUL-2024,\n"
    "OPTIDX,NIFTY,25-Jul-2024,25000,CE,80,90,70,85,85,300,2000,400000,1000,05-JUL-2024,\n"
    "OPTSTK,TCS,25-Jul-2024,4000,CE,100,110,90,105,105,50,300,10000,0,05-JUL-2024,\n"
)
UDIFF_HEAD = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,"
              "OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,"
              "ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n")
UDIFF = UDIFF_HEAD + (
    "2024-07-08,2024-07-08,FO,NSE,IDF,1,,NIFTY,,2024-07-25,2024-07-25,,,NIFTY24JULFUT,24300,24400,24250,24375.60,24375,"
    "24379.4,24320.55,24375.60,14239275,67950,130096,79178179681.25,1,F1,25,,,,,\n"
    "2024-07-08,2024-07-08,FO,NSE,IDO,2,,NIFTY,,2024-07-11,2024-07-11,24000.00,PE,NIFTY24JUL24000PE,50,60,40,45,45,"
    "45,24320.55,45,600000,100000,1500,1000000.00,1,F1,25,,,,,\n"
    "2024-07-08,2024-07-08,FO,NSE,IDO,3,,NIFTY,,2024-07-11,2024-07-11,25000.00,CE,NIFTY24JUL25000CE,9,10,8,9,9,"
    "9,24320.55,9,1000000,100000,2000,1000000.00,1,F1,25,,,,,\n"
)


def zipped(text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("fo.csv", text)
    return buf.getvalue()


def test_urls_switch_format_on_8_july_2024():
    assert fno.url_for(date(2024, 7, 5)) == (
        "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/2024/JUL/fo05JUL2024bhav.csv.zip")
    assert fno.url_for(date(2024, 7, 8)) == (
        "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip")


def test_parse_old_format_units():
    df = fno.parse(zipped(OLD))
    assert list(df.columns) == fno.COLUMNS
    fut = df[(df.instrument == "FUTIDX")].iloc[0]
    assert fut.expiry == date(2024, 7, 25) and pd.isna(fut.strike) and fut.option_type == ""
    assert fut.contracts == 230381 and fut.open_interest == 14171325
    assert fut.turnover == pytest.approx(1400814.91 * 1e5)  # ₹ lakh → ₹
    assert pd.isna(fut.underlying) and pd.isna(fut.lot_size)


def test_parse_two_digit_expiry_years():
    # NSE's 14 May 2012 file writes "31-May-12".
    df = fno.parse(zipped(OLD.replace("25-Jul-2024", "25-Jul-24")))
    assert df["expiry"].notna().all() and date(2024, 7, 25) in set(df["expiry"])


def test_parse_udiff_maps_instruments_and_keeps_extras():
    df = fno.parse(zipped(UDIFF))
    assert df["instrument"].tolist() == ["FUTIDX", "OPTIDX", "OPTIDX"]
    fut = df.iloc[0]
    assert (fut.contracts, fut.open_interest, fut.lot_size) == (130096, 14239275, 25)
    assert fut.turnover == pytest.approx(79178179681.25) and fut.underlying == pytest.approx(24320.55)
    assert df.iloc[1][["strike", "option_type"]].tolist() == [24000.0, "PE"]


def test_summary_per_underlying():
    day = date(2024, 7, 5)
    s = fno.summarise(fno.parse(zipped(OLD)), day).set_index("symbol")
    nifty = s.loc["NIFTY"]
    assert nifty.kind == "index" and nifty.fut_near_expiry == date(2024, 7, 25) and nifty.fut_near_close == 24379.4
    assert nifty.fut_oi == 14171325 + 1387175
    assert (nifty.call_oi, nifty.put_oi) == (1300000, 1200000)
    assert nifty.pcr_oi == pytest.approx(1200000 / 1300000)
    assert nifty.opt_near_expiry == date(2024, 7, 11)
    assert nifty.near_pcr_oi == pytest.approx(1200000 / 900000)
    assert (nifty.max_call_oi_strike, nifty.max_put_oi_strike) == (25000.0, 23900.0)
    assert s.loc["TCS"].kind == "stock" and s.loc["TCS"].pcr_oi == 0  # calls but no puts
    assert pd.isna(s.loc["TCS"].max_put_oi_strike)


def test_expired_contracts_are_ignored_in_the_summary():
    s = fno.summarise(fno.parse(zipped(OLD)), date(2024, 7, 20))  # weekly 11-Jul options expired
    assert s.set_index("symbol").loc["NIFTY"].opt_near_expiry == date(2024, 7, 25)


def test_build_writes_prices_and_summary(tmp_path):
    lake = Lake(tmp_path)
    for day, text in ((date(2024, 7, 5), OLD), (date(2024, 7, 8), UDIFF)):
        path = raw_path(lake, "nse_fno_bhavcopy", RawFile(day, "", fno.file_name(day)))
        path.parent.mkdir(parents=True)
        path.write_bytes(zipped(text))
    assert ingest_fno.build(lake, date(2024, 7, 5), date(2024, 7, 8), workers=2) == 2  # parallel path
    assert ingest_fno.build(lake, date(2024, 7, 5), date(2024, 7, 8)) == 0
    counts = lake.query("select strftime(date, '%Y-%m-%d') as d, count(*) as n from fno_prices group by d order by d")
    assert counts.values.tolist() == [["2024-07-05", 7], ["2024-07-08", 3]]
    s = lake.query("select strftime(date, '%Y-%m-%d') as d, underlying from fno_summary where symbol = 'NIFTY' order by d")
    assert pd.isna(s["underlying"].iloc[0]) and s["underlying"].iloc[1] == pytest.approx(24320.55)
