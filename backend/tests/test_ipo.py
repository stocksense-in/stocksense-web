from datetime import date

import pytest
from fastapi.testclient import TestClient

from stocksense import ipo
from stocksense.api import create_app
from stocksense.sources.nse_ipo import NseUnavailable

TODAY = date(2026, 10, 14)

CATEGORY = {
    "updateTime": "14-Oct-2026 17:00:00",
    "dataList": [
        {"srNo": "Sr.No.", "category": "Category", "noOfTotalMeant": "No. of times"},
        {"srNo": "1", "category": "Qualified Institutional Buyers(QIBs)", "noOfTotalMeant": "1.04"},
        {"srNo": "1(a)", "category": "Foreign Institutional Investors(FIIs)", "noOfTotalMeant": ""},
        {"srNo": "2", "category": "Non Institutional Investors", "noOfTotalMeant": "11.38"},
        {"srNo": "3", "category": "Retail Individual Investors(RIIs)", "noOfTotalMeant": "3.78"},
        {"srNo": None, "category": "Total", "noOfTotalMeant": "4.62"},
    ],
}


def test_parsers():
    assert ipo.parse_band("Rs.275 to Rs.289") == (275, 289)
    assert ipo.parse_band("Rs.1000") == (1000, 1000)
    assert ipo.parse_band("-") is None
    assert ipo.parse_date("05-OCT-2026") == date(2026, 10, 5)
    assert ipo.parse_number("1.8420492E7") == 18420492
    assert ipo.parse_number("    75") == 75 and ipo.parse_number("") is None


def test_subscription_reads_main_rows_only():
    sub = ipo.parse_subscription(CATEGORY)
    assert (sub.qib, sub.nii, sub.retail, sub.total) == (1.04, 11.38, 3.78, 4.62)


def test_build_issue_status_and_size():
    raw = {"symbol": "ZETWERK", "companyName": "Zetwerk", "issueStartDate": "15-Oct-2026", "issueEndDate": "19-Oct-2026",
           "issuePrice": "Rs.143 to Rs.151", "issueSize": "342495665", "series": "EQ"}
    issue = ipo.build_issue(raw, today=TODAY)
    assert issue.status == "upcoming" and issue.board == "mainboard"
    assert issue.size_crore == 5171.7
    assert issue.demand.level == "early"
    assert ipo.build_issue(raw, today=date(2026, 10, 16)).status == "open"
    assert ipo.build_issue(raw, today=date(2026, 10, 20)).status == "closed"


@pytest.mark.parametrize("qib,total,status,level", [
    (25, 40, "open", "strong"),
    (3, 2.5, "closed", "moderate"),
    (None, 4.6, "open", "moderate"),
    (0.2, 0.4, "open", "early"),
    (0.5, 1.5, "open", "weak"),
    (0.5, 1.5, "closed", "weak"),
])
def test_demand_levels(qib, total, status, level):
    assert ipo.assess_demand(ipo.Subscription(qib=qib, total=total), status).level == level


def test_recent_listings_returns_and_filters():
    past = [
        {"symbol": "ORIENTCABL", "company": "Orient Cables", "listingDate": "05-OCT-2026", "issuePrice": "272", "priceRange": "Rs.258 to Rs.272", "securityType": "EQ"},
        {"symbol": "OLDCO", "company": "Old Co", "listingDate": "01-JAN-2026", "issuePrice": "100", "securityType": "EQ"},
        {"symbol": "BOND1", "company": "Some Bond", "listingDate": "05-OCT-2026", "issuePrice": "-", "securityType": "DEBT"},
        {"symbol": "NOPX", "company": "No Price", "listingDate": "06-OCT-2026", "issuePrice": "-", "priceRange": "Rs.50 to Rs.55", "securityType": "SME"},
    ]
    rows = ipo.recent_listings(past, {"ORIENTCABL": 414.1}, days=30, today=TODAY)
    assert [r["symbol"] for r in rows] == ["NOPX", "ORIENTCABL"]
    assert rows[1]["return_pct"] == 52.24
    assert rows[0]["issue_price"] == 55 and rows[0]["return_pct"] is None and rows[0]["board"] == "sme"


class FakeNse:
    NseUnavailable = NseUnavailable

    def __init__(self, fail=False):
        self.fail = fail

    def _check(self):
        if self.fail:
            raise NseUnavailable("down")

    def current_issues(self):
        self._check()
        return [{"symbol": "HDFIRE", "noOfTime": "4.62"}]

    def upcoming_issues(self):
        self._check()
        return [
            {"symbol": "HDFIRE", "companyName": "HD Fire", "issueStartDate": "01-Jan-2020", "issueEndDate": "31-Dec-2099",
             "issuePrice": "Rs.258 to Rs.271", "issueSize": "18420492", "series": "EQ"},
            {"symbol": "LATER", "companyName": "Later Ltd", "issueStartDate": "01-Jan-2099", "issueEndDate": "05-Jan-2099",
             "issuePrice": "Rs.10 to Rs.12", "issueSize": "1000000", "series": "EQ"},
        ]

    def category_subscription(self, symbol):
        return CATEGORY

    def past_issues(self):
        self._check()
        return []


def test_ipo_endpoint(market):
    body = TestClient(create_app(market=market, nse=FakeNse())).get("/ipos").json()
    assert [i["symbol"] for i in body["open"]] == ["HDFIRE"]
    assert body["open"][0]["subscription"]["retail"] == 3.78
    assert [i["symbol"] for i in body["upcoming"]] == ["LATER"]


def test_ipo_endpoint_reports_nse_outage(market):
    resp = TestClient(create_app(market=market, nse=FakeNse(fail=True))).get("/ipos")
    assert resp.status_code == 503 and "unavailable" in resp.json()["detail"]
