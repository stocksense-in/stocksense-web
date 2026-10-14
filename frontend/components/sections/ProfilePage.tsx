'use client';
import React, { useState } from 'react';
import { Page } from '@/lib/types';
import { C } from '@/lib/constants';
import { formatINR } from '@/lib/utils';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';

export function ProfilePage({ onNav }: { onNav: (p: Page) => void }) {
  const [capital, setCapital] = useState(100000);
  const [risk, setRisk] = useState('Moderate');
  const [sectors, setSectors] = useState(['IT', 'Pharma', 'Auto']);
  const riskDescs: Record<string, string> = {
    Conservative: 'Conservative: Protects capital first. Targets 10–14% CAGR. Suitable for 3+ year horizon with low drawdown tolerance.',
    Moderate: 'Moderate: Accepts 15–20% drawdown for 18–24% CAGR. Best for 1–3 year horizon with quality focus.',
    Aggressive: 'Aggressive: Tolerates 30%+ drawdown for 30%+ CAGR. High-conviction bets. 3+ year horizon required.',
  };

  return (
    <div className="g2">
      <div>
        <div className="profile-step">
          <div className="ps-num">1</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, fontFamily: 'var(--f-body)' }}>Investment Capital</div>
          <div className="field-label">Available capital (₹)</div>
          <input type="range" className="range-input" style={{ width: '100%', margin: '10px 0 4px' }}
            min={10000} max={1000000} step={5000} value={capital} onChange={e => setCapital(Number(e.target.value))} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--cream-mute)', marginBottom: 6 }}>
            <span>₹10K</span>
            <span style={{ color: 'var(--gold)', fontWeight: 500, fontFamily: 'var(--f-mono)' }}>{formatINR(capital)}</span>
            <span>₹10L+</span>
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">2</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Investment Horizon</div>
          <div className="seg-row">
            {['3 Months', '1 Year', '3 Years', '5+ Years'].map(h => (
              <button key={h} className={`seg-btn${h === '1 Year' ? ' active' : ''}`}>{h}</button>
            ))}
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">3</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Risk Appetite</div>
          <div className="seg-row">
            {['Conservative', 'Moderate', 'Aggressive'].map(r => (
              <button key={r} className={`seg-btn${r === risk ? ' active' : ''}`} onClick={() => setRisk(r)}>{r}</button>
            ))}
          </div>
          <div style={{ marginTop: 10, padding: '9px 12px', background: 'var(--s2)', borderRadius: 5, fontSize: 10, color: 'var(--cream-dim)', lineHeight: 1.6 }}>
            {riskDescs[risk]}
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">4</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Sector Preferences</div>
          <div className="seg-row" style={{ flexWrap: 'wrap' }}>
            {['IT', 'Banking', 'Pharma', 'FMCG', 'Auto', 'Defence', 'Real Estate'].map(s => (
              <button key={s} className={`seg-btn${sectors.includes(s) ? ' active' : ''}`}
                onClick={() => setSectors(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])}>{s}</button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="card card-gold" style={{ marginBottom: 10 }}>
          <div className="ct" style={{ color: 'var(--gold)' }}>Your Investment DNA</div>
          <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 5, fontFamily: 'var(--f-display)' }}>Balanced Growth</div>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.7, marginBottom: 14 }}>Seeks steady compounding with managed downside. Focus on quality mid-caps with strong ROE and low debt. Suitable for 1–3 year horizon.</div>
          <StatRow label="Suggested allocation" value="60% Equity · 40% Hybrid" valueStyle={{ color: 'var(--gold)' }} />
          <StatRow label="Expected CAGR (3yr)" value="18–24%" valueStyle={{ color: C.green }} />
          <StatRow label="Niche matches" value="7 stocks today" valueStyle={{ color: C.gold }} />
        </div>
        <div className="card" style={{ marginBottom: 10 }}>
          <div className="ct">Geopolitical Risk Overlay</div>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.7, marginBottom: 10 }}>Current Middle East tensions have <strong style={{ color: 'var(--gold)' }}>moderate impact</strong> on your sector preferences.</div>
          <StatRow label="Oil sensitivity" value={<Pill type="g">Low</Pill>} />
          <StatRow label="USD revenue exposure" value={<Pill type="g">High (IT)</Pill>} />
          <StatRow label="Defence opportunity" value={<Pill type="g">Yes ↑</Pill>} />
          <StatRow label="Gold safe-haven relevance" value={<Pill type="gold">Moderate</Pill>} />
        </div>
        <button className="btn-gold-main" style={{ width: '100%' }} onClick={() => onNav('premium')}><span>Get My Niche Matches ↗</span></button>
      </div>
    </div>
  );
}
