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


def test_suspect_flags_a_quarter_far_off_its_neighbours():
    import pandas as pd

    ends = pd.date_range("2021-03-31", periods=8, freq="QE").date
    df = pd.DataFrame({"symbol": "LT", "consolidated": True, "period_end": ends,
                       "revenue": [40000, 41000, 42000, 83, 43000, 44000, 45000, 46000]})
    assert ingest_results.suspect(df).tolist() == [False, False, False, True, False, False, False, False]


def test_a_lender_stays_a_lender():
    import pandas as pd

    df = pd.DataFrame({"symbol": "BAJFINANCE", "period_end": [date(2022, 12, 31), date(2023, 3, 31)],
                       "kind": ["finance", "company"], "revenue": [100.0, 110.0], "finance_cost": [30.0, 35.0],
                       "other_income": [1.0, 1.0], "net_revenue": [71.0, 110.0]})
    out = ingest_results.consistent_kind(df)
    assert out["kind"].tolist() == ["finance", "finance"] and out["net_revenue"].tolist() == [71.0, 76.0]


def test_fetch_stops_when_nse_stops_responding(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    monkeypatch.setattr(nse_results, "client", lambda: FakeClient())
    monkeypatch.setattr(nse_results, "fetch_filings",
                        lambda c, s: [filing(f"{d}-Dec-2024", seq=d) for d in ("27", "28", "29", "30")])
    calls = []

    def timeout(c, f):
        calls.append(f["seqNumber"])
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(nse_results, "fetch_detail", timeout)
    monkeypatch.setattr(nse_integrated, "fetch_filings", lambda c, s: calls.append("integrated") or [])
    assert ingest_results.fetch(lake, ["SUNPHARMA", "TITAN"], pause=0) == 0
    assert len(calls) == ingest_results.MAX_FAILURES_IN_A_ROW  # stopped, didn't try the rest or TITAN


def test_a_success_resets_the_count():
    b = ingest_results.Breaker(limit=2)
    b.fail("x", Exception("1"))
    b.ok()
    b.fail("x", Exception("2"))  # 1 in a row again, no stop
    with pytest.raises(ingest_results.NseUnavailable):
        b.fail("x", Exception("3"))


def test_rests_then_resumes_from_the_same_company(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    monkeypatch.setattr(nse_results, "client", lambda: FakeClient())
    monkeypatch.setattr(nse_integrated, "fetch_filings", lambda c, s: [])
    state = {"down": True, "rests": 0}
    monkeypatch.setattr(ingest_results.time, "sleep", lambda s: state.update(down=False, rests=state["rests"] + 1) if s > 60 else None)

    def filings(c, symbol):
        if state["down"] and symbol == "B":
            raise TimeoutError("timed out")
        return [filing("31-Dec-2024", seq=symbol)]

    monkeypatch.setattr(nse_results, "fetch_filings", filings)
    monkeypatch.setattr(nse_results, "fetch_detail", lambda c, f: {"resultsData2": {"re_net_sale": "100"}})
    monkeypatch.setattr(ingest_results.Breaker.__init__, "__defaults__", (1,))  # one failure trips it
    assert ingest_results.fetch(lake, ["A", "B", "C"], pause=0, rests=1, rest_seconds=900) == 3
    assert state["rests"] == 1


def test_missing_files_do_not_count_as_nse_refusing():
    import httpx

    def status(code):
        req = httpx.Request("GET", "https://nsearchives.nseindia.in/x.xml")
        return httpx.HTTPStatusError("err", request=req, response=httpx.Response(code, request=req))

    b = ingest_results.Breaker(limit=2)
    for _ in range(5):
        b.fail("xbrl", status(404))  # dead links: answered, never trips
    b.fail("list", status(403))
    with pytest.raises(ingest_results.NseUnavailable):
        b.fail("list", status(429))


def test_missing_excise_in_a_table_is_nan_not_a_number_to_subtract():
    import pandas as pd

    df = pd.DataFrame({"symbol": ["IOC", "TCS"], "period_end": [date(2026, 9, 30)] * 2, "kind": ["company"] * 2,
                       "revenue": [100.0, 50.0], "finance_cost": [1.0, 1.0], "other_income": [1.0, 1.0],
                       "excise_duty": [10.0, float("nan")], "net_revenue": [None, None]})
    assert ingest_results.consistent_kind(df)["net_revenue"].tolist() == [90.0, 50.0]
