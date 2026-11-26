'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { ScreenPage, ScreenQuery, SectorOption } from '@/lib/api';
import { API_URL, api, fmtCrore, fmtNum, fmtPct, stockScoreColor } from '@/lib/api';

type Sort = NonNullable<ScreenQuery['sort']>;

interface Filters {
  sector: string;
  cap: '' | 'large' | 'mid' | 'small';
  min_score: string;
  max_pe: string;
  min_roe: string;
  max_de: string;
}

const EMPTY: Filters = { sector: '', cap: '', min_score: '', max_pe: '', min_roe: '', max_de: '' };
const PAGE_SIZE = 25;

// Ready-made screens that teach a way of looking at companies, not a pick list.
const PRESETS: { label: string; hint: string; f: Partial<Filters> }[] = [
  { label: 'Quality', hint: 'High return on equity, little debt', f: { min_roe: '18', max_de: '0.5' } },
  { label: 'Value', hint: 'Low P/E with healthy returns', f: { max_pe: '15', min_roe: '12' } },
  { label: 'Strong fundamentals', hint: 'Score 65 or more', f: { min_score: '65' } },
  { label: 'Large caps', hint: 'Market cap above ₹1 lakh crore', f: { cap: 'large' } },
];

const num = (v: string) => (v.trim() === '' || Number.isNaN(Number(v)) ? undefined : Number(v));

export function ScreenerPage() {
  const router = useRouter();
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [applied, setApplied] = useState<Filters>(EMPTY);
  const [sort, setSort] = useState<Sort>('score');
  const [order, setOrder] = useState<'asc' | 'desc' | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<{ key: string; data: ScreenPage | null } | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    api.sectors(ctl.signal).then(s => { if (s) setSectors(s); });
    return () => ctl.abort();
  }, []);

  const query: ScreenQuery = {
    sector: applied.sector || undefined,
    cap: applied.cap || undefined,
    min_score: num(applied.min_score),
    max_pe: num(applied.max_pe),
    min_roe: num(applied.min_roe),
    max_de: num(applied.max_de),
    sort, order, page, page_size: PAGE_SIZE,
  };
  const key = JSON.stringify(query);

  useEffect(() => {
    const ctl = new AbortController();
    const q = JSON.parse(key) as ScreenQuery;
    api.screen(q, ctl.signal).then(data => { if (!ctl.signal.aborted) setResult({ key, data }); });
    return () => ctl.abort();
  }, [key]);

  const loading = result?.key !== key;
  const data = result?.data ?? null;
  const offline = !loading && result !== null && data === null;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const run = (f: Filters = draft) => { setApplied(f); setPage(1); };
  const reset = () => { setDraft(EMPTY); run(EMPTY); };
  const sortBy = (s: Sort) => {
    if (s === sort) setOrder(o => (o === 'asc' ? 'desc' : o === 'desc' ? 'asc' : (s === 'pe' || s === 'de' || s === 'name' ? 'desc' : 'asc')));
    else { setSort(s); setOrder(undefined); }
    setPage(1);
  };
  const arrow = (s: Sort) => (s !== sort ? '' : order === 'asc' ? ' ▲' : order === 'desc' ? ' ▼' : (s === 'pe' || s === 'de' || s === 'name' ? ' ▲' : ' ▼'));

  const field = (k: keyof Filters, label: string, placeholder: string, hint: string) => (
    <div>
      <div className="field-label">{label}</div>
      <input className="fi" inputMode="decimal" value={draft[k]} placeholder={placeholder} title={hint}
        onChange={e => setDraft(d => ({ ...d, [k]: e.target.value }))} onKeyDown={e => e.key === 'Enter' && run()} />
    </div>
  );

  const th = (s: Sort | null, label: string, align: 'left' | 'right' | 'center' = 'right') => (
    <th style={{ textAlign: align, cursor: s ? 'pointer' : 'default', whiteSpace: 'nowrap' }} onClick={() => s && sortBy(s)}>
      {label}{s ? arrow(s) : ''}
    </th>
  );

  return (
    <div>
      <div className="card" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <div style={{ width: 3, height: 16, background: 'var(--gold)', borderRadius: 2 }} />
          <span className="ct" style={{ marginBottom: 0 }}>Filter universe · NSE</span>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          {data && <span className="pill pill-gold">{data.total.toLocaleString('en-IN')} stocks</span>}
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {PRESETS.map(p => (
            <button key={p.label} title={p.hint} onClick={() => { const f = { ...EMPTY, ...p.f }; setDraft(f); run(f); }}
              style={{ background: 'var(--s2)', border: '1px solid var(--border)', borderRadius: 5, padding: '6px 12px', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left' }}>
              <div style={{ fontSize: 11, color: 'var(--gold)', fontWeight: 600 }}>{p.label}</div>
              <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 2 }}>{p.hint}</div>
            </button>
          ))}
        </div>

        <div className="g3" style={{ marginBottom: 12 }}>
          <div>
            <div className="field-label">Sector</div>
            <select className="fi" value={draft.sector} onChange={e => setDraft(d => ({ ...d, sector: e.target.value }))}>
              <option value="">All sectors</option>
              {sectors.map(s => <option key={s.code} value={s.code}>{s.label} ({s.stocks})</option>)}
            </select>
          </div>
          <div>
            <div className="field-label">Market cap</div>
            <select className="fi" value={draft.cap} onChange={e => setDraft(d => ({ ...d, cap: e.target.value as Filters['cap'] }))}>
              <option value="">All</option>
              <option value="large">Large (above ₹1 lakh Cr)</option>
              <option value="mid">Mid (₹30,000 Cr – ₹1 lakh Cr)</option>
              <option value="small">Small (below ₹30,000 Cr)</option>
            </select>
          </div>
          {field('min_score', 'Minimum score', 'e.g. 60', 'StockSense score, 0–100')}
        </div>
        <div className="g3" style={{ marginBottom: 16 }}>
          {field('max_pe', 'Maximum P/E', 'e.g. 25', 'Price to earnings: lower means cheaper per rupee of profit')}
          {field('min_roe', 'Minimum ROE %', 'e.g. 15', 'Return on equity: profit on every ₹100 of shareholders’ money')}
          {field('max_de', 'Maximum debt / equity', 'e.g. 1', 'Borrowing for every rupee shareholders own')}
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn-gold-main" onClick={() => run()}><span>Run screener ↗</span></button>
          <button className="btn-ghost" onClick={reset}>Reset</button>
          <span style={{ fontSize: 10, color: 'var(--cream-mute)', marginLeft: 4 }}>
            P/E, ROE and debt filters skip companies without that figure. Click a column to sort, a row to open the company.
          </span>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 3, height: 16, background: 'var(--gold)', borderRadius: 2 }} />
            <span className="ct" style={{ marginBottom: 0 }}>Results{data ? ` · ${data.total.toLocaleString('en-IN')} stocks` : ''}</span>
          </div>
          {data && data.total > PAGE_SIZE && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 10, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)' }}>
              <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹</button>
              <span>Page {page} of {pages}</span>
              <button className="btn-ghost" disabled={page >= pages} onClick={() => setPage(p => Math.min(pages, p + 1))}>›</button>
            </div>
          )}
        </div>

        {offline ? (
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.8 }}>
            The StockSense API at <span style={{ fontFamily: 'var(--f-mono)' }}>{API_URL}</span> isn&apos;t reachable, so the screener has no data.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', opacity: loading ? 0.55 : 1, transition: 'opacity .2s' }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 28 }}>#</th>
                  {th('name', 'Company', 'left')}
                  <th>Sector</th>
                  {th('score', 'Score', 'center')}
                  {th('market_cap', 'Market cap')}
                  {th('change_pct', 'Today')}
                  {th('pe', 'P/E')}
                  {th('roe', 'ROE')}
                  {th('de', 'D/E')}
                </tr>
              </thead>
              <tbody>
                {data?.results.map((r, i) => (
                  <tr key={r.symbol} onClick={() => router.push(`/analysis?s=${encodeURIComponent(r.symbol)}`)} style={{ cursor: 'pointer' }}>
                    <td style={{ color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)', fontSize: 10 }}>{String((page - 1) * PAGE_SIZE + i + 1).padStart(2, '0')}</td>
                    <td>
                      <div style={{ fontWeight: 700, fontSize: 12, letterSpacing: '-0.3px', color: 'var(--cream)' }}>{r.name ?? r.symbol}</div>
                      <div style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--gold)', marginTop: 2 }}>{r.symbol}</div>
                    </td>
                    <td><span className="ct" style={{ marginBottom: 0 }}>{r.sector_label}</span></td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--f-mono)', fontWeight: 600, color: stockScoreColor(r.score) }}>{r.score ?? '—'}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtCrore(r.market_cap)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11, color: (r.change_pct ?? 0) < 0 ? 'var(--red)' : 'var(--green)' }}>{fmtPct(r.change_pct, 2, true)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtNum(r.pe)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtPct(r.roe)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtNum(r.de, 2)}</td>
                  </tr>
                ))}
                {data && data.results.length === 0 && (
                  <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--cream-mute)', padding: 24 }}>No company passes these filters. Loosen one and run again.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 12 }}>
          Screens describe companies by their numbers; they are a starting point for reading, not a list of recommendations.
        </p>
      </div>
    </div>
  );
}
