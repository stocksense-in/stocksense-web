import assert from 'node:assert/strict';
import { test } from 'node:test';
import { STARTING_CASH, charges, initialState, portfolioValue, reducer, type Instrument } from '../lib/paperTrading.ts';

const INFY: Instrument = { symbol: 'INFY', name: 'Infosys', price: 1000, changePct: -1.2, volatility: 0.02 };
const TCS: Instrument = { symbol: 'TCS', name: 'TCS', price: 2000, changePct: 0.5, volatility: 0.02 };
const ITC: Instrument = { symbol: 'ITC', name: 'ITC', price: 400, changePct: 0.1, volatility: 0.02 };

test('buying moves cash into a position and charges fees', () => {
  const s = reducer(initialState, { type: 'buy', instrument: INFY, qty: 10, stopLossPct: 7 });
  assert.equal(s.positions.length, 1);
  assert.equal(s.cash, STARTING_CASH - 10_000 - charges(10_000));
  assert.equal(s.positions[0].stopLoss, 930);
  assert.ok(s.missions.includes('first-trade'));
  assert.ok(s.missions.includes('stop-loss-set'));
  assert.ok(s.missions.includes('buy-red-day'), 'INFY is down today');
});

test('an order larger than cash is refused', () => {
  const s = reducer(initialState, { type: 'buy', instrument: TCS, qty: 1000, stopLossPct: 5 });
  assert.equal(s, initialState);
});

test('a stop-loss sells automatically on the next day', () => {
  let s = reducer(initialState, { type: 'buy', instrument: INFY, qty: 10, stopLossPct: 1 });
  s = reducer(s, { type: 'next-day', instruments: [INFY], random: () => 0 }); // worst move: −0.96 × 2 × 2% ≈ −1.9%
  assert.equal(s.positions.length, 0);
  assert.equal(s.trades.at(-1)?.reason, 'stop-loss');
  assert.ok(s.missions.includes('stop-loss-hit'));
});

test('holding three stocks completes the diversification mission', () => {
  let s = initialState;
  for (const inst of [INFY, TCS, ITC]) s = reducer(s, { type: 'buy', instrument: inst, qty: 1, stopLossPct: 5 });
  assert.ok(s.missions.includes('diversify'));
});

test('selling returns the market value minus charges', () => {
  let s = reducer(initialState, { type: 'buy', instrument: ITC, qty: 10, stopLossPct: 5 });
  s = reducer(s, { type: 'sell', symbol: 'ITC' });
  assert.equal(s.positions.length, 0);
  assert.equal(Math.round(portfolioValue(s)), Math.round(STARTING_CASH - 2 * charges(4000)));
});
