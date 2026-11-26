'use client';
import { useEffect, useState } from 'react';
import type { AnalogueDetail, Analogues, Geopolitics } from '@/lib/api';
import { api, effectPill, fmtPct, timeAgo } from '@/lib/api';

const effectColor = (e: string) => (e === 'risk' ? 'var(--red)' : e === 'opportunity' || e === 'haven' ? 'var(--green)' : 'var(--gold)');

function AnalogueTable({ index }: { index: Analogues }) {
  const [code, setCode] = useState(index.events[0]?.code ?? '');
  const [horizon, setHorizon] = useState(index.horizons_days.includes(3) ? 3 : index.horizons_days[0]);
  const [detail, setDetail] = useState<AnalogueDetail | null>(null);

  useEffect(() => {
    if (!code) return;
    const ctl = new AbortController();
    api.analogue(code, ctl.signal).then(d => { if (!ctl.signal.aborted) setDetail(d); });
    return () => ctl.abort();
  }, [code]);

  const shown = detail && detail.code === code ? detail : null;
  const cells = (shown?.sectors ?? []).filter(c => c.horizon_days === horizon).sort((a, b) => b.mean_excess_pct - a.mean_excess_pct);
  const span = Math.max(0.5, ...cells.map(c => Math.max(Math.abs(c.ci_low_pct), Math.abs(c.ci_high_pct))));
  const pos = (v: number) => 50 + (v / span) * 50;
  const ev = index.events.find(e => e.code === code);
  const share = index.notable_share[String(horizon)];

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, gap: 8, flexWrap: 'wrap' }}>
        <div className="ct" style={{ marginBottom: 0 }}>What similar events did before · {index.data_from.slice(0, 4)}–{index.data_through.slice(0, 4)}</div>
        <span className="pill pill-gold">Historical tendency, not a forecast</span>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12, alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 240px' }}>
          <div className="field-label">Event</div>
          <select className="fi" value={code} onChange={e => setCode(e.target.value)}>
            {index.events.map(e => <option key={e.code} value={e.code}>{e.label} ({e.occurrences} times)</option>)}
          </select>
        </div>
        <div>
          <div className="field-label">Over the next</div>
          <div style={{ display: 'flex', gap: 4 }}>
            {index.horizons_days.map(h => (
              <button key={h} onClick={() => setHorizon(h)}
                style={{ fontSize: 10, padding: '8px 12px', borderRadius: 4, cursor: 'pointer', fontFamily: 'var(--f-mono)', background: h === horizon ? 'rgba(201,168,76,0.12)' : 'var(--s2)', color: h === horizon ? 'var(--gold)' : 'var(--cream-mute)', border: `1px solid ${h === horizon ? 'var(--border-bright)' : 'var(--border)'}` }}>
                {h} day{h > 1 ? 's' : ''}
              </button>
            ))}
          </div>
        </div>
      </div>

      {ev && (
        <p className="mc-plain" style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--cream)' }}>{ev.label}:</strong> {ev.rule}. Happened {ev.occurrences} times
          {ev.first && ev.last ? ` between ${ev.first.slice(0, 4)} and ${ev.last.slice(0, 4)}` : ''}
          {shown?.recent.length ? `; most recently ${shown.recent.slice(0, 3).map(r => new Date(r.date + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })).join(', ')}` : ''}.
        </p>
      )}

      <div style={{ overflowX: 'auto', opacity: shown ? 1 : 0.5 }}>
        <table className="tbl">
          <thead>
            <tr>
              <th>Sector</th>
              <th style={{ textAlign: 'right' }} title={`Average return minus ${index.benchmark}`}>Avg vs {index.benchmark}</th>
              <th style={{ minWidth: 160 }}>95% range of the average</th>
              <th style={{ textAlign: 'right' }} title={`Share of occurrences where the sector beat ${index.benchmark}`}>Beat the index</th>
              <th style={{ textAlign: 'right' }}>Cases</th>
            </tr>
          </thead>
          <tbody>
            {cells.map(c => {
              const col = !c.notable ? 'var(--cream-dim)' : c.mean_excess_pct >= 0 ? 'var(--green)' : 'var(--red)';
              return (
                <tr key={c.sector}>
                  <td style={{ fontSize: 11.5, color: 'var(--cream)' }} title={index.sector_sources[c.sector]}>
                    {c.sector}{c.notable && <span className="pill pill-gold" style={{ marginLeft: 6, fontSize: 7 }}>notable</span>}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', color: col }}>{fmtPct(c.mean_excess_pct, 2, true)}</td>
                  <td>
                    <div style={{ position: 'relative', height: 10 }}>
                      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'var(--border-bright)' }} />
                      <div style={{ position: 'absolute', top: 4, height: 2, left: `${pos(c.ci_low_pct)}%`, width: `${Math.max(1, pos(c.ci_high_pct) - pos(c.ci_low_pct))}%`, background: col, opacity: 0.6 }} />
                      <div style={{ position: 'absolute', top: 2, width: 6, height: 6, borderRadius: '50%', transform: 'translateX(-50%)', left: `${pos(c.mean_excess_pct)}%`, background: col }} />
                    </div>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11 }}>{Math.round(c.hit_rate * 100)}%</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--cream-mute)' }}>{c.n}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.7 }}>
        Each row is the sector&apos;s return minus {index.benchmark}&apos;s after past occurrences. A sector is marked notable when the range of its average
        excludes its usual behaviour. With this many rows, some look notable by chance alone
        {share !== undefined ? ` (${Math.round(share * 100)}% of rows at this horizon are notable; chance alone gives about 5%)` : ''}, so treat single rows with care.
      </p>
    </div>
  );
}

export function GeoPage() {
  const [geo, setGeo] = useState<Geopolitics | null | undefined>(undefined);
  const [index, setIndex] = useState<Analogues | null>(null);

  useEffect(() => {
    let alive = true;
    api.geopolitics(10).then(g => { if (alive) setGeo(g); });
    api.analogues().then(a => { if (alive) setIndex(a); });
    return () => { alive = false; };
  }, []);

  const exposure = geo?.exposure ?? [];
  const top = exposure.find(e => e.effect === 'risk') ?? exposure[0];
  const maxSens = Math.max(1, ...exposure.map(e => e.sensitivity));

  return (
    <div>
      <div className="geo-alert" style={{ marginBottom: 20 }}>
        <div className="geo-alert-icon">⚠</div>
        <div style={{ flex: 1 }}>
          <div className="geo-alert-top">
            <div className="pulse-dot" />
            <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '1.8px', textTransform: 'uppercase', color: 'var(--red)' }}>What world news is about today</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--cream)', marginBottom: 5, letterSpacing: '-0.3px', fontFamily: 'var(--f-display)' }}>
            {geo === undefined ? 'Reading the news…' : top ? `${top.sector}: ${top.label.toLowerCase()} in ${top.headlines} recent headlines` : 'Headlines aren’t available right now'}
          </div>
          {exposure.length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.65 }}>
              Affects: {exposure.slice(0, 6).map((e, i) => (
                <span key={e.sector}>{i > 0 && ' · '}<strong style={{ color: effectColor(e.effect) }}>{e.sector}</strong></span>
              ))}
              {geo && <> &nbsp;·&nbsp; Updated {timeAgo(geo.updated_at)}</>}
            </div>
          )}
        </div>
      </div>

      <div className="split" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 12, marginBottom: 14 }}>
        <div className="card" style={{ minWidth: 0 }}>
          <div className="ct">Global pulse feed</div>
          {geo?.events.map(e => {
            const fx = e.sectors[0];
            const cls = fx?.effect === 'risk' ? 'ev-red' : fx?.effect === 'haven' ? 'ev-gold' : '';
            return (
              <a key={e.link} href={e.link} target="_blank" rel="noopener noreferrer" className={`event-card ${cls}`} style={{ display: 'block', marginBottom: 8, textDecoration: 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
                  {e.topics.slice(0, 2).map(t => <span key={t} className="pill pill-gold">{t}</span>)}
                  {e.sectors.slice(0, 3).map(s => <span key={s.sector} className={effectPill(s.effect)} style={{ fontSize: 8 }}>{s.sector}: {s.label}</span>)}
                </div>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--cream)', lineHeight: 1.55 }}>{e.title}</div>
                <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 4 }}>{e.source} · {timeAgo(e.published)}</div>
              </a>
            );
          })}
          {geo === null && <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>The news feed isn&apos;t reachable right now.</div>}
        </div>

        <div className="card">
          <div className="ct">Sector exposure · recent news</div>
          {exposure.map(g => (
            <div key={g.sector} style={{ marginBottom: 14 }} title={`${g.headlines} headlines`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--cream)' }}>{g.sector}</span>
                <span className={effectPill(g.effect)} style={{ fontSize: 8, minWidth: 72, justifyContent: 'center' }}>{g.label}</span>
              </div>
              <div style={{ height: 4, background: 'rgba(201,168,76,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: `${(g.sensitivity / maxSens) * 100}%`, height: '100%', borderRadius: 2, background: effectColor(g.effect), opacity: 0.8 }} />
              </div>
            </div>
          ))}
          <p style={{ fontSize: 9, color: 'var(--cream-mute)', lineHeight: 1.6 }}>
            Bars show each sector&apos;s share of recent macro and world headlines; labels come from keyword rules on the headlines, so read the stories themselves.
          </p>
        </div>
      </div>

      {index ? <AnalogueTable index={index} /> : (
        <div className="card" style={{ fontSize: 11, color: 'var(--cream-mute)' }}>The historical event study isn&apos;t available right now.</div>
      )}
    </div>
  );
}
