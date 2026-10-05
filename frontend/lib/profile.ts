/**
 * The investor profile: saved in a cookie so server pages (Matched picks) can
 * read it without an account. Shared by the profile form and the matching logic.
 */
import type { SectorCode, Stock } from './types';
import { METRICS } from './metrics';
import { sectorLabel } from './sectors';

export const PROFILE_COOKIE = 'stocksense_profile';

export type Risk = 'conservative' | 'moderate' | 'aggressive';
export type Horizon = '1y' | '3y' | '5y';

export interface Profile {
  capital: number;
  horizon: Horizon;
  risk: Risk;
  sectors: SectorCode[];
}

export const DEFAULT_PROFILE: Profile = { capital: 100_000, horizon: '3y', risk: 'moderate', sectors: [] };

export const RISK_COPY: Record<Risk, { label: string; description: string }> = {
  conservative: {
    label: 'Conservative',
    description: 'Protect what you have. Large, profitable companies with little debt; slower but steadier.',
  },
  moderate: {
    label: 'Balanced',
    description: 'Quality companies of any size, accepting some ups and downs for better growth.',
  },
  aggressive: {
    label: 'Growth',
    description: 'Faster-growing, often smaller companies. Expect big swings — needs a 3+ year horizon.',
  },
};

export const HORIZON_LABEL: Record<Horizon, string> = { '1y': 'About a year', '3y': '3 years', '5y': '5 years or more' };

export function parseProfile(raw: string | undefined): Profile | null {
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as Partial<Profile>;
    return {
      capital: typeof p.capital === 'number' ? p.capital : DEFAULT_PROFILE.capital,
      horizon: p.horizon && p.horizon in HORIZON_LABEL ? p.horizon : DEFAULT_PROFILE.horizon,
      risk: p.risk && p.risk in RISK_COPY ? p.risk : DEFAULT_PROFILE.risk,
      sectors: Array.isArray(p.sectors) ? p.sectors : [],
    };
  } catch {
    return null;
  }
}

export interface Match {
  stock: Stock;
  reasons: string[];
}

const BANK = new Set(['bank', 'nbfc', 'finance']);

/** Stocks that fit the profile, best first, each with the plain reasons it fits. */
export function matchStocks(stocks: Stock[], profile: Profile, limit = 9): Match[] {
  const rules = {
    conservative: { minScore: 60, minCap: 100_000, maxDe: 0.5, minCagr: -Infinity },
    moderate: { minScore: 55, minCap: 20_000, maxDe: 1, minCagr: 5 },
    aggressive: { minScore: 50, minCap: 3_000, maxDe: 1.5, minCagr: 15 },
  }[profile.risk];

  const preferred = new Set(profile.sectors);
  const candidates = stocks.filter((s) => {
    if (s.score == null || s.score < rules.minScore || s.price == null) return false;
    if ((s.marketCap ?? 0) < rules.minCap) return false;
    if (!BANK.has(s.sector) && s.de != null && s.de > rules.maxDe) return false;
    if (s.cagr != null && s.cagr < rules.minCagr) return false;
    // Shares above the whole budget can't be bought even once.
    if (s.price > profile.capital) return false;
    return preferred.size === 0 || preferred.has(s.sector);
  });

  // Growth investors care more about growth; conservative ones about quality.
  const rank = (s: Stock) =>
    (s.score ?? 0) + (profile.risk === 'aggressive' ? Math.min(s.cagr ?? 0, 40) / 2 : 0) + (profile.risk === 'conservative' ? Math.min((s.marketCap ?? 0) / 100_000, 10) : 0);

  return candidates
    .sort((a, b) => rank(b) - rank(a))
    .slice(0, limit)
    .map((stock) => ({ stock, reasons: reasonsFor(stock, profile) }));
}

function reasonsFor(s: Stock, profile: Profile): string[] {
  const reasons: string[] = [];
  if (s.roe != null && s.roe >= 15) reasons.push(`Earns ${s.roe.toFixed(0)}% on shareholder money`);
  if (s.de != null && !BANK.has(s.sector) && s.de < 0.3) reasons.push('Almost no debt');
  if (s.cagr != null && s.cagr >= 15) reasons.push(`Revenue growing ${s.cagr.toFixed(0)}% a year`);
  if (s.margin != null && s.margin >= 15) reasons.push(`Keeps ${s.margin.toFixed(0)}% of sales as profit`);
  if (s.pe != null && s.pe > 0 && s.pe < 15 && s.sector !== 'newage') reasons.push(`Modest valuation at ${s.pe.toFixed(1)}× earnings`);
  if (profile.sectors.includes(s.sector)) reasons.push(`In ${sectorLabel(s.sector)}, a sector you picked`);
  if (reasons.length === 0) reasons.push(`${METRICS.pe.short} and returns are within healthy ranges`);
  return reasons.slice(0, 3);
}
