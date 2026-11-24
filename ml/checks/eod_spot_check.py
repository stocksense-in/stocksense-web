"""
M1.1 acceptance check: adjusted NSE price history against an independent source,
and continuity across known splits and bonuses.

    backend\\.venv\\Scripts\\python ml\\checks\\eod_spot_check.py      # from the repo root

1. 10 large caps × 6 dates: our eod_adjusted close vs Yahoo's split-adjusted close
   (chart endpoint `close`, which Yahoo adjusts for splits and bonuses, not dividends).
2. 3 known actions: the adjustment factor used, and that the adjusted close doesn't
   jump on the ex-date the way the traded price does.
Prints a table; exits non-zero if anything is outside tolerance.
"""

from __future__ import annotations

import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from stocksense import eod  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

SYMBOLS = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ITC", "NESTLEIND", "SBIN", "LT", "BHARTIARTL", "MARUTI"]
DATES = [date(2012, 3, 15), date(2015, 6, 10), date(2018, 1, 10), date(2020, 3, 24), date(2023, 2, 15), date(2026, 10, 14)]
KNOWN = [("NESTLEIND", date(2024, 1, 5), 10.0), ("HDFCBANK", date(2019, 9, 19), 2.0), ("RELIANCE", date(2024, 10, 28), 2.0)]
TOLERANCE = 0.01


def yahoo_closes(symbol: str) -> pd.Series:
    r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS",
                  params={"period1": 0, "period2": int(time.time()), "interval": "1d"},
                  headers={"User-Agent": "Mozilla/5.0 (StockSense)"}, timeout=60)
    res = r.json()["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 19800)
    idx = [datetime.fromtimestamp(t + off, timezone.utc).date() for t in res["timestamp"]]
    return pd.Series(res["indicators"]["quote"][0]["close"], index=idx).dropna()


def main() -> int:
    lake = Lake.from_settings()
    ours = eod.adjusted_history(lake, SYMBOLS)
    ours["d"] = ours["date"].dt.date
    bad = 0
    print("1) Adjusted close vs Yahoo (split-adjusted)\n")
    print(f"{'symbol':11} {'date':10} {'ours':>10} {'yahoo':>10} {'diff':>7}")
    for sym in SYMBOLS:
        y = yahoo_closes(sym)
        mine = ours[ours["symbol"] == sym].set_index("d")["close"]
        for d in DATES:
            if d not in mine.index or d not in y.index:
                print(f"{sym:11} {d}   (no trading data on one side)")
                continue
            diff = mine[d] / y[d] - 1
            flag = "" if abs(diff) <= TOLERANCE else "  <-- check"
            bad += bool(flag)
            print(f"{sym:11} {d} {mine[d]:10.2f} {y[d]:10.2f} {diff:+7.2%}{flag}")
        time.sleep(0.5)

    print("\n2) Known actions\n")
    for sym, ex, expected in KNOWN:
        h = ours[ours["symbol"] == sym].set_index("d")
        before = h[h.index < ex].iloc[-1]
        on = h[h.index >= ex].iloc[0]
        traded_jump = on["close_traded"] / before["close_traded"] - 1
        adjusted_jump = on["close"] / before["close"] - 1
        factor = before["adj_factor"] / on["adj_factor"]
        ok = abs(factor / expected - 1) < 0.01 and abs(adjusted_jump) < 0.10
        bad += not ok
        print(f"{sym:10} ex {ex}: factor {factor:.3f} (expected {expected}), traded {traded_jump:+.1%}, "
              f"adjusted {adjusted_jump:+.1%} {'OK' if ok else '<-- check'}")
    print(f"\n{'all within tolerance' if not bad else f'{bad} check(s) failed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
