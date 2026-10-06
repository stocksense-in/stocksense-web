import type { Metadata } from 'next';
import Link from 'next/link';
import { AutoSubmitForm } from '@/components/ui/AutoSubmitForm';
import { Change } from '@/components/ui/Change';
import { ScoreMeter } from '@/components/ui/ScoreMeter';
import { SCREENER_PAGE_SIZE, screen, type ScreenerFilters, type SortKey } from '@/lib/data/queries';
import { crore, inr } from '@/lib/format';
import { SECTOR_LABELS, SECTOR_OPTIONS, sectorLabel } from '@/lib/sectors';
import type { SectorCode } from '@/lib/types';

export const metadata: Metadata = { title: 'Screener' };

type Params = Record<string, string | string[] | undefined>;

const SORTS: SortKey[] = ['score', 'marketCap', 'changePct', 'pe', 'roe', 'de', 'name'];

function parse(params: Params): ScreenerFilters {
  const one = (k: string) => (typeof params[k] === 'string' ? (params[k] as string) : undefined);
  const number = (k: string) => {
    const v = one(k);
    return v && !Number.isNaN(Number(v)) ? Number(v) : undefined;
  };
  const sector = one('sector');
  const cap = one('cap');
  const sort = one('sort') as SortKey | undefined;
  return {
    sector: sector && sector in SECTOR_LABELS ? (sector as SectorCode) : undefined,
    cap: cap === 'large' || cap === 'mid' || cap === 'small' ? cap : undefined,
    minScore: number('minScore'),
    maxPe: number('maxPe'),
    minRoe: number('minRoe'),
    maxDe: number('maxDe'),
    sort: sort && SORTS.includes(sort) ? sort : undefined,
    dir: one('dir') === 'asc' ? 'asc' : one('dir') === 'desc' ? 'desc' : undefined,
    page: number('page'),
  };
}

function Select({ name, label, value, options }: { name: string; label: string; value?: string | number; options: [string, string][] }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <select name={name} defaultValue={value ?? ''} className="field">
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </label>
  );
}

export default async function ScreenerPage(props: PageProps<'/screener'>) {
  const params = await props.searchParams;
  const f = parse(params);
  const { rows, total, universe } = await screen(f);
  const page = Math.max(1, f.page ?? 1);
  const pages = Math.max(1, Math.ceil(total / SCREENER_PAGE_SIZE));
  const activeSort = f.sort ?? 'score';

  /** URL for the current filters with some values replaced. */
  const href = (changes: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (typeof v === 'string' && v) q.set(k, v);
    for (const [k, v] of Object.entries(changes)) {
      if (v == null || v === '') q.delete(k);
      else q.set(k, String(v));
    }
    const s = q.toString();
    return s ? `/screener?${s}` : '/screener';
  };

  const defaultDir = (key: SortKey) => (key === 'pe' || key === 'de' || key === 'name' ? 'asc' : 'desc');
  const sortHeader = (key: SortKey, label: string, align: 'left' | 'right' = 'right') => {
    const active = activeSort === key;
    const current = f.dir ?? defaultDir(key);
    const next = active ? (current === 'asc' ? 'desc' : 'asc') : defaultDir(key);
    return (
      <th className={align === 'right' ? 'r' : ''} aria-sort={active ? (current === 'asc' ? 'ascending' : 'descending') : undefined}>
        <Link href={href({ sort: key, dir: next, page: undefined })} className={`hover:text-ink ${active ? 'text-ink' : ''}`}>
          {label}
          {active && <span aria-hidden> {current === 'asc' ? '↑' : '↓'}</span>}
        </Link>
      </th>
    );
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Screener</h1>
        <p className="text-ink-2">
          Filter all {universe.toLocaleString('en-IN')} NSE stocks by fundamentals. Filters apply as you change them.
        </p>
      </header>

      <AutoSubmitForm className="panel grid gap-4 p-5 sm:grid-cols-3 xl:grid-cols-6">
        <Select name="sector" label="Sector" value={f.sector} options={[['', 'All sectors'], ...SECTOR_OPTIONS.map((s) => [s, SECTOR_LABELS[s]] as [string, string])]} />
        <Select name="cap" label="Size" value={f.cap} options={[['', 'Any size'], ['large', 'Large cap (₹1 L Cr+)'], ['mid', 'Mid cap'], ['small', 'Small cap (< ₹30,000 Cr)']]} />
        <Select name="minScore" label="Score" value={f.minScore} options={[['', 'Any score'], ['65', 'Strong (65+)'], ['45', 'Fair or better (45+)']]} />
        <Select name="maxPe" label="P/E" value={f.maxPe} options={[['', 'Any P/E'], ['15', 'Under 15×'], ['25', 'Under 25×'], ['40', 'Under 40×']]} />
        <Select name="minRoe" label="ROE" value={f.minRoe} options={[['', 'Any ROE'], ['12', 'Above 12%'], ['15', 'Above 15%'], ['20', 'Above 20%']]} />
        <Select name="maxDe" label="Debt/equity" value={f.maxDe} options={[['', 'Any debt'], ['0.3', 'Under 0.3×'], ['0.8', 'Under 0.8×'], ['1.5', 'Under 1.5×']]} />
        {f.sort && <input type="hidden" name="sort" value={f.sort} />}
        {f.dir && <input type="hidden" name="dir" value={f.dir} />}
        <div className="flex items-center gap-3 sm:col-span-3 xl:col-span-6">
          <noscript>
            <button className="btn btn-primary btn-sm">Apply filters</button>
          </noscript>
          <p className="num text-sm text-ink-2">
            {total.toLocaleString('en-IN')} {total === 1 ? 'stock matches' : 'stocks match'}
          </p>
          {Object.values(params).some(Boolean) && (
            <Link href="/screener" className="text-sm text-brand hover:text-brand-ink">Clear filters</Link>
          )}
        </div>
      </AutoSubmitForm>

      <section className="panel overflow-x-auto">
        {rows.length === 0 ? (
          <div className="px-6 py-14 text-center">
            <p className="font-medium text-ink">No stocks pass all these filters.</p>
            <p className="mt-1 text-sm text-ink-2">Loosen one filter, such as P/E or debt, to see more.</p>
          </div>
        ) : (
          <table className="data-table min-w-[56rem]">
            <thead>
              <tr>
                {sortHeader('name', 'Company', 'left')}
                <th>Sector</th>
                <th className="r">Price</th>
                {sortHeader('changePct', 'Today')}
                {sortHeader('marketCap', 'Market cap')}
                {sortHeader('pe', 'P/E')}
                {sortHeader('roe', 'ROE')}
                {sortHeader('de', 'Debt/eq.')}
                {sortHeader('score', 'Score')}
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.symbol} className="relative">
                  <td className="max-w-[16rem]">
                    <Link href={`/stocks/${encodeURIComponent(s.symbol)}`} className="block after:absolute after:inset-0">
                      <span className="font-medium text-ink">{s.symbol}</span>
                      <span className="block truncate text-[0.8rem] text-ink-3">{s.name}</span>
                    </Link>
                  </td>
                  <td className="text-ink-2">{sectorLabel(s.sector)}</td>
                  <td className="r num text-ink">{inr(s.price)}</td>
                  <td className="r"><Change value={s.changePct} pill /></td>
                  <td className="r num text-ink-2">{crore(s.marketCap)}</td>
                  <td className="r num">{s.pe != null && s.pe > 0 ? `${s.pe.toFixed(1)}×` : '—'}</td>
                  <td className="r num">{s.roe != null ? `${s.roe.toFixed(1)}%` : '—'}</td>
                  <td className="r num">{s.de != null ? `${s.de.toFixed(2)}×` : '—'}</td>
                  <td className="r"><ScoreMeter score={s.score} compact /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {pages > 1 && (
        <nav className="flex items-center justify-between text-sm" aria-label="Pages">
          <span className="text-ink-3">Page {page} of {pages}</span>
          <div className="flex gap-2">
            {page > 1 && <Link className="btn btn-secondary btn-sm" href={href({ page: page - 1 })}>Previous</Link>}
            {page < pages && <Link className="btn btn-secondary btn-sm" href={href({ page: page + 1 })}>Next</Link>}
          </div>
        </nav>
      )}
    </div>
  );
}
