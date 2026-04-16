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

export function RHPPage() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<null | 'done'>(null);

  const rhpDemo = () => {
    setScanning(true);
    setTimeout(() => { setScanning(false); setResults('done'); }, 1400);
  };

  const risks = [
    { level: 'HIGH', c: 'r', title: 'Concentrated Revenue Risk', body: 'Top 3 customers account for 68% of total revenue — significant client concentration risk.' },
    { level: 'HIGH', c: 'r', title: 'Promoter Litigation Pending', body: '2 civil suits pending against promoter group for ₹42 Cr. Material if adverse judgment.' },
    { level: 'MED', c: 'gold', title: 'Use of Proceeds — Partial Clarity', body: '₹420 Cr for "general corporate purposes" lacks specific deployment plan in DRHP.' },
    { level: 'LOW', c: 'g', title: 'Peer Comparison Fair', body: 'Comparable company selection methodology is appropriate and disclosed transparently.' },
    { level: 'MED', c: 'gold', title: 'EV Market Dependency', body: '100% revenue from EV segment — highly sensitive to EV adoption rate changes and subsidy policy.' },
  ];

  return (
    <div className="g2">
      <div>
        <div className="rhp-upload" onClick={rhpDemo} style={{ opacity: scanning ? 0.5 : 1 }}>
          <div style={{ fontSize: 32, marginBottom: 10, opacity: 0.4 }}>📄</div>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 5 }}>Upload RHP / DRHP</div>
          <div style={{ fontSize: 11, color: C.ink2, marginBottom: 14 }}>AI extracts key risk factors in seconds. Drop a PDF or click to browse.</div>
          <button className="btn-blue" onClick={e => { e.stopPropagation(); rhpDemo(); }}>Try Demo: Ather Energy DRHP ↗</button>
        </div>
        <div className="card" style={{ marginTop: 12 }}>
          <div className="ct">What We Scan For</div>
          <StatRow label="Related party transactions" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Promoter litigation" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Revenue concentration" value={<Pill type="gold">Medium</Pill>} />
          <StatRow label="DRHP vs actual financials" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Use of proceeds clarity" value={<Pill type="g">Low Risk</Pill>} />
          <StatRow label="Peer comparison fairness" value={<Pill type="gold">Medium</Pill>} />
        </div>
      </div>

      <div>
        {results === null ? (
          <div className="card" style={{ textAlign: 'center', padding: 36 }}>
            <div style={{ fontSize: 28, opacity: 0.2, marginBottom: 8 }}>◈</div>
            <div style={{ fontSize: 12, color: C.ink3 }}>Upload a DRHP or try the demo to see AI risk extraction</div>
          </div>
        ) : (
          <div className="card" style={{ marginBottom: 10 }}>
            <div className="ct">RHP Analysis · Ather Energy DRHP</div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
              <span className="pill pill-gold">Risk Score: 58/100</span>
              <span className="pill pill-gold">MODERATE RISK</span>
            </div>
            <div style={{ fontSize: 11, color: C.ink2, marginBottom: 12, lineHeight: 1.6 }}>AI extracted {risks.length} key risk factors from 342 pages. 2 high-severity items require attention before subscribing.</div>
            {risks.map(r => (
              <div key={r.title} className="rhp-risk-item">
                <div className="status-dot" style={{ background: r.c === 'r' ? C.red : r.c === 'g' ? C.green : C.gold, boxShadow: `0 0 5px ${r.c === 'r' ? C.red : r.c === 'g' ? C.green : C.gold}`, marginTop: 3, flexShrink: 0 }} />
                <div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: C.ink }}>{r.title}</span>
                    <span className={`pill pill-${r.c}`} style={{ fontSize: 8 }}>{r.level}</span>
                  </div>
                  <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.6 }}>{r.body}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
