import type { Metadata } from 'next';
import Link from 'next/link';
import { StockTable } from '@/components/ui/StockTable';
import { getStocks, screen } from '@/lib/data/queries';
import { SECTOR_LABELS, SECTOR_OPTIONS } from '@/lib/sectors';

export const metadata: Metadata = { title: 'Stocks' };

/** Stocks people look up most when they start out. */
const FAMILIAR = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'SBIN', 'TMPV', 'ETERNAL', 'ASIANPAINT', 'HAL'];

export default async function StocksPage() {
  const [familiar, largest] = await Promise.all([
    getStocks(FAMILIAR),
    screen({ sort: 'marketCap', dir: 'desc' }).then((r) => r.rows.slice(0, 15)),
  ]);

  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Stocks</h1>
        <p className="mt-1 text-ink-2">
          Every NSE-listed company gets a report card: six fundamentals checked against what’s healthy for its sector.
          Search above (press <kbd className="rounded border border-rule bg-surface px-1.5 text-sm">/</kbd>), or start with a familiar name.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="panel overflow-hidden" aria-labelledby="familiar-heading">
          <h2 id="familiar-heading" className="panel-title px-5 pt-4 pb-3">Familiar names</h2>
          <StockTable stocks={familiar} showScore empty="No data yet. Run the fundamentals job in backend/." />
        </section>
        <section className="panel overflow-hidden" aria-labelledby="largest-heading">
          <h2 id="largest-heading" className="panel-title px-5 pt-4 pb-3">Largest by market cap</h2>
          <StockTable stocks={largest} showScore empty="No data yet. Run the fundamentals job in backend/." />
        </section>
      </div>

      <section aria-labelledby="sectors-heading">
        <h2 id="sectors-heading" className="panel-title mb-3">Browse by sector</h2>
        <ul className="flex flex-wrap gap-2">
          {SECTOR_OPTIONS.map((s) => (
            <li key={s}>
              <Link href={`/screener?sector=${s}`} className="btn btn-secondary btn-sm">{SECTOR_LABELS[s]}</Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
