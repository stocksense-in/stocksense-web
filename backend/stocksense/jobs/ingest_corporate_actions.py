"""
Corporate actions job — NSE's corporate actions and symbol changes into the lake,
then the split/bonus adjustment tables and the `eod_adjusted` view (stocksense/eod.py).

    python -m stocksense ingest-corporate-actions
    python -m stocksense check-eod            # data checks on the price history

Raw copies: raw/nse_corporate_actions/<today>/actions.json and symbolchange.csv.
Run it after `ingest-bhavcopy` (the adjustment checks read the prices) and again
whenever new splits or bonuses happen (weekly is plenty).
"""

from __future__ import annotations

import json
from datetime import date

from .. import eod
from ..lake import Lake
from ..log import get_logger
from ..sources import nse_corporate

log = get_logger(__name__)

SOURCE = "nse_corporate_actions"
START = date(2010, 1, 1)


def run(lake: Lake | None = None, today: date | None = None) -> None:
    lake = lake or Lake.from_settings()
    today = today or date.today()
    folder = lake.raw_dir(SOURCE, today)

    rows = nse_corporate.fetch_actions(START, date(today.year + 1, 12, 31))  # ex-dates announced ahead too
    (folder / "actions.json").write_text(json.dumps(rows), encoding="utf-8")
    changes_csv = nse_corporate.fetch_symbol_changes()
    (folder / "symbolchange.csv").write_bytes(changes_csv)

    actions = nse_corporate.actions_frame(rows)
    changes = nse_corporate.symbol_changes_frame(changes_csv)
    lake.write_table(actions, "corporate_actions", refresh=False)
    lake.write_table(changes, "symbol_changes", refresh=False)
    log.info(f"Corporate actions: {len(actions)} rows, {len(changes)} symbol changes")
    eod.build_adjustments(lake, actions, changes)


def check(lake: Lake | None = None) -> dict:
    lake = lake or Lake.from_settings()
    report = eod.check(lake)
    for key, value in report.items():
        if isinstance(value, list) and len(value) > 12:
            value = value[:12] + [f"… {len(value) - 12} more"]
        print(f"{key}: {value}")
    return report
