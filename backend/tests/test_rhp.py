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
