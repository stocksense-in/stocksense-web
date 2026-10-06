import Link from 'next/link';
import type { SectorMove } from '@/lib/data/queries';
import { sectorLabel } from '@/lib/sectors';

/**
 * Sectors as a heatmap bento: mint tiles rose, coral tiles fell, and the
 * stronger the move the brighter the tile. Each tile opens that sector in the screener.
 */
export function SectorBento({ sectors }: { sectors: SectorMove[] }) {
  const extent = Math.max(0.5, ...sectors.map((s) => Math.abs(s.changePct)));
  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {sectors.map((s) => {
        const up = s.changePct >= 0;
        const strength = 0.08 + 0.3 * (Math.abs(s.changePct) / extent);
        const rgb = up ? '34 211 154' : '255 93 115';
        return (
          <li key={s.sector}>
            <Link
              href={`/screener?sector=${s.sector}`}
              className={`tile h-full ${up ? 'text-up' : 'text-down'}`}
              style={{ background: `rgb(${rgb} / ${strength.toFixed(2)})`, borderColor: `rgb(${rgb} / ${Math.min(strength + 0.08, 0.45).toFixed(2)})` }}
              title={`${s.advancers} up, ${s.decliners} down`}
            >
              <span className="truncate text-sm font-medium text-ink">{sectorLabel(s.sector)}</span>
              <span className="num mt-1.5 text-[1.05rem] font-semibold">
                {up ? '+' : '−'}{Math.abs(s.changePct).toFixed(2)}%
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
