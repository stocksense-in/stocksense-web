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

export function DashboardPage({ onNav }: { onNav: (p: Page) => void }) {
  const [prices, setPrices] = useState({
  NIFTY50: null,
  SENSEX: null,
  BANKNIFTY: null,
})
  useEffect(() => {
  const fetchPrices = async () => {
    const { data, error } = await supabase
      .from("live_prices")
      .select("symbol, price")
      .in("symbol", ["NIFTY50", "SENSEX", "BANKNIFTY"])

    if (!error && data) {
      const updated = {
        NIFTY50: null,
        SENSEX: null,
        BANKNIFTY: null,
      }

      data.forEach((row) => {
        if (row.symbol === "NIFTY50") updated.NIFTY50 = row.price
        if (row.symbol === "SENSEX") updated.SENSEX = row.price
        if (row.symbol === "BANKNIFTY") updated.BANKNIFTY = row.price
      })

      setPrices(updated)
    }
  }

  fetchPrices()

  const interval = setInterval(fetchPrices, 2000)

  return () => clearInterval(interval)
}, [])
  const sectors = [['IT', '+2.1%', 'green'], ['FMCG', '+0.8%', 'green'], ['Auto', '+1.4%', 'green'], ['Pharma', '-0.3%', 'red'], ['Banking', '-0.6%', 'red'], ['Defence', '+3.8%', 'green']];
  const movers = [['RELIANCE', '₹2,934', '+3.2%', 'g'], ['MTAR TECH', '₹2,180', '+4.1%', 'g'], ['HAL', '₹4,620', '+2.8%', 'g'], ['INDIGO', '₹3,240', '-2.6%', 'r'], ['NTPC', '₹364', '-1.4%', 'r']];
  const news = [
    { t: 'RBI holds repo rate at 6.5% — neutral stance Q2', tag: 'MACRO', c: 'gold' },
    { t: 'Crude breaches $96 on Hormuz escalation — OMCs under pressure', tag: 'RISK', c: 'r' },
    { t: 'TCS Q4 PAT +8.2% YoY — double-digit FY26 guidance confirmed', tag: 'RESULT', c: 'g' },
    { t: 'Ather Energy IPO opens Apr 28 — GMP at +₹38 over issue price', tag: 'IPO', c: 'b' },
  ];

  return (
    <div>
      <div className="idx-strip">
  {[
  [
    'Nifty 50',
    prices.NIFTY50 !== null
      ? `₹${prices.NIFTY50}`
      : 'Loading...',
    'LIVE',
    'green'
  ],
  [
    'Sensex',
    prices.SENSEX !== null
      ? `₹${prices.SENSEX}`
      : 'Loading...',
    'LIVE',
    'green'
  ],
  [
    'Bank Nifty',
    prices.BANKNIFTY !== null
      ? `₹${prices.BANKNIFTY}`
      : 'Loading...',
    'LIVE',
    'red'
  ],
  ['India VIX', '13.42', 'Moderate', 'ink2']
].map(([name, val, chg, c]) => (
    <div key={name} className="idx-card">
      <div className="idx-name">{name}</div>
      <div className="idx-val">{val}</div>
      <div className="idx-chg" style={{ color: `var(--${c})` }}>
        {chg}
      </div>
    </div>
  ))}
</div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Market Pulse · FII / DII</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
            <svg width="80" height="80" viewBox="0 0 80 80" style={{ flexShrink: 0 }}>
              <circle cx="40" cy="40" r="30" fill="none" stroke="var(--ink4)" strokeWidth="7" />
              <circle cx="40" cy="40" r="30" fill="none" stroke="var(--green)" strokeWidth="7"
                strokeDasharray="188.5" strokeDashoffset="53" strokeLinecap="round" transform="rotate(-90 40 40)"
                style={{ filter: 'drop-shadow(0 0 7px rgba(0,230,118,.4))' }} />
              <text x="40" y="37" textAnchor="middle" fontSize="15" fontWeight="800" fill="#EEF2FF" fontFamily="Inter,sans-serif">72%</text>
              <text x="40" y="51" textAnchor="middle" fontSize="8" fill="#8B9EC0" fontFamily="Inter,sans-serif">BULLISH</text>
            </svg>
            <div style={{ flex: 1 }}>
              <StatRow label="FII Net" value="+₹2,840 Cr" valueStyle={{ color: C.green }} />
              <StatRow label="DII Net" value="-₹1,120 Cr" valueStyle={{ color: C.red }} />
              <StatRow label="Advances" value="1,847" />
              <StatRow label="Declines" value="892" />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="ct">Sector Performance · Today</div>
          {sectors.map(([n, v, c]) => (
            <div key={n} className="stat-r">
              <span className="sl">{n}</span>
              <div style={{ flex: 1, margin: '0 10px' }}>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.abs(parseFloat(v)) / 4 * 100}%`, background: `var(--${c})` }} />
                </div>
              </div>
              <span className="sv" style={{ color: `var(--${c})` }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Top Movers</div>
          <table className="tbl">
            <thead><tr><th>Stock</th><th>Price</th><th>Change</th><th>Signal</th></tr></thead>
            <tbody>
              {movers.map(([n, p, c, s]) => (
                <tr key={n}>
                  <td style={{ fontWeight: 600 }}>{n}</td>
                  <td style={{ fontFamily: 'monospace' }}>{p}</td>
                  <td style={{ color: `var(--${s === 'g' ? 'green' : 'red'})`, fontWeight: 600 }}>{c}</td>
                  <td><Pill type={s}>{s === 'g' ? 'Buy' : 'Watch'}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="ct">Market Intelligence Feed</div>
          {news.map((item, i) => (
            <div key={i} className="stat-r" style={{ alignItems: 'flex-start', padding: '8px 0' }}>
              <span className={`pill pill-${item.c}`} style={{ flexShrink: 0, marginTop: 1 }}>{item.tag}</span>
              <span style={{ fontSize: 11, color: C.ink, marginLeft: 10, lineHeight: 1.5 }}>{item.t}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card card-gold" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div className="ct" style={{ color: C.gold }}>Active Geopolitical Risk Alert</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.ink, marginBottom: 4 }}>Middle East escalation — Oil, Gold, Defence sectors flagged</div>
          <div style={{ fontSize: 11, color: C.ink2 }}>Updated 2hr ago · Gold/Silver showing safe-haven demand surge</div>
        </div>
        <button className="btn-gold" onClick={() => onNav('geo')}>View Full Analysis →</button>
      </div>
      <p style={{fontSize:'10px', color:'#3D5070', marginTop:'20px'}}>
  StockSense v0.1 · Day 1 · Branch: frontend_kartikey
</p>
    </div>
  );
}
