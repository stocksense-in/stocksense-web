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

export function IPOPage() {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div>
      <div className="g2" style={{ marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Active IPOs · Tap to Analyse</div>
          {IPOS.map((ipo, i) => (
            <div key={i} className={`ipo-card${selected === i ? ' sel' : ''}`} onClick={() => setSelected(i)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{ipo.name}</div>
                  <div style={{ fontSize: 10, color: C.ink3, marginTop: 2 }}>{ipo.sector} · Opens {ipo.open} · {ipo.size}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(ipo.score) }}>{ipo.score}</div>
                  <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: 1, color: C.ink3 }}>SCORE</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Pill type={ipo.verdict === 'Subscribe' ? 'g' : ipo.verdict === 'Risky' ? 'gold' : 'r'}>{ipo.verdict}</Pill>
                <span style={{ fontSize: 10, color: C.ink3 }}>{ipo.band}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          {selected === null ? (
            <div style={{ fontSize: 11, color: C.ink3, padding: '20px 0', textAlign: 'center' }}>← Select an IPO to view full scoring</div>
          ) : (() => {
            const ipo = IPOS[selected];
            const sc = scoreColor(ipo.score);
            const sigs: [string, string, number][] = [['GMP Signal', '20%', ipo.gmp], ['QIB Subscription', '25%', ipo.qib], ['Retail Interest', '10%', ipo.retail], ['Fundamentals', '30%', ipo.fund], ['Geo Risk Score', '15%', ipo.geo]];
            return (
              <div>
                <div className="ct">IPO Analysis · {ipo.name}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 800 }}>{ipo.name}</div>
                    <div style={{ fontSize: 10, color: C.ink3, marginTop: 3 }}>{ipo.sector} · {ipo.band} · {ipo.size} · Opens {ipo.open}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 32, fontWeight: 800, color: sc }}>{ipo.score}</div>
                    <Pill type={ipo.verdict === 'Subscribe' ? 'g' : ipo.verdict === 'Risky' ? 'gold' : 'r'}>{ipo.verdict}</Pill>
                  </div>
                </div>
                {sigs.map(([lbl, w, v]) => (
                  <div key={lbl} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 10, color: C.ink2 }}>{lbl} <span style={{ color: C.ink3 }}>({w})</span></span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: v >= 65 ? C.green : v >= 45 ? C.gold : C.red }}>{v}/100</span>
                    </div>
                    <div className="bar-track" style={{ height: 5 }}>
                      <div className="bar-fill" style={{ width: `${v}%`, background: v >= 65 ? C.green : v >= 45 ? C.gold : C.red }} />
                    </div>
                  </div>
                ))}
                <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--gold2)', borderLeft: `2px solid ${C.gold}`, fontSize: 10, color: C.ink2, lineHeight: 1.7 }}>
                  <strong style={{ color: C.gold }}>Analyst note —</strong>{' '}
                  {ipo.verdict === 'Subscribe' ? 'Strong institutional interest and fair valuation. GMP positive. Suitable for listing gain + short-term hold.' : ipo.verdict === 'Risky' ? 'Mixed signals — QIB interest moderate. Suitable only for high risk tolerance.' : 'Poor QIB interest and weak fundamentals. Listing losses likely. Avoid.'}
                </div>
              </div>
            );
          })()}
        </div>
      </div>

      <div className="card">
        <div className="ct">Scoring Methodology</div>
        <div className="g4" style={{ textAlign: 'center' }}>
          {[['30%', 'FUNDAMENTALS', C.blue], ['25%', 'QIB SUBSCRIPTION', C.green], ['20%', 'GMP SIGNAL', C.gold], ['15%', 'GEO RISK', C.red]].map(([pct, label, color], i, arr) => (
            <div key={label} style={{ padding: 10, borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color }}>{pct}</div>
              <div style={{ fontSize: 9, fontWeight: 700, color: C.ink3, marginTop: 3, letterSpacing: 1 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
