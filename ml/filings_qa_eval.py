"""
Filings Q&A citation test (M3.5): questions about IPO prospectuses, each with the pages that hold
the answer. A question counts as answered when a cited page is one of those.

    python ml/filings_qa_eval.py            # report to ml/reports/filings-qa-<date>.md

Two sets, from different companies' prospectuses:
  • test (ml/data/filings_qa_questions.json): 50 questions, reported
  • dev  (ml/data/filings_qa_dev.json): 90 questions, where the search's settings were chosen

Six kinds of fact: lead managers, registrar, statutory auditors, incorporation date, net worth and
criminal cases against the company. Each is asked in one of two fixed phrasings: the prospectus's
own words ("who is the registrar to the offer") or plain English ("which firm handles share
allotment and refunds"). Answers were taken from the documents and checked by hand. Gold pages are
every page where the answer appears; for criminal cases, every page that repeats the litigation
summary table or states the company's criminal cases in the litigation chapter.

The plain-English phrasings are the same few templates in both sets, and the glossary was written
knowing them, so plain-English results flatter real readers' questions.

The PLAN's bar is ≥80% of answers citing the right page. Until the LLM runs (it needs the GPU),
"cited" means the top page the search returns (hit@1). Hit@3 and hit@5 show what an LLM reading the
top few pages could reach.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense import filings_qa  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

QUESTIONS = REPO / "ml" / "data" / "filings_qa_questions.json"
DEV = REPO / "ml" / "data" / "filings_qa_dev.json"
KS = (1, 3, 5)
B_GRID = (0.75, 0.5, 0.25, 0.0)
NAME_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)


def run(lake: Lake, questions: list[dict]) -> list[dict]:
    rows = []
    for q in questions:
        cited = [h.page for h in filings_qa.ask(lake, q["symbol"], q["question"], k=max(KS))]
        gold = set(q["gold_pages"])
        rows.append({**q, "cited": cited, **{f"hit{k}": bool(gold & set(cited[:k])) for k in KS}})
    return rows


def rates(rows: list[dict]) -> dict[str, float]:
    return {f"hit{k}": sum(r[f"hit{k}"] for r in rows) / len(rows) for k in KS}


def variant(lake: Lake, questions: list[dict], *, b: float | None = None, glossary: bool = True,
            name_weight: float | None = None) -> dict[str, float]:
    """Hit rates with one setting changed."""
    saved_b, saved_glossary, saved_weight = filings_qa.B, dict(filings_qa.GLOSSARY), filings_qa.NAME_WEIGHT
    try:
        if b is not None:
            filings_qa.B = b
        if not glossary:
            filings_qa.GLOSSARY.clear()
        if name_weight is not None:
            filings_qa.NAME_WEIGHT = name_weight
        filings_qa._index.cache_clear()
        return rates(run(lake, questions))
    finally:
        filings_qa.B, filings_qa.NAME_WEIGHT = saved_b, saved_weight
        filings_qa.GLOSSARY.clear()
        filings_qa.GLOSSARY.update(saved_glossary)
        filings_qa._index.cache_clear()


def pct(x: float) -> str:
    return f"{x:.0%}"


def row(name: str, g: dict[str, float], n: int | None = None) -> str:
    return f"| {name} |" + (f" {n} |" if n is not None else "") + "".join(f" {pct(g[f'hit{k}'])} |" for k in KS)


def report(rows: list[dict], dev_rows: list[dict], variants: dict[str, tuple[dict, dict]], grid: dict) -> str:
    total, dev_total = rates(rows), rates(dev_rows)
    verdict = "meets" if total["hit1"] >= 0.8 else "misses"
    lines = [f"# Filings Q&A citation test — {date.today():%d %b %Y}", "",
             f"{len(rows)} test questions about {len({r['symbol'] for r in rows})} IPO prospectuses "
             f"(`ml/data/filings_qa_questions.json`), answered by `stocksense.filings_qa`: BM25 over the pages of the "
             f"company's prospectus, with the company's name counting half and plain English mapped to "
             f"prospectus terms.", "",
             f"**The top page cites the answer for {pct(total['hit1'])} of questions**, which {verdict} the PLAN's 80% "
             f"bar. One of the top 3 pages does for {pct(total['hit3'])}, and the top 5 for {pct(total['hit5'])}. "
             f"So search alone won't meet the bar; an LLM reading the top 5 pages could. "
             f"(Dev set, {len(dev_rows)} questions about {len({r['symbol'] for r in dev_rows})} other prospectuses: "
             f"{pct(dev_total['hit1'])}, {pct(dev_total['hit3'])}, {pct(dev_total['hit5'])}.)", "",
             "| Test set | Questions | Hit@1 | Hit@3 | Hit@5 |", "|---|---:|---:|---:|---:|", row("All", total, len(rows))]
    for kind in dict.fromkeys(r["kind"] for r in rows):
        group = [r for r in rows if r["kind"] == kind]
        lines.append(row(f"Kind: {kind}", rates(group), len(group)))
    for phrasing in ("prospectus words", "plain English"):
        group = [r for r in rows if r["phrasing"] == phrasing]
        if group:
            lines.append(row(f"Phrasing: {phrasing}", rates(group), len(group)))
    lines += ["", "The plain-English questions reuse a few templates, and the glossary was written knowing them, so "
              "real readers' plain-English questions will do worse than the plain-English row.", "",
              "## What each part adds", "", "| Search | Test hit@1 | @3 | @5 | Dev hit@1 | @3 | @5 |",
              "|---|---:|---:|---:|---:|---:|---:|",
              "| As shipped |" + "".join(f" {pct(total[f'hit{k}'])} |" for k in KS)
              + "".join(f" {pct(dev_total[f'hit{k}'])} |" for k in KS)]
    for name, (test_g, dev_g) in variants.items():
        lines.append(f"| {name} |" + "".join(f" {pct(test_g[f'hit{k}'])} |" for k in KS)
                     + "".join(f" {pct(dev_g[f'hit{k}'])} |" for k in KS))
    lines += ["", "Word pairs (\"registrar offer\") and re-ranking pages where the question's words sit close together "
              "were tried on the dev set and didn't help, so they're not used.", "",
              "## Settings (chosen on the dev set only)", "",
              "BM25's b decides how much long pages are marked down; cover pages and summary tables are long and hold "
              "many answers. The name weight is how much the company's own name counts in the question. Both were "
              f"chosen on the dev set, never on the test questions: b = {filings_qa.B}, name weight "
              f"{filings_qa.NAME_WEIGHT} (the best top-3 rate, and a better top page than dropping the name for a "
              "small loss in the top 5).", "", "| Dev set | Hit@1 | Hit@3 | Hit@5 |", "|---|---:|---:|---:|"]
    lines += [row(name, g) for name, g in grid.items()]
    misses = [r for r in rows if not r["hit1"]]
    if misses:
        lines += ["", "## Test questions the top page missed", "", "| Question | Answer | Answer on pages | Cited |",
                  "|---|---|---|---|"]
        for r in misses:
            gold = ", ".join(map(str, r["gold_pages"][:6])) + (" …" if len(r["gold_pages"]) > 6 else "")
            lines.append(f"| {r['question']} | {r['answer']} | {gold} | {', '.join(map(str, r['cited']))} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    lake = Lake.from_settings()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    dev = json.loads(DEV.read_text(encoding="utf-8"))
    grid = {f"b = {b}": variant(lake, dev, b=b) for b in B_GRID}
    grid |= {f"name weight {w}": variant(lake, dev, name_weight=w) for w in NAME_GRID}
    rows, dev_rows = run(lake, questions), run(lake, dev)
    variants = {"No glossary": (variant(lake, questions, glossary=False), variant(lake, dev, glossary=False)),
                "Company name dropped": (variant(lake, questions, name_weight=0.0), variant(lake, dev, name_weight=0.0)),
                "Company name at full weight": (variant(lake, questions, name_weight=1.0), variant(lake, dev, name_weight=1.0))}
    out = REPO / "ml" / "reports" / f"filings-qa-{date.today():%Y-%m-%d}.md"
    out.write_text(report(rows, dev_rows, variants, grid), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
