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


def test_suspect_quarters_count_as_missing():
    df = quarters().assign(suspect=False)
    df.loc[df["period_end"] == date(2024, 12, 31), "suspect"] = True
    assert fm.latest(df).iloc[0]["as_of"] == date(2024, 9, 30)


def test_bank_margin_uses_net_revenue():
    df = quarters(margin=0.05).assign(net_revenue=lambda d: d["revenue"] / 2)
    assert fm.latest(df).iloc[0]["net_margin"] == pytest.approx(10.0)


def test_roe_on_average_equity_and_debt_to_equity():
    df = quarters(margin=0.10)  # trailing profit 40
    df["equity"], df["borrowings"] = None, None
    df.loc[df["period_end"] == date(2023, 12, 31), ["equity", "borrowings"]] = [150.0, 30.0]
    df.loc[df["period_end"] == date(2024, 12, 31), ["equity", "borrowings"]] = [250.0, 50.0]
    m = fm.latest(df).iloc[0]
    assert m["roe"] == pytest.approx(20.0)          # 40 / average(150, 250)
    assert m["debt_equity"] == pytest.approx(0.2)   # 50 / 250, latest sheet


def test_no_balance_sheet_ratios_from_a_stale_sheet_or_for_banks():
    df = quarters()
    df["equity"], df["borrowings"], df["bank"] = None, None, False
    df.loc[df["period_end"] == date(2023, 12, 31), ["equity", "borrowings"]] = [100.0, 10.0]
    m = fm.latest(df).iloc[0]
    assert pd.isna(m["roe"]) and pd.isna(m["debt_equity"])  # a year older than the P&L
    df.loc[df["period_end"] == date(2024, 9, 30), ["equity", "borrowings"]] = [100.0, 10.0]
    df["bank"] = True
    m = fm.latest(df).iloc[0]
    assert m["roe"] == pytest.approx(40.0) and pd.isna(m["debt_equity"])


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


def test_rescore_filings_saves_nothing_without_apply(monkeypatch):
    from stocksense import lake as lake_module
    from stocksense.jobs import rescore

    rows = [{"symbol": f"S{i}", "sector": "it", "pe_ratio": 20, "roe": 15, "debt_equity": 0.1, "net_margin": 10,
             "promoter_holding": 50, "revenue_cagr_3yr": 8} for i in range(12)]
    monkeypatch.setattr(rescore, "load_rows", lambda: rows)

    class FakeLake:
        def datasets(self):
            return ["financial_results"]

        def query(self, sql):
            return quarters(symbol="S0")

    monkeypatch.setattr(lake_module.Lake, "from_settings", classmethod(lambda cls: FakeLake()))

    class Store:
        saved = None

        def upsert_stocks(self, changed):
            Store.saved = changed

    rescore.run(Store(), "filings")
    assert Store.saved is None


def test_promoter_from_the_latest_shareholding_pattern():
    metrics = pd.DataFrame([{"symbol": "TCS", "as_of": date(2026, 9, 30), "net_margin": 18.2}])
    sh = pd.DataFrame([{"symbol": "TCS", "quarter_end": date(2026, 6, 30), "promoter_pct": 71.78},
                       {"symbol": "TCS", "quarter_end": date(2026, 9, 30), "promoter_pct": 71.77},
                       {"symbol": "ITC", "quarter_end": date(2026, 9, 30), "promoter_pct": 0.0}])
    out = fm.with_promoter(metrics, sh).set_index("symbol")
    assert out.at["TCS", "promoter_holding"] == 71.77 and out.at["TCS", "net_margin"] == 18.2
    assert out.at["ITC", "promoter_holding"] == 0.0 and out.at["ITC", "as_of"] == date(2026, 9, 30)
    rows, replaced = fm.overlay([{"symbol": "ITC", "promoter_holding": 29.49, "net_margin": 25.0}], out.reset_index())
    assert rows[0]["promoter_holding"] == 0.0 and rows[0]["net_margin"] == 25.0  # no results: Yahoo's margin kept


def test_growth_on_reported_revenue_margin_on_net():
    df = quarters(growth=0.10, margin=0.10).assign(kind="company")
    df["net_revenue"] = df["revenue"]
    recent = df["period_end"] >= date(2024, 1, 1)
    df.loc[recent, "net_revenue"] = df.loc[recent, "revenue"] * 0.8  # excise netted only lately
    m = fm.latest(df).iloc[0]
    assert m["revenue_cagr_3yr"] == pytest.approx(10.0, abs=0.01)  # like with like, not net vs gross
    assert m["net_margin"] == pytest.approx(12.5)  # profit / net revenue


def test_switch_only_selected_metrics():
    metrics = pd.DataFrame([{"symbol": "ITC", "as_of": date(2026, 9, 30), "net_margin": 24.4, "promoter_holding": 0.0}])
    rows = [{"symbol": "ITC", "net_margin": 25.0, "promoter_holding": 29.49}]
    out, n = fm.overlay(rows, metrics, only=["promoter"])
    assert n == 1 and out[0] == {"symbol": "ITC", "net_margin": 25.0, "promoter_holding": 0.0}


def test_apply_skips_stale_companies_instead_of_refusing(monkeypatch):
    from stocksense import lake as lake_module
    from stocksense.jobs import rescore

    rows = [{"symbol": f"S{i}", "sector": "it", "pe_ratio": 20, "roe": 15, "debt_equity": 0.1, "net_margin": 10,
             "promoter_holding": 50, "revenue_cagr_3yr": 8} for i in range(12)]
    monkeypatch.setattr(rescore, "load_rows", lambda: rows)
    fresh_and_stale = pd.DataFrame([{"symbol": "S0", "quarter_end": date.today(), "promoter_pct": 75.0},
                                    {"symbol": "S1", "quarter_end": date(2023, 3, 31), "promoter_pct": 10.0}])

    class FakeLake:
        def datasets(self):
            return ["shareholding"]

        def query(self, sql):
            return fresh_and_stale

    monkeypatch.setattr(lake_module.Lake, "from_settings", classmethod(lambda cls: FakeLake()))

    class Store:
        saved = None

        def upsert_stocks(self, changed):
            Store.saved = {r["symbol"]: r for r in changed}

    rescore.run(Store(), "filings", apply=True, only=["promoter"])
    assert Store.saved["S0"]["promoter_holding"] == 75.0  # switched
    assert "S1" not in Store.saved or Store.saved["S1"]["promoter_holding"] == 50  # stale: kept
