from datetime import date

import pytest

from stocksense.sources import nse_shareholding as sh

# Trimmed from NSE's master list for TCS.
MASTER = [
    {"symbol": "TCS", "date": "30-SEP-2026", "pr_and_prgrp": "71.77", "public_val": "28.23", "employeeTrusts": "0",
     "submissionDate": "19-OCT-2026", "revisedData": "N", "recordId": "215653",
     "xbrl": "https://nsearchives.nseindia.in/corporate/xbrl/SHP_1741905_19102026063741_WEB.xml"},
    {"symbol": "TCS", "date": "30-JUN-2026", "pr_and_prgrp": "71.77", "public_val": "28.23", "employeeTrusts": "0",
     "submissionDate": "21-JUL-2026", "revisedData": "N", "recordId": "1"},
    {"symbol": "TCS", "date": "30-JUN-2026", "pr_and_prgrp": "71.78", "public_val": "28.22", "employeeTrusts": "0",
     "submissionDate": "02-AUG-2026", "revisedData": "Y", "recordId": "2"},  # revised pattern wins
    {"symbol": "TCS", "date": "not a date"},
]
# Adani Enterprises pledge position, 25 Nov 2026.
PLEDGE = [{"shp": "30-Sep-2026", "percPromoterHolding": "    71.97", "percPromoterShares": "     0.79",
           "numSharesPledged": "23446206", "totPromoterHolding": "974234554", "totIssuedShares": "1353722600"}]


def test_holdings_one_row_per_quarter_latest_submission():
    rows = sh.holdings(MASTER)
    assert [r["quarter_end"] for r in rows] == [date(2026, 6, 30), date(2026, 9, 30)]
    assert rows[0]["promoter_pct"] == 71.78 and rows[0]["revised"] and rows[0]["record_id"] == "2"
    assert rows[1]["public_pct"] == 28.23 and rows[1]["employee_trusts_pct"] == 0.0


def test_pledge_as_share_of_promoter_and_total():
    p = sh.pledge(PLEDGE, "adanient", date(2026, 11, 26))
    assert p["symbol"] == "ADANIENT" and p["shp_quarter_end"] == date(2026, 9, 30)
    assert p["promoter_pct"] == 71.97 and p["encumbered_pct_of_promoter_shp"] == 0.79
    assert p["pledged_pct_of_promoter"] == pytest.approx(2.41) and p["pledged_pct_of_total"] == pytest.approx(1.73)
    assert sh.pledge([], "X", date(2026, 11, 26)) is None
