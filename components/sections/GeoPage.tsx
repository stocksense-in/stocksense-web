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

export function GeoPage() {
  const hist = [
    ['Iran-Israel Apr 2024', '2 weeks', 'Oil +8%, Gold +6%, Aviation -4%', '-1.2%'],
    ['Russia-Ukraine Feb 2022', '3 months', 'Defence +22%, Oil +32%, Metals +14%', '-8.4%'],
    ['COVID Mar 2020', '6 months', 'Pharma +18%, Aviation -45%, IT -12%', '-38%'],
    ['India-China Galwan 2020', '1 month', 'Defence +15%, China-exposed -8%', '-3.6%'],
  ];

  return (
    <div>
      <div className="geo-alert">
        <div className="geo-alert-top">
          <div className="pulse-dot" />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: C.red }}>Active High Risk Alert</span>
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: C.ink, marginBottom: 3 }}>Middle East tensions elevated — Strait of Hormuz disruption risk</div>
        <div style={{ fontSize: 11, color: C.ink2 }}>Affects: Oil &amp; Gas · Aviation · Gold/Silver safe-haven · Defence opportunity | Updated 2 hours ago · 14 sources</div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Global Pulse Feed</div>
          {GEO_EVENTS.map((e, i) => (
            <div key={i} className={`event-card ${e.cls}`}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className={`pill ${e.tag === 'CONFLICT' || e.tag === 'OIL' ? 'pill-r' : e.tag === 'COMMODITY' || e.tag === 'AGRI' ? 'pill-gold' : 'pill-b'}`}>{e.tag}</span>
                {e.cls === 'ev-gold' && <span style={{ fontSize: 9, color: C.gold, fontWeight: 700 }}>● GOLD SAFE HAVEN</span>}
              </div>
              <div style={{ fontSize: 11, color: C.ink, lineHeight: 1.5 }}>{e.title}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="ct">Sector Risk Matrix · Live</div>
          {GEO_SECTORS.map(g => (
            <div key={g.s} className="stat-r">
              <span className="sl" style={{ minWidth: 110 }}>{g.s}</span>
              <div style={{ flex: 1, margin: '0 10px' }}>
                <div className="bar-track" style={{ height: 4 }}>
                  <div className="bar-fill" style={{ width: `${g.risk}%`, background: g.c === 'r' ? C.red : g.c === 'g' ? C.green : C.gold }} />
                </div>
              </div>
              <span className={`pill pill-${g.c}`} style={{ fontSize: 8, minWidth: 72, justifyContent: 'center' }}>{g.impact}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="ct">Historical Precedents — How Markets Reacted</div>
        <table className="tbl">
          <thead><tr><th>Event</th><th>Period</th><th>Key Sector Impact</th><th>Nifty Move</th></tr></thead>
          <tbody>
            {hist.map(([e, p, s, n]) => (
              <tr key={e}>
                <td style={{ fontWeight: 600 }}>{e}</td>
                <td style={{ color: C.ink2, fontSize: 11 }}>{p}</td>
                <td style={{ color: C.ink2, fontSize: 11 }}>{s}</td>
                <td style={{ fontWeight: 700, color: (n as string).startsWith('-') ? C.red : C.green }}>{n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
