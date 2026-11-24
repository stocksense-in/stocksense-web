import pytest

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


def test_no_score_without_balance_sheet_data():
    # Profitable-looking numbers but no ROE or D/E (typical of negative equity).
    distressed = {"pe": 3.7, "roe": None, "de": None, "margin": 82, "promoter": 75, "cagr": 2}
    assert score_stock(distressed, "telecom").composite is None


def test_implausibly_low_pe_scores_neutral():
    assert metric_score("pe", 3.0, "it") == 50
    assert metric_score("pe", 6.0, "it") == 100


def test_too_few_metrics_gives_no_score():
    assert score_stock({"pe": 20, "roe": 15, "de": None}, "it").composite is None


def test_banks_tolerate_leverage():
    assert metric_score("de", 8, "bank") > 50
    assert metric_score("de", 8, "it") == 0


def test_loss_making_pe_scores_zero_and_newage_is_flat():
    assert metric_score("pe", -12, "it") == 0
    assert metric_score("pe", 320, "newage") == 40


def test_scores_are_clamped():
    assert metric_score("pe", 5, "it") == 100
    assert metric_score("roe", 90, "it") == 100
    assert metric_score("margin", -5, "it") == 0


def test_sector_codes_use_industry_first():
    assert sector_code("Financial Services", "Banks - Regional") == "bank"
    assert sector_code("Financial Services", "Credit Services") == "nbfc"
    assert sector_code("Financial Services", "Insurance - Life") == "finance"
    assert sector_code("Technology", "Information Technology Services") == "it"
    assert sector_code(None, None) == "general"


# ── teaching layer ────────────────────────────────────────────────────────────
from stocksense import scoring as _scoring  # noqa: E402 — kept next to the tests that use it


def test_score_ranges_are_the_curves_read_backwards():
    for sector in ("it", "bank", "general"):
        for metric in _scoring.WEIGHTS:
            bands = _scoring.healthy_range(metric, sector)
            if bands is None:
                continue
            assert _scoring.metric_score(metric, bands["strong_from"], sector) == pytest.approx(70, abs=0.5)
            assert _scoring.metric_score(metric, bands["fair_from"], sector) == pytest.approx(40, abs=0.5)


def test_range_text_reads_naturally():
    assert _scoring.healthy_range("roe", "it")["text"] == "Strong: 35% or more · Fair: 20–35% · Weak: below 20%"
    assert _scoring.healthy_range("pe", "it")["text"] == "Strong: 21 or less · Fair: 21–33 · Weak: above 33"
    assert _scoring.healthy_range("pe", "newage") is None


def test_explain_special_cases():
    assert _scoring.explain("roe", 31, "it")["verdict"] == "fair"
    assert _scoring.explain("pe", -5, "it")["verdict"] == "weak"
    assert _scoring.explain("pe", 2.5, "it")["verdict"] == "unclear"
    assert _scoring.explain("pe", 80, "newage")["verdict"] == "not judged"
    assert "lend borrowed money" in _scoring.explain("de", 8, "bank")["note"]
