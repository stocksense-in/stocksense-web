import type { Metadata } from 'next';
import Link from 'next/link';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { IPOS, IPO_WEIGHTS, ipoScore, ipoVerdict } from '@/lib/content/ipos';

export const metadata: Metadata = { title: 'IPOs' };

const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export default async function IpoPage(props: PageProps<'/ipo'>) {
  const { ipo: selectedSlug } = await props.searchParams;
  const ipos = IPOS.map((i) => ({ ...i, slug: slug(i.name), score: ipoScore(i) })).sort((a, b) => b.score - a.score);
  const selected = ipos.find((i) => i.slug === selectedSlug) ?? ipos[0];
  const verdict = ipoVerdict(selected.score);

  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">IPOs</h1>
        <p className="mt-1 text-ink-2">
          Each upcoming issue is scored on five signals — what the company is worth, who is buying, and what could go wrong — into one verdict.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <nav aria-label="Upcoming IPOs" className="panel h-fit overflow-hidden">
          <ul className="divide-y divide-rule-2">
            {ipos.map((i) => {
              const v = ipoVerdict(i.score);
              const active = i.slug === selected.slug;
              return (
                <li key={i.slug}>
                  <Link
                    href={`/ipo?ipo=${i.slug}`}
                    scroll={false}
                    aria-current={active ? 'true' : undefined}
                    className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 px-5 py-4 ${active ? 'bg-brand-wash/60 shadow-[inset_3px_0_0_var(--color-brand)]' : 'hover:bg-sunken'}`}
                  >
                    <span className="truncate font-medium text-ink">{i.name}</span>
                    <span className="num row-span-2 font-display text-[1.5rem] font-semibold text-ink">{i.score}</span>
                    <span className="flex items-center gap-2 text-[0.8rem] text-ink-3">
                      <StatusBadge status={v.tone}>{v.label}</StatusBadge>
                      Opens {i.opens}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <article className="panel p-6" aria-labelledby="ipo-title">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-sm text-ink-3">{selected.sector}</p>
              <h2 id="ipo-title" className="font-display text-[1.75rem] font-semibold tracking-tight text-ink">{selected.name}</h2>
              <div className="mt-2"><StatusBadge status={verdict.tone}>{verdict.label}</StatusBadge></div>
            </div>
            <div className="text-right">
              <div className="num font-display text-[2.6rem] leading-none font-semibold text-ink">{selected.score}</div>
              <div className="text-sm text-ink-3">IPO score out of 100</div>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-rule bg-rule">
            {[
              ['Price band', selected.priceBand],
              ['Issue size', selected.issueSize],
              ['Opens', selected.opens],
            ].map(([k, v]) => (
              <div key={k} className="bg-surface px-4 py-3">
                <dt className="text-[0.8rem] text-ink-3">{k}</dt>
                <dd className="num mt-0.5 font-medium text-ink">{v}</dd>
              </div>
            ))}
          </dl>

          <h3 className="mt-8 mb-4 font-display text-[1.0667rem] font-semibold text-ink">How the score adds up</h3>
          <ul className="space-y-5">
            {IPO_WEIGHTS.map((w) => {
              const value = selected.signals[w.key];
              const max = w.weight * 100;
              return (
                <li key={w.key}>
                  <div className="flex items-baseline justify-between gap-4">
                    <div>
                      <span className="text-ink">{w.label}</span>
                      <span className="block text-[0.8rem] text-ink-3">{w.help}</span>
                    </div>
                    <div className="num shrink-0 text-sm text-ink">
                      {((value / 100) * max).toFixed(1)} <span className="text-ink-3">/ {max}</span>
                    </div>
                  </div>
                  <div className="relative mt-2 h-2 rounded-full bg-raised" role="img" aria-label={`${w.label}: ${value} out of 100`}>
                    <span className="absolute inset-y-0 left-0 rounded-full bar-brand" style={{ width: `${value}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>

          <p className="mt-8 border-t border-rule-2 pt-4 text-[0.8rem] text-ink-3">
            Sample data while the IPO feed is being built. 65+ is Subscribe, 50–64 Risky, below 50 Avoid. Not investment advice.
          </p>
        </article>
      </div>
    </div>
  );
}
