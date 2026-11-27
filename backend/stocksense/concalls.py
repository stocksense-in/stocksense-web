"""
What management said on an earnings call, quoted with page numbers (M3.6, the CPU half).

Reads the transcripts `ingest-transcripts` collected and picks out, without a language model:

  • highlights — sentences from management's prepared remarks that state a result with a number
  • guidance   — forward-looking sentences with a number (growth, margins, capex, loans, orders…),
                 from management, never the analysts' questions
  • changes    — for each topic, this call's guidance beside the previous call's: new, dropped,
                 repeated (same numbers) or changed

Everything is a quote from the company's own filing with its page, so a reader can check it. A local
LLM (M3.6 proper, on the GPU) will write the summaries; this is what it gets measured against.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

from .config import DATA_DIR

PAGE_LINE = re.compile(r"^\s*(page\s*\d+\s*(of\s*\d+)?|\d+)\s*$", re.I)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(₹$])")
# A speaker's turn starts with their name: "Samir Seksaria: Thank you" (TCS, HDFC Bank), the name alone on
# a line (Infosys), or the name with the time stamps of the recording (Reliance: "Sh V Srikanth 00:00:01 – …").
_NAME = r"(?:(?:Sh|Smt|Shri|Mr|Ms|Mrs|Dr)\.?\s+)?([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,4})"
SPEAKER_COLON = re.compile(rf"^{_NAME}\s*:\s*(.*)$")
SPEAKER_ROLE = re.compile(r"^(?:Company Speaker|Speaker|Management)\s*\(([^)]{3,40})\)\s*(.*)$")  # Reliance's Q&A
# Bullets PDFs put before lines, including private-use glyphs (Power Grid's U+F02D)
BULLETS = re.compile(r"^[\s\ue000-\uf8ff\u2022\u25aa\u25cf\u25e6\u2023\u2013\-]+(?=\S)")
COPYRIGHT = re.compile(r"(?:External Document\s*)?©\s*\d{4}\s+[^.]{0,60}?(?:Limited|Ltd\.?)\s*\d*\s*")
SPEAKER_LINE = re.compile(rf"^{_NAME}(?:\s+\d{{1,2}}:\d{{2}}(?::\d{{2}})?\b.*)?$")
NOT_NAMES = re.compile(r"^(sub|subject|ref|encl|copy to|regd|scrip code|trading symbol|dear|date|page|note|"
                       r"corporate participants|call participants|transcript|presentation|disclaimer|q\d|fy)\b", re.I)
HOSTS = re.compile(r"^(moderator|operator|coordinator|host)$", re.I)
# An analyst's turn, often mid-line: "Shri Mohit Kumar – ICICI Securities:" or "Anand – Nuvama:"
ANALYST_LABEL = re.compile(r"(?:^|(?<=[.?!]\s))((?:Shri|Mr\.?|Ms\.?)?\s?[A-Z][\w.']*(?:\s+[A-Z][\w.']*){0,3})\s+[–-]\s+"
                           r"([A-Z][\w&.,' ]{1,70}?)\s*:(?:\s|$)")
# ...and the same style for the company's own people: "Mr. C.S. Setty – Chairman, State Bank of India:"
COMPANY_ROLE = re.compile(r"\b(chairman|chairperson|managing director|\bmd\b|ceo|cfo|coo|chief|director|president|"
                          r"head|officer|founder|executive|whole[- ]time|general manager|treasurer|secretary)\b", re.I)
# Questions that don't end with a question mark
ASKING = re.compile(r"^(sir|madam|ma'am)\b|\b(just trying to understand|wanted to understand|want to understand|"
                    r"can you (please )?(help|share|give|tell|throw)|could you|would you|if you could|any colou?r on)\b", re.I)
# The moderator names each questioner: "the next question is from the line of Vibhor Singhal from Nuvama"
ANALYST_INTRO = re.compile(r"(?:line of|question (?:is |comes )?from)\s+(?:Mr\.?|Ms\.?|Mrs\.?)?\s*"
                           r"([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,3})")
# Letterheads and cover letters: lines that look like names but aren't people
NOT_PEOPLE = re.compile(r"\b(limited|ltd|exchange|email|e-mail|website|secretary|officer|membership|tel|fax|"
                        r"conference|call|india|bank|company|participants?|management|speaker|duration|audio|scrip|code|nse|bse|office|plays)\b", re.I)
QA_START = re.compile(r"\b(first question|question[- ]and[- ]answer session|q\s?&\s?a session|"
                      r"open the (floor|line) for questions|begin the question)\b", re.I)

QUANT = re.compile(
    r"(\d+(?:\.\d+)?\s?(?:%|per\s?cent\b|bps\b|basis points|x\b))"
    r"|((?:\b(?:rs\.?|inr|usd|us\$)|[₹$])\s?\d[\d,]*(?:\.\d+)?)"
    r"|(\b\d[\d,]*(?:\.\d+)?\s?(?:crores?|cr\b|billion|bn\b|million|mn\b|lakh|tonnes|mtpa\b|gw\b|mw\b))", re.I)
FORWARD = re.compile(
    r"\b(expect(?:s|ed|ing)?|guidance|guid(?:e|ing)|outlook|target(?:s|ing)?|aim(?:s|ing)?|anticipat\w+|"
    r"plan(?:s|ning)? to|going forward|in the coming|next (?:year|quarter|few|financial year|fiscal)|over the next|"
    r"will (?:be|grow|continue|remain|reach|deliver|add|invest|spend)|should (?:be|grow|remain|see)|"
    r"likely to|on track|by the end of)\b", re.I)
FISCAL = re.compile(r"\bFY\s?'?(\d{2}|\d{4})\b", re.I)
PAST = re.compile(r"\b(was|were|grew|rose|fell|declined|reported|stood at|came in|delivered|registered|increased|"
                  r"decreased|improved|recorded|achieved)\b", re.I)
SMALL_TALK = re.compile(r"\b(thank you|thanks|good (morning|afternoon|evening)|welcome|ladies and gentlemen|"
                        r"over to you|safe harbor|forward-looking statements?|disclaimer|recording|hand over)\b", re.I)

TOPICS = {
    "revenue": r"revenue|sales|top ?line|turnover|business growth|growth rate|double[- ]digit growth",
    "margins": r"margins?|ebitda|ebit\b|operating profit|profitability",
    "loans": r"loans?|advances|credit growth|disbursements?|\baum\b|book growth",
    "deposits": r"deposits?|casa",
    "asset quality": r"credit cost|\bnpa|slippages?|gnpa|nnpa|provisions?",
    "interest margin": r"\bnim\b|net interest margin|spreads?|cost of funds",
    "orders": r"order (?:book|inflow|backlog|pipeline)|deal wins?|\btcv\b|pipeline",
    "capex": r"capex|capital expenditure|capacity|expansion|new plant",
    "volumes": r"volumes?|tonnage|units sold|throughput",
    "debt": r"\bdebt\b|leverage|net cash|borrowings?",
    "costs": r"costs?|expenses|wage|salary hikes?|attrition",
    "tax": r"tax rate",
    "payout": r"dividend|payout|buyback",
}
TOPIC_RES = {name: re.compile(rf"\b(?:{pattern})", re.I) for name, pattern in TOPICS.items()}
MAX_PER_TOPIC = 2
MAX_GUIDANCE = 10
MAX_HIGHLIGHTS = 6


@dataclass
class Quote:
    page: int
    text: str
    topic: str | None = None
    numbers: tuple[str, ...] = ()
    score: float = 0.0


def fiscal_year(day: date) -> int:
    """India's fiscal year a day falls in (FY27 runs April 2026 to March 2027)."""
    return day.year + 1 if day.month >= 4 else day.year


def _clean_lines(pages: list[str]) -> list[list[str]]:
    """Each page's lines without running headers and footers (on a third or more of pages) or page numbers."""
    lines = [[BULLETS.sub("", ln).strip() for ln in p.splitlines()] for p in pages]
    counts = Counter(ln for page in lines for ln in set(page) if ln)
    repeated = {ln for ln, n in counts.items() if len(pages) >= 4 and n >= max(3, len(pages) / 3)
                and _speaker(ln)[0] is None and not ANALYST_LABEL.search(ln + " ")}  # people who speak on many pages aren't running headers
    return [[ln for ln in page if ln and ln not in repeated and not PAGE_LINE.match(ln)] for page in lines]


def _person(name: str) -> bool:
    """A person's name or a host, not a letterhead line ("BSE LIMITED", "Email", "October")."""
    words = name.split()
    if HOSTS.match(name):
        return True
    return 2 <= len(words) <= 5 and not NOT_PEOPLE.search(name) and not (name.isupper() and len(name) > 3)


def _speaker(line: str) -> tuple[str | None, str]:
    """(speaker, rest of the line) when a line starts a turn, else (None, line)."""
    m = SPEAKER_ROLE.match(line)
    if m:
        return m.group(1).strip(), m.group(2)
    if len(line) <= 60 and not NOT_NAMES.match(line):
        m = SPEAKER_LINE.match(line)
        if m and not line.endswith((".", ",")) and _person(m.group(1).strip()):
            return m.group(1).strip(), ""
    m = SPEAKER_COLON.match(line)
    if m and not NOT_NAMES.match(line) and _person(m.group(1).strip()):
        return m.group(1).strip(), m.group(2)
    return None, line


@dataclass
class Line:
    page: int
    speaker: str | None
    text: str


def sentences(pages: list[str]) -> list[Line]:
    """Every sentence with its page (from 1) and speaker (None before the first name)."""
    chunks: list[Line] = []
    speaker = None

    def add(n: int, who: str | None, text: str) -> None:
        if not text:
            return
        if chunks and chunks[-1].page == n and chunks[-1].speaker == who:
            chunks[-1].text += " " + text
        else:
            chunks.append(Line(n, who, text))

    for n, page in enumerate(_clean_lines(pages), 1):
        for line in page:
            who, rest = _speaker(line)
            if who:
                speaker = who
            # an analyst's label inside the line: what follows is theirs
            while m := ANALYST_LABEL.search(rest):
                add(n, speaker, rest[:m.start()].strip())
                name, affiliation = m.group(1).strip(), m.group(2).strip()
                # the company's people keep their name; anyone else is marked by their firm
                speaker = name if COMPANY_ROLE.search(affiliation) else f"{name} ({affiliation})"
                rest = rest[m.end():]
            add(n, speaker, rest)
    out = []
    for c in chunks:
        text = re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1-\2", COPYRIGHT.sub(" ", c.text)))
        for s in SENTENCE_END.split(text):
            s = s.strip(" -•")
            if 25 <= len(s) <= 600:
                out.append(Line(c.page, c.speaker, s))
    return out


# The agenda mentions Q&A before it starts: "…an overview, followed by a Q&A session"
AGENDA = re.compile(r"followed by|will (?:then )?(?:open|begin|have|take)|after (?:the|this|their|our)|post the|"
                    r"overview|opening remarks|later in the call|\d{1,2}:\d{2}:\d{2}", re.I)  # or a timed contents list
REMARKS_BEFORE_QA = 3  # sentences from the company before a Q&A marker counts (the host's welcome mentions Q&A too)


def qa_start(sents: list[Line]) -> int:
    """Index where the questions begin; the end when the call has no Q&A marker. The host's opening
    ("…a chance to ask questions after the presentation") doesn't count: management must have spoken."""
    spoken = 0
    floor = max(REMARKS_BEFORE_QA, len(sents) // 20)
    for i, s in enumerate(sents):
        if s.speaker and not HOSTS.match(s.speaker):
            spoken += 1
        if QA_START.search(s.text) and not AGENDA.search(s.text) and (spoken >= REMARKS_BEFORE_QA or (spoken == 0 and i >= floor)):
            return i
    return len(sents)


def management(sents: list[Line]) -> set[str] | None:
    """Who speaks for the company: everyone named in the prepared remarks, plus anyone who mostly
    answers rather than asks. None when the transcript names no speakers."""
    named = [s for s in sents if s.speaker and not HOSTS.match(s.speaker)]
    if not named:
        return None
    analysts = {s.speaker for s in named if s.speaker.endswith(")") and "(" in s.speaker}
    start = qa_start(sents)
    asked, said = Counter(), Counter()
    for s in named:
        said[s.speaker] += 1
        asked[s.speaker] += s.text.endswith("?")
    introduced = {m.group(1) for s in sents if s.speaker and HOSTS.match(s.speaker)
                  for m in ANALYST_INTRO.finditer(s.text)}
    # in the prepared remarks and not asking (a press conference before the call has journalists' questions)
    team = {s.speaker for s in sents[:start] if s.speaker in said and asked[s.speaker] / said[s.speaker] < 0.3}
    team |= {who for who, n in said.items() if n >= 15 and asked[who] / n < 0.1}
    return {who for who in team if said[who] >= 3 and who not in analysts
            and not any(_same_person(who, a) for a in introduced)}


def _same_person(a: str, b: str) -> bool:
    """'Vibhor Singhal' and 'Vibhor Singhal from Nuvama' (the intro runs on), or a surname match."""
    wa, wb = a.lower().split(), b.lower().split()
    return wa == wb[: len(wa)] or (len(wa) >= 2 and len(wb) >= 2 and wa[-1] in wb and wa[0] in wb)


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(re.sub(r"\s+", "", m.group(0)).lower() for m in QUANT.finditer(text))


def _topic(text: str) -> str | None:
    hits = [(m.start(), name) for name, rx in TOPIC_RES.items() for m in [rx.search(text)] if m]
    return min(hits)[1] if hits else None


def _forward_score(text: str, call_day: date) -> float:
    score = 1.5 * len(FORWARD.findall(text))
    years = [int(y) % 100 for y in FISCAL.findall(text)]
    current = fiscal_year(call_day) % 100
    if any(y > current for y in years):
        score += 2.0  # a later fiscal year: plainly about the future
    elif any(y == current for y in years) and FORWARD.search(text):
        score += 1.0
    if PAST.search(text) and not FORWARD.search(text):
        score -= 3.0
    return score


def _from_company(sents: list[Line]) -> list[tuple[int, Line]]:
    """(index, sentence) for what the company's people said: named management where the transcript
    names speakers (plus unlabelled prepared remarks: SBI's chairman reads his without a name), else
    every statement that isn't a question."""
    team = management(sents)
    start = qa_start(sents)
    out = []
    for i, s in enumerate(sents):
        if s.text.endswith("?") or SMALL_TALK.search(s.text) or ASKING.search(s.text):
            continue
        if team is not None and s.speaker not in team and not (s.speaker is None and i < start):
            continue
        out.append((i, s))
    return out


def guidance(pages: list[str], call_day: date) -> list[Quote]:
    """Management's forward-looking statements with a number, at most two per topic, best first."""
    sents = sentences(pages)
    picked: list[Quote] = []
    for _, s in _from_company(sents):
        numbers, topic = _numbers(s.text), _topic(s.text)
        if not numbers or not topic:
            continue
        score = _forward_score(s.text, call_day)
        if score >= 1.5:
            picked.append(Quote(s.page, s.text, topic, numbers, score + 0.5 * min(len(numbers), 3)))
    picked.sort(key=lambda q: (-q.score, q.page))
    out, per_topic, said = [], Counter(), set()
    for q in picked:  # the same figure repeated (press conference, then analysts' call) counts once
        if per_topic[q.topic] < MAX_PER_TOPIC and (q.topic, frozenset(q.numbers)) not in said:
            out.append(q)
            per_topic[q.topic] += 1
            said.add((q.topic, frozenset(q.numbers)))
    return out[:MAX_GUIDANCE]


def highlights(pages: list[str], call_day: date) -> list[Quote]:
    """Results management stated in its prepared remarks: sentences with numbers, one per topic first."""
    sents = sentences(pages)
    start = qa_start(sents)
    picked = []
    for i, s in _from_company(sents):
        if i >= start:
            break
        numbers, topic = _numbers(s.text), _topic(s.text)
        if not numbers or not topic or _forward_score(s.text, call_day) >= 1.5:
            continue  # forward-looking lines belong to guidance
        picked.append(Quote(s.page, s.text, topic, numbers, min(len(numbers), 3) + (1.0 if PAST.search(s.text) else 0.0)))
    picked.sort(key=lambda q: (-q.score, q.page))
    out, seen = [], set()
    for q in picked:  # breadth first: the best sentence for each topic, then the rest
        if q.topic not in seen:
            out.append(q)
            seen.add(q.topic)
    out += [q for q in picked if q not in out]
    return sorted(out[:MAX_HIGHLIGHTS], key=lambda q: q.page)


def changes(latest: list[Quote], previous: list[Quote]) -> list[dict]:
    """Per topic, this call's best guidance beside the previous call's."""
    def best(quotes: list[Quote]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for q in quotes:
            if q.topic not in out or q.score > out[q.topic].score:
                out[q.topic] = q
        return out

    best_now, best_then = best(latest), best(previous)
    out = []
    for topic in dict.fromkeys(list(best_now) + list(best_then)):
        now, then = best_now.get(topic), best_then.get(topic)
        if now and not then:
            status = "new"
        elif then and not now:
            status = "dropped"
        elif set(now.numbers) == set(then.numbers):
            status = "repeated"
        else:
            status = "changed"
        out.append({"topic": topic, "status": status, "now": asdict(now) if now else None,
                    "before": asdict(then) if then else None})
    order = {"changed": 0, "new": 1, "repeated": 2, "dropped": 3}
    return sorted(out, key=lambda c: order[c["status"]])


def call(lake, symbol: str) -> dict:
    """The latest call's highlights and guidance, and how the guidance moved since the call before.
    Raises LookupError without a transcript."""
    from .jobs import ingest_transcripts

    rows = lake.query("select filed, file, attachment from transcripts where symbol = ? and is_call order by filed desc",
                      [symbol.upper()]) if "transcripts" in set(lake.datasets()) else None
    if rows is None or rows.empty:
        raise LookupError(f"No call transcript for {symbol.upper()}: run `ingest-transcripts --symbols {symbol.upper()}`")
    calls = []
    for r in rows.head(2).itertuples():
        day = r.filed.date() if hasattr(r.filed, "date") else r.filed
        pages = ingest_transcripts.load_pages(lake.raw / ingest_transcripts.SOURCE / r.file)
        calls.append({"filed": day.isoformat(), "source": r.attachment, "pages": pages, "day": day})
    latest = calls[0]
    now = guidance(latest["pages"], latest["day"])
    before = guidance(calls[1]["pages"], calls[1]["day"]) if len(calls) > 1 else []
    return {"symbol": symbol.upper(), "filed": latest["filed"], "source": latest["source"],
            "previous_filed": calls[1]["filed"] if len(calls) > 1 else None,
            "highlights": [asdict(q) for q in highlights(latest["pages"], latest["day"])],
            "guidance": [asdict(q) for q in now],
            "changes": changes(now, before) if len(calls) > 1 else []}


OUTPUT = DATA_DIR / "concalls.json"


def _short(q: dict | None) -> dict | None:
    return None if q is None else {k: q[k] for k in ("page", "text", "topic") if k in q}


def build(lake, symbols: list[str] | None = None, today: date | None = None) -> dict:
    """Every company with a call transcript: the latest call's quotes and the guidance changes."""
    if "transcripts" not in set(lake.datasets()):
        return {"generated": (today or date.today()).isoformat(), "companies": {}}
    found = lake.query("select distinct symbol from transcripts where is_call order by 1")["symbol"].tolist()
    companies = {}
    for symbol in symbols or found:
        try:
            doc = call(lake, symbol)
        except (LookupError, OSError, ValueError):
            continue
        companies[symbol] = {
            "filed": doc["filed"], "source": doc["source"], "previous_filed": doc["previous_filed"],
            "highlights": [_short(q) for q in doc["highlights"]], "guidance": [_short(q) for q in doc["guidance"]],
            "changes": [{"topic": c["topic"], "status": c["status"], "now": _short(c["now"]),
                         "before": _short(c["before"])} for c in doc["changes"]]}
    return {"generated": (today or date.today()).isoformat(),
            "source": "Earnings-call transcripts the companies filed with NSE", "companies": companies}


def write(lake, output=OUTPUT) -> dict:
    import json

    doc = build(lake)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return doc
