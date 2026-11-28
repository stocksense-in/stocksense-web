"""
Prospectus study data (M3.7): every mainboard IPO's red herring prospectus from SEBI, scanned
with the same rules as the prospectus checker (stocksense/rhp.py), one row per IPO.

    python -m stocksense ingest-rhp                    # list, match, download, extract, scan
    python -m stocksense ingest-rhp --no-download      # rescan what's on disk (after a rule change)

Steps, each resumable:
  1. SEBI's register of red herring documents, newest first, back to `since`
     (raw/sebi_offers/<day>/listing.json).
  2. Match each NSE mainboard IPO (NSE's past-issues list) to its prospectus: same company,
     filed within 120 days before the issue opened. Exact name first, then a close spelling.
     FPOs and partly paid rights issues are left out: they aren't new listings.
  3. Download each prospectus once (raw/sebi_rhp/<filing day>/<SYMBOL>.pdf), one request at a time.
  4. Extract each page's text once, in parallel (<SYMBOL>.pages.json.gz beside the PDF): the
     slow part, so rule changes only rerun step 5.
  5. Scan with rhp.RULES into clean/ipo_prospectus: symbol, dates, issue price, pages, and one
     column per rule holding its severity (high / medium / low, empty when clear).
"""

from __future__ import annotations

import difflib
import gzip
import json
import re
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import httpx
import pandas as pd

from .. import rhp
from ..config import DATA_DIR
from ..lake import Lake, write_atomic
from ..log import get_logger
from ..sources import nse_ipo, sebi_offers

log = get_logger(__name__)

SOURCE = "sebi_rhp"
LISTING_SOURCE = "sebi_offers"
DATASET = "ipo_prospectus"
EXPORT = DATA_DIR / "ipo_prospectus.json"  # served with the IPO page's recent listings
SINCE = date(2015, 6, 1)
FILED_BEFORE_DAYS = 120   # an RHP is filed with the ROC days to weeks before the issue opens
CLOSE_SPELLING = 0.88     # difflib ratio for a fuzzy name match
PAUSE_SECONDS = 2.0       # between requests to SEBI
_NOT_A_NEW_LISTING = re.compile(r"\bFPO\b|follow.?on|rights", re.I)


def _listing_page(c, page: int, pause: float, tries: int = 3):
    """One page of SEBI's register, trying again after a network blip (a DNS failure ended a run on 27 Nov)."""
    for attempt in range(1, tries + 1):
        try:
            return sebi_offers.listing_page(c, page)
        except httpx.TransportError:
            if attempt == tries:
                raise
            time.sleep(max(pause, 1.0) * 5 * attempt)


def fetch_listing(c, since: date = SINCE, pause: float = PAUSE_SECONDS) -> list[dict]:
    rows, page, total = [], 0, None
    while True:
        got, t = _listing_page(c, page, pause)
        total = total or t
        rows += got
        if not got or (total and len(rows) >= total) or got[-1]["date"] < since.isoformat():
            return rows
        page += 1
        time.sleep(pause)


def new_listings(issues: list[dict]) -> list[dict]:
    """NSE mainboard IPOs only: equity, not an FPO or a partly paid rights line (ADANIENPP1)."""
    out = []
    for i in issues:
        name = i.get("company") or i.get("companyName") or ""
        if i.get("securityType") != "Equity" or _NOT_A_NEW_LISTING.search(name) or re.search(r"PP\d*$", i.get("symbol") or ""):
            continue
        out.append(i)
    return out


def match(listing: list[dict], issues: list[dict]) -> list[dict]:
    """[{symbol, company, ipo_start, listing_date, issue_price, filed, title, url}] for every IPO with a prospectus."""
    prospectuses = [r for r in listing if sebi_offers.is_prospectus(r["title"])]
    for r in prospectuses:
        r["key"] = sebi_offers.name_key(sebi_offers.company_of(r["title"]))
        r["day"] = date.fromisoformat(r["date"])
    out = []
    for i in new_listings(issues):
        start = sebi_offers.nse_day(i.get("ipoStartDate"))
        if start is None:
            continue
        window = [r for r in prospectuses if start - timedelta(days=FILED_BEFORE_DAYS) <= r["day"] <= start + timedelta(days=5)]
        key = sebi_offers.name_key(i.get("company") or i.get("companyName") or "")
        same = [r for r in window if r["key"] == key]
        if not same and key:
            scored = sorted(((difflib.SequenceMatcher(None, key, r["key"]).ratio(), r) for r in window),
                            key=lambda x: x[0], reverse=True)
            same = [scored[0][1]] if scored and scored[0][0] >= CLOSE_SPELLING else []
        if not same:
            continue
        best = max(same, key=lambda r: r["day"])  # a refiled RHP: the latest before the issue
        price = pd.to_numeric(str(i.get("issuePrice") or "").strip(), errors="coerce")
        out.append({"symbol": i["symbol"], "company": i.get("company") or i.get("companyName"),
                    "ipo_start": start.isoformat(),
                    "listing_date": (sebi_offers.nse_day(i.get("listingDate")) or start).isoformat(),
                    "issue_price": None if pd.isna(price) else float(price),
                    "filed": best["date"], "title": best["title"], "url": best["url"]})
    return out


def pdf_path(lake: Lake, ipo: dict) -> Path:
    return lake.raw_dir(SOURCE, date.fromisoformat(ipo["filed"])) / f"{ipo['symbol']}.pdf"


DOWNLOAD_TRIES = 3  # SEBI cuts ~1 in 10 large transfers short (27 Nov); a second try usually completes


def _get_whole(c, url: str, pause: float, tries: int = DOWNLOAD_TRIES):
    """GET a PDF, trying again when the server closes the connection mid-file."""
    for attempt in range(1, tries + 1):
        try:
            resp = c.get(url)
            resp.raise_for_status()
            return resp
        except httpx.TransportError:
            if attempt == tries:
                raise
            time.sleep(pause * attempt)


def download(c, lake: Lake, ipos: list[dict], pause: float = PAUSE_SECONDS) -> int:
    got = 0
    for n, ipo in enumerate(ipos, 1):
        path = pdf_path(lake, ipo)
        missing = path.with_suffix(".missing")
        if path.exists() or (missing.exists() and missing.read_text(encoding="utf-8").startswith(f"v{sebi_offers.PDF_FINDER} ")):
            continue
        try:
            page = c.get(ipo["url"])
            page.raise_for_status()
            url = sebi_offers.pdf_url(page.text)
            time.sleep(pause)
            if not url:
                missing.write_text(f"v{sebi_offers.PDF_FINDER} {ipo['url']}", encoding="utf-8")
                log.warning(f"{SOURCE}: {ipo['symbol']}: no PDF on {ipo['url']}")
                continue
            resp = _get_whole(c, url, pause)
        except Exception as exc:  # SEBI hiccup: skip, the next run retries
            log.warning(f"{SOURCE}: {ipo['symbol']}: {exc}")
            time.sleep(pause)
            continue
        part = path.with_suffix(".part")
        part.write_bytes(resp.content)
        part.replace(path)
        got += 1
        log.info(f"{SOURCE}: {n}/{len(ipos)} {ipo['symbol']} — {len(resp.content) / 1e6:.1f} MB")
        time.sleep(pause)
    return got


def _pages_file(pdf: Path) -> Path:
    return pdf.with_name(pdf.stem + ".pages.json.gz")


def _extract(pdf: str) -> tuple[str, int, str | None]:
    """Worker: one PDF's page text to <SYMBOL>.pages.json.gz. Returns (pdf, pages, error)."""
    path = Path(pdf)
    try:
        pages = rhp.pdf_pages(path.read_bytes())
    except Exception as exc:  # scanned, damaged, encrypted: recorded, not retried every run
        path.with_suffix(".error").write_text(str(exc), encoding="utf-8")
        return pdf, 0, str(exc)
    write_atomic(_pages_file(path), gzip.compress(json.dumps(pages).encode("utf-8")))
    return pdf, len(pages), None


def extract(lake: Lake, workers: int = 6) -> int:
    todo = [str(p) for p in sorted((lake.raw / SOURCE).glob("*/*.pdf"))
            if not _pages_file(p).exists() and not p.with_suffix(".error").exists()]
    if not todo:
        return 0
    log.info(f"{SOURCE}: extracting text from {len(todo)} prospectuses with {workers} workers")
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for pdf, pages, error in pool.map(_extract, todo):
            done += 1
            log.info(f"{SOURCE}: {done}/{len(todo)} {Path(pdf).stem} — " + (f"failed: {error}" if error else f"{pages} pages"))
    return done


def litigation_numbers(pages: list[str]) -> dict:
    """The litigation summary table as numbers: cases and amounts against the company, its promoters,
    directors and subsidiaries, and the amount as a share of net worth (None where not found)."""
    table, worth = rhp.litigation_table(pages), rhp.net_worth_crore(pages)
    out = {"lit_table": table is not None, "net_worth_cr": worth, "lit_cases": None, "lit_criminal": None,
           "lit_amount_cr": None, "lit_share": None}
    if table:
        rows = table["rows"]
        out["lit_cases"] = int(sum(r["tax"] + r["civil"] + r["regulatory"] + r["criminal"] for r in rows.values()))
        out["lit_criminal"] = int(rows["company"]["criminal"] + rows.get("promoters", {}).get("criminal", 0))
        out["lit_amount_cr"] = round(sum(r["amount_cr"] for r in rows.values()), 2)
        if worth:
            out["lit_share"] = round(out["lit_amount_cr"] / worth, 4)
    return out


def scan(lake: Lake, ipos: list[dict]) -> pd.DataFrame:
    rows = []
    for ipo in ipos:
        pdf = pdf_path(lake, ipo)
        pages_file = _pages_file(pdf)
        row = {k: ipo[k] for k in ("symbol", "company", "ipo_start", "listing_date", "issue_price", "filed", "url")}
        if not pages_file.exists():
            row["pages"] = 0
            row["error"] = pdf.with_suffix(".error").read_text(encoding="utf-8") if pdf.with_suffix(".error").exists() else "not downloaded"
            rows.append(row)
            continue
        with gzip.open(pages_file, "rt", encoding="utf-8") as f:
            pages = json.load(f)
        result = rhp.scan_pages(pages)
        row["pages"] = result.pages
        row["error"] = None
        for rule in rhp.RULES:
            row[rule.id] = None
        for finding in result.findings:
            row[finding.id] = finding.severity
        row["summaries"] = json.dumps({f.id: f.summary for f in result.findings}, ensure_ascii=False)
        row.update(litigation_numbers(pages))
        rows.append(row)
    df = pd.DataFrame(rows)
    for col in ("ipo_start", "listing_date", "filed"):
        df[col] = pd.to_datetime(df[col])
    lake.write_table(df, DATASET)
    log.info(f"{DATASET}: {int((df['pages'] > 0).sum())} of {len(df)} IPOs scanned")
    return df


def export(df: pd.DataFrame, output: Path = EXPORT) -> dict:
    """Per IPO: the prospectus link and its medium and high findings, for the IPO page."""
    titles = {r.id: r.title for r in rhp.RULES}
    ipos = {}
    for r in df[df["pages"] > 0].to_dict("records"):
        summaries = json.loads(r.get("summaries") or "{}")
        flags = [{"id": rule.id, "title": titles[rule.id], "severity": r[rule.id], "summary": summaries.get(rule.id, "")}
                 for rule in rhp.RULES if r.get(rule.id) in (rhp.HIGH, rhp.MEDIUM)]
        flags.sort(key=lambda f: rhp._ORDER[f["severity"]])
        ipos[r["symbol"]] = {"company": r["company"], "filed": pd.Timestamp(r["filed"]).date().isoformat(),
                             "url": r["url"], "pages": int(r["pages"]), "flags": flags}
    doc = {"generated": date.today().isoformat(), "source": "Red herring prospectuses filed with SEBI, scanned with "
           "StockSense's prospectus checker", "ipos": ipos}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return doc


def run(lake: Lake | None = None, since: date = SINCE, download_new: bool = True, workers: int = 6) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    today = date.today()
    listing_file = lake.raw_dir(LISTING_SOURCE, today) / "listing.json"
    issues_file = lake.raw_dir(LISTING_SOURCE, today) / "nse_past_issues.json"
    if download_new:
        with sebi_offers.client() as c:
            listing = fetch_listing(c, since)
            listing_file.write_text(json.dumps(listing), encoding="utf-8")
            issues = nse_ipo.past_issues()
            issues_file.write_text(json.dumps(issues), encoding="utf-8")
            ipos = match(listing, issues)
            log.info(f"{SOURCE}: {len(ipos)} IPOs matched to a prospectus ({len(new_listings(issues))} new listings on NSE)")
            download(c, lake, ipos)
    else:
        latest = sorted((lake.raw / LISTING_SOURCE).glob("*/listing.json"))[-1].parent
        listing = json.loads((latest / "listing.json").read_text(encoding="utf-8"))
        issues = json.loads((latest / "nse_past_issues.json").read_text(encoding="utf-8"))
        ipos = match(listing, issues)
    extract(lake, workers)
    df = scan(lake, ipos)
    export(df)
    return df
