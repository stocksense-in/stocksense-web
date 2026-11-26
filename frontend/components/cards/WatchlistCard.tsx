'use client';
import { Fragment, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Alert, StockOut } from '@/lib/api';
import { ALERT_LABEL, api, fmtPct, fmtRupees, stockScoreColor } from '@/lib/api';
import { useWatchlist } from '@/lib/watchlist';

/** The visitor's watchlist with today's prices, scores and each company's latest alert. */
export function WatchlistCard() {
  const router = useRouter();
  const { list, toggle } = useWatchlist();
  const key = list.join(',');
  const [data, setData] = useState<{ key: string; stocks: StockOut[]; alerts: Alert[] } | null>(null);

  useEffect(() => {
    if (!key) return;
    let alive = true;
    Promise.all([
      api.screen({ symbols: key, sort: 'name', page_size: 100 }),
      api.alerts({ symbols: key, days: 10, limit: 300 }),
    ]).then(([s, a]) => {
      if (alive) setData({ key, stocks: s?.results ?? [], alerts: a?.alerts ?? [] });
    });
    return () => { alive = false; };
  }, [key]);

  const fresh = data && data.key === key ? data : null;
  const bySymbol = new Map((fresh?.stocks ?? []).map(s => [s.symbol, s]));
  const latest = new Map<string, Alert>();
  const counts = new Map<string, number>();
  for (const a of fresh?.alerts ?? []) {
    if (!latest.has(a.symbol)) latest.set(a.symbol, a);
    counts.set(a.symbol, (counts.get(a.symbol) ?? 0) + 1);
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="ct" style={{ marginBottom: 0 }}>Your watchlist{list.length ? ` · ${list.length}` : ''}</div>
        <span className="pill pill-b">Saved in this browser</span>
      </div>
      {!list.length && (
        <p className="mc-plain">
          Follow companies to see their price, score and anything notable — big moves, heavy trading, results, order wins, promoter stake changes — here.
          Open a company and press <strong style={{ color: 'var(--gold)' }}>☆ Watch</strong>.
        </p>
      )}
      {list.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table className="tbl">
            <thead><tr><th>Company</th><th style={{ textAlign: 'right' }}>Price</th><th style={{ textAlign: 'right' }}>Today</th><th style={{ textAlign: 'center' }}>Score</th><th /></tr></thead>
            <tbody>
              {list.map(sym => {
                const s = bySymbol.get(sym);
                const a = latest.get(sym);
                const go = () => router.push(`/analysis?s=${encodeURIComponent(sym)}`);
                return (
                  <Fragment key={sym}>
                  <tr onClick={go} style={{ cursor: 'pointer' }}>
                    <td>
                      <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11.5, fontWeight: 700, color: 'var(--gold)' }}>{sym}</div>
                      <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 2, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s?.name ?? ''}</div>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11.5 }}>{fmtRupees(s?.price ?? null)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11.5, color: (s?.change_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>{fmtPct(s?.change_pct ?? null, 2, true)}</td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--f-mono)', color: stockScoreColor(s?.score) }}>{s?.score ?? '—'}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn-ghost" title={`Stop watching ${sym}`} aria-label={`Stop watching ${sym}`}
                        onClick={e => { e.stopPropagation(); toggle(sym); }} style={{ padding: '2px 8px', fontSize: 10 }}>✕</button>
                    </td>
                  </tr>
                  <tr onClick={go} style={{ cursor: 'pointer' }}>
                    <td colSpan={5} style={{ paddingTop: 0, fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.5 }}>
                      {a ? <><span className="pill pill-gold" style={{ fontSize: 7, marginRight: 6 }}>{ALERT_LABEL[a.kind] ?? a.kind}</span>{a.text}{(counts.get(sym) ?? 0) > 1 ? ` (+${(counts.get(sym) ?? 1) - 1} more)` : ''}</>
                        : <span style={{ color: 'var(--cream-mute)' }}>Nothing notable in the last two weeks</span>}
                    </td>
                  </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
