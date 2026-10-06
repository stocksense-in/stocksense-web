import { change, direction } from '@/lib/format';

/**
 * A signed day-change like "+1.42%", mint when up and coral when down.
 * `pill` adds a tinted background — used in tables so the column scans at a glance.
 */
export function Change({ value, className = '', pill = false }: { value: number | null | undefined; className?: string; pill?: boolean }) {
  const dir = direction(value);
  const color = dir === 'up' ? 'text-up' : dir === 'down' ? 'text-down' : 'text-ink-3';
  const wash = pill ? (dir === 'up' ? 'chg-pill bg-up-wash' : dir === 'down' ? 'chg-pill bg-down-wash' : 'chg-pill bg-sunken') : '';
  return <span className={`num ${color} ${wash} ${className}`}>{change(value)}</span>;
}
