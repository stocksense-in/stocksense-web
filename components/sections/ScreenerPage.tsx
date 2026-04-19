'use client';
import React, { useState } from 'react';
import { SCREENER } from '@/lib/constants';
import { Pill } from '@/components/ui/Pill';

export function ScreenerPage() {
  const [activeFilters, setActiveFilters] = useState({ sector: 'All Sectors', cap: 'All', signal: 'All' });

  const filters = [
    { key: 'sector', label: 'Sector', opts: ['All Sectors', 'IT Services', 'Banking', 'Auto', 'FMCG', 'Pharma', 'Defence'] },
    { key: 'cap', label: 'Market Cap', opts: ['All', 'Large Cap (>₹20K Cr)', 'Mid Cap', 'Small Cap'] },
    { key: 'signal', label: 'Signal Quality', opts: ['All', 'Strong (70+)', 'Moderate (50–70)', 'Weak (<50)'] },
  ];

  return (
    <div>
      {/* Filter card */}
      <div className="card" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <div style={{ width: 3, height: 16, background: 'var(--blue)', borderRadius: 2 }} />
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink2)' }}>Filter Universe · NSE + BSE</span>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          <span className="pill pill-b">2,847 Stocks</span>
        </div>

        <div className="g3" style={{ marginBottom: 16 }}>
          {filters.map(f => (
            <div key={f.key}>
              <div className="field-label">{f.label}</div>
              <select
                className="fi"
                value={(activeFilters as any)[f.key]}
                onChange={e => setActiveFilters(prev => ({ ...prev, [f.key]: e.target.value }))}
              >
                {f.opts.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button className="btn-blue">Run Screener ↗</button>
          <button className="btn-ghost" onClick={() => setActiveFilters({ sector: 'All Sectors', cap: 'All', signal: 'All' })}>Reset</button>
          <span style={{ fontSize: 10, color: 'var(--ink3)', marginLeft: 4 }}>Showing top 8 by StockSense score</span>
        </div>
      </div>

      {/* Results table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 3, height: 16, background: 'var(--blue)', borderRadius: 2 }} />
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink2)' }}>Results · {SCREENER.length} Stocks</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="pill pill-b">Live NSE Data</span>
            <span className="pill pill-g">Market Open</span>
          </div>
        </div>

        <table className="tbl">
          <thead>
            <tr>
              <th>#</th>
              <th>Company</th>
              <th>Sector</th>
              <th style={{ textAlign: 'center' }}>Score</th>
              <th style={{ textAlign: 'right' }}>P/E</th>
              <th style={{ textAlign: 'right' }}>ROE</th>
              <th style={{ textAlign: 'right' }}>D/E</th>
              <th style={{ textAlign: 'center' }}>Signal</th>
            </tr>
          </thead>
          <tbody>
            {SCREENER.map((r, i) => (
              <tr key={r.n}>
                <td style={{ color: 'var(--ink3)', fontFamily: 'var(--mono)', fontSize: 10, width: 28 }}>{String(i + 1).padStart(2, '0')}</td>
                <td>
                  <span style={{ fontWeight: 800, fontSize: 12, letterSpacing: '-0.3px', color: 'var(--ink)' }}>{r.n}</span>
                </td>
                <td>
                  <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--ink3)' }}>{r.s}</span>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <Pill type={r.sig}>{r.sc}</Pill>
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11.5, fontWeight: 600 }}>{r.pe}</td>
                <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11.5, fontWeight: 700, color: r.roe >= 20 ? 'var(--green)' : r.roe >= 15 ? 'var(--ink)' : 'var(--gold)' }}>{r.roe}%</td>
                <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11.5, fontWeight: 700, color: r.de < 0.5 ? 'var(--green)' : r.de < 1.5 ? 'var(--ink)' : 'var(--gold)' }}>{r.de}</td>
                <td style={{ textAlign: 'center' }}>
                  <Pill type={r.sig}>{r.sig === 'g' ? 'Strong' : r.sig === 'gold' ? 'Moderate' : 'Weak'}</Pill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
