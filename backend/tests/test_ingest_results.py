from datetime import date

import pytest

from stocksense.jobs import ingest_results
from stocksense.lake import Lake
from stocksense.sources import nse_integrated, nse_results


def filing(end, consolidated=True, seq="1", cumulative="Non-cumulative"):
    return {"symbol": "TCS", "fromDate": "01-Oct-2024", "toDate": end, "seqNumber": seq, "params": "p",
            "consolidated": "Consolidated" if consolidated else "Non-Consolidated", "cumulative": cumulative,
            "audited": "Audited", "indAs": "Ind-AS New", "bank": "N", "format": "New"}


def test_quarterly_keeps_both_bases_and_the_latest_refiling():
    picked = ingest_results.quarterly([
        filing("31-Dec-2024", consolidated=False, seq="1"), filing("31-Dec-2024", seq="2"),
        filing("31-Dec-2024", seq="5"),  # refiled
        filing("30-Sep-2024", consolidated=False, seq="3"),
        filing("31-Mar-2024", seq="4", cumulative="Cumulative"),
    ])
    assert sorted(f["seqNumber"] for f in picked) == ["1", "3", "5"]


class FakeClient:
    def __init__(self):
        self.detail_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_is_resumable_and_build_makes_one_table(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    fake = FakeClient()
    monkeypatch.setattr(nse_results, "client", lambda: fake)
    monkeypatch.setattr(nse_results, "fetch_filings", lambda c, s: [filing("31-Dec-2024", seq="9"), filing("30-Sep-2024", seq="8")])

    def detail(c, f):
        fake.detail_calls += 1
        return {"resultsData2": {"re_net_sale": "6397300", "re_pl_own_par": "1238000"}}

    monkeypatch.setattr(nse_results, "fetch_detail", detail)
    monkeypatch.setattr(nse_integrated, "fetch_filings", lambda c, s: [])
    assert ingest_results.fetch(lake, ["TCS"], pause=0) == 2
    assert ingest_results.fetch(lake, ["TCS"], pause=0) == 0 and fake.detail_calls == 2  # nothing refetched
    df = ingest_results.build(lake)
    assert df["period_end"].tolist() == [date(2024, 9, 30), date(2024, 12, 31)]
    assert lake.query("select sum(revenue) from financial_results").iloc[0, 0] == pytest.approx(2 * 63973.0)


def test_integrated_filings_join_the_same_table(tmp_path, monkeypatch):
    from tests.test_nse_integrated import FILING, TCS

    lake = Lake(tmp_path)
    monkeypatch.setattr(nse_integrated, "fetch_filings", lambda c, s: [FILING])
    monkeypatch.setattr(nse_integrated, "fetch_xbrl", lambda c, f: TCS)
    assert ingest_results.fetch_integrated(None, lake, "TCS", pause=0) == 1
    assert ingest_results.fetch_integrated(None, lake, "TCS", pause=0) == 0  # already saved
    df = ingest_results.build(lake)
    row = df.iloc[0]
    assert (row["period_end"], row["source"], row["equity"]) == (date(2026, 9, 30), "nse_integrated", pytest.approx(118986.0))
