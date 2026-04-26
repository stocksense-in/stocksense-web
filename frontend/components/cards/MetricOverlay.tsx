'use client';
import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { MM, C } from '@/lib/constants';
import { getMetricStatus } from '@/lib/utils';
import { MetricKey } from '@/lib/types';
import { METRIC_INTEL } from '@/lib/metricIntel';
import { METRIC_CONTENT } from '@/lib/metricContent';

interface MetricOverlayProps {
  mk: MetricKey;
  val: number;
  sector: string;
  onClose: () => void;
}

export function MetricOverlay({ mk, val, sector, onClose }: MetricOverlayProps) {
  const content = METRIC_CONTENT[mk];
  const m = MM[mk];
  const intel = METRIC_INTEL[mk];
  const st = getMetricStatus(mk, val, sector);
  const dc = st === 'green' ? C.green : st === 'yellow' ? C.gold : C.red;
  const dcRaw = st === 'green' ? '#00E676' : st === 'yellow' ? '#D4AF37' : '#FF3A3A';
  const bcl = st === 'green' ? 'pill-g' : st === 'yellow' ? 'pill-gold' : 'pill-r';
  const bl = st === 'green' ? 'Healthy' : st === 'yellow' ? 'Monitor' : 'Concern';

  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  const dl = Math.max(1, Math.min(97, n));
  const il = Math.max(0, Math.min(90, ip));

  const sectorCtx = intel.sectorAvg(sector);
  const trend = intel.trend(val, sector);
  const rangeLogic = intel.rangeLogic(sector);
  const action = intel.action(val, sector);
  const actionColor = action.color === 'green' ? C.green : action.color === 'gold' ? C.gold : C.red;
  const actionColorRaw = action.color === 'green' ? '#00E676' : action.color === 'gold' ? '#D4AF37' : '#FF3A3A';
  const actionBg = action.color === 'green' ? 'rgba(0,230,118,0.07)' : action.color === 'gold' ? 'rgba(212,175,55,0.07)' : 'rgba(255,58,58,0.07)';
  const actionBorder = action.color === 'green' ? 'rgba(0,230,118,0.2)' : action.color === 'gold' ? 'rgba(212,175,55,0.2)' : 'rgba(255,58,58,0.2)';

  const trendColor = trend.direction === 'improving' ? C.green : trend.direction === 'stable' ? C.gold : C.red;
  const trendIcon = trend.direction === 'improving' ? '↑' : trend.direction === 'stable' ? '→' : '↓';

  const scrollRef = useRef<HTMLDivElement>(null);

  // ESC to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  // Reset scroll on metric change
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [mk]);


  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  return createPortal(
    <>
      <style>{`
        @keyframes mo-in {
          from { opacity: 0; transform: scale(0.97) translateY(12px); }
          to   { opacity: 1; transform: scale(1)    translateY(0);    }
        }
        .mo-backdrop {
          position: fixed; inset: 0; z-index: 9000;
          background: rgba(4,6,12,0.55);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          display: flex; align-items: center; justify-content: center;
          padding: 24px;
        }
        .mo-workspace {
          display: flex;
          width: min(920px, 88vw);
          height: min(78vh, 680px);
          background: rgba(11,16,28,0.88);
          backdrop-filter: blur(28px);
          -webkit-backdrop-filter: blur(28px);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 20px;
          box-shadow: 0 32px 80px rgba(0,0,0,0.75), 0 0 0 1px rgba(0,212,255,0.03) inset;
          animation: mo-in 210ms cubic-bezier(0.22,1,0.36,1) both;
          overflow: hidden;
          position: relative;
        }

        /* Top glow */
        .mo-top-glow {
          position: absolute; top: 0; left: 60px; right: 60px; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(0,212,255,0.3), transparent);
          pointer-events: none;
        }

        /* ── LEFT PANEL ── */
        .mo-left {
          width: 310px; flex-shrink: 0;
          padding: 28px 24px;
          border-right: 1px solid rgba(255,255,255,0.05);
          display: flex; flex-direction: column; gap: 0;
          background: rgba(8,11,20,0.4);
          overflow: hidden;
        }
        .mo-eyebrow {
          font-size: 9px; font-weight: 700; letter-spacing: 2.5px;
          text-transform: uppercase; color: var(--ink3); margin-bottom: 16px;
        }
        .mo-metric-name {
          font-size: 19px; font-weight: 800; color: var(--ink);
          letter-spacing: -.3px; line-height: 1.25; margin-bottom: 6px;
        }
        .mo-val-block { display: flex; align-items: baseline; gap: 5px; margin: 16px 0 6px; }
        .mo-big-val { font-size: 58px; font-weight: 900; line-height: 1; letter-spacing: -3px; }
        .mo-big-unit { font-size: 20px; font-weight: 400; color: var(--ink2); letter-spacing: 0; }

        .mo-bar-section { margin: 16px 0 0; }
        .mo-bar-title { font-size: 8px; font-weight: 700; letter-spacing: 1.8px; text-transform: uppercase; color: var(--ink3); margin-bottom: 8px; }
        .mo-bar-labels { display: flex; justify-content: space-between; font-size: 8px; color: var(--ink3); margin-bottom: 5px; }
        .mo-track {
          position: relative; height: 7px;
          background: rgba(238,242,255,0.06); border-radius: 4px; overflow: visible;
        }
        .mo-zone { position: absolute; top: 0; height: 100%; border-radius: 4px; opacity: .3; }
        .mo-mid { position: absolute; top: -5px; width: 1px; height: 17px; background: rgba(238,242,255,0.12); }
        .mo-needle {
          position: absolute; top: 50%; transform: translate(-50%,-50%);
          width: 15px; height: 15px; border-radius: 50%;
          border: 2.5px solid rgba(11,16,28,0.9); z-index: 2;
        }
        .mo-bar-ann { display: flex; justify-content: space-between; align-items: center; margin-top: 9px; }

        .mo-position-block {
          margin-top: 18px; padding: 12px 14px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 10px;
        }
        .mo-pos-label { font-size: 8px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ink3); margin-bottom: 6px; }
        .mo-pos-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
        .mo-pos-k { font-size: 10px; color: var(--ink3); }
        .mo-pos-v { font-size: 10px; font-weight: 700; color: var(--ink); }

        .mo-plain-left {
          margin-top: 18px; padding-top: 18px;
          border-top: 1px solid rgba(255,255,255,0.05);
          font-size: 11px; color: var(--ink2); line-height: 1.75;
        }

        /* ── RIGHT PANEL ── */
        .mo-right {
          flex: 1; overflow-y: auto; padding: 28px 28px 32px;
          scrollbar-width: thin;
          scrollbar-color: rgba(0,212,255,0.15) transparent;
        }
        .mo-right::-webkit-scrollbar { width: 4px; }
        .mo-right::-webkit-scrollbar-track { background: transparent; }
        .mo-right::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.15); border-radius: 2px; }

        .mo-close {
          position: absolute; top: 16px; right: 18px; z-index: 10;
          width: 30px; height: 30px; border-radius: 8px;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.09);
          color: rgba(238,242,255,0.5);
          font-size: 14px; display: flex; align-items: center; justify-content: center;
          cursor: pointer; transition: all .15s;
        }
        .mo-close:hover { background: rgba(255,255,255,0.12); color: var(--ink); }

        /* Right panel sections */
        .mo-section { margin-bottom: 24px; }
        .mo-section-title {
          font-size: 8px; font-weight: 700; letter-spacing: 2px;
          text-transform: uppercase; color: var(--ink3);
          display: flex; align-items: center; gap: 8px;
          margin-bottom: 10px;
        }
        .mo-section-title::after {
          content: ''; flex: 1; height: 1px;
          background: rgba(255,255,255,0.05);
        }
        .mo-divider { height: 1px; background: rgba(255,255,255,0.04); margin: 20px 0; }

        /* Summary */
        .mo-summary {
          padding: 16px 18px;
          background: rgba(0,212,255,0.05);
          border: 1px solid rgba(0,212,255,0.12);
          border-left: 3px solid rgba(0,212,255,0.6);
          border-radius: 0 10px 10px 0;
          font-size: 13px; font-weight: 500;
          color: var(--ink); line-height: 1.75;
        }

        /* Verdict quote */
        .mo-verdict {
          font-size: 13px; font-weight: 700; font-style: italic;
          padding: 12px 0; color: var(--ink2); line-height: 1.6;
        }

        /* Definition */
        .mo-def { font-size: 12px; color: var(--ink2); line-height: 1.8; }

        /* Sector comparison */
        .mo-sector-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
        .mo-sector-cell {
          padding: 10px 12px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 8px;
        }
        .mo-sector-cell-label { font-size: 8px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--ink3); margin-bottom: 5px; }
        .mo-sector-cell-val { font-size: 13px; font-weight: 700; color: var(--ink); }

        /* Trend */
        .mo-trend-row { display: flex; align-items: flex-start; gap: 12px; }
        .mo-trend-badge {
          font-size: 11px; font-weight: 700; padding: 4px 10px;
          border-radius: 6px; flex-shrink: 0; letter-spacing: .3px;
        }
        .mo-trend-text { font-size: 12px; color: var(--ink2); line-height: 1.75; }

        /* Range logic */
        .mo-range-block {
          padding: 12px 14px;
          border-left: 2px solid var(--gold);
          background: rgba(212,175,55,0.04);
          border-radius: 0 8px 8px 0;
          font-size: 12px; color: var(--ink2); line-height: 1.75;
        }

        /* Risks */
        .mo-risk-list { display: flex; flex-direction: column; gap: 7px; }
        .mo-risk-item {
          display: flex; align-items: flex-start; gap: 10px;
          padding: 9px 12px;
          background: rgba(255,58,58,0.04);
          border: 1px solid rgba(255,58,58,0.1);
          border-radius: 8px;
          font-size: 11px; color: var(--ink2); line-height: 1.65;
        }
        .mo-risk-dot {
          width: 5px; height: 5px; border-radius: 50%;
          background: var(--red); flex-shrink: 0; margin-top: 5px;
        }

        /* Drivers */
        .mo-drivers-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .mo-driver-card {
          padding: 11px 13px;
          background: rgba(255,255,255,0.025);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 9px;
        }
        .mo-driver-label {
          font-size: 9px; font-weight: 700; letter-spacing: .8px;
          text-transform: uppercase; color: var(--blue);
          margin-bottom: 5px;
        }
        .mo-driver-desc { font-size: 11px; color: var(--ink2); line-height: 1.6; }

        /* Impact */
        .mo-impact { font-size: 12px; color: var(--ink2); line-height: 1.8; }

        /* Action */
        .mo-action-block {
          padding: 16px 18px;
          border-radius: 12px;
          border: 1px solid;
        }
        .mo-action-label {
          font-size: 9px; font-weight: 700; letter-spacing: 1.8px;
          text-transform: uppercase; margin-bottom: 8px;
        }
        .mo-action-title { font-size: 15px; font-weight: 800; margin-bottom: 8px; }
        .mo-action-text { font-size: 12px; line-height: 1.75; opacity: .8; }
      `}</style>

      <div
        className="mo-backdrop"
        onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      >
        <div className="mo-workspace">
          <div className="mo-top-glow" />

          {/* ── CLOSE BTN ── */}
          <button className="mo-close" onClick={onClose} aria-label="Close overlay">✕</button>

          {/* ════════════ LEFT PANEL ════════════ */}
          <div className="mo-left">
            <div className="mo-eyebrow">Metric Intelligence</div>

            <div className="mo-metric-name">{m.name}</div>
            <span className={`pill ${bcl}`} style={{ alignSelf: 'flex-start', fontSize: 9 }}>{bl}</span>

            {/* Big value */}
            <div className="mo-val-block">
              <span className="mo-big-val" style={{ color: dcRaw }}>{val}</span>
              <span className="mo-big-unit">{m.unit}</span>
            </div>

            {/* Ideal bar */}
            <div className="mo-bar-section">
              <div className="mo-bar-title">Position in Range</div>
              <div className="mo-bar-labels">
                <span>{m.lo}</span>
                <span style={{ color: '#D4AF37', fontSize: 7 }}>▌ Ideal zone</span>
                <span>{m.hi}</span>
              </div>
              <div className="mo-track">
                <div className="mo-zone" style={{ left: `${il}%`, width: `${iw}%`, background: dcRaw }} />
                <div className="mo-mid"  style={{ left: `${il + iw / 2}%` }} />
                <div
                  className="mo-needle"
                  style={{ left: `${dl}%`, background: dcRaw, boxShadow: `0 0 10px ${dcRaw}88` }}
                />
              </div>
              <div className="mo-bar-ann">
                <span style={{ fontSize: 8, color: 'var(--ink3)' }}>Ideal: {m.il}</span>
                <span style={{ fontSize: 8, color: 'var(--ink3)' }}>
                  This: <strong style={{ color: dcRaw }}>{val}{m.unit}</strong>
                </span>
              </div>
            </div>

            {/* Snapshot */}
            <div className="mo-position-block">
              <div className="mo-pos-label">Snapshot</div>
              <div className="mo-pos-row">
                <span className="mo-pos-k">Sector avg</span>
                <span className="mo-pos-v">{sectorCtx.avg}</span>
              </div>
              <div className="mo-pos-row">
                <span className="mo-pos-k">Top quartile</span>
                <span className="mo-pos-v">{sectorCtx.top}</span>
              </div>
              <div className="mo-pos-row">
                <span className="mo-pos-k">Peer group</span>
                <span className="mo-pos-v" style={{ fontSize: 9 }}>{sectorCtx.label}</span>
              </div>
              <div className="mo-pos-row" style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <span className="mo-pos-k">Trend</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: trend.direction === 'improving' ? '#00E676' : trend.direction === 'stable' ? '#D4AF37' : '#FF3A3A' }}>
                  {trendIcon} {trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1)}
                </span>
              </div>
            </div>

            {/* Plain summary */}
            <div className="mo-plain-left">{m.plain(val, sector)}</div>
          </div>

          {/* ════════════ RIGHT PANEL ════════════ */}
          <div className="mo-right" ref={scrollRef} onClick={e => e.stopPropagation()}>

            {/* ── LAYER 2: Medium — always visible ── */}
            {content?.medium && (
              <>
                {/* Why it matters */}
                <div className="mo-section">
                  <div className="mo-section-title">⭐ Why This Metric Matters</div>
                  <div className="mo-summary">{content.medium.why}</div>
                </div>

                {/* Price impact */}
                <div className="mo-section">
                  <div className="mo-section-title">📈 How It Moves Price</div>
                  <div className="mo-def" style={{ lineHeight: 1.8 }}>{content.medium.priceImpact}</div>
                </div>

                {/* Risk bullets */}
                <div className="mo-section">
                  <div className="mo-section-title">⚠️ Key Risks</div>
                  <div className="mo-risk-list">
                    {content.medium.risks.map((r, i) => (
                      <div key={i} className="mo-risk-item">
                        <div className="mo-risk-dot" />
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* ── GOLD SECTION DIVIDER ── */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              margin: '4px 0 24px',
            }}>
              <div style={{ flex: 1, height: 1, background: 'rgba(212,175,55,0.15)' }} />
              <span style={{
                fontSize: 9, fontWeight: 700, letterSpacing: '1.5px',
                color: 'var(--gold)', whiteSpace: 'nowrap', textTransform: 'uppercase',
                fontFamily: 'var(--f)',
              }}>Detailed Analysis</span>
              <div style={{ flex: 1, height: 1, background: 'rgba(212,175,55,0.15)' }} />
            </div>

            {/* ── LAYER 3: Full analysis — always visible ── */}
            {content?.full && (
              <>
                {/* Core Insight */}
                <div className="mo-section">
                  <div className="mo-section-title">💡 Core Insight</div>
                  <div className="mo-summary">{content.full.coreInsight}</div>
                </div>

                {/* Price Mechanism */}
                <div className="mo-section">
                  <div className="mo-section-title">⚙️ Price Mechanism</div>
                  <div className="mo-def" style={{ lineHeight: 1.8 }}>{content.full.mechanism}</div>
                </div>

                <div className="mo-divider" />

                {/* Sector Context */}
                <div className="mo-section">
                  <div className="mo-section-title">🏭 Sector Context</div>
                  <div className="mo-range-block">{content.full.sector}</div>
                </div>

                {/* Drivers */}
                <div className="mo-section">
                  <div className="mo-section-title">🧮 Root Cause — What Drives This</div>
                  <div className="mo-def" style={{ lineHeight: 1.8 }}>{content.full.drivers}</div>
                </div>

                <div className="mo-divider" />

                {/* Risk Signals */}
                <div className="mo-section">
                  <div className="mo-section-title">⚠️ Risk Signals</div>
                  <div className="mo-risk-list">
                    {content.full.risks.map((r, i) => (
                      <div key={i} className="mo-risk-item">
                        <div className="mo-risk-dot" />
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Fake Signals */}
                <div className="mo-section">
                  <div className="mo-section-title">🚩 Fake Signal Detection</div>
                  <div className="mo-risk-list">
                    {content.full.fakeSignals.map((f, i) => (
                      <div key={i} className="mo-risk-item" style={{
                        background: 'rgba(212,175,55,0.04)',
                        borderColor: 'rgba(212,175,55,0.15)',
                      }}>
                        <div className="mo-risk-dot" style={{ background: 'var(--gold)' }} />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mo-divider" />

                {/* Final Verdict */}
                <div
                  className="mo-action-block"
                  style={{ background: actionBg, borderColor: actionBorder }}
                >
                  <div className="mo-action-label" style={{ color: actionColorRaw }}>🚀 Final Verdict Logic</div>
                  <div className="mo-action-title" style={{ color: actionColorRaw }}>{action.label}</div>
                  <div className="mo-action-text" style={{ color: 'var(--ink2)', marginBottom: 12 }}>{action.text}</div>
                  <div style={{
                    fontSize: 11, color: 'var(--ink2)', lineHeight: 1.75,
                    borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 10,
                  }}>
                    {content.full.verdict}
                  </div>
                </div>
              </>
            )}

          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
