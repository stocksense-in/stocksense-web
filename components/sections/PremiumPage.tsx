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

export function PremiumPage({ onNav }: { onNav: (p: Page) => void }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, padding: '14px 18px', background: 'var(--gold2)', border: '1px solid var(--border-gold)', borderRadius: 10, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 20 }}>★</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.gold }}>Sovereign Intelligence · Premium Active</div>
          <div style={{ fontSize: 11, color: C.ink2, marginTop: 2 }}>Tailored to your investment profile · Geopolitics-adjusted · Updated daily</div>
        </div>
        <button className="btn-gold" onClick={() => onNav('profile')}>Edit Profile →</button>
      </div>

      <div className="g2" style={{ marginBottom: 14 }}>
        <div className="card">
          <div className="ct">Your Profile Summary</div>
          <StatRow label="Capital Range" value="₹50K – ₹2L" />
          <StatRow label="Horizon" value="1–3 Years" />
          <StatRow label="Risk Appetite" value="Moderate" />
          <StatRow label="Preferred Sectors" value="IT · Pharma · Auto" />
          <StatRow label="Geopolitics Adjusted" value="Yes ✓" valueStyle={{ color: C.green }} />
        </div>
        <div className="card card-gold">
          <div className="ct" style={{ color: C.gold }}>Tailored Matches Today</div>
          <div className="bn bn-gold" style={{ marginBottom: 6 }}>7</div>
          <div style={{ fontSize: 11, color: C.ink2, marginBottom: 10 }}>Niche picks calibrated to your risk, capital &amp; current geopolitical conditions</div>
          <div style={{ fontSize: 10, color: C.ink3 }}>3 flagged as current opportunity · 1 geo-risk warning</div>
        </div>
      </div>

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Tailored Matches · Niche Picks</div>
      <div className="g2">
        {NICHE.map(n => (
          <div key={n.name} className="niche-card">
            <div className="risk-match" style={{ background: 'rgba(0,230,118,.1)', color: C.green, border: '1px solid rgba(0,230,118,.2)' }}>{n.match}% Match</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 3, paddingRight: 80 }}>{n.name}</div>
            <div style={{ fontSize: 10, color: C.ink3, marginBottom: 8 }}>{n.sector}</div>
            <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.6, marginBottom: 10 }}>{n.why}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Pill type="g">{n.risk} Risk</Pill>
              <Pill type="gold">{n.tag}</Pill>
              <span style={{ fontSize: 10, color: C.ink3, alignSelf: 'center' }}>PE {n.pe}× · ROE {n.roe}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
