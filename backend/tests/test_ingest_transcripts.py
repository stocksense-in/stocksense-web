from datetime import date, datetime

import httpx
import pandas as pd

from stocksense.jobs import ingest_transcripts as job
from stocksense.lake import Lake

CALL = ("Moderator: Ladies and gentlemen, good day and welcome to the earnings call. " + "Revenue grew well. " * 800
        + "Moderator: The next question is from the line of a participant.")


def announcements(lake: Lake) -> None:
    rows = [
        # TCS: three calls, one filed twice (same PDF), plus an unrelated board-meeting notice
        ("1", "TCS", job.TRANSCRIPT_CATEGORY, "Transcript", "https://x/TCS_q2.pdf", datetime(2026, 10, 14, 15)),
        ("2", "TCS", job.TRANSCRIPT_CATEGORY, "Transcript", "https://x/TCS_q2.pdf", datetime(2026, 10, 15, 9)),
        ("3", "TCS", "Analysts/Institutional Investor Meet/Con. Call Updates", "Transcript of the earnings call",
         "https://x/TCS_q1.PDF", datetime(2026, 7, 15, 19)),
        ("4", "TCS", job.TRANSCRIPT_CATEGORY, "Transcript", "https://x/TCS_q4.pdf", datetime(2026, 4, 12, 18)),
        ("5", "TCS", "Board Meeting Intimation", "Results on 9 Jan", "https://x/TCS_bm.pdf", datetime(2026, 12, 1, 9)),
        ("6", "INFY", "Analysts/Institutional Investor Meet/Con. Call Updates", "Audio recording of the call",
         "https://x/INFY_audio.pdf", datetime(2026, 10, 20, 9)),
        ("7", "INFY", job.TRANSCRIPT_CATEGORY, "Transcript", "https://x/INFY.zip", datetime(2026, 10, 21, 9)),
    ]
    df = pd.DataFrame(rows, columns=["seq_id", "symbol", "category", "summary", "attachment", "broadcast_at"])
    df["date"] = df["broadcast_at"].dt.date
    lake.write_table(df, "announcements")


def test_find_latest_calls_one_per_pdf(tmp_path):
    lake = Lake(tmp_path).ensure()
    announcements(lake)
    found = job.find(lake, ["TCS", "INFY", "NOPE"], calls=2)
    assert found["seq_id"].tolist() == ["2", "3"]  # newest filing of the repeated PDF, then July; no INFY
    assert job.find(lake, ["TCS"], calls=4)["seq_id"].tolist() == ["2", "3", "4"]
    assert job.find(lake, [], calls=4).empty


def test_is_call_tells_transcripts_from_covering_letters():
    assert job.is_call([CALL[:4000], CALL[4000:]])
    assert not job.is_call(["We enclose the link to the audio recording: https://example.com/call. " * 20])
    assert not job.is_call(["Moderator: welcome. Next question. Participant."])  # too short to be a call


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url):
        self.calls.append(url)
        status, body = self.responses[url]
        return httpx.Response(status, content=body, request=httpx.Request("GET", url))


def test_download_saves_pdfs_marks_dead_links_and_builds(tmp_path, monkeypatch):
    lake = Lake(tmp_path).ensure()
    announcements(lake)
    rows = job.find(lake, ["TCS"], calls=3)
    fake = FakeClient({"https://x/TCS_q2.pdf": (200, b"%PDF-1.7 q2"), "https://x/TCS_q1.PDF": (404, b""),
                       "https://x/TCS_q4.pdf": (200, b"<html>moved</html>")})
    monkeypatch.setattr(job.httpx, "Client", lambda **kw: fake)
    assert job.download(lake, rows, pause=0) == 1
    assert job.pdf_path(lake, rows.iloc[0]).read_bytes() == b"%PDF-1.7 q2"
    assert job.pdf_path(lake, rows.iloc[1]).with_suffix(".missing").exists()  # 404: not asked for again
    assert job.pdf_path(lake, rows.iloc[2]).with_suffix(".missing").exists()  # not a PDF
    assert job.download(lake, rows, pause=0) == 0 and len(fake.calls) == 3

    monkeypatch.setattr(job.rhp, "pdf_pages", lambda data: [CALL])
    job._extract(str(job.pdf_path(lake, rows.iloc[0])))
    built = job.build(lake)
    assert built.to_dict("records")[0] | {"words": 0} == {
        "symbol": "TCS", "seq_id": "2", "filed": date(2026, 10, 15), "pages": 1, "words": 0, "is_call": True,
        "file": "2026-10-15/TCS_2.pages.json.gz", "attachment": "https://x/TCS_q2.pdf", "summary": "Transcript"}
    assert "transcripts" in lake.datasets()
