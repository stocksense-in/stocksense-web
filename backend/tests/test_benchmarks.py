from types import SimpleNamespace

import pytest

from stocksense import benchmarks as bm


def stock(sector="it", pe=20.0, roe=15.0, de=0.3, margin=12.0, promoter=50.0, cagr=10.0):
    return SimpleNamespace(sector=sector, pe=pe, roe=roe, de=de, margin=margin, promoter=promoter, cagr=cagr)


# IT: P/E 10, 20, …, 120 (12 peers); FMCG: only 3 companies → falls back to the market.
UNIVERSE = [stock("it", pe=10.0 * i, roe=float(i)) for i in range(1, 13)] + \
           [stock("fmcg", pe=60.0), stock("fmcg", pe=70.0), stock("fmcg", pe=-5.0)]


@pytest.fixture
def benches():
    return bm.build(UNIVERSE)


def test_quartiles_and_counts(benches):
    it_pe = benches[("it", "pe")]
    assert it_pe.n == 12 and it_pe.quantile(0.5) == pytest.approx(65.0)
    assert benches[("market", "pe")].n == 14  # the loss-maker (P/E -5) isn't ranked


def test_lower_pe_beats_more_peers(benches):
    cheap = bm.peer_context("pe", 15.0, "it", benches)
    pricey = bm.peer_context("pe", 115.0, "it", benches)
    assert cheap["better_than_pct"] > 85 and cheap["standing"] == "top quarter"
    assert pricey["better_than_pct"] < 15 and pricey["standing"] == "bottom quarter"
    assert cheap["group"] == "IT Services companies" and cheap["peers"] == 12


def test_higher_roe_beats_more_peers(benches):
    ctx = bm.peer_context("roe", 11.5, "it", benches)
    assert ctx["better_than_pct"] > 85
    assert ctx["typical_range"] == "4–9%"  # one unit sign, like the score's ranges


def test_small_sector_falls_back_to_market(benches):
    ctx = bm.peer_context("pe", 65.0, "fmcg", benches)
    assert ctx["group"] == "all NSE companies" and ctx["peers"] == 14


def test_loss_making_pe_shows_range_but_isnt_ranked(benches):
    ctx = bm.peer_context("pe", -5.0, "fmcg", benches)
    assert ctx["better_than_pct"] is None and "Typical for" in ctx["text"]


def test_no_context_without_a_value(benches):
    assert bm.peer_context("pe", None, "it", benches) is None


def test_stage():
    assert bm.stage(stock(pe=-3)) == "loss-making"
    assert bm.stage(stock(margin=-2)) == "loss-making"
    assert bm.stage(stock(cagr=35)) == "high growth"
    assert bm.stage(stock(cagr=8)) == "steady"
    assert bm.stage(stock(cagr=None)) == "unknown"


def test_growth_adjusted_pe():
    assert bm.growth_adjusted_pe(stock(pe=30, cagr=30))["reading"] == "cheap for its growth"
    assert bm.growth_adjusted_pe(stock(pe=45, cagr=30))["reading"] == "reasonable for its growth"
    assert bm.growth_adjusted_pe(stock(pe=60, cagr=10))["reading"] == "expensive for its growth"
    assert bm.growth_adjusted_pe(stock(pe=-10, cagr=30)) is None
    assert bm.growth_adjusted_pe(stock(sector="newage", pe=200, cagr=40)) is None


def test_stage_note_for_pe():
    assert "growing fast" in bm.stage_note("pe", stock(pe=45, cagr=30))
    assert "making a loss" in bm.stage_note("pe", stock(pe=-3))
    assert bm.stage_note("roe", stock()) is None


def test_guardrails():
    assert "heavy" in bm.guardrails("de", stock(de=3.0))
    assert bm.guardrails("de", stock(sector="bank", de=8.0)) is None  # lenders run on debt
    assert "losing money" in bm.guardrails("margin", stock(margin=-4))
    assert bm.guardrails("roe", stock(roe=12)) is None
