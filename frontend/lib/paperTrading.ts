/**
 * Paper-trading simulator: all state changes in one pure reducer, so the rules
 * are easy to read and test. The UI lives in components/paper/PaperTrading.tsx.
 */

export const STARTING_CASH = 100_000;
export const BROKERAGE = 20; // ₹ per order, like a discount broker
export const STT_RATE = 0.001; // securities transaction tax on delivery trades, both sides

export interface Instrument {
  symbol: string;
  name: string;
  price: number;
  changePct: number | null;
  /** Typical daily move as a fraction, used to simulate the next day. */
  volatility: number;
}

export interface Position {
  symbol: string;
  qty: number;
  avgCost: number;
  price: number;
  stopLoss: number; // ₹ price that triggers an automatic exit
  daysHeld: number;
  history: number[]; // closing prices since bought, newest last
}

export interface Trade {
  day: number;
  side: 'buy' | 'sell';
  symbol: string;
  qty: number;
  price: number;
  reason?: 'stop-loss';
}

export type MissionId = 'first-trade' | 'stop-loss-set' | 'diversify' | 'buy-red-day' | 'stop-loss-hit' | 'hold-red' | 'green-week';

export interface State {
  cash: number;
  day: number;
  positions: Position[];
  trades: Trade[];
  missions: MissionId[];
  prices: Record<string, number>;
  /** Each stock's % move on the latest simulated day. */
  moves: Record<string, number>;
}

export type Action =
  | { type: 'buy'; instrument: Instrument; qty: number; stopLossPct: number }
  | { type: 'sell'; symbol: string }
  | { type: 'next-day'; instruments: Instrument[]; random?: () => number }
  | { type: 'restore'; state: State }
  | { type: 'reset' };

export const MISSIONS: { id: MissionId; title: string; how: string }[] = [
  { id: 'first-trade', title: 'Place your first trade', how: 'Buy any stock.' },
  { id: 'stop-loss-set', title: 'Protect a position', how: 'Buy with a stop-loss of 10% or less.' },
  { id: 'buy-red-day', title: 'Buy on a red day', how: 'Buy a stock that is down today.' },
  { id: 'diversify', title: 'Spread your risk', how: 'Hold three different stocks at once.' },
  { id: 'hold-red', title: 'Sit through a loss', how: 'Keep a losing position for three days.' },
  { id: 'stop-loss-hit', title: 'See a stop-loss work', how: 'Let a stop-loss exit a falling stock.' },
  { id: 'green-week', title: 'Finish a green week', how: 'After 5 trading days, be worth more than ₹1,00,000.' },
];

export const initialState: State = {
  cash: STARTING_CASH,
  day: 0,
  positions: [],
  trades: [],
  missions: [],
  prices: {},
  moves: {},
};

export function charges(value: number): number {
  return BROKERAGE + value * STT_RATE;
}

export function portfolioValue(state: State): number {
  return state.cash + state.positions.reduce((sum, p) => sum + p.qty * p.price, 0);
}

const complete = (missions: MissionId[], ...ids: MissionId[]) => [...new Set([...missions, ...ids])];

/** Can this order go through? Returns a reason when it can't. */
export function checkBuy(state: State, instrument: Instrument, qty: number): string | null {
  if (!Number.isInteger(qty) || qty < 1) return 'Enter a quantity of at least 1.';
  const price = state.prices[instrument.symbol] ?? instrument.price;
  const total = price * qty + charges(price * qty);
  if (total > state.cash) return `Not enough cash — this order needs ₹${Math.ceil(total).toLocaleString('en-IN')}.`;
  return null;
}

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'buy': {
      const { instrument, qty, stopLossPct } = action;
      if (checkBuy(state, instrument, qty)) return state;
      const price = state.prices[instrument.symbol] ?? instrument.price;
      const value = price * qty;
      const existing = state.positions.find((p) => p.symbol === instrument.symbol);
      const stopLoss = price * (1 - stopLossPct / 100);
      const positions = existing
        ? state.positions.map((p) =>
            p.symbol === instrument.symbol
              ? { ...p, qty: p.qty + qty, avgCost: (p.avgCost * p.qty + value) / (p.qty + qty), stopLoss }
              : p,
          )
        : [...state.positions, { symbol: instrument.symbol, qty, avgCost: price, price, stopLoss, daysHeld: 0, history: [price] }];

      const earned: MissionId[] = ['first-trade'];
      if (stopLossPct > 0 && stopLossPct <= 10) earned.push('stop-loss-set');
      const todaysMove = state.day === 0 ? instrument.changePct : state.moves[instrument.symbol];
      if ((todaysMove ?? 0) < 0) earned.push('buy-red-day');
      if (positions.length >= 3) earned.push('diversify');

      return {
        ...state,
        cash: state.cash - value - charges(value),
        positions,
        trades: [...state.trades, { day: state.day, side: 'buy', symbol: instrument.symbol, qty, price }],
        missions: complete(state.missions, ...earned),
      };
    }

    case 'sell': {
      const position = state.positions.find((p) => p.symbol === action.symbol);
      if (!position) return state;
      const value = position.qty * position.price;
      return {
        ...state,
        cash: state.cash + value - charges(value),
        positions: state.positions.filter((p) => p.symbol !== action.symbol),
        trades: [...state.trades, { day: state.day, side: 'sell', symbol: position.symbol, qty: position.qty, price: position.price }],
      };
    }

    case 'next-day': {
      const random = action.random ?? Math.random;
      const day = state.day + 1;
      const prices = { ...state.prices };
      const moves: Record<string, number> = {};
      for (const inst of action.instruments) {
        const last = prices[inst.symbol] ?? inst.price;
        // Random walk with a slight upward drift, scaled by the stock's volatility.
        const move = (random() - 0.48) * 2 * inst.volatility;
        prices[inst.symbol] = Math.max(1, Math.round(last * (1 + move) * 100) / 100);
        moves[inst.symbol] = ((prices[inst.symbol] - last) / last) * 100;
      }

      let cash = state.cash;
      const trades = [...state.trades];
      const earned: MissionId[] = [];
      const positions: Position[] = [];
      for (const p of state.positions) {
        const price = prices[p.symbol] ?? p.price;
        if (price <= p.stopLoss) {
          const value = p.qty * price;
          cash += value - charges(value);
          trades.push({ day, side: 'sell', symbol: p.symbol, qty: p.qty, price, reason: 'stop-loss' });
          earned.push('stop-loss-hit');
          continue;
        }
        const next = { ...p, price, daysHeld: p.daysHeld + 1, history: [...p.history, price].slice(-30) };
        if (next.daysHeld >= 3 && price < p.avgCost) earned.push('hold-red');
        positions.push(next);
      }

      const next = { ...state, day, prices, moves, cash, positions, trades };
      if (day >= 5 && portfolioValue(next) > STARTING_CASH) earned.push('green-week');
      return { ...next, missions: complete(state.missions, ...earned) };
    }

    case 'restore':
      return action.state;

    case 'reset':
      return initialState;
  }
}

/** One plain-language suggestion about the current portfolio, or null. */
export function coachNote(state: State): string | null {
  const invested = state.positions.reduce((sum, p) => sum + p.qty * p.price, 0);
  if (state.positions.length === 0) return null;
  for (const p of state.positions) {
    const weight = (p.qty * p.price) / (invested + state.cash);
    if (weight > 0.3) return `${p.symbol} is ${Math.round(weight * 100)}% of your portfolio. One bad result could hurt a lot — consider spreading it out.`;
  }
  for (const p of state.positions) {
    const gain = (p.price - p.avgCost) / p.avgCost;
    if (gain > 0.12) return `${p.symbol} is up ${(gain * 100).toFixed(1)}%. Many investors book some profit at this point and raise their stop-loss.`;
  }
  if (state.cash / (invested + state.cash) > 0.8) return 'Most of your money is still in cash. That’s fine while you learn — try a small position first.';
  return null;
}
