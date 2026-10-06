import { verdict } from '@/lib/scoring';

const TONE = {
  healthy: { stroke: '#22D39A', glow: 'drop-shadow(0 0 6px rgb(34 211 154 / 0.6))' },
  watch: { stroke: '#FFB648', glow: 'drop-shadow(0 0 6px rgb(255 182 72 / 0.55))' },
  concern: { stroke: '#FF5D73', glow: 'drop-shadow(0 0 6px rgb(255 93 115 / 0.6))' },
};

/** The 0–100 score as a glowing ring: mint when strong (65+), amber when fair, coral when weak. */
export function ScoreRing({ score, size = 76 }: { score: number | null; size?: number }) {
  const v = verdict(score);
  const tone = TONE[v?.tone ?? 'concern'];
  const r = 15.9155; // circumference = 100, so dasharray is the score itself
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }} role="img" aria-label={`Score ${score ?? 'not available'} out of 100${v ? `, ${v.label}` : ''}`}>
      <svg viewBox="0 0 36 36" className="absolute inset-0 size-full -rotate-90">
        <circle cx="18" cy="18" r={r} fill="none" stroke="var(--color-raised)" strokeWidth="3" />
        {score != null && (
          <circle cx="18" cy="18" r={r} fill="none" stroke={tone.stroke} strokeWidth="3" strokeLinecap="round" strokeDasharray={`${score} 100`} style={{ filter: tone.glow }} />
        )}
      </svg>
      <span className="num text-xl font-semibold text-ink">{score ?? '—'}</span>
    </div>
  );
}
