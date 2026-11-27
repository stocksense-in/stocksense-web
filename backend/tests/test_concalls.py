import gzip
import json
from datetime import date

import pandas as pd
import pytest

from stocksense import concalls as cc
from stocksense.lake import Lake

HEADER = "Acme Industries Limited\nQ2 FY27 Earnings Call\n"


def page(n: int, body: str) -> str:
    return f"{HEADER}Page {n} of 6\n{body}\n"


# A call in the "Name: text" style (TCS, HDFC Bank)
CALL = [
    page(1, "Moderator: Ladies and gentlemen, good day and welcome to the Acme earnings call.\n"
            "Ravi Kumar: Thank you. Good evening, everyone.\n"
            "Revenue grew 18% year-on-year to Rs 4,200 crores this quarter.\n"
            "EBITDA margin was 21.5%, up 120 bps."),
    page(2, "Ravi Kumar: For FY28 we expect revenue growth of 15% to 17%.\n"
            "We will invest Rs 900 crores in capex next year in a new plant.\n"
            "Our EBITDA margin guidance remains at 20% to 22% for the year."),
    page(3, "Moderator: We will now begin the question-and-answer session. The first question is from the line "
            "of Priya Shah from Alpha Securities.\nPriya Shah: Thanks. Your peers expect margins of 25% next year. "
            "Do you see margins reaching 25%?\nAnd will revenue grow 30% next year, as you said last time?"),
    page(4, "Ravi Kumar: We expect revenue growth of 15% to 17%, as I said.\nPriya Shah: Thank you."),
    page(5, "Moderator: The next question is from the line of Arun Rao from Beta Capital.\n"
            "Arun Rao: What about debt? We think debt will be Rs 2,000 crores next year.\n"
            "Meena Iyer: Net debt should be below Rs 500 crores by the end of FY28."),
    page(6, "Moderator: Thank you. That concludes the call."),
]
DAY = date(2026, 10, 20)


def test_fiscal_year():
    assert cc.fiscal_year(date(2026, 10, 20)) == 2027 and cc.fiscal_year(date(2027, 3, 31)) == 2027
    assert cc.fiscal_year(date(2027, 4, 1)) == 2028


def test_sentences_drop_headers_and_carry_speakers_across_pages():
    sents = cc.sentences(CALL)
    texts = [s.text for s in sents]
    assert not any("Acme Industries Limited" in t or "Page 2" in t for t in texts)
    first_capex = next(s for s in sents if "capex" in s.text)
    assert (first_capex.page, first_capex.speaker) == (2, "Ravi Kumar")
    assert cc.qa_start(sents) == texts.index(next(t for t in texts if "question-and-answer" in t))


def test_management_excludes_moderator_and_the_analysts_it_introduces():
    sents = cc.sentences(CALL)
    # Meena Iyer only answers in the Q&A but says too little to be told from an analyst; the CFO-style
    # answerers who spoke in the prepared remarks are kept
    assert "Ravi Kumar" in cc.management(sents)
    assert not {"Moderator", "Priya Shah", "Arun Rao"} & cc.management(sents)
    assert cc.management([cc.Line(1, None, "No names anywhere in this text at all.")]) is None


def test_speaker_label_styles():
    assert cc._speaker("Salil Parekh") == ("Salil Parekh", "")  # name alone on a line (Infosys)
    assert cc._speaker("Sh V Srikanth 00:00:01 – 00:09:00 (Group Performance)")[0] == "V Srikanth"  # Reliance
    assert cc._speaker("Company Speaker (Amit Chaturvedi) So, our volume was 1.6 million tonnes.") == (
        "Amit Chaturvedi", "So, our volume was 1.6 million tonnes.")
    assert cc._speaker("K Krithivasan: Thank you, Sudheer.") == ("K Krithivasan", "Thank you, Sudheer.")
    for not_a_name in ("BSE LIMITED", "Email", "Scrip Code: 500325", "National Stock Exchange of India Limited",
                       "Revenue grew 18% this quarter."):
        assert cc._speaker(not_a_name)[0] is None, not_a_name


def test_guidance_is_managements_forward_looking_figures():
    quotes = cc.guidance(CALL, DAY)
    texts = [q.text for q in quotes]
    assert "For FY28 we expect revenue growth of 15% to 17%." in texts
    assert any("Rs 900 crores in capex" in t for t in texts)
    assert any("margin guidance remains at 20% to 22%" in t for t in texts)
    assert not any("25%" in t or "30%" in t for t in texts)  # the analyst's numbers, not the company's
    assert not any("grew 18%" in t for t in texts)  # a result, not guidance
    assert sum("15% to 17%" in t for t in texts) == 1  # said twice, counted once
    assert {q.topic for q in quotes} >= {"revenue", "capex", "margins"}
    assert all(q.page for q in quotes)


def test_highlights_are_reported_results_from_the_prepared_remarks():
    texts = [q.text for q in cc.highlights(CALL, DAY)]
    assert "Revenue grew 18% year-on-year to Rs 4,200 crores this quarter." in texts
    assert "EBITDA margin was 21.5%, up 120 bps." in texts
    assert not any("expect" in t for t in texts)


def test_quantities():
    assert cc._numbers("revenue of Rs 4,200 crores, up 18%, margin 120 bps, ₹50 and 3.2x") == (
        "₹4,200", "18%", "120bps", "₹50", "3.2x")
    assert cc._numbers("across the next 2 quarters, we will see volumes grow") == ()  # not "rs," of quarters


def test_changes_compare_like_with_like():
    def q(topic, text):
        return cc.Quote(1, text, topic, cc._numbers(text), 3.0)

    now = [q("revenue", "Based on our Q2 performance our revenue growth guidance for the year is 1% to 2%."),
           q("margins", "Our operating margin guidance remains at 20% to 22% for the year."),
           q("capex", "Capex guidance of Rs. 37,000 crore for the year stays."),
           q("tax", "We expect the tax rate to be 29% to 30%."),
           q("debt", "Net debt should fall below 1x by March.")]
    before = [q("revenue", "We are revising our revenue growth guidance for the year to 1.5% to 3%."),
              q("margins", "Operating margin guidance remains the same at 20% to 22% for the year."),
              q("capex", "The capex guidance for the year was ₹37,000 crore."),
              q("tax", "We registered a tax rate of 27% this quarter, in line with guidance."),
              q("orders", "We expect the order book to reach ₹50,000 crore.")]
    out = {c["topic"]: c["status"] for c in cc.changes(now, before)}
    # same figure in other words is repeated (the rupee written two ways); a result isn't guidance to compare;
    # a topic on only one call isn't claimed as new or dropped
    assert out == {"revenue": "changed", "margins": "repeated", "capex": "repeated"}
    assert cc.changes(now, before)[0]["topic"] == "revenue"
    assert cc.similarity("revenue guidance for the year", "the year revenue guidance") == 1.0


def test_call_reads_the_two_latest_transcripts(tmp_path):
    lake = Lake(tmp_path).ensure()
    rows = []
    for filed, pages in ((date(2026, 7, 20), [p.replace("15% to 17%", "12% to 14%") for p in CALL]), (DAY, CALL)):
        folder = lake.raw_dir("nse_transcripts", filed)
        name = f"ACME_{filed:%m}.pages.json.gz"
        (folder / name).write_bytes(gzip.compress(json.dumps(pages).encode()))
        rows.append({"symbol": "ACME", "filed": filed, "file": f"{filed.isoformat()}/{name}", "is_call": True,
                     "attachment": f"https://x/{name}.pdf"})
    lake.write_table(pd.DataFrame(rows), "transcripts")
    doc = cc.call(lake, "acme")
    assert doc["filed"] == "2026-10-20" and doc["previous_filed"] == "2026-07-20"
    revenue = next(c for c in doc["changes"] if c["topic"] == "revenue")
    assert revenue["status"] == "changed" and "12% to 14%" in revenue["before"]["text"]
    with pytest.raises(LookupError, match="ingest-transcripts"):
        cc.call(lake, "NOPE")


def test_export_and_api(tmp_path, market):
    from fastapi.testclient import TestClient

    from conftest import ROWS
    from stocksense.api import create_app

    lake = Lake(tmp_path).ensure()
    symbol = ROWS[0]["symbol"]
    folder = lake.raw_dir("nse_transcripts", DAY)
    (folder / f"{symbol}_1.pages.json.gz").write_bytes(gzip.compress(json.dumps(CALL).encode()))
    lake.write_table(pd.DataFrame([{"symbol": symbol, "filed": DAY, "file": f"{DAY.isoformat()}/{symbol}_1.pages.json.gz",
                                    "is_call": True, "attachment": "https://x/call.pdf"}]), "transcripts")
    doc = cc.write(lake, output=tmp_path / "concalls.json")
    entry = doc["companies"][symbol]
    assert entry["previous_filed"] is None and entry["changes"] == []
    assert set(entry["guidance"][0]) == {"page", "text", "topic"}

    client = TestClient(create_app(market=market, headlines=lambda: [], history=lambda s, r: [], concalls=lambda: doc))
    body = client.get(f"/stocks/{symbol.lower()}/concall").json()
    assert body["source"] == "https://x/call.pdf" and any("15% to 17%" in q["text"] for q in body["guidance"])
    assert client.get(f"/stocks/{symbol}").json()["available"]["concall"] is True
    assert client.get("/stocks/NOPE/concall").status_code == 404


def test_dash_labels_bullets_and_unmarked_questions():
    pages = [" Mr. C.S. Setty – Chairman, State Bank of India:\nWe stick to our guidance of 14% to 15% credit growth "
             "next year. We expect NIM to be at least 3% for the year. Our ROA target of 1% will be maintained next year.\n"
             " Shri Mohit Kumar – ICICI Securities:\nSir, just trying to understand if credit growth will reach 20% "
             "next year. We think margins will be 3.5% next year.\nMr. C.S. Setty – Chairman, State Bank of India: "
             "We will deliver 14% growth next year, as guided."]
    sents = cc.sentences(pages)
    assert {s.speaker for s in sents} == {"Mr. C.S. Setty", "Shri Mohit Kumar (ICICI Securities)"}
    assert cc.management(sents) == {"Mr. C.S. Setty"}
    texts = [q.text for q in cc.guidance(pages, DAY)]
    assert texts and not any("20%" in t or "3.5%" in t for t in texts)  # the analyst's figures
    assert cc.BULLETS.sub("", "• Revenue grew 18%.") == "Revenue grew 18%."
    assert cc.ASKING.search("Sir, given the repo hike, what is the sensitivity of our cost of funds.")


def test_changes_moved_ranges_revisions_and_reaffirmed_outlooks():
    def q(topic, text):
        return cc.Quote(1, text, topic, cc._numbers(text), 3.0)

    pairs = {
        # a range that moved at one end
        "costs": ("Our cost-to-income ratio guidance will remain in the range of 47% to 48% for the year.",
                  "We expect our cost-to-income guidance to be around 45% to 47% for the year."),
        # a stated revision, though the old figure appears again
        "revenue": ("Our revenue growth guidance for the year is 25%.",
                    "I would like to revise our revenue growth guidance for the year from 25% to around 30%."),
        # reaffirmed, quoted with an extra figure
        "margins": ("We reiterate our FY28 outlook of $400 million revenue and EBITDA margins of 40%.",
                    "We are reaffirming our FY28 outlook of $400 million revenue and $160 million EBITDA."),
        # the same figures written differently
        "capex": ("We expect to spend between INR200 crores to INR225 crores in capex for FY27.",
                  "Our capex guidance for FY27 also remains the same between INR200 crores-225 crores."),
    }
    out = {c["topic"]: c["status"] for c in cc.changes([q(t, now) for t, (_, now) in pairs.items()],
                                                       [q(t, before) for t, (before, _) in pairs.items()])}
    assert out == {"costs": "changed", "revenue": "changed", "margins": "repeated", "capex": "repeated"}
    assert cc._values(q("capex", "INR200 crores-225 crores")) == {200.0, 225.0}
    assert cc.sentences(["The capex is 4. 9% of revenue this quarter, below guidance."])[0].text.startswith("The capex is 4.9%")


def test_market_figures_are_not_the_companys():
    pages = ["Ravi Kumar: Global refinery runs fell to 79% and outages are likely to support margins next year.\n"
             "Government capital expenditure will grow 15% next year.\n"
             "We expect our EBITDA margin to be 20% next year, as the industry recovers.\n"
             "Ravi Kumar: Revenue grew 18% this quarter."] * 2
    texts = [q.text for q in cc.guidance(pages, DAY)]
    assert any("our EBITDA margin to be 20%" in t for t in texts)  # names the industry, but it's about us
    assert not any("refinery" in t or "Government" in t for t in texts)
