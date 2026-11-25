from datetime import date

import pytest

from stocksense.sources import nse_integrated as ni


def xbrl(facts: str) -> str:
    """A minimal XBRL instance: quarter, half-year, quarter-end and a dimensional context."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-capmkt="http://example/in-capmkt"
            xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
 <xbrli:context id="OneD"><xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="FourD"><xbrli:period><xbrli:startDate>2026-04-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="OneI"><xbrli:period><xbrli:instant>2026-09-30</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:context id="PY_I"><xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:context id="Seg1D"><xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="x">in-capmkt:SegMember</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
  <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context>
 {facts}
</xbrli:xbrl>"""


# TCS Q2 FY27 consolidated, rupees (from NSE's XBRL).
TCS = xbrl("""
 <in-capmkt:RevenueFromOperations contextRef="Seg1D" decimals="-7">1</in-capmkt:RevenueFromOperations>
 <in-capmkt:RevenueFromOperations contextRef="OneD" decimals="-7">731880000000</in-capmkt:RevenueFromOperations>
 <in-capmkt:RevenueFromOperations contextRef="FourD" decimals="-7">1454630000000</in-capmkt:RevenueFromOperations>
 <in-capmkt:OtherIncome contextRef="OneD" decimals="-7">13370000000</in-capmkt:OtherIncome>
 <in-capmkt:FinanceCosts contextRef="OneD" decimals="-7">2520000000</in-capmkt:FinanceCosts>
 <in-capmkt:ProfitBeforeTax contextRef="OneD" decimals="-7">186380000000</in-capmkt:ProfitBeforeTax>
 <in-capmkt:TaxExpense contextRef="OneD" decimals="-7">47040000000</in-capmkt:TaxExpense>
 <in-capmkt:ProfitLossForPeriod contextRef="OneD" decimals="-7">139340000000</in-capmkt:ProfitLossForPeriod>
 <in-capmkt:ProfitOrLossAttributableToOwnersOfParent contextRef="OneD" decimals="-7">138840000000</in-capmkt:ProfitOrLossAttributableToOwnersOfParent>
 <in-capmkt:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="OneD" decimals="INF">38.37</in-capmkt:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations>
 <in-capmkt:EquityAttributableToOwnersOfParent contextRef="OneI" decimals="-7">1189860000000</in-capmkt:EquityAttributableToOwnersOfParent>
 <in-capmkt:EquityAttributableToOwnersOfParent contextRef="PY_I" decimals="-7">1</in-capmkt:EquityAttributableToOwnersOfParent>
 <in-capmkt:BorrowingsNoncurrent contextRef="OneI" decimals="-7">0</in-capmkt:BorrowingsNoncurrent>
 <in-capmkt:BorrowingsCurrent contextRef="OneI" decimals="-7">0</in-capmkt:BorrowingsCurrent>
 <in-capmkt:Assets contextRef="OneI" decimals="-7">1907820000000</in-capmkt:Assets>
 <in-capmkt:NameOfCompany contextRef="OneD">Tata Consultancy Services Limited</in-capmkt:NameOfCompany>
""")
FILING = {"symbol": "TCS", "qe_Date": "30-SEP-2026", "consolidated": "Consolidated", "audited": "Audited",
          "seq_Id": "200121", "broadcast_Date": "08-Oct-2026 22:07:33",
          "xbrl": "https://nsearchives.nseindia.in/corporate/xbrl/INTEGRATED_FILING_INDAS_1734607_08102026100810_WEB.xml"}


def test_quarter_figures_in_crore_not_half_year_or_segments():
    r = ni.normalise(FILING, TCS)
    assert (r["symbol"], r["period_end"], r["consolidated"], r["kind"]) == ("TCS", date(2026, 9, 30), True, "company")
    assert r["revenue"] == pytest.approx(73188.0) and r["net_revenue"] == r["revenue"]
    assert r["net_profit"] == pytest.approx(13884.0)  # owners' share, not 13,934 total
    assert r["profit_before_tax"] == pytest.approx(18638.0) and r["tax"] == pytest.approx(4704.0)
    assert r["eps"] == 38.37


def test_balance_sheet_at_quarter_end_only():
    r = ni.normalise(FILING, TCS)
    assert r["equity"] == pytest.approx(118986.0) and r["borrowings"] == 0.0
    assert r["total_assets"] == pytest.approx(190782.0)


def test_bank_taxonomy_and_net_revenue():
    # HDFC Bank Q2 FY27 consolidated, rupees.
    bank = xbrl("""
 <in-capmkt:InterestEarned contextRef="OneD">951316300000</in-capmkt:InterestEarned>
 <in-capmkt:InterestExpended contextRef="OneD">506674300000</in-capmkt:InterestExpended>
 <in-capmkt:OtherIncome contextRef="OneD">342270600000</in-capmkt:OtherIncome>
 <in-capmkt:ProfitLossFromOrdinaryActivitiesBeforeTax contextRef="OneD">278254800000</in-capmkt:ProfitLossFromOrdinaryActivitiesBeforeTax>
 <in-capmkt:ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates contextRef="OneD">207000300000</in-capmkt:ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates>
""")
    filing = {**FILING, "symbol": "HDFCBANK", "xbrl": "https://x/INTEGRATED_FILING_BANKING_1740913_17102026054812_WEB.xml"}
    r = ni.normalise(filing, bank)
    assert r["kind"] == "bank" and r["bank"] and r["revenue"] == pytest.approx(95131.63)
    assert r["net_revenue"] == pytest.approx(95131.63 - 50667.43 + 34227.06)
    assert r["net_profit"] == pytest.approx(20700.03) and r["equity"] is None and r["borrowings"] is None


def test_insurer_revenue_is_total_income():
    # LIC Q2 FY27 standalone, rupees.
    lic = xbrl("""
 <in-capmkt:Income contextRef="OneD">2627392700000</in-capmkt:Income>
 <in-capmkt:ProfitLossBeforeTax contextRef="OneD">121258200000</in-capmkt:ProfitLossBeforeTax>
 <in-capmkt:ProfitLossAfterTaxAndExtraordinaryItems contextRef="OneD">120760200000</in-capmkt:ProfitLossAfterTaxAndExtraordinaryItems>
""")
    r = ni.normalise({**FILING, "symbol": "LICI", "xbrl": "https://x/INTEGRATED_FILING_LI_1753945_05112026064353_WEB.xml"}, lic)
    assert r["kind"] == "insurance" and r["revenue"] == pytest.approx(262739.27)
    assert r["net_profit"] == pytest.approx(12076.02) and r["profit_before_tax"] == pytest.approx(12125.82)


def test_filing_kind_from_file_name():
    assert ni.kind({"xbrl": "…/INTEGRATED_FILING_NBFC_INDAS_1_WEB.xml"}) == "finance"
    assert ni.kind({"xbrl": None}) == "company"
