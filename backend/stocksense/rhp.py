"""
Prospectus (DRHP / RHP) scanner — finds the risk disclosures new investors most
often miss, and quotes the page each finding came from so it can be checked.

Pattern-based, not AI: every rule is a readable regular expression over the
prospectus text. It can miss risks that are worded unusually; it never replaces
reading the "Risk Factors" chapter.

    from stocksense.rhp import scan_pdf
    result = scan_pdf(open("drhp.pdf", "rb").read())
"""

from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass, field
from typing import Callable

HIGH, MEDIUM, LOW = "high", "medium", "low"
_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2}
MAX_EVIDENCE = 3


class ScanError(ValueError):
    """The file can't be scanned; the message is safe to show to a user."""


@dataclass
class Evidence:
    page: int  # 1-based
    quote: str


@dataclass
class Finding:
    id: str
    title: str
    severity: str
    summary: str
    why: str
    evidence: list[Evidence]


@dataclass
class ScanResult:
    pages: int
    findings: list[Finding] = field(default_factory=list)
    clear: list[dict] = field(default_factory=list)  # rules that ran and found nothing

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Hit:
    page: int
    match: re.Match
    quote: str


def _find(pages: list[str], pattern: str, limit: int = 50) -> list[_Hit]:
    """Every match with ~220 characters of context and its page number."""
    regex = re.compile(pattern, re.IGNORECASE)
    hits: list[_Hit] = []
    for number, text in enumerate(pages, start=1):
        for match in regex.finditer(text):
            if len(hits) >= limit:
                return hits
            start, end = max(0, match.start() - 80), min(len(text), match.end() + 140)
            quote = re.sub(r"\s+", " ", text[start:end]).strip()
            hits.append(_Hit(number, match, ("…" if start else "") + quote + ("…" if end < len(text) else "")))
    return hits


def _evidence(hits: list[_Hit]) -> list[Evidence]:
    """Up to three distinct quotes (the same sentence often matches more than once)."""
    seen: set[str] = set()
    out: list[Evidence] = []
    for h in hits:
        key = f"{h.page}:{h.quote[:120]}"
        if key not in seen:
            seen.add(key)
            out.append(Evidence(h.page, h.quote))
        if len(out) == MAX_EVIDENCE:
            break
    return out


def _places(hits: list[_Hit]) -> str:
    n = len({h.page for h in hits})
    return "on 1 page" if n == 1 else f"on {n} pages"


_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "five": 5, "ten": 10, "twenty": 20}
MONEY = r"(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d+)?)\s?(crores?|million|lakhs?|billion)"


def _crore(amount: str, unit: str) -> float:
    """'₹ 1,234.5 crore' / 'Rs. 120 million' → value in ₹ crore."""
    n = float(amount.replace(",", ""))
    unit = unit.lower()
    if unit.startswith("million"):
        return n / 10
    if unit.startswith("lakh"):
        return n / 100
    if unit.startswith("billion"):
        return n * 100
    return n


def _inr(crore: float) -> str:
    return f"₹{round(crore):,} crore"


# ── Rules ────────────────────────────────────────────────────────────────────
# Each rule returns (severity, summary, hits) or None.

RuleResult = tuple[str, str, list[_Hit]] | None


def _customer_concentration(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"top\s+(\d+|one|five|ten|twenty)\s+customers?[^.%]{0,220}?(\d{1,3}(?:\.\d+)?)\s?%")
    if not hits:
        return None
    worst = max(hits, key=lambda h: float(h.match.group(2)))
    pct = float(worst.match.group(2))
    n = _WORD_NUMBERS.get(worst.match.group(1).lower(), worst.match.group(1))
    severity = HIGH if pct >= 50 else MEDIUM if pct >= 25 else LOW
    return severity, f"The top {n} customers account for about {pct:g}% of revenue.", [worst, *[h for h in hits if h is not worst]]


def _supplier_concentration(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"top\s+(\d+|one|five|ten|twenty)\s+suppliers?[^.%]{0,220}?(\d{1,3}(?:\.\d+)?)\s?%")
    if not hits:
        return None
    pct = max(float(h.match.group(2)) for h in hits)
    if pct < 30:
        return None
    return (HIGH if pct >= 60 else MEDIUM), f"The largest suppliers provide about {pct:g}% of purchases.", hits


def _criminal_proceedings(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"criminal\s+(?:proceedings?|cases?|complaints?)[^.]{0,160}?(?:against|involving)\s+(?:our\s+)?(?:company|promoters?|directors?)")
    return (HIGH, f"Criminal proceedings are disclosed {_places(hits)}.", hits) if hits else None


def _litigation(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"(?:outstanding|pending)\s+(?:legal\s+)?(?:litigations?|proceedings|tax\s+proceedings)")
    if not hits:
        return None
    amounts = _find(pages, rf"(?:litigation|proceedings|claims?)[^.]{{0,120}}?aggregat\w*[^.]{{0,40}}?{MONEY}")
    total = sum(_crore(h.match.group(1), h.match.group(2)) for h in amounts)
    if total > 0:
        return (HIGH if total > 100 else MEDIUM), f"Pending cases are disclosed, with amounts adding up to about {_inr(total)}.", amounts
    return MEDIUM, f"Pending legal or tax proceedings are disclosed {_places(hits)}.", hits


def _offer_for_sale(pages: list[str]) -> RuleResult:
    fresh = _find(pages, rf"fresh\s+issue\s+of[^.]{{0,120}}?{MONEY}", limit=5)
    ofs = _find(pages, rf"offer\s+for\s+sale\s+of[^.]{{0,160}}?{MONEY}", limit=5)
    if not ofs:
        return None
    ofs_cr = _crore(ofs[0].match.group(1), ofs[0].match.group(2))
    fresh_cr = _crore(fresh[0].match.group(1), fresh[0].match.group(2)) if fresh else 0.0
    share = ofs_cr / (ofs_cr + fresh_cr)
    if share < 0.5:
        return None
    return (
        HIGH if share >= 0.8 else MEDIUM,
        f"About {round(share * 100)}% of the issue ({_inr(ofs_cr)}) is an offer for sale by existing shareholders.",
        ofs + fresh,
    )


def _general_corporate_purposes(pages: list[str]) -> RuleResult:
    hits = _find(pages, rf"general\s+corporate\s+purposes[^.]{{0,120}}?{MONEY}") + _find(
        pages, rf"{MONEY}[^.]{{0,60}}?(?:towards|for)\s+general\s+corporate\s+purposes"
    )
    if not hits:
        return None
    amount = max(_crore(h.match.group(1), h.match.group(2)) for h in hits)
    return LOW, f"Up to about {_inr(amount)} is set aside for general corporate purposes.", hits


def _losses(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"(?:have|has)\s+(?:in\s+the\s+past\s+)?incurred\s+(?:net\s+)?losses|restated\s+(?:net\s+)?loss\s+(?:for|of)")
    return (MEDIUM, "The prospectus discloses losses in recent years.", hits) if hits else None


def _negative_cash_flow(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"negative\s+cash\s+flows?\s+(?:from|in)")
    return (MEDIUM, "Periods of negative cash flow are disclosed.", hits) if hits else None


def _promoter_pledge(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"(?:promoters?|promoter\s+group)[^.]{0,120}?(?:shares?|equity)[^.]{0,60}?(?:are|have\s+been|were)\s+pledged")
    return (HIGH, "Some promoter shareholding is pledged.", hits) if hits else None


def _related_party(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"related\s+party\s+transactions?[^.]{0,200}?(\d{1,3}(?:\.\d+)?)\s?%\s+of\s+(?:our\s+)?(?:total\s+)?(?:revenue|income|expenses)")
    if not hits:
        return None
    pct = max(float(h.match.group(1)) for h in hits)
    if pct < 10:
        return None
    return (HIGH if pct >= 25 else MEDIUM), f"Related-party transactions reach about {pct:g}% of revenue or expenses.", hits


def _auditor_remarks(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"qualified\s+opinion|emphasis\s+of\s+matter|adverse\s+(?:remarks?|opinion)")
    return (MEDIUM, "The auditors added qualifications or emphasis-of-matter remarks.", hits) if hits else None


def _regulatory_action(pages: list[str]) -> RuleResult:
    hits = _find(pages, r"show[\s-]cause\s+notices?|(?:penalty|penalties)\s+(?:was|were|has\s+been|have\s+been)\s+(?:imposed|levied)")
    return (MEDIUM, f"Regulatory notices or penalties are mentioned {_places(hits)}.", hits) if hits else None


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    why: str
    run: Callable[[list[str]], RuleResult]


RULES: list[Rule] = [
    Rule("customer-concentration", "Depends on a few customers", "If one large customer leaves, revenue can drop overnight.", _customer_concentration),
    Rule("supplier-concentration", "Depends on a few suppliers", "A supplier problem can stop production.", _supplier_concentration),
    Rule("criminal-proceedings", "Criminal cases involving the company or its leaders", "Criminal proceedings against promoters or directors can damage the business and its reputation.", _criminal_proceedings),
    Rule("litigation", "Outstanding litigation", "Large pending cases can turn into payouts that the financials don't yet show.", _litigation),
    Rule("offer-for-sale", "Most of the money goes to existing shareholders", "In an offer for sale, existing investors cash out; the company itself receives none of that money.", _offer_for_sale),
    Rule("general-corporate-purposes", "Money raised without a specific plan", "'General corporate purposes' lets management spend the money as it chooses. SEBI caps it at 25% of the fresh issue.", _general_corporate_purposes),
    Rule("losses", "Has been making losses", "A loss-making company needs future profits to justify its price, and may need to raise money again.", _losses),
    Rule("negative-cash-flow", "Negative cash flow", "Burning cash means the business can't yet fund itself from operations.", _negative_cash_flow),
    Rule("promoter-pledge", "Promoter shares are pledged", "Pledged shares can be sold by lenders if the price falls, pushing it down further.", _promoter_pledge),
    Rule("related-party", "Large related-party dealings", "Deals with companies owned by insiders can move money out of the listed company.", _related_party),
    Rule("auditor-remarks", "Auditor raised concerns", "Qualified opinions or emphasis-of-matter notes flag things the auditor wants investors to notice.", _auditor_remarks),
    Rule("regulatory-action", "Regulatory notices or penalties", "Past action by SEBI, RBI or other regulators can signal compliance problems.", _regulatory_action),
]


def scan_pages(pages: list[str]) -> ScanResult:
    result = ScanResult(pages=len(pages))
    for rule in RULES:
        outcome = rule.run(pages)
        if outcome:
            severity, summary, hits = outcome
            result.findings.append(Finding(rule.id, rule.title, severity, summary, rule.why, _evidence(hits)))
        else:
            result.clear.append({"id": rule.id, "title": rule.title})
    result.findings.sort(key=lambda f: _ORDER[f.severity])
    return result


def pdf_pages(data: bytes) -> list[str]:
    """Text of each page. Raises ScanError with a user-facing message when the PDF can't be read."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if not data.startswith(b"%PDF-"):
        raise ScanError("That isn't a PDF. Upload the prospectus as a .pdf file.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ScanError("This PDF is password-protected. Use the public version from the SEBI or exchange website.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise ScanError("Couldn't read this PDF. It may be damaged.") from exc
    if sum(len(p.strip()) for p in pages) < 200:
        raise ScanError("No text found. This PDF looks scanned; use the text PDF from the SEBI or exchange website.")
    return pages


def scan_pdf(data: bytes) -> ScanResult:
    return scan_pages(pdf_pages(data))
