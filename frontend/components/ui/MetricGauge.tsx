import { METRICS, metricStatus } from '@/lib/metrics';
import type { MetricKey } from '@/lib/types';
import { STATUS_FILL } from './StatusBadge';

/**
 * A ruler for one metric: the hatched band is the sector's ideal range, the
 * marker is this stock's value. Values off the scale are pinned to the edge.
 */
export function MetricGauge({
  metric,
  value,
  sector,
  size = 'md',
}: {
  metric: MetricKey;
  value: number | null;
  sector: string;
  size?: 'sm' | 'md';
}) {
  const spec = METRICS[metric];
  const [min, max] = spec.scale;
  const pos = (v: number) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
  const ideal = spec.ideal(sector);
  const status = metricStatus(metric, value, sector);
  const track = size === 'sm' ? 'h-1.5' : 'h-2';

  return (
    <div className="w-full">
      <div className={`relative ${track} rounded-full bg-rule-2`}>
        {ideal && (
          <div
            className="ideal-band absolute inset-y-0 rounded-full"
            style={{ left: `${pos(ideal[0])}%`, right: `${100 - pos(ideal[1])}%` }}
          />
        )}
        {value != null && (
          <div
            className={`absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface ${STATUS_FILL[status]} shadow-[0_0_0_1px_rgb(20_23_31/0.15)]`}
            style={{ left: `${pos(value)}%` }}
            aria-hidden
          />
        )}
      </div>
      {size === 'md' && (
        <div className="num mt-1.5 flex justify-between text-[0.7333rem] text-ink-3">
          <span>{min}{spec.unit}</span>
          <span>{max}{spec.unit}{max < 100 ? '+' : ''}</span>
        </div>
      )}
    </div>
  );
}
