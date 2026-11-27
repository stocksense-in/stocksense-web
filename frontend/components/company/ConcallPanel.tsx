'use client';
import type { Concall, CallQuote } from '@/lib/api';

const day = (s: string) => new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

const STATUS: Record<string, { label: string; pill: string; plain: string }> = {
  changed: { label: 'Changed', pill: 'pill pill-gold', plain: 'the figures differ from the previous call' },
  new: { label: 'New', pill: 'pill pill-g', plain: 'not given on the previous call' },
  repeated: { label: 'Repeated', pill: 'pill pill-b', plain: 'the same figures as the previous call' },
  dropped: { label: 'Not repeated', pill: 'pill pill-r', plain: 'given last time, not found this time' },
};

function Quote({ q, source }: { q: CallQuote; source: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <p style={{ fontSize: 12, color: 'var(--cream)', lineHeight: 1.6, margin: 0 }}>“{q.text}”</p>
      <div style={{ fontSize: 9, color: 'var(--cream-mute)', fontFamily: 'var(--f-mono)', marginTop: 3 }}>
        {q.topic && <span style={{ textTransform: 'uppercase', letterSpacing: '1px', marginRight: 8 }}>{q.topic}</span>}
        <a href={`${source}#page=${q.page}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--gold)' }}>page {q.page}</a>
      </div>
    </div>
  );
}

/** The latest earnings call in the company's own words: what it reported, what it expects, what changed. */
export function ConcallPanel({ c, name }: { c: Concall; name: string }) {
  const changed = c.changes.filter(x => x.status !== 'repeated');
  return (
    <div className="g2" style={{ alignItems: 'start' }}>
      <div>
        <div className="card">
          <div className="ct">What {name} reported · call filed {day(c.filed)}</div>
          {c.highlights.length
            ? c.highlights.map((q, i) => <Quote key={i} q={q} source={c.source} />)
            : <p className="mc-plain">No results with figures found in the prepared remarks.</p>}
        </div>
        <div className="card" style={{ marginTop: 12 }}>
          <div className="ct">What management expects</div>
          {c.guidance.length
            ? c.guidance.map((q, i) => <Quote key={i} q={q} source={c.source} />)
            : <p className="mc-plain">No forward-looking figures on this call. Many companies don&apos;t give numeric guidance; listen to the call for their view.</p>}
          <p className="mc-plain" style={{ marginTop: 6 }}>Guidance is what the company hopes for, not a promise. Compare it with what it delivers over the next few quarters.</p>
        </div>
      </div>
      <div>
        {c.previous_filed && (
          <div className="card">
            <div className="ct">Guidance against the call filed {day(c.previous_filed)}</div>
            {c.changes.length === 0 && <p className="mc-plain">Neither call gave figures to compare.</p>}
            {[...changed, ...c.changes.filter(x => x.status === 'repeated')].map((x, i) => {
              const st = STATUS[x.status] ?? STATUS.changed;
              return (
                <div key={i} style={{ marginBottom: 14, paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                    <span className={st.pill} title={st.plain}>{st.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--cream-dim)', textTransform: 'capitalize' }}>{x.topic}</span>
                  </div>
                  {x.before && x.status !== 'repeated' && (
                    <div style={{ opacity: 0.7 }}>
                      <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginBottom: 2 }}>BEFORE</div>
                      <p style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.6, margin: '0 0 6px' }}>“{x.before.text}” <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9 }}>p{x.before.page}</span></p>
                    </div>
                  )}
                  {x.now && <Quote q={x.now} source={c.source} />}
                </div>
              );
            })}
          </div>
        )}
        <p style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10, lineHeight: 1.6 }}>
          Every line is quoted from the transcript {name} filed with NSE (<a href={c.source} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--gold)' }}>PDF</a>), picked by rules
          rather than written by StockSense: sentences with figures from the company&apos;s own speakers. Read the call for context.
        </p>
      </div>
    </div>
  );
}
