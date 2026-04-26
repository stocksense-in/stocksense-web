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

export function PaperTradingPage() {
  const [cash, setCash] = useState(100000);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [dayCount, setDayCount] = useState(0);
  const [completedMissions, setCompletedMissions] = useState<Set<string>>(new Set());
  const [ptStock, setPtStock] = useState('INFY|1842');
  const [ptQty, setPtQty] = useState(5);
  const [ptSl, setPtSl] = useState(7);
  const [toast, setToast] = useState<{ msg: string; color: string } | null>(null);
  const [insight, setInsight] = useState('');

  const showToast = (msg: string, color = C.blue) => {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 3200);
  };

  const [sym, priceStr] = ptStock.split('|');
  const price = parseFloat(priceStr);
  const estCost = Math.round(price * ptQty);

  const inv = holdings.reduce((s, h) => s + h.qty * h.avgCost, 0);
  const mkt = holdings.reduce((s, h) => s + h.qty * h.ltp, 0);
  const pnl = mkt - inv;
  const total = cash + mkt;
  const pnlPct = inv > 0 ? (pnl / inv * 100).toFixed(2) : '0.00';

  const updateInsight = (hs: Holding[]) => {
    const totalInvested = hs.reduce((s, h) => s + h.qty * h.avgCost, 0);
    for (const h of hs) {
      const pct = h.qty * h.avgCost / (totalInvested || 1);
      if (pct > 0.30) { setInsight(`${h.sym} is >${Math.round(pct * 100)}% of portfolio — consider reducing concentration.`); return; }
      const pp = ((h.ltp - h.avgCost) / h.avgCost * 100);
      if (pp > 15) { setInsight(`${h.sym} is up ${pp.toFixed(1)}% — consider booking partial profits.`); return; }
    }
    setInsight('');
  };

  const ptTrade = (side: 'BUY' | 'SELL') => {
    if (side === 'BUY') {
      const total = price * ptQty + 29;
      if (total > cash) { showToast('Insufficient capital', C.red); return; }
      setHoldings(prev => {
        const ex = prev.find(h => h.sym === sym);
        let next: Holding[];
        if (ex) {
          next = prev.map(h => h.sym === sym ? { ...h, qty: h.qty + ptQty, avgCost: (h.avgCost * h.qty + price * ptQty) / (h.qty + ptQty), sl: price * (1 - ptSl / 100) } : h);
        } else {
          next = [...prev, { sym, qty: ptQty, avgCost: price, ltp: price, sl: price * (1 - ptSl / 100), daysHeld: 0, hist: [price] }];
        }
        updateInsight(next);
        return next;
      });
      setCash(c => c - total);
      setCompletedMissions(m => new Set([...m, 'first-trade']));
      showToast(`Bought ${ptQty} × ${PT_STOCKS[sym]?.n || sym} @ ${formatINR(price)}`, C.green);
    } else {
      const h = holdings.find(h => h.sym === sym);
      if (!h) { showToast('No position in ' + sym, C.red); return; }
      setCash(c => c + h.ltp * h.qty - 29);
      setHoldings(prev => prev.filter(x => x.sym !== sym));
      showToast(`Exited ${sym}`, C.gold);
    }
  };

  const simDay = () => {
    if (!holdings.length) { showToast('No holdings to simulate'); return; }
    setDayCount(d => d + 1);
    const completed = new Set(completedMissions);
    setHoldings(prev => {
      let next = prev.map(h => {
        const vol = PT_STOCKS[h.sym]?.vol || 0.018;
        const ltp = Math.max(1, Math.round(h.ltp * (1 + (Math.random() - 0.47) * vol * 2)));
        const hist = [...h.hist, ltp].slice(-12);
        const daysHeld = h.daysHeld + 1;
        if (ltp <= h.sl) {
          setCash(c => c + ltp * h.qty - 29);
          showToast(`Stop loss: ${h.sym} exited @ ${formatINR(ltp)}`, C.red);
          completed.add('stop-loss');
        }
        if (daysHeld >= 3 && ltp < h.avgCost) completed.add('survive-red');
        return { ...h, ltp, hist, daysHeld };
      }).filter(h => h.ltp > h.sl);
      const sectors = new Set(next.map(h => h.sym));
      if (sectors.size >= 3) completed.add('diversify');
      setCompletedMissions(completed);
      updateInsight(next);
      return next;
    });
    showToast(`Day ${dayCount + 1} simulated — markets moved`, C.blue);
  };

  const quickExit = (exitSym: string) => {
    const h = holdings.find(x => x.sym === exitSym);
    if (!h) return;
    setCash(c => c + h.ltp * h.qty - 29);
    setHoldings(prev => prev.filter(x => x.sym !== exitSym));
    showToast('Exited ' + exitSym, C.gold);
  };

  const missions = [
    { id: 'first-trade', title: 'First Trade', desc: 'Execute your first buy order.', ic: 'm-ic-blue' },
    { id: 'diversify', title: 'Diversification', desc: 'Hold 3+ different stocks simultaneously.', ic: 'm-ic-blue' },
    { id: 'stop-loss', title: 'Stop Loss', desc: 'Watch a stop loss trigger in simulation.', ic: 'm-ic-gold' },
    { id: 'survive-red', title: 'Hold Through Red', desc: 'Keep a losing position for 3+ simulated days.', ic: 'm-ic-gold' },
    { id: 'golden-hour', title: 'Golden Hour', desc: 'Buy a stock during a market dip.', ic: 'm-ic-gold' },
    { id: 'week-profit', title: 'Green Week', desc: 'End 7 simulated days with overall profit.', ic: 'm-ic-blue' },
  ];

  return (
    <div>
      {toast && (
        <div className="toast show">
          <span style={{ color: toast.color }}>{toast.msg}</span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
        <div className="sim-badge"><div className="sim-dot" />Simulation Mode · Virtual ₹1,00,000</div>
        <button className="btn-ghost" style={{ fontSize: 10 }} onClick={simDay}>Simulate Next Day ↻</button>
      </div>

      <div className="g4" style={{ marginBottom: 12 }}>
        <div className="card card-blue">
          <div className="ct" style={{ color: C.blue }}>Virtual Capital</div>
          <div className="bn bn-blue">{formatINR(total)}</div>
          <div style={{ fontSize: 9, color: C.ink3, marginTop: 3 }}>Total portfolio value</div>
        </div>
        <div className="card card-gold">
          <div className="ct" style={{ color: C.gold }}>Savings Potential</div>
          <div className="bn bn-gold">{formatINR(total * 0.18)}</div>
          <div style={{ fontSize: 9, color: C.ink3, marginTop: 3 }}>Projected 1yr at 18% avg</div>
        </div>
        <div className="card">
          <div className="ct">Unrealised P&amp;L</div>
          <div className="bn" style={{ color: pnl >= 0 ? C.green : C.red }}>{pnl >= 0 ? '+' : '-'}{formatINR(Math.abs(pnl))}</div>
          <div style={{ fontSize: 9, marginTop: 3, color: pnl >= 0 ? C.green : C.red }}>{pnl >= 0 ? '+' : ''}{pnlPct}%</div>
        </div>
        <div className="card">
          <div className="ct">Available Cash</div>
          <div className="bn">{formatINR(cash)}</div>
          <div style={{ fontSize: 9, color: C.green, marginTop: 3 }}>Free to deploy</div>
        </div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Execute Trade</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
            <div>
              <div className="field-label">Stock</div>
              <select className="fi" value={ptStock} onChange={e => setPtStock(e.target.value)}>
                <option value="INFY|1842">Infosys · ₹1,842</option>
                <option value="HDFCBANK|1623">HDFC Bank · ₹1,623</option>
                <option value="TATAMOTORS|934">Tata Motors · ₹934</option>
                <option value="ZOMATO|224">Zomato · ₹224</option>
                <option value="RELIANCE|2934">Reliance · ₹2,934</option>
              </select>
            </div>
            <div>
              <div className="field-label">Quantity</div>
              <input className="fi" type="number" value={ptQty} min={1} onChange={e => setPtQty(Number(e.target.value))} />
            </div>
            <div>
              <div className="field-label">Order Type</div>
              <select className="fi"><option>Market Order</option><option>Limit Order</option><option>Stop Loss</option></select>
            </div>
            <div>
              <div className="field-label">Stop Loss %</div>
              <input className="fi" type="number" value={ptSl} min={1} max={20} onChange={e => setPtSl(Number(e.target.value))} />
            </div>
          </div>
          <div className="nudge">Mission 1: Set a Stop Loss to protect your capital — every trade needs one.</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: C.ink3, margin: '9px 0 10px' }}>
            <span>Est. cost: <strong style={{ color: C.blue }}>{formatINR(estCost)}</strong></span>
            <span>Brokerage + STT: <strong style={{ color: C.ink2 }}>₹29</strong></span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <button className="btn-blue" onClick={() => ptTrade('BUY')}>Buy / Long ↗</button>
            <button className="btn-ghost" style={{ color: C.red, borderColor: 'rgba(255,58,58,.2)' }} onClick={() => ptTrade('SELL')}>Exit Position</button>
          </div>
        </div>

        <div className="card">
          <div className="ct">Holdings</div>
          {holdings.length === 0 ? (
            <div style={{ fontSize: 11, color: C.ink3, padding: '16px 0', textAlign: 'center' }}>No positions yet. Execute a trade to begin.</div>
          ) : (
            <>
              <table className="tbl">
                <thead><tr><th>Stock</th><th>Qty</th><th>Avg</th><th>LTP</th><th>P&amp;L</th><th>Exit</th></tr></thead>
                <tbody>
                  {holdings.map(h => {
                    const hPnl = (h.ltp - h.avgCost) * h.qty;
                    const hPnlPct = ((h.ltp - h.avgCost) / h.avgCost * 100).toFixed(1);
                    const hc = hPnl >= 0 ? C.green : C.red;
                    const mn = Math.min(...h.hist), mx = Math.max(...h.hist), r = mx - mn || 1;
                    return (
                      <tr key={h.sym}>
                        <td>
                          <div style={{ fontWeight: 600, fontSize: 11 }}>{h.sym}</div>
                          <div className="sparkline" style={{ marginTop: 3 }}>
                            {h.hist.map((v, i) => (
                              <div key={i} className="spark-b" style={{ height: `${Math.max(10, (v - mn) / r * 100)}%`, background: v >= h.avgCost ? C.green : C.red }} />
                            ))}
                          </div>
                        </td>
                        <td style={{ fontFamily: 'monospace' }}>{h.qty}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{formatINR(h.avgCost)}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{formatINR(h.ltp)}</td>
                        <td>
                          <div style={{ fontFamily: 'monospace', fontSize: 11, color: hc }}>{hPnl >= 0 ? '+' : '-'}{formatINR(Math.abs(hPnl))}</div>
                          <div style={{ fontFamily: 'monospace', fontSize: 9, color: hc }}>{hPnl >= 0 ? '+' : ''}{hPnlPct}%</div>
                        </td>
                        <td>
                          <button onClick={() => quickExit(h.sym)} style={{ background: 'transparent', border: '1px solid var(--border)', color: C.ink2, borderRadius: 5, padding: '3px 9px', fontSize: 9, cursor: 'pointer', fontFamily: 'var(--f)' }}>EXIT</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {insight && <div className="nudge" style={{ marginTop: 8 }}>{insight}</div>}
            </>
          )}
        </div>
      </div>

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Learning Missions</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
        {missions.map(m => {
          const done = completedMissions.has(m.id);
          return (
            <div key={m.id} className={`mission-card${done ? ' done' : ''}`}>
              <div className={`m-ic ${done ? 'm-ic-green' : m.ic}`}>{done ? '✓' : '→'}</div>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>{m.title}</div>
              <div style={{ fontSize: 10, color: C.ink3, lineHeight: 1.5, marginBottom: 6 }}>{m.desc}</div>
              <div style={{ fontSize: 9, fontWeight: 700, color: done ? C.green : C.ink3 }}>
                {done ? 'COMPLETED' : m.id === 'diversify' ? `${holdings.length}/3 sectors` : 'In progress'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
