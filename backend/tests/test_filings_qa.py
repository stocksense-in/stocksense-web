import gzip
import json
from datetime import date

import pandas as pd
import pytest

from stocksense import filings_qa as fq
from stocksense.lake import Lake

PAGES = [
    "RED HERRING PROSPECTUS. DHARMAJ CROP GUARD LIMITED. Our Company was incorporated on January 19, 2015 at Ahmedabad. "
    "BOOK RUNNING LEAD MANAGER Elara Capital (India) Private Limited. REGISTRAR TO THE OFFER Link Intime India Private Limited.",
    "Dharmaj Crop Guard sells crop protection products to farmers across India. Dharmaj Crop Guard has three plants.",
    "Summary of restated financial information (₹ million): Revenue from operations 3,940.73; Net worth 1,011.67.",
    "Outstanding litigation. Litigation against our Company: criminal proceedings 1; tax proceedings 3.",
    "Risk factors. Our business depends on the monsoon. Our Company may face competition from larger peers.",
]


def test_terms_fold_plurals_drop_stopwords_and_keep_numbers_whole():
    assert fq.terms("The Statutory Auditors' net worth was 2,093.71 crores") == [
        "statutory", "auditor", "net", "worth", "2093.71", "crore"]
    assert fq.terms("Company's liabilities") == ["company", "liability"]


def test_glossary_maps_plain_english_to_prospectus_terms():
    assert "incorporated" in fq.expand("When was it set up?")
    assert "book running lead managers" in fq.expand("Which investment banks run the IPO?")
    assert fq.expand("What is the net worth?") == "What is the net worth?"


@pytest.mark.parametrize("question,page", [
    ("Who is the registrar to the offer?", 1),
    ("When was Dharmaj Crop Guard incorporated?", 1),
    ("What is Dharmaj Crop Guard's net worth?", 3),
    ("How many criminal cases are pending against the company?", 4),
    ("Who are its competitors?", 5),
])
def test_search_ranks_the_answer_page_first(question, page):
    hits = fq.PageIndex(PAGES, "Dharmaj Crop Guard Limited").search(question)
    assert hits[0].page == page


def test_company_name_counts_less_than_the_question():
    index = fq.PageIndex(PAGES, "Dharmaj Crop Guard Limited")
    weights = index.query("Who audits Dharmaj Crop Guard?")
    assert weights["dharmaj"] == fq.NAME_WEIGHT and weights["audit"] == 1.0
    # page 2 repeats the name but says nothing else the question asks
    assert index.search("Dharmaj Crop Guard net worth")[0].page == 3


def test_snippet_shows_the_part_of_the_page_with_the_question_words():
    page = "Intro text. " * 60 + "Registrar to the Offer: Link Intime India Private Limited, Mumbai." + " More text." * 60
    text = fq.snippet(page, "Who is the registrar to the offer?")
    assert "Registrar to the Offer: Link Intime" in text and text.startswith("…")


def test_ask_reads_the_extracted_prospectus_and_the_company_name(tmp_path):
    lake = Lake(tmp_path).ensure()
    folder = lake.raw_dir(fq.SOURCE, date(2022, 11, 21))
    (folder / "DHARMAJ.pages.json.gz").write_bytes(gzip.compress(json.dumps(PAGES).encode()))
    lake.write_table(pd.DataFrame([{"symbol": "DHARMAJ", "company": "Dharmaj Crop Guard Limited"}]), "ipo_prospectus")
    assert fq.company_name(lake, "dharmaj") == "Dharmaj Crop Guard Limited"
    hits = fq.ask(lake, "dharmaj", "Who is the registrar?", k=2)
    assert [h.page for h in hits][0] == 1 and len(hits) <= 2
    with pytest.raises(LookupError, match="ingest-rhp"):
        fq.ask(lake, "NOPE", "anything")


def test_ask_calls_searches_the_latest_transcripts_and_says_which_call(tmp_path):
    lake = Lake(tmp_path).ensure()
    calls = {date(2026, 7, 20): ["Welcome to the call.", "Loan growth should be about 12% next year, we expect."],
             date(2026, 10, 20): ["Welcome to the call.", "Deposits grew well.", "Credit costs stayed low this quarter."]}
    rows = []
    for filed, pages in calls.items():
        folder = lake.raw_dir("nse_transcripts", filed)
        (folder / f"ACME_{filed:%m}.pages.json.gz").write_bytes(gzip.compress(json.dumps(pages).encode()))
        rows.append({"symbol": "ACME", "filed": filed, "file": f"{filed.isoformat()}/ACME_{filed:%m}.pages.json.gz",
                     "is_call": True, "attachment": f"https://x/{filed:%m}.pdf"})
    lake.write_table(pd.DataFrame(rows), "transcripts")
    hit = fq.ask_calls(lake, "acme", "What is the outlook for loan growth?", k=1)[0]
    assert (hit.document, hit.page, hit.link) == ("2026-07-20", 2, "https://x/07.pdf")
    assert fq.ask_calls(lake, "ACME", "credit costs", k=1)[0].document == "2026-10-20"
    with pytest.raises(LookupError, match="ingest-transcripts"):
        fq.ask_calls(lake, "NOPE", "anything")
