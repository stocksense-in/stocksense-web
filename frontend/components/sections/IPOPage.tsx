'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Ipo, IpoBoard, Listing } from '@/lib/api';
import { api, fmtNum, fmtPct, fmtRupees } from '@/lib/api';

const DEMAND: Record<string, [string, string]> = {
  strong: ['pill pill-g', 'Strong demand'],
  moderate: ['pill pill-gold', 'Moderate demand'],
  weak: ['pill pill-r', 'Demand building'],
  early: ['pill pill-b', 'Not started'],
};

const CATEGORIES: [keyof Ipo['subscription'], string, string][] = [
  ['total', 'Overall', 'All bids against all shares on offer.'],
  ['qib', 'Institutions (QIB)', 'Mutual funds, insurers, banks and foreign funds. They study the company closely, so their demand is the most watched.'],
  ['nii', 'High-net-worth (NII)', 'Individuals and firms bidding more than ₹2 lakh.'],
  ['retail', 'Retail', 'Individuals bidding up to ₹2 lakh.'],
  ['employees', 'Employees', 'The company’s own staff, often at a discount.'],
];

const date = (s: string | null) => (s ? new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—');
const band = (i: Ipo) => (i.price_low === null ? '—' : i.price_low === i.price_high ? fmtRupees(i.price_low) : `${fmtRupees(i.price_low)}–${fmtRupees(i.price_high)}`);
const times = (v: number | null) => (v === null ? '—' : `${fmtNum(v, v < 10 ? 2 : 1)}×`);

function IpoCard({ ipo, selected, onSelect }: { ipo: Ipo; selected: boolean; onSelect: () => void }) {
  const [cls, label] = DEMAND[ipo.demand.level] ?? DEMAND.early;
  return (
    <div onClick={onSelect} className={`ipo-card${selected ? ' sel' : ''}`} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && onSelect()}>
      {selected && <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 2, background: 'var(--gold)' }} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, gap: 8 }}>
        <div style={{ paddingLeft: selected ? 8 : 0, transition: 'padding .15s', minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--cream)', letterSpacing: '-0.3px', marginBottom: 4 }}>{ipo.name}</div>
          <div style={{ fontSize: 9, fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--cream-mute)' }}>
            {ipo.board === 'sme' ? 'SME' : 'Mainboard'} · {date(ipo.opens)} – {date(ipo.closes)}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 20, fontWeight: 500, fontFamily: 'var(--f-mono)', color: 'var(--cream)', letterSpacing: '-1px', lineHeight: 1 }}>{times(ipo.subscription.total)}</div>
          <div style={{ fontSize: 7, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--cream-mute)', marginTop: 2, fontFamily: 'var(--f-mono)' }}>SUBSCRIBED</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span className={cls}>{label}</span>
          <span style={{ fontSize: 10, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)' }}>{band(ipo)}</span>
        </div>
        <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>{ipo.size_crore === null ? '' : `₹${fmtNum(ipo.size_crore, 0)} Cr`}</span>
      </div>
    </div>
  );
}

function IpoDetail({ ipo }: { ipo: Ipo }) {
  const sub = ipo.subscription;
  const max = Math.max(1, ...CATEGORIES.map(([k]) => (sub[k] as number | null) ?? 0));
  const [cls, label] = DEMAND[ipo.demand.level] ?? DEMAND.early;
  return (
    <div>
      <div style={{ position: 'relative', overflow: 'hidden', background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 22px', marginBottom: 14 }}>
        <div className="ct" style={{ marginBottom: 6 }}>{ipo.board === 'sme' ? 'SME platform' : 'Mainboard'} · {ipo.size_crore === null ? 'size not stated' : `₹${fmtNum(ipo.size_crore, 1)} Cr issue`}</div>
        <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--cream)', marginBottom: 8, fontFamily: 'var(--f-display)' }}>{ipo.name}</div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className={cls}>{label}</span>
          <span style={{ fontSize: 10, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)' }}>Price band {band(ipo)}</span>
          <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>Bidding {date(ipo.opens)} – {date(ipo.closes)}</span>
        </div>
        <p className="mc-plain" style={{ marginTop: 12, color: 'var(--cream)' }}>{ipo.demand.summary}</p>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="ct">Subscription by investor type{sub.updated_at ? ` · ${sub.updated_at.replace('Updated as on ', '')}` : ''}</div>
        {CATEGORIES.map(([k, name, means]) => {
          const v = sub[k] as number | null;
          if (v === null && (k === 'employees' || (k !== 'total' && sub.total !== null && sub.qib === null && sub.retail === null))) return null;
          const col = v === null ? 'var(--cream-mute)' : v >= 1 ? 'var(--green)' : 'var(--gold)';
          return (
            <div key={k} style={{ marginBottom: 14 }} title={means}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--cream)' }}>{name}</span>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 12, fontWeight: 500, color: col }}>{times(v)}</span>
              </div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${v === null ? 0 : Math.max(2, (v / max) * 100)}%`, background: col }} /></div>
              <div style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 5 }}>{means}</div>
            </div>
          );
        })}
        <p className="mc-plain">
          &quot;3×&quot; means bids for three times the shares on offer in that category. 1× means fully subscribed. Heavy demand often lifts the listing price,
          but it says nothing about the business itself. For that, read the prospectus.
        </p>
      </div>
    </div>
  );
}

export function IPOPage() {
  const router = useRouter();
  const [board, setBoard] = useState<IpoBoard | null | undefined>(undefined);
  const [listings, setListings] = useState<Listing[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [boardFilter, setBoardFilter] = useState<'all' | 'mainboard' | 'sme'>('all');

  useEffect(() => {
    let alive = true;
    api.ipos().then(b => { if (alive) setBoard(b); });
    api.listings().then(l => { if (alive) setListings(l); });
    return () => { alive = false; };
  }, []);

  const keep = (i: Ipo) => boardFilter === 'all' || i.board === boardFilter;
  const open = (board?.open ?? []).filter(keep);
  const upcoming = (board?.upcoming ?? []).filter(keep);
  const all = [...open, ...upcoming];
  const sel = all.find(i => i.symbol === selected) ?? all[0] ?? null;
  // Mainboard listings first: StockSense tracks their prices, most SME listings it doesn't yet.
  const recent = (listings ?? [])
    .filter(l => boardFilter === 'all' || l.board === boardFilter)
    .sort((a, b) => Number(a.board !== 'mainboard') - Number(b.board !== 'mainboard') || b.listed.localeCompare(a.listed))
    .slice(0, 12);

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div className="ct" style={{ marginBottom: 3 }}>IPOs open for bidding and coming up</div>
          <div style={{ fontSize: 12, color: 'var(--cream-dim)' }}>Who is bidding, how much, and what that does and doesn&apos;t tell you.</div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {(['all', 'mainboard', 'sme'] as const).map(b => (
            <button key={b} onClick={() => setBoardFilter(b)}
              style={{ fontSize: 9, padding: '4px 10px', borderRadius: 3, cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '1px', background: b === boardFilter ? 'rgba(201,168,76,0.12)' : 'transparent', color: b === boardFilter ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${b === boardFilter ? 'var(--border-bright)' : 'var(--border)'}` }}>
              {b === 'sme' ? 'SME' : b}
            </button>
          ))}
        </div>
        <span className="live-badge"><div className="live-dot" />IPO TRACKER</span>
      </div>

      {board === null && (
        <div className="card" style={{ fontSize: 11, color: 'var(--cream-mute)', marginBottom: 14 }}>IPO data isn&apos;t reachable right now.</div>
      )}

      <div className="split" style={{ display: 'grid', gridTemplateColumns: '340px minmax(0,1fr)', gap: 12 }}>
        <div>
          {open.length > 0 && <div className="ct" style={{ margin: '0 0 8px' }}>Open now · {open.length}</div>}
          {open.map(i => <IpoCard key={i.symbol} ipo={i} selected={sel?.symbol === i.symbol} onSelect={() => setSelected(i.symbol)} />)}
          {upcoming.length > 0 && <div className="ct" style={{ margin: '14px 0 8px' }}>Coming up · {upcoming.length}</div>}
          {upcoming.map(i => <IpoCard key={i.symbol} ipo={i} selected={sel?.symbol === i.symbol} onSelect={() => setSelected(i.symbol)} />)}
          {board && all.length === 0 && <div className="card" style={{ fontSize: 11, color: 'var(--cream-mute)' }}>No IPOs open or announced on this board right now.</div>}

          <div className="card" style={{ marginTop: 4 }}>
            <div className="ct">Before you bid</div>
            <p className="mc-plain">SME IPOs are smaller, less liquid and lightly regulated: lots are large (often over ₹1 lakh) and prices can swing hard after listing.</p>
            <p className="mc-plain" style={{ marginTop: 6 }}>Read the risk factors and use of proceeds in the prospectus. The RHP scanner flags common warning signs.</p>
            <button className="btn-ghost" style={{ marginTop: 10 }} onClick={() => router.push('/rhp-analyser')}>Open the RHP scanner →</button>
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          {sel ? <IpoDetail ipo={sel} /> : board === undefined ? (
            <div className="card" style={{ fontSize: 11, color: 'var(--cream-mute)', padding: 40, textAlign: 'center' }}>Loading IPOs…</div>
          ) : null}

          {recent.length > 0 && (
            <div className="card">
              <div className="ct">Recent listings · how they have done</div>
              <div style={{ overflowX: 'auto' }}>
                <table className="tbl">
                  <thead><tr><th>Company</th><th>Listed</th><th style={{ textAlign: 'right' }}>Issue price</th><th style={{ textAlign: 'right' }}>Now</th><th style={{ textAlign: 'right' }}>Return</th></tr></thead>
                  <tbody>
                    {recent.map(l => (
                      <tr key={l.symbol + l.listed} onClick={() => l.price !== null && router.push(`/analysis?s=${encodeURIComponent(l.symbol)}`)} style={{ cursor: l.price !== null ? 'pointer' : 'default' }}>
                        <td>
                          <div style={{ fontSize: 11.5, color: 'var(--cream)' }}>{l.name}</div>
                          <div style={{ fontSize: 9, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)', marginTop: 2 }}>{l.symbol} · {l.board === 'sme' ? 'SME' : 'Mainboard'}</div>
                        </td>
                        <td style={{ fontFamily: 'var(--f-mono)', fontSize: 11 }}>{date(l.listed)}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtRupees(l.issue_price)}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{fmtRupees(l.price)}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11, color: l.return_pct === null ? 'var(--cream-mute)' : l.return_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>{fmtPct(l.return_pct, 1, true)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>Returns are from the issue price to the latest close, where StockSense tracks the stock (most SME listings aren&apos;t tracked yet).</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
