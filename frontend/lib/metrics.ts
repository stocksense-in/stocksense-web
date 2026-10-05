import type { MetricKey, Status } from './types';

/**
 * How each fundamental is displayed: its gauge scale, the sector-specific ideal
 * range, and the plain-language reading of a value. Ranges are in the metric's
 * own units (P/E in ×, ROE in %), so the gauge reads like a ruler.
 */
export interface MetricSpec {
  key: MetricKey;
  label: string;
  /** Compact label for tight spaces (tables, score breakdown). */
  short: string;
  unit: '×' | '%';
  /** Gauge range [min, max] — values outside are pinned to the ends. */
  scale: [number, number];
  /** Ideal range for this sector, or null when the metric doesn't apply (e.g. D/E for banks). */
  ideal: (sector: string) => [number, number] | null;
  /** How far outside the ideal range still counts as "watch" rather than "concern". */
  tolerance: number;
  /** One sentence a beginner can act on. */
  reading: (value: number, sector: string) => string;
  /** Why this metric doesn't apply, when ideal() is null. */
  notApplicable?: (sector: string) => string;
}

const BANK = new Set(['bank', 'nbfc']);
const OPEN = 1e9; // "no upper limit"

export const METRICS: Record<MetricKey, MetricSpec> = {
  pe: {
    key: 'pe',
    label: 'P/E ratio',
    short: 'P/E',
    unit: '×',
    scale: [0, 60],
    ideal: (s) => (s === 'newage' ? null : BANK.has(s) ? [12, 20] : [10, 28]),
    tolerance: 6,
    reading: (v) =>
      v <= 0
        ? 'Loss-making, so P/E has no meaning yet.'
        : v < 10
          ? 'Cheap for its sector. Check that earnings aren’t a one-off.'
          : v <= 28
            ? 'Fairly valued for its sector.'
            : 'Priced for strong growth. Any earnings miss hurts more.',
    notApplicable: () => 'New-age platforms are valued on growth, not current earnings. Watch revenue and margin trends instead.',
  },
  roe: {
    key: 'roe',
    label: 'Return on equity',
    short: 'ROE',
    unit: '%',
    scale: [0, 50],
    ideal: (s) => (s === 'newage' ? [5, OPEN] : BANK.has(s) ? [12, OPEN] : [15, OPEN]),
    tolerance: 4,
    reading: (v) =>
      v >= 25
        ? 'Exceptional use of shareholder money — top decile in India.'
        : v >= 15
          ? 'Earns well on shareholder money.'
          : v > 0
            ? 'Below the quality bar. Watch whether it’s improving.'
            : 'Losing money on shareholder equity.',
  },
  de: {
    key: 'de',
    label: 'Debt to equity',
    short: 'Debt/equity',
    unit: '×',
    scale: [0, 3],
    ideal: (s) => (BANK.has(s) ? null : [0, 0.8]),
    tolerance: 0.7,
    reading: (v) =>
      v < 0.3
        ? 'Very little debt — a strong balance sheet.'
        : v <= 0.8
          ? 'Moderate, manageable debt.'
          : 'Heavily borrowed. Check it can cover interest in a bad year.',
    notApplicable: () => 'Lenders borrow to lend, so high debt is normal. Judge banks on asset quality (GNPA) and margins (NIM).',
  },
  margin: {
    key: 'margin',
    label: 'Net profit margin',
    short: 'Net margin',
    unit: '%',
    scale: [0, 40],
    ideal: (s) => (s === 'newage' ? [3, OPEN] : [12, OPEN]),
    tolerance: 4,
    reading: (v) =>
      v >= 20
        ? 'Keeps a large share of every rupee of sales — strong pricing power.'
        : v >= 12
          ? 'Healthy profitability.'
          : v > 0
            ? 'Thin margins leave little room if costs rise.'
            : 'Currently loss-making.',
  },
  promoter: {
    key: 'promoter',
    label: 'Promoter holding',
    short: 'Promoter stake',
    unit: '%',
    scale: [0, 100],
    ideal: (s) => (BANK.has(s) || s === 'newage' ? null : [40, 75]),
    tolerance: 10,
    reading: (v) =>
      v >= 75
        ? 'Very high — little free float, so the stock can swing sharply.'
        : v >= 40
          ? 'Founders have real skin in the game.'
          : 'Low founder stake. Check who the large owners are.',
    notApplicable: (s) =>
      s === 'newage'
        ? 'Venture-backed companies often have no promoter group. Watch large-shareholder exits instead.'
        : 'RBI caps how much of a bank promoters can own, so a low number is expected.',
  },
  cagr: {
    key: 'cagr',
    label: 'Revenue growth (3 yr)',
    short: 'Revenue growth',
    unit: '%',
    scale: [-10, 50],
    ideal: () => [12, OPEN],
    tolerance: 5,
    reading: (v) =>
      v >= 30
        ? 'Growing very fast — well ahead of the economy.'
        : v >= 12
          ? 'Growing faster than most of the market.'
          : v >= 0
            ? 'Slow growth.'
            : 'Revenue is shrinking.',
  },
};

export const METRIC_ORDER: MetricKey[] = ['pe', 'roe', 'de', 'margin', 'promoter', 'cagr'];

export function metricStatus(key: MetricKey, value: number | null, sector: string): Status {
  const spec = METRICS[key];
  const ideal = spec.ideal(sector);
  if (value == null || !ideal) return 'neutral';
  const [lo, hi] = ideal;
  if (value >= lo && value <= hi) return 'healthy';
  const distance = value < lo ? lo - value : value - hi;
  return distance <= spec.tolerance ? 'watch' : 'concern';
}

export function formatMetric(key: MetricKey, value: number | null): string {
  if (value == null) return '—';
  const spec = METRICS[key];
  const decimals = spec.unit === '×' && Math.abs(value) < 10 ? 2 : 1;
  return `${value.toFixed(decimals)}${spec.unit}`;
}

export function idealLabel(key: MetricKey, sector: string): string {
  const spec = METRICS[key];
  const ideal = spec.ideal(sector);
  if (!ideal) return 'Not applicable';
  const [lo, hi] = ideal;
  const fmt = (v: number) => `${v}${spec.unit}`;
  if (hi >= OPEN) return `Above ${fmt(lo)}`;
  if (lo <= 0) return `Below ${fmt(hi)}`;
  return `${fmt(lo)} – ${fmt(hi)}`;
}

export const STATUS_LABEL: Record<Status, string> = {
  healthy: 'Healthy',
  watch: 'Watch',
  concern: 'Concern',
  neutral: 'No benchmark',
};
