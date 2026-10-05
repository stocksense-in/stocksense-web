import type { Metadata } from 'next';
import Link from 'next/link';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { change } from '@/lib/format';
import { EXPOSURE_LABEL, GEO_EVENTS, PRECEDENTS, SECTOR_EXPOSURE, type Exposure } from '@/lib/content/geopolitics';
import type { Status } from '@/lib/types';

export const metadata: Metadata = { title: 'Geopolitics' };

const TONE: Record<Exposure, Status> = { risk: 'concern', opportunity: 'healthy', haven: 'watch', low: 'neutral' };

/** Screener link for the sectors this page talks about, where we have a matching code. */
const SCREENER_SECTOR: Record<string, string> = {
  'Oil & Gas': 'energy',
  'Defence & Aerospace': 'defence',
  Banking: 'bank',
  Pharma: 'pharma',
  'IT Services': 'it',
  FMCG: 'fmcg',
};

export default function GeopoliticsPage() {
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Geopolitics</h1>
        <p className="mt-1 text-ink-2">
          Global events move Indian sectors before they show up in company results. This map shows which sectors current events push, and how far.
        </p>
      </header>

      <section className="panel overflow-hidden" aria-labelledby="exposure-heading">
        <div className="border-b border-rule px-5 py-4">
          <h2 id="exposure-heading" className="panel-title">Sector exposure</h2>
          <p className="text-sm text-ink-3">Bar length is how strongly today’s events move the sector, in either direction.</p>
        </div>
        <ul className="divide-y divide-rule-2">
          {SECTOR_EXPOSURE.map((s) => {
            const code = SCREENER_SECTOR[s.sector];
            return (
              <li key={s.sector} className="grid items-center gap-x-6 gap-y-2 px-5 py-3.5 md:grid-cols-[12rem_minmax(0,1fr)_8rem]">
                <div>
                  {code ? (
                    <Link href={`/screener?sector=${code}`} className="font-medium text-ink hover:text-brand">{s.sector}</Link>
                  ) : (
                    <span className="font-medium text-ink">{s.sector}</span>
                  )}
                  <p className="text-[0.8rem] text-ink-3 md:hidden">{s.note}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="relative h-2 flex-1 rounded-full bg-rule-2" role="img" aria-label={`Sensitivity ${s.sensitivity} out of 100`}>
                    <span className="absolute inset-y-0 left-0 rounded-full bg-ink" style={{ width: `${s.sensitivity}%` }} />
                  </span>
                  <span className="num w-8 text-right text-sm text-ink">{s.sensitivity}</span>
                  <span className="hidden flex-[1.4] text-sm text-ink-2 md:block">{s.note}</span>
                </div>
                <div className="md:text-right">
                  <StatusBadge status={TONE[s.exposure]}>{EXPOSURE_LABEL[s.exposure]}</StatusBadge>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section className="panel p-5" aria-labelledby="events-heading">
          <h2 id="events-heading" className="panel-title">What’s happening</h2>
          <ul className="mt-2 divide-y divide-rule-2">
            {GEO_EVENTS.map((e) => (
              <li key={e.title} className="py-3">
                <p className="text-[0.8rem] text-ink-3">{e.topic}</p>
                <p className="leading-snug text-ink">{e.title}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel overflow-hidden" aria-labelledby="history-heading">
          <div className="px-5 pt-4 pb-3">
            <h2 id="history-heading" className="panel-title">When it happened before</h2>
            <p className="text-sm text-ink-3">How the market reacted to similar shocks.</p>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Sector moves</th>
                <th className="r">NIFTY</th>
              </tr>
            </thead>
            <tbody>
              {PRECEDENTS.map((p) => (
                <tr key={p.event}>
                  <td>
                    <div className="font-medium text-ink">{p.event}</div>
                    <div className="text-[0.8rem] text-ink-3">Lasted {p.lasted}</div>
                  </td>
                  <td className="text-sm text-ink-2">{p.sectors}</td>
                  <td className={`r num ${p.nifty < 0 ? 'text-down' : 'text-up'}`}>{change(p.nifty, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <p className="text-[0.8rem] text-ink-3">Event list and sensitivities are curated sample data; a live news feed is planned.</p>
    </div>
  );
}
