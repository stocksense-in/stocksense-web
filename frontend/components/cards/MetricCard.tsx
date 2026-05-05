'use client';
import { MM, C } from '@/lib/constants';
import { getMetricStatus } from '@/lib/utils';
import { MetricKey } from '@/lib/types';
import { METRIC_CONTENT } from '@/lib/metricContent';

interface MetricCardProps {
  mk: MetricKey;
  val: number;
  sector: string;
  /** Called when the card is clicked — parent opens the overlay */
  onOpen: () => void;
}

export function MetricCard({ mk, val, sector, onOpen }: MetricCardProps) {
  const m = MM[mk];
  const st = getMetricStatus(mk, val, sector);
  const dc = st === 'green' ? 'var(--green)' : st === 'yellow' ? 'var(--gold)' : 'var(--red)';
  const dcRaw = st === 'green' ? '#00E676' : st === 'yellow' ? '#C9A84C' : '#C45C5C';
  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  const dl = Math.max(1, Math.min(97, n));
  const il = Math.max(0, Math.min(90, ip));
  const bcl = st === 'green' ? 'pill-g' : st === 'yellow' ? 'pill-gold' : 'pill-r';
  const bl = st === 'green' ? 'Healthy' : st === 'yellow' ? 'Monitor' : 'Concern';
  const borderColor = st === 'green' ? 'rgba(0,230,118,.2)' : st === 'yellow' ? 'rgba(201,168,76,.2)' : 'rgba(196,92,92,.2)';

  // Layer 1 content
  const cardContent = METRIC_CONTENT[mk]?.card;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpen();
  };

  return (
    <div
      className="mc"
      style={{ borderColor }}
      onClick={handleClick}
    >
      <div className="mc-top">
        <span className="mc-name">{m.name}</span>
        <div className="status-dot" style={{ background: dcRaw, boxShadow: `0 0 6px ${dcRaw}` }} />
      </div>
      <div className="mc-val">{val}<sup> {m.unit}</sup></div>
      <div className="ideal-bar">
        <div className="ideal-bar-lbl">
          <span>{m.lo}</span>
          <span style={{ color: 'var(--gold)', fontSize: 8 }}>▌ Ideal zone</span>
          <span>{m.hi}</span>
        </div>
        <div className="ideal-track">
          <div className="ideal-zone" style={{ left: `${il}%`, width: `${iw}%`, background: dcRaw }} />
          <div className="ideal-mid"  style={{ left: `${il + iw / 2}%` }} />
          <div className="ideal-needle" style={{ left: `${dl}%`, background: dcRaw, boxShadow: `0 0 6px ${dcRaw}` }} />
        </div>
        <div className="ideal-ann">
          <span style={{ fontSize: 9, color: 'var(--cream-mute)' }}>Ideal: {m.il}</span>
          <span className={`pill ${bcl}`} style={{ fontSize: 8 }}>{bl}</span>
        </div>
      </div>

      {/* Layer 1: plain lang + card insight */}
      <div className="mc-plain">{m.plain(val, sector)}</div>

      {cardContent && (
        <div style={{
          marginTop: 10,
          paddingTop: 10,
          borderTop: '1px solid rgba(201,168,76,0.06)',
        }}>
          {/* Insight */}
          <div style={{
            fontSize: 10,
            color: 'var(--cream-dim)',
            lineHeight: 1.6,
            marginBottom: 8,
          }}>
            {cardContent.insight}
          </div>
          {/* Risk chip */}
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 5,
            fontSize: 9,
            lineHeight: 1.5,
            width: '100%',
          }}>
            <span style={{ flexShrink: 0, color: 'var(--red)' }}>⚠</span>
            <span style={{ color: 'rgba(196,92,92,0.75)' }}>{cardContent.risk}</span>
          </div>
        </div>
      )}
    </div>
  );
}