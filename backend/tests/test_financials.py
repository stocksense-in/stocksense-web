from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from stocksense import financials
from stocksense.api import create_app

ENDS = [date(y, m, d) for y in range(2021, 2025) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))]


def results(symbol="ACME"):
    rows = []
    for i, end in enumerate(ENDS):
        for consolidated, scale in ((True, 1.0), (False, 0.8)):
            revenue = (100 + i) * scale
            rows.append({"symbol": symbol, "period_end": end, "consolidated": consolidated, "kind": "company",
                         "revenue": revenue, "net_revenue": revenue, "net_profit": revenue / 10, "eps": 1.5,
                         "suspect": False})
    return pd.DataFrame(rows)


def test_build_quarters_years_and_metrics_on_one_basis():
    doc = financials.build(results(), today=date(2025, 1, 15))
    acme = doc["companies"]["ACME"]
    assert acme["basis"] == "consolidated" and len(acme["quarters"]) == financials.QUARTERS
    assert acme["quarters"][-1] == {"period_end": "2024-12-31", "revenue": 115.0, "net_profit": 11.5, "eps": 1.5,
                                    "margin_pct": 10.0}
    # FY2022–FY2024 are complete (Apr–Mar); FY2021 has one quarter, FY2025 three.
    assert [y["fiscal_year"] for y in acme["years"]] == [2022, 2023, 2024]
    assert acme["years"][0]["revenue"] == 101 + 102 + 103 + 104
    assert acme["metrics"]["as_of"] == "2024-12-31" and acme["metrics"]["net_margin"] == 10.0


def test_suspect_quarters_are_left_out():
    df = results()
    df.loc[df["period_end"] == date(2023, 6, 30), "suspect"] = True
    years = financials.build(df)["companies"]["ACME"]["years"]
    assert 2024 not in [y["fiscal_year"] for y in years]  # FY2024 lost a quarter


def test_api_serves_financials_and_404s_unknown(market):
    doc = financials.build(results("TCS"))
    client = TestClient(create_app(market=market, headlines=lambda: [], history=lambda s, r: [],
                                   financials=lambda: doc))
    body = client.get("/stocks/tcs/financials").json()
    assert body["symbol"] == "TCS" and body["basis"] == "consolidated" and body["unit"] == "₹ crore"
    assert body["years"][-1]["fiscal_year"] == 2024
    missing = client.get("/stocks/NOPE/financials")
    assert missing.status_code == 404 and "No filed results" in missing.json()["detail"]
