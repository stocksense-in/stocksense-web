import pytest

from pdf_fixture import SAMPLE_DRHP, make_pdf
from stocksense import rhp


def test_finds_expected_red_flags_with_pages():
    result = rhp.scan_pdf(make_pdf(SAMPLE_DRHP))
    by_id = {f.id: f for f in result.findings}
    assert result.pages == 3
    assert by_id["customer-concentration"].severity == rhp.HIGH
    assert by_id["customer-concentration"].evidence[0].page == 1
    assert "₹142 crore" in by_id["litigation"].summary
    assert "80%" in by_id["offer-for-sale"].summary
    assert "₹75 crore" in by_id["general-corporate-purposes"].summary
    assert "criminal-proceedings" in by_id


def test_high_severity_first_and_clean_rules_listed():
    result = rhp.scan_pages([" ".join(p) for p in SAMPLE_DRHP])
    order = [rhp._ORDER[f.severity] for f in result.findings]
    assert order == sorted(order)
    assert {c["id"] for c in result.clear} >= {"promoter-pledge", "auditor-remarks"}


def test_clean_document_has_no_findings():
    assert rhp.scan_pages(["We make biscuits. Revenue grew steadily."]).findings == []


@pytest.mark.parametrize("data,message", [
    (b"hello", "isn't a PDF"),
    (b"%PDF-1.4 truncated", "damaged"),
    (make_pdf([["short"]]), "looks scanned"),
])
def test_unreadable_files_raise_friendly_errors(data, message):
    with pytest.raises(rhp.ScanError, match=message):
        rhp.scan_pdf(data)


EVIDENCE = {"listed_from": "2016-02", "listed_to": "2026-05", "rules": {
    "losses": {"flagged": 120, "clear": 280, "verdict": "worse", "median_flagged": -0.081, "median_clear": -0.012,
               "weak_flagged": 0.41, "weak_clear": 0.28, "diff": -0.06, "lo": -0.10, "hi": -0.02},
    "litigation": {"flagged": 350, "clear": 50, "verdict": "no clear difference", "median_flagged": -0.02,
                   "median_clear": -0.015, "weak_flagged": 0.31, "weak_clear": 0.30, "diff": -0.01, "lo": -0.06, "hi": 0.04},
    "promoter-pledge": {"flagged": 6, "clear": 394, "verdict": "too few to judge"},
}}


def test_track_record_reads_the_study():
    text = rhp.track_record("losses", EVIDENCE)
    assert text.startswith("In 400 IPOs listed 2016–2026, the 120 with this flag returned a median -8% against NIFTY 50")
    assert "41% trailed the market by more than 10 points, against 28%" in text and text.endswith("measurably worse.")
    assert "within what chance would give" in rhp.track_record("litigation", EVIDENCE)
    assert rhp.track_record("promoter-pledge", EVIDENCE) is None  # too few cases
    assert rhp.track_record("losses", {}) is None  # no study yet


# A synthetic offer-document summary in the SEBI ICDR layout, as text extraction lays it out.
LITIGATION_PAGE = """Summary of Outstanding Litigation (in Rs. million, unless otherwise specified)
Name of the Entity Criminal Proceedings Tax Proceedings Statutory or Regulatory Proceedings Disciplinary
actions by the SEBI or Stock Exchanges against our Promoter Material Civil Litigations Aggregate Amount Involved*
Company By our Company 2 - - - - 11.93
Against our
Company
- 9 2 - 1 2,155.40
Directors By our Directors - - - - - -
Against our Directors 1# Nil Nil N.A Nil Nil
Promoters By our Promoters - - - - - -
Against our Promoters - 1 - - - 0.15
* To the extent quantifiable"""
FINANCIALS_PAGE = """Summary of Restated Consolidated Financial Information (in Rs. million, unless otherwise stated)
Particulars June 30, 2024 March 31, 2024 Equity Share capital 247.93 247.93 Net Worth(1) 11,406.53 10,758.68"""
FOOTNOTED_NET_WORTH = "Summary of restated financial information (in Rs. million) Return on Net Worth (%) 9.39 Net Worth1 1,870.50 1,794.08"


def test_litigation_table_reads_cases_against_each():
    table = rhp.litigation_table(["Cover page", LITIGATION_PAGE])
    assert table["page"] == 2
    company = table["rows"]["company"]
    assert (company["criminal"], company["tax"], company["regulatory"], company["civil"]) == (0, 9, 2, 1)
    assert company["amount_cr"] == pytest.approx(215.54)  # ₹2,155.40 million
    assert table["rows"]["directors"]["criminal"] == 1  # footnote mark ignored
    assert rhp.net_worth_crore([FINANCIALS_PAGE]) == pytest.approx(1140.653)
    assert rhp.net_worth_crore([FOOTNOTED_NET_WORTH]) == pytest.approx(187.05)  # not the return on net worth


def test_rules_use_the_table_not_boilerplate():
    boilerplate = ("Criminal proceedings against our Company, if any, could harm our reputation. "
                   "There are no qualifications, reservations and adverse remarks by our Statutory Auditors.")
    found = {f.id: f for f in rhp.scan_pages([boilerplate, LITIGATION_PAGE, FINANCIALS_PAGE]).findings}
    assert found["criminal-proceedings"].severity == rhp.MEDIUM  # none against the company or promoters; one against a director
    assert "against its directors" in found["criminal-proceedings"].summary
    assert found["litigation"].severity == rhp.HIGH  # ₹215.6 crore is 18.9% of a ₹1,141 crore net worth
    assert "18.9% of its net worth" in found["litigation"].summary
    assert found["regulatory-action"].severity == rhp.LOW  # two regulatory proceedings
    assert "auditor-remarks" not in found  # "no qualifications" is a negation
    clean = LITIGATION_PAGE.replace("- 9 2 - 1 2,155.40", "- - - - - -").replace("1# Nil", "Nil Nil").replace("- 1 - - - 0.15", "- - - - - -")
    assert {f.id for f in rhp.scan_pages([boilerplate, clean]).findings}.isdisjoint(
        {"criminal-proceedings", "litigation", "regulatory-action"})


def test_auditor_qualification_outranks_emphasis():
    q = rhp.scan_pages(["Our Statutory Auditors have included certain emphasis of matters, and audit qualifications in the report."])
    assert {f.id: f.severity for f in q.findings}["auditor-remarks"] == rhp.HIGH
    e = rhp.scan_pages(["Our Statutory Auditors have included an emphasis of matter paragraph in their Examination Report."])
    assert {f.id: f.severity for f in e.findings}["auditor-remarks"] == rhp.LOW


def test_stated_judges_each_match_in_its_own_sentence():
    page = ("There is no emphasis of\nmatter in the audit report for Fiscal 2024. Our Statutory Auditors have included an "
            "emphasis of matter paragraph for Fiscal 2023.")
    hits = rhp._stated([page], r"emphasis\s+of\s+matters?")
    assert len(hits) == 1 and "2023" in hits[0].quote  # the first (across a line break) is negated, the second stands
