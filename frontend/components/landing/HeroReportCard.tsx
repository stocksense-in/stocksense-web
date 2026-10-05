'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Change } from '@/components/ui/Change';
import { STATUS_FILL } from '@/components/ui/StatusBadge';
import { inr } from '@/lib/format';
import { METRICS, METRIC_ORDER, STATUS_LABEL, formatMetric, metricStatus } from '@/lib/metrics';
import { verdict } from '@/lib/scoring';
import { sectorLabel } from '@/lib/sectors';
import type { Stock } from '@/lib/types';

/**
 * The landing page's centrepiece: a real report card you can flip between
 * companies. Markers slide to their positions once on load and again on
 * every switch — the one piece of motion on the page.
 */
export function HeroReportCard({ stocks }: { stocks: Stock[] }) {
  const [index, setIndex] = useState(0);
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    const t = requestAnimationFrame(() => setSettled(true));
    return () => cancelAnimationFrame(t);
  }, []);

  const stock = stocks[index];
  if (!stock) return null;
  const v = verdict(stock.score);

  return (
    <div className="panel overflow-hidden shadow-pop">
      <div className="flex gap-1 overflow-x-auto border-b border-rule bg-sunken p-1.5" role="tablist" aria-label="Example companies">
        {stocks.map((s, i) => (
          <button
            key={s.symbol}
            role="tab"
            aria-selected={i === index}
            onClick={() => setIndex(i)}
            className={`h-8 shrink-0 rounded-md px-3 text-sm font-medium transition-colors ${i === index ? 'bg-surface text-ink shadow-[0_0_0_1px_var(--color-rule)]' : 'text-ink-3 hover:text-ink'}`}
          >
            {s.symbol}
          </button>
        ))}
      </div>

      <div className="p-5 sm:p-6" role="tabpanel">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="truncate font-display text-[1.25rem] font-semibold tracking-tight text-ink">{stock.name}</div>
            <div className="mt-0.5 flex items-baseline gap-2 text-sm">
              <span className="num text-ink">{inr(stock.price)}</span>
              <Change value={stock.changePct} />
              <span className="text-ink-3">{sectorLabel(stock.sector)}</span>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="num font-display text-[2rem] leading-none font-semibold text-ink">{stock.score ?? '—'}</div>
            <div className="text-[0.8rem] text-ink-3">{v ? `${v.label}, of 100` : 'of 100'}</div>
          </div>
        </div>

        <ul className="mt-5 space-y-3.5">
          {METRIC_ORDER.map((key) => {
            const spec = METRICS[key];
            const value = stock[key];
            const status = metricStatus(key, value, stock.sector);
            const [min, max] = spec.scale;
            const pos = (x: number) => Math.max(0, Math.min(100, ((x - min) / (max - min)) * 100));
            const ideal = spec.ideal(stock.sector);
            return (
              <li key={key} className="grid grid-cols-[7.5rem_minmax(0,1fr)_4.25rem] items-center gap-3 text-sm sm:grid-cols-[9rem_minmax(0,1fr)_4.5rem]">
                <span className="truncate text-ink-2">{spec.short}</span>
                <span className="relative h-2 rounded-full bg-rule-2">
                  {ideal && (
                    <span
                      className="ideal-band absolute inset-y-0 rounded-full transition-all duration-500"
                      style={{ left: `${pos(ideal[0])}%`, right: `${100 - pos(ideal[1])}%` }}
                    />
                  )}
                  {value != null && (
                    <span
                      className={`absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface shadow-[0_0_0_1px_rgb(20_23_31/0.15)] transition-[left] duration-700 ease-[cubic-bezier(.2,.8,.2,1)] ${STATUS_FILL[status]}`}
                      style={{ left: settled ? `${pos(value)}%` : '0%' }}
                      title={STATUS_LABEL[status]}
                    />
                  )}
                </span>
                <span className="num text-right text-ink">{formatMetric(key, value)}</span>
              </li>
            );
          })}
        </ul>

        <div className="mt-5 flex items-center justify-between gap-3 border-t border-rule-2 pt-4 text-[0.8rem] text-ink-3">
          <span className="flex items-center gap-1.5">
            <span className="ideal-band inline-block h-2 w-5 rounded-full" aria-hidden /> Healthy range for this sector
          </span>
          <Link href={`/stocks/${encodeURIComponent(stock.symbol)}`} className="font-medium text-brand hover:text-brand-ink">
            Full report
          </Link>
        </div>
      </div>
    </div>
  );
}
