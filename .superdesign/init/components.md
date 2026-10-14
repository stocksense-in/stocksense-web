# Components

Framework: Next.js 16 App Router, React 19, TypeScript. Styling: Tailwind CSS v4 (tokens in app/globals.css @theme) plus a few component classes (.panel, .btn, .field, .data-table, .segmented, .ideal-band, .num). Icons: lucide-react. No component library.

## Change
Signed % change, green up / red down

### `frontend/components/ui/Change.tsx`

```tsx
import { change, direction } from '@/lib/format';

/** A signed day-change like "+1.42%", green when up and red when down. */
export function Change({ value, className = '' }: { value: number | null | undefined; className?: string }) {
  const dir = direction(value);
  const color = dir === 'up' ? 'text-up' : dir === 'down' ? 'text-down' : 'text-ink-3';
  return <span className={`num ${color} ${className}`}>{change(value)}</span>;
}
```

## StatusBadge
Dot + word status pill (healthy/watch/concern/neutral)

### `frontend/components/ui/StatusBadge.tsx`

```tsx
import type { Status } from '@/lib/types';

const STYLES: Record<Status, { dot: string; text: string; bg: string }> = {
  healthy: { dot: 'bg-up', text: 'text-up', bg: 'bg-up-wash' },
  watch: { dot: 'bg-watch', text: 'text-watch-ink', bg: 'bg-watch-wash' },
  concern: { dot: 'bg-down', text: 'text-down', bg: 'bg-down-wash' },
  neutral: { dot: 'bg-ink-3', text: 'text-ink-2', bg: 'bg-sunken' },
};

/** Coloured dot + word. Status is never shown by colour alone. */
export function StatusBadge({ status, children }: { status: Status; children: React.ReactNode }) {
  const s = STYLES[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.8rem] font-medium ${s.bg} ${s.text}`}>
      <span className={`size-1.5 rounded-full ${s.dot}`} aria-hidden />
      {children}
    </span>
  );
}

export const STATUS_FILL: Record<Status, string> = {
  healthy: 'bg-up',
  watch: 'bg-watch',
  concern: 'bg-down',
  neutral: 'bg-ink-3',
};
```

## MetricGauge
Ruler gauge with hatched sector ideal band and value marker

### `frontend/components/ui/MetricGauge.tsx`

```tsx
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
```

## ScoreMeter
0–100 StockSense score meter (full and compact)

### `frontend/components/ui/ScoreMeter.tsx`

```tsx
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
```

## StockTable
Compact stock list table (symbol, price, change, score)

### `frontend/components/ui/StockTable.tsx`

```tsx
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
              <Change value={s.changePct} />
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
```

## AutoSubmitForm
GET form that submits on change

### `frontend/components/ui/AutoSubmitForm.tsx`

```tsx
'use client';

/** A GET form that submits itself whenever a field changes — filters apply instantly, and still work without JavaScript via the submit button. */
export function AutoSubmitForm({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <form
      method="get"
      className={className}
      onChange={(e) => (e.currentTarget as HTMLFormElement).requestSubmit()}
    >
      {children}
    </form>
  );
}
```

## PriceChart
SVG closing-price line chart with crosshair + range switch

### `frontend/components/charts/PriceChart.tsx`

```tsx
'use client';

import { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { change, num } from '@/lib/format';
import type { PricePoint } from '@/lib/types';

type Range = '1mo' | '6mo' | '1y' | '5y';
const RANGES: { value: Range; label: string }[] = [
  { value: '1mo', label: '1M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '5y', label: '5Y' },
];

const H = 240;
const PAD = { top: 12, right: 64, bottom: 26, left: 0 };

/**
 * Closing-price line with a crosshair tooltip. The line is green when the
 * period ended higher than it started and red when lower.
 */
export function PriceChart({
  symbol,
  initial,
  initialRange = '1y',
}: {
  symbol: string;
  initial: PricePoint[];
  initialRange?: Range;
}) {
  const [range, setRange] = useState<Range>(initialRange);
  const [points, setPoints] = useState(initial);
  const [hover, setHover] = useState<number | null>(null);
  const [pending, startTransition] = useTransition();
  const svgRef = useRef<SVGSVGElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  // Draw at the real pixel width so text and strokes are never scaled.
  const [W, setW] = useState(720);
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setW(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const selectRange = (next: Range) => {
    setRange(next);
    startTransition(async () => {
      const res = await fetch(`/api/chart/${encodeURIComponent(symbol)}?range=${next}`);
      setPoints(res.ok ? await res.json() : []);
    });
  };

  const geo = useMemo(() => {
    if (points.length < 2) return null;
    const closes = points.map((p) => p.close);
    const lo = Math.min(...closes), hi = Math.max(...closes);
    const span = hi - lo || 1;
    const yMin = lo - span * 0.08, yMax = hi + span * 0.08;
    const x = (i: number) => PAD.left + (i / (points.length - 1)) * (W - PAD.left - PAD.right);
    const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
    const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`).join('');
    const area = `${line}L${x(points.length - 1)},${H - PAD.bottom}L${x(0)},${H - PAD.bottom}Z`;
    const ticks = [0, 1, 2, 3].map((k) => yMin + ((yMax - yMin) * (k + 0.5)) / 4);
    const up = closes.at(-1)! >= closes[0];
    return { x, y, line, area, ticks, up };
  }, [points, W]);

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const box = svgRef.current?.getBoundingClientRect();
    if (!box || points.length < 2) return;
    const plotWidth = ((W - PAD.left - PAD.right) / W) * box.width;
    const ratio = (e.clientX - box.left - (PAD.left / W) * box.width) / plotWidth;
    setHover(Math.max(0, Math.min(points.length - 1, Math.round(ratio * (points.length - 1)))));
  };

  const first = points[0]?.close;
  const shown = hover != null ? points[hover] : points.at(-1);
  const periodChange = first && shown ? ((shown.close - first) / first) * 100 : null;
  const color = geo?.up ? 'var(--color-up)' : 'var(--color-down)';
  const dateFmt = (t: number) =>
    new Date(t * 1000).toLocaleDateString('en-IN', range === '5y' || range === '1y'
      ? { day: 'numeric', month: 'short', year: '2-digit' }
      : { day: 'numeric', month: 'short' });

  return (
    <div ref={boxRef} className="min-w-0">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div className="min-h-[2.6rem]">
          {shown && (
            <>
              <div className="text-[0.8rem] text-ink-3">{hover != null ? dateFmt(shown.t) : 'Close'}</div>
              <div className="num text-base text-ink">
                ₹{num(shown.close)}{' '}
                <span className={periodChange != null && periodChange < 0 ? 'text-down' : 'text-up'}>
                  {change(periodChange)}
                </span>{' '}
                <span className="text-ink-3">over {RANGES.find((r) => r.value === range)?.label}</span>
              </div>
            </>
          )}
        </div>
        <div className="segmented" role="group" aria-label="Chart range">
          {RANGES.map((r) => (
            <button key={r.value} aria-pressed={range === r.value} onClick={() => selectRange(r.value)}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {!geo ? (
        <div className="grid h-[240px] place-items-center rounded-lg bg-sunken text-sm text-ink-3">
          {pending ? 'Loading…' : 'Price history is unavailable right now.'}
        </div>
      ) : (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          className={`block max-w-full touch-none select-none transition-opacity ${pending ? 'opacity-50' : ''}`}
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
          role="img"
          aria-label={`${symbol} closing price, ${RANGES.find((r) => r.value === range)?.label}`}
        >
          {geo.ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={W - PAD.right} y1={geo.y(t)} y2={geo.y(t)} stroke="var(--color-rule-2)" />
              <text x={W - PAD.right + 8} y={geo.y(t) + 4} className="num fill-ink-3 text-[11px]">
                {num(t, t >= 1000 ? 0 : 1)}
              </text>
            </g>
          ))}
          <path d={geo.area} fill={color} opacity={0.08} />
          <path d={geo.line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {[0, Math.floor((points.length - 1) / 2), points.length - 1].map((i, k) => (
            <text
              key={i}
              x={geo.x(i)}
              y={H - 6}
              textAnchor={k === 0 ? 'start' : k === 2 ? 'end' : 'middle'}
              className="fill-ink-3 text-[11px]"
            >
              {dateFmt(points[i].t)}
            </text>
          ))}
          {hover != null && (
            <g pointerEvents="none">
              <line x1={geo.x(hover)} x2={geo.x(hover)} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--color-ink-3)" strokeDasharray="0" strokeWidth={1} />
              <circle cx={geo.x(hover)} cy={geo.y(points[hover].close)} r={4.5} fill={color} stroke="var(--color-surface)" strokeWidth={2} />
            </g>
          )}
        </svg>
      )}
    </div>
  );
}
```

## SectorBars
Diverging sector change bars

### `frontend/components/charts/SectorBars.tsx`

```tsx
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
```

