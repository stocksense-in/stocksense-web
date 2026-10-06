'use client';
import React from 'react';
import { GEO_SECTORS, GEO_EVENTS } from '@/lib/constants';
import { Pill } from '@/components/ui/Pill';

export function GeoPage() {
  const hist = [
    { e: 'Iran–Israel Apr 2024', p: '2 weeks', s: 'Oil +8%  ·  Gold +6%  ·  Aviation −4%', n: '−1.2%', neg: true },
    { e: 'Russia–Ukraine Feb 2022', p: '3 months', s: 'Defence +22%  ·  Oil +32%  ·  Metals +14%', n: '−8.4%', neg: true },
    { e: 'COVID Mar 2020', p: '6 months', s: 'Pharma +18%  ·  Aviation −45%  ·  IT −12%', n: '−38%', neg: true },
    { e: 'India–China Galwan 2020', p: '1 month', s: 'Defence +15%  ·  China-exposed −8%', n: '−3.6%', neg: true },
  ];

  return (
    <div>
      {/* Alert banner */}
      <div className="geo-alert" style={{ marginBottom: 20 }}>
        <div className="geo-alert-icon">⚠</div>
        <div style={{ flex: 1 }}>
          <div className="geo-alert-top">
            <div className="pulse-dot" />
            <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '1.8px', textTransform: 'uppercase', color: 'var(--red)' }}>Active High Risk Alert</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--cream)', marginBottom: 5, letterSpacing: '-0.3px', fontFamily: 'var(--f-display)' }}>
            Middle East tensions elevated — Strait of Hormuz disruption risk
          </div>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.65 }}>
            Affects: <strong style={{ color: 'var(--red)' }}>Oil &amp; Gas</strong> · <strong style={{ color: 'var(--red)' }}>Aviation</strong> · <span style={{ color: 'var(--gold)' }}>Gold/Silver safe-haven</span> · <span style={{ color: 'var(--green)' }}>Defence opportunity</span>
            &nbsp;·&nbsp; Updated 2 hours ago · 14 sources
          </div>
        </div>
      </div>

      {/* Main 2-col */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 12, marginBottom: 14 }}>

        {/* Global Pulse Feed */}
        <div className="card">
          <div className="ct">Global Pulse Feed</div>
          {GEO_EVENTS.map((e, i) => {
            const tagColor = e.tag === 'CONFLICT' || e.tag === 'OIL' ? 'r' : e.tag === 'COMMODITY' || e.tag === 'AGRI' ? 'gold' : e.tag === 'DEFENCE' ? 'g' : 'gold';
            return (
              <div key={i} className={`event-card ${e.cls}`} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Pill type={tagColor as 'r' | 'g' | 'gold'}>{e.tag}</Pill>
                  {e.cls === 'ev-gold' && (
                    <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--gold)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ display: 'inline-block', width: 5, height: 5, borderRadius: '50%', background: 'var(--gold)', boxShadow: '0 0 6px rgba(201,168,76,0.5)' }} />
                      GOLD SAFE HAVEN
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--cream)', lineHeight: 1.55 }}>{e.title}</div>
              </div>
            );
          })}
        </div>

        {/* Sector Risk Matrix */}
        <div className="card">
          <div className="ct">Sector Risk Matrix · Live</div>
          {GEO_SECTORS.map(g => (
            <div key={g.s} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--cream)' }}>{g.s}</span>
                <span className={`pill pill-${g.c}`} style={{ fontSize: 8, minWidth: 72, justifyContent: 'center' }}>{g.impact}</span>
              </div>
              <div style={{ height: 4, background: 'rgba(201,168,76,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${g.risk}%`,
                    height: '100%',
                    borderRadius: 2,
                    background: g.c === 'r' ? 'var(--red)' : g.c === 'g' ? 'var(--green)' : 'var(--gold)',
                    opacity: 0.8,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Historical Precedents */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div className="ct" style={{ marginBottom: 0 }}>Historical Precedents — How Markets Reacted</div>
          <span className="pill pill-gold">Past Performance</span>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Event</th>
              <th>Duration</th>
              <th>Key Sector Impact</th>
              <th style={{ textAlign: 'right' }}>Nifty Move</th>
            </tr>
          </thead>
          <tbody>
            {hist.map(row => (
              <tr key={row.e}>
                <td style={{ fontWeight: 700, fontSize: 12, letterSpacing: '-0.2px' }}>{row.e}</td>
                <td style={{ color: 'var(--cream-mute)', fontSize: 10, fontFamily: 'var(--f-mono)' }}>{row.p}</td>
                <td style={{ color: 'var(--cream-dim)', fontSize: 10.5, lineHeight: 1.5 }}>{row.s}</td>
                <td style={{ textAlign: 'right', fontWeight: 500, fontFamily: 'var(--f-mono)', fontSize: 13, color: row.neg ? 'var(--red)' : 'var(--green)' }}>{row.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
