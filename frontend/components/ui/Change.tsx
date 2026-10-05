import { change, direction } from '@/lib/format';

/** A signed day-change like "+1.42%", green when up and red when down. */
export function Change({ value, className = '' }: { value: number | null | undefined; className?: string }) {
  const dir = direction(value);
  const color = dir === 'up' ? 'text-up' : dir === 'down' ? 'text-down' : 'text-ink-3';
  return <span className={`num ${color} ${className}`}>{change(value)}</span>;
}
