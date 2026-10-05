'use client';

import { useCallback, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { MetricGauge } from '@/components/ui/MetricGauge';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { METRICS, METRIC_ORDER, STATUS_LABEL, formatMetric, idealLabel, metricStatus } from '@/lib/metrics';
import type { MetricKey, Stock } from '@/lib/types';
import { MetricSheet } from './MetricSheet';

/**
 * The six fundamentals as rows of a report card. Each row reads left to right:
 * what it is → the number → where it sits against the sector's ideal → verdict.
 * Clicking a row opens the in-depth explanation.
 */
export function ReportCard({ stock }: { stock: Stock }) {
  const [open, setOpen] = useState<MetricKey | null>(null);
  const close = useCallback(() => setOpen(null), []);

  return (
    <>
      <ul className="divide-y divide-rule-2">
        {METRIC_ORDER.map((key) => {
          const spec = METRICS[key];
          const value = stock[key];
          const status = metricStatus(key, value, stock.sector);
          return (
            <li key={key}>
              <button
                onClick={() => setOpen(key)}
                className="group grid w-full grid-cols-[1fr_auto] items-center gap-x-6 gap-y-3 px-5 py-4 text-left transition-colors hover:bg-sunken md:grid-cols-[minmax(0,15rem)_6rem_minmax(0,1fr)_7rem_1rem]"
              >
                <div className="min-w-0">
                  <div className="font-medium text-ink">{spec.label}</div>
                  <div className="mt-0.5 text-[0.8667rem] text-ink-3">
                    {value != null ? spec.reading(value, stock.sector) : 'Not published for this company.'}
                  </div>
                </div>
                <div className="num text-right font-display text-[1.35rem] font-semibold text-ink md:text-left">
                  {formatMetric(key, value)}
                </div>
                <div className="col-span-2 md:col-span-1">
                  <MetricGauge metric={key} value={value} sector={stock.sector} size="sm" />
                  <div className="num mt-1.5 text-[0.7333rem] text-ink-3">Ideal: {idealLabel(key, stock.sector)}</div>
                </div>
                <div className="hidden md:block">
                  <StatusBadge status={status}>{STATUS_LABEL[status]}</StatusBadge>
                </div>
                <ChevronRight className="hidden size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 md:block" />
              </button>
            </li>
          );
        })}
      </ul>
      {open && (
        <MetricSheet
          metric={open}
          value={stock[open]}
          sector={stock.sector}
          companyName={stock.name}
          onClose={close}
        />
      )}
    </>
  );
}
