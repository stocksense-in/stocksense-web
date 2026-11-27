"""
M1.3 acceptance check: promoter pledges from the quarterly patterns match NSE's pledge disclosures.

    backend\\.venv\\Scripts\\python ml\\checks\\pledge_spot_check.py      # from the repo root

Two separate filings report the share of the promoters' holding that is pledged:
  • the quarterly shareholding pattern (XBRL), read into `shareholding.promoter_pledged_pct`
    and `promoter_encumbered_pct`; this is where the history comes from
  • NSE's pledge disclosures (`pledges.pledged_pct_of_promoter`), the current position only

For companies whose latest pattern is the Sep 2026 quarter, compare that pattern with the first pledge
snapshot after it. Pledges made or released between the quarter end and the snapshot show up as
differences, so the check reports the share within a point rather than demanding all match, and
lists the rest. Exits non-zero if fewer than 90% agree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from stocksense.lake import Lake  # noqa: E402

TOLERANCE = 1.0  # percentage points of the promoters' stake
QUARTER = "2026-09-30"
PASS_RATE = 0.9


def main() -> int:
    lake = Lake.from_settings()
    h = lake.query(f"""
        select symbol, quarter_end, promoter_pct, promoter_pledged_pct, promoter_encumbered_pct
        from shareholding
        where quarter_end = date '{QUARTER}' and promoter_pledged_pct is not null and promoter_pct >= 1""")
    p = lake.query("""
        select symbol, fetched, pledged_pct_of_promoter from pledges
        where pledged_pct_of_promoter is not null
        qualify row_number() over (partition by symbol order by fetched) = 1""")
    m = h.merge(p, on="symbol")
    if m.empty:
        print("No company has both a Sep 2026 pattern with pledges and a pledge snapshot yet.")
        return 1
    m["diff_pledged"] = (m["promoter_pledged_pct"] - m["pledged_pct_of_promoter"]).round(2)
    m["diff_encumbered"] = (m["promoter_encumbered_pct"] - m["pledged_pct_of_promoter"]).round(2)
    m["ok"] = m["diff_pledged"].abs() <= TOLERANCE
    pledged = m[(m["promoter_pledged_pct"] > 0) | (m["pledged_pct_of_promoter"] > 0)]
    cols = ["symbol", "promoter_pct", "promoter_pledged_pct", "promoter_encumbered_pct", "pledged_pct_of_promoter",
            "fetched", "diff_pledged"]
    with pd.option_context("display.width", 160, "display.max_rows", 500):
        print("Companies with pledges in either filing:")
        print(pledged.sort_values("symbol")[cols].to_string(index=False))
        misses = m[~m["ok"]]
        if len(misses):
            print("\nDifferences of more than a point:")
            print(misses.sort_values("diff_pledged")[cols].to_string(index=False))
    rate = m["ok"].mean()
    enc_rate = (m["diff_encumbered"].abs() <= TOLERANCE).mean()
    print(f"\n{int(m['ok'].sum())} of {len(m)} companies ({rate:.0%}) match within {TOLERANCE:g} pt "
          f"(pledged only); {enc_rate:.0%} if every encumbrance is counted. "
          f"Of the {len(pledged)} with pledges in either filing, {int(pledged['ok'].sum())} match.")
    return 0 if rate >= PASS_RATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
