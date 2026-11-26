'use client';
import { useMemo } from 'react';
import type { History } from '@/lib/api';
import { fmtPct, fmtRupees } from '@/lib/api';

const RANGES: [string, string][] = [['1mo', '1M'], ['6mo', '6M'], ['1y', '1Y'], ['5y', '5Y']];

export function PriceChart({ history, range, onRange }: { history: History | null; range: string; onRange: (r: string) => void }) {
  const W = 640, H = 150, PAD = 4;
  const chart = useMemo(() => {
    const pts = history?.points ?? [];
    if (pts.length < 2) return null;
    const closes = pts.map(p => p.close);
    const lo = Math.min(...closes), hi = Math.max(...closes);
    const span = hi - lo || 1;
    const x = (i: number) => PAD + (i / (pts.length - 1)) * (W - 2 * PAD);
    const y = (c: number) => PAD + (1 - (c - lo) / span) * (H - 2 * PAD);
    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`).join(' ');
    const area = `${line} L${x(pts.length - 1).toFixed(1)},${H} L${x(0).toFixed(1)},${H} Z`;
    const first = closes[0], last = closes[closes.length - 1];
    const fmtDate = (t: number) => new Date(t * 1000).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    return { line, area, lo, hi, change: (last / first - 1) * 100, from: fmtDate(pts[0].t), to: fmtDate(pts[pts.length - 1].t) };
  }, [history]);

  const up = (chart?.change ?? 0) >= 0;
  const stroke = up ? '#00E676' : '#C45C5C';

  return (
    <div className="chart-wrap">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 9, fontWeight: 500, letterSpacing: '1.8px', textTransform: 'uppercase', color: 'var(--cream-mute)' }}>
          Price · closing prices{chart && <span style={{ color: up ? 'var(--green)' : 'var(--red)', marginLeft: 10, fontFamily: 'var(--f-mono)', letterSpacing: 0 }}>{fmtPct(chart.change, 1, true)}</span>}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {RANGES.map(([r, label]) => (
            <button key={r} onClick={() => onRange(r)} className="seg-btn"
              style={{ fontSize: 9, padding: '3px 8px', borderRadius: 3, cursor: 'pointer', fontFamily: 'var(--f-mono)', background: r === range ? 'rgba(201,168,76,0.12)' : 'transparent', color: r === range ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${r === range ? 'var(--border-bright)' : 'var(--border)'}` }}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {chart ? (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 150, display: 'block' }} role="img" aria-label={`Price from ${chart.from} to ${chart.to}`}>
            <defs>
              <linearGradient id="pc-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity="0.18" />
                <stop offset="100%" stopColor={stroke} stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={chart.area} fill="url(#pc-fill)" />
            <path d={chart.line} fill="none" stroke={stroke} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          </svg>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--cream-mute)', marginTop: 6, fontFamily: 'var(--f-mono)' }}>
            <span>{chart.from}</span>
            <span>Low {fmtRupees(chart.lo, 0)} · High {fmtRupees(chart.hi, 0)}</span>
            <span>{chart.to}</span>
          </div>
        </>
      ) : (
        <div style={{ height: 150, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: 'var(--cream-mute)' }}>
          Price history isn&apos;t available right now.
        </div>
      )}
    </div>
  );
}
