import { Change } from '@/components/ui/Change';
import { getIndices, getLastUpdated } from '@/lib/data/queries';
import { usingSnapshot } from '@/lib/data/source';
import { ago, num } from '@/lib/format';

/** NIFTY, SENSEX, BANK NIFTY, VIX across the top of every app page. */
export async function IndexBar() {
  const [indices, updated] = await Promise.all([getIndices(), getLastUpdated()]);
  return (
    <div className="flex items-center gap-6 overflow-x-auto text-sm [scrollbar-width:none]">
      {indices.map((q) => (
        <div key={q.symbol} className="flex shrink-0 items-baseline gap-2">
          <span className="text-ink-3">{q.label}</span>
          <span className="num font-medium text-ink">{num(q.price)}</span>
          <Change value={q.changePct} className="text-[0.8667rem]" />
        </div>
      ))}
      <span className="ml-auto shrink-0 text-[0.8rem] text-ink-3">
        {usingSnapshot ? 'Offline snapshot' : `Prices ${ago(updated)}`}
      </span>
    </div>
  );
}
