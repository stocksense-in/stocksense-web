import type { Metadata } from 'next';
import Link from 'next/link';
import { PriceChart } from '@/components/charts/PriceChart';
import { SectorBento } from '@/components/charts/SectorBento';
import { Change } from '@/components/ui/Change';
import { ScoreRing } from '@/components/ui/ScoreRing';
import { StockTable } from '@/components/ui/StockTable';
import { getPriceHistory } from '@/lib/data/chart';
import { getBreadth, getIndices, getMovers, getSectorMoves, getTopScored } from '@/lib/data/queries';
import { GEO_EVENTS, type GeoEvent } from '@/lib/content/geopolitics';
import { num } from '@/lib/format';

export const metadata: Metadata = { title: 'Dashboard' };

/** Colour of each geopolitics topic chip. */
const TOPIC_TONE: Record<GeoEvent['topic'], string> = {
  Conflict: 'text-down bg-down-wash',
  Oil: 'text-down bg-down-wash',
  Defence: 'text-up bg-up-wash',
  Commodities: 'text-watch bg-watch-wash',
  Trade: 'text-info bg-info/12',
  Agriculture: 'text-violet bg-violet/12',
};

function marketStatus(now = new Date()) {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const minutes = ist.getHours() * 60 + ist.getMinutes();
  const weekday = ist.getDay() >= 1 && ist.getDay() <= 5;
  const open = weekday && minutes >= 9 * 60 + 15 && minutes <= 15 * 60 + 30;
  const date = ist.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
  return { open, date };
}

export default async function DashboardPage() {
  const [indices, intraday, sectors, breadth, movers, top] = await Promise.all([
    getIndices(),
    getPriceHistory('NIFTY50', '1d'),
    getSectorMoves(),
    getBreadth(),
    getMovers(5),
    getTopScored(8),
  ]);
  const { open, date } = marketStatus();
  const nifty = indices.find((q) => q.symbol === 'NIFTY50');
  const others = indices.filter((q) => q.symbol !== 'NIFTY50');
  const points = nifty?.changePct != null ? nifty.price - nifty.price / (1 + nifty.changePct / 100) : null;
  const total = breadth.advancers + breadth.decliners + breadth.unchanged || 1;

  return (
    <div className="space-y-6">
      {/* Hero: NIFTY in large type with today's chart, the other indices, and market breadth. */}
      <section className="panel panel-aurora overflow-hidden" aria-labelledby="hero-heading">
        <div className="grid gap-8 p-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:p-8">
          <div>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 id="hero-heading" className="font-display text-[1.6rem] font-semibold tracking-tight text-ink">Market today</h1>
              <span className="text-[0.8rem] text-ink-3">{date}</span>
            </div>
            <div className="mt-6 text-sm text-ink-2">NIFTY 50</div>
            <div className="mt-1 flex flex-wrap items-baseline gap-3">
              <span className="num text-[2.75rem] leading-none font-semibold tracking-tight text-ink sm:text-[3.6rem]">
                {nifty ? num(nifty.price) : '—'}
              </span>
              {nifty?.changePct != null && (
                <span className={`num rounded-full px-2.5 py-1 text-sm font-medium ${nifty.changePct >= 0 ? 'bg-up-wash text-up' : 'bg-down-wash text-down'}`}>
                  {points != null && `${points >= 0 ? '+' : '−'}${num(Math.abs(points))} `}
                  ({nifty.changePct >= 0 ? '+' : '−'}{Math.abs(nifty.changePct).toFixed(2)}%)
                </span>
              )}
            </div>
            <dl className="mt-8 grid grid-cols-3 gap-4 border-t border-rule pt-5">
              {others.map((q) => (
                <div key={q.symbol}>
                  <dt className="text-[0.8rem] text-ink-3">{q.label}</dt>
                  <dd className="num mt-1 font-medium text-ink">{num(q.price)}</dd>
                  {/* For VIX a rise means more fear, so it reads as a warning. */}
                  <dd className="text-[0.8667rem]">
                    {q.symbol === 'INDIAVIX' ? (
                      <span className={`num ${(q.changePct ?? 0) > 0 ? 'text-down' : 'text-up'}`}>
                        {(q.changePct ?? 0) >= 0 ? '+' : '−'}{Math.abs(q.changePct ?? 0).toFixed(2)}%
                      </span>
                    ) : (
                      <Change value={q.changePct} />
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <PriceChart symbol="NIFTY50" initial={intraday} initialRange="1d" ranges={['1d', '1mo', '1y']} height={200} bare title="NIFTY 50, latest session" />
        </div>

        <div className="border-t border-rule bg-sunken/40 px-6 py-5 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-sm font-medium text-ink">Market breadth</h2>
              <p className="text-[0.8rem] text-ink-3">{open ? 'NSE open until 3:30 pm' : 'NSE closed, showing the last session'}</p>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2">
              <div><span className="num text-[1.75rem] font-semibold text-up">{breadth.advancers.toLocaleString('en-IN')}</span> <span className="text-sm text-ink-3">rose</span></div>
              <div><span className="num text-[1.75rem] font-semibold text-ink-2">{breadth.unchanged.toLocaleString('en-IN')}</span> <span className="text-sm text-ink-3">unchanged</span></div>
              <div><span className="num text-[1.75rem] font-semibold text-down">{breadth.decliners.toLocaleString('en-IN')}</span> <span className="text-sm text-ink-3">fell</span></div>
            </div>
          </div>
          <div className="mt-4 flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={`${breadth.advancers} stocks rose and ${breadth.decliners} fell`}>
            <span className="rounded-l-full bg-up shadow-[0_0_12px_rgb(34_211_154/0.6)]" style={{ width: `${(breadth.advancers / total) * 100}%` }} />
            <span className="bg-raised" style={{ width: `${(breadth.unchanged / total) * 100}%` }} />
            <span className="rounded-r-full bg-down shadow-[0_0_12px_rgb(255_93_115/0.5)]" style={{ width: `${(breadth.decliners / total) * 100}%` }} />
          </div>
        </div>
      </section>

      {/* Sector bento, with gainers and fallers beside it. */}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <section className="panel p-5" aria-labelledby="sectors-heading">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="sectors-heading" className="panel-title">Sectors</h2>
            <span className="text-[0.8rem] text-ink-3">Brighter tile, bigger move</span>
          </div>
          <p className="mb-4 text-sm text-ink-3">Day change weighted by market cap. Select a sector to screen it.</p>
          {sectors.length ? <SectorBento sectors={sectors} /> : <p className="text-sm text-ink-3">No sector data yet. Run the fundamentals job in backend/.</p>}
        </section>

        <div className="grid content-start gap-6">
          <section className="panel edge-up overflow-hidden" aria-labelledby="gainers-heading">
            <h2 id="gainers-heading" className="panel-title px-5 pt-4 pb-3">Biggest gainers</h2>
            <StockTable stocks={movers.gainers} empty="No stock worth over ₹10,000 Cr rose today." />
          </section>
          <section className="panel edge-down overflow-hidden" aria-labelledby="losers-heading">
            <h2 id="losers-heading" className="panel-title px-5 pt-4 pb-3">Biggest fallers</h2>
            <StockTable stocks={movers.losers} empty="No stock worth over ₹10,000 Cr fell today." />
          </section>
        </div>
      </div>

      <section aria-labelledby="top-heading">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 id="top-heading" className="font-display text-[1.2rem] font-semibold text-ink">Strongest fundamentals</h2>
          <Link href="/screener?sort=score&cap=large" className="text-sm text-brand hover:text-brand-ink">Open in screener</Link>
        </div>
        {top.length === 0 ? (
          <p className="panel px-5 py-6 text-sm text-ink-3">No scored stocks yet. Run the fundamentals job in backend/.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {top.map((s) => (
              <li key={s.symbol}>
                <Link href={`/stocks/${encodeURIComponent(s.symbol)}`} className="panel flex h-full flex-col items-center p-4 text-center transition-colors hover:bg-sunken">
                  <span className="font-medium text-ink">{s.symbol}</span>
                  <span className="mb-4 w-full truncate text-[0.75rem] text-ink-3">{s.name}</span>
                  <ScoreRing score={s.score} />
                  <Change value={s.changePct} className="mt-3 text-[0.8rem]" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="geo-heading">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 id="geo-heading" className="font-display text-[1.2rem] font-semibold text-ink">Geopolitical watch</h2>
          <Link href="/geopolitics" className="text-sm text-brand hover:text-brand-ink">See sector risk map</Link>
        </div>
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {GEO_EVENTS.slice(0, 4).map((e) => (
            <li key={e.title}>
              <Link href="/geopolitics" className="panel flex h-full flex-col p-4 transition-colors hover:bg-sunken">
                <span className={`mb-2 self-start rounded px-2 py-1 text-[0.7333rem] font-medium ${TOPIC_TONE[e.topic]}`}>{e.topic}</span>
                <p className="mb-3 leading-snug font-medium text-ink">{e.title}</p>
                <p className="mt-auto text-[0.8rem] text-ink-3">Moves {e.affects.join(', ')}</p>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
