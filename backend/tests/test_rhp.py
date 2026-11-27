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
