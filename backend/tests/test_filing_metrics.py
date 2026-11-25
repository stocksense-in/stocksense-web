from datetime import date

import pandas as pd
import pytest

from stocksense import filing_metrics as fm

QUARTER_ENDS = [date(y, m, d) for y in range(2020, 2025) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))]


def quarters(symbol="ACME", revenue=100.0, growth=0.0, margin=0.1, ends=QUARTER_ENDS):
    rows = []
    for i, end in enumerate(ends):
        r = revenue * (1 + growth) ** (i / 4)
        rows.append({"symbol": symbol, "period_end": end, "revenue": r, "net_profit": r * margin})
    return pd.DataFrame(rows)


def test_margin_and_cagr_from_trailing_twelve_months():
    m = fm.latest(quarters(growth=0.10, margin=0.12)).set_index("symbol").loc["ACME"]
    assert m["as_of"] == date(2024, 12, 31)
    assert m["net_margin"] == pytest.approx(12.0)
    assert m["revenue_cagr_3yr"] == pytest.approx(10.0, abs=0.01)


def test_gap_in_filings_breaks_the_trailing_window():
    df = quarters()
    df = df[df["period_end"] != date(2024, 9, 30)]  # a missing quarter
    m = fm.latest(df).set_index("symbol").loc["ACME"]
    assert m["as_of"] == date(2024, 6, 30)  # Dec 2024's four would span a gap


def test_never_mixes_standalone_and_consolidated_quarters():
    cons = quarters(margin=0.20)
    cons = cons[cons["period_end"] != date(2024, 6, 30)].assign(consolidated=True)  # one quarter only standalone
    alone = quarters(margin=0.10).assign(consolidated=False)
    m = fm.latest(pd.concat([cons, alone])).iloc[0]
    assert m["as_of"] == date(2024, 12, 31) and not m["consolidated"]
    assert m["net_margin"] == pytest.approx(10.0)  # all-standalone window, not 3 + 1


def test_bank_margin_uses_net_revenue():
    df = quarters(margin=0.05).assign(net_revenue=lambda d: d["revenue"] / 2)
    assert fm.latest(df).iloc[0]["net_margin"] == pytest.approx(10.0)


def test_no_cagr_without_three_years_of_history():
    m = fm.latest(quarters(ends=QUARTER_ENDS[-8:])).iloc[0]
    assert m["net_margin"] == pytest.approx(10.0)
    assert pd.isna(m["revenue_cagr_3yr"])


def test_overlay_replaces_only_covered_companies_and_values():
    metrics = pd.DataFrame([{"symbol": "ACME", "as_of": date(2024, 12, 31), "net_margin": 12.0, "revenue_cagr_3yr": None}])
    rows = [{"symbol": "ACME", "net_margin": 9.0, "revenue_cagr_3yr": 7.0}, {"symbol": "OTHER", "net_margin": 5.0}]
    out, replaced = fm.overlay(rows, metrics)
    assert replaced == 1 and out[0] == {"symbol": "ACME", "net_margin": 12.0, "revenue_cagr_3yr": 7.0}
    assert out[1] is rows[1] and rows[0]["net_margin"] == 9.0  # inputs untouched


def test_stale_flags_old_figures():
    metrics = pd.DataFrame([{"symbol": "OLD", "as_of": date(2024, 12, 31)}, {"symbol": "NEW", "as_of": date(2026, 9, 30)}])
    assert fm.stale(metrics, today=date(2026, 11, 25)) == ["OLD"]


def test_rescore_compare_reports_both_scores():
    from stocksense.jobs import rescore

    rows = [{"symbol": f"S{i}", "sector": "it", "pe_ratio": 20 + i, "roe": 15 + i, "debt_equity": 0.1,
             "net_margin": 10 + i, "promoter_holding": 50, "revenue_cagr_3yr": 8} for i in range(12)]
    metrics = pd.DataFrame([{"symbol": "S0", "as_of": date(2024, 12, 31), "net_margin": 30.0, "revenue_cagr_3yr": 25.0}])
    report = rescore.compare(rows, metrics)
    assert report["symbol"].tolist() == ["S0"]
    r = report.iloc[0]
    assert (r["margin_yahoo"], r["margin_filings"]) == (10, 30.0)
    assert r["score_filings"] > r["score_yahoo"] and r["score_move"] > 0
