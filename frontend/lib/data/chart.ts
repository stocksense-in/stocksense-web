/**
 * Daily price history from Yahoo Finance's public chart endpoint. Server-only.
 * Cached for an hour — daily candles don't change intraday except the last one.
 */
import type { PricePoint } from '@/lib/types';

export type Range = '1mo' | '6mo' | '1y' | '5y';

export const RANGES: { value: Range; label: string }[] = [
  { value: '1mo', label: '1M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '5y', label: '5Y' },
];

const INDEX_TICKERS: Record<string, string> = {
  NIFTY50: '^NSEI',
  SENSEX: '^BSESN',
  BANKNIFTY: '^NSEBANK',
};

export async function getPriceHistory(symbol: string, range: Range = '1y'): Promise<PricePoint[]> {
  const ticker = INDEX_TICKERS[symbol] ?? `${symbol}.NS`;
  const interval = range === '5y' ? '1wk' : '1d';
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=${range}&interval=${interval}`;
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (StockSense)' },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const json = await res.json();
    const result = json?.chart?.result?.[0];
    const times: number[] = result?.timestamp ?? [];
    const closes: (number | null)[] = result?.indicators?.quote?.[0]?.close ?? [];
    return times.flatMap((t, i) => (closes[i] != null ? [{ t, close: closes[i] as number }] : []));
  } catch {
    return []; // the page shows "Price history unavailable" instead of failing
  }
}
