import type { Metadata } from 'next';
import Link from 'next/link';
import { cookies } from 'next/headers';
import { Change } from '@/components/ui/Change';
import { ScoreMeter } from '@/components/ui/ScoreMeter';
import { loadStocks } from '@/lib/data/source';
import { inr } from '@/lib/format';
import { HORIZON_LABEL, PROFILE_COOKIE, RISK_COPY, matchStocks, parseProfile } from '@/lib/profile';
import { sectorLabel } from '@/lib/sectors';

export const metadata: Metadata = { title: 'Matched picks' };

export default async function MatchedPicksPage() {
  const profile = parseProfile((await cookies()).get(PROFILE_COOKIE)?.value);

  if (!profile) {
    return (
      <div className="panel mx-auto max-w-xl px-8 py-12 text-center">
        <h1 className="font-display text-2xl font-semibold text-ink">Tell us how you invest first</h1>
        <p className="mt-2 text-ink-2">
          Matched picks filters every scored NSE stock by your budget, risk appetite and favourite sectors. It takes four quick answers.
        </p>
        <Link href="/profile" className="btn btn-primary mt-6">Set up my profile</Link>
      </div>
    );
  }

  const matches = matchStocks(await loadStocks(), profile);
  const summary = [
    RISK_COPY[profile.risk].label,
    HORIZON_LABEL[profile.horizon].toLowerCase(),
    `${inr(profile.capital, 0)} to invest`,
    profile.sectors.length ? profile.sectors.map(sectorLabel).join(', ') : 'any sector',
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Matched picks</h1>
          <p className="mt-1 text-ink-2">Stocks whose fundamentals fit your profile, with the reasons each one made the list.</p>
        </div>
        <Link href="/profile" className="btn btn-secondary btn-sm">Edit profile</Link>
      </header>

      <ul className="flex flex-wrap gap-2" aria-label="Your profile">
        {summary.map((s) => (
          <li key={s} className="rounded-full border border-rule bg-surface px-3 py-1 text-sm text-ink-2">{s}</li>
        ))}
      </ul>

      {matches.length === 0 ? (
        <div className="panel px-8 py-12 text-center">
          <p className="font-medium text-ink">No stock passes every rule for this profile right now.</p>
          <p className="mt-1 text-sm text-ink-2">Try adding sectors, or choose a Balanced risk level.</p>
        </div>
      ) : (
        <ol className="grid overflow-hidden rounded-[10px] border border-rule bg-surface md:grid-cols-2 xl:grid-cols-3">
          {matches.map(({ stock, reasons }, i) => (
            <li key={stock.symbol} className="relative -mr-px -mb-px flex flex-col border-r border-b border-rule p-5 hover:bg-sunken">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <span className="num text-[0.8rem] text-ink-3">#{i + 1}</span>
                  <Link href={`/stocks/${encodeURIComponent(stock.symbol)}`} className="block font-display text-[1.15rem] font-semibold text-ink after:absolute after:inset-0">
                    {stock.name}
                  </Link>
                  <p className="text-sm text-ink-3">{stock.symbol}, {sectorLabel(stock.sector)}</p>
                </div>
                <div className="text-right">
                  <div className="num text-ink">{inr(stock.price)}</div>
                  <Change value={stock.changePct} className="text-sm" />
                </div>
              </div>
              <ul className="mt-4 mb-5 space-y-1 text-sm text-ink-2">
                {reasons.map((r) => (
                  <li key={r} className="flex gap-2"><span className="mt-2 size-1 shrink-0 rounded-full bg-ink-3" aria-hidden />{r}</li>
                ))}
              </ul>
              <div className="mt-auto"><ScoreMeter score={stock.score} compact /></div>
            </li>
          ))}
        </ol>
      )}

      <p className="text-[0.8rem] text-ink-3">
        A starting point for your own research, not a recommendation. StockSense is not a SEBI-registered investment adviser.
      </p>
    </div>
  );
}
