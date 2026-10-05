import { verdict } from '@/lib/scoring';

/**
 * The StockSense score on a 0–100 ruler with the two band edges (45, 65) marked,
 * so the number always reads in context: weak | fair | strong.
 */
export function ScoreMeter({ score, compact = false }: { score: number | null; compact?: boolean }) {
  const v = verdict(score);
  const fill = v?.tone === 'healthy' ? 'bg-up' : v?.tone === 'watch' ? 'bg-watch' : 'bg-down';

  if (compact) {
    return (
      <span className="inline-flex items-center gap-2">
        <span className="num w-6 text-right font-medium text-ink">{score ?? '—'}</span>
        <span className="relative h-1.5 w-14 rounded-full bg-rule-2" aria-hidden>
          {score != null && <span className={`absolute inset-y-0 left-0 rounded-full ${fill}`} style={{ width: `${score}%` }} />}
        </span>
      </span>
    );
  }

  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="num font-display text-[2.6rem] leading-none font-semibold tracking-tight text-ink">
          {score ?? '—'}
        </span>
        <span className="text-sm text-ink-3">/ 100</span>
        {v && <span className="ml-auto text-sm font-medium text-ink-2">{v.label}</span>}
      </div>
      <div className="relative mt-3 h-2 rounded-full bg-rule-2">
        {score != null && <div className={`absolute inset-y-0 left-0 rounded-full ${fill}`} style={{ width: `${score}%` }} />}
        {[45, 65].map((edge) => (
          <span key={edge} className="absolute -top-1 -bottom-1 w-0.5 bg-surface" style={{ left: `${edge}%` }} aria-hidden />
        ))}
      </div>
      <div className="mt-1.5 grid grid-cols-[45fr_20fr_35fr] text-[0.7333rem] text-ink-3">
        <span>Weak</span>
        <span>Fair</span>
        <span>Strong</span>
      </div>
    </div>
  );
}
