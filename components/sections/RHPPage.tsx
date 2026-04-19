'use client';
import React, { useState } from 'react';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';

export function RHPPage() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<null | 'done'>(null);

  const rhpDemo = () => {
    setScanning(true);
    setTimeout(() => { setScanning(false); setResults('done'); }, 1400);
  };

  const risks = [
    { level: 'HIGH', c: 'r', title: 'Concentrated Revenue Risk', body: 'Top 3 customers account for 68% of total revenue — significant client concentration risk.' },
    { level: 'HIGH', c: 'r', title: 'Promoter Litigation Pending', body: '2 civil suits pending against promoter group for ₹42 Cr. Material if adverse judgment.' },
    { level: 'MED', c: 'gold', title: 'Use of Proceeds — Partial Clarity', body: '₹420 Cr for "general corporate purposes" lacks specific deployment plan in DRHP.' },
    { level: 'LOW', c: 'g', title: 'Peer Comparison Fair', body: 'Comparable company selection methodology is appropriate and disclosed transparently.' },
    { level: 'MED', c: 'gold', title: 'EV Market Dependency', body: '100% revenue from EV segment — highly sensitive to EV adoption rate changes and subsidy policy.' },
  ];

  const scanChecks = [
    ['Related party transactions', 'r', 'High Risk'],
    ['Promoter litigation', 'r', 'High Risk'],
    ['Revenue concentration', 'gold', 'Medium'],
    ['DRHP vs actual financials', 'r', 'High Risk'],
    ['Use of proceeds clarity', 'g', 'Low Risk'],
    ['Peer comparison fairness', 'gold', 'Medium'],
  ];

  const borderColor = { r: 'var(--red)', gold: 'var(--gold)', g: 'var(--green)' } as any;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 14 }}>

      {/* Left: Upload + scan checklist */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div
          className="rhp-upload"
          onClick={rhpDemo}
          style={{ opacity: scanning ? 0.5 : 1, cursor: scanning ? 'wait' : 'pointer' }}
        >
          <div style={{ fontSize: 40, marginBottom: 14 }}>📄</div>
          <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 8, color: 'var(--ink)', letterSpacing: '-0.3px' }}>Upload RHP / DRHP</div>
          <div style={{ fontSize: 11, color: 'var(--ink2)', marginBottom: 18, lineHeight: 1.7, maxWidth: 260, margin: '0 auto 18px' }}>
            AI extracts key risk factors in seconds.<br />Drop a PDF or click to browse.
          </div>
          <button
            className="btn-blue"
            onClick={e => { e.stopPropagation(); rhpDemo(); }}
            style={{ width: '100%' }}
          >
            {scanning ? 'Scanning…' : 'Try Demo: Ather Energy DRHP ↗'}
          </button>
        </div>

        <div className="card">
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 14 }}>What We Scan For</div>
          {scanChecks.map(([label, c, badge]) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,.04)' }}>
              <span style={{ fontSize: 11, color: 'var(--ink2)' }}>{label}</span>
              <Pill type={c as 'r' | 'g' | 'gold'}>{badge}</Pill>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Results panel */}
      <div>
        {results === null ? (
          <div style={{ height: '100%', minHeight: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 'var(--r3)', padding: '40px 24px', gap: 12 }}>
            <div style={{ fontSize: 44, opacity: 0.12 }}>◈</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink3)' }}>Upload a DRHP or try the demo</div>
            <div style={{ fontSize: 11, color: 'var(--ink4)', textAlign: 'center', maxWidth: 260, lineHeight: 1.65 }}>
              AI reads 300+ pages and surfaces only what matters — in under 2 seconds.
            </div>
            <button className="btn-blue" onClick={rhpDemo} style={{ marginTop: 8 }}>Try Demo</button>
          </div>
        ) : (
          <div>
            {/* Report header */}
            <div style={{ position: 'relative', overflow: 'hidden', background: 'var(--s1)', border: '1px solid rgba(201,153,30,.2)', borderRadius: 'var(--r3)', padding: '18px 22px', marginBottom: 14 }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg,transparent,rgba(201,153,30,.6),transparent)' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 5 }}>RHP Analysis · Ather Energy DRHP</div>
                  <div style={{ fontSize: 11, color: 'var(--ink2)', lineHeight: 1.6 }}>
                    AI extracted <strong style={{ color: 'var(--ink)' }}>{risks.length} key risk factors</strong> from 342 pages.<br />
                    <span style={{ color: 'var(--red)' }}>2 high-severity items</span> require attention before subscribing.
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 4 }}>Risk Score</div>
                  <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--mono)', color: 'var(--gold)', letterSpacing: '-1.5px', lineHeight: 1 }}>58</div>
                  <div style={{ fontSize: 9, color: 'var(--ink3)', marginTop: 2, fontWeight: 700 }}>MODERATE</div>
                </div>
              </div>
            </div>

            {/* Risk items */}
            <div className="card">
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--ink3)', marginBottom: 14 }}>Extracted Risk Factors</div>
              {risks.map((r, i) => (
                <div
                  key={r.title}
                  style={{
                    display: 'flex',
                    gap: 14,
                    padding: '13px 0',
                    borderBottom: i < risks.length - 1 ? '1px solid rgba(255,255,255,.05)' : 'none',
                    paddingLeft: 12,
                    borderLeft: `2px solid ${borderColor[r.c]}`,
                    marginBottom: 2,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 5 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', letterSpacing: '-0.2px' }}>{r.title}</span>
                      <Pill type={r.c as 'r' | 'g' | 'gold'}>{r.level}</Pill>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--ink2)', lineHeight: 1.65 }}>{r.body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
