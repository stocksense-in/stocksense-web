import gzip
import json
from datetime import date

from stocksense.jobs import ingest_rhp
from stocksense.lake import Lake
from stocksense.sources import sebi_offers

FIRST_PAGE = """<tbody><tr role='row' class='odd'>
<td>Nov 23, 2026</td>
<td><a href="https://www.sebi.gov.in/filings/public-issues/nov-2026/monomark-rhp_105932.html"  target="_blank"
 title="Monomark Engineering (India) Limited - RHP<br><a href='x-prospectus_p.pdf'>Abridged</a>" class="points">x</a></td>
</tr></tbody><p>1 to 25 of 1302 records</p>"""
AJAX_PAGE = """<tr role='row' class='odd'><td>Dec 19, 2023</td><td><a href='https://www.sebi.gov.in/filings/public-issues/dec-2023/happy_1.html'
 target="_blank" title="Happy Forgings Limited - RHP" class='points'>Happy Forgings Limited - RHP</a></td></tr>
<tr role='row' class='odd'><td>Jan 20, 2025</td><td><a href='https://www.sebi.gov.in/filings/public-issues/jan-2025/dr_2.html'
 target="_blank" title="Dr. Agarwal&#39;s Healthcare Limited - RHP" class='points'>x</a></td></tr>
<tr role='row' class='odd'><td>Jan 22, 2025</td><td><a href='https://www.sebi.gov.in/filings/public-issues/jan-2025/dr_3.html'
 target="_blank" title="Dr. Agarwal&#39;s Healthcare Limited - Addendum to RHP" class='points'>x</a></td></tr>
<p>26 to 50 of 1302 records</p>"""


def test_listing_pages_parse_both_layouts():
    rows, total = sebi_offers.parse_listing(FIRST_PAGE)
    assert total == 1302 and rows == [{"date": "2026-11-23", "title": "Monomark Engineering (India) Limited - RHP",
                                       "url": "https://www.sebi.gov.in/filings/public-issues/nov-2026/monomark-rhp_105932.html"}]
    rows, _ = sebi_offers.parse_listing(AJAX_PAGE)
    assert [r["title"] for r in rows][1] == "Dr. Agarwal's Healthcare Limited - RHP"  # entities decoded
    assert [sebi_offers.is_prospectus(r["title"]) for r in rows] == [True, True, False]


def test_company_names_and_pdf_links():
    assert sebi_offers.company_of("Seshaasai Technologies Limited RHP") == "Seshaasai Technologies Limited"
    assert sebi_offers.name_key("Monomark Engineering (India) Limited") == "monomark engineering"
    page = ("<a href='https://www.sebi.gov.in/sebi_data/commondocs/nov-2026/M-prospectus_p.pdf'>abridged</a>"
            "<iframe src='../../../web/?file=https://www.sebi.gov.in/sebi_data/attachdocs/nov-2026/1795410085057.pdf'>")
    assert sebi_offers.pdf_url(page) == "https://www.sebi.gov.in/sebi_data/attachdocs/nov-2026/1795410085057.pdf"
    assert sebi_offers.pdf_url("<p>no document</p>") is None


ISSUES = [
    {"symbol": "HAPPYFORGE", "company": "Happy Forging Limited", "ipoStartDate": "19-DEC-2023", "listingDate": "27-DEC-2023",
     "issuePrice": " 850", "securityType": "Equity"},
    {"symbol": "AGARWALEYE", "company": "Dr. Agarwal's Health Care Limited", "ipoStartDate": "29-JAN-2025",
     "listingDate": "04-FEB-2025", "issuePrice": "402", "securityType": "Equity"},
    {"symbol": "IDEAFPO", "company": "Vodafone Idea Limited - FPO", "ipoStartDate": "18-APR-2024", "securityType": "Equity"},
    {"symbol": "ADANIENPP1", "company": "Adani Enterprises Limited", "ipoStartDate": "04-SEP-2024", "securityType": "Equity"},
    {"symbol": "SMECO", "company": "Small Co Limited", "ipoStartDate": "01-JAN-2024", "securityType": "SME"},
    {"symbol": "LATE", "company": "Happy Forgings Limited", "ipoStartDate": "01-JUN-2024", "securityType": "Equity"},
]


def test_match_by_name_and_filing_window():
    listing, _ = sebi_offers.parse_listing(AJAX_PAGE)
    got = {m["symbol"]: m for m in ingest_rhp.match(listing, ISSUES)}
    assert set(got) == {"HAPPYFORGE", "AGARWALEYE"}  # FPO, partly paid, SME out; LATE filed too long before
    assert got["HAPPYFORGE"]["issue_price"] == 850.0 and got["HAPPYFORGE"]["filed"] == "2023-12-19"
    assert got["AGARWALEYE"]["url"].endswith("dr_2.html")  # the RHP, not the addendum


def test_scan_writes_one_row_per_ipo_with_rule_severities(tmp_path):
    lake = Lake(tmp_path).ensure()
    ipos = [{"symbol": "AAA", "company": "AAA Ltd", "ipo_start": "2023-12-19", "listing_date": "2023-12-27",
             "issue_price": 100.0, "filed": "2023-12-10", "url": "u1"},
            {"symbol": "BBB", "company": "BBB Ltd", "ipo_start": "2024-01-10", "listing_date": "2024-01-18",
             "issue_price": 50.0, "filed": "2024-01-02", "url": "u2"}]
    pages = ["The company has incurred losses in the last three financial years. " * 3,
             "Our top ten customers contributed 85% of our revenue from operations. " * 2] + ["filler text " * 50] * 3
    pdf = ingest_rhp.pdf_path(lake, ipos[0])
    with gzip.open(pdf.with_name("AAA.pages.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(pages, f)
    df = ingest_rhp.scan(lake, ipos).set_index("symbol")
    assert df.loc["AAA", "pages"] == 5 and df.loc["BBB", "error"] == "not downloaded"
    assert df.loc["AAA", "losses"] in ("high", "medium", "low")
    assert lake.query("select count(*) from ipo_prospectus").iloc[0, 0] == 2
    assert df.loc["AAA", "ipo_start"].date() == date(2023, 12, 19)


def test_cut_off_downloads_are_tried_again():
    import httpx

    calls = []

    class Flaky:
        def get(self, url):
            calls.append(url)
            if len(calls) < 2:
                raise httpx.RemoteProtocolError("peer closed connection without sending complete message body")
            return httpx.Response(200, content=b"%PDF-1.7", request=httpx.Request("GET", url))

    resp = ingest_rhp._get_whole(Flaky(), "https://www.sebi.gov.in/x.pdf", pause=0)
    assert resp.content == b"%PDF-1.7" and len(calls) == 2
