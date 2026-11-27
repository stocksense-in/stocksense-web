'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Alert } from '@/lib/api';
import { api, fmtCrore } from '@/lib/api';

const day = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
const SHOWN = 6;

/** The market's largest bulk and block deals of the latest session: which funds and big investors bought or sold what. */
export function BigDealsCard() {
  const router = useRouter();
  const [rows, setRows] = useState<Alert[] | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    api.alerts({ kind: 'big_deal', days: 3, limit: 200 })
      .then(d => { if (alive) setRows(d?.alerts ?? null); })
      .catch(() => { if (alive) setRows(null); });
    return () => { alive = false; };
  }, []);

  if (!rows || !rows.length) return null;  // loading, unavailable, or no deal of ₹10 crore+ lately
  const latest = rows[0].date;
  const top = rows.filter(a => a.date === latest).sort((a, b) => Math.abs(b.value ?? 0) - Math.abs(a.value ?? 0)).slice(0, SHOWN);
  return (
    <div className="card">
      <div className="ct">Big deals · {day(latest)}</div>
      {top.map((a, i) => {
        const bought = (a.value ?? 0) >= 0;
        return (
          <button key={a.symbol + i} onClick={() => router.push(`/analysis?s=${encodeURIComponent(a.symbol)}&tab=events`)}
            style={{ all: 'unset', cursor: 'pointer', display: 'block', width: '100%', padding: '7px 0', borderBottom: i < top.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none' }}
            title={a.text}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--cream)', fontFamily: 'var(--f-mono)' }}>{a.symbol}</span>
              <span style={{ fontSize: 11, fontFamily: 'var(--f-mono)', color: bought ? 'var(--green)' : 'var(--red)' }}>
                {bought ? 'Bought' : 'Sold'} {fmtCrore(Math.abs(a.value ?? 0))}
              </span>
            </div>
            <div style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 2, lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {a.text.split(/ (?:bought|sold) /)[0]} · {/ in a block deal/.test(a.text) ? 'block deal' : 'bulk deal'}
            </div>
          </button>
        );
      })}
      <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10, lineHeight: 1.6 }}>
        The day&apos;s largest deal per company of ₹10 crore or more, as NSE publishes them. A fund building or cutting a stake is worth a look, not a reason on its own.
      </p>
    </div>
  );
}
