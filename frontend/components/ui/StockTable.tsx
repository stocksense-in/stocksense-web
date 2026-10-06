import Link from 'next/link';
import { Change } from './Change';
import { ScoreMeter } from './ScoreMeter';
import { inr } from '@/lib/format';
import type { Stock } from '@/lib/types';

/** Compact list of stocks: name, price, day change, optional score. Rows link to the stock page. */
export function StockTable({ stocks, showScore = false, empty }: { stocks: Stock[]; showScore?: boolean; empty: string }) {
  if (stocks.length === 0) return <p className="px-5 py-6 text-sm text-ink-3">{empty}</p>;
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Company</th>
          <th className="r">Price</th>
          <th className="r">Today</th>
          {showScore && <th className="r">Score</th>}
        </tr>
      </thead>
      <tbody>
        {stocks.map((s) => (
          <tr key={s.symbol} className="relative">
            <td className="max-w-0 w-full">
              <Link href={`/stocks/${encodeURIComponent(s.symbol)}`} className="block after:absolute after:inset-0">
                <span className="font-medium text-ink">{s.symbol}</span>
                <span className="block truncate text-[0.8rem] text-ink-3">{s.name}</span>
              </Link>
            </td>
            <td className="r num whitespace-nowrap text-ink">{inr(s.price)}</td>
            <td className="r whitespace-nowrap">
              <Change value={s.changePct} pill />
            </td>
            {showScore && (
              <td className="r">
                <ScoreMeter score={s.score} compact />
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
