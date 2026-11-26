'use client';
import type { Dividends } from '@/lib/api';
import { fmtFY, fmtRupees } from '@/lib/api';

export function DividendsPanel({ d }: { d: Dividends }) {
  const max = Math.max(1, ...d.years.map(y => y.per_share));
  const date = (s: string) => new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  return (
    <div className="g2" style={{ alignItems: 'start' }}>
      <div className="card">
        <div className="ct">Dividend per share by year</div>
        {d.years.length ? (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 100 }}>
            {d.years.map(y => (
              <div key={y.fiscal_year} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                <div style={{ fontSize: 9, fontFamily: 'var(--f-mono)', color: 'var(--cream-dim)', marginBottom: 4 }}>{fmtRupees(y.per_share)}</div>
                <div style={{ width: '100%', height: `${(y.per_share / max) * 70}%`, minHeight: 2, background: 'rgba(201,168,76,0.5)', borderRadius: '2px 2px 0 0' }} />
                <div style={{ fontSize: 9, fontFamily: 'var(--f-mono)', color: 'var(--cream-mute)', marginTop: 4 }}>{fmtFY(y.fiscal_year)}</div>
              </div>
            ))}
          </div>
        ) : <p className="mc-plain">No dividends in the past five years.</p>}
        {d.note && <p className="mc-plain" style={{ marginTop: 12, color: 'var(--cream)' }}>{d.note}</p>}
        <p className="mc-plain" style={{ marginTop: 6 }}>
          A long, steady dividend record usually means dependable cash flow. A very high yield can also mean the price has fallen, so check why.
        </p>
      </div>
      <div className="card">
        <div className="ct">Record</div>
        <div className="stat-r"><span className="sl">Past 12 months</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{fmtRupees(d.ttm_per_share)} per share</span></div>
        <div className="stat-r"><span className="sl">Years paid in a row</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{d.paid_years_in_a_row}{d.streak_since_data_start ? '+' : ''}</span></div>
        {d.last_dividend && (
          <div className="stat-r"><span className="sl">Last dividend</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{fmtRupees(d.last_dividend.per_share)} · ex {date(d.last_dividend.ex_date)}</span></div>
        )}
        {d.capital_actions.length > 0 && (
          <>
            <div className="ct" style={{ marginTop: 14, marginBottom: 6 }}>Splits and bonus issues</div>
            {d.capital_actions.slice(-5).reverse().map(a => (
              <div key={a.ex_date + a.kind} className="stat-r">
                <span className="sl" style={{ textTransform: 'capitalize' }}>{a.kind} {a.subject.match(/\d+\s*:\s*\d+/)?.[0] ?? ''}</span>
                <span className="sv" style={{ fontFamily: 'var(--f-mono)', fontSize: 10 }}>{date(a.ex_date)}</span>
              </div>
            ))}
            <p className="mc-plain" style={{ marginTop: 6 }}>Splits and bonuses add shares without changing what the company is worth; past prices are adjusted for them.</p>
          </>
        )}
        <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>{d.source}{d.data_from_fiscal_year ? `, from FY${String(d.data_from_fiscal_year).slice(-2)}` : ''}.</p>
      </div>
    </div>
  );
}
