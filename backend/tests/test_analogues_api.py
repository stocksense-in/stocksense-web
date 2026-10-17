import json
import os

import pytest
from fastapi.testclient import TestClient

from stocksense.api import create_app
from stocksense.api.app import load_analogues


def cell(sector, horizon, mean, notable=False):
    return {"sector": sector, "horizon_days": horizon, "n": 14, "mean_excess_pct": mean, "median_excess_pct": mean,
            "hit_rate": 0.3, "ci_low_pct": mean - 1, "ci_high_pct": mean + 1, "baseline_pct": 0.01, "notable": notable}


DOC = {
    "generated_at": "2026-10-16T22:00:00+00:00", "data_from": "2012-01-02", "data_through": "2026-10-15",
    "benchmark": "NIFTY 50", "horizons_days": [1, 3, 10], "method": "…", "notable_share": {"1": 0.12},
    "sector_sources": {"Aviation": "equal-weight basket: INDIGO, SPICEJET"},
    "events": [{
        "code": "crude_spike", "label": "Crude oil spike", "rule": "Brent up 5% or more in a day",
        "occurrences": 14, "first": "2012-06-29", "last": "2026-06-13",
        "recent": [{"date": "2026-06-13", "evidence": []}],
        "sectors": [cell("Aviation", 1, -1.8, True), cell("IT Services", 1, 0.1), cell("Aviation", 3, -2.4, True)],
    }],
}


@pytest.fixture
def client(market):
    return TestClient(create_app(market=market, headlines=lambda: [], analogues=lambda: DOC))


def test_list_event_types(client):
    body = client.get("/geopolitics/analogues").json()
    assert body["data_through"] == "2026-10-15" and body["notable_share"] == {"1": 0.12}
    assert body["events"] == [{"code": "crude_spike", "label": "Crude oil spike", "rule": "Brent up 5% or more in a day",
                               "occurrences": 14, "first": "2012-06-29", "last": "2026-06-13"}]


def test_event_detail_filters(client):
    body = client.get("/geopolitics/analogues/crude_spike").json()
    assert [(c["sector"], c["horizon_days"]) for c in body["sectors"]] == [
        ("Aviation", 1), ("IT Services", 1), ("Aviation", 3)]  # by horizon, then most negative first
    one_day = client.get("/geopolitics/analogues/crude_spike", params={"horizon": 1, "notable": True}).json()
    assert [c["sector"] for c in one_day["sectors"]] == ["Aviation"]
    assert client.get("/geopolitics/analogues/alien_invasion").status_code == 404


def test_not_published_yet(market):
    client = TestClient(create_app(market=market, headlines=lambda: [], analogues=lambda: None))
    assert client.get("/geopolitics/analogues").status_code == 503


def test_loader_rereads_when_the_file_changes(tmp_path):
    path = tmp_path / "geo_analogues.json"
    assert load_analogues(path) is None
    path.write_text(json.dumps(DOC))
    assert load_analogues(path)["benchmark"] == "NIFTY 50"
    path.write_text(json.dumps({**DOC, "benchmark": "changed"}))
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 5))
    assert load_analogues(path)["benchmark"] == "changed"
