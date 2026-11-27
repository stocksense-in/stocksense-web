"""
Filings Q&A, the retrieval half (M3.5): find the pages of a company's offer document that answer
a question, so an answer can cite them.

    python -m stocksense ask ZAGGLE "who are the statutory auditors?"

Questions are about one company, so the search picks that company's prospectus first (the text
`ingest-rhp` extracted, raw/sebi_rhp/<filed>/<SYMBOL>.pages.json.gz), then ranks its pages with
BM25. Long pages aren't marked down (b = 0): cover pages and summary tables are long and hold many
answers. Word pairs and a proximity re-rank were tried and didn't help (ml/filings_qa_eval.py).

The company's own name counts half in the question. The document is already chosen, so at full
weight the name pulls in any page that repeats it. But the cover and general-information pages,
which hold many answers, spell the name out where the rest say "our Company", so dropping it
entirely loses those.

Plain-English words are mapped to the prospectus's own terms first ("lawsuits" → litigation,
"set up" → incorporated): a reader asks about "investment banks", the document says "book running
lead managers".

A local LLM reading the top pages and writing the answer with citations is the other half; it waits
for GPU time. Until then, the top page and its snippet are the answer.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SOURCE = "sebi_rhp"
K1, B = 1.2, 0.0  # b and the name weight chosen on the dev set (ml/data/filings_qa_dev.json)
NAME_WEIGHT = 0.5

STOPWORDS = frozenset("""
a an and are as at be been being by can could did do does for from had has have how i if in into is it its
me my no not of on or our so such than that the their them then there these they this those to was we were
what when where which who whom why will with would you your about any all also each other over per s
""".split())

# plain English → the words a prospectus uses for it
GLOSSARY = {
    "ipo": "offer issue",
    "share sale": "offer",
    "investment bank": "book running lead manager",
    "investment banks": "book running lead managers",
    "set up": "incorporated",
    "founded": "incorporated",
    "established": "incorporated",
    "audit firm": "statutory auditors",
    "auditor": "statutory auditor",
    "accounts": "financial statements",
    "lawsuits": "litigation proceedings",
    "court cases": "litigation proceedings",
    "legal cases": "litigation proceedings",
    "criminal cases": "criminal proceedings",
    "debt": "borrowings indebtedness",
    "loans": "borrowings",
    "profit": "profit after tax",
    "sales": "revenue from operations",
    "owners": "promoters shareholding",
    "use the money": "objects of the offer net proceeds",
    "money raised": "net proceeds",
    "competitors": "competition peers",
    "dividends": "dividend policy",
    "allotment": "registrar allotment",
}

_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def _normal(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3 and not word[0].isdigit():
        return word[:-1]
    return word


def terms(text: str) -> list[str]:
    """Words: stopwords dropped, plurals folded, '2,093.71' kept whole."""
    text = re.sub(r"(?<=\d),(?=\d)", "", text.lower().replace("’", "'").replace("'s", ""))
    return [_normal(w) for w in _WORD.findall(text) if w not in STOPWORDS]


def expand(question: str) -> str:
    """The question with the prospectus's words for its plain-English ones added."""
    q = question.lower()
    extra = [v for k, v in GLOSSARY.items() if re.search(rf"\b{re.escape(k)}\b", q)]
    return " ".join([question, *extra])


@dataclass(frozen=True)
class PageHit:
    page: int        # 1-based, as printed in a PDF viewer
    score: float
    snippet: str
    document: str = ""  # which filing, when the search covers several (an earnings call's filing date)
    link: str = ""      # the filing's PDF


def issuer_words(company: str | None) -> frozenset[str]:
    """The company's name as terms ("Dharmaj Crop Guard Limited" → dharmaj, crop, guard)."""
    return frozenset(terms(company or "")) - {"limited", "ltd"}


class PageIndex:
    """BM25 over one document's pages. `company` is the issuer's name, left out of questions."""

    def __init__(self, pages: list[str], company: str | None = None):
        self.pages = pages
        self.issuer = issuer_words(company)
        self.tf = [Counter(terms(p)) for p in pages]
        self.lengths = [sum(c.values()) for c in self.tf]
        self.avg = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(pages)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def query(self, question: str) -> dict[str, float]:
        """Each term of the question with its weight: the company's own name counts NAME_WEIGHT."""
        return {t: (NAME_WEIGHT if t in self.issuer else 1.0) for t in terms(expand(question))}

    def scores(self, question: str) -> list[float]:
        query = self.query(question)
        out = []
        for tf, length in zip(self.tf, self.lengths):
            norm = K1 * (1 - B + B * length / self.avg) if self.avg else K1
            out.append(sum(w * self.idf.get(t, 0.0) * f * (K1 + 1) / (f + norm)
                           for t, w in query.items() if (f := tf.get(t))))
        return out

    def search(self, question: str, k: int = 5) -> list[PageHit]:
        scores = self.scores(question)
        best = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [PageHit(i + 1, round(scores[i], 3), snippet(self.pages[i], question, self.issuer))
                for i in best if scores[i] > 0]


def snippet(page: str, question: str, skip: frozenset[str] = frozenset(), width: int = 320) -> str:
    """The stretch of the page with the most question words in it."""
    text = re.sub(r"\s+", " ", page).strip()
    wanted = set(terms(expand(question))) - skip
    spots = [m.start() for m in _WORD.finditer(text.lower()) if _normal(m.group()) in wanted]
    if not spots:
        return text[:width]
    best = max(spots, key=lambda s: sum(s <= x < s + width for x in spots))
    start = max(0, best - 40)
    return ("…" if start else "") + text[start:start + width] + ("…" if start + width < len(text) else "")


def pages_file(lake, symbol: str) -> Path | None:
    """The latest extracted prospectus for a company, if `ingest-rhp` has one."""
    files = sorted((lake.raw / SOURCE).glob(f"*/{symbol.upper()}.pages.json.gz"))
    return files[-1] if files else None


def company_name(lake, symbol: str) -> str | None:
    """The issuer's name as SEBI lists it (clean/ipo_prospectus, written by `ingest-rhp`)."""
    try:
        rows = lake.query("select company from ipo_prospectus where symbol = ? limit 1", [symbol.upper()])
    except Exception:  # no scan yet: search with the name left in
        return None
    return rows["company"].iloc[0] if len(rows) else None


@lru_cache(maxsize=8)
def _index(path: str, company: str | None = None) -> PageIndex:
    return PageIndex(json.loads(gzip.decompress(Path(path).read_bytes())), company)


CALLS = 4  # earnings calls searched: about a year


def ask_calls(lake, symbol: str, question: str, k: int = 5, calls: int = CALLS) -> list[PageHit]:
    """The pages of the company's latest earnings-call transcripts most likely to answer the question,
    each with its call's filing date and PDF. Uses what `ingest-transcripts` collected."""
    from .jobs import ingest_transcripts

    rows = (lake.query("select filed, file, attachment from transcripts where symbol = ? and is_call "
                       "order by filed desc limit ?", [symbol.upper(), calls])
            if "transcripts" in set(lake.datasets()) else None)
    if rows is None or rows.empty:
        raise LookupError(f"no call transcripts for {symbol}: run `python -m stocksense ingest-transcripts` first")
    pages, where = [], []
    for r in rows.itertuples():
        doc = ingest_transcripts.load_pages(lake.raw / ingest_transcripts.SOURCE / r.file)
        filed = str(r.filed)[:10]
        pages += doc
        where += [(filed, n, r.attachment) for n in range(1, len(doc) + 1)]
    index = PageIndex(pages)
    return [PageHit(where[h.page - 1][1], h.score, h.snippet, where[h.page - 1][0], where[h.page - 1][2])
            for h in index.search(question, k)]


def ask(lake, symbol: str, question: str, k: int = 5) -> list[PageHit]:
    """The pages of the company's prospectus most likely to answer the question (best first)."""
    path = pages_file(lake, symbol)
    if path is None:
        raise LookupError(f"no prospectus text for {symbol}: run `python -m stocksense ingest-rhp` first")
    return _index(str(path), company_name(lake, symbol)).search(question, k)
