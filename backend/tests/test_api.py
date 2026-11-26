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


def test_coverage_note_names_missing_metrics():
    from stocksense.api.app import _coverage_note

    assert _coverage_note(60, []) is None
    assert _coverage_note(60, ["Promoter holding"]) == ("This score uses 5 of 6 metrics — promoter holding isn't "
                                                         "available, so the others carry its weight. Treat it as a "
                                                         "rougher guide.")
    assert "missing: P/E ratio, debt to equity" in _coverage_note(50, ["P/E ratio", "Debt to equity"])
    assert _coverage_note(None, ["P/E ratio"]).startswith("Not enough data")


def test_company_news_filters_to_the_company(market):
    from datetime import datetime, timezone
    asked = []

    def company_headlines(query):
        asked.append(query)
        when = datetime(2026, 11, 20, tzinfo=timezone.utc)
        return [Headline("TCS wins a $1 bn deal - Mint", "https://a", "Google News", when),
                Headline("Markets close higher - Mint", "https://b", "Google News", when)]

    c = TestClient(create_app(market=market, headlines=lambda: [], company_headlines=company_headlines))
    rows = c.get("/stocks/TCS/news").json()
    assert asked == ["TCS"]  # fixture name "TCS Limited" → everyday name "TCS"
    assert rows == [{"title": "TCS wins a $1 bn deal", "link": "https://a", "source": "Mint", "published": "2026-11-20T00:00:00+00:00"}]
    assert c.get("/stocks/TCS/news").json() == rows and asked == ["TCS"]  # cached
    assert c.get("/stocks/NOPE/news").status_code == 404


def test_company_news_survives_a_feed_failure(market):
    def broken(query):
        raise RuntimeError("feed down")

    c = TestClient(create_app(market=market, headlines=lambda: [], company_headlines=broken))
    assert c.get("/stocks/TCS/news").json() == []


def test_alerts_filter_by_watchlist_kind_and_days(market):
    doc = {"generated_at": "2026-11-27T00:00:00+00:00", "days": ["2026-11-26", "2026-11-25"], "alerts": [
        {"date": "2026-11-25", "symbol": "TCS", "kind": "price_move", "value": 6.1, "text": "TCS rose 6.1%"},
        {"date": "2026-11-26", "symbol": "TCS", "kind": "results_filed", "value": None, "text": "TCS filed results"},
        {"date": "2026-11-26", "symbol": "INFY", "kind": "price_move", "value": -5.2, "text": "Infosys fell 5.2%"},
    ]}
    c = TestClient(create_app(market=market, headlines=lambda: [], alerts=lambda: doc))
    body = c.get("/alerts", params={"symbols": "tcs"}).json()
    assert [a["kind"] for a in body["alerts"]] == ["results_filed", "price_move"]  # newest day first
    assert body["days"] == ["2026-11-26", "2026-11-25"]
    assert [a["symbol"] for a in c.get("/alerts", params={"kind": "price_move"}).json()["alerts"]] == ["INFY", "TCS"]
    assert [a["symbol"] for a in c.get("/alerts", params={"days": 1}).json()["alerts"]] == ["TCS", "INFY"]
    empty = TestClient(create_app(market=market, headlines=lambda: [], alerts=lambda: None)).get("/alerts").json()
    assert empty == {"generated_at": None, "days": [], "alerts": []}


def test_screen_by_symbols_for_a_watchlist(client):
    body = client.get("/stocks", params={"symbols": "tcs, infy,NOPE"}).json()
    assert sorted(r["symbol"] for r in body["results"]) == ["INFY", "TCS"]
    too_many = ",".join(f"S{i}" for i in range(101))
    assert client.get("/stocks", params={"symbols": too_many}).status_code == 422


def test_no_promoter_group_is_not_applicable_not_missing():
    from stocksense.api.app import NOT_APPLICABLE_NOTE, _coverage_note, _no_promoter_group
    assert _no_promoter_group({"quarters": [{"promoter_pct": 45.0}, {"promoter_pct": 0.0}]})
    assert not _no_promoter_group({"quarters": [{"promoter_pct": 0.0}, {"promoter_pct": 12.0}]})
    assert not _no_promoter_group(None) and not _no_promoter_group({"quarters": []})
    assert _coverage_note(66, [], ["Promoter holding"]) == NOT_APPLICABLE_NOTE
    both = _coverage_note(60, ["Debt to equity"], ["Promoter holding"])
    assert both.startswith("This score uses 4 of 5 metrics — debt to equity isn't available") and both.endswith(NOT_APPLICABLE_NOTE)


def test_stock_detail_marks_promoter_not_applicable(market):
    holders = {"source": "test", "companies": {"TCS": {"quarters": [{"quarter_end": "2026-09-30", "promoter_pct": 0.0}],
                                                       "pledge": None}}}
    c = TestClient(create_app(market=market, headlines=lambda: [], holders=lambda: holders))
    score = c.get("/stocks/TCS").json()["score"]
    (promoter,) = [p for p in score["breakdown"] if p["metric"] == "promoter"]
    # The fixture still carries a promoter figure (as Yahoo does), so it is scored, with the caveat shown.
    assert promoter["note"].startswith("Its filings show no promoter group")
    assert score["not_applicable"] == [] and "Promoter holding" not in score["missing"]


def test_after_the_switch_promoter_is_not_applicable(market):
    from stocksense.api.app import NOT_APPLICABLE_NOTE
    from stocksense.market import MarketData
    from tests.conftest import ROWS
    rows = [dict(r, promoter_holding=None) if r["symbol"] == "TCS" else r for r in ROWS]
    holders = {"source": "test", "companies": {"TCS": {"quarters": [{"quarter_end": "2026-09-30", "promoter_pct": 0.0}],
                                                       "pledge": None}}}
    c = TestClient(create_app(market=MarketData(rows=rows), headlines=lambda: [], holders=lambda: holders))
    score = c.get("/stocks/TCS").json()["score"]
    assert score["not_applicable"] == ["Promoter holding"] and score["missing"] == []
    assert score["coverage_note"] == NOT_APPLICABLE_NOTE
