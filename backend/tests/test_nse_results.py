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
    assert r["kind"] == "company" and r["net_revenue"] == r["revenue"]


def test_old_format_maps_the_same_columns():
    r = nr.normalise(FILING_OLD, DETAIL_OLD)
    assert r["period_from"] == date(2015, 10, 1) and r["revenue"] == pytest.approx(27364.0)
    assert r["net_profit"] == pytest.approx(6110.0)  # already after minority interest
    assert r["total_income"] == pytest.approx(27364.0) and r["eps"] == 31.01


def test_tax_from_current_plus_deferred_and_bank_revenue():
    detail = {"resultsData2": {"re_curr_tax": "300", "re_deff_tax": "-100", "re_int_earned": "50000"}}
    r = nr.normalise({**FILING_NEW, "bank": "B"}, detail)
    assert r["tax"] == pytest.approx(2.0) and r["revenue"] == pytest.approx(500.0) and r["bank"]
    assert r["kind"] == "bank" and r["net_revenue"] is None  # no interest expended given


def test_bank_net_revenue_is_net_interest_plus_other_income():
    # HDFC Bank Q3 FY25 consolidated (₹ lakh)
    detail = {"resultsData2": {"re_int_earned": "8504017", "re_int_expd": "4691428", "re_oth_inc": "2715377",
                               "re_tot_inc": "11219394", "re_net_profit": "1834011", "re_con_pro_loss": "1765661"}}
    r = nr.normalise({**FILING_NEW, "symbol": "HDFCBANK", "bank": "B"}, detail)
    assert r["net_revenue"] == pytest.approx(85040.17 - 46914.28 + 27153.77)
    assert r["total_income"] == pytest.approx(112193.94)
    assert r["net_profit"] == pytest.approx(17656.61)  # owners' share, after minority interest
    fin = nr.normalise({**FILING_NEW, "bank": "F"}, detail)
    assert fin["kind"] == "finance" and fin["net_revenue"] == pytest.approx(r["net_revenue"])


def test_zero_owners_share_is_a_placeholder():
    # Bajaj Finance Dec 2022 consolidated (₹ lakh): owners' line "0", profit in the next field.
    r = nr.normalise(FILING_NEW, {"resultsData2": {"re_pl_own_par": "0", "re_con_pro_loss": "297300"}})
    assert r["net_profit"] == pytest.approx(2973.0)
    assert nr.normalise(FILING_NEW, {"resultsData2": {"re_pl_own_par": "0"}})["net_profit"] == 0.0


def test_missing_values_stay_missing():
    r = nr.normalise(FILING_NEW, {"resultsData2": {"re_net_sale": "-", "re_tax": None}})
    assert r["revenue"] is None and r["tax"] is None and r["net_profit"] is None
