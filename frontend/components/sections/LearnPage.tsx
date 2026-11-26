'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { LearnMetrics, SectorOption, StockOut } from '@/lib/api';
import { api, fmtCrore, stockScoreColor } from '@/lib/api';
import { METRIC_CONTENT } from '@/lib/metricContent';

const STAGE_ORDER = ['steady', 'high growth', 'loss-making'];

export function LearnPage() {
  const router = useRouter();
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [sector, setSector] = useState('general');
  const [guide, setGuide] = useState<{ sector: string; data: LearnMetrics | null } | null>(null);
  const [examples, setExamples] = useState<{ sector: string; rows: StockOut[] } | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    api.sectors(ctl.signal).then(s => { if (s) setSectors(s); });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    const ctl = new AbortController();
    api.learn(sector, ctl.signal).then(d => { if (!ctl.signal.aborted) setGuide({ sector, data: d }); });
    if (sector !== 'general') {
      api.screen({ sector, sort: 'market_cap', page_size: 5 }, ctl.signal).then(r => { if (!ctl.signal.aborted) setExamples({ sector, rows: r?.results ?? [] }); });
    }
    return () => ctl.abort();
  }, [sector]);

  const data = guide?.sector === sector ? guide.data : null;
  const rows = sector !== 'general' && examples?.sector === sector ? examples.rows : [];
  const label = sector === 'general' ? 'all companies' : (sectors.find(s => s.code === sector)?.label ?? data?.sector_label ?? sector);

  return (
    <div>
      <div className="card card-gold" style={{ marginBottom: 14 }}>
        <div className="ct" style={{ marginBottom: 8 }}>How to judge a company</div>
        <p style={{ fontSize: 13, color: 'var(--cream)', lineHeight: 1.7, margin: 0, fontFamily: 'var(--f-display)' }}>
          Six numbers tell you most of what matters: what you pay for the profits, how well the business uses its money,
          how much it has borrowed, how much of each sale it keeps, whether its owners have their own money in it, and how fast it is growing.
        </p>
        <p className="mc-plain" style={{ marginTop: 10 }}>
          None of them means much alone. A number is only high or low <strong style={{ color: 'var(--gold)' }}>compared with similar companies</strong>,
          so pick a sector to see what is typical there. The StockSense score blends both views: 70% from where a company sits among its sector peers,
          30% from a fixed scale for all companies.
        </p>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 14, flexWrap: 'wrap' }}>
          <span className="field-label" style={{ margin: 0 }}>Sector</span>
          <select className="fi" value={sector} onChange={e => { setSector(e.target.value); setOpen(null); }} style={{ maxWidth: 280 }}>
            <option value="general">All companies</option>
            {sectors.map(s => <option key={s.code} value={s.code}>{s.label} ({s.stocks})</option>)}
          </select>
        </div>
      </div>

      {data?.market_note && (
        <div className="geo-alert" style={{ marginBottom: 14, padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
            <strong style={{ color: 'var(--gold)' }}>Valuation today · </strong>{data.market_note}
          </div>
        </div>
      )}

      {!data && guide && <div className="card" style={{ fontSize: 11, color: 'var(--cream-mute)' }}>The metric guide isn&apos;t reachable right now.</div>}

      <div className="mc-grid" style={{ alignItems: 'start' }}>
        {data?.metrics.map(m => {
          const deep = (METRIC_CONTENT as Record<string, { medium: { why: string; risks: string[] } } | undefined>)[m.metric]?.medium;
          const isOpen = open === m.metric;
          return (
            <div key={m.metric} className={`mc${isOpen ? ' open' : ''}`} onClick={() => setOpen(isOpen ? null : m.metric)} role="button" tabIndex={0}
              onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setOpen(isOpen ? null : m.metric)} aria-expanded={isOpen}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--cream)', fontFamily: 'var(--f-display)' }}>{m.label}</div>
                <span className="pill pill-b" title="Share of the StockSense score">{Math.round(m.weight * 100)}% of score</span>
              </div>
              <p className="mc-plain" style={{ marginTop: 8, color: 'var(--cream)' }}>{m.measures[0].toUpperCase() + m.measures.slice(1)}.</p>
              <div className="stat-r" style={{ marginTop: 8 }}>
                <span className="sl">Typical in {label}</span>
                <span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{m.peers?.typical_range ?? '—'}</span>
              </div>
              {m.peers?.median !== null && m.peers?.median !== undefined && (
                <div className="stat-r">
                  <span className="sl">Median of {m.peers.peers.toLocaleString('en-IN')} companies</span>
                  <span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{m.peers.median.toLocaleString('en-IN', { maximumFractionDigits: m.metric === 'de' ? 2 : 1 })}{m.metric === 'pe' || m.metric === 'de' ? '×' : '%'}</span>
                </div>
              )}
              <div className="stat-r">
                <span className="sl">{m.higher_is_better ? 'Higher is better' : 'Lower is better'}</span>
                <span className="sv" style={{ fontFamily: 'var(--f-mono)', fontSize: 9.5, textAlign: 'right' }}>{m.healthy_range}</span>
              </div>
              {m.watch_for && <p className="mc-plain" style={{ marginTop: 10 }}><strong style={{ color: 'var(--gold)' }}>Watch for: </strong>{m.watch_for}</p>}
              {isOpen && deep && (
                <div className="mc-expand" onClick={e => e.stopPropagation()}>
                  <div className="ct" style={{ marginBottom: 6 }}>Why it matters</div>
                  <p className="exp-body" style={{ color: 'var(--cream-dim)' }}>{deep.why}</p>
                  <div className="ct" style={{ margin: '10px 0 6px' }}>Common traps</div>
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    {deep.risks.map(r => <li key={r} className="exp-body" style={{ color: 'var(--cream-dim)', marginBottom: 4 }}>{r}</li>)}
                  </ul>
                </div>
              )}
              <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>{isOpen ? 'Less ▲' : 'Why it matters ▼'}</div>
            </div>
          );
        })}
      </div>

      <div className="g2" style={{ marginTop: 14, alignItems: 'start' }}>
        {data && (
          <div className="card">
            <div className="ct">A company&apos;s stage changes the reading</div>
            {STAGE_ORDER.filter(k => data.stages[k]).map(k => (
              <div key={k} style={{ padding: '8px 0', borderBottom: '1px solid rgba(201,168,76,0.04)' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--cream)', textTransform: 'capitalize' }}>{k}</div>
                <div style={{ fontSize: 11, color: 'var(--cream-dim)', marginTop: 3, lineHeight: 1.6 }}>{data.stages[k]}</div>
              </div>
            ))}
          </div>
        )}
        {rows.length > 0 && (
          <div className="card">
            <div className="ct">Practise on the largest {label} companies</div>
            {rows.map(r => (
              <div key={r.symbol} onClick={() => router.push(`/analysis?s=${encodeURIComponent(r.symbol)}`)}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(201,168,76,0.04)', cursor: 'pointer' }}>
                <div>
                  <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)' }}>{r.symbol}</div>
                  <div style={{ fontSize: 10, color: 'var(--cream-mute)', marginTop: 2 }}>{r.name} · {fmtCrore(r.market_cap)}</div>
                </div>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 13, color: stockScoreColor(r.score) }}>{r.score ?? '—'}</span>
              </div>
            ))}
            <p className="mc-plain" style={{ marginTop: 10 }}>Open one and check each metric against the typical range above before reading its score.</p>
          </div>
        )}
      </div>

      <div className="geo-alert" style={{ marginTop: 14, padding: '12px 16px' }}>
        <div style={{ fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--red)' }}>Disclosure: </strong>StockSense teaches how to read a company; it doesn&apos;t tell you what to buy or sell, and it isn&apos;t SEBI-registered investment advice.
        </div>
      </div>
    </div>
  );
}
