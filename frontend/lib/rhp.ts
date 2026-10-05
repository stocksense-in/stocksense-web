/**
 * Prospectus (DRHP/RHP) scanner — finds the risk disclosures beginners usually
 * miss, and quotes the page each finding came from so it can be checked.
 *
 * Pattern-based, not AI: every rule below is a readable regular expression
 * over the prospectus text. It can miss things phrased unusually, and it never
 * replaces reading the "Risk Factors" chapter — the UI says so.
 */

export type Severity = 'high' | 'medium' | 'low';

export interface Evidence {
  page: number; // 1-based
  quote: string;
}

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  summary: string;
  why: string;
  evidence: Evidence[];
}

export interface ScanResult {
  pages: number;
  findings: Finding[];
  /** Rules that ran and found nothing — shown so "no finding" is visible too. */
  clear: { id: string; title: string }[];
}

interface Rule {
  id: string;
  title: string;
  why: string;
  run: (pages: string[]) => Omit<Finding, 'id' | 'title' | 'why'> | null;
}

const MAX_EVIDENCE = 3;

/** Every match of `pattern` with ~220 characters of context and its page number. */
function find(pages: string[], pattern: RegExp, limit = 50): { page: number; match: RegExpExecArray; quote: string }[] {
  const flags = pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g';
  const re = new RegExp(pattern.source, flags);
  const hits: { page: number; match: RegExpExecArray; quote: string }[] = [];
  pages.forEach((text, i) => {
    for (const match of text.matchAll(re)) {
      if (hits.length >= limit) return;
      const start = Math.max(0, match.index! - 80);
      const end = Math.min(text.length, match.index! + match[0].length + 140);
      const quote = (start > 0 ? '…' : '') + text.slice(start, end).replace(/\s+/g, ' ').trim() + (end < text.length ? '…' : '');
      hits.push({ page: i + 1, match: match as RegExpExecArray, quote });
    }
  });
  return hits;
}

/** Up to three distinct quotes (the same sentence often matches twice). */
function evidence(hits: { page: number; quote: string }[]): Evidence[] {
  const seen = new Set<string>();
  const out: Evidence[] = [];
  for (const { page, quote } of hits) {
    const key = `${page}:${quote.slice(0, 120)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ page, quote });
    if (out.length === MAX_EVIDENCE) break;
  }
  return out;
}

const places = (hits: { page: number }[]) => {
  const n = new Set(hits.map((h) => h.page)).size;
  return n === 1 ? 'on 1 page' : `on ${n} pages`;
};

const WORD_NUMBERS: Record<string, number> = { one: 1, two: 2, three: 3, five: 5, ten: 10, twenty: 20 };

/** "₹ 1,234.5 crore" / "Rs. 120 million" → value in ₹ crore. */
function crore(amount: string, unit: string): number {
  const n = Number(amount.replace(/,/g, ''));
  const u = unit.toLowerCase();
  if (u.startsWith('million')) return n / 10;
  if (u.startsWith('lakh')) return n / 100;
  if (u.startsWith('billion')) return n * 100;
  return n;
}

const MONEY = String.raw`(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d+)?)\s?(crores?|million|lakhs?|billion)`;

const RULES: Rule[] = [
  {
    id: 'customer-concentration',
    title: 'Depends on a few customers',
    why: 'If one large customer leaves, revenue can drop overnight.',
    run(pages) {
      const hits = find(pages, /top\s+(\d+|one|five|ten|twenty)\s+customers?[^.%]{0,220}?(\d{1,3}(?:\.\d+)?)\s?%/i);
      if (!hits.length) return null;
      const worst = hits.reduce((a, b) => (Number(b.match[2]) > Number(a.match[2]) ? b : a));
      const pct = Number(worst.match[2]);
      const n = WORD_NUMBERS[worst.match[1].toLowerCase()] ?? worst.match[1];
      return {
        severity: pct >= 50 ? 'high' : pct >= 25 ? 'medium' : 'low',
        summary: `The top ${n} customers account for about ${pct}% of revenue.`,
        evidence: evidence([worst, ...hits.filter((h) => h !== worst)]),
      };
    },
  },
  {
    id: 'supplier-concentration',
    title: 'Depends on a few suppliers',
    why: 'A supplier problem can stop production.',
    run(pages) {
      const hits = find(pages, /top\s+(\d+|one|five|ten|twenty)\s+suppliers?[^.%]{0,220}?(\d{1,3}(?:\.\d+)?)\s?%/i);
      if (!hits.length) return null;
      const pct = Math.max(...hits.map((h) => Number(h.match[2])));
      if (pct < 30) return null;
      return { severity: pct >= 60 ? 'high' : 'medium', summary: `The largest suppliers provide about ${pct}% of purchases.`, evidence: evidence(hits) };
    },
  },
  {
    id: 'criminal-proceedings',
    title: 'Criminal cases involving the company or its leaders',
    why: 'Criminal proceedings against promoters or directors can damage the business and its reputation.',
    run(pages) {
      const hits = find(pages, /criminal\s+(?:proceedings?|cases?|complaints?)[^.]{0,160}?(?:against|involving)\s+(?:our\s+)?(?:company|promoters?|directors?)/i);
      return hits.length
        ? { severity: 'high', summary: `Criminal proceedings are disclosed ${places(hits)}.`, evidence: evidence(hits) }
        : null;
    },
  },
  {
    id: 'litigation',
    title: 'Outstanding litigation',
    why: 'Large pending cases can turn into payouts that the financials don’t yet show.',
    run(pages) {
      const hits = find(pages, /(?:outstanding|pending)\s+(?:legal\s+)?(?:litigations?|proceedings|tax\s+proceedings)/i);
      if (!hits.length) return null;
      const amounts = find(pages, new RegExp(String.raw`(?:litigation|proceedings|claims?)[^.]{0,120}?aggregat\w*[^.]{0,40}?${MONEY}`, 'i'));
      const total = amounts.reduce((sum, h) => sum + crore(h.match[1], h.match[2]), 0);
      return {
        severity: total > 100 ? 'high' : 'medium',
        summary: total > 0 ? `Pending cases are disclosed, with amounts adding up to about ₹${Math.round(total).toLocaleString('en-IN')} crore.` : `Pending legal or tax proceedings are disclosed ${places(hits)}.`,
        evidence: evidence(amounts.length ? amounts : hits),
      };
    },
  },
  {
    id: 'offer-for-sale',
    title: 'Most of the money goes to existing shareholders',
    why: 'In an offer for sale, existing investors cash out; the company itself receives none of that money.',
    run(pages) {
      const fresh = find(pages, new RegExp(String.raw`fresh\s+issue\s+of[^.]{0,120}?${MONEY}`, 'i'), 5);
      const ofs = find(pages, new RegExp(String.raw`offer\s+for\s+sale\s+of[^.]{0,160}?${MONEY}`, 'i'), 5);
      if (!ofs.length) return null;
      const ofsCr = crore(ofs[0].match[1], ofs[0].match[2]);
      const freshCr = fresh.length ? crore(fresh[0].match[1], fresh[0].match[2]) : 0;
      const share = ofsCr / (ofsCr + freshCr);
      if (share < 0.5) return null;
      return {
        severity: share >= 0.8 ? 'high' : 'medium',
        summary: `About ${Math.round(share * 100)}% of the issue (₹${Math.round(ofsCr).toLocaleString('en-IN')} crore) is an offer for sale by existing shareholders.`,
        evidence: evidence([...ofs, ...fresh]),
      };
    },
  },
  {
    id: 'general-corporate-purposes',
    title: 'Money raised without a specific plan',
    why: '“General corporate purposes” lets management spend the money as it chooses. SEBI caps it at 25% of the fresh issue.',
    run(pages) {
      const hits = [
        ...find(pages, new RegExp(String.raw`general\s+corporate\s+purposes[^.]{0,120}?${MONEY}`, 'i')),
        ...find(pages, new RegExp(String.raw`${MONEY}[^.]{0,60}?(?:towards|for)\s+general\s+corporate\s+purposes`, 'i')),
      ];
      if (!hits.length) return null;
      const amount = Math.max(...hits.map((h) => crore(h.match[1], h.match[2])));
      return {
        severity: 'low',
        summary: `Up to about ₹${Math.round(amount).toLocaleString('en-IN')} crore is set aside for general corporate purposes.`,
        evidence: evidence(hits),
      };
    },
  },
  {
    id: 'losses',
    title: 'Has been making losses',
    why: 'A loss-making company needs future profits to justify its price — and may need to raise money again.',
    run(pages) {
      const hits = find(pages, /(?:have|has)\s+(?:in\s+the\s+past\s+)?incurred\s+(?:net\s+)?losses|restated\s+(?:net\s+)?loss\s+(?:for|of)/i);
      return hits.length ? { severity: 'medium', summary: 'The prospectus discloses losses in recent years.', evidence: evidence(hits) } : null;
    },
  },
  {
    id: 'negative-cash-flow',
    title: 'Negative cash flow',
    why: 'Burning cash means the business can’t yet fund itself from operations.',
    run(pages) {
      const hits = find(pages, /negative\s+cash\s+flows?\s+(?:from|in)/i);
      return hits.length ? { severity: 'medium', summary: 'Periods of negative cash flow are disclosed.', evidence: evidence(hits) } : null;
    },
  },
  {
    id: 'promoter-pledge',
    title: 'Promoter shares are pledged',
    why: 'Pledged shares can be sold by lenders if the price falls, pushing it down further.',
    run(pages) {
      const hits = find(pages, /(?:promoters?|promoter\s+group)[^.]{0,120}?(?:shares?|equity)[^.]{0,60}?(?:are|have\s+been|were)\s+pledged/i);
      return hits.length ? { severity: 'high', summary: 'Some promoter shareholding is pledged.', evidence: evidence(hits) } : null;
    },
  },
  {
    id: 'related-party',
    title: 'Large related-party dealings',
    why: 'Deals with companies owned by insiders can move money out of the listed company.',
    run(pages) {
      const hits = find(pages, /related\s+party\s+transactions?[^.]{0,200}?(\d{1,3}(?:\.\d+)?)\s?%\s+of\s+(?:our\s+)?(?:total\s+)?(?:revenue|income|expenses)/i);
      if (!hits.length) return null;
      const pct = Math.max(...hits.map((h) => Number(h.match[1])));
      if (pct < 10) return null;
      return { severity: pct >= 25 ? 'high' : 'medium', summary: `Related-party transactions reach about ${pct}% of revenue or expenses.`, evidence: evidence(hits) };
    },
  },
  {
    id: 'auditor-remarks',
    title: 'Auditor raised concerns',
    why: 'Qualified opinions or emphasis-of-matter notes flag things the auditor wants investors to notice.',
    run(pages) {
      const hits = find(pages, /qualified\s+opinion|emphasis\s+of\s+matter|adverse\s+(?:remarks?|opinion)/i);
      return hits.length ? { severity: 'medium', summary: 'The auditors added qualifications or emphasis-of-matter remarks.', evidence: evidence(hits) } : null;
    },
  },
  {
    id: 'regulatory-action',
    title: 'Regulatory notices or penalties',
    why: 'Past action by SEBI, RBI or other regulators can signal compliance problems.',
    run(pages) {
      const hits = find(pages, /show[\s-]cause\s+notices?|(?:penalty|penalties)\s+(?:was|were|has\s+been|have\s+been)\s+(?:imposed|levied)/i);
      return hits.length ? { severity: 'medium', summary: `Regulatory notices or penalties are mentioned ${places(hits)}.`, evidence: evidence(hits) } : null;
    },
  },
];

export const RULE_LIST = RULES.map(({ id, title, why }) => ({ id, title, why }));

const ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

export function scanProspectus(pages: string[]): ScanResult {
  const findings: Finding[] = [];
  const clear: ScanResult['clear'] = [];
  for (const rule of RULES) {
    const result = rule.run(pages);
    if (result) findings.push({ id: rule.id, title: rule.title, why: rule.why, ...result });
    else clear.push({ id: rule.id, title: rule.title });
  }
  findings.sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
  return { pages: pages.length, findings, clear };
}
