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
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Investment Capital</div>
          <div className="field-label">Available capital (₹)</div>
          <input type="range" className="range-input" style={{ width: '100%', margin: '10px 0 4px' }}
            min={10000} max={1000000} step={5000} value={capital} onChange={e => setCapital(Number(e.target.value))} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: C.ink3, marginBottom: 6 }}>
            <span>₹10K</span>
            <span style={{ color: C.blue, fontWeight: 700 }}>{formatINR(capital)}</span>
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
          <div style={{ marginTop: 10, padding: '9px 12px', background: 'var(--s2)', borderRadius: 7, fontSize: 10, color: C.ink2, lineHeight: 1.6 }}>
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
          <div className="ct" style={{ color: C.gold }}>Your Investment DNA</div>
          <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 5 }}>Balanced Growth</div>
          <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.7, marginBottom: 14 }}>Seeks steady compounding with managed downside. Focus on quality mid-caps with strong ROE and low debt. Suitable for 1–3 year horizon.</div>
          <StatRow label="Suggested allocation" value="60% Equity · 40% Hybrid" valueStyle={{ color: C.blue }} />
          <StatRow label="Expected CAGR (3yr)" value="18–24%" valueStyle={{ color: C.green }} />
          <StatRow label="Niche matches" value="7 stocks today" valueStyle={{ color: C.gold }} />
        </div>
        <div className="card" style={{ marginBottom: 10 }}>
          <div className="ct">Geopolitical Risk Overlay</div>
          <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.7, marginBottom: 10 }}>Current Middle East tensions have <strong style={{ color: C.gold }}>moderate impact</strong> on your sector preferences.</div>
          <StatRow label="Oil sensitivity" value={<Pill type="g">Low</Pill>} />
          <StatRow label="USD revenue exposure" value={<Pill type="g">High (IT)</Pill>} />
          <StatRow label="Defence opportunity" value={<Pill type="g">Yes ↑</Pill>} />
          <StatRow label="Gold safe-haven relevance" value={<Pill type="gold">Moderate</Pill>} />
        </div>
        <button className="btn-blue" style={{ width: '100%' }} onClick={() => onNav('premium')}>Get My Niche Matches ↗</button>
      </div>
    </div>
  );
}
