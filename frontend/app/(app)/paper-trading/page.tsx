import type { Metadata } from 'next';
import { PaperTrading } from '@/components/paper/PaperTrading';
import { getStocks } from '@/lib/data/queries';
import type { Instrument } from '@/lib/paperTrading';

export const metadata: Metadata = { title: 'Paper trading' };

/** Liquid, well-known stocks to practise with. */
const SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ITC', 'SBIN', 'TMPV', 'ETERNAL', 'HAL', 'BAJFINANCE', 'ASIANPAINT'];

export default async function PaperTradingPage() {
  const stocks = await getStocks(SYMBOLS);
  const instruments: Instrument[] = stocks
    .filter((s) => s.price != null)
    .map((s) => ({
      symbol: s.symbol,
      name: s.name,
      price: s.price!,
      changePct: s.changePct,
      // Rough daily volatility: young tech platforms swing more than blue chips.
      volatility: s.sector === 'newage' ? 0.028 : s.sector === 'defence' ? 0.022 : 0.016,
    }));

  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Paper trading</h1>
        <p className="mt-1 text-ink-2">
          Practise with ₹1,00,000 of pretend money at today’s real prices, then step through simulated days to see how stop-losses and position sizes play out.
        </p>
      </header>
      <PaperTrading instruments={instruments} />
    </div>
  );
}
