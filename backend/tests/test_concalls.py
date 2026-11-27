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
        "rs4,200", "18%", "120bps", "₹50", "3.2x")
    assert cc._numbers("across the next 2 quarters, we will see volumes grow") == ()  # not "rs," of quarters


def test_changes_compare_each_topic_with_the_previous_call():
    def q(topic, numbers, score=3.0):
        return cc.Quote(1, f"{topic} {numbers}", topic, numbers, score)

    out = cc.changes([q("revenue", ("1%", "2%")), q("margins", ("20%", "22%")), q("tax", ("29%",))],
                     [q("revenue", ("1.5%", "3%")), q("margins", ("20%", "22%")), q("capex", ("rs900",))])
    assert [(c["topic"], c["status"]) for c in out] == [
        ("revenue", "changed"), ("tax", "new"), ("margins", "repeated"), ("capex", "dropped")]
    assert out[0]["before"]["numbers"] == ("1.5%", "3%")


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
