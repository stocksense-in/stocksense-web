from stocksense import analytics
from stocksense.analytics import ScreenFilters


def test_live_price_overrides_older_fundamentals_price(market):
    tcs = market.stock("tcs")
    assert tcs.price == 2114.4 and tcs.change_pct == 2.0


def test_screen_filters_and_default_sort(market):
    rows = analytics.screen(market.stocks(), ScreenFilters(sector="it", cap="large"))
    assert [s.symbol for s in rows] == ["TCS", "INFY", "WIPRO"]  # score, highest first


def test_screen_excludes_unpriced_and_sorts_missing_last(market):
    rows = analytics.screen(market.stocks(), ScreenFilters(sort="de"))
    assert "NOPRICE" not in [s.symbol for s in rows]
    assert [s.de for s in rows][-3:] == [None, None, None]  # banks have no D/E


def test_screen_ascending_pe_by_default(market):
    rows = analytics.screen(market.stocks(), ScreenFilters(sector="it", max_pe=16, sort="pe"))
    assert [s.symbol for s in rows] == ["INFY", "TCS"]  # P/E 14, then 15


def test_movers_ignore_micro_caps(market):
    moves = analytics.movers(market.stocks(), 3)
    assert "TINYCO" not in [s.symbol for s in moves["gainers"]]
    assert moves["gainers"][0].symbol == "TCS"
    assert [s.symbol for s in moves["losers"]] == ["HDFCBANK", "INFY"]


def test_breadth_counts(market):
    assert analytics.breadth(market.stocks()) == {"advancers": 5, "decliners": 2, "unchanged": 1}


def test_sector_moves_are_cap_weighted(market):
    banks = next(s for s in analytics.sector_moves(market.stocks()) if s["sector"] == "bank")
    expected = (-2.3 * 1_080_000 + 0.8 * 900_000 + 0.5 * 950_000) / (1_080_000 + 900_000 + 950_000)
    assert banks["change_pct"] == round(expected, 2)
    assert banks["label"] == "Banking"


def test_search_ranks_exact_symbol_first(market):
    assert [s.symbol for s in analytics.search(market.stocks(), "tcs")][0] == "TCS"
    assert analytics.search(market.stocks(), "  ") == []


def test_peers_include_the_stock_itself(market):
    tiny = market.stock("TINYCO")
    peers = analytics.peers(market.stocks(), tiny, count=2)
    assert [s.symbol for s in peers] == ["TCS", "TINYCO"]


def test_score_breakdown_points_sum_to_composite(market):
    from stocksense.scoring import score_stock

    s = market.stock("TCS")
    parts = analytics.score_breakdown(s)
    composite = score_stock({"pe": s.pe, "roe": s.roe, "de": s.de, "margin": s.margin, "promoter": s.promoter, "cagr": s.cagr}, s.sector).composite
    # Each part is rounded to 0.1, so the total can drift by a few tenths.
    assert abs(sum(p["points"] for p in parts) - composite) <= 0.6
    assert abs(sum(p["weight"] for p in parts) - 1) < 1e-3
