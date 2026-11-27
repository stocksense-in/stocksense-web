import json
from datetime import date, datetime

import pandas as pd
import pytest

from stocksense.jobs import ingest_filings
from stocksense.lake import Lake
from stocksense.sources import nse_filings

ANN = [
    {"seq_id": "106818038", "symbol": "ACMESOLAR", "sm_name": "Acme Solar Holdings Limited", "sm_isin": "INE622W01025",
     "desc": "General Updates", "attchmntText": "formation of a wholly owned subsidiary",
     "attchmntFile": "https://nsearchives.nseindia.com/corporate/x.pdf", "an_dt": "14-Oct-2026 23:40:23",
     "sort_date": "2026-10-14 23:40:23", "hasXbrl": True},
    {"seq_id": "106818038", "symbol": "ACMESOLAR", "sort_date": "2026-10-14 23:40:23", "desc": "General Updates"},  # dup
    {"seq_id": "1", "symbol": "TCS", "desc": "Outcome of Board Meeting", "an_dt": "15-Oct-2026 16:05:00"},  # old-style date
    {"seq_id": "2", "symbol": "BAD", "desc": "x"},  # no date: dropped
]
PIT = [
    {"symbol": "GEOJITFSL", "company": "Geojit Financial Services Limited", "acqName": "Krishnan Ramachandran",
     "personCategory": "Employees/Designated Employees", "secType": "Equity Shares", "tdpTransactionType": "Buy",
     "acqMode": "ESOP", "secAcq": "50000", "secVal": "1275000", "befAcqSharesNo": "150000", "afterAcqSharesNo": "200000",
     "befAcqSharesPer": "0.064", "afterAcqSharesPer": "-", "acqfromDt": "22-Jan-2016", "acqtoDt": "22-Jan-2016",
     "intimDt": "27-Jan-2016", "date": "30-Jan-2016 17:08"},
]
FII = [{"buyValue": "17201.8", "category": "DII", "date": "16-Oct-2026", "netValue": "-3661.28", "sellValue": "20863.08"},
       {"buyValue": "19951.59", "category": "FII/FPI", "date": "16-Oct-2026", "netValue": "1165.92", "sellValue": "18785.67"}]


def test_announcements_frame():
    df = nse_filings.announcements_frame(ANN)
    assert df["symbol"].tolist() == ["ACMESOLAR", "TCS"]
    first = df.iloc[0]
    assert first.broadcast_at == datetime(2026, 10, 14, 23, 40, 23) and first.has_xbrl
    assert first.category == "General Updates" and first.attachment.endswith(".pdf")
    assert df.iloc[1].broadcast_at == datetime(2026, 10, 15, 16, 5)


def test_insider_frame():
    r = nse_filings.insider_frame(PIT).iloc[0]
    # r["mode"], not r.mode: that's pandas' Series.mode method.
    assert [r[c] for c in ("symbol", "transaction", "mode", "quantity", "value")] == ["GEOJITFSL", "Buy", "ESOP", 50000, 1275000]
    assert r["pct_before"] == pytest.approx(0.064) and pd.isna(r["pct_after"])  # NSE writes "-"
    assert r["disclosed_at"] == datetime(2016, 1, 30, 17, 8) and r["traded_from"] == datetime(2016, 1, 22)


def test_fii_dii_frame():
    df = nse_filings.fii_dii_frame(FII)
    assert df["category"].tolist() == ["DII", "FII"] and df["net_cr"].tolist() == [-3661.28, 1165.92]


def test_months_cover_the_range():
    assert ingest_filings.months(date(2025, 11, 15), date(2026, 2, 3)) == [
        (date(2025, 11, 1), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)), (date(2026, 2, 1), date(2026, 2, 3))]


def test_sync_fetches_old_months_once_and_refetches_recent(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    calls = []

    def fake_fetch(c, first, last):
        calls.append(first)
        return [{**ANN[0], "seq_id": f"{first}", "sort_date": f"{first} 10:00:00"}]

    monkeypatch.setattr(nse_filings, "fetch_announcements", fake_fetch)
    monkeypatch.setattr(nse_filings, "client", lambda: _Null())
    n = ingest_filings.run_announcements(lake, date(2026, 6, 1), date(2026, 9, 30), pause=0)
    assert n == 4 and len(calls) == 4
    calls.clear()
    ingest_filings.run_announcements(lake, date(2026, 6, 1), date(2026, 9, 30), pause=0)
    assert calls == [date(2026, 8, 1), date(2026, 9, 1)]  # only the latest two months again
    assert lake.query("select count(*) from announcements").iloc[0, 0] == 4
    assert json.loads((tmp_path / "raw" / "nse_announcements" / "2026-06-01" / "announcements.json").read_text())


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


BULK = """Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks
27-NOV-2026,AGIIL,Agi Infra Limited,THAKKAR NILESHKUMAR FARSHURAM HUF,BUY,1150000,307.77,-
27-NOV-2026,AKG,AKG Exim Limited,SHRI MUKTA SHARES,SELL,"1,67,495",8.30,-
"""
BLOCK = """Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price
27-NOV-2026,IGIL,Intl Gemological Inst Ltd,OLD BRIDGE MUTUAL FUND,BUY,2400000,417.00
"""


def test_deals_frame():
    df = nse_filings.deals_frame(BULK, "bulk")
    assert list(df["symbol"]) == ["AGIIL", "AKG"] and list(df["side"]) == ["buy", "sell"]
    assert df["quantity"].iloc[1] == 167495 and df["remarks"].iloc[0] == ""
    assert df["value_cr"].iloc[0] == round(1150000 * 307.77 / 1e7, 2)  # ₹35.39 crore
    block = nse_filings.deals_frame(BLOCK, "block")  # no Remarks column
    assert block["kind"].iloc[0] == "block" and block["value_cr"].iloc[0] == 100.08
    # a day without deals: header only, or nothing at all
    assert nse_filings.deals_frame(BULK.splitlines()[0] + "\n", "bulk").empty
    assert nse_filings.deals_frame("", "bulk").empty


def test_run_deals_keeps_the_trading_day(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    monkeypatch.setattr(ingest_filings, "PAUSE_SECONDS", 0)
    monkeypatch.setattr(nse_filings, "client", lambda: _Null())
    df = ingest_filings.run_deals(lake, fetch=lambda c, kind: BULK if kind == "bulk" else BLOCK)
    assert len(df) == 3
    assert (tmp_path / "raw" / "nse_deals" / "2026-11-27" / "block.csv").read_text().startswith("Date,")
    got = lake.query("select kind, symbol, value_cr from deals order by value_cr desc")
    assert list(got["symbol"]) == ["IGIL", "AGIIL", "AKG"]
    # rerun the same day: the partition is replaced, not doubled
    ingest_filings.run_deals(lake, fetch=lambda c, kind: BULK if kind == "bulk" else BLOCK)
    assert lake.query("select count(*) from deals").iloc[0, 0] == 3
