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
