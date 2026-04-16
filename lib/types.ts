export type Page = 'dashboard' | 'analysis' | 'ipo' | 'screener'
  | 'geo' | 'premium' | 'profile' | 'paper' | 'rhp';

export type Sector = 'it' | 'bank' | 'auto' | 'newage' | 'fmcg' | 'pharma' | 'defence' | 'nbfc' | 'electronics';

export interface StockData {
  ticker: string; sub: string; price: string; chg: string;
  score: number; sector: Sector;
  data: { pe: number; roe: number; de: number; margin: number; promoter: number; cagr: number };
  ctx: { idealPE: string; avgROE: number; idealDE: string; avgMargin: number; sectorCAGR: number; promoterNote: string; cagr: number; pe: number; margin: number };
}

export interface Holding {
  sym: string; qty: number; avgCost: number; ltp: number;
  sl: number; daysHeld: number; hist: number[];
}

export interface IPO {
  name: string; sector: string; open: string; size: string;
  score: number; gmp: number; qib: number; retail: number;
  fund: number; geo: number; verdict: string; band: string;
}

export type MetricKey = 'pe' | 'roe' | 'de' | 'margin' | 'promoter' | 'cagr';

export interface MetricMeta {
  name: string; unit: string; il: string; lo: string; hi: string;
  norm: (v: number, s?: string) => number;
  iz: (s?: string) => [number, number];
  plain: (v: number, s?: string) => string;
  verd: (v: number, s?: string) => string;
}
