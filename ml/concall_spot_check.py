"""
M3.6 spot check: the latest earnings call of 50 large companies, quoted by `stocksense.concalls`.

    python ml/concall_spot_check.py              # worksheet + scores → ml/reports/concall-spot-check-<date>.md

Two checks:

  • automatic, every quote: the quoted sentence appears on the page it cites (citation accuracy), and
    the speaker is one of the company's people (where the transcript names speakers)
  • by reading, from ml/data/concall_judgements.json: whether each guidance line is really guidance
    (management, forward-looking, a figure) and each highlight a result the company reported. Verdicts
    are keyed by the quote's first 50 characters: "ok" or a short reason it's wrong.

Companies: the 50 largest by market value with a call transcript, so the set doesn't move with the
results. Guidance changes are listed for the companies that have a previous call.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense import concalls as cc  # noqa: E402
from stocksense.jobs import ingest_transcripts  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

JUDGEMENTS = REPO / "ml" / "data" / "concall_judgements.json"
COMPANIES = 50


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9%]", "", text.lower())


def on_page(pages: list[str], quote: dict) -> bool:
    """The quote's text is on the page it cites (ignoring spacing and punctuation the PDF breaks up)."""
    lines = [s.text for s in cc.sentences(pages) if s.page == quote["page"]]
    return _norm(quote["text"]) in _norm(" ".join(lines))


def companies(lake: Lake, n: int = COMPANIES) -> list[str]:
    from stocksense.jobs.ingest_results import top_symbols

    have = set(lake.query("select distinct symbol from transcripts where is_call")["symbol"])
    return [s for s in top_symbols(1000) if s in have][:n]


def check(lake: Lake, symbols: list[str]) -> list[dict]:
    rows = []
    for symbol in symbols:
        doc = cc.call(lake, symbol)
        latest = lake.query("select file from transcripts where symbol = ? and is_call order by filed desc limit 1",
                            [symbol]).iloc[0, 0]
        pages = ingest_transcripts.load_pages(lake.raw / ingest_transcripts.SOURCE / latest)
        team = cc.management(cc.sentences(pages))
        for kind, quotes in (("highlight", doc["highlights"]), ("guidance", doc["guidance"])):
            for i, q in enumerate(quotes):
                rows.append({"symbol": symbol, "filed": doc["filed"], "kind": kind, "n": i, "page": q["page"],
                             "topic": q["topic"], "text": q["text"], "on_page": on_page(pages, q),
                             "named_speakers": team is not None,
                             "changes": doc["changes"] if kind == "guidance" and i == 0 else None})
        if not doc["guidance"]:
            rows.append({"symbol": symbol, "filed": doc["filed"], "kind": "guidance", "n": -1, "page": None,
                         "topic": None, "text": None, "on_page": None, "named_speakers": team is not None,
                         "changes": doc["changes"]})
    return rows


def verdict(judgements: dict, symbol: str, text: str) -> str | None:
    """The reader's verdict on a quote, keyed by the quote's first 50 characters so it survives re-runs."""
    return judgements.get(symbol, {}).get(text[:50])


def report(rows: list[dict], judgements: dict) -> str:
    df = pd.DataFrame(rows)
    quotes = df[df["n"] >= 0].copy()
    quotes["verdict"] = [verdict(judgements, r.symbol, r.text) for r in quotes.itertuples()]
    judged = quotes[quotes["verdict"].notna()]
    companies_n = df["symbol"].nunique()
    no_guidance = df[(df["kind"] == "guidance") & (df["n"] == -1)]["symbol"].tolist()
    lines = [f"# Earnings-call quotes — spot check, {date.today():%d %b %Y}", "",
             f"The latest call of the {companies_n} largest companies with a transcript, quoted by "
             f"`stocksense.concalls` (rules, no language model).", "",
             f"- **Citations:** {int(quotes['on_page'].sum())} of {len(quotes)} quotes appear on the page they cite "
             f"({quotes['on_page'].mean():.0%}).",
             f"- **Speakers named:** {int(df.groupby('symbol')['named_speakers'].first().sum())} of {companies_n} "
             f"transcripts name their speakers, so quotes come only from the company's people; the rest fall back to "
             f"every statement that isn't a question."]
    for kind, label in (("highlight", "reported results"), ("guidance", "guidance")):
        k = judged[judged["kind"] == kind]
        if len(k):
            good = (k["verdict"] == "ok").sum()
            lines.append(f"- **Read and judged, {label}:** {good} of {len(k)} right ({good / len(k):.0%}).")
    lines.append(f"- **No forward-looking figures found:** {len(no_guidance)} companies "
                 f"({', '.join(no_guidance) if no_guidance else 'none'}).")
    wrong = judged[judged["verdict"] != "ok"]
    if len(wrong):
        lines += ["", "## Quotes judged wrong", "", "| Company | Kind | Page | Quote | Why |", "|---|---|---:|---|---|"]
        for r in wrong.itertuples():
            lines.append(f"| {r.symbol} | {r.kind} | {int(r.page)} | {r.text[:160]} | {r.verdict} |")
    lines += ["", "## Every quote", ""]
    for symbol, g in df.groupby("symbol", sort=False):
        lines.append(f"### {symbol} (filed {g['filed'].iloc[0]})")
        for r in g[g["n"] >= 0].itertuples():
            said = verdict(judgements, symbol, r.text) or "not judged"
            mark = "" if r.on_page else " ⚠ not on cited page"
            lines.append(f"- {r.kind} p{int(r.page)} [{r.topic}] {r.text} — *{said}*{mark}")
        changes = next((c for c in g["changes"] if c), None)
        for c in changes or []:
            if c["status"] != "repeated":
                lines.append(f"  - change: {c['topic']} {c['status']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    lake = Lake.from_settings()
    rows = check(lake, companies(lake))
    judgements = json.loads(JUDGEMENTS.read_text(encoding="utf-8")) if JUDGEMENTS.exists() else {}
    out = REPO / "ml" / "reports" / f"concall-spot-check-{date.today():%Y-%m-%d}.md"
    out.write_text(report(rows, judgements), encoding="utf-8")
    print(out.read_text(encoding="utf-8")[:3000])


if __name__ == "__main__":
    main()
