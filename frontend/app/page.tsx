import type { Metadata } from 'next';
import Link from 'next/link';
import { HeroReportCard } from '@/components/landing/HeroReportCard';
import { Logo } from '@/components/shell/Logo';
import { getStocks } from '@/lib/data/queries';
import { METRICS, METRIC_ORDER } from '@/lib/metrics';
import { WEIGHTS } from '@/lib/scoring';

export const metadata: Metadata = { title: { absolute: 'StockSense — Know what you’re buying' } };

const EXAMPLES = ['TCS', 'HDFCBANK', 'ETERNAL', 'TMPV', 'ITC'];

const WHY: Record<string, string> = {
  pe: 'What you pay for each rupee of profit.',
  roe: 'How well the company uses shareholders’ money.',
  margin: 'How much of each sale it keeps as profit.',
  de: 'How much it relies on borrowed money.',
  cagr: 'How fast sales have grown over three years.',
  promoter: 'How much the founders still own.',
};

const TOOLS = [
  { href: '/screener', title: 'Screener', body: 'Filter all 2,600 NSE stocks by score, valuation, returns and debt.' },
  { href: '/ipo', title: 'IPO scores', body: 'Fundamentals, institutional demand and grey-market premium, weighed into one verdict.' },
  { href: '/geopolitics', title: 'Geopolitics', body: 'Which Indian sectors today’s global events push up or drag down.' },
  { href: '/paper-trading', title: 'Paper trading', body: '₹1,00,000 of pretend money at real prices, with stop-losses and missions.' },
  { href: '/rhp-analyser', title: 'Prospectus scanner', body: 'The risk factors buried in a 400-page IPO prospectus, pulled out and ranked.' },
];

export default async function Landing() {
  const examples = (await getStocks(EXAMPLES)).filter((s) => s.score != null);
  const order = [...METRIC_ORDER].sort((a, b) => WEIGHTS[b] - WEIGHTS[a]);

  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex h-16 max-w-[1200px] items-center gap-8 px-5 sm:px-8">
        <Link href="/" aria-label="StockSense home"><Logo /></Link>
        <nav className="hidden gap-6 text-[0.9333rem] text-ink-2 md:flex" aria-label="Product">
          <Link href="/stocks" className="hover:text-ink">Stocks</Link>
          <Link href="/screener" className="hover:text-ink">Screener</Link>
          <Link href="/ipo" className="hover:text-ink">IPOs</Link>
          <Link href="/paper-trading" className="hover:text-ink">Paper trading</Link>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Link href="/login" className="btn btn-quiet btn-sm">Sign in</Link>
          <Link href="/dashboard" className="btn btn-primary btn-sm">Open StockSense</Link>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-[1200px] items-center gap-12 px-5 pt-10 pb-20 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)] lg:pt-20">
          <div>
            <h1 className="font-display text-[2.75rem] leading-[1.02] font-semibold tracking-[-0.035em] text-ink sm:text-[4rem] lg:text-[4.6rem]">
              Know what you’re buying.
            </h1>
            <p className="mt-6 max-w-[34rem] text-[1.1333rem] leading-relaxed text-ink-2">
              StockSense checks every NSE-listed company against six fundamentals, judged by what’s healthy for its own sector, and explains each one in plain words.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/stocks" className="btn btn-primary h-11 px-5">Look up a stock</Link>
              <Link href="/paper-trading" className="btn btn-secondary h-11 px-5">Practise with ₹1,00,000</Link>
            </div>
            <p className="mt-5 text-sm text-ink-3">Free, no account needed. For learning, not advice.</p>
          </div>
          {examples.length > 0 && <HeroReportCard stocks={examples} />}
        </section>

        <section className="border-y border-rule bg-surface">
          <div className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8">
            <h2 className="max-w-xl font-display text-[2rem] leading-tight font-semibold tracking-[-0.02em] text-ink">
              A score you can take apart.
            </h2>
            <p className="mt-3 max-w-2xl text-ink-2">
              Every stock gets up to 100 points. Here is where they come from. Missing data never counts against a company; the other weights scale up instead.
            </p>

            <div className="mt-10 flex h-11 gap-0.5 overflow-hidden rounded-lg" role="img" aria-label="Score weights: P/E 20, ROE 20, net margin 20, debt to equity 15, revenue growth 15, promoter holding 10">
              {order.map((key, i) => (
                <div
                  key={key}
                  className="flex items-center px-3 text-sm font-medium text-white"
                  style={{ flexGrow: WEIGHTS[key], backgroundColor: `color-mix(in oklab, var(--color-ink) ${100 - i * 11}%, var(--color-brand))` }}
                >
                  <span className="truncate">{METRICS[key].short} <span className="num opacity-70">{WEIGHTS[key] * 100}</span></span>
                </div>
              ))}
            </div>

            <dl className="mt-8 grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
              {order.map((key) => (
                <div key={key}>
                  <dt className="flex items-baseline gap-2">
                    <span className="font-medium text-ink">{METRICS[key].label}</span>
                    <span className="num text-sm text-ink-3">{WEIGHTS[key] * 100} pts</span>
                  </dt>
                  <dd className="mt-1 text-[0.9333rem] text-ink-2">{WHY[key]}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="mx-auto grid max-w-[1200px] gap-12 px-5 py-20 sm:px-8 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-[2rem] leading-tight font-semibold tracking-[-0.02em] text-ink">Judged by its own sector.</h2>
            <p className="mt-3 max-w-lg text-ink-2">
              Debt of twice its equity is a warning sign for a software company and an ordinary day for a bank, which borrows in order to lend. StockSense knows the difference, so a healthy bank isn’t marked down for being a bank.
            </p>
          </div>
          <div className="panel grid gap-6 p-6">
            {[
              { who: 'IT company', verdict: 'Concern', tone: 'bg-down', ideal: [0, 27], note: 'Healthy range: below 0.8×' },
              { who: 'Bank', verdict: 'Expected', tone: 'bg-ink-3', ideal: null, note: 'Judged on asset quality and margins instead' },
            ].map((row) => (
              <div key={row.who}>
                <div className="mb-2 flex items-baseline justify-between text-sm">
                  <span className="font-medium text-ink">{row.who} with debt/equity of 2.0×</span>
                  <span className="text-ink-2">{row.verdict}</span>
                </div>
                <div className="relative h-2 rounded-full bg-rule-2">
                  {row.ideal && <span className="ideal-band absolute inset-y-0 rounded-full" style={{ left: `${row.ideal[0]}%`, width: `${row.ideal[1]}%` }} />}
                  <span className={`absolute top-1/2 left-[66%] size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface ${row.tone}`} />
                </div>
                <p className="mt-1.5 text-[0.8rem] text-ink-3">{row.note}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-5 pb-24 sm:px-8">
          <h2 className="font-display text-[2rem] leading-tight font-semibold tracking-[-0.02em] text-ink">The rest of the toolkit</h2>
          <ul className="mt-6 divide-y divide-rule border-y border-rule">
            {TOOLS.map((t) => (
              <li key={t.href}>
                <Link href={t.href} className="group grid gap-1 py-5 sm:grid-cols-[14rem_minmax(0,1fr)] sm:items-baseline">
                  <span className="font-display text-[1.2rem] font-semibold text-ink group-hover:text-brand">{t.title}</span>
                  <span className="text-ink-2">{t.body}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-start justify-between gap-6 px-5 py-8 text-sm text-ink-3 sm:px-8">
          <Logo />
          <p className="max-w-xl">
            Market data from NSE and Yahoo Finance, refreshed daily. StockSense is an educational tool and is not registered with SEBI as an investment adviser. Nothing here is a recommendation to buy or sell.
          </p>
        </div>
      </footer>
    </div>
  );
}
