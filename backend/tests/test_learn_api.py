import pytest
from fastapi.testclient import TestClient

from stocksense.api import create_app
from stocksense import benchmarks as bm
from stocksense import blend

VALUATION = {
    "market_index": "NIFTY_50",
    "sector_index": {"it": "NIFTY_IT"},
    "indices": {
        "NIFTY_50": {"pe": 20.6, "median_pe": 22.1, "since": "2021-04-01", "higher_than_pct_of_days": 3,
                     "reading": "cheap by its own history"},
        "NIFTY_IT": {"pe": 19.4, "median_pe": 27.4, "since": "2021-04-01", "higher_than_pct_of_days": 6,
                     "reading": "cheap by its own history"},
    },
}


@pytest.fixture
def client(market):
    return TestClient(create_app(market=market, headlines=lambda: [], valuation=lambda: VALUATION))


def test_stock_breakdown_explains_every_metric_in_three_layers(client):
    body = client.get("/stocks/TCS").json()
    score = body["score"]
    assert score["stage"] == "steady" and score["stage_text"]
    parts = {p["metric"]: p for p in score["breakdown"]}
    roe = parts["roe"]
    assert roe["label"] == "Return on equity" and roe["verdict"] in {"strong", "fair", "weak"}
    assert roe["healthy_range"].startswith("Strong:")
    assert roe["peers"]["better_than_pct"] is not None and roe["peers"]["text"].startswith("Better than")
    assert parts["pe"]["market_note"].startswith("The IT Services sector trades at a P/E of 19")
    assert parts["roe"]["market_note"] is None  # valuation context is about P/E


def test_points_sum_to_the_blended_score(client, market):
    # The fixture's stored score is hand-set, so compare with the blend computed over the same universe.
    parts = client.get("/stocks/TCS").json()["score"]["breakdown"]
    composite = blend.blended_score(market.stock("TCS"), bm.build(market.fresh_stocks())).composite
    assert sum(p["points"] for p in parts) == pytest.approx(composite, abs=1)
    for p in parts:  # each sub-score is 70% peers + 30% fixed curve (or the curve alone if not ranked)
        expected = p["absolute_score"] if p["peer_score"] is None else 0.7 * p["peer_score"] + 0.3 * p["absolute_score"]
        assert p["score"] == pytest.approx(expected, abs=0.2)


def test_learn_metrics_for_a_sector(client):
    body = client.get("/learn/metrics", params={"sector": "it"}).json()
    assert body["sector_label"] == "IT Services"
    assert body["market_note"].startswith("The IT Services sector")
    assert set(body["stages"]) == {"loss-making", "high growth", "steady"}
    metrics = {m["metric"]: m for m in body["metrics"]}
    assert set(metrics) == {"pe", "roe", "de", "margin", "promoter", "cagr"}
    assert metrics["pe"]["higher_is_better"] is False and metrics["pe"]["weight"] == 0.2
    peers = metrics["roe"]["peers"]
    assert peers["better_than_pct"] is None and peers["text"].startswith("Typical for")


def test_learn_metrics_without_valuation_or_sector(market):
    client = TestClient(create_app(market=market, headlines=lambda: [], valuation=lambda: None))
    body = client.get("/learn/metrics").json()
    assert body["sector"] == "general" and body["market_note"] is None
    assert len(body["metrics"]) == 6
