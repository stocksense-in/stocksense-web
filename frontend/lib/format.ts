/** Number formatting in Indian conventions (lakh/crore grouping). */

const inrFormatters = new Map<number, Intl.NumberFormat>();

function inrFormatter(decimals: number) {
  let f = inrFormatters.get(decimals);
  if (!f) {
    f = new Intl.NumberFormat('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    inrFormatters.set(decimals, f);
  }
  return f;
}

/** ₹1,842.50 — prices. */
export function inr(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';
  return '₹' + inrFormatter(decimals).format(value);
}

/** 24,762.35 — index levels and plain numbers. */
export function num(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';
  return inrFormatter(decimals).format(value);
}

/** +1.42% — always signed, for changes. */
export function change(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${Math.abs(value).toFixed(decimals)}%`;
}

/** 31.2% — unsigned percentages (ROE, margins). */
export function pct(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—';
  return `${value.toFixed(decimals)}%`;
}

/** Market cap from ₹ crore: "₹4.13 L Cr", "₹8,420 Cr". */
export function crore(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value >= 100_000) return `₹${(value / 100_000).toFixed(2)} L Cr`;
  return `₹${inrFormatter(0).format(value)} Cr`;
}

/** Large-cap ≥ ₹1 L Cr? Rough SEBI-style buckets by market cap. */
export function capBand(value: number | null | undefined): 'Large cap' | 'Mid cap' | 'Small cap' | null {
  if (value == null) return null;
  if (value >= 100_000) return 'Large cap';
  if (value >= 30_000) return 'Mid cap';
  return 'Small cap';
}

export function direction(value: number | null | undefined): 'up' | 'down' | 'flat' {
  if (value == null || value === 0) return 'flat';
  return value > 0 ? 'up' : 'down';
}

/** "2 min ago", "3 h ago", "12 Apr". */
export function ago(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return '—';
  // Supabase stores some timestamps without a zone; they are UTC.
  const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
  if (Number.isNaN(t)) return '—';
  const minutes = Math.round((now - t) / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}
