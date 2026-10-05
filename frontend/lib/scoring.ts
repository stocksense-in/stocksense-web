import type { MetricKey, Stock } from './types';

/**
 * The StockSense score curves — a mirror of backend/stocksense/scoring.py.
 * The backend computes the stored score; this copy lets the UI show how each
 * metric contributed. Change both files together.
 */

export const WEIGHTS: Record<MetricKey, number> = {
  pe: 0.2,
  roe: 0.2,
  de: 0.15,
  margin: 0.2,
  promoter: 0.1,
  cagr: 0.15,
};

const BANK = new Set(['bank', 'nbfc']);
const clamp = (v: number) => Math.max(0, Math.min(100, v));

export function metricScore(metric: MetricKey, value: number, sector: string): number {
  switch (metric) {
    case 'pe':
      if (sector === 'newage') return 40;
      if (value <= 0) return 0;
      return clamp(100 - ((value - 8) / (BANK.has(sector) ? 30 : 42)) * 100);
    case 'roe':
      return clamp((value / 50) * 100);
    case 'de':
      return BANK.has(sector) ? clamp(100 - ((value - 3) / 12) * 100) : clamp(100 - (value / 3.5) * 100);
    case 'margin':
      return clamp((value / 38) * 100);
    case 'promoter':
      return clamp((value / 80) * 100);
    case 'cagr':
      return clamp((value / 55) * 100);
  }
}

export interface ScorePart {
  metric: MetricKey;
  score: number; // 0–100
  /** Share of the final score after re-normalising for missing metrics, 0–1. */
  weight: number;
}

/** How each available metric contributes to the stock's score. */
export function scoreBreakdown(stock: Stock): ScorePart[] {
  const known = (Object.keys(WEIGHTS) as MetricKey[]).filter((m) => stock[m] != null);
  const total = known.reduce((sum, m) => sum + WEIGHTS[m], 0) || 1;
  return known.map((m) => ({
    metric: m,
    score: metricScore(m, stock[m] as number, stock.sector),
    weight: WEIGHTS[m] / total,
  }));
}

export type Verdict = { label: 'Strong' | 'Fair' | 'Weak'; tone: 'healthy' | 'watch' | 'concern' };

/** Plain-language band for a 0–100 score. */
export function verdict(score: number | null): Verdict | null {
  if (score == null) return null;
  if (score >= 65) return { label: 'Strong', tone: 'healthy' };
  if (score >= 45) return { label: 'Fair', tone: 'watch' };
  return { label: 'Weak', tone: 'concern' };
}
