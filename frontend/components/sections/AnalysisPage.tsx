'use client';
import { useState, useCallback, useEffect } from 'react';
import { SD, MM, C } from '@/lib/constants';
import { MetricKey } from '@/lib/types';
import { Pill } from '@/components/ui/Pill';
import { CandleChart } from '@/components/cards/CandleChart';
import { MetricCard } from '@/components/cards/MetricCard';
import { MetricOverlay } from '@/components/cards/MetricOverlay';

export function AnalysisPage() {
  const [query, setQuery] = useState('Infosys');
  const [stock, setStock] = useState<{ key: string; data: typeof SD[string] } | null>(null);
  const [activeMetric, setActiveMetric] = useState<MetricKey | null>(null);

  const doAnalyse = useCallback((q: string) => {
    const key = Object.keys(SD).find(k => k.toLowerCase().includes(q.toLowerCase())) || 'Infosys';
    setStock({ key, data: SD[key] });
    setActiveMetric(null);
  }, []);

  useEffect(() => { doAnalyse('Infosys'); }, [doAnalyse]);

  const s = stock?.data;
  const key = stock?.key || '';
  const vs = s
    ? (s.score >= 70 ? ['pill-g', 'Strong Buy'] : s.score >= 55 ? ['pill-gold', 'Moderate'] : ['pill-r', 'Risky'])
    : [];

  const scoreColor = s ? (s.score >= 70 ? 'var(--green)' : s.score >= 55 ? 'var(--gold)' : 'var(--red)') : 'var(--cream)';

  const quickPicks = [
    ['Infosys', 'INFY', 'IT Services'],
    ['HDFC Bank', 'HDFCBANK', 'Banking'],
    ['Tata Motors', 'TATAMOTORS', 'Auto'],
    ['Zomato', 'ZOMATO', 'Consumer'],
  ];

  return (
    <div>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          className="fi"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doAnalyse(query)}
          placeholder="Search — INFY · HDFCBANK · TATAMOTORS · ZOMATO"
          style={{ flex: 1 }}
        />
        <button className="btn-gold-main" onClick={() => doAnalyse(query)}><span>Analyse ↗</span></button>
      </div>

      {/* Quick picks */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        <span className="ct" style={{ alignSelf: 'center', marginBottom: 0 }}>Quick:</span>
        {quickPicks.map(([k, ticker, sector]) => (
          <button
            key={k}
            onClick={() => { setQuery(k); doAnalyse(k); }}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', background: 'var(--s2)', border: `1px solid ${query === k || (stock?.key || '') === k ? 'var(--border-bright)' : 'var(--border)'}`, borderRadius: 5, padding: '6px 12px', cursor: 'pointer', transition: 'all .15s', fontFamily: 'inherit' }}
          >
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, fontWeight: 500, color: 'var(--gold)' }}>{ticker}</span>
            <span style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 1 }}>{sector}</span>
          </button>
        ))}
      </div>

      {s && (
        <div>
          {/* Stock hero header */}
          <div style={{ background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px', marginBottom: 14, position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${scoreColor},transparent)` }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
              {/* Left: Identity */}
              <div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, fontWeight: 500, color: 'var(--gold)', background: 'rgba(201,168,76,0.07)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 3, padding: '3px 9px', letterSpacing: '1.5px', textTransform: 'uppercase' }}>NSE: {s.ticker}</span>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>{s.sub}</span>
                </div>
                <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.8px', color: 'var(--cream)', marginBottom: 2, fontFamily: 'var(--f-display)' }}>{key} Ltd.</div>
                <div style={{ display: 'flex', gap: 12, marginTop: 10 }}>
                  <span className={vs[0]}>{vs[1]}</span>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)', alignSelf: 'center' }}>52W Range: ₹1,240 – ₹1,924</span>
                </div>
              </div>

              {/* Right: Price + Score */}
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="ct" style={{ marginBottom: 4 }}>Last Price</div>
                  <div style={{ fontSize: 22, fontWeight: 500, fontFamily: 'var(--f-mono)', color: 'var(--cream)', letterSpacing: '-1.5px', lineHeight: 1 }}>{s.price}</div>
                  <div style={{ fontSize: 12, fontWeight: 500, marginTop: 6, color: s.chg.startsWith('-') ? C.red : C.green, fontFamily: 'var(--f-mono)' }}>{s.chg} today</div>
                </div>
                <div style={{ width: 1, height: 64, background: 'var(--border)', flexShrink: 0, alignSelf: 'center' }} />
                <div style={{ textAlign: 'center' }}>
                  <div className="ct" style={{ marginBottom: 4 }}>StockSense Score</div>
                  <div style={{ fontSize: 20, fontWeight: 500, fontFamily: 'var(--f-mono)', color: scoreColor, letterSpacing: '-2px', lineHeight: 1 }}>{s.score}</div>
                  <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 4, fontWeight: 500, letterSpacing: '0.5px', fontFamily: 'var(--f-mono)' }}>OUT OF 100</div>
                </div>
              </div>
            </div>
          </div>

          <CandleChart />

          <div className="mc-grid">
            {(Object.keys(MM) as MetricKey[]).map(mk => (
              <MetricCard
                key={mk}
                mk={mk}
                val={s.data[mk]}
                sector={s.sector}
                onOpen={() => setActiveMetric(mk)}
              />
            ))}
          </div>

          {/* Disclosure */}
          <div className="geo-alert" style={{ marginTop: 14, padding: '12px 16px' }}>
            <div style={{ fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
              <strong style={{ color: 'var(--red)' }}>Disclosure — </strong>StockSense is educational only. Not SEBI-registered investment advice. Consult a registered advisor before investing.
            </div>
          </div>
        </div>
      )}

      {activeMetric && s && (
        <MetricOverlay
          mk={activeMetric}
          val={s.data[activeMetric]}
          sector={s.sector}
          onClose={() => setActiveMetric(null)}
        />
      )}
    </div>
  );
}