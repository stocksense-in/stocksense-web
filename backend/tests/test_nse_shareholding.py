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
           "percTotShares": "     0.57", "totPromoterShares": "7700000", "numSharesPledged": "23446206",
           "percSharesPledged": "1.73", "totPromoterHolding": "974234554", "totIssuedShares": "1353722600"}]
# ITC: no promoter group to speak of; depository pledges are other holders' margin pledges.
PLEDGE_ITC = [{"shp": "30-Sep-2026", "percPromoterHolding": "     0.00", "percPromoterShares": "     0.00",
               "totPromoterShares": "0", "numSharesPledged": "249875656", "percSharesPledged": "2",
               "totPromoterHolding": "0"}]


def test_holdings_one_row_per_quarter_latest_submission():
    rows = sh.holdings(MASTER)
    assert [r["quarter_end"] for r in rows] == [date(2026, 6, 30), date(2026, 9, 30)]
    assert rows[0]["promoter_pct"] == 71.78 and rows[0]["revised"] and rows[0]["record_id"] == "2"
    assert rows[1]["public_pct"] == 28.23 and rows[1]["employee_trusts_pct"] == 0.0


def test_pledge_as_share_of_promoter_and_total():
    p = sh.pledge(PLEDGE, "adanient", date(2026, 11, 26))
    assert p["symbol"] == "ADANIENT" and p["shp_quarter_end"] == date(2026, 9, 30)
    assert p["promoter_pct"] == 71.97 and p["promoter_shares_pledged"] == 7700000
    assert p["pledged_pct_of_promoter"] == 0.79 and p["pledged_pct_of_total"] == 0.57
    assert p["all_pledges_pct_of_total"] == pytest.approx(1.73)  # anyone's pledges, not the promoters'
    assert sh.pledge([], "X", date(2026, 11, 26)) is None


def test_no_promoter_no_promoter_pledge():
    p = sh.pledge(PLEDGE_ITC, "ITC", date(2026, 11, 26))
    assert p["pledged_pct_of_promoter"] is None and p["all_pledges_pct_of_total"] == 2.0


def test_categories_from_pattern_xbrl():
    xml = """<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
        xmlns:in-capmkt="http://x">
      <xbrli:context id="F"><xbrli:entity><xbrli:segment>
        <xbrldi:explicitMember dimension="d">in-capmkt:InstitutionsForeignMember</xbrldi:explicitMember>
      </xbrli:segment></xbrli:entity></xbrli:context>
      <xbrli:context id="D"><xbrli:entity><xbrli:segment>
        <xbrldi:explicitMember dimension="d">in-capmkt:InstitutionsDomesticMember</xbrldi:explicitMember>
      </xbrli:segment></xbrli:entity></xbrli:context>
      <xbrli:context id="D2"><xbrli:entity><xbrli:segment>
        <xbrldi:explicitMember dimension="d">in-capmkt:InstitutionsDomesticMember</xbrldi:explicitMember>
        <xbrldi:explicitMember dimension="e">in-capmkt:SomeHolderMember</xbrldi:explicitMember>
      </xbrli:segment></xbrli:entity></xbrli:context>
      <in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="D2">0.5</in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="F">0.0901</in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="D">0.1357</in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <in-capmkt:NumberOfShares contextRef="F">123</in-capmkt:NumberOfShares>
    </xbrli:xbrl>"""
    assert sh.categories(xml) == {"fii_pct": 9.01, "dii_pct": 13.57}  # TCS, Sep 2026


def test_old_patterns_in_percent_new_in_fractions():
    assert sh.as_percent({"fii_pct": 0.0901, "dii_pct": 0.1357}) == {"fii_pct": 9.01, "dii_pct": 13.57}
    assert sh.as_percent({"fii_pct": 0.0, "non_institutions_pct": 28.98}) == {"fii_pct": 0.0, "non_institutions_pct": 28.98}
    assert sh.as_percent({}) == {}


def _pattern(values: dict[str, float]) -> str:
    """A minimal shareholding-pattern XBRL: one context and one percentage per category member."""
    contexts = "".join(
        f'<xbrli:context id="c{i}"><xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="d">'
        f'in-capmkt:{member}</xbrldi:explicitMember></xbrli:segment></xbrli:entity></xbrli:context>'
        for i, member in enumerate(values))
    facts = "".join(f'<in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="c{i}">{v}'
                    f'</in-capmkt:ShareholdingAsAPercentageOfTotalNumberOfShares>' for i, v in enumerate(values.values()))
    return ('<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            f'xmlns:in-capmkt="http://x">{contexts}{facts}</xbrli:xbrl>')


def _with_pledges(facts: str, answers: dict[str, str] | None = None) -> str:
    """A pattern with a promoter context ("P"), a public one ("Q") and the given pledge facts."""
    contexts = "".join(
        f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="d">'
        f'in-bse-shp:{member}</xbrldi:explicitMember></xbrli:segment></xbrli:entity></xbrli:context>'
        for cid, member in (("P", "ShareholdingOfPromoterAndPromoterGroupMember"), ("Q", "PublicShareholdingMember")))
    yes_no = "".join(f'<in-bse-shp:{q} contextRef="MainI">{a}</in-bse-shp:{q}>' for q, a in (answers or {}).items())
    return ('<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            f'xmlns:in-bse-shp="http://x">{contexts}{yes_no}{facts}'
            '<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="P">0.3053'
            '</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares></xbrli:xbrl>')


def test_promoter_pledges_since_2024_split_pledges_from_other_encumbrances():
    facts = ('<in-bse-shp:EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares contextRef="Q">0.9'
             '</in-bse-shp:EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares>'
             '<in-bse-shp:EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares contextRef="P">0.8283'
             '</in-bse-shp:EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares>'
             '<in-bse-shp:EncumberedSharesHeldAsPercentageOfTotalNumberOfShares contextRef="P">0.9'
             '</in-bse-shp:EncumberedSharesHeldAsPercentageOfTotalNumberOfShares>')
    out = sh.categories(_with_pledges(facts))  # Pakka, Oct 2026 (the public row's pledges are ignored)
    assert out["promoter_pledged_pct"] == 82.83 and out["promoter_encumbered_pct"] == 90.0
    assert out["promoter_pct_pattern"] == 30.53


def test_promoter_pledges_before_2024_one_column():
    facts = ('<in-bse-shp:PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares contextRef="P">0.8499'
             '</in-bse-shp:PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares>')
    out = sh.categories(_with_pledges(facts))
    assert out["promoter_encumbered_pct"] == 84.99 and "promoter_pledged_pct" not in out


def test_no_pledges_declared_means_zero():
    new = {q: "false" for q in sh.NONE_ENCUMBERED}
    assert {k: v for k, v in sh.categories(_with_pledges("", new)).items() if "pledged" in k or "encumbered" in k} == {
        "promoter_pledged_pct": 0.0, "promoter_encumbered_pct": 0.0}
    old = sh.categories(_with_pledges("", {sh.NONE_ENCUMBERED_OLD: "false"}))
    assert old["promoter_encumbered_pct"] == 0.0 and "promoter_pledged_pct" not in old
    # pledged nothing but tied shares up another way: the encumbered figure is unknown, not zero
    partial = sh.categories(_with_pledges("", {**new, sh.NONE_ENCUMBERED[1]: "true"}))
    assert partial["promoter_pledged_pct"] == 0.0 and "promoter_encumbered_pct" not in partial


def test_older_pattern_formats():
    # 2023–24: same categories, older spellings (MutualFundsOrUti, the taxonomy's own "Goverments")
    mid = sh.categories(_pattern({"InstitutionsForeignMember": 47.83, "InstitutionsDomesticMember": 33.6,
                                                 "MutualFundsOrUtiMember": 25.1, "GovermentsMember": 0.2}))
    assert (mid["fii_pct"], mid["dii_pct"], mid["mutual_funds_pct"], mid["government_pct"]) == (47.83, 33.6, 25.1, 0.2)
    # pre-2023: foreign portfolio investors inside one Institutions total; domestic is the rest
    old = sh.categories(_pattern({"InstitutionsMember": 59.42, "InstitutionsForeignPortfolioInvestorMember": 32.31,
                                                 "MutualFundsOrUtiMember": 18.03,
                                                 "IndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakhMember": 10.78}))
    assert (old["fii_pct"], old["dii_pct"], old["mutual_funds_pct"], old["small_retail_pct"]) == (32.31, 27.11, 18.03, 10.78)
    assert "_fpi" not in old and "_institutions" not in old
