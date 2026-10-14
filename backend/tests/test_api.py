import pytest
from fastapi.testclient import TestClient

from conftest import ROWS
from pdf_fixture import SAMPLE_DRHP, make_pdf
from stocksense.api import create_app
from stocksense.sources.news import Headline


@pytest.fixture
def client(market):
    headlines = lambda: [Headline("Brent crude jumps on Hormuz fears", "https://x", "Test", None)]  # noqa: E731
    history = lambda symbol, range_: [(1, 100.0), (2, 101.5)]  # noqa: E731
    return TestClient(create_app(market=market, headlines=headlines, history=history))


def test_health_reports_source_and_counts(client):
    body = client.get("/health").json()
    assert body["data_source"] == "fixture"
    assert body["stocks"] == len(ROWS)
    assert body["stale"] == 1


def test_overview(client):
    body = client.get("/market/overview").json()
    assert body["indices"][0]["symbol"] == "NIFTY50"
    assert body["breadth"]["advancers"] == 5
    assert body["movers"]["gainers"][0]["symbol"] == "TCS"


def test_screener_paginates_and_validates(client):
    page = client.get("/stocks", params={"page_size": 2, "page": 2}).json()
    assert page["total"] == 7 and len(page["results"]) == 2  # GONE (stale) and NOPRICE excluded
    assert client.get("/stocks", params={"cap": "giant"}).status_code == 422
    asc = client.get("/stocks", params={"sort": "score", "order": "asc", "sector": "it"}).json()["results"]
    assert asc[0]["symbol"] == "TINYCO"


def test_stale_stocks_are_hidden_from_rankings_but_still_open(client):
    overview = client.get("/market/overview").json()
    assert "GONE" not in [s["symbol"] for s in overview["movers"]["losers"]]
    detail = client.get("/stocks/GONE").json()
    assert detail["stock"]["stale"] is True


def test_stock_detail_and_404(client):
    body = client.get("/stocks/tcs").json()
    assert body["stock"]["symbol"] == "TCS" and body["stock"]["sector_label"] == "IT Services"
    assert body["score"]["verdict"] == "Strong" and body["score"]["coverage"] == 6
    assert body["peers"][0]["symbol"] == "TCS"
    assert client.get("/stocks/NOPE").status_code == 404


def test_search_and_history(client):
    assert client.get("/stocks/search", params={"q": "infy"}).json()[0]["symbol"] == "INFY"
    hist = client.get("/stocks/NIFTY50/history", params={"range": "1d"}).json()
    assert hist["points"] == [{"t": 1, "close": 100.0}, {"t": 2, "close": 101.5}]
    assert client.get("/stocks/INFY/history", params={"range": "10y"}).status_code == 422


def test_news_and_geopolitics(client):
    events = client.get("/news", params={"topic": "oil"}).json()
    assert events[0]["topics"] == ["Conflict", "Oil"]
    geo_body = client.get("/geopolitics").json()
    assert geo_body["exposure"][0]["sensitivity"] == 100


def test_prospectus_scan(client):
    ok = client.post("/prospectus/scan", files={"file": ("d.pdf", make_pdf(SAMPLE_DRHP), "application/pdf")})
    assert ok.status_code == 200 and ok.json()["findings"][0]["severity"] == "high"
    bad = client.post("/prospectus/scan", files={"file": ("d.pdf", b"nope", "application/pdf")})
    assert bad.status_code == 422 and "isn't a PDF" in bad.json()["detail"]
    assert len(client.get("/prospectus/rules").json()) == 12
