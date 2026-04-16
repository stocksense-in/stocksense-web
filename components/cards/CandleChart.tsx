'use client';
import React from 'react';
import { C } from '@/lib/constants';

export function CandleChart() {
  const candles = Array.from({ length: 28 }, (_, i) => {
    const open = 1800 + Math.sin(i * 0.4) * 120 + (Math.random() - 0.5) * 60;
    const close = open + (Math.random() - 0.47) * 50;
    const high = Math.max(open, close) + Math.random() * 30;
    const low = Math.min(open, close) - Math.random() * 30;
    const up = close >= open;
    const range = 220, minP = 1620;
    const bodyH = Math.max(4, Math.abs(close - open) / range * 90);
    const wickTopH = (high - Math.max(open, close)) / range * 90;
    const wickBotH = (Math.min(open, close) - low) / range * 90;
    return { up, bodyH, wickTopH, wickBotH, dim: i < 6 };
  });

  return (
    <div className="chart-wrap">
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>
        Price Action · 30 Days
      </div>
      <div className="chart-grid-lines">
        {Array(5).fill(0).map((_, i) => <div key={i} className="chart-grid-line" />)}
      </div>
      <div className="candles">
        {candles.map((c, i) => (
          <div key={i} className="candle-g" style={{ height: '100%', justifyContent: 'flex-end' }}>
            <div className="wick" style={{ height: c.wickTopH }} />
            <div className="body-c" style={{ height: c.bodyH, background: c.up ? C.green : C.red, opacity: c.dim ? 0.35 : 0.85 }} />
            <div className="wick" style={{ height: c.wickBotH }} />
          </div>
        ))}
      </div>
      <div className="buy-zone">
        <div className="buy-zone-lbl"><div className="buy-zone-dot" />Institutional Buying Zone</div>
      </div>
    </div>
  );
}