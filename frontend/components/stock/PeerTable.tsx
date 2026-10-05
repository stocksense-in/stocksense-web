import Link from 'next/link';
import { ScoreMeter } from '@/components/ui/ScoreMeter';
import { crore } from '@/lib/format';
import { METRICS, METRIC_ORDER, formatMetric } from '@/lib/metrics';
import type { Stock } from '@/lib/types';

/** Same-sector companies side by side. The current stock's row is highlighted. */
export function PeerTable({ stock, peers }: { stock: Stock; peers: Stock[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="data-table min-w-[52rem]">
        <thead>
          <tr>
            <th>Company</th>
            <th className="r">Market cap</th>
            {METRIC_ORDER.map((m) => (
              <th key={m} className="r">{METRICS[m].short}</th>
            ))}
            <th className="r">Score</th>
          </tr>
        </thead>
        <tbody>
          {peers.map((p) => {
            const self = p.symbol === stock.symbol;
            return (
              <tr key={p.symbol} className={self ? 'bg-brand-wash/50' : 'relative'} aria-current={self ? 'true' : undefined}>
                <td>
                  {self ? (
                    <span className="font-medium text-ink">{p.symbol}</span>
                  ) : (
                    <Link href={`/stocks/${encodeURIComponent(p.symbol)}`} className="font-medium text-ink after:absolute after:inset-0 hover:text-brand">
                      {p.symbol}
                    </Link>
                  )}
                </td>
                <td className="r num text-ink-2">{crore(p.marketCap)}</td>
                {METRIC_ORDER.map((m) => (
                  <td key={m} className="r num">{formatMetric(m, p[m])}</td>
                ))}
                <td className="r"><ScoreMeter score={p.score} compact /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
