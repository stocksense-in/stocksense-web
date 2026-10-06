import { inr } from '@/lib/format';

/** Where today's price sits between the 52-week low and high. */
export function RangeBar({ low, high, price }: { low: number | null; high: number | null; price: number | null }) {
  if (low == null || high == null || price == null || high <= low) return null;
  const pos = Math.max(0, Math.min(100, ((price - low) / (high - low)) * 100));
  return (
    <div className="w-full max-w-xs">
      <div className="mb-1.5 text-[0.8rem] text-ink-3">52-week range</div>
      <div className="relative h-1.5 rounded-full bg-gradient-to-r from-down/50 via-raised to-up/50">
        <span
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-brand shadow-[0_0_10px_rgb(242_181_68/0.6)]"
          style={{ left: `${pos}%` }}
          aria-hidden
        />
      </div>
      <div className="num mt-1.5 flex justify-between text-[0.8rem] text-ink-2">
        <span>{inr(low)}</span>
        <span>{inr(high)}</span>
      </div>
    </div>
  );
}
