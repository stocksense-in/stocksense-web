import { METRICS } from '@/lib/metrics';
import { scoreBreakdown } from '@/lib/scoring';
import type { Stock } from '@/lib/types';

/**
 * How the score adds up: each metric can earn up to its weight in points
 * (P/E up to 20, ROE up to 20, …). Earned points sum to the score.
 */
export function ScoreBreakdown({ stock }: { stock: Stock }) {
  const parts = scoreBreakdown(stock);
  const missing = 6 - parts.length;

  return (
    <div>
      <ul className="space-y-2.5">
        {parts.map(({ metric, score, weight }) => {
          const max = weight * 100;
          const earned = (score / 100) * max;
          return (
            <li key={metric} className="grid grid-cols-[minmax(0,1fr)_5.5rem_4.5rem] items-center gap-3 text-sm">
              <span className="truncate text-ink-2">{METRICS[metric].short}</span>
              <span className="relative h-1.5 rounded-full bg-raised" aria-hidden>
                <span className="absolute inset-y-0 left-0 rounded-full bar-brand" style={{ width: `${score}%` }} />
              </span>
              <span className="num text-right text-ink">
                {earned.toFixed(1)} <span className="text-ink-3">/ {max.toFixed(0)}</span>
              </span>
            </li>
          );
        })}
      </ul>
      {missing > 0 && (
        <p className="mt-3 text-[0.8rem] text-ink-3">
          {missing} metric{missing > 1 ? 's' : ''} not published for this company, so the other weights were scaled up.
        </p>
      )}
    </div>
  );
}
