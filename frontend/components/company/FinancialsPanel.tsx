'use client';
import { useState } from 'react';
import type { Financials } from '@/lib/api';
import { fmtCrore, fmtFY, fmtNum, fmtPct, fmtQuarter } from '@/lib/api';

/** Revenue bars with the profit share drawn inside each bar. */
function QuarterBars({ fin }: { fin: Financials }) {
  const qs = fin.quarters;
  const max = Math.max(1, ...qs.map(q => Math.abs(q.revenue ?? 0)));
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 120 }}>
        {qs.map(q => {
          const rev = Math.max(0, q.revenue ?? 0);
          const prof = q.net_profit ?? 0;
          const h = (rev / max) * 100;
          const ph = rev > 0 ? Math.min(100, (Math.abs(prof) / rev) * 100) : 0;
          return (
            <div key={q.period_end} title={`${fmtQuarter(q.period_end)}: revenue ${fmtCrore(q.revenue)}, profit ${fmtCrore(q.net_profit)} (${fmtPct(q.margin_pct)})`}
              style={{ flex: 1, height: `${h}%`, minHeight: 2, background: 'rgba(201,168,76,0.22)', borderRadius: '2px 2px 0 0', display: 'flex', alignItems: 'flex-end' }}>
              <div style={{ width: '100%', height: `${ph}%`, background: prof < 0 ? 'rgba(196,92,92,0.85)' : 'rgba(0,230,118,0.7)', borderRadius: '2px 2px 0 0' }} />
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        {qs.map((q, i) => (
          <div key={q.period_end} style={{ flex: 1, fontSize: 8, color: 'var(--cream-mute)', textAlign: 'center', fontFamily: 'var(--f-mono)' }}>
            {i % 2 === qs.length % 2 ? fmtQuarter(q.period_end).replace(' 20', " '") : ''}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 14, fontSize: 9, color: 'var(--cream-mute)', marginTop: 8 }}>
        <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'rgba(201,168,76,0.4)', marginRight: 5 }} />Revenue</span>
        <span><span style={{ display: 'inline-block', width: 8, height: 8, background: 'rgba(0,230,118,0.7)', marginRight: 5 }} />Net profit (share of revenue)</span>
      </div>
    </div>
  );
}

function MarginRange({ fin }: { fin: Financials }) {
  const m = fin.margin_history;
  if (!m) return null;
  const span = m.high - m.low || 1;
  const pos = (v: number) => Math.max(2, Math.min(98, ((v - m.low) / span) * 100));
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="ct">Margin against its own history</div>
      <div className="ideal-bar" style={{ marginBottom: 8 }}>
        <div className="ideal-bar-lbl">
          <span>Lowest {fmtPct(m.low)}</span>
          <span>Highest {fmtPct(m.high)}</span>
        </div>
        <div className="ideal-track">
          <div className="ideal-mid" style={{ left: `${pos(m.median)}%` }} />
          <div className="ideal-needle" style={{ left: `${pos(m.now)}%`, background: 'var(--gold)' }} />
        </div>
      </div>
      <p className="mc-plain">
        Trailing-twelve-month net margin is <strong style={{ color: 'var(--cream)' }}>{fmtPct(m.now)}</strong>, higher than on {m.percentile}% of
        quarters since {fmtQuarter(m.since)} (median {fmtPct(m.median)}, the tick on the bar). A margin near its own low can mean costs are rising or prices are under pressure; near its high, the
        business is at its most profitable for this period.
        {m.includes_excise && ' Earlier years include excise duty in revenue, which makes those margins look lower.'}
      </p>
    </div>
  );
}

function Reactions({ fin }: { fin: Financials }) {
  const rows = fin.reactions.slice(-6).reverse();
  if (!rows.length) return null;
  const col = (v: number | null) => (v === null ? 'var(--cream-mute)' : v >= 0 ? 'var(--green)' : 'var(--red)');
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="ct">How the share reacted to results</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead><tr><th>Quarter</th><th>Revenue YoY</th><th>Profit YoY</th><th>Next day vs NIFTY</th><th>5 days vs NIFTY</th></tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.period_end}>
                <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtQuarter(r.period_end)}</td>
                <td style={{ fontFamily: 'var(--f-mono)', color: col(r.revenue_yoy_pct) }}>{fmtPct(r.revenue_yoy_pct, 1, true)}</td>
                <td style={{ fontFamily: 'var(--f-mono)', color: col(r.profit_yoy_pct) }}>{fmtPct(r.profit_yoy_pct, 1, true)}</td>
                <td style={{ fontFamily: 'var(--f-mono)', color: col(r.excess_1d_pct) }}>{fmtPct(r.excess_1d_pct, 1, true)}</td>
                <td style={{ fontFamily: 'var(--f-mono)', color: col(r.excess_5d_pct) }}>{fmtPct(r.excess_5d_pct, 1, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {fin.reaction_note && <p className="mc-plain" style={{ marginTop: 10 }}>{fin.reaction_note}</p>}
    </div>
  );
}

export function FinancialsPanel({ fin }: { fin: Financials }) {
  const [view, setView] = useState<'quarters' | 'years'>('quarters');
  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
          <div className="ct" style={{ marginBottom: 0 }}>Results · {fin.unit} · {fin.basis}</div>
          <div style={{ display: 'flex', gap: 4 }}>
            {(['quarters', 'years'] as const).map(v => (
              <button key={v} onClick={() => setView(v)}
                style={{ fontSize: 9, padding: '3px 9px', borderRadius: 3, cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'var(--f-body)', background: v === view ? 'rgba(201,168,76,0.12)' : 'transparent', color: v === view ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${v === view ? 'var(--border-bright)' : 'var(--border)'}` }}>
                {v}
              </button>
            ))}
          </div>
        </div>
        {view === 'quarters' ? <QuarterBars fin={fin} /> : (
          <div style={{ overflowX: 'auto' }}>
            <table className="tbl">
              <thead><tr><th>Year</th><th>Revenue</th><th>Net profit</th><th>Margin</th></tr></thead>
              <tbody>
                {[...fin.years].reverse().map(y => (
                  <tr key={y.fiscal_year}>
                    <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtFY(y.fiscal_year)}</td>
                    <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtCrore(y.revenue)}</td>
                    <td style={{ fontFamily: 'var(--f-mono)', color: (y.net_profit ?? 0) < 0 ? 'var(--red)' : 'var(--cream)' }}>{fmtCrore(y.net_profit)}</td>
                    <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtPct(y.margin_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="g4" style={{ marginTop: 14 }}>
          {[
            ['Net margin', fmtPct(fin.metrics.net_margin)],
            ['3-yr revenue growth', fin.metrics.revenue_cagr_3yr === null ? '—' : `${fmtNum(fin.metrics.revenue_cagr_3yr)}% a year`],
            ['Return on equity', fmtPct(fin.metrics.roe)],
            ['Debt to equity', fin.metrics.debt_equity === null ? '—' : `${fmtNum(fin.metrics.debt_equity, 2)}×`],
          ].map(([l, v]) => (
            <div key={l}>
              <div style={{ fontSize: 9, color: 'var(--cream-mute)', letterSpacing: '1px', textTransform: 'uppercase' }}>{l}</div>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 14, color: 'var(--cream)', marginTop: 4 }}>{v}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.6 }}>
          From the company&apos;s own filings ({fin.source}), figures to {fmtQuarter(fin.metrics.as_of)}. Revenue means {fin.revenue_means}.
        </p>
      </div>
      <MarginRange fin={fin} />
      <Reactions fin={fin} />
    </div>
  );
}
