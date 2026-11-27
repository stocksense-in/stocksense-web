from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from stocksense import events as ev
from stocksense.api import create_app

TODAY = date(2026, 11, 27)
URL = "https://nsearchives.nseindia.com/corporate/"


def ann(symbol, category, summary, at, link=None):
    return {"symbol": symbol, "category": category, "summary": summary, "broadcast_at": pd.Timestamp(at),
            "attachment": link}


ANNOUNCEMENTS = pd.DataFrame([
    ann("TCS", "Outcome of Board Meeting", "Tata Consultancy Services Limited has informed the Exchange regarding "
        "'Outcome of Board Meeting held on October 9, 2026'.", "2026-10-09 16:00", URL + "TCS_09102026.pdf"),
    ann("TCS", "Outcome of Board Meeting", "Tata Consultancy Services Limited has informed the Exchange regarding "
        "'Outcome of Board Meeting held on October 9, 2026'.", "2026-10-09 16:04"),  # posted twice
    ann("TCS", "Copy of Newspaper Publication", "Newspaper copy", "2026-10-10 10:00"),  # routine: dropped
    ann("TCS", "Trading Window", "Trading window closure", "2026-09-25 10:00"),  # routine: dropped
    ann("TCS", "Bagging/Receiving of orders/contracts", "TCS has informed the Exchange about 'Order win from a UK "
        "insurer'.", "2026-08-01 09:00", "https://nsearchives.nseindia.in/corporate/TCS_order.pdf"),
    ann("TCS", "Press Release", "A press release dated July 1, 2026, titled \"Media Release on the subject TCS opens "
        "a new centre in Pune\"", "2026-07-01 12:00"),
    ann("TCS", "Credit Rating", "Credit rating reaffirmed", "2025-06-01 12:00"),  # older than a year: dropped
    ann("ABC", "Resignation of Statutory Auditor", "ABC Limited has informed the Exchange regarding 'Resignation of "
        "Statutory Auditor'.", "2026-11-20 18:00"),
    ann("ABC", "Suspension of Trading", "Members of the Exchange are hereby informed that the trading in the partly "
        "paid-up equity shares of ABC shall be suspended", "2026-11-01 18:00"),  # routine suspension: dropped
    ann("ABC", "Disclosure under SEBI Takeover Regulations", "Disclosure under Regulation 30 of the SEBI (Listing "
        "Obligations and Disclosure Requirements) Regulations, 2015 - stake sale", "2026-11-02 18:00"),  # not kept
])

INSIDERS = pd.DataFrame([
    {"symbol": "ABC", "person": "A Promoter", "person_category": "Promoters", "mode": "Market Sale",
     "value": 5e8, "pct_after": 40.5, "date": date(2026, 4, 1)},
    {"symbol": "ABC", "person": "A Director", "person_category": "Director", "mode": "Market Purchase",
     "value": 1e7, "pct_after": 0.2, "date": date(2026, 5, 2)},
    {"symbol": "ABC", "person": "Staff", "person_category": "Employees/Designated Employees", "mode": "Market Sale",
     "value": 9e9, "pct_after": 0.0, "date": date(2026, 5, 1)},  # not an insider for this purpose
    {"symbol": "ABC", "person": "A Promoter", "person_category": "Promoters", "mode": "Market Sale",
     "value": 7e9, "pct_after": 45.0, "date": date(2024, 1, 1)},  # more than two years before the feed ends
])


def test_titles_lose_nse_wrappers():
    assert ev.title_of("Infosys Limited has submitted to the Exchange, the financial results for the period ended "
                       "Jun 30, 2026", "Financial Results") == "The financial results for the period ended Jun 30, 2026"
    assert ev.title_of("Disclosure under Regulation 30 of the SEBI (Listing Obligations and Disclosure Requirements) "
                       "Regulations, 2015- Update regarding Senior Management Personnel", "x") == (
        "Update regarding Senior Management Personnel")
    assert ev.title_of("", "Credit Rating") == "Credit Rating"
    assert ev.group_of("Defaults on Payment of Interest/Principal") == "warning"
    assert ev.group_of("Clarification - Financial Results") == "exchange"
    assert ev.group_of("Investor Presentation") is None


def test_export_keeps_notable_announcements_and_insider_market_trades():
    doc = ev.build(ANNOUNCEMENTS, INSIDERS, TODAY)
    tcs = doc["companies"]["TCS"]
    assert [a["group"] for a in tcs["announcements"]] == ["results", "orders", "business"]
    assert tcs["announcements"][0]["title"] == "Outcome of Board Meeting held on October 9, 2026"
    assert tcs["announcements"][0]["link"] == "TCS_09102026.pdf"  # archive prefix dropped
    assert tcs["announcements"][1]["link"].startswith("https://nsearchives.nseindia.in/")  # mirror kept whole
    assert tcs["announcements"][2]["title"] == "TCS opens a new centre in Pune"
    assert tcs["counts"] == {"results": 1, "orders": 1, "business": 1}
    abc = doc["companies"]["ABC"]
    assert [a["group"] for a in abc["announcements"]] == ["warning"]
    assert abc["insiders"]["sold_cr"] == 50.0 and abc["insiders"]["bought_cr"] == 1.0
    assert [t["side"] for t in abc["insiders"]["trades"]] == ["buy", "sell"]
    assert doc["insiders_until"] == "2026-05-02"
    assert "selling alone says less" in ev.insider_note(abc, doc["insiders_until"])


def test_events_endpoint(market):
    doc = ev.build(ANNOUNCEMENTS, INSIDERS, TODAY)
    c = TestClient(create_app(market=market, headlines=lambda: [], events=lambda: doc))
    body = c.get("/stocks/tcs/events").json()
    assert body["symbol"] == "TCS" and body["insiders"] is None and body["insider_note"] is None
    assert body["announcements"][0]["link"] == URL + "TCS_09102026.pdf"  # full address restored
    assert c.get("/stocks/TCS").json()["available"]["events"] is True
    assert c.get("/stocks/INFY").json()["available"]["events"] is False
    assert c.get("/stocks/INFY/events").status_code == 404


def test_money_reads_in_lakh_under_a_crore():
    assert ev.money(0.25) == "₹25 lakh" and ev.money(0.031) == "₹3.1 lakh"
    assert ev.money(0) == "₹0 cr" and ev.money(1343.21) == "₹1,343.2 cr"


def test_screener_filters_on_insiders_and_red_flags(market):
    doc = {"companies": {
        "TCS": {"announcements": [], "counts": {"warning": 1}, "insiders": None},
        "INFY": {"announcements": [], "counts": {"results": 4},
                 "insiders": {"bought_cr": 5.0, "sold_cr": 1.0, "buys": 2, "sells": 1, "trades": []}},
    }}
    c = TestClient(create_app(market=market, headlines=lambda: [], events=lambda: doc))
    total = c.get("/stocks").json()["total"]
    assert [s["symbol"] for s in c.get("/stocks", params={"insiders": "buying"}).json()["results"]] == ["INFY"]
    without = c.get("/stocks", params={"red_flags": "none", "page_size": 200}).json()
    assert without["total"] == total - 1 and "TCS" not in {s["symbol"] for s in without["results"]}
    assert c.get("/stocks", params={"insiders": "selling"}).status_code == 422


DEALS = pd.DataFrame([
    {"date": date(2026, 11, 27), "kind": "bulk", "symbol": "IGIL", "client": "OLD BRIDGE MUTUAL FUND", "side": "buy",
     "quantity": 2400000.0, "price": 417.0, "value_cr": 100.08},
    {"date": date(2026, 11, 27), "kind": "block", "symbol": "IGIL", "client": "OLD BRIDGE MUTUAL FUND", "side": "buy",
     "quantity": 2400000.0, "price": 417.0, "value_cr": 100.08},  # the same trade in both files: listed once
    {"date": date(2026, 11, 27), "kind": "bulk", "symbol": "IGIL", "client": "SMALL FUND", "side": "sell",
     "quantity": 10000.0, "price": 417.0, "value_cr": 0.42},
    {"date": date(2026, 11, 28), "kind": "bulk", "symbol": "TCS", "client": "A FUND", "side": "sell",
     "quantity": 50000.0, "price": 3000.0, "value_cr": 15.0},
])


def test_deals_join_the_company_events():
    doc = ev.build(ANNOUNCEMENTS, INSIDERS, TODAY, DEALS)
    assert doc["deals_since"] == "2026-11-27"
    igil = doc["companies"]["IGIL"]  # a company with deals only still gets an entry
    assert [(d["kind"], d["client"]) for d in igil["deals"]] == [("block", "Old Bridge Mutual Fund"), ("bulk", "Small Fund")]
    assert igil["announcements"] == [] and igil["insiders"] is None
    assert doc["companies"]["TCS"]["deals"][0]["value_cr"] == 15.0
    assert "deals" not in doc["companies"]["ABC"]
    c = TestClient(create_app(market=None, headlines=lambda: [], events=lambda: doc))
    body = c.get("/stocks/igil/events").json()
    assert body["deals"][0]["quantity"] == 2400000 and body["deals_since"] == "2026-11-27"
    assert ev.build(ANNOUNCEMENTS, INSIDERS, TODAY)["deals_since"] is None  # no deals data yet
