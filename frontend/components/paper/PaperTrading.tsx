'use client';

import { useEffect, useReducer, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import { Change } from '@/components/ui/Change';
import { inr } from '@/lib/format';
import {
  MISSIONS,
  STARTING_CASH,
  charges,
  checkBuy,
  coachNote,
  initialState,
  portfolioValue,
  reducer,
  type Instrument,
  type State,
} from '@/lib/paperTrading';

const STORAGE_KEY = 'stocksense.paper.v1';

function Sparkline({ values, up }: { values: number[]; up: boolean }) {
  if (values.length < 2) return <span className="inline-block h-5 w-16" />;
  const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${(i / (values.length - 1)) * 64},${18 - ((v - lo) / span) * 16}`).join('');
  return (
    <svg width="64" height="20" viewBox="0 0 64 20" aria-hidden>
      <path d={d} fill="none" stroke={up ? 'var(--color-up)' : 'var(--color-down)'} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export function PaperTrading({ instruments }: { instruments: Instrument[] }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const loaded = useRef(false);
  const [symbol, setSymbol] = useState(instruments[0]?.symbol ?? '');
  const [qty, setQty] = useState(5);
  const [stopLossPct, setStopLossPct] = useState(7);
  const [message, setMessage] = useState<string | null>(null);
  const lastTrades = useRef(0);

  // Restore the saved portfolio after mount (localStorage isn't available on the server).
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) dispatch({ type: 'restore', state: { ...initialState, ...JSON.parse(saved) } as State });
    } catch {
      /* corrupt save — start fresh */
    }
    loaded.current = true;
  }, []);

  // Save after every change (skipped until the saved portfolio has been read).
  useEffect(() => {
    if (loaded.current) localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  // Announce stop-loss exits that happened during "next day".
  useEffect(() => {
    const fresh = state.trades.slice(lastTrades.current);
    lastTrades.current = state.trades.length;
    const stopped = fresh.filter((t) => t.reason === 'stop-loss');
    if (stopped.length) setMessage(`Stop-loss sold ${stopped.map((t) => `${t.symbol} at ${inr(t.price)}`).join(', ')}.`);
  }, [state.trades]);

  const instrument = instruments.find((i) => i.symbol === symbol);
  const price = instrument ? state.prices[instrument.symbol] ?? instrument.price : 0;
  const orderValue = price * (Number.isFinite(qty) ? qty : 0);
  const problem = instrument ? checkBuy(state, instrument, qty) : 'Pick a stock.';
  const total = portfolioValue(state);
  const invested = state.positions.reduce((s, p) => s + p.qty * p.avgCost, 0);
  const marketValue = state.positions.reduce((s, p) => s + p.qty * p.price, 0);
  const pnl = marketValue - invested;
  const overall = ((total - STARTING_CASH) / STARTING_CASH) * 100;
  const note = coachNote(state);

  const buy = () => {
    if (!instrument || problem) return;
    dispatch({ type: 'buy', instrument, qty, stopLossPct });
    setMessage(`Bought ${qty} ${instrument.symbol} at ${inr(price)}. Stop-loss set at ${inr(price * (1 - stopLossPct / 100))}.`);
  };

  return (
    <div className="space-y-6">
      <section aria-label="Portfolio summary" className="grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-rule bg-rule lg:grid-cols-4">
        {[
          { label: 'Portfolio value', value: inr(total, 0), sub: <Change value={overall} /> },
          { label: 'Cash', value: inr(state.cash, 0), sub: <span className="text-ink-3">ready to invest</span> },
          { label: 'Invested', value: inr(invested, 0), sub: <span className="text-ink-3">{state.positions.length} {state.positions.length === 1 ? "position" : "positions"}</span> },
          {
            label: 'Unrealised gain',
            value: `${pnl >= 0 ? '+' : '−'}${inr(Math.abs(pnl), 0)}`,
            sub: <Change value={invested ? (pnl / invested) * 100 : 0} />,
          },
        ].map((t) => (
          <div key={t.label} className="bg-surface px-5 py-4">
            <div className="text-[0.8rem] text-ink-3">{t.label}</div>
            <div className="num mt-1 font-display text-[1.5rem] font-semibold text-ink">{t.value}</div>
            <div className="text-sm">{t.sub}</div>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <section className="panel h-fit p-5" aria-labelledby="order-heading">
          <h2 id="order-heading" className="panel-title mb-4">Place an order</h2>
          <div className="space-y-4">
            <label className="block">
              <span className="label">Stock</span>
              <select className="field" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                {instruments.map((i) => (
                  <option key={i.symbol} value={i.symbol}>
                    {i.symbol} — {inr(state.prices[i.symbol] ?? i.price)}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="label">Quantity</span>
                <input className="field num" type="number" min={1} step={1} value={qty} onChange={(e) => setQty(Math.floor(Number(e.target.value)))} />
              </label>
              <label className="block">
                <span className="label">Stop-loss</span>
                <div className="relative">
                  <input className="field num pr-8" type="number" min={1} max={30} value={stopLossPct} onChange={(e) => setStopLossPct(Number(e.target.value))} />
                  <span className="absolute top-1/2 right-3 -translate-y-1/2 text-sm text-ink-3">%</span>
                </div>
              </label>
            </div>
            <dl className="num space-y-1.5 rounded-lg bg-sunken px-4 py-3 text-sm">
              <div className="flex justify-between"><dt className="text-ink-2">Order value</dt><dd className="text-ink">{inr(orderValue)}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-2">Brokerage + STT</dt><dd className="text-ink">{inr(charges(orderValue))}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-2">Sells automatically below</dt><dd className="text-ink">{inr(price * (1 - stopLossPct / 100))}</dd></div>
            </dl>
            {problem && qty > 0 && <p className="text-sm text-down">{problem}</p>}
            <button className="btn btn-primary w-full" onClick={buy} disabled={!!problem}>
              Buy {Number.isFinite(qty) && qty > 0 ? qty : ''} {symbol}
            </button>
          </div>
        </section>

        <section className="panel overflow-hidden" aria-labelledby="holdings-heading">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4 pb-3">
            <div>
              <h2 id="holdings-heading" className="panel-title">Holdings</h2>
              <p className="text-sm text-ink-3">{state.day === 0 ? 'Market day 1 — real closing prices.' : `Simulated day ${state.day + 1}.`}</p>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary btn-sm" onClick={() => dispatch({ type: 'next-day', instruments })}>
                Simulate next day
              </button>
              <button
                className="btn btn-quiet btn-sm"
                onClick={() => {
                  if (confirm('Start over with ₹1,00,000? Your simulated trades will be cleared.')) {
                    dispatch({ type: 'reset' });
                    setMessage('Portfolio reset to ₹1,00,000.');
                  }
                }}
              >
                Start over
              </button>
            </div>
          </div>
          {state.positions.length === 0 ? (
            <p className="border-t border-rule-2 px-5 py-10 text-center text-sm text-ink-2">
              No positions yet. Place an order to start — nothing here uses real money.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table min-w-[40rem]">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th className="r">Qty</th>
                    <th className="r">Avg cost</th>
                    <th className="r">Price</th>
                    <th className="r">Gain</th>
                    <th className="r">Stop-loss</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {state.positions.map((p) => {
                    const gain = (p.price - p.avgCost) * p.qty;
                    return (
                      <tr key={p.symbol}>
                        <td>
                          <div className="flex items-center gap-3">
                            <span className="font-medium text-ink">{p.symbol}</span>
                            <Sparkline values={p.history} up={p.price >= p.avgCost} />
                          </div>
                        </td>
                        <td className="r num">{p.qty}</td>
                        <td className="r num">{inr(p.avgCost)}</td>
                        <td className="r num text-ink">{inr(p.price)}</td>
                        <td className="r">
                          <div className={`num ${gain >= 0 ? 'text-up' : 'text-down'}`}>{gain >= 0 ? '+' : '−'}{inr(Math.abs(gain), 0)}</div>
                          <Change value={((p.price - p.avgCost) / p.avgCost) * 100} className="text-[0.8rem]" />
                        </td>
                        <td className="r num text-ink-2">{inr(p.stopLoss)}</td>
                        <td className="r">
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              dispatch({ type: 'sell', symbol: p.symbol });
                              setMessage(`Sold ${p.qty} ${p.symbol} at ${inr(p.price)}.`);
                            }}
                          >
                            Sell
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {note && <p className="border-t border-rule-2 bg-brand-wash/50 px-5 py-3 text-sm text-brand-ink">{note}</p>}
        </section>
      </div>

      <p role="status" aria-live="polite" className={`text-sm text-ink-2 ${message ? '' : 'sr-only'}`}>
        {message}
      </p>

      <section className="panel p-5" aria-labelledby="missions-heading">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 id="missions-heading" className="panel-title">Learning missions</h2>
          <span className="num text-sm text-ink-3">{state.missions.length} of {MISSIONS.length} done</span>
        </div>
        <ol className="grid gap-x-8 sm:grid-cols-2">
          {MISSIONS.map((m) => {
            const done = state.missions.includes(m.id);
            return (
              <li key={m.id} className="flex items-start gap-3 border-t border-rule-2 py-3">
                <span
                  className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${done ? 'border-up bg-up text-paper' : 'border-rule text-transparent'}`}
                  aria-hidden
                >
                  <Check className="size-3" strokeWidth={3} />
                </span>
                <div>
                  <div className={done ? 'text-ink-3 line-through decoration-ink-3/50' : 'text-ink'}>{m.title}</div>
                  <div className="text-[0.8rem] text-ink-3">{m.how}</div>
                </div>
                <span className="sr-only">{done ? 'Completed' : 'Not yet'}</span>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
