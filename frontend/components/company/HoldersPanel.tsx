'use client';
import type { Holders } from '@/lib/api';
import { fmtPct, fmtQuarter } from '@/lib/api';

const SPLIT: [keyof Holders['quarters'][number], string, string, string][] = [
  ['promoter_pct', 'Promoters', '#C9A84C', 'founders or parent company and their group'],
  ['fii_pct', 'Foreign institutions', '#E8C96A', 'overseas funds (FIIs/FPIs)'],
  ['mutual_funds_pct', 'Mutual funds', '#00E676', 'Indian mutual funds'],
  ['insurance_pct', 'Insurers', '#5BC08A', 'LIC and other insurance companies'],
  ['small_retail_pct', 'Small investors', '#B8AFA0', 'individuals holding up to ₹2 lakh of shares'],
  ['government_pct', 'Government', '#8C7A4A', 'central or state government'],
];

function PromoterTrend({ h }: { h: Holders }) {
  const qs = h.quarters.filter(q => q.promoter_pct !== null);
  if (qs.length < 2) return null;
  const W = 300, H = 60;
  const vals = qs.map(q => q.promoter_pct as number);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = Math.max(hi - lo, 2);
  const mid = (hi + lo) / 2;
  const y = (v: number) => H / 2 - ((v - mid) / span) * (H - 8);
  const x = (i: number) => (i / (qs.length - 1)) * W;
  const d = vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 60, display: 'block' }} role="img" aria-label="Promoter holding by quarter">
        <path d={d} fill="none" stroke="#C9A84C" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)', marginTop: 4 }}>
        <span>{fmtQuarter(qs[0].quarter_end)} · {fmtPct(vals[0])}</span>
        <span>{fmtQuarter(qs[qs.length - 1].quarter_end)} · {fmtPct(vals[vals.length - 1])}</span>
      </div>
    </div>
  );
}

export function HoldersPanel({ h }: { h: Holders }) {
  const latest = [...h.quarters].reverse().find(q => q.fii_pct !== null || q.dii_pct !== null) ?? h.quarters[h.quarters.length - 1];
  const rows = SPLIT.filter(([k]) => latest && latest[k] !== null && latest[k] !== undefined);
  const promoterPledged = h.pledge?.pledged_pct_of_promoter;
  return (
    <div className="g2" style={{ alignItems: 'start' }}>
      <div className="card">
        <div className="ct">Who owns the company · {latest ? fmtQuarter(latest.quarter_end) : ''}</div>
        {rows.map(([k, label, color, means]) => {
          const v = latest[k] as number;
          return (
            <div key={k} style={{ marginBottom: 10 }} title={means}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                <span style={{ color: 'var(--cream-dim)' }}>{label}</span>
                <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--cream)' }}>{fmtPct(v)}</span>
              </div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.min(100, v)}%`, background: color }} /></div>
            </div>
          );
        })}
        {latest?.dii_pct !== null && latest?.dii_pct !== undefined && (
          <p className="mc-plain" style={{ marginTop: 6 }}>Domestic institutions together (mutual funds, insurers, banks, pension funds): {fmtPct(latest.dii_pct)}.</p>
        )}
        <p className="mc-plain" style={{ marginTop: 8 }}>
          Promoters putting their own money at stake can align them with shareholders; large holdings by funds mean professional investors have studied the company.
          Neither guarantees anything.
        </p>
      </div>
      <div>
        <div className="card">
          <div className="ct">Promoter holding over time</div>
          <PromoterTrend h={h} />
          {h.trend_note && <p className="mc-plain" style={{ marginTop: 10, color: 'var(--cream)' }}>{h.trend_note}</p>}
          <p className="mc-plain" style={{ marginTop: 6 }}>A steady or rising stake is usually read as confidence; a falling one is worth a look at why (sales, dilution or a share issue).</p>
        </div>
        {h.pledge && (
          <div className={h.pledge_warning ? 'card card-alert' : 'card'} style={{ marginTop: 12 }}>
            <div className="ct">Pledged shares · {fmtQuarter(h.pledge.as_of)}</div>
            <div className="stat-r"><span className="sl">Promoter shares pledged</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{fmtPct(promoterPledged)}</span></div>
            <div className="stat-r"><span className="sl">As a share of the whole company</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{fmtPct(h.pledge.pledged_pct_of_total, 2)}</span></div>
            {h.pledge_warning
              ? <p className="mc-plain" style={{ marginTop: 8, color: 'var(--red)' }}>{h.pledge_warning}</p>
              : <p className="mc-plain" style={{ marginTop: 8 }}>Promoters who pledge shares have borrowed against them; if the price falls far, lenders can sell, which pushes it lower still.</p>}
          </div>
        )}
        <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>{h.source}.</p>
      </div>
    </div>
  );
}
