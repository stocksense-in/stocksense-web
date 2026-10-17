"""
Daily engine run — one command that brings the lake up to date and checks it, for a
scheduler to call once a day (M0.4). Nothing here installs a scheduler.

    python -m stocksense engine-daily              # last 10 days of every daily source
    python -m stocksense engine-daily --weekly     # also corporate actions + the event study
    python -m stocksense engine-daily --days 30    # catch up after the machine was off

Steps run in order; one failing doesn't stop the rest (each source is independent).
Every run appends one JSON line to <lake>/runs.jsonl: when, how long, each step's
result or error, and the data-check problems. The exit code is non-zero if any step
failed or a check found problems, so a scheduler can alert on it.

Run it after ~19:00 IST: NSE publishes the bhavcopy and index file in the evening.
Every step is resumable and rewrites only the days it touches, so rerunning is safe.
"""

from __future__ import annotations

import json
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from .. import eod, lake_checks
from ..lake import Lake
from ..log import get_logger

log = get_logger(__name__)

RUNS_FILE = "runs.jsonl"


@dataclass
class Step:
    name: str
    run: Callable[[], object]
    weekly: bool = False  # only with --weekly


@dataclass
class RunReport:
    started_at: str
    steps: list[dict] = field(default_factory=list)
    problems: dict[str, list[str]] = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return all(s["ok"] for s in self.steps) and not any(self.problems.values())


def default_steps(lake: Lake, days: int, today: date) -> list[Step]:
    from . import event_study, ingest_bhavcopy, ingest_corporate_actions, ingest_gdelt, ingest_market

    start = today - timedelta(days=days)
    return [
        Step("bhavcopy", lambda: ingest_bhavcopy.run(start, today, lake=lake)),
        Step("indices", lambda: ingest_market.run_indices(start, today, lake=lake)),
        Step("macro", lambda: ingest_market.run_macro(lake=lake, today=today)),
        Step("gdelt", lambda: ingest_gdelt.run(start, today, lake=lake)),
        Step("corporate_actions", lambda: ingest_corporate_actions.run(lake=lake, today=today), weekly=True),
        Step("event_study", lambda: event_study.run(lake=lake), weekly=True),
    ]


def run_steps(lake: Lake, steps: list[Step], weekly: bool, today: date | None = None) -> RunReport:
    today = today or date.today()
    t0 = time.monotonic()
    report = RunReport(started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for step in steps:
        if step.weekly and not weekly:
            continue
        s0 = time.monotonic()
        try:
            step.run()
            report.steps.append({"step": step.name, "ok": True, "seconds": round(time.monotonic() - s0, 1)})
            log.info(f"engine: {step.name} done in {time.monotonic() - s0:.0f}s")
        except Exception as exc:  # one source failing mustn't stop the others
            report.steps.append({"step": step.name, "ok": False, "seconds": round(time.monotonic() - s0, 1),
                                 "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)})
            log.error(f"engine: {step.name} failed: {exc}")
    try:
        checks = lake_checks.check_all(lake, today)
        report.problems = {name: r["problems"] for name, r in checks.items()}
        if "eod_prices" in lake.datasets():
            last = eod.check(lake).get("last_day")
            if last and (today - date.fromisoformat(last)).days > lake_checks.STALE_AFTER_DAYS:
                report.problems["eod_prices"] = [f"latest day {last} is stale"]
    except Exception as exc:
        report.problems = {"checks": [f"checks failed: {type(exc).__name__}: {exc}"]}
    report.seconds = round(time.monotonic() - t0, 1)
    with (lake.root / RUNS_FILE).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"started_at": report.started_at, "seconds": report.seconds, "weekly": weekly,
                            "ok": report.ok, "steps": report.steps, "problems": report.problems}) + "\n")
    return report


def run(days: int = 10, weekly: bool = False, lake: Lake | None = None, today: date | None = None) -> int:
    """Returns the process exit code: 0 when every step worked and the checks are clean."""
    lake = lake or Lake.from_settings()
    today = today or date.today()
    report = run_steps(lake, default_steps(lake, days, today), weekly, today)
    failed = [s["step"] for s in report.steps if not s["ok"]]
    found = {k: v for k, v in report.problems.items() if v}
    log.info(f"engine: {'OK' if report.ok else 'NEEDS ATTENTION'} in {report.seconds:.0f}s"
             + (f"; failed: {', '.join(failed)}" if failed else "") + (f"; problems: {found}" if found else ""))
    return 0 if report.ok else 1
