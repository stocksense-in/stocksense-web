/** Sector codes come from the backend (backend/stocksense/sectors.py). */
export type SectorCode =
  | 'it' | 'bank' | 'nbfc' | 'finance' | 'newage' | 'defence' | 'electronics' | 'auto'
  | 'telecom' | 'consumer' | 'fmcg' | 'pharma' | 'materials' | 'industrial' | 'energy'
  | 'realestate' | 'utilities' | 'general';

/** The six fundamentals that make up the StockSense score. */
export type MetricKey = 'pe' | 'roe' | 'de' | 'margin' | 'promoter' | 'cagr';

/**
 * One NSE stock. Percent fields are percentages (31.2 = 31.2%), `de` is a ratio
 * (0.4 = 0.4×), `marketCap` is in ₹ crore. Any field can be null when the data
 * source doesn't publish it.
 */
export interface Stock {
  symbol: string;
  name: string;
  sector: SectorCode;
  industry: string | null;
  marketCap: number | null;
  price: number | null;
  changePct: number | null;
  week52High: number | null;
  week52Low: number | null;
  pe: number | null;
  pb: number | null;
  roe: number | null;
  de: number | null;
  margin: number | null;
  dividendYield: number | null;
  promoter: number | null;
  cagr: number | null;
  score: number | null;
  updatedAt: string | null;
}

export interface Quote {
  symbol: string;
  price: number;
  changePct: number | null;
  updatedAt: string | null;
}

export interface PricePoint {
  /** Unix seconds */
  t: number;
  close: number;
}

export type Status = 'healthy' | 'watch' | 'concern' | 'neutral';
