'use client';
import React, { useState } from 'react';
import { MetricKey } from '@/lib/types';
import { MM, C } from '@/lib/constants';
import { getMetricStatus, pillClass } from '@/lib/utils';

export function MetricCard({ mk, val, sector }: { mk: MetricKey; val: number; sector: string }) {
  const [open, setOpen] = useState(false);
  const m = MM[mk];
  const st = getMetricStatus(mk, val, sector);
  const dc = st === 'green' ? C.green : st === 'yellow' ? C.gold : C.red;
  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  const dl = Math.max(1, Math.min(97, n));
  const il = Math.max(0, Math.min(90, ip));
  const bcl = st === 'green' ? 'pill-g' : st === 'yellow' ? 'pill-gold' : 'pill-r';
  const bl = st === 'green' ? 'Healthy' : st === 'yellow' ? 'Monitor' : 'Concern';
  const borderColor = st === 'green' ? 'rgba(0,230,118,.2)' : st === 'yellow' ? 'rgba(212,175,55,.2)' : 'rgba(255,58,58,.2)';

  return (
    <div className={`mc${open ? ' open' : ''}`} style={{ borderColor }} onClick={() => setOpen(o => !o)}>
      <div className="mc-top">
        <span className="mc-name">{m.name}</span>
        <div className="status-dot" style={{ background: dc, boxShadow: `0 0 6px ${dc}` }} />
      </div>
      <div className="mc-val">{val}<sup> {m.unit}</sup></div>
      <div className="ideal-bar">
        <div className="ideal-bar-lbl">
          <span>{m.lo}</span>
          <span style={{ color: C.gold, fontSize: 8 }}>▌ Ideal zone</span>
          <span>{m.hi}</span>
        </div>
        <div className="ideal-track">
          <div className="ideal-zone" style={{ left: `${il}%`, width: `${iw}%`, background: dc }} />
          <div className="ideal-mid" style={{ left: `${il + iw / 2}%` }} />
          <div className="ideal-needle" style={{ left: `${dl}%`, background: dc, boxShadow: `0 0 6px ${dc}` }} />
        </div>
        <div className="ideal-ann">
          <span style={{ fontSize: 9, color: C.ink3 }}>Ideal: {m.il}</span>
          <span className={`pill ${bcl}`} style={{ fontSize: 8 }}>{bl}</span>
        </div>
      </div>
      <div className="mc-plain">{m.plain(val, sector)}</div>
      {open && (
        <div className="mc-expand">
          <div className="exp-body">{m.verd(val, sector)} — {m.plain(val, sector)}</div>
          <div className="exp-rule">
            <strong style={{ color: C.gold }}>Ideal range: {m.il}</strong> · This stock: {val}{m.unit} ·{' '}
            {st === 'green' ? 'Within the ideal zone for this sector.' : st === 'yellow' ? 'Near the boundary — watch closely.' : 'Outside the ideal range — understand why before investing.'}
          </div>
          <div className="exp-verd" style={{ color: dc }}>"{m.verd(val, sector)}"</div>
        </div>
      )}
    </div>
  );
}