from stocksense.scoring import WEIGHTS, metric_score, score_stock
from stocksense.sectors import sector_code

INFOSYS = {"pe": 24.2, "roe": 31, "de": 0.08, "margin": 17.2, "promoter": 14.7, "cagr": 12.8}


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1) < 1e-9


def test_full_score_matches_hand_calculation():
    result = score_stock(INFOSYS, "it")
    parts = {
        "pe": 100 - (24.2 - 8) / 42 * 100,
        "roe": 31 / 50 * 100,
        "de": 100 - 0.08 / 3.5 * 100,
        "margin": 17.2 / 38 * 100,
        "promoter": 14.7 / 80 * 100,
        "cagr": 12.8 / 55 * 100,
    }
    expected = sum(parts[k] * WEIGHTS[k] for k in WEIGHTS)
    assert result.composite == round(expected)
    assert result.coverage == 6


def test_missing_metrics_renormalise_weights():
    partial = {**INFOSYS, "promoter": None, "cagr": None}
    result = score_stock(partial, "it")
    assert result.coverage == 4
    known = {k: metric_score(k, v, "it") for k, v in partial.items() if v is not None}
    expected = sum(known[k] * WEIGHTS[k] for k in known) / sum(WEIGHTS[k] for k in known)
    assert result.composite == round(expected)


def test_too_few_metrics_gives_no_score():
    assert score_stock({"pe": 20, "roe": 15, "de": None}, "it").composite is None


def test_banks_tolerate_leverage():
    assert metric_score("de", 8, "bank") > 50
    assert metric_score("de", 8, "it") == 0


def test_loss_making_pe_scores_zero_and_newage_is_flat():
    assert metric_score("pe", -12, "it") == 0
    assert metric_score("pe", 320, "newage") == 40


def test_scores_are_clamped():
    assert metric_score("pe", 2, "it") == 100
    assert metric_score("roe", 90, "it") == 100
    assert metric_score("margin", -5, "it") == 0


def test_sector_codes_use_industry_first():
    assert sector_code("Financial Services", "Banks - Regional") == "bank"
    assert sector_code("Financial Services", "Credit Services") == "nbfc"
    assert sector_code("Financial Services", "Insurance - Life") == "finance"
    assert sector_code("Technology", "Information Technology Services") == "it"
    assert sector_code(None, None) == "general"
