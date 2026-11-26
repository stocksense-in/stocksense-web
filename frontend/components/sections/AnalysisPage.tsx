'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { Alert, CompanyHeadline, Dividends, Financials, History, Holders, StockDetail, StockOut } from '@/lib/api';
import { API_URL, api, fmtCrore, fmtPct, fmtRupees, stockScoreColor, verdictPill } from '@/lib/api';
import { PriceChart } from '@/components/company/PriceChart';
import { ScoreBreakdown } from '@/components/company/ScoreBreakdown';
import { FinancialsPanel } from '@/components/company/FinancialsPanel';
import { HoldersPanel } from '@/components/company/HoldersPanel';
import { DividendsPanel } from '@/components/company/DividendsPanel';
import { PeersTable } from '@/components/company/PeersTable';
import { NewsPanel } from '@/components/company/NewsPanel';
import { AlertsStrip } from '@/components/company/AlertsStrip';
import { useWatchlist } from '@/lib/watchlist';

type Status = 'loading' | 'ok' | 'notfound' | 'offline';
export type CompanyTab = 'score' | 'financials' | 'holders' | 'dividends' | 'peers' | 'news';
type Tab = CompanyTab;
const TABS: Tab[] = ['score', 'financials', 'holders', 'dividends', 'peers', 'news'];

const QUICK: [string, string][] = [
  ['INFY', 'IT Services'], ['HDFCBANK', 'Banking'], ['MARUTI', 'Auto'], ['ITC', 'FMCG'], ['SUNPHARMA', 'Pharma'],
];

const SYMBOL_RE = /^[A-Za-z0-9&_-]{1,20}$/;

/** The company and tab named in the address (?s=INFY&tab=financials). */
function fromUrl(params: URLSearchParams | null): { symbol: string; tab: Tab; key: string } {
  const raw = params?.get('s') ?? '';
  const symbol = SYMBOL_RE.test(raw) ? raw.toUpperCase() : 'INFY';
  const t = params?.get('tab') as Tab | null;
  const tab = t && TABS.includes(t) ? t : 'score';
  return { symbol, tab, key: `${symbol}|${tab}` };
}

interface Company {
  symbol: string;
  status: 'ok' | 'notfound' | 'offline';
  detail: StockDetail | null;
  fin: Financials | null;
  holders: Holders | null;
  divs: Dividends | null;
}

export function AnalysisPage() {
  const params = useSearchParams();
  const url = fromUrl(params);
  const [query, setQuery] = useState('');
  const [found, setFound] = useState<{ q: string; items: StockOut[] }>({ q: '', items: [] });
  const [highlight, setHighlight] = useState(0);
  const [symbol, setSymbol] = useState<string>(url.symbol);
  const [company, setCompany] = useState<Company | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [range, setRange] = useState('1y');
  const [tab, setTab] = useState<Tab>(url.tab);
  const [news, setNews] = useState<{ symbol: string; items: CompanyHeadline[] | null } | null>(null);
  const [seenUrl, setSeenUrl] = useState(url.key);
  const [recentAlerts, setRecentAlerts] = useState<{ symbol: string; items: Alert[] } | null>(null);
  const watch = useWatchlist();

  // When the address changes (command bar, links, back/forward), open what it names.
  // Adjusting state while rendering is React's recommended way to follow a changing input.
  if (url.key !== seenUrl) {
    setSeenUrl(url.key);
    setSymbol(url.symbol);
    setTab(url.tab);
  }
  const searchSeq = useRef(0);

  // Load the company whenever the symbol changes. State is only set after the network
  // answers; "loading" is derived from company.symbol !== symbol.
  useEffect(() => {
    const ctl = new AbortController();
    const { signal } = ctl;
    (async () => {
      const d = await api.stock(symbol, signal);
      if (signal.aborted) return;
      if (!d) {
        const probe = await api.search(symbol, signal);
        if (signal.aborted) return;
        setCompany({ symbol, status: probe === null ? 'offline' : 'notfound', detail: null, fin: null, holders: null, divs: null });
        return;
      }
      setCompany({ symbol, status: 'ok', detail: d, fin: null, holders: null, divs: null });
      const [fin, holders, divs] = await Promise.all([
        d.available.financials ? api.financials(symbol, signal) : Promise.resolve(null),
        d.available.holders ? api.holders(symbol, signal) : Promise.resolve(null),
        d.available.dividends ? api.dividends(symbol, signal) : Promise.resolve(null),
      ]);
      if (signal.aborted) return;
      setCompany(c => (c && c.symbol === symbol ? { ...c, fin, holders, divs } : c));
    })();
    return () => ctl.abort();
  }, [symbol]);

  const loaded = company?.symbol === symbol;
  const status: Status = loaded && company ? company.status : 'loading';

  // Price history follows the symbol and the chosen range.
  useEffect(() => {
    if (status !== 'ok') return;
    const ctl = new AbortController();
    api.history(symbol, range, ctl.signal).then(h => { if (!ctl.signal.aborted) setHistory(h); });
    return () => ctl.abort();
  }, [symbol, range, status]);

  // Type-ahead search: results are kept with the query they answer.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) return;
    const seq = ++searchSeq.current;
    const t = setTimeout(async () => {
      const r = await api.search(q);
      if (seq === searchSeq.current) { setFound({ q, items: r ?? [] }); setHighlight(0); }
    }, 180);
    return () => clearTimeout(t);
  }, [query]);

  const suggestions = query.trim().length >= 2 && found.q === query.trim() ? found.items : [];

  const open = useCallback((s: string) => {
    setSymbol(s.toUpperCase());
    setQuery('');
    setTab('score');
  }, []);

  const submit = () => {
    if (suggestions.length) open(suggestions[Math.min(highlight, suggestions.length - 1)].symbol);
    else if (query.trim()) open(query.trim());
  };

  // While the next company loads, keep showing the previous one (dimmed).
  const detail = company?.detail ?? null;
  const fin = company?.fin ?? null;
  const holders = company?.holders ?? null;
  const divs = company?.divs ?? null;
  const shownHistory = history && detail && history.symbol === detail.stock.symbol ? history : null;
  const s = detail?.stock;
  const sc = detail?.score;
  const tabs: [Tab, string, boolean][] = [
    ['score', 'Score breakdown', true],
    ['financials', 'Financials', !!fin],
    ['holders', 'Holders', !!holders],
    ['dividends', 'Dividends', !!divs],
    ['peers', 'Peers', !!detail?.peers.length],
    ['news', 'News', !!detail],
  ];
  // Show the chosen tab once its data is there; until then (or if this company has none), the score.
  const activeTab: Tab = tabs.some(([k, , ok]) => k === tab && ok) ? tab : 'score';

  // Load headlines the first time the News tab is opened for a company.
  const newsFor = detail?.stock.symbol;
  useEffect(() => {
    if (activeTab !== 'news' || !newsFor || news?.symbol === newsFor) return;
    const ctl = new AbortController();
    api.companyNews(newsFor, 20, ctl.signal).then(items => { if (!ctl.signal.aborted) setNews({ symbol: newsFor, items: items ?? [] }); });
    return () => ctl.abort();
  }, [activeTab, newsFor, news?.symbol]);

  // The company's alerts over the last two weeks.
  useEffect(() => {
    if (!newsFor || recentAlerts?.symbol === newsFor) return;
    const ctl = new AbortController();
    api.alerts({ symbols: newsFor, days: 10 }, ctl.signal).then(r => { if (!ctl.signal.aborted) setRecentAlerts({ symbol: newsFor, items: r?.alerts ?? [] }); });
    return () => ctl.abort();
  }, [newsFor, recentAlerts?.symbol]);

  // Keep the address bar in step, so links and reloads open the same company and tab.
  useEffect(() => {
    if (!newsFor) return;
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('s', newsFor);
      if (tab === 'score') url.searchParams.delete('tab'); else url.searchParams.set('tab', tab);
      window.history.replaceState(window.history.state, '', url.toString());
    } catch { /* ignore */ }
  }, [newsFor, tab]);

  return (
    <div>
      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 10 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="fi"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') submit();
              else if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight(h => Math.min(h + 1, suggestions.length - 1)); }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight(h => Math.max(h - 1, 0)); }
              else if (e.key === 'Escape') setQuery('');
            }}
            placeholder="Search any NSE company — name or symbol (INFY, HDFC Bank, Maruti…)"
            aria-label="Search companies"
            style={{ flex: 1 }}
          />
          <button className="btn-gold-main" onClick={submit}><span>Analyse ↗</span></button>
        </div>
        {suggestions.length > 0 && (
          <div role="listbox" style={{ position: 'absolute', zIndex: 20, top: '100%', left: 0, right: 0, marginTop: 4, background: 'var(--s2)', border: '1px solid var(--border-bright)', borderRadius: 6, overflow: 'hidden' }}>
            {suggestions.map((x, i) => (
              <div key={x.symbol} role="option" aria-selected={i === highlight} onMouseEnter={() => setHighlight(i)} onMouseDown={() => open(x.symbol)}
                style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '8px 12px', cursor: 'pointer', background: i === highlight ? 'rgba(201,168,76,0.08)' : 'transparent' }}>
                <span><span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)', marginRight: 10 }}>{x.symbol}</span><span style={{ fontSize: 11, color: 'var(--cream)' }}>{x.name}</span></span>
                <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>{x.sector_label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick picks */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        <span className="ct" style={{ alignSelf: 'center', marginBottom: 0 }}>Quick:</span>
        {QUICK.map(([ticker, sector]) => (
          <button key={ticker} onClick={() => open(ticker)}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', background: 'var(--s2)', border: `1px solid ${s?.symbol === ticker ? 'var(--border-bright)' : 'var(--border)'}`, borderRadius: 5, padding: '6px 12px', cursor: 'pointer', transition: 'all .15s', fontFamily: 'inherit' }}>
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, fontWeight: 500, color: 'var(--gold)' }}>{ticker}</span>
            <span style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 1 }}>{sector}</span>
          </button>
        ))}
      </div>

      {status === 'loading' && !detail && (
        <div className="card" style={{ textAlign: 'center', fontSize: 11, color: 'var(--cream-mute)', padding: 40 }}>Loading…</div>
      )}

      {status === 'notfound' && (
        <div className="card" style={{ fontSize: 12, color: 'var(--cream-dim)', padding: 24 }}>
          No NSE company matches <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--gold)' }}>{symbol}</span>. Try its name or another symbol.
        </div>
      )}

      {status === 'offline' && (
        <div className="geo-alert" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.8 }}>
            <strong style={{ color: 'var(--gold)' }}>Company data is offline. </strong>
            The StockSense API at <span style={{ fontFamily: 'var(--f-mono)' }}>{API_URL}</span> isn&apos;t reachable.
            Locally, start it with <span style={{ fontFamily: 'var(--f-mono)' }}>cd backend &amp;&amp; python -m stocksense api</span>, or set
            <span style={{ fontFamily: 'var(--f-mono)' }}> NEXT_PUBLIC_API_URL</span>.
          </div>
        </div>
      )}

      {s && sc && detail && status !== 'notfound' && status !== 'offline' && (
        <div style={{ opacity: status === 'loading' ? 0.55 : 1, transition: 'opacity .2s' }}>
          {/* Hero */}
          <div style={{ background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px', marginBottom: 14, position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${stockScoreColor(sc.value)},transparent)` }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, fontWeight: 500, color: 'var(--gold)', background: 'rgba(201,168,76,0.07)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 3, padding: '3px 9px', letterSpacing: '1.5px', textTransform: 'uppercase' }}>NSE: {s.symbol}</span>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>{[s.sector_label, s.industry].filter(Boolean).join(' · ')}</span>
                </div>
                <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.8px', color: 'var(--cream)', marginBottom: 2, fontFamily: 'var(--f-display)' }}>{s.name ?? s.symbol}</div>
                <div style={{ display: 'flex', gap: 12, marginTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                  {sc.verdict && <span className={verdictPill(sc.verdict)}>{sc.verdict} fundamentals</span>}
                  <button onClick={() => watch.toggle(s.symbol)} aria-pressed={watch.has(s.symbol)} disabled={!watch.has(s.symbol) && watch.full}
                    title={watch.has(s.symbol) ? 'Remove from your watchlist' : 'Add to your watchlist (saved in this browser)'}
                    style={{ fontSize: 10, padding: '3px 10px', borderRadius: 3, cursor: 'pointer', fontFamily: 'var(--f-body)', background: watch.has(s.symbol) ? 'rgba(201,168,76,0.12)' : 'transparent', color: 'var(--gold)', border: '1px solid var(--border-bright)' }}>
                    {watch.has(s.symbol) ? '★ Watching' : '☆ Watch'}
                  </button>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>52W range: {fmtRupees(s.week52_low, 0)} – {fmtRupees(s.week52_high, 0)}</span>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>Market cap: {fmtCrore(s.market_cap)}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="ct" style={{ marginBottom: 4 }}>Last price</div>
                  <div style={{ fontSize: 22, fontWeight: 500, fontFamily: 'var(--f-mono)', color: 'var(--cream)', letterSpacing: '-1.5px', lineHeight: 1 }}>{fmtRupees(s.price)}</div>
                  {s.change_pct !== null && (
                    <div style={{ fontSize: 12, fontWeight: 500, marginTop: 6, color: s.change_pct < 0 ? 'var(--red)' : 'var(--green)', fontFamily: 'var(--f-mono)' }}>{fmtPct(s.change_pct, 2, true)} today</div>
                  )}
                </div>
                <div style={{ width: 1, height: 64, background: 'var(--border)', flexShrink: 0, alignSelf: 'center' }} />
                <div style={{ textAlign: 'center' }}>
                  <div className="ct" style={{ marginBottom: 4 }}>StockSense score</div>
                  <div style={{ fontSize: 20, fontWeight: 500, fontFamily: 'var(--f-mono)', color: stockScoreColor(sc.value), letterSpacing: '-2px', lineHeight: 1 }}>{sc.value ?? '—'}</div>
                  <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 4, fontWeight: 500, letterSpacing: '0.5px', fontFamily: 'var(--f-mono)' }}>OUT OF 100 · {sc.coverage}/{6 - (sc.not_applicable?.length ?? 0)} METRICS</div>
                </div>
              </div>
            </div>
            {s.stale && (
              <div style={{ fontSize: 10, color: 'var(--gold)', marginTop: 12 }}>These figures haven&apos;t been refreshed recently{s.updated_at ? ` (last ${s.updated_at.slice(0, 10)})` : ''}.</div>
            )}
          </div>

          {recentAlerts?.symbol === s.symbol && <AlertsStrip alerts={recentAlerts.items} />}

          <PriceChart history={shownHistory} range={range} onRange={setRange} />

          {/* Tabs */}
          <div role="tablist" style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '16px 0 12px' }}>
            {tabs.filter(([, , ok]) => ok).map(([key, label]) => (
              <button key={key} role="tab" aria-selected={activeTab === key} onClick={() => setTab(key)}
                style={{ fontSize: 10, padding: '6px 14px', borderRadius: 4, cursor: 'pointer', letterSpacing: '1px', textTransform: 'uppercase', fontFamily: 'var(--f-body)', fontWeight: 600, background: activeTab === key ? 'rgba(201,168,76,0.12)' : 'var(--s1)', color: activeTab === key ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${activeTab === key ? 'var(--border-bright)' : 'var(--border)'}` }}>
                {label}
              </button>
            ))}
          </div>

          {activeTab === 'score' && <ScoreBreakdown score={sc} />}
          {activeTab === 'financials' && fin && <FinancialsPanel fin={fin} />}
          {activeTab === 'holders' && holders && <HoldersPanel h={holders} />}
          {activeTab === 'dividends' && divs && <DividendsPanel d={divs} />}
          {activeTab === 'peers' && <PeersTable stock={s} peers={detail.peers} onOpen={open} />}
          {activeTab === 'news' && <NewsPanel name={s.name ?? s.symbol} items={news?.symbol === s.symbol ? news.items : null} />}

          <div className="geo-alert" style={{ marginTop: 14, padding: '12px 16px' }}>
            <div style={{ fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
              <strong style={{ color: 'var(--red)' }}>Disclosure: </strong>StockSense is educational only. The score describes a company&apos;s fundamentals against its peers; it is not a recommendation to buy or sell and not SEBI-registered investment advice.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
