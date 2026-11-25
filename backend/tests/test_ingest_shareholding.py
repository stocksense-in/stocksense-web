from datetime import date

from stocksense.jobs import ingest_shareholding as job
from stocksense.lake import Lake
from stocksense.sources import nse_shareholding
from tests.test_nse_shareholding import MASTER, PLEDGE


class FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_once_a_day_and_build_both_tables(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    calls = []
    monkeypatch.setattr(nse_shareholding, "client", lambda: FakeClient())
    monkeypatch.setattr(nse_shareholding, "fetch_master", lambda c, s: calls.append(s) or MASTER)
    monkeypatch.setattr(nse_shareholding, "fetch_pledges", lambda c, s: PLEDGE)
    day1, day2 = date(2026, 11, 26), date(2026, 11, 27)
    assert job.fetch(lake, ["TCS"], today=day1, pause=0) == 1
    assert job.fetch(lake, ["TCS"], today=day1, pause=0) == 0 and calls == ["TCS"]  # already fetched today
    assert job.fetch(lake, ["TCS"], today=day2, pause=0) == 1
    holdings, pledges = job.build(lake)
    assert holdings["quarter_end"].tolist() == [date(2026, 6, 30), date(2026, 9, 30)]  # quarters not duplicated
    assert pledges["fetched"].tolist() == [day1, day2]  # one snapshot per day: pledge history
    assert lake.query("select max(promoter_pct) from shareholding").iloc[0, 0] == 71.78


def test_a_failed_request_keeps_the_other(tmp_path, monkeypatch):
    lake = Lake(tmp_path)
    monkeypatch.setattr(nse_shareholding, "client", lambda: FakeClient())
    monkeypatch.setattr(nse_shareholding, "fetch_master", lambda c, s: MASTER)

    def down(c, s):
        raise TimeoutError("timed out")

    monkeypatch.setattr(nse_shareholding, "fetch_pledges", down)
    assert job.fetch(lake, ["TCS"], today=date(2026, 11, 26), pause=0) == 1
    holdings, pledges = job.build(lake)
    assert len(holdings) == 2 and pledges.empty
