'use client';

import { useRef, useState } from 'react';
import { FileSearch, Upload } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { RULE_LIST, type ScanResult, type Severity } from '@/lib/rhp';
import type { Status } from '@/lib/types';

const TONE: Record<Severity, Status> = { high: 'concern', medium: 'watch', low: 'neutral' };
const LABEL: Record<Severity, string> = { high: 'High', medium: 'Medium', low: 'Note' };

type Phase = { kind: 'idle' } | { kind: 'scanning'; name: string } | { kind: 'done'; name: string; result: ScanResult } | { kind: 'error'; message: string };

export function ProspectusScanner() {
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' });
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const scan = async (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setPhase({ kind: 'error', message: 'Choose a PDF file — the DRHP or RHP as published on the SEBI or exchange website.' });
      return;
    }
    setPhase({ kind: 'scanning', name: file.name });
    const body = new FormData();
    body.append('file', file);
    try {
      const res = await fetch('/api/rhp', { method: 'POST', body });
      const json = await res.json();
      setPhase(res.ok ? { kind: 'done', name: file.name, result: json } : { kind: 'error', message: json.error ?? 'The scan failed.' });
    } catch {
      setPhase({ kind: 'error', message: 'Couldn’t reach the scanner. Check your connection and try again.' });
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
      <div className="space-y-6">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            scan(e.dataTransfer.files[0]);
          }}
          className={`panel flex cursor-pointer flex-col items-center px-6 py-10 text-center transition-colors ${dragging ? 'border-brand bg-brand-wash' : 'border-dashed hover:border-ink-3'}`}
        >
          <Upload className="size-6 text-ink-3" strokeWidth={1.75} />
          <span className="mt-3 font-medium text-ink">Drop a prospectus PDF here</span>
          <span className="mt-1 text-sm text-ink-3">or select a file. DRHP or RHP, up to 60 MB.</span>
          <input
            ref={input}
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            onChange={(e) => {
              scan(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
        </label>

        <section className="panel p-5" aria-labelledby="checks-heading">
          <h2 id="checks-heading" className="panel-title mb-2">What it looks for</h2>
          <ul className="divide-y divide-rule-2">
            {RULE_LIST.map((r) => (
              <li key={r.id} className="py-2.5">
                <div className="text-sm font-medium text-ink">{r.title}</div>
                <div className="text-[0.8rem] text-ink-3">{r.why}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel min-h-[24rem]" aria-live="polite">
        {phase.kind === 'idle' && (
          <div className="flex h-full flex-col items-center justify-center px-8 py-16 text-center">
            <FileSearch className="size-8 text-ink-3" strokeWidth={1.5} />
            <p className="mt-4 max-w-sm font-medium text-ink">Upload an IPO prospectus to see its red flags.</p>
            <p className="mt-1 max-w-sm text-sm text-ink-2">
              Find the PDF on the company’s IPO page at sebi.gov.in, nseindia.com or bseindia.com. The file is read on our server and not stored.
            </p>
          </div>
        )}

        {phase.kind === 'scanning' && (
          <div className="flex h-full flex-col items-center justify-center px-8 py-16 text-center">
            <span className="size-6 animate-spin rounded-full border-2 border-rule border-t-brand" aria-hidden />
            <p className="mt-4 font-medium text-ink">Reading {phase.name}</p>
            <p className="mt-1 text-sm text-ink-3">A 400-page prospectus takes about 20 seconds.</p>
          </div>
        )}

        {phase.kind === 'error' && (
          <div className="flex h-full flex-col items-center justify-center px-8 py-16 text-center">
            <p className="font-medium text-ink">{phase.message}</p>
            <button className="btn btn-secondary btn-sm mt-4" onClick={() => input.current?.click()}>Choose another file</button>
          </div>
        )}

        {phase.kind === 'done' && (
          <div>
            <header className="border-b border-rule px-5 py-4">
              <h2 className="panel-title truncate">{phase.name}</h2>
              <p className="num text-sm text-ink-3">
                {phase.result.pages} pages read, {phase.result.findings.length} {phase.result.findings.length === 1 ? 'finding' : 'findings'}
              </p>
            </header>
            {phase.result.findings.length === 0 ? (
              <p className="px-5 py-10 text-center text-ink-2">None of the patterns matched. Still read the Risk Factors chapter — wording varies between prospectuses.</p>
            ) : (
              <ol className="divide-y divide-rule-2">
                {phase.result.findings.map((f) => (
                  <li key={f.id} className="px-5 py-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={TONE[f.severity]}>{LABEL[f.severity]}</StatusBadge>
                      <h3 className="font-medium text-ink">{f.title}</h3>
                    </div>
                    <p className="mt-2 text-ink">{f.summary}</p>
                    <p className="mt-1 text-sm text-ink-2">{f.why}</p>
                    <ul className="mt-3 space-y-2">
                      {f.evidence.map((e, i) => (
                        <li key={i} className="rounded-md border-l-2 border-rule bg-sunken px-3 py-2 text-[0.8667rem] text-ink-2">
                          <span className="num mr-2 font-medium text-ink-3">p. {e.page}</span>
                          {e.quote}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
            {phase.result.clear.length > 0 && (
              <div className="border-t border-rule px-5 py-4 text-sm text-ink-3">
                Nothing found for: {phase.result.clear.map((c) => c.title.toLowerCase()).join('; ')}.
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
