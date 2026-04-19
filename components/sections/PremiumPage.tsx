'use client';
import React from 'react';
import { Page } from '@/lib/types';
import { NICHE, C } from '@/lib/constants';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';

export function PremiumPage({ onNav }: { onNav: (p: Page) => void }) {
  const profile = [
    ['Capital Range', '₹50K – ₹2L', 'ink'],
    ['Time Horizon', '1–3 Years', 'ink'],
    ['Risk Appetite', 'Moderate', 'gold'],
    ['Preferred Sectors', 'IT · Pharma · Auto', 'ink'],
    ['Geo-Adjusted', 'Active ✓', 'green'],
  ];

  return (
    <div>
      {/* Premium header */}
      <div style={{ position: 'relative', overflow: 'hidden', marginBottom: 20, padding: '22px 24px', background: 'linear-gradient(135deg,rgba(201,153,30,.13),rgba(201,153,30,.04))', border: '1px solid rgba(201,153,30,.24)', borderRadius: 'var(--r3)' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg,transparent 0%,rgba(201,153,30,.8) 40%,rgba(255,220,100,.9) 50%,rgba(201,153,30,.8) 60%,transparent 100%)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg,rgba(201,153,30,.25),rgba(201,153,30,.08))', border: '1px solid rgba(201,153,30,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0 }}>★</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 5 }}>Sovereign Intelligence · Premium Active</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-0.4px', marginBottom: 3 }}>Tailored to your investment profile</div>
            <div style={{ fontSize: 11, color: 'var(--ink2)' }}>Geopolitics-adjusted · Updated daily · <strong style={{ color: 'var(--gold)' }}>7 active opportunities</strong></div>
          </div>
          <button className="btn-gold" onClick={() => onNav('profile')} style={{ flexShrink: 0 }}>Edit Profile →</button>
        </div>
      </div>

      {/* Profile + Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 20 }}>
        {/* Profile card */}
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 14 }}>Your Investment Profile</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' }}>
            {profile.map(([label, val, c]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
                <span style={{ fontSize: 11, color: 'var(--ink2)' }}>{label}</span>
                <span style={{ fontSize: 11, fontWeight: 600, color: `var(--${c})` }}>{val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Matches today */}
        <div className="card card-gold" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 8 }}>Matches Today</div>
          <div style={{ fontSize: 52, fontWeight: 800, color: 'var(--gold)', fontFamily: 'var(--mono)', letterSpacing: '-2px', lineHeight: 1 }}>7</div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--ink2)', lineHeight: 1.6, marginBottom: 6 }}>Niche picks calibrated to your risk, capital &amp; geopolitical conditions</div>
            <div style={{ fontSize: 10, color: 'var(--ink3)' }}>3 flagged as opportunity · 1 geo-risk warning</div>
          </div>
        </div>
      </div>

      {/* Section heading */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
        <div style={{ width: 3, height: 16, background: 'var(--gold)', borderRadius: 2 }} />
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink2)' }}>Tailored Matches · Niche Picks</span>
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        <span className="pill pill-gold">{NICHE.length} picks</span>
      </div>

      {/* Niche grid */}
      <div className="g2">
        {NICHE.map(n => (
          <div key={n.name} className="niche-card">
            <div className="risk-match" style={{ background: 'rgba(0,217,126,.1)', color: 'var(--green)', border: '1px solid rgba(0,217,126,.2)' }}>{n.match}% Match</div>
            <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 6 }}>{n.sector}</div>
            <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 8, paddingRight: 80, letterSpacing: '-0.4px', color: 'var(--ink)', lineHeight: 1.3 }}>{n.name}</div>
            <div style={{ fontSize: 11, color: 'var(--ink2)', lineHeight: 1.7, marginBottom: 14 }}>{n.why}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', paddingTop: 12, borderTop: '1px solid rgba(255,255,255,.05)' }}>
              <Pill type="g">{n.risk} Risk</Pill>
              <Pill type="gold">{n.tag}</Pill>
              <span style={{ fontSize: 10, color: 'var(--ink3)', marginLeft: 'auto', fontFamily: 'var(--mono)', fontWeight: 600 }}>
                PE {n.pe}× · ROE {n.roe}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
