'use client';
import React, { useState } from 'react';
import { IPOS, C } from '@/lib/constants';
import { scoreColor } from '@/lib/utils';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';

export function IPOPage() {
  const [selected, setSelected] = useState<number | null>(null);

  const sel = selected !== null ? IPOS[selected] : null;

  const sigs: [string, string, number][] = sel
    ? [['GMP Signal', '20%', sel.gmp], ['QIB Subscription', '25%', sel.qib], ['Retail Interest', '10%', sel.retail], ['Fundamentals', '30%', sel.fund], ['Geo Risk Score', '15%', sel.geo]]
    : [];

  const methodWeights = [
    ['Fundamentals', '30%', 'gold'],
    ['QIB Subscription', '25%', 'gold'],
    ['GMP Signal', '20%', 'gold'],
    ['Geo Risk', '15%', 'red'],
    ['Retail Interest', '10%', 'green'],
  ];

  return (
    <div>
      {/* Header strip */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <div className="ct" style={{ marginBottom: 3 }}>Active IPOs · Tap to Analyse</div>
          <div style={{ fontSize: 12, color: 'var(--cream-dim)' }}>5-factor scoring: Fundamentals · GMP · QIB · Retail · Geo Risk</div>
        </div>
        <span className="live-badge"><div className="live-dot" />IPO TRACKER</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 12 }}>
        {/* IPO list */}
        <div>
          {IPOS.map((ipo, i) => {
            const sc = scoreColor(ipo.score);
            const isSel = selected === i;
            return (
              <div
                key={i}
                onClick={() => setSelected(i)}
                className={`ipo-card${isSel ? ' sel' : ''}`}
              >
                {isSel && <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 2, background: 'var(--gold)' }} />}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ paddingLeft: isSel ? 8 : 0, transition: 'padding .15s' }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--cream)', letterSpacing: '-0.3px', marginBottom: 4, fontFamily: 'var(--f-body)' }}>{ipo.name}</div>
                    <div style={{ fontSize: 9, fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--cream-mute)', fontFamily: 'var(--f-body)' }}>{ipo.sector} · Opens {ipo.open}</div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: 22, fontWeight: 500, fontFamily: 'var(--f-mono)', color: sc, letterSpacing: '-1.5px', lineHeight: 1 }}>{ipo.score}</div>
                    <div style={{ fontSize: 7, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--cream-mute)', marginTop: 2, fontFamily: 'var(--f-mono)' }}>SCORE</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Pill type={ipo.verdict === 'Subscribe' ? 'g' : ipo.verdict === 'Risky' ? 'gold' : 'r'}>{ipo.verdict}</Pill>
                    <span style={{ fontSize: 10, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)', alignSelf: 'center' }}>{ipo.band}</span>
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>{ipo.size}</span>
                </div>
              </div>
            );
          })}

          {/* Scoring methodology card */}
          <div className="card" style={{ marginTop: 4 }}>
            <div className="ct">Scoring Methodology</div>
            {methodWeights.map(([label, pct, c]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid rgba(201,168,76,0.04)' }}>
                <span style={{ fontSize: 11, color: 'var(--cream-dim)' }}>{label}</span>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, fontWeight: 500, color: `var(--${c})` }}>{pct}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div>
          {!sel ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--cream-mute)', gap: 12, padding: '40px 24px', background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 40, opacity: 0.15 }}>◆</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--cream-mute)' }}>Select an IPO to view full analysis</div>
              <div style={{ fontSize: 11, color: 'var(--cream-mute)', textAlign: 'center', maxWidth: 240, lineHeight: 1.6, opacity: 0.6 }}>5-factor scoring powered by fundamentals, institutional demand, and geopolitical risk</div>
            </div>
          ) : (
            <div>
              {/* IPO detail header */}
              <div style={{ position: 'relative', overflow: 'hidden', background: 'var(--s1)', border: `1px solid var(--border)`, borderRadius: 8, padding: '20px 22px', marginBottom: 14 }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${scoreColor(sel.score)},transparent)` }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div className="ct" style={{ marginBottom: 6 }}>{sel.sector} · {sel.size}</div>
                    <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--cream)', marginBottom: 8, fontFamily: 'var(--f-display)' }}>{sel.name}</div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <Pill type={sel.verdict === 'Subscribe' ? 'g' : sel.verdict === 'Risky' ? 'gold' : 'r'}>{sel.verdict}</Pill>
                      <span style={{ fontSize: 10, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)' }}>Price Band: {sel.band}</span>
                      <span style={{ fontSize: 10, color: 'var(--cream-mute)' }}>Opens {sel.open}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 22, fontWeight: 500, fontFamily: 'var(--f-mono)', color: scoreColor(sel.score), letterSpacing: '-2px', lineHeight: 1 }}>{sel.score}</div>
                    <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 4, letterSpacing: '1.5px', fontWeight: 500, fontFamily: 'var(--f-mono)' }}>/ 100</div>
                  </div>
                </div>
              </div>

              {/* 5 signals */}
              <div className="card" style={{ marginBottom: 14 }}>
                <div className="ct">Signal Breakdown</div>
                {sigs.map(([label, weight, score]) => (
                  <div key={label} style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--cream)' }}>{label}</span>
                        <span style={{ fontSize: 9, color: 'var(--cream-mute)', marginLeft: 8 }}>weight {weight}</span>
                      </div>
                      <span style={{ fontFamily: 'var(--f-mono)', fontSize: 12, fontWeight: 500, color: score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--gold)' : 'var(--red)' }}>{score}</span>
                    </div>
                    <div style={{ height: 4, background: 'rgba(201,168,76,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ width: `${score}%`, height: '100%', borderRadius: 2, background: score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--gold)' : 'var(--red)', opacity: 0.8 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
