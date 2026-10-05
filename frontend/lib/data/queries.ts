/**
 * Questions the pages ask about the market. Server-only.
 * Everything works on the full stock list from source.ts, cached per request.
 */
import { cache } from 'react';
import type { Quote, SectorCode, Stock } from '@/lib/types';
import { loadQuotes, loadStocks } from './source';

const stocks = cache(loadStocks);
const quotes = cache(loadQuotes);

export const INDICES = [
  { symbol: 'NIFTY50', label: 'NIFTY 50' },
  { symbol: 'SENSEX', label: 'SENSEX' },
  { symbol: 'BANKNIFTY', label: 'BANK NIFTY' },
  { symbol: 'INDIAVIX', label: 'India VIX' },
] as const;

export async function getIndices(): Promise<(Quote & { label: string })[]> {
  const all = await quotes();
  return INDICES.flatMap(({ symbol, label }) => {
    const q = all.get(symbol);
    return q ? [{ ...q, label }] : [];
  });
}

export async function getStock(symbol: string): Promise<Stock | null> {
  const wanted = symbol.toUpperCase();
  return (await stocks()).find((s) => s.symbol === wanted) ?? null;
}

export async function getStocks(symbols: string[]): Promise<Stock[]> {
  const bySymbol = new Map((await stocks()).map((s) => [s.symbol, s]));
  return symbols.flatMap((sym) => bySymbol.get(sym) ?? []);
}

/** Symbol or company-name search, best matches first. */
export async function searchStocks(query: string, limit = 8): Promise<Stock[]> {
  const q = query.trim().toUpperCase();
  if (!q) return [];
  const rank = (s: Stock) => {
    if (s.symbol === q) return 0;
    if (s.symbol.startsWith(q)) return 1;
    if (s.name.toUpperCase().startsWith(q)) return 2;
    if (s.name.toUpperCase().includes(q) || s.symbol.includes(q)) return 3;
    return 9;
  };
  return (await stocks())
    .map((s) => ({ s, r: rank(s) }))
    .filter(({ r }) => r < 9)
    .sort((a, b) => a.r - b.r || (b.s.marketCap ?? 0) - (a.s.marketCap ?? 0))
    .slice(0, limit)
    .map(({ s }) => s);
}

// ── Screener ────────────────────────────────────────────────────────────────

export type SortKey = 'score' | 'marketCap' | 'changePct' | 'pe' | 'roe' | 'de' | 'name';

export interface ScreenerFilters {
  sector?: SectorCode;
  minScore?: number;
  cap?: 'large' | 'mid' | 'small';
  maxPe?: number;
  minRoe?: number;
  maxDe?: number;
  sort?: SortKey;
  dir?: 'asc' | 'desc';
  page?: number;
}

export const SCREENER_PAGE_SIZE = 50;

const CAP_RANGES = { large: [100_000, Infinity], mid: [30_000, 100_000], small: [0, 30_000] } as const;

export async function screen(f: ScreenerFilters): Promise<{ rows: Stock[]; total: number; universe: number }> {
  const all = await stocks();
  const rows = all.filter((s) => {
    if (s.price == null) return false;
    if (f.sector && s.sector !== f.sector) return false;
    if (f.minScore != null && (s.score ?? -1) < f.minScore) return false;
    if (f.cap) {
      const [lo, hi] = CAP_RANGES[f.cap];
      if (s.marketCap == null || s.marketCap < lo || s.marketCap >= hi) return false;
    }
    if (f.maxPe != null && (s.pe == null || s.pe <= 0 || s.pe > f.maxPe)) return false;
    if (f.minRoe != null && (s.roe == null || s.roe < f.minRoe)) return false;
    if (f.maxDe != null && (s.de == null || s.de > f.maxDe)) return false;
    return true;
  });

  const key = f.sort ?? 'score';
  const dir = f.dir ?? (key === 'name' || key === 'pe' || key === 'de' ? 'asc' : 'desc');
  const sign = dir === 'asc' ? 1 : -1;
  rows.sort((a, b) => {
    if (key === 'name') return sign * a.name.localeCompare(b.name);
    const av = a[key], bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1; // missing values always last
    if (bv == null) return -1;
    return sign * (av - bv);
  });

  const page = Math.max(1, f.page ?? 1);
  return {
    rows: rows.slice((page - 1) * SCREENER_PAGE_SIZE, page * SCREENER_PAGE_SIZE),
    total: rows.length,
    universe: all.length,
  };
}

// ── Dashboard ───────────────────────────────────────────────────────────────

/** Biggest gainers and losers among stocks worth at least ₹10,000 Cr (filters out illiquid noise). */
export async function getMovers(count = 5): Promise<{ gainers: Stock[]; losers: Stock[] }> {
  const liquid = (await stocks()).filter((s) => s.changePct != null && (s.marketCap ?? 0) >= 10_000);
  const sorted = [...liquid].sort((a, b) => (b.changePct ?? 0) - (a.changePct ?? 0));
  return {
    gainers: sorted.slice(0, count).filter((s) => (s.changePct ?? 0) > 0),
    losers: sorted.slice(-count).reverse().filter((s) => (s.changePct ?? 0) < 0),
  };
}

export interface SectorMove {
  sector: SectorCode;
  /** Market-cap-weighted average day change, % */
  changePct: number;
  advancers: number;
  decliners: number;
}

export async function getSectorMoves(): Promise<SectorMove[]> {
  const groups = new Map<SectorCode, { weighted: number; cap: number; up: number; down: number }>();
  for (const s of await stocks()) {
    if (s.changePct == null || s.marketCap == null || s.sector === 'general') continue;
    const g = groups.get(s.sector) ?? { weighted: 0, cap: 0, up: 0, down: 0 };
    g.weighted += s.changePct * s.marketCap;
    g.cap += s.marketCap;
    if (s.changePct > 0) g.up++;
    else if (s.changePct < 0) g.down++;
    groups.set(s.sector, g);
  }
  return [...groups.entries()]
    .filter(([, g]) => g.up + g.down >= 3)
    .map(([sector, g]) => ({ sector, changePct: g.weighted / g.cap, advancers: g.up, decliners: g.down }))
    .sort((a, b) => b.changePct - a.changePct);
}

export async function getBreadth(): Promise<{ advancers: number; decliners: number; unchanged: number }> {
  let advancers = 0, decliners = 0, unchanged = 0;
  for (const s of await stocks()) {
    if (s.changePct == null) continue;
    if (s.changePct > 0) advancers++;
    else if (s.changePct < 0) decliners++;
    else unchanged++;
  }
  return { advancers, decliners, unchanged };
}

/** Highest-scoring stocks, optionally only large/mid caps. */
export async function getTopScored(count = 8, minMarketCap = 30_000): Promise<Stock[]> {
  return (await stocks())
    .filter((s) => s.score != null && (s.marketCap ?? 0) >= minMarketCap)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, count);
}

/** Latest data timestamp, for "Updated 4 min ago" labels. */
export async function getLastUpdated(): Promise<string | null> {
  const times = [...(await quotes()).values()].map((q) => q.updatedAt).filter(Boolean) as string[];
  return times.sort().at(-1) ?? null;
}
