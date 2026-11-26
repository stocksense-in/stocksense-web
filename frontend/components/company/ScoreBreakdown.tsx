'use client';
import { useState } from 'react';
import type { ScoreDetail, ScorePart } from '@/lib/api';
import { fmtNum, verdictColor, verdictPill } from '@/lib/api';
import { METRIC_CONTENT } from '@/lib/metricContent';

const UNIT: Record<string, string> = { pe: '×', de: '×', roe: '%', margin: '%', promoter: '%', cagr: '%' };

function metricValue(p: ScorePart): string {
  if (p.value === null || p.value === undefined) return 'Not available';
  const digits = p.metric === 'de' ? 2 : 1;
  return `${fmtNum(p.value, digits)}${UNIT[p.metric] ?? ''}`;
}

/** Where the company sits among its sector peers: 0 = worst, 100 = best on this measure. */
function PeerBar({ part }: { part: ScorePart }) {
  const pct = part.peers?.better_than_pct;
  if (pct === null || pct === undefined) return null;
  const color = verdictColor(part.verdict);
  return (
    <div className="ideal-bar" style={{ marginTop: 12, marginBottom: 6 }}>
      <div className="ideal-bar-lbl">
        <span>Weakest in sector</span>
        <span style={{ color: 'var(--cream-dim)' }}>{part.peers?.standing}</span>
        <span>Strongest</span>
      </div>
      <div className="ideal-track">
        <div className="ideal-zone" style={{ left: '25%', width: '50%', background: 'var(--gold)' }} />
        <div className="ideal-mid" style={{ left: '50%' }} />
        <div className="ideal-needle" style={{ left: `${Math.max(2, Math.min(98, pct))}%`, background: color }} />
      </div>
    </div>
  );
}

function PartCard({ part }: { part: ScorePart }) {
  const [open, setOpen] = useState(false);
  const missing = part.value === null || part.value === undefined;
  const notes = [part.guardrail, part.note, part.stage_note, part.history_note, part.market_note].filter(Boolean) as string[];
  const maxPoints = Math.round(part.weight * 100);
  const learn = (METRIC_CONTENT as Record<string, { medium: { why: string; risks: string[] } } | undefined>)[part.metric]?.medium;
  return (
    <div className={`mc${open ? ' open' : ''}`} onClick={() => setOpen(o => !o)} role="button" tabIndex={0}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setOpen(o => !o)} aria-expanded={open}>
      <div className="mc-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div>
          <div className="mc-name" style={{ fontSize: 10, letterSpacing: '1.4px', textTransform: 'uppercase', color: 'var(--cream-mute)', marginBottom: 6 }}>{part.label}</div>
          <div className="mc-val" style={{ fontFamily: 'var(--f-mono)', fontSize: missing ? 13 : 22, color: missing ? 'var(--cream-mute)' : 'var(--cream)', letterSpacing: '-0.5px' }}>{metricValue(part)}</div>
        </div>
        {!missing && part.verdict && <span className={verdictPill(part.verdict)}>{part.verdict}</span>}
      </div>
      <p className="mc-plain" style={{ marginTop: 8 }}>{part.measures}.</p>
      {!missing && <PeerBar part={part} />}
      {!missing && part.peers?.text && <p className="mc-plain" style={{ color: 'var(--cream)' }}>{part.peers.text}</p>}
      {part.guardrail && <p className="mc-plain" style={{ color: 'var(--red)', marginTop: 6 }}>{part.guardrail}</p>}
      {open && (
        <div className="mc-expand" onClick={e => e.stopPropagation()}>
          {part.healthy_range && (
            <div className="stat-r"><span className="sl">Healthy range (all companies)</span><span className="sv" style={{ fontFamily: 'var(--f-mono)', fontSize: 10, textAlign: 'right' }}>{part.healthy_range}</span></div>
          )}
          {part.peers?.typical_range && (
            <div className="stat-r"><span className="sl">Typical in {part.peers.group}</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{part.peers.typical_range}</span></div>
          )}
          <div className="stat-r"><span className="sl">Points in the score</span><span className="sv" style={{ fontFamily: 'var(--f-mono)' }}>{missing ? '—' : `${fmtNum(part.points, 1)} of ${maxPoints}`}</span></div>
          {notes.filter(n => n !== part.guardrail).map((n, i) => (
            <p key={i} className="exp-body" style={{ marginTop: 10, color: 'var(--cream-dim)' }}>{n}</p>
          ))}
          {missing && <p className="exp-body" style={{ marginTop: 10, color: 'var(--cream-dim)' }}>No figure is available for this metric yet, so the score is built from the others.</p>}
          {learn && (
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid rgba(201,168,76,0.06)' }}>
              <div className="ct" style={{ marginBottom: 8 }}>Why it matters</div>
              <p className="exp-body" style={{ color: 'var(--cream-dim)' }}>{learn.why}</p>
              <div className="ct" style={{ margin: '12px 0 8px' }}>Watch out for</div>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {learn.risks.map(r => <li key={r} className="exp-body" style={{ color: 'var(--cream-dim)', marginBottom: 4 }}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
      <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>{open ? 'Less ▲' : 'Ranges and context ▼'}</div>
    </div>
  );
}

export function ScoreBreakdown({ score }: { score: ScoreDetail }) {
  return (
    <div>
      <div className="card" style={{ marginBottom: 12, padding: '12px 16px' }}>
        <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
          {score.stage_text && <span style={{ color: 'var(--cream)' }}>{score.stage_text} </span>}
          Each metric is compared with sector peers (70%) and a fixed scale for all companies (30%).
          {score.coverage_note && <span style={{ color: 'var(--gold)' }}> {score.coverage_note}</span>}
        </div>
      </div>
      <div className="mc-grid" style={{ alignItems: 'start' }}>
        {score.breakdown.map(p => <PartCard key={p.metric} part={p} />)}
      </div>
    </div>
  );
}
