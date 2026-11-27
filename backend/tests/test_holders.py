from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from conftest import ROWS
from stocksense import holders
from stocksense.api import create_app

QUARTERS = pd.date_range("2025-03-31", periods=7, freq="QE").date


def shareholding(symbol, promoter):
    return pd.DataFrame([{"symbol": symbol, "quarter_end": q, "promoter_pct": p, "public_pct": 100 - p,
                          "employee_trusts_pct": 0.0} for q, p in zip(QUARTERS, promoter)])


def test_build_and_notes():
    sh = pd.concat([shareholding("JSWSTEEL", [45, 45, 44.9, 44.8, 44.6, 44.5, 44.4]),
                    shareholding("SELLER", [75, 75, 74, 72, 70, 69, 68])])
    pledges = pd.DataFrame([{"symbol": "JSWSTEEL", "fetched": date(2026, 11, 26), "pledged_pct_of_promoter": 12.21,
                             "pledged_pct_of_total": 5.43, "all_pledges_pct_of_total": 7.8}])
    doc = holders.build(sh, pledges, today=date(2026, 11, 26))
    jsw, seller = doc["companies"]["JSWSTEEL"], doc["companies"]["SELLER"]
    assert len(jsw["quarters"]) == 7 and jsw["pledge"]["pledged_pct_of_promoter"] == 12.21
    assert "pledged 12%" in holders.pledge_warning(jsw) and holders.pledge_warning(seller) is None
    assert "held steady" in holders.trend_note(jsw)
    assert "cut their stake from 74.0% to 68.0%" in holders.trend_note(seller)
    assert holders.trend_note({"quarters": jsw["quarters"][:3]}) is None  # under a year of history


def test_high_pledge_is_a_stronger_warning():
    assert "push the price down" in holders.pledge_warning({"pledge": {"pledged_pct_of_promoter": 40.0}})


def test_api_holders_and_breakdown(market):
    symbol = ROWS[0]["symbol"]
    doc = holders.build(shareholding(symbol, [60, 60, 61, 61, 62, 63, 64]),
                        pd.DataFrame([{"symbol": symbol, "fetched": date(2026, 11, 26), "pledged_pct_of_promoter": 30.0,
                                       "pledged_pct_of_total": 19.0, "all_pledges_pct_of_total": 20.0}]))
    client = TestClient(create_app(market=market, headlines=lambda: [], history=lambda s, r: [], holders=lambda: doc))
    body = client.get(f"/stocks/{symbol.lower()}/holders").json()
    assert body["quarters"][-1]["promoter_pct"] == 64 and "raised" in body["trend_note"]
    assert "30%" in body["pledge_warning"]
    assert client.get("/stocks/NOPE/holders").status_code == 404
    detail = client.get(f"/stocks/{symbol}").json()
    promoter = [p for p in detail["score"]["breakdown"] if p["metric"] == "promoter"]
    if promoter:  # the fixture row has a promoter value
        assert "raised" in promoter[0]["history_note"] and "30%" in promoter[0]["guardrail"]


def test_slow_drift_and_no_promoter():
    hz = [64.92, 64.92, 64.92, 63.42, 63.42, 63.42, 61.84, 61.84, 61.84, 60.71, 60.71, 60.71]
    entry = {"quarters": [{"promoter_pct": p} for p in hz]}
    assert holders.trend_note(entry) == "Steady over the past year (60.7%), but down from 64.9% 3 years ago."
    assert "No promoter group" in holders.trend_note({"quarters": [{"promoter_pct": 0.0}] * 6})


def test_split_carried_where_known():
    sh = shareholding("TCS", [71.77] * 7)
    sh["fii_pct"] = [None] * 6 + [9.01]
    q = holders.build(sh)["companies"]["TCS"]["quarters"]
    assert q[-1]["fii_pct"] == 9.01 and q[0]["fii_pct"] is None and q[-1]["dii_pct"] is None


def test_stock_detail_says_which_panels_exist(market):
    symbol = ROWS[0]["symbol"]
    doc = holders.build(shareholding(symbol, [60] * 7))
    client = TestClient(create_app(market=market, headlines=lambda: [], history=lambda s, r: [],
                                   holders=lambda: doc, financials=lambda: None, dividends=lambda: None, events=lambda: None))
    assert client.get(f"/stocks/{symbol}").json()["available"] == {"financials": False, "holders": True, "dividends": False,
                                                                  "events": False}


def test_institutions_note_compares_a_year_of_the_split():
    sh = shareholding("BUYINGCO", [50.0] * 7)
    sh["fii_pct"] = [None, None, 12.0, 12.4, 13.1, 14.0, 15.5]
    sh["mutual_funds_pct"] = [None, None, 8.0, 8.0, 8.2, 8.1, 8.3]
    sh["dii_pct"] = [None, None, 20.0, 19.5, 19.0, 18.6, 18.2]
    entry = holders.build(sh)["companies"]["BUYINGCO"]
    note = holders.institutions_note(entry)  # Sep 2026 against Sep 2025
    assert note.startswith("Foreign investors raised their stake from 12.0% to 15.5%; "
                           "domestic institutions cut their stake from 20.0% to 18.2% over the past year.")
    assert "Mutual funds" not in note  # moved under a point
    assert holders.institutions_note({"quarters": entry["quarters"][-2:]}) is None  # under a year of the split
    flat = shareholding("FLAT", [50.0] * 7)
    flat["fii_pct"], flat["dii_pct"] = [10.0] * 7, [20.0] * 7
    assert "barely moved" in holders.institutions_note(holders.build(flat)["companies"]["FLAT"])
