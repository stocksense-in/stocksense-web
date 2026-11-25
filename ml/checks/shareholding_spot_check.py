"""
M1.3 acceptance check: shareholding figures match the filed patterns.

    backend\\.venv\\Scripts\\python ml\\checks\\shareholding_spot_check.py      # from the repo root

For every company whose latest full pattern (XBRL) has been read, the promoter holding
in NSE's summary list must equal the promoter total in the filed pattern, and the filed
split (promoter + foreign + domestic institutions + non-institutions + government +
employee trusts) must add to 100%. Prints a table; exits non-zero if any company fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from stocksense.lake import Lake  # noqa: E402

TOLERANCE = 0.01  # percentage points; both are reported to two decimals


def main() -> int:
    h = Lake.from_settings().query("select * from shareholding where promoter_pct_pattern is not null")
    if h.empty:
        print("No full patterns read yet: run ingest-shareholding first.")
        return 1
    h["split_total"] = (h["promoter_pct_pattern"] + h["fii_pct"] + h["dii_pct"] + h["non_institutions_pct"]
                        + h["government_pct"].fillna(0) + h["employee_trusts_pct"].fillna(0)).round(2)
    h["promoter_diff"] = (h["promoter_pct"] - h["promoter_pct_pattern"]).round(2)
    h["ok"] = (h["promoter_diff"].abs() <= TOLERANCE) & ((h["split_total"] - 100).abs() <= 0.1)
    cols = ["symbol", "quarter_end", "promoter_pct", "promoter_pct_pattern", "fii_pct", "dii_pct",
            "small_retail_pct", "split_total", "ok"]
    with pd.option_context("display.width", 160, "display.max_rows", 500):
        print(h.sort_values("symbol")[cols].to_string(index=False))
    print(f"\n{int(h['ok'].sum())} of {len(h)} companies match their filed pattern "
          f"(promoter within {TOLERANCE} pt, split adds to 100%)")
    return 0 if h["ok"].all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
