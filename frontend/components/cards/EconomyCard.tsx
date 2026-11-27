'use client';
import { useEffect, useState } from 'react';
import type { Economy, EconomySeries } from '@/lib/api';
import { api } from '@/lib/api';

const fmt = (s: EconomySeries, v: number) => (s.unit === 'US$ bn' ? `$${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })} bn` : `${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}%`);
const when = (s: EconomySeries) => new Date(s.period + 'T00:00:00').toLocaleDateString('en-IN', s.series === 'repo_rate' ? { day: 'numeric', month: 'short', year: 'numeric' } : { month: 'short', year: 'numeric' });

/** A small line of the series' recent history (a step line for the repo rate, which changes on decision days). */
function Spark({ s }: { s: EconomySeries }) {
  const pts = s.history.map(([, v]) => v);
  if (pts.length < 2) return null;
  const w = 64, h = 18, lo = Math.min(...pts), hi = Math.max(...pts), span = hi - lo || 1;
  const x = (i: number) => (i / (pts.length - 1)) * w;
  const y = (v: number) => h - 1 - ((v - lo) / span) * (h - 2);
  const d = pts.map((v, i) => (i === 0 ? `M${x(i)},${y(v)}` : s.series === 'repo_rate' ? `H${x(i)}V${y(v)}` : `L${x(i)},${y(v)}`)).join('');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d={d} fill="none" stroke="rgba(201,168,76,0.7)" strokeWidth="1.2" />
    </svg>
  );
}

/** India's economy at a glance: the macro numbers that move whole sectors, each explained. */
export function EconomyCard() {
  const [doc, setDoc] = useState<Economy | null | undefined>(undefined);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.economy().then(d => { if (alive) setDoc(d); });
    return () => { alive = false; };
  }, []);

  if (!doc || !doc.series.length) return null;  // still loading, or the API has no macro data
  return (
    <div className="card">
      <div className="ct">India&apos;s economy</div>
      {doc.series.map((s, i) => {
        const isOpen = open === s.series;
        return (
          <div key={s.series} style={{ padding: '7px 0', borderBottom: i < doc.series.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none' }}>
            <button onClick={() => setOpen(isOpen ? null : s.series)} aria-expanded={isOpen}
              style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: 'block', fontSize: 10, color: 'var(--cream-dim)' }}>{s.label}</span>
                <span style={{ display: 'block', fontSize: 8.5, color: 'var(--cream-mute)', marginTop: 2 }}>{when(s)}</span>
              </span>
              <Spark s={s} />
              <span style={{ fontSize: 12, fontFamily: 'var(--f-mono)', color: 'var(--cream)', minWidth: 62, textAlign: 'right' }}>{fmt(s, s.value)}</span>
            </button>
            {isOpen && (
              <div style={{ fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.6, marginTop: 6 }}>
                <div style={{ color: 'var(--cream)' }}>{s.note}</div>
                <div style={{ marginTop: 4 }}>{s.why}</div>
                <div style={{ fontSize: 8.5, color: 'var(--cream-mute)', marginTop: 4 }}>{s.source} · public from {new Date(s.released + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
              </div>
            )}
          </div>
        );
      })}
      <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10, lineHeight: 1.6 }}>
        Tap a line to see what it means for shares. Each is the latest figure published; inflation and output come out weeks after the month ends.
      </p>
    </div>
  );
}
