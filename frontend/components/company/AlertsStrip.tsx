'use client';
import type { Alert } from '@/lib/api';
import { ALERT_LABEL } from '@/lib/api';

const tone = (a: Alert) =>
  a.kind === 'price_move' || a.kind === 'promoter_stake' || a.kind === 'pledge_change'
    ? (a.value ?? 0) >= 0 ? (a.kind === 'pledge_change' ? 'pill pill-r' : 'pill pill-g') : (a.kind === 'pledge_change' ? 'pill pill-g' : 'pill pill-r')
    : 'pill pill-gold';

const day = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

/** What happened to the company over the last sessions: moves, heavy trading, results, orders, stake changes. */
export function AlertsStrip({ alerts, max = 6 }: { alerts: Alert[]; max?: number }) {
  if (!alerts.length) return null;
  return (
    <div className="card" style={{ marginBottom: 14, padding: '12px 16px' }}>
      <div className="ct" style={{ marginBottom: 8 }}>Last two weeks</div>
      {alerts.slice(0, max).map((a, i) => (
        <div key={`${a.date}-${a.kind}-${i}`} style={{ display: 'flex', gap: 10, alignItems: 'baseline', padding: '5px 0', borderBottom: i < Math.min(max, alerts.length) - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none' }}>
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--cream-mute)', minWidth: 48 }}>{day(a.date)}</span>
          <span className={tone(a)} style={{ fontSize: 8, flexShrink: 0 }}>{ALERT_LABEL[a.kind] ?? a.kind}</span>
          <span style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.5 }}>{a.text}</span>
        </div>
      ))}
    </div>
  );
}
