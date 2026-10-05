/**
 * Where stock data comes from. Server-only: imported by pages and route handlers.
 *
 * With SUPABASE_URL + SUPABASE_ANON_KEY set, everything is read from Supabase
 * (written there by the Python pipeline in backend/). Without them, the app runs
 * on data/snapshot.json — real numbers from the last time someone ran the
 * pipeline with --snapshot — so it always works locally.
 *
 * Both modes return the full universe (~2,600 rows); filtering and sorting
 * happen in lib/data/queries.ts so there is one code path for both.
 */
import snapshot from '@/data/snapshot.json';
import type { Quote, SectorCode, Stock } from '@/lib/types';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY;

export const usingSnapshot = !SUPABASE_URL || !SUPABASE_KEY;

/** Seconds a cached response is reused before Supabase is asked again. */
const STOCKS_TTL = 300; // fundamentals change daily
const PRICES_TTL = 30; // prices change by the minute
const PAGE = 1000; // PostgREST's default max rows per request

interface StockRow {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  industry?: string | null;
  market_cap?: number | null;
  price?: number | string | null;
  price_change_pct?: number | string | null;
  week52_high?: number | null;
  week52_low?: number | null;
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  roe?: number | null;
  debt_equity?: number | null;
  net_margin?: number | null;
  dividend_yield?: number | null;
  promoter_holding?: number | null;
  revenue_cagr_3yr?: number | null;
  composite_score?: number | null;
  last_updated?: string | null;
}

interface PriceRow {
  symbol: string;
  price: number | string;
  change_pct?: number | string | null;
  updated_at?: string | null;
}

/** Postgres numerics can arrive as strings; normalise to number | null. */
const n = (v: unknown): number | null => {
  if (v == null || v === '') return null;
  const x = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(x) ? x : null;
};

function toStock(r: StockRow): Stock {
  return {
    symbol: r.symbol,
    name: r.name || r.symbol,
    sector: (r.sector || 'general') as SectorCode,
    industry: r.industry ?? null,
    marketCap: n(r.market_cap),
    price: n(r.price),
    changePct: n(r.price_change_pct),
    week52High: n(r.week52_high),
    week52Low: n(r.week52_low),
    pe: n(r.pe_ratio),
    pb: n(r.pb_ratio),
    roe: n(r.roe),
    de: n(r.debt_equity),
    margin: n(r.net_margin),
    dividendYield: n(r.dividend_yield),
    promoter: n(r.promoter_holding),
    cagr: n(r.revenue_cagr_3yr),
    score: n(r.composite_score),
    updatedAt: r.last_updated ?? null,
  };
}

function toQuote(r: PriceRow): Quote {
  return { symbol: r.symbol, price: Number(r.price), changePct: n(r.change_pct), updatedAt: r.updated_at ?? null };
}

async function selectAll<T>(table: string, columns: string, ttl: number): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?select=${columns}&order=symbol`, {
      headers: {
        apikey: SUPABASE_KEY!,
        Authorization: `Bearer ${SUPABASE_KEY}`,
        Range: `${offset}-${offset + PAGE - 1}`,
      },
      next: { revalidate: ttl, tags: [table] },
    });
    if (!res.ok) throw new Error(`Supabase ${table}: ${res.status} ${await res.text()}`);
    const page = (await res.json()) as T[];
    rows.push(...page);
    if (page.length < PAGE) return rows;
  }
}

/** Every stock with its latest known fundamentals and price. */
export async function loadStocks(): Promise<Stock[]> {
  const [rows, quotes] = await Promise.all([
    usingSnapshot ? (snapshot.stocks as StockRow[]) : orSnapshot(selectAll<StockRow>('stocks', '*', STOCKS_TTL), 'stocks'),
    loadQuotes(),
  ]);
  return rows.map((r) => withQuote(toStock(r), quotes.get(r.symbol)));
}

/** Latest prices for stocks and indices (NIFTY50, SENSEX, BANKNIFTY, INDIAVIX). */
export async function loadQuotes(): Promise<Map<string, Quote>> {
  const rows = usingSnapshot
    ? (snapshot.prices as PriceRow[])
    : await orSnapshot(selectAll<PriceRow>('live_prices', 'symbol,price,change_pct,updated_at', PRICES_TTL), 'prices');
  return new Map(rows.map((r) => [r.symbol, toQuote(r)]));
}

/** If Supabase is down (or paused), serve the snapshot instead of an error page. */
async function orSnapshot<T>(query: Promise<T[]>, key: 'stocks' | 'prices'): Promise<T[]> {
  try {
    return await query;
  } catch (error) {
    console.error(`[data] Supabase unavailable, using snapshot ${key}:`, error instanceof Error ? error.message : error);
    return snapshot[key] as T[];
  }
}

/** A live price beats the fundamentals job's price when it is newer. */
function withQuote(stock: Stock, quote: Quote | undefined): Stock {
  if (!quote) return stock;
  const stockTime = stock.updatedAt ? Date.parse(stock.updatedAt) : 0;
  const quoteTime = quote.updatedAt ? Date.parse(quote.updatedAt) : 0;
  if (stock.price != null && stockTime > quoteTime) return stock;
  return { ...stock, price: quote.price, changePct: quote.changePct ?? stock.changePct };
}
