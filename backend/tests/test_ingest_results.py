from datetime import date

import pytest

from stocksense.jobs import ingest_results
from stocksense.lake import Lake
from stocksense.sources import nse_results


def filing(end, consolidated=True, seq="1", cumulative="Non-cumulative"):
    return {"symbol": "TCS", "fromDate": "01-Oct-2024", "toDate": end, "seqNumber": seq, "params": "p",
            "consolidated": "Consolidated" if consolidated else "Non-Consolidated", "cumulative": cumulative,
            "audited": "Audited", "indAs": "Ind-AS New", "bank": "N", "format": "New"}


def test_one_per_quarter_prefers_consolidated():
    picked = ingest_results.one_per_quarter([
        filing("31-Dec-2024", consolidated=False, seq="a"), filing("31-Dec-2024", seq="b"),
        filing("30-Sep-2024", consolidated=False, seq="c"),
        filing("31-Mar-2024", seq="d", cumulative="Cumulative"),
    ])
    assert sorted(f["seqNumber"] for f in picked) == ["b", "c"]


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
    assert ingest_results.fetch(lake, ["TCS"], pause=0) == 2
    assert ingest_results.fetch(lake, ["TCS"], pause=0) == 0 and fake.detail_calls == 2  # nothing refetched
    df = ingest_results.build(lake)
    assert df["period_end"].tolist() == [date(2024, 9, 30), date(2024, 12, 31)]
    assert lake.query("select sum(revenue) from financial_results").iloc[0, 0] == pytest.approx(2 * 63973.0)
