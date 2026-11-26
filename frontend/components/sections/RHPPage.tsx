'use client';
import { useEffect, useRef, useState } from 'react';
import type { ScanResult, ScanRule } from '@/lib/api';
import { api, scanProspectus } from '@/lib/api';

const SEVERITY: Record<string, [string, string, string]> = {
  high: ['pill pill-r', 'High', 'var(--red)'],
  medium: ['pill pill-gold', 'Medium', 'var(--gold)'],
  low: ['pill pill-g', 'Low', 'var(--green)'],
};
const ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };
const MAX_MB = 60;

export function RHPPage() {
  const [rules, setRules] = useState<ScanRule[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const ctl = new AbortController();
    api.prospectusRules(ctl.signal).then(r => { if (r) setRules(r); });
    return () => ctl.abort();
  }, []);

  const scan = async (f: File) => {
    setFile(f);
    setResult(null);
    setError(null);
    if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') { setError('Choose the prospectus as a PDF file.'); return; }
    if (f.size > MAX_MB * 1024 * 1024) { setError(`That file is over ${MAX_MB} MB. Upload the DRHP or RHP PDF only.`); return; }
    setScanning(true);
    const out = await scanProspectus(f);
    setScanning(false);
    if ('result' in out) setResult(out.result);
    else setError(out.error);
  };

  const findings = result ? [...result.findings].sort((a, b) => (ORDER[a.severity] ?? 3) - (ORDER[b.severity] ?? 3)) : [];
  const highs = findings.filter(f => f.severity === 'high').length;

  return (
    <div className="split" style={{ display: 'grid', gridTemplateColumns: '340px minmax(0,1fr)', gap: 12 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div
          className="rhp-upload"
          onClick={() => !scanning && input.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f && !scanning) scan(f); }}
          style={{ opacity: scanning ? 0.6 : 1, cursor: scanning ? 'wait' : 'pointer', borderColor: dragOver ? 'var(--gold)' : undefined }}
          role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && input.current?.click()}
        >
          <input ref={input} type="file" accept="application/pdf,.pdf" style={{ display: 'none' }}
            onChange={e => { const f = e.target.files?.[0]; if (f) scan(f); e.target.value = ''; }} />
          <div style={{ fontSize: 40, marginBottom: 14 }}>📄</div>
          <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 8, color: 'var(--cream)', letterSpacing: '-0.3px', fontFamily: 'var(--f-display)' }}>Upload a DRHP or RHP</div>
          <div style={{ fontSize: 11, color: 'var(--cream-dim)', lineHeight: 1.7, maxWidth: 260, margin: '0 auto 18px' }}>
            Drop the prospectus PDF here or click to choose it. The scanner reads every page and quotes what it finds. The file isn&apos;t stored.
          </div>
          <button className="btn-gold-main" style={{ width: '100%' }} disabled={scanning}
            onClick={e => { e.stopPropagation(); input.current?.click(); }}>
            <span>{scanning ? 'Reading the prospectus…' : 'Choose a PDF ↗'}</span>
          </button>
          <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 10 }}>
            Prospectuses are on SEBI&apos;s site under Filings → Public issues, and on NSE&apos;s IPO pages.
          </div>
        </div>

        <div className="card">
          <div className="ct">What the scanner looks for</div>
          {rules.map(r => (
            <div key={r.id} style={{ padding: '8px 0', borderBottom: '1px solid rgba(201,168,76,0.04)' }} title={r.why}>
              <div style={{ fontSize: 11, color: 'var(--cream)' }}>{r.title}</div>
              <div style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 3, lineHeight: 1.5 }}>{r.why}</div>
            </div>
          ))}
          {!rules.length && <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>The scanner isn&apos;t reachable right now.</div>}
        </div>
      </div>

      <div style={{ minWidth: 0 }}>
        {error && (
          <div className="card card-alert" style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--cream)' }}>{error}</div>
          </div>
        )}

        {!result && !error && (
          <div style={{ minHeight: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--s1)', border: '1px solid var(--border)', borderRadius: 8, padding: '40px 24px', gap: 12 }}>
            <div style={{ fontSize: 44, opacity: 0.12, color: 'var(--gold)' }}>◈</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--cream-mute)' }}>{scanning ? `Reading ${file?.name ?? 'the prospectus'}…` : 'Upload a prospectus to scan it'}</div>
            <div style={{ fontSize: 11, color: 'var(--cream-mute)', textAlign: 'center', maxWidth: 320, lineHeight: 1.65, opacity: 0.75 }}>
              {scanning ? 'Large prospectuses take up to a minute.' : 'You get the warning signs it contains, each with the page and the sentence it came from, so you can check them yourself.'}
            </div>
          </div>
        )}

        {result && (
          <div>
            <div style={{ position: 'relative', overflow: 'hidden', background: 'var(--s1)', border: '1px solid var(--border-bright)', borderRadius: 8, padding: '18px 22px', marginBottom: 14 }}>
              <div className="ct" style={{ marginBottom: 5 }}>Prospectus scan · {file?.name}</div>
              <div style={{ fontSize: 12, color: 'var(--cream-dim)', lineHeight: 1.7 }}>
                Read <strong style={{ color: 'var(--cream)' }}>{result.pages} pages</strong> and found{' '}
                <strong style={{ color: 'var(--cream)' }}>{findings.length} warning sign{findings.length === 1 ? '' : 's'}</strong>
                {highs > 0 && <>, <span style={{ color: 'var(--red)' }}>{highs} of them serious</span></>}.
                {' '}{result.clear.length} other checks found nothing.
              </div>
              <div style={{ fontSize: 10, color: 'var(--cream-mute)', marginTop: 8 }}>
                Every prospectus lists risks; what matters is how large they are for this company. Read the quoted pages before deciding anything.
              </div>
            </div>

            {findings.length > 0 && (
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="ct">Warning signs, with where they appear</div>
                {findings.map((f, i) => {
                  const [cls, label, color] = SEVERITY[f.severity] ?? SEVERITY.medium;
                  return (
                    <div key={f.id} style={{ padding: '13px 0 13px 12px', borderBottom: i < findings.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none', borderLeft: `2px solid ${color}`, marginBottom: 2 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 5, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--cream)' }}>{f.title}</span>
                        <span className={cls}>{label}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--cream)', lineHeight: 1.65 }}>{f.summary}</div>
                      <div style={{ fontSize: 10.5, color: 'var(--cream-mute)', lineHeight: 1.6, marginTop: 4 }}>Why it matters: {f.why}</div>
                      {f.evidence.slice(0, 3).map(ev => (
                        <blockquote key={ev.page + ev.quote.slice(0, 20)} style={{ margin: '8px 0 0', padding: '6px 10px', background: 'rgba(201,168,76,0.04)', borderRadius: 4, fontSize: 10.5, color: 'var(--cream-dim)', lineHeight: 1.6 }}>
                          <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--gold)', marginRight: 8 }}>p.{ev.page}</span>
                          “{ev.quote}”
                        </blockquote>
                      ))}
                    </div>
                  );
                })}
              </div>
            )}

            {result.clear.length > 0 && (
              <div className="card">
                <div className="ct">Checked and not found</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {result.clear.map(c => <span key={c.id} className="pill pill-b">{c.title}</span>)}
                </div>
                <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 10, lineHeight: 1.6 }}>
                  Not found means the scanner&apos;s patterns didn&apos;t match; it isn&apos;t proof the risk is absent.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
