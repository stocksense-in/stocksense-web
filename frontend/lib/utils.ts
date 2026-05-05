import { MetricKey } from './types';
import { MM, C } from './constants';

export function pillClass(sig: string) {
  return sig === 'g' ? 'pill pill-g' : sig === 'gold' ? 'pill pill-gold' : sig === 'r' ? 'pill pill-r' : 'pill pill-gold';
}

export function getMetricStatus(mk: MetricKey, val: number, sector: string): 'green' | 'yellow' | 'red' {
  const m = MM[mk];
  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  if (n >= ip && n <= ip + iw) return 'green';
  if (n >= ip - 14 && n <= ip + iw + 14) return 'yellow';
  return 'red';
}

export function scoreColor(score: number) {
  return score >= 70 ? C.green : score >= 55 ? C.gold : C.red;
}

export function formatINR(n: number) {
  return '₹' + Math.round(n).toLocaleString('en-IN');
}
