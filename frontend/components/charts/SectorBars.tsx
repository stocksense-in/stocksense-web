import Link from 'next/link';
import { change } from '@/lib/format';
import type { SectorMove } from '@/lib/data/queries';
import { sectorLabel } from '@/lib/sectors';

/**
 * Diverging bars around zero: sectors up today extend right in green, down
 * extend left in red. Each row links to that sector in the screener.
 */
export function SectorBars({ sectors }: { sectors: SectorMove[] }) {
  const extent = Math.max(0.5, ...sectors.map((s) => Math.abs(s.changePct)));
  return (
    <ul className="space-y-1">
      {sectors.map((s) => {
        const width = (Math.abs(s.changePct) / extent) * 50;
        const up = s.changePct >= 0;
        return (
          <li key={s.sector}>
            <Link
              href={`/screener?sector=${s.sector}`}
              className="grid grid-cols-[9.5rem_minmax(0,1fr)_4rem] items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-sunken"
              title={`${s.advancers} up, ${s.decliners} down`}
            >
              <span className="truncate text-ink-2">{sectorLabel(s.sector)}</span>
              <span className="relative h-2.5">
                <span className="absolute inset-y-[-3px] left-1/2 w-px bg-rule" aria-hidden />
                <span
                  className={`absolute inset-y-0 ${up ? 'rounded-r-[3px] bg-up' : 'rounded-l-[3px] bg-down'}`}
                  style={up ? { left: '50%', width: `${width}%` } : { right: '50%', width: `${width}%` }}
                />
              </span>
              <span className={`num text-right ${up ? 'text-up' : 'text-down'}`}>{change(s.changePct)}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
