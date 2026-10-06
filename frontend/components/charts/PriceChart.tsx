'use client';

import { useEffect, useId, useMemo, useRef, useState, useTransition } from 'react';
import { change, num } from '@/lib/format';
import type { PricePoint } from '@/lib/types';

type Range = '1d' | '1mo' | '6mo' | '1y' | '5y';
const LABELS: Record<Range, string> = { '1d': '1D', '1mo': '1M', '6mo': '6M', '1y': '1Y', '5y': '5Y' };

const PAD = { top: 12, right: 64, bottom: 26, left: 0 };

/**
 * Price line with a gradient fill and crosshair tooltip. The line is mint when
 * the period ended higher than it started and coral when lower.
 * Used on stock pages (with the price read-out) and in the dashboard hero (`bare`).
 */
export function PriceChart({
  symbol,
  initial,
  initialRange = '1y',
  ranges = ['1mo', '6mo', '1y', '5y'],
  height = 240,
  bare = false,
  title,
}: {
  symbol: string;
  initial: PricePoint[];
  initialRange?: Range;
  ranges?: Range[];
  height?: number;
  /** Hide the price read-out; show a small title and the range switch only. */
  bare?: boolean;
  title?: string;
}) {
  const [range, setRange] = useState<Range>(initialRange);
  const [points, setPoints] = useState(initial);
  const [hover, setHover] = useState<number | null>(null);
  const [pending, startTransition] = useTransition();
  const svgRef = useRef<SVGSVGElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const gradientId = useId();
  // Draw at the real pixel width so text and strokes are never scaled.
  const [W, setW] = useState(720);
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setW(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const H = height;
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
  }, [points, W, H]);

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
  const color = geo?.up ? '#22D39A' : '#FF5D73';
  const glow = geo?.up ? 'rgb(34 211 154 / 0.55)' : 'rgb(255 93 115 / 0.55)';
  const dateFmt = (t: number) =>
    range === '1d'
      ? new Date(t * 1000).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })
      : new Date(t * 1000).toLocaleDateString(
          'en-IN',
          range === '5y' || range === '1y' ? { day: 'numeric', month: 'short', year: '2-digit' } : { day: 'numeric', month: 'short' },
        );

  return (
    <div ref={boxRef} className="min-w-0">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        {bare ? (
          <div className="text-sm text-ink-2">
            {hover != null && shown ? <span className="num text-ink">{dateFmt(shown.t)}  {num(shown.close)}</span> : title}
          </div>
        ) : (
          <div className="min-h-[2.6rem]">
            {shown && (
              <>
                <div className="text-[0.8rem] text-ink-3">{hover != null ? dateFmt(shown.t) : 'Close'}</div>
                <div className="num text-base text-ink">
                  ₹{num(shown.close)}{' '}
                  <span className={periodChange != null && periodChange < 0 ? 'text-down' : 'text-up'}>{change(periodChange)}</span>{' '}
                  <span className="text-ink-3">over {LABELS[range]}</span>
                </div>
              </>
            )}
          </div>
        )}
        <div className="segmented" role="group" aria-label="Chart range">
          {ranges.map((r) => (
            <button key={r} aria-pressed={range === r} onClick={() => selectRange(r)}>
              {LABELS[r]}
            </button>
          ))}
        </div>
      </div>

      {!geo ? (
        <div className="grid place-items-center rounded-lg bg-sunken text-sm text-ink-3" style={{ height: H }}>
          {pending ? 'Loading…' : range === '1d' ? 'No trades yet today. The market opens at 9:15.' : 'Price history is unavailable right now.'}
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
          aria-label={`${symbol} price, ${LABELS[range]}`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.32} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          {geo.ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={W - PAD.right} y1={geo.y(t)} y2={geo.y(t)} stroke="rgb(148 163 209 / 0.1)" />
              <text x={W - PAD.right + 8} y={geo.y(t) + 4} className="num fill-ink-3 text-[11px]">
                {num(t, t >= 1000 ? 0 : 1)}
              </text>
            </g>
          ))}
          <path d={geo.area} fill={`url(#${gradientId})`} />
          <path
            d={geo.line}
            fill="none"
            stroke={color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${glow})` }}
          />
          {[0, Math.floor((points.length - 1) / 2), points.length - 1].map((i, k) => (
            <text
              key={i}
              x={geo.x(i)}
              y={H - 6}
              textAnchor={k === 0 ? 'start' : k === 2 ? 'end' : 'middle'}
              className="num fill-ink-3 text-[11px]"
            >
              {dateFmt(points[i].t)}
            </text>
          ))}
          {hover != null ? (
            <g pointerEvents="none">
              <line x1={geo.x(hover)} x2={geo.x(hover)} y1={PAD.top} y2={H - PAD.bottom} stroke="rgb(148 163 209 / 0.4)" strokeWidth={1} />
              <circle cx={geo.x(hover)} cy={geo.y(points[hover].close)} r={4.5} fill={color} stroke="var(--color-surface)" strokeWidth={2} />
            </g>
          ) : (
            <circle cx={geo.x(points.length - 1)} cy={geo.y(points.at(-1)!.close)} r={4} fill={color} stroke="var(--color-surface)" strokeWidth={2} />
          )}
        </svg>
      )}
    </div>
  );
}
