"""
Earnings-call transcripts (M3.5, M3.6) — the PDFs companies file with NSE after each call.

    python -m stocksense ingest-transcripts --top 500            # last 4 calls of the 500 largest
    python -m stocksense ingest-transcripts --symbols TCS INFY --calls 8

  1. Find transcript filings in the announcements already collected (M1.4): the "Transcript of
     Analysts/Institutional Investor Meet/Con. Call" category, or a call update whose summary says
     transcript, with a PDF attached. The latest `calls` per company, one per PDF.
  2. Download each PDF once from NSE's archive, one a second
     (raw/nse_transcripts/<filed>/<SYMBOL>_<seq_id>.pdf).
  3. Extract each page's text once, in parallel (<same name>.pages.json.gz beside the PDF).
  4. Rebuild clean/transcripts: one row per filing with pages, words, and whether the text reads
     like a call (a moderator, questions) rather than a notice that only links to a recording.

Only the companies' own filings are used; the text stays in the lake for search and summaries.
"""

from __future__ import annotations

import gzip
import json
import re
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from .. import rhp
from ..lake import Lake
from ..log import get_logger
from .ingest_results import Breaker, NseUnavailable

log = get_logger(__name__)

SOURCE = "nse_transcripts"
PAUSE_SECONDS = 1.0
REST_SECONDS = 15 * 60
CALLS = 4  # a year of quarterly calls
TRANSCRIPT_CATEGORY = "Transcript of Analysts/Institutional Investor Meet/Con. Call"
MIN_WORDS = 1500  # a call runs to several thousand words; a covering letter with a link, a few hundred
# Words of a call: some transcripts have no moderator (Reliance names each speaker); all have questions.
CALL_WORDS = re.compile(r"\b(moderator|operator|ladies and gentlemen|questions?|participants?|analysts?)\b", re.I)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36", "Accept": "application/pdf,*/*"}


def find(lake: Lake, symbols: list[str], calls: int = CALLS, until: date | None = None) -> pd.DataFrame:
    """The latest `calls` transcript filings per company, newest first."""
    if not symbols:
        return pd.DataFrame(columns=["symbol", "seq_id", "date", "summary", "attachment"])
    until_sql = f"and date <= date '{until.isoformat()}'" if until else ""
    df = lake.query(f"""
        select symbol, seq_id, date, summary, attachment, broadcast_at from announcements
        where symbol in (select unnest(?))
          and (category = '{TRANSCRIPT_CATEGORY}' or lower(summary) like '%transcript%')
          and lower(attachment) like '%.pdf' {until_sql}
        qualify row_number() over (partition by symbol, attachment order by broadcast_at desc) = 1""",
                    [list(symbols)])
    if df.empty:
        return df
    df = df.sort_values(["symbol", "broadcast_at"], ascending=[True, False])
    return df.groupby("symbol").head(calls).drop(columns="broadcast_at").reset_index(drop=True)


def pdf_path(lake: Lake, row) -> Path:
    filed = row["date"] if isinstance(row["date"], date) else pd.Timestamp(row["date"]).date()
    return lake.raw_dir(SOURCE, filed) / f"{row['symbol']}_{row['seq_id']}.pdf"


def download(lake: Lake, rows: pd.DataFrame, pause: float = PAUSE_SECONDS, rests: int = 0,
             rest_seconds: float = REST_SECONDS) -> int:
    """Fetch each PDF not yet saved. A dead link is marked (.missing) so it isn't asked for again."""
    todo = [r for r in rows.to_dict("records")
            if not pdf_path(lake, r).exists() and not pdf_path(lake, r).with_suffix(".missing").exists()]
    got, position = 0, 0
    while True:
        breaker = Breaker()
        try:
            with httpx.Client(headers=HEADERS, timeout=90, follow_redirects=True) as c:
                while position < len(todo):
                    row = todo[position]
                    position += 1
                    got += _download_one(c, lake, row, breaker)
                    time.sleep(pause)
                    if position % 100 == 0:
                        log.info(f"{SOURCE}: {position} of {len(todo)} transcripts tried, {got} saved")
            return got
        except NseUnavailable as exc:
            if rests <= 0:
                log.warning(f"{SOURCE}: stopping — NSE is not responding ({exc}); a later run resumes")
                return got
            rests -= 1
            log.warning(f"{SOURCE}: NSE is not responding ({exc}); resting {rest_seconds / 60:.0f} min ({rests} left)")
            time.sleep(rest_seconds)


def _download_one(c, lake: Lake, row: dict, breaker: Breaker) -> int:
    path = pdf_path(lake, row)
    try:
        resp = c.get(row["attachment"])
        resp.raise_for_status()
        breaker.ok()
    except Exception as exc:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
            path.with_suffix(".missing").write_text(row["attachment"], encoding="utf-8")
        breaker.fail(f"{SOURCE}: {row['symbol']} {row['seq_id']}", exc)
        return 0
    if not resp.content.startswith(b"%PDF-"):
        path.with_suffix(".missing").write_text(f"not a PDF: {row['attachment']}", encoding="utf-8")
        return 0
    part = path.with_suffix(".part")
    part.write_bytes(resp.content)
    part.replace(path)
    return 1


def pages_file(pdf: Path) -> Path:
    return pdf.with_name(pdf.stem + ".pages.json.gz")


def _extract(pdf: str) -> tuple[str, int, str | None]:
    """Worker: one PDF's page text beside it. Returns (pdf, pages, error)."""
    path = Path(pdf)
    try:
        pages = rhp.pdf_pages(path.read_bytes())
    except Exception as exc:  # scanned or damaged: recorded, not retried every run
        path.with_suffix(".error").write_text(str(exc), encoding="utf-8")
        return pdf, 0, str(exc)
    with gzip.open(pages_file(path), "wt", encoding="utf-8") as f:
        json.dump(pages, f)
    return pdf, len(pages), None


def extract(lake: Lake, workers: int = 4) -> int:
    todo = [str(p) for p in sorted((lake.raw / SOURCE).glob("*/*.pdf"))
            if not pages_file(p).exists() and not p.with_suffix(".error").exists()]
    if not todo:
        return 0
    log.info(f"{SOURCE}: extracting text from {len(todo)} transcripts with {workers} workers")
    failed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for _, _, error in pool.map(_extract, todo, chunksize=8):
            failed += error is not None
    log.info(f"{SOURCE}: {len(todo) - failed} extracted, {failed} unreadable (scanned or damaged)")
    return len(todo)


def is_call(pages: list[str]) -> bool:
    """A call transcript, not a covering letter that only links to a recording or a website."""
    text = " ".join(pages)
    return len(text.split()) >= MIN_WORDS and len(CALL_WORDS.findall(text)) >= 3


def load_pages(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def build(lake: Lake) -> pd.DataFrame:
    """Rebuild clean/transcripts from every extracted file, joined to its announcement."""
    rows = []
    for path in sorted((lake.raw / SOURCE).glob("*/*.pages.json.gz")):
        symbol, _, seq_id = path.name[: -len(".pages.json.gz")].rpartition("_")
        try:
            pages = load_pages(path)
        except (OSError, ValueError) as exc:
            log.warning(f"{SOURCE}: could not read {path}: {exc}")
            continue
        rows.append({"symbol": symbol, "seq_id": seq_id, "filed": date.fromisoformat(path.parent.name),
                     "pages": len(pages), "words": sum(len(p.split()) for p in pages), "is_call": is_call(pages),
                     "file": f"{path.parent.name}/{path.name}"})
    df = pd.DataFrame(rows)
    if df.empty:
        log.info(f"{SOURCE}: no transcripts extracted yet")
        return df
    meta = lake.query("select seq_id, attachment, summary from announcements where seq_id in (select unnest(?))",
                      [df["seq_id"].tolist()]).drop_duplicates("seq_id")
    df = df.merge(meta, on="seq_id", how="left").sort_values(["symbol", "filed"]).reset_index(drop=True)
    lake.write_table(df, "transcripts")
    log.info(f"{SOURCE}: {len(df)} filings for {df['symbol'].nunique()} companies; "
             f"{int(df['is_call'].sum())} read as call transcripts")
    return df


def run(symbols: list[str] | None = None, top: int | None = 500, calls: int = CALLS, lake: Lake | None = None,
        rests: int = 0, workers: int = 4) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    if symbols:
        targets = [s.upper() for s in symbols]
    else:
        from .ingest_results import top_symbols

        targets = top_symbols(top or 500)
    rows = find(lake, targets, calls)
    log.info(f"{SOURCE}: {len(rows)} transcript filings for {rows['symbol'].nunique() if len(rows) else 0} of "
             f"{len(targets)} companies (last {calls} each)")
    download(lake, rows, rests=rests)
    extract(lake, workers=workers)
    return build(lake)
