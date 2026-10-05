import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { PriceChart } from '@/components/charts/PriceChart';
import { RangeBar } from '@/components/stock/RangeBar';
import { ReportCard } from '@/components/stock/ReportCard';
import { ScoreBreakdown } from '@/components/stock/ScoreBreakdown';
import { Change } from '@/components/ui/Change';
import { ScoreMeter } from '@/components/ui/ScoreMeter';
import { getPriceHistory } from '@/lib/data/chart';
import { getStock } from '@/lib/data/queries';
import { ago, capBand, crore, inr, pct } from '@/lib/format';
import { sectorLabel } from '@/lib/sectors';

export async function generateMetadata(props: PageProps<'/stocks/[symbol]'>): Promise<Metadata> {
  const { symbol } = await props.params;
  const stock = await getStock(decodeURIComponent(symbol));
  return { title: stock ? `${stock.name} (${stock.symbol})` : 'Stock not found' };
}

export default async function StockPage(props: PageProps<'/stocks/[symbol]'>) {
  const { symbol } = await props.params;
  const stock = await getStock(decodeURIComponent(symbol));
  if (!stock) notFound();
  const history = await getPriceHistory(stock.symbol, '1y');

  const facts = [
    { label: 'Market cap', value: crore(stock.marketCap), note: capBand(stock.marketCap) },
    { label: 'Price to book', value: stock.pb != null ? `${stock.pb.toFixed(2)}×` : '—' },
    { label: 'Dividend yield', value: pct(stock.dividendYield, 2) },
    { label: 'Industry', value: stock.industry ?? sectorLabel(stock.sector) },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-md border border-rule bg-surface px-2 py-0.5 font-medium text-ink">{stock.symbol}</span>
            <Link href={`/screener?sector=${stock.sector}`} className="text-ink-2 hover:text-brand">
              {sectorLabel(stock.sector)}
            </Link>
          </div>
          <h1 className="mt-2 font-display text-[2rem] leading-tight font-semibold tracking-[-0.02em] text-ink sm:text-[2.4rem]">
            {stock.name}
          </h1>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="num text-[1.6rem] font-medium text-ink">{inr(stock.price)}</span>
            <Change value={stock.changePct} className="text-base" />
            <span className="text-sm text-ink-3">today</span>
          </div>
        </div>
        <RangeBar low={stock.week52Low} high={stock.week52High} price={stock.price} />
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <section className="panel p-5" aria-labelledby="price-heading">
          <h2 id="price-heading" className="sr-only">Price history</h2>
          <PriceChart symbol={stock.symbol} initial={history} />
        </section>

        <section className="panel p-5" aria-labelledby="score-heading">
          <h2 id="score-heading" className="panel-title mb-4">StockSense score</h2>
          <ScoreMeter score={stock.score} />
          <div className="mt-6 border-t border-rule-2 pt-5">
            <h3 className="mb-3 text-sm font-medium text-ink-2">How it adds up</h3>
            <ScoreBreakdown stock={stock} />
          </div>
        </section>
      </div>

      <section className="panel overflow-hidden" aria-labelledby="report-heading">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule px-5 py-4">
          <div>
            <h2 id="report-heading" className="panel-title">Fundamentals against {sectorLabel(stock.sector)} norms</h2>
            <p className="mt-0.5 text-sm text-ink-3">The hatched band on each ruler is the healthy range for this sector. Select a row for the full explanation.</p>
          </div>
          <span className="text-[0.8rem] text-ink-3">Updated {ago(stock.updatedAt)}</span>
        </div>
        <ReportCard stock={stock} />
      </section>

      <section aria-label="Key facts" className="grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-rule bg-rule md:grid-cols-4">
        {facts.map((f) => (
          <div key={f.label} className="bg-surface px-5 py-4">
            <div className="text-[0.8rem] text-ink-3">{f.label}</div>
            <div className="num mt-1 truncate font-medium text-ink">{f.value}</div>
            {f.note && <div className="text-[0.8rem] text-ink-3">{f.note}</div>}
          </div>
        ))}
      </section>

      <p className="text-[0.8rem] text-ink-3">
        Data from Yahoo Finance and NSE, refreshed daily. For learning only — not investment advice. StockSense is not a SEBI-registered investment adviser.
      </p>
    </div>
  );
}
