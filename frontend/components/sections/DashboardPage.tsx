'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Page } from '@/lib/types';
import { supabase } from '@/lib/supabase';
import type { Geopolitics, IndexQuote, NewsEvent, Overview, StockOut } from '@/lib/api';
import { api, effectPill, fmtNum, fmtPct, fmtRupees, stockScoreColor, timeAgo } from '@/lib/api';
import { WatchlistCard } from '@/components/cards/WatchlistCard';
import { EconomyCard } from '@/components/cards/EconomyCard';

const INDEX_ORDER = ['NIFTY50', 'SENSEX', 'BANKNIFTY', 'INDIAVIX'];
const INDEX_LABEL: Record<string, string> = { NIFTY50: 'NIFTY 50', SENSEX: 'SENSEX', BANKNIFTY: 'BANK NIFTY', INDIAVIX: 'INDIA VIX' };

/** Index quotes from the API; if it is down, fall back to Supabase's live_prices table. */
async function loadIndices(): Promise<IndexQuote[] | null> {
  const fromApi = await api.indices();
  if (fromApi) return fromApi;
  if (!supabase) return null;
  const { data, error } = await supabase.from('live_prices').select('symbol, price').in('symbol', INDEX_ORDER);
  if (error || !data) return null;
  return (data as { symbol: string; price: number }[]).map(r => ({ symbol: r.symbol, label: INDEX_LABEL[r.symbol] ?? r.symbol, price: r.price, change_pct: null, updated_at: null }));
}

export function DashboardPage({ onNav }: { onNav: (p: Page) => void }) {
  const router = useRouter();
  const [indices, setIndices] = useState<IndexQuote[] | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [news, setNews] = useState<NewsEvent[] | null>(null);
  const [geo, setGeo] = useState<Geopolitics | null>(null);
  const [moverTab, setMoverTab] = useState<'gainers' | 'losers'>('gainers');

  useEffect(() => {
    let alive = true;
    const tickIndices = () => loadIndices().then(r => { if (alive && r) setIndices(r); });
    const tickMarket = () => api.overview().then(r => { if (alive && r) setOverview(r); });
    tickIndices();
    tickMarket();
    api.news({ limit: 6 }).then(r => { if (alive) setNews(r); });
    api.geopolitics(0).then(r => { if (alive) setGeo(r); });
    const a = setInterval(tickIndices, 15000);
    const b = setInterval(tickMarket, 60000);
    return () => { alive = false; clearInterval(a); clearInterval(b); };
  }, []);

  const quotes = INDEX_ORDER.map(sym => indices?.find(i => i.symbol === sym) ?? { symbol: sym, label: INDEX_LABEL[sym], price: null as number | null, change_pct: null as number | null });

  const sectors = overview?.sectors ?? [];
  const shownSectors = sectors.length > 8 ? [...sectors.slice(0, 4), ...sectors.slice(-4)] : sectors;
  const maxMove = Math.max(0.5, ...shownSectors.map(s => Math.abs(s.change_pct)));

  const breadth = overview?.breadth;
  const total = breadth ? breadth.advancers + breadth.decliners + breadth.unchanged : 0;
  const advPct = breadth && total ? Math.round((breadth.advancers / total) * 100) : null;
  const CIRC = 175.9;

  const movers: StockOut[] = overview ? overview.movers[moverTab].slice(0, 6) : [];
  const topExposure = geo?.exposure.find(e => e.effect === 'risk') ?? geo?.exposure[0];
  const open = (s: string) => router.push(`/analysis?s=${encodeURIComponent(s)}`);

  return (
    <div>
      {/* Index strip */}
      <div className="idx-strip" style={{ marginBottom: 20 }}>
        {quotes.map(q => {
          const vix = q.symbol === 'INDIAVIX';
          // For VIX a fall means calmer markets, so colour it the other way round.
          const up = (q.change_pct ?? 0) >= 0;
          const good = vix ? !up : up;
          return (
            <div key={q.symbol} className="idx-card" title={vix ? 'Expected volatility over the next 30 days; lower means calmer markets' : undefined}>
              <div className="idx-name">{INDEX_LABEL[q.symbol] ?? q.label}</div>
              <div className="idx-val">{q.price === null ? '—' : fmtNum(q.price, 2)}</div>
              <div className="idx-chg" style={{ color: q.change_pct === null ? 'var(--cream-mute)' : good ? 'var(--green)' : 'var(--red)' }}>{fmtPct(q.change_pct, 2, true)}</div>
            </div>
          );
        })}
      </div>

      <div className="split" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 340px', gap: 12, marginBottom: 14 }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
          <WatchlistCard />
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div className="ct" style={{ marginBottom: 0 }}>Sector performance · today</div>
              <span className="pill pill-gold">Best and worst</span>
            </div>
            {shownSectors.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {shownSectors.map(s => {
                  const c = s.change_pct >= 0 ? 'green' : 'red';
                  return (
                    <div key={s.sector} style={{ display: 'flex', alignItems: 'center', gap: 12 }} title={`${s.advancers} up, ${s.decliners} down`}>
                      <div style={{ width: 150, fontSize: 12, color: 'var(--cream)', fontWeight: 500, flexShrink: 0 }}>{s.label}</div>
                      <div style={{ flex: 1, height: 4, background: 'rgba(201,168,76,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${(Math.abs(s.change_pct) / maxMove) * 100}%`, height: '100%', background: `var(--${c})`, borderRadius: 2, opacity: 0.8 }} />
                      </div>
                      <div style={{ width: 60, textAlign: 'right', fontSize: 11, fontWeight: 500, fontFamily: 'var(--f-mono)', color: `var(--${c})` }}>{fmtPct(s.change_pct, 2, true)}</div>
                    </div>
                  );
                })}
              </div>
            ) : <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>Market data isn&apos;t available right now.</div>}
            <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 12 }}>Average move of the companies in each sector, weighted by size.</p>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div className="ct" style={{ marginBottom: 0 }}>Top movers · NSE</div>
              <div style={{ display: 'flex', gap: 4 }}>
                {(['gainers', 'losers'] as const).map(t => (
                  <button key={t} onClick={() => setMoverTab(t)}
                    style={{ fontSize: 9, padding: '3px 9px', borderRadius: 3, cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'var(--f-body)', background: t === moverTab ? 'rgba(201,168,76,0.12)' : 'transparent', color: t === moverTab ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${t === moverTab ? 'var(--border-bright)' : 'var(--border)'}` }}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th style={{ textAlign: 'right' }}>Price</th>
                    <th style={{ textAlign: 'right' }}>Change</th>
                    <th style={{ textAlign: 'center' }} title="StockSense score: fundamentals against sector peers">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {movers.map(m => (
                    <tr key={m.symbol} onClick={() => open(m.symbol)} style={{ cursor: 'pointer' }}>
                      <td>
                        <div style={{ fontWeight: 700, fontFamily: 'var(--f-mono)', fontSize: 11.5, color: 'var(--gold)' }}>{m.symbol}</div>
                        <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 2, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.name}{m.sector_label ? ` · ${m.sector_label}` : ''}</div>
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 500, fontSize: 11.5 }}>{fmtRupees(m.price)}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontWeight: 500, color: (m.change_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>{fmtPct(m.change_pct, 2, true)}</td>
                      <td style={{ textAlign: 'center', fontFamily: 'var(--f-mono)', color: stockScoreColor(m.score) }}>{m.score ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>
              A big one-day move says what the market did, not whether the company is good. The score column shows how its fundamentals compare with its peers.
            </p>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="card">
            <div className="ct">Market breadth · NSE</div>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <svg width="72" height="72" viewBox="0 0 72 72" style={{ flexShrink: 0 }} role="img" aria-label={advPct === null ? 'No data' : `${advPct}% of stocks rose`}>
                <circle cx="36" cy="36" r="28" fill="none" stroke="rgba(196,92,92,0.35)" strokeWidth="6" />
                {advPct !== null && (
                  <circle cx="36" cy="36" r="28" fill="none" stroke="var(--green)" strokeWidth="6"
                    strokeDasharray={CIRC} strokeDashoffset={CIRC * (1 - advPct / 100)} strokeLinecap="round" transform="rotate(-90 36 36)" />
                )}
                <text x="36" y="34" textAnchor="middle" fontSize="13" fontWeight="800" fill="var(--cream)" fontFamily="'JetBrains Mono',monospace">{advPct === null ? '—' : `${advPct}%`}</text>
                <text x="36" y="45" textAnchor="middle" fontSize="7" fill="var(--cream-mute)" fontFamily="'JetBrains Mono',monospace" letterSpacing="1">ROSE</text>
              </svg>
              <div style={{ flex: 1 }}>
                {[
                  ['Advances', breadth?.advancers, 'var(--green)'],
                  ['Declines', breadth?.decliners, 'var(--red)'],
                  ['Unchanged', breadth?.unchanged, 'var(--cream)'],
                ].map(([l, v, c], i) => (
                  <div key={l as string} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: i < 2 ? '1px solid rgba(201,168,76,0.04)' : 'none' }}>
                    <span style={{ fontSize: 10, color: 'var(--cream-dim)' }}>{l}</span>
                    <span style={{ fontSize: 10, fontFamily: 'var(--f-mono)', fontWeight: 500, color: c as string }}>{v === undefined ? '—' : (v as number).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </div>
            <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10, lineHeight: 1.6 }}>
              Breadth shows whether a move is broad or carried by a few large companies: an index can rise while most stocks fall.
            </p>
          </div>

          <EconomyCard />

          <div className="card" style={{ flex: 1 }}>
            <div className="ct">Intelligence feed</div>
            {news === null && <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>Headlines aren&apos;t available right now.</div>}
            {news?.map((item, i) => {
              const fx = item.sectors[0];
              return (
                <a key={item.link} href={item.link} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'block', padding: '10px 0', borderBottom: i < news.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none', textDecoration: 'none' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <span className="pill pill-gold" style={{ flexShrink: 0, marginTop: 1 }}>{item.topics[0] ?? 'Markets'}</span>
                    <span style={{ fontSize: 11, color: 'var(--cream)', lineHeight: 1.55, flex: 1 }}>{item.title}</span>
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 5, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <span>{item.source} · {timeAgo(item.published)}</span>
                    {fx && <span className={effectPill(fx.effect)} style={{ fontSize: 8 }}>{fx.sector}: {fx.label}</span>}
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      </div>

      {/* Geopolitics banner */}
      <div className="geo-alert">
        <div className="geo-alert-icon">⚠</div>
        <div style={{ flex: 1 }}>
          <div className="geo-alert-top">
            <div className="pulse-dot" />
            <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '1.8px', textTransform: 'uppercase', color: 'var(--red)' }}>Geopolitics · what the news is about</span>
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--cream)', marginBottom: 3, letterSpacing: '-0.2px' }}>
            {topExposure
              ? `${topExposure.sector}: ${topExposure.label.toLowerCase()} — ${topExposure.headlines} recent headlines`
              : 'Sector exposure to world news'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)' }}>
            {geo
              ? `Most-discussed sectors: ${geo.exposure.slice(0, 3).map(e => e.sector).join(', ')}. Updated ${timeAgo(geo.updated_at)}.`
              : 'Which sectors world events touch, and what similar events did to them in the past.'}
          </div>
        </div>
        <button className="btn-gold-main" onClick={() => onNav('geo')} style={{ flexShrink: 0 }}><span>View full analysis →</span></button>
      </div>
    </div>
  );
}
