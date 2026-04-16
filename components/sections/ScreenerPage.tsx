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

export function ScreenerPage() {
  return (
    <div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="ct">Filter Universe · NSE + BSE</div>
        <div className="g3" style={{ marginBottom: 12 }}>
          {[['Sector', ['All Sectors', 'IT Services', 'Banking', 'Auto', 'FMCG', 'Pharma', 'Defence']],
            ['Market Cap', ['All', 'Large Cap (>₹20K Cr)', 'Mid Cap', 'Small Cap']],
            ['Signal Quality', ['All', 'Strong (70+)', 'Moderate (50–70)', 'Weak']]].map(([label, opts]) => (
            <div key={label as string}>
              <div className="field-label">{label}</div>
              <select className="fi">
                {(opts as string[]).map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-blue">Run Screener ↗</button>
          <button className="btn-ghost">Reset</button>
        </div>
      </div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="ct" style={{ margin: 0 }}>Results · 8 Stocks</div>
          <span className="pill pill-b">Live NSE Data</span>
        </div>
        <table className="tbl">
          <thead><tr><th>Company</th><th>Sector</th><th>Score</th><th>P/E</th><th>ROE</th><th>D/E</th><th>Signal</th></tr></thead>
          <tbody>
            {SCREENER.map(r => (
              <tr key={r.n}>
                <td style={{ fontWeight: 600 }}>{r.n}</td>
                <td style={{ color: C.ink3, fontSize: 10 }}>{r.s}</td>
                <td><Pill type={r.sig}>{r.sc}</Pill></td>
                <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{r.pe}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 11, color: r.roe >= 20 ? C.green : r.roe >= 15 ? C.ink : C.gold }}>{r.roe}%</td>
                <td style={{ fontFamily: 'monospace', fontSize: 11, color: r.de < 0.5 ? C.green : r.de < 1.5 ? C.ink : C.gold }}>{r.de}</td>
                <td><Pill type={r.sig}>{r.sig === 'g' ? 'Strong' : r.sig === 'gold' ? 'Moderate' : 'Weak'}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
