"""
M2.4 acceptance check: alerts fire on a historical replay of a known event.

    backend\\.venv\\Scripts\\python ml\\checks\\alerts_replay.py      # from the repo root

27 January 2023, the first trading day after the Hindenburg report on the Adani group:
the group's shares fell sharply on many times their usual volume. Replaying that day
must raise price_move and unusual_volume alerts for Adani Enterprises and Adani Ports;
a quiet control day two weeks earlier must raise neither for them. Exits non-zero if
either expectation fails.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from stocksense import alerts  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

EVENT, CONTROL = date(2023, 1, 27), date(2023, 1, 12)
WATCH = ["ADANIENT", "ADANIPORTS", "ADANIGREEN", "ADANIPOWER", "TCS"]
MUST_FIRE = {("ADANIENT", "price_move"), ("ADANIENT", "unusual_volume"),
             ("ADANIPORTS", "price_move"), ("ADANIPORTS", "unusual_volume")}


def main() -> int:
    lake = Lake.from_settings()
    ok = True
    for day in (EVENT, CONTROL):
        found = alerts.for_day(lake, day, WATCH)
        print(f"\n{day}: {len(found)} alerts")
        for a in found:
            print(f"  {a['symbol']:<11} {a['kind']:<15} {a['text']}")
        fired = {(a["symbol"], a["kind"]) for a in found}
        if day == EVENT and not MUST_FIRE <= fired:
            print(f"MISSING on the event day: {sorted(MUST_FIRE - fired)}")
            ok = False
        if day == CONTROL and fired & MUST_FIRE:
            print(f"FALSE ALARMS on the control day: {sorted(fired & MUST_FIRE)}")
            ok = False
    print("\nreplay passed" if ok else "\nreplay FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
