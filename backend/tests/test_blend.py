from types import SimpleNamespace

import pytest

from stocksense import benchmarks as bm
from stocksense import blend
from stocksense.scoring import metric_score


def stock(sector="it", pe=20.0, roe=15.0, de=0.3, margin=12.0, promoter=50.0, cagr=10.0):
    return SimpleNamespace(sector=sector, pe=pe, roe=roe, de=de, margin=margin, promoter=promoter, cagr=cagr)


# 12 IT companies with ROE 1..12% and P/E 10..120.
PEERS = [stock(pe=10.0 * i, roe=float(i)) for i in range(1, 13)]


@pytest.fixture
def benches():
    return bm.build(PEERS)


def test_sub_score_is_seventy_thirty(benches):
    s = stock(roe=12.0)  # beats nearly every peer on ROE, but 12% is weak on the fixed curve
    part = blend.metric_parts(s, benches)["roe"]
    assert part["absolute"] == pytest.approx(metric_score("roe", 12.0, "it"), abs=0.1)
    assert part["score"] == pytest.approx(0.7 * part["peer"] + 0.3 * part["absolute"], abs=0.1)
    assert part["peer"] > 90 and part["score"] > part["absolute"]


def test_special_pe_cases(benches):
    assert blend.metric_parts(stock(pe=-8), benches)["pe"] == {"peer": 0.0, "absolute": 0.0, "score": 0.0}
    assert blend.metric_parts(stock(pe=2.5), benches)["pe"]["score"] == 50.0  # one-off profits: neutral
    newage = blend.metric_parts(stock(sector="newage", pe=300), benches)["pe"]
    assert newage["peer"] is None and newage["score"] == newage["absolute"] == 40.0


def test_coverage_rules_still_apply(benches):
    assert blend.blended_score(stock(roe=None, de=None), benches).composite is None  # no balance-sheet metric
    thin = stock(pe=None, margin=None, promoter=None)  # 3 metrics
    assert blend.blended_score(thin, benches).composite is None


def test_rescore_rows_uses_the_same_rows_as_peers():
    rows = [{"symbol": f"S{i}", "sector": "it", "pe_ratio": 10.0 * i, "roe": float(i), "debt_equity": 0.3,
             "net_margin": 12.0, "promoter_holding": 50.0, "revenue_cagr_3yr": 10.0} for i in range(1, 13)]
    results = blend.rescore_rows(rows)
    assert len(results) == 12 and all(r.composite is not None for r in results)
    # Cheapest P/E and highest ROE in the group → the first and last stocks rank at the ends on those metrics.
    assert results[0].parts["pe"] > results[-1].parts["pe"]
    assert results[-1].parts["roe"] > results[0].parts["roe"]
