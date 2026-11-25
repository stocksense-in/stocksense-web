from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from conftest import ROWS
from stocksense import dividends
from stocksense.api import create_app

TODAY = date(2026, 11, 26)


def actions(symbol="TCS"):
    rows = [(date(2021, 7, 16), "dividend", 7.0, "Interim Dividend Rs 7"),
            (date(2022, 7, 15), "dividend", 8.0, "Interim Dividend Rs 8"),
            (date(2023, 7, 14), "dividend", 9.0, "Interim Dividend Rs 9"),
            (date(2024, 7, 16), "dividend", 10.0, "Interim Dividend Rs 10"),
            (date(2025, 7, 16), "dividend", 11.0, "Interim Dividend Rs 11"),
            (date(2026, 1, 16), "dividend", 57.0, "Interim Dividend Rs 11 / Special Dividend Rs 46"),
            (date(2026, 7, 15), "dividend", 12.0, "Interim Dividend Rs 12"),
            (date(2027, 1, 15), "dividend", 13.0, "Interim Dividend Rs 13"),  # announced, not yet ex
            (date(2018, 5, 31), "bonus", None, "Bonus 1:1")]
    return pd.DataFrame([{"symbol": symbol, "ex_date": d, "kind": k, "dividend": v, "subject": s} for d, k, v, s in rows])


def test_years_streak_ttm_and_actions():
    tcs = dividends.build(actions(), today=TODAY)["companies"]["TCS"]
    assert [y["fiscal_year"] for y in tcs["years"]] == [2022, 2023, 2024, 2025, 2026]
    assert tcs["years"][-1]["per_share"] == 68.0  # FY26: Jul 2025 11 + Jan 2026 57
    assert tcs["ttm_per_share"] == 69.0  # Jan 2026 57 + Jul 2026 12; the Jan 2027 one isn't paid yet
    assert tcs["paid_years_in_a_row"] == 5 and tcs["last_dividend"] == {"ex_date": "2026-07-15", "per_share": 12.0}
    assert not tcs["streak_since_data_start"]  # the data starts in 2018, FY2019-21 had no dividend
    assert tcs["capital_actions"][0]["kind"] == "bonus"


def test_note():
    tcs = dividends.build(actions(), today=TODAY)["companies"]["TCS"]
    assert dividends.note(tcs, 3450.0) == ("Paid a dividend every year for the last 5 years. "
                                           "₹69 per share over the past 12 months, a 2.0% yield at ₹3,450.")
    assert "kept in the business" in dividends.note({"paid_years_in_a_row": 0, "ttm_per_share": 0})


def test_api(market):
    symbol = ROWS[0]["symbol"]
    doc = dividends.build(actions(symbol), today=TODAY)
    client = TestClient(create_app(market=market, headlines=lambda: [], history=lambda s, r: [], dividends=lambda: doc))
    body = client.get(f"/stocks/{symbol}/dividends").json()
    assert body["ttm_per_share"] == 69.0 and "every year" in body["note"]
    assert client.get("/stocks/NOPE/dividends").status_code == 404
    assert client.get(f"/stocks/{symbol}").json()["available"]["dividends"] is True


def test_streak_back_to_the_start_of_the_data():
    rows = pd.DataFrame([{"symbol": "X", "ex_date": date(y, 8, 1), "kind": "dividend", "dividend": 1.0, "subject": "Div"}
                         for y in range(2010, 2026)])
    x = dividends.build(rows, today=TODAY)["companies"]["X"]
    assert x["streak_since_data_start"] and x["data_from_fiscal_year"] == 2012
    assert dividends.note(x).startswith("Paid a dividend every year since FY2012 (as far back as this data goes).")
