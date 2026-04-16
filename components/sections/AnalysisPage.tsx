'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Page, StockData, Holding, IPO, MetricKey, MetricMeta, Sector } from '@/lib/types';
import { SD, MM, IPOS, SCREENER, GEO_SECTORS, GEO_EVENTS, NICHE, PT_STOCKS, PAGE_TITLES, NAV_ITEMS, C } from '@/lib/constants';
import { pillClass, getMetricStatus, scoreColor, formatINR } from '@/lib/utils';
import { supabase } from '@/lib/supabase';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';
import { SectionDiv } from '@/components/ui/SectionDiv';
import { CandleChart } from '@/components/cards/CandleChart';
import { MetricCard } from '@/components/cards/MetricCard';

export function AnalysisPage() {
  const [query, setQuery] = useState('Infosys');
  const [stock, setStock] = useState<{ key: string; data: StockData } | null>(null);

  const doAnalyse = useCallback((q: string) => {
    const key = Object.keys(SD).find(k => k.toLowerCase().includes(q.toLowerCase())) || 'Infosys';
    setStock({ key, data: SD[key] });
  }, []);

  useEffect(() => { doAnalyse('Infosys'); }, [doAnalyse]);

  const s = stock?.data;
  const key = stock?.key || '';
  const vs = s ? (s.score >= 70 ? ['pill-g', 'Strong'] : s.score >= 55 ? ['pill-gold', 'Moderate'] : ['pill-r', 'Risky']) : [];

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input className="fi" value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doAnalyse(query)}
          placeholder="Search — INFY · HDFCBANK · TATAMOTORS · ZOMATO" style={{ flex: 1 }} />
        <button className="btn-blue" onClick={() => doAnalyse(query)}>Analyse ↗</button>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 1, color: C.ink3, alignSelf: 'center' }}>QUICK:</span>
        {[['Infosys', 'INFY'], ['HDFC Bank', 'HDFCBANK'], ['Tata Motors', 'TATAMOTORS'], ['Zomato', 'ZOMATO']].map(([k, label]) => (
          <span key={k} className="pill pill-b" style={{ cursor: 'pointer', padding: '4px 10px' }}
            onClick={() => { setQuery(k); doAnalyse(k); }}>{label}</span>
        ))}
      </div>

      {s && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: 14, borderBottom: '1px solid var(--border)', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.blue, marginBottom: 4 }}>{s.ticker}</div>
              <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.3px' }}>{key} Ltd</div>
              <div style={{ fontSize: 11, color: C.ink2, marginTop: 3 }}>{s.sub}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>{s.price}</div>
              <div style={{ fontSize: 11, fontWeight: 600, marginTop: 2, color: s.chg.startsWith('-') ? C.red : C.green }}>{s.chg} today</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginTop: 6 }}>
                <span style={{ fontSize: 10, color: C.ink2 }}>Score</span>
                <span style={{ fontSize: 20, fontWeight: 800 }}>{s.score}</span>
                <span className={`pill ${vs[0]}`}>{vs[1]}</span>
              </div>
            </div>
          </div>

          <CandleChart />

          <div className="mc-grid">
            {(Object.keys(MM) as MetricKey[]).map(mk => (
              <MetricCard key={mk} mk={mk} val={s.data[mk]} sector={s.sector} />
            ))}
          </div>

          <div style={{ marginTop: 10, padding: '10px 14px', background: 'var(--red2)', border: '1px solid rgba(255,58,58,.15)', borderRadius: 8, fontSize: 10, color: C.ink2 }}>
            <strong style={{ color: C.red }}>Disclosure —</strong> StockSense is educational only. Not SEBI-registered investment advice. Consult a registered advisor before investing.
          </div>
        </div>
      )}
    </div>
  );
}
