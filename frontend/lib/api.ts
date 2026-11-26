// Typed client for the StockSense REST API (backend/stocksense/api).
// The base URL comes from NEXT_PUBLIC_API_URL; locally the API runs on port 8000.
// Every fetcher returns null when the API is unreachable or has no data, so panels
// can hide themselves instead of breaking the page.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface StockOut {
  symbol: string;
  name: string | null;
  sector: string | null;
  sector_label: string | null;
  industry: string | null;
  market_cap: number | null;
  price: number | null;
  change_pct: number | null;
  week52_high: number | null;
  week52_low: number | null;
  pe: number | null;
  pb: number | null;
  roe: number | null;
  de: number | null;
  margin: number | null;
  dividend_yield: number | null;
  promoter: number | null;
  cagr: number | null;
  score: number | null;
  updated_at: string | null;
  stale: boolean;
}

export interface PeerStanding {
  group: string;
  peers: number;
  p25: number | null;
  median: number | null;
  p75: number | null;
  typical_range: string | null;
  better_than_pct: number | null;
  standing: string | null;
  text: string | null;
}

export interface ScorePart {
  metric: string;
  value: number | null;
  score: number | null;
  peer_score: number | null;
  absolute_score: number | null;
  weight: number;
  points: number | null;
  label: string;
  measures: string;
  verdict: string | null;
  healthy_range: string | null;
  note: string | null;
  peers: PeerStanding | null;
  stage_note: string | null;
  market_note: string | null;
  history_note: string | null;
  guardrail: string | null;
}

export interface ScoreDetail {
  value: number | null;
  verdict: string | null;
  coverage: number;
  missing: string[];
  coverage_note: string | null;
  stage: string | null;
  stage_text: string | null;
  breakdown: ScorePart[];
}

export interface StockDetail {
  stock: StockOut;
  score: ScoreDetail;
  peers: StockOut[];
  available: { financials: boolean; holders: boolean; dividends: boolean };
}

export interface FinancialQuarter {
  period_end: string;
  revenue: number | null;
  net_profit: number | null;
  eps: number | null;
  margin_pct: number | null;
}

export interface FinancialYear {
  fiscal_year: number;
  revenue: number | null;
  net_profit: number | null;
  margin_pct: number | null;
}

export interface ResultReaction {
  period_end: string;
  filed: string;
  revenue_yoy_pct: number | null;
  profit_yoy_pct: number | null;
  move_1d_pct: number | null;
  excess_1d_pct: number | null;
  move_5d_pct: number | null;
  excess_5d_pct: number | null;
}

export interface Financials {
  symbol: string;
  source: string;
  unit: string;
  basis: string;
  kind: string;
  revenue_means: string;
  quarters: FinancialQuarter[];
  years: FinancialYear[];
  margin_history: {
    now: number; low: number; median: number; high: number;
    since: string; percentile: number; includes_excise: boolean;
  } | null;
  reactions: ResultReaction[];
  reaction_note: string | null;
  metrics: { as_of: string; net_margin: number | null; revenue_cagr_3yr: number | null; roe: number | null; debt_equity: number | null };
}

export interface HolderQuarter {
  quarter_end: string;
  promoter_pct: number | null;
  public_pct: number | null;
  employee_trusts_pct: number | null;
  fii_pct: number | null;
  dii_pct: number | null;
  mutual_funds_pct: number | null;
  insurance_pct: number | null;
  small_retail_pct: number | null;
  government_pct: number | null;
}

export interface Holders {
  symbol: string;
  source: string;
  quarters: HolderQuarter[];
  pledge: { as_of: string; pledged_pct_of_promoter: number | null; pledged_pct_of_total: number | null; all_pledges_pct_of_total: number | null } | null;
  trend_note: string | null;
  pledge_warning: string | null;
}

export interface Dividends {
  symbol: string;
  source: string;
  years: { fiscal_year: number; per_share: number }[];
  ttm_per_share: number;
  paid_years_in_a_row: number;
  streak_since_data_start: boolean;
  data_from_fiscal_year: number | null;
  last_dividend: { ex_date: string; per_share: number } | null;
  capital_actions: { ex_date: string; kind: string; subject: string }[];
  note: string | null;
}

export interface History {
  symbol: string;
  range: string;
  points: { t: number; close: number }[];
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

const sym = (s: string) => encodeURIComponent(s.trim().toUpperCase());

export const api = {
  search: (q: string, signal?: AbortSignal) => get<StockOut[]>(`/stocks/search?q=${encodeURIComponent(q.trim())}`, signal),
  stock: (s: string, signal?: AbortSignal) => get<StockDetail>(`/stocks/${sym(s)}`, signal),
  financials: (s: string, signal?: AbortSignal) => get<Financials>(`/stocks/${sym(s)}/financials`, signal),
  holders: (s: string, signal?: AbortSignal) => get<Holders>(`/stocks/${sym(s)}/holders`, signal),
  dividends: (s: string, signal?: AbortSignal) => get<Dividends>(`/stocks/${sym(s)}/dividends`, signal),
  history: (s: string, range = '1y', signal?: AbortSignal) => get<History>(`/stocks/${sym(s)}/history?range=${range}`, signal),
};

// ── formatting ──────────────────────────────────────────────────────────────

export function fmtNum(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return v.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function fmtPct(v: number | null | undefined, digits = 1, signed = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const s = v.toFixed(digits);
  return `${signed && v > 0 ? '+' : ''}${s}%`;
}

export function fmtRupees(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return '₹' + v.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

/** ₹ crore figures: 457693 → "₹4.58 L Cr", 38821 → "₹38,821 Cr". */
export function fmtCrore(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  if (Math.abs(v) >= 100000) return `₹${(v / 100000).toFixed(2)} L Cr`;
  return `₹${Math.round(v).toLocaleString('en-IN')} Cr`;
}

/** "2026-09-30" → "Sep 2026"; fiscal year 2026 → "FY26". */
export function fmtQuarter(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleString('en-IN', { month: 'short', year: 'numeric' });
}

export const fmtFY = (y: number) => `FY${String(y).slice(-2)}`;

/** Verdict → the golden UI's pill classes. Descriptive only — never buy/sell language. */
export function verdictPill(verdict: string | null | undefined): string {
  const v = (verdict || '').toLowerCase();
  if (v === 'strong') return 'pill pill-g';
  if (v === 'weak') return 'pill pill-r';
  return 'pill pill-gold';
}

export function verdictColor(verdict: string | null | undefined): string {
  const v = (verdict || '').toLowerCase();
  if (v === 'strong') return 'var(--green)';
  if (v === 'weak') return 'var(--red)';
  return 'var(--gold)';
}

/** Colour for a StockSense company score, on the API's own bands: Strong 65+, Fair 45–64, Weak below. */
export function stockScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'var(--cream-mute)';
  return score >= 65 ? 'var(--green)' : score >= 45 ? 'var(--gold)' : 'var(--red)';
}
