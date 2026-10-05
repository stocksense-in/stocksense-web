import type { Metadata } from 'next';
import Link from 'next/link';
import { SectorBars } from '@/components/charts/SectorBars';
import { StockTable } from '@/components/ui/StockTable';
import { getBreadth, getMovers, getSectorMoves, getTopScored } from '@/lib/data/queries';
import { GEO_EVENTS } from '@/lib/content/geopolitics';

export const metadata: Metadata = { title: 'Dashboard' };

function marketStatus(now = new Date()) {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const minutes = ist.getHours() * 60 + ist.getMinutes();
  const weekday = ist.getDay() >= 1 && ist.getDay() <= 5;
  const open = weekday && minutes >= 9 * 60 + 15 && minutes <= 15 * 60 + 30;
  const date = ist.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
  return { open, date };
}

export default async function DashboardPage() {
  const [sectors, breadth, movers, top] = await Promise.all([
    getSectorMoves(),
    getBreadth(),
    getMovers(5),
    getTopScored(8),
  ]);
  const { open, date } = marketStatus();
  const total = breadth.advancers + breadth.decliners + breadth.unchanged || 1;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-ink-3">{date}</p>
          <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Market today</h1>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-rule bg-surface px-3 py-1 text-sm text-ink-2">
          <span className={`size-2 rounded-full ${open ? 'bg-up' : 'bg-ink-3'}`} aria-hidden />
          NSE {open ? 'open until 3:30 pm' : 'closed — showing last session'}
        </span>
      </header>

      <section className="panel p-5" aria-labelledby="breadth-heading">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="breadth-heading" className="panel-title">Breadth</h2>
          <p className="num flex gap-4 text-sm">
            <span className="text-up">{breadth.advancers.toLocaleString('en-IN')} rose</span>
            <span className="text-down">{breadth.decliners.toLocaleString('en-IN')} fell</span>
            {breadth.unchanged > 0 && <span className="text-ink-3">{breadth.unchanged} unchanged</span>}
          </p>
        </div>
        <div className="mt-3 flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={`${breadth.advancers} stocks rose and ${breadth.decliners} fell`}>
          <span className="bg-up" style={{ width: `${(breadth.advancers / total) * 100}%` }} />
          <span className="bg-rule" style={{ width: `${(breadth.unchanged / total) * 100}%` }} />
          <span className="bg-down" style={{ width: `${(breadth.decliners / total) * 100}%` }} />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <section className="panel p-5" aria-labelledby="sectors-heading">
          <h2 id="sectors-heading" className="panel-title">Sectors</h2>
          <p className="mb-4 text-sm text-ink-3">Day change weighted by market cap. Select a sector to screen it.</p>
          {sectors.length ? <SectorBars sectors={sectors} /> : <p className="text-sm text-ink-3">No sector data yet. Run the fundamentals job in backend/.</p>}
        </section>

        <div className="grid gap-6">
          <section className="panel overflow-hidden" aria-labelledby="gainers-heading">
            <h2 id="gainers-heading" className="panel-title px-5 pt-4 pb-3">Biggest gainers</h2>
            <StockTable stocks={movers.gainers} empty="No stock worth over ₹10,000 Cr rose today." />
          </section>
          <section className="panel overflow-hidden" aria-labelledby="losers-heading">
            <h2 id="losers-heading" className="panel-title px-5 pt-4 pb-3">Biggest fallers</h2>
            <StockTable stocks={movers.losers} empty="No stock worth over ₹10,000 Cr fell today." />
          </section>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <section className="panel overflow-hidden" aria-labelledby="top-heading">
          <div className="flex items-baseline justify-between px-5 pt-4 pb-3">
            <h2 id="top-heading" className="panel-title">Strongest fundamentals</h2>
            <Link href="/screener?sort=score&cap=large" className="text-sm text-brand hover:text-brand-ink">
              Open in screener
            </Link>
          </div>
          <StockTable stocks={top} showScore empty="No scored stocks yet. Run the fundamentals job in backend/." />
        </section>

        <section className="panel flex flex-col p-5" aria-labelledby="geo-heading">
          <h2 id="geo-heading" className="panel-title">Geopolitical watch</h2>
          <ul className="mt-2 mb-5 divide-y divide-rule-2">
            {GEO_EVENTS.slice(0, 4).map((e) => (
              <li key={e.title} className="py-3">
                <p className="leading-snug text-ink">{e.title}</p>
                <p className="mt-1 text-[0.8rem] text-ink-3">Moves {e.affects.join(', ')}</p>
              </li>
            ))}
          </ul>
          <Link href="/geopolitics" className="btn btn-secondary btn-sm mt-auto self-start">
            See sector risk map
          </Link>
        </section>
      </div>
    </div>
  );
}
