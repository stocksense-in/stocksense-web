from datetime import date

import pytest

from stocksense.sources import nse_results as nr

FILING_NEW = {"symbol": "TCS", "fromDate": "01-Oct-2024", "toDate": "31-Dec-2024", "consolidated": "Consolidated",
              "audited": "Audited", "indAs": "Ind-AS New", "bank": "N", "filingDate": "09-Jan-2025 21:39",
              "seqNumber": "1189599", "params": "01-Oct-202431-Dec-2024Q3ANNCNETCS", "format": "New"}
# Real figures from NSE (₹ lakh), TCS Q3 FY25 consolidated.
DETAIL_NEW = {"resultsData2": {"re_net_sale": "6397300", "re_oth_inc_new": "124300", "re_total_inc": "6521600",
                               "re_oth_tot_exp": "4855000", "re_depr_und_exp": "137700", "re_int_new": "23400",
                               "re_pro_loss_bef_tax": "1666600", "re_tax": "422200", "re_con_pro_loss": "1244400",
                               "re_pl_own_par": "1238000", "re_bsc_eps_bfr_exi": "34.21", "re_pdup": "36200",
                               "re_face_val": "1"}}
FILING_OLD = {**FILING_NEW, "fromDate": "01-Oct-2015", "toDate": "31-Dec-2015", "indAs": "Ind-AS", "format": "Old"}
# TCS Q3 FY16 consolidated: no separate owners' line; tax as one figure.
DETAIL_OLD = {"resultsData2": {"re_net_sale": "2736400", "re_oth_inc_new": "70700", "re_gro_inc": "2736400",
                               "re_oth_tot_exp": "2008800", "re_depr_und_exp": "47100", "re_int_new": "800",
                               "re_pro_loss_bef_tax": "797500", "re_tax": "185000", "re_con_pro_loss": "611000",
                               "re_net_profit": "612500", "re_bsc_eps_bfr_exi": "31.01", "re_pdup": "19704"}}


def test_new_format_in_crore():
    r = nr.normalise(FILING_NEW, DETAIL_NEW)
    assert (r["symbol"], r["period_end"], r["consolidated"], r["audited"]) == ("TCS", date(2024, 12, 31), True, True)
    assert r["revenue"] == pytest.approx(63973.0)      # ₹ crore, as published
    assert r["net_profit"] == pytest.approx(12380.0)   # owners' share
    assert r["profit_before_tax"] == pytest.approx(16666.0) and r["tax"] == pytest.approx(4222.0)
    assert r["eps"] == 34.21 and r["face_value"] == 1.0


def test_old_format_maps_the_same_columns():
    r = nr.normalise(FILING_OLD, DETAIL_OLD)
    assert r["period_from"] == date(2015, 10, 1) and r["revenue"] == pytest.approx(27364.0)
    assert r["net_profit"] == pytest.approx(6110.0)  # already after minority interest
    assert r["total_income"] == pytest.approx(27364.0) and r["eps"] == 31.01


def test_tax_from_current_plus_deferred_and_bank_revenue():
    detail = {"resultsData2": {"re_curr_tax": "300", "re_deff_tax": "-100", "re_int_earned": "50000"}}
    r = nr.normalise({**FILING_NEW, "bank": "Y"}, detail)
    assert r["tax"] == pytest.approx(2.0) and r["revenue"] == pytest.approx(500.0) and r["bank"]


def test_missing_values_stay_missing():
    r = nr.normalise(FILING_NEW, {"resultsData2": {"re_net_sale": "-", "re_tax": None}})
    assert r["revenue"] is None and r["tax"] is None and r["net_profit"] is None
