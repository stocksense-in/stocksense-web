import json
from datetime import date

from stocksense.jobs import engine_daily
from stocksense.jobs.engine_daily import Step
from stocksense.lake import Lake

TODAY = date(2026, 10, 16)


def test_steps_run_in_order_and_failures_dont_stop_the_rest(tmp_path):
    lake = Lake(tmp_path).ensure()
    calls = []

    def boom():
        calls.append("gdelt")
        raise RuntimeError("GDELT is down")

    steps = [Step("bhavcopy", lambda: calls.append("bhavcopy")), Step("gdelt", boom),
             Step("macro", lambda: calls.append("macro")), Step("event_study", lambda: calls.append("study"), weekly=True)]
    report = engine_daily.run_steps(lake, steps, weekly=False, today=TODAY)
    assert calls == ["bhavcopy", "gdelt", "macro"]  # weekly step skipped, later steps still ran
    assert [(s["step"], s["ok"]) for s in report.steps] == [("bhavcopy", True), ("gdelt", False), ("macro", True)]
    assert "GDELT is down" in report.steps[1]["error"]
    assert not report.ok

    line = json.loads((tmp_path / "runs.jsonl").read_text().splitlines()[-1])
    assert line["ok"] is False and line["weekly"] is False and len(line["steps"]) == 3


def test_weekly_runs_everything_and_a_clean_run_is_ok(tmp_path):
    lake = Lake(tmp_path).ensure()
    calls = []
    steps = [Step("a", lambda: calls.append("a")), Step("b", lambda: calls.append("b"), weekly=True)]
    report = engine_daily.run_steps(lake, steps, weekly=True, today=TODAY)
    assert calls == ["a", "b"] and report.ok and report.problems == {}
    engine_daily.run_steps(lake, steps, weekly=True, today=TODAY)
    assert len((tmp_path / "runs.jsonl").read_text().splitlines()) == 2  # appends, never overwrites


def test_exit_code_follows_the_report(tmp_path, monkeypatch):
    lake = Lake(tmp_path).ensure()
    monkeypatch.setattr(engine_daily, "default_steps", lambda lake, days, today: [Step("ok", lambda: None)])
    assert engine_daily.run(lake=lake, today=TODAY) == 0

    def failing(lake, days, today):
        return [Step("bad", lambda: 1 / 0)]

    monkeypatch.setattr(engine_daily, "default_steps", failing)
    assert engine_daily.run(lake=lake, today=TODAY) == 1


def test_default_steps_cover_every_source(tmp_path):
    names = [(s.name, s.weekly) for s in engine_daily.default_steps(Lake(tmp_path), 10, TODAY)]
    assert names == [("bhavcopy", False), ("indices", False), ("macro", False), ("gdelt", False), ("fno", False),
                     ("corporate_actions", True), ("event_study", True)]
