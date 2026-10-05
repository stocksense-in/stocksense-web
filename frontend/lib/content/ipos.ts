/**
 * IPO watchlist. Hand-maintained sample data until an IPO feed is wired into
 * the pipeline — the scoring model below is the real part.
 */

export interface Ipo {
  name: string;
  sector: string;
  opens: string;
  issueSize: string;
  priceBand: string;
  /** Each signal scored 0–100. */
  signals: { fundamentals: number; qib: number; gmp: number; geo: number; retail: number };
}

/** Weights of each signal in the IPO score. */
export const IPO_WEIGHTS = [
  { key: 'fundamentals', label: 'Fundamentals', weight: 0.3, help: 'Profitability, growth and debt from the prospectus.' },
  { key: 'qib', label: 'Institutional demand', weight: 0.25, help: 'How heavily qualified institutional buyers subscribed.' },
  { key: 'gmp', label: 'Grey-market premium', weight: 0.2, help: 'Unofficial premium traders pay before listing.' },
  { key: 'geo', label: 'Geopolitical exposure', weight: 0.15, help: 'Higher is safer: less exposure to current global risks.' },
  { key: 'retail', label: 'Retail interest', weight: 0.1, help: 'Retail subscription — a weak signal on its own.' },
] as const;

export function ipoScore(ipo: Ipo): number {
  return Math.round(IPO_WEIGHTS.reduce((sum, w) => sum + ipo.signals[w.key] * w.weight, 0));
}

export function ipoVerdict(score: number): { label: 'Subscribe' | 'Risky' | 'Avoid'; tone: 'healthy' | 'watch' | 'concern' } {
  if (score >= 65) return { label: 'Subscribe', tone: 'healthy' };
  if (score >= 50) return { label: 'Risky', tone: 'watch' };
  return { label: 'Avoid', tone: 'concern' };
}

export const IPOS: Ipo[] = [
  { name: 'Ather Energy', sector: 'EV / Auto', opens: '28 Apr', issueSize: '₹2,626 Cr', priceBand: '₹304–321', signals: { fundamentals: 65, qib: 85, gmp: 68, geo: 60, retail: 72 } },
  { name: 'Hexaware Technologies', sector: 'IT Services', opens: '5 May', issueSize: '₹8,750 Cr', priceBand: '₹674–708', signals: { fundamentals: 70, qib: 78, gmp: 55, geo: 72, retail: 65 } },
  { name: 'Smartworks Coworking', sector: 'Real Estate', opens: '22 Apr', issueSize: '₹583 Cr', priceBand: '₹387–407', signals: { fundamentals: 48, qib: 55, gmp: 42, geo: 55, retail: 68 } },
  { name: 'Swiggy (OFS)', sector: 'Food Tech', opens: '12 May', issueSize: '₹1,200 Cr', priceBand: '₹390–410', signals: { fundamentals: 38, qib: 48, gmp: 30, geo: 50, retail: 60 } },
];
