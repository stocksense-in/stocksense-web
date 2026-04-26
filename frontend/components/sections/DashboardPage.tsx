'use client';
import React, { useState, useEffect } from 'react';
import { Page } from '@/lib/types';
import { C, GEO_SECTORS } from '@/lib/constants';
import { supabase } from '@/lib/supabase';
import { Pill } from '@/components/ui/Pill';

export function DashboardPage({ onNav }: { onNav: (p: Page) => void }) {
  const [prices, setPrices] = useState<{ NIFTY50: number|null; SENSEX: number|null; BANKNIFTY: number|null }>({
    NIFTY50: null, SENSEX: null, BANKNIFTY: null,
  });

  useEffect(() => {
    const fetchPrices = async () => {
      const { data, error } = await supabase.from('live_prices').select('symbol, price').in('symbol', ['NIFTY50', 'SENSEX', 'BANKNIFTY']);
      if (!error && data) {
        const u: any = { NIFTY50: null, SENSEX: null, BANKNIFTY: null };
        data.forEach((r: any) => { if (r.symbol in u) u[r.symbol] = r.price; });
        setPrices(u);
      }
    };
    fetchPrices();
    const iv = setInterval(fetchPrices, 3000);
    return () => clearInterval(iv);
  }, []);

  const sectors = [
    ['Defence & Aerospace', '+3.8', 'green', 95],
    ['IT Services', '+2.1', 'green', 52],
    ['Auto', '+1.4', 'green', 35],
    ['FMCG', '+0.8', 'green', 20],
    ['Banking', '-0.6', 'red', 15],
    ['Pharma', '-0.3', 'red', 8],
  ];

  const movers = [
    ['RELIANCE', '₹2,934', '+3.2%', 'g', '52W High'],
    ['MTAR TECH', '₹2,180', '+4.1%', 'g', '↑ Strong Vol'],
    ['HAL', '₹4,620', '+2.8%', 'g', 'Defence Play'],
    ['INDIGO', '₹3,240', '-2.6%', 'r', 'Fuel Pressure'],
    ['NTPC', '₹364', '-1.4%', 'r', '↓ Overbought'],
  ];

  const news = [
    { t: 'RBI holds repo rate at 6.5% — neutral stance maintained Q2 FY26', tag: 'MACRO', c: 'gold', time: '2h ago' },
    { t: 'Crude breaches $96 on Hormuz escalation — OMCs under pressure', tag: 'RISK', c: 'r', time: '3h ago' },
    { t: 'TCS Q4 PAT +8.2% YoY — double-digit FY26 guidance confirmed', tag: 'RESULT', c: 'g', time: '5h ago' },
    { t: 'Ather Energy IPO opens Apr 28 — GMP at +₹38 over issue price', tag: 'IPO', c: 'b', time: '6h ago' },
  ];

  const pf = (v: number|null, sym: string) => v !== null ? `${sym}${v.toLocaleString('en-IN')}` : '—';

  return (
    <div>
      {/* Index Strip */}
      <div className="idx-strip" style={{ marginBottom: 20 }}>
        {[
          ['NIFTY 50', pf(prices.NIFTY50, ''), '+0.82%', 'green', 'bull', '24,762'],
          ['SENSEX', pf(prices.SENSEX, ''), '+0.76%', 'green', 'bull', '81,430'],
          ['BANK NIFTY', pf(prices.BANKNIFTY, ''), '−0.41%', 'red', 'bear', '52,114'],
          ['INDIA VIX', '13.42', '−4.2%', 'green', 'bull', '—'],
        ].map(([name, val, chg, c, cls, base]) => (
          <div key={name} className={`idx-card ${cls}`}>
            <div className="idx-name">{name}</div>
            <div className="idx-val" style={{ fontSize: 22 }}>{val !== '—' ? val : base}</div>
            <div className="idx-chg" style={{ color: `var(--${c})` }}>{chg}</div>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 14, marginBottom: 14 }}>

        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Sector heatmap */}
          <div className="card" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)' }}>Sector Performance · Today</div>
              <span className="pill pill-g">Market Open</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {sectors.map(([n, v, c, w]) => (
                <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 130, fontSize: 11, color: 'var(--ink)', fontWeight: 500, flexShrink: 0 }}>{n}</div>
                  <div style={{ flex: 1, height: 6, background: 'var(--ink4)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${w}%`, height: '100%', background: `var(--${c})`, borderRadius: 4, opacity: 0.8 }} />
                  </div>
                  <div style={{ width: 52, textAlign: 'right', fontSize: 11, fontWeight: 700, fontFamily: 'var(--mono)', color: `var(--${c})` }}>{String(v)}%</div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Movers */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)' }}>Top Movers · NSE</div>
              <span className="pill pill-b">Live Data</span>
            </div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Stock</th>
                  <th style={{ textAlign: 'right' }}>LTP</th>
                  <th style={{ textAlign: 'right' }}>Change</th>
                  <th>Note</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {movers.map(([n, p, c, s, note]) => (
                  <tr key={n}>
                    <td><span style={{ fontWeight: 700, fontFamily: 'var(--mono)', fontSize: 11.5, letterSpacing: '-0.2px' }}>{n}</span></td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontWeight: 600, fontSize: 11.5 }}>{p}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontWeight: 700, color: `var(--${s === 'g' ? 'green' : 'red'})` }}>{c}</td>
                    <td style={{ fontSize: 10, color: 'var(--ink3)', fontStyle: 'italic' }}>{note}</td>
                    <td><Pill type={s}>{s === 'g' ? 'BUY' : 'WATCH'}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* FII/DII donut */}
          <div className="card">
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 14 }}>Market Breadth · FII / DII</div>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <svg width="72" height="72" viewBox="0 0 72 72" style={{ flexShrink: 0 }}>
                <circle cx="36" cy="36" r="28" fill="none" stroke="var(--ink4)" strokeWidth="6" />
                <circle cx="36" cy="36" r="28" fill="none" stroke="var(--green)" strokeWidth="6"
                  strokeDasharray="175.9" strokeDashoffset="49.3" strokeLinecap="round" transform="rotate(-90 36 36)"
                  style={{ filter: 'drop-shadow(0 0 6px rgba(0,217,126,.4))' }} />
                <text x="36" y="32" textAnchor="middle" fontSize="13" fontWeight="800" fill="#DCE5F8" fontFamily="Inter,sans-serif">72%</text>
                <text x="36" y="44" textAnchor="middle" fontSize="7" fill="#60789E" fontFamily="Inter,sans-serif" letterSpacing="1">BULL</text>
              </svg>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                  <span style={{ fontSize: 10, color: 'var(--ink2)' }}>FII Net</span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--green)' }}>+₹2,840 Cr</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                  <span style={{ fontSize: 10, color: 'var(--ink2)' }}>DII Net</span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--red)' }}>−₹1,120 Cr</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                  <span style={{ fontSize: 10, color: 'var(--ink2)' }}>Advances</span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 600 }}>1,847</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                  <span style={{ fontSize: 10, color: 'var(--ink2)' }}>Declines</span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 600 }}>892</span>
                </div>
              </div>
            </div>
          </div>

          {/* News feed */}
          <div className="card" style={{ flex: 1 }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 12 }}>Intelligence Feed</div>
            {news.map((item, i) => (
              <div key={i} style={{ padding: '10px 0', borderBottom: i < news.length - 1 ? '1px solid rgba(255,255,255,.05)' : 'none' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <span className={`pill pill-${item.c}`} style={{ flexShrink: 0, marginTop: 1 }}>{item.tag}</span>
                  <span style={{ fontSize: 11, color: 'var(--ink)', lineHeight: 1.55, flex: 1 }}>{item.t}</span>
                </div>
                <div style={{ fontSize: 9, color: 'var(--ink3)', marginTop: 5, marginLeft: 0 }}>{item.time}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Geo Alert Banner */}
      <div style={{ position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '18px 22px', background: 'linear-gradient(135deg,rgba(201,153,30,.1),rgba(201,153,30,.04))', border: '1px solid rgba(201,153,30,.2)', borderRadius: 'var(--r3)', flexWrap: 'wrap' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: 'linear-gradient(90deg,transparent,rgba(201,153,30,.4),transparent)' }} />
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <div style={{ width: 42, height: 42, borderRadius: 12, background: 'rgba(201,153,30,.14)', border: '1px solid rgba(201,153,30,.24)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0 }}>⚠</div>
          <div>
            <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 4 }}>Active Geopolitical Risk Alert</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 3, letterSpacing: '-0.2px' }}>Middle East escalation — Oil, Gold, Defence sectors flagged</div>
            <div style={{ fontSize: 11, color: 'var(--ink2)' }}>Updated 2hr ago · Gold/Silver showing safe-haven demand surge</div>
          </div>
        </div>
        <button className="btn-gold" onClick={() => onNav('geo')} style={{ flexShrink: 0 }}>View Full Analysis →</button>
      </div>
    </div>
  );
}
