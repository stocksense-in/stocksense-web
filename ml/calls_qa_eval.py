"""
Earnings-call search test (M3.5): can `ask SYMBOL "…" --calls` find the page where management gave guidance?

    python ml/calls_qa_eval.py              # report to ml/reports/calls-qa-<date>.md

Questions come from the guidance lines read and judged right in the M3.6 spot check
(ml/data/concall_judgements.json): one plain question per company and topic ("What margin guidance
did management give?"), the answer being the page of the latest call that line is on. Guidance said
on more than one page counts only on the judged page, so the rates are a floor.

Nothing was tuned on these questions: the search runs with the prospectus settings (BM25, b = 0). The
one choice made from them is how many calls to search by default; the report shows each.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense import concalls, filings_qa  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

JUDGEMENTS = REPO / "ml" / "data" / "concall_judgements.json"
KS = (1, 3, 5)
CALL_COUNTS = (1, 2, 4)
QUESTION = {
    "revenue": "What revenue growth does the company expect this year?",
    "margins": "What margin guidance did management give?",
    "loans": "What loan growth or disbursement target does management expect?",
    "deposits": "What deposit growth does the bank expect?",
    "asset quality": "What credit cost or slippage guidance did management give?",
    "interest margin": "What net interest margin does management expect?",
    "orders": "What order inflow or order book does the company expect?",
    "capex": "How much capex or new capacity does the company plan?",
    "volumes": "What volume growth does the company expect?",
    "debt": "What are the company's plans for debt and borrowing?",
    "costs": "What does management expect for costs?",
    "tax": "What tax rate does the company expect?",
    "payout": "What are the plans for dividends or payouts?",
}


def questions(lake: Lake) -> list[dict]:
    judged = json.loads(JUDGEMENTS.read_text(encoding="utf-8"))
    out, seen = [], set()
    for symbol, verdicts in judged.items():
        if symbol == "changes":
            continue
        try:
            doc = concalls.call(lake, symbol)
        except LookupError:
            continue
        for q in doc["guidance"]:
            key = (symbol, q["topic"])
            # one question per company and topic: the same question can't have two different answers
            if verdicts.get(q["text"][:50]) == "ok" and q["topic"] in QUESTION and key not in seen:
                seen.add(key)
                out.append({"symbol": symbol, "topic": q["topic"], "question": QUESTION[q["topic"]],
                            "filed": doc["filed"], "page": q["page"], "quote": q["text"]})
    return out


def run(lake: Lake, qs: list[dict], calls: int) -> list[dict]:
    rows = []
    for q in qs:
        hits = filings_qa.ask_calls(lake, q["symbol"], q["question"], k=max(KS), calls=calls)
        cited = [(h.document, h.page) for h in hits]
        rows.append({**q, "cited": cited, **{f"hit{k}": (q["filed"], q["page"]) in cited[:k] for k in KS}})
    return rows


def rates(rows: list[dict]) -> dict[int, float]:
    return {k: sum(r[f"hit{k}"] for r in rows) / len(rows) for k in KS}


def report(by_calls: dict[int, list[dict]]) -> str:
    rows = by_calls[filings_qa.CALLS]
    rate = rates(rows)
    lines = [f"# Earnings-call search test — {date.today():%d %b %Y}", "",
             f"{len(rows)} questions about {len({r['symbol'] for r in rows})} companies' latest calls, from guidance "
             "lines judged right in the M3.6 spot check.", "",
             f"**Searching the latest call (the default), the top page is the guidance page for {rate[1]:.0%} of "
             f"questions**, one of the top 3 for {rate[3]:.0%}, the top 5 for {rate[5]:.0%}. These are floors: guidance "
             "said on several pages counts only on the judged one. Searching more calls puts older calls' pages "
             "first, so the default is the latest call (`--last N` searches more).", "",
             "| Calls searched | Hit@1 | Hit@3 | Hit@5 |", "|---:|---:|---:|---:|"]
    for n, r in by_calls.items():
        g = rates(r)
        lines.append(f"| {n} |" + "".join(f" {g[k]:.0%} |" for k in KS))
    lines += ["", "| Topic (latest call) | Questions | Hit@1 | Hit@3 | Hit@5 |", "|---|---:|---:|---:|---:|"]
    for topic in dict.fromkeys(r["topic"] for r in rows):
        g = [r for r in rows if r["topic"] == topic]
        lines.append(f"| {topic} | {len(g)} |" + "".join(f" {sum(r[f'hit{k}'] for r in g) / len(g):.0%} |" for k in KS))
    lines += ["", "Generic questions share few words with the page that answers them; an LLM reading the top pages "
              "(M3.5 proper, on the GPU) is what would close the gap.", "",
              "## Questions the top 5 missed (latest call)", "", "| Company | Question | Guidance (page) | Cited pages |",
              "|---|---|---|---|"]
    for r in rows:
        if not r["hit5"]:
            cited = ", ".join(str(p) for _, p in r["cited"][:5])
            lines.append(f"| {r['symbol']} | {r['question']} | {r['quote'][:100]} (p{r['page']}) | {cited} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    lake = Lake.from_settings()
    qs = questions(lake)
    by_calls = {n: run(lake, qs, n) for n in CALL_COUNTS}
    out = REPO / "ml" / "reports" / f"calls-qa-{date.today():%Y-%m-%d}.md"
    out.write_text(report(by_calls), encoding="utf-8")
    print(out.read_text(encoding="utf-8")[:1800])


if __name__ == "__main__":
    main()
