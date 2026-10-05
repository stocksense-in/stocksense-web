'use client';

import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MetricGauge } from '@/components/ui/MetricGauge';
import { METRIC_CONTENT } from '@/lib/metricContent';
import { METRIC_INTEL } from '@/lib/metricIntel';
import { METRICS, STATUS_LABEL, formatMetric, idealLabel, metricStatus } from '@/lib/metrics';
import { sectorLabel } from '@/lib/sectors';
import type { MetricKey } from '@/lib/types';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-rule-2 pt-5">
      <h3 className="mb-2 font-display text-[1rem] font-semibold text-ink">{title}</h3>
      <div className="space-y-2 text-[0.9333rem] leading-relaxed text-ink-2">{children}</div>
    </section>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5 marker:text-ink-3">
      {items.map((t) => (
        <li key={t}>{t}</li>
      ))}
    </ul>
  );
}

/** Side panel explaining one metric in depth, for this stock and its sector. */
export function MetricSheet({
  metric,
  value,
  sector,
  companyName,
  onClose,
}: {
  metric: MetricKey;
  value: number | null;
  sector: string;
  companyName: string;
  onClose: () => void;
}) {
  const spec = METRICS[metric];
  const intel = METRIC_INTEL[metric];
  const content = METRIC_CONTENT[metric];
  const status = metricStatus(metric, value, sector);
  const peers = intel.sectorAvg(sector);
  const action = value != null ? intel.action(value, sector) : null;
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="metric-sheet-title">
      <div className="absolute inset-0 bg-ink/25 [animation:fade-in_150ms]" onClick={onClose} />
      <div className="absolute inset-y-0 right-0 flex w-full max-w-xl flex-col bg-surface shadow-sheet [animation:sheet-in_200ms_ease-out]">
        <header className="flex items-start gap-4 border-b border-rule px-6 py-5">
          <div className="min-w-0 flex-1">
            <p className="text-sm text-ink-3">{companyName}</p>
            <h2 id="metric-sheet-title" className="font-display text-[1.5rem] font-semibold tracking-tight text-ink">
              {spec.label}
            </h2>
          </div>
          <button ref={closeRef} className="btn btn-quiet btn-sm" onClick={onClose} aria-label="Close">
            <X className="size-5" />
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="num font-display text-[2.2rem] leading-none font-semibold text-ink">
                {formatMetric(metric, value)}
              </span>
              <StatusBadge status={status}>{STATUS_LABEL[status]}</StatusBadge>
            </div>
            <MetricGauge metric={metric} value={value} sector={sector} />
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-ink-3">Ideal for {sectorLabel(sector)}</dt>
                <dd className="num mt-0.5 font-medium text-ink">{idealLabel(metric, sector)}</dd>
              </div>
              <div>
                <dt className="text-ink-3">{peers.label} average</dt>
                <dd className="num mt-0.5 font-medium text-ink">{peers.avg}</dd>
              </div>
              <div>
                <dt className="text-ink-3">Top quartile</dt>
                <dd className="num mt-0.5 font-medium text-ink">{peers.top}</dd>
              </div>
            </dl>
            {value != null && <p className="text-[0.9333rem] text-ink-2">{spec.reading(value, sector)}</p>}
            {!spec.ideal(sector) && spec.notApplicable && (
              <p className="rounded-lg bg-sunken px-4 py-3 text-sm text-ink-2">{spec.notApplicable(sector)}</p>
            )}
          </div>

          <Section title="What it measures">
            <p>{intel.definition}</p>
          </Section>

          {action && (
            <Section title="What this reading suggests">
              <p className="font-medium text-ink">{action.label}</p>
              <p>{action.text}</p>
            </Section>
          )}

          <Section title="Why it matters">
            <p>{content.medium.why}</p>
          </Section>

          <Section title="How it moves the share price">
            <p>{content.medium.priceImpact}</p>
          </Section>

          <Section title={`In ${sectorLabel(sector)}`}>
            <p>{intel.rangeLogic(sector)}</p>
          </Section>

          <Section title="What drives it">
            <dl className="space-y-2.5">
              {intel.drivers.map((d) => (
                <div key={d.label}>
                  <dt className="font-medium text-ink">{d.label}</dt>
                  <dd>{d.desc}</dd>
                </div>
              ))}
            </dl>
          </Section>

          <Section title="Risks to watch">
            <Bullets items={content.medium.risks} />
          </Section>

          <Section title="Signals that mislead">
            <Bullets items={content.full.fakeSignals} />
          </Section>

          <p className="border-t border-rule-2 pt-5 text-[0.8rem] text-ink-3">
            Educational explanation, not a recommendation. StockSense is not a SEBI-registered investment adviser.
          </p>
        </div>
      </div>
    </div>
  );
}
