'use client';
import { useEffect, useRef, useState } from 'react';
import type { Page } from '@/lib/types';
import type { StockOut } from '@/lib/api';
import { api } from '@/lib/api';
import type { CompanyTab } from '@/components/sections/AnalysisPage';

// Terminal-style commands. Company functions follow a symbol: "INFY FA".
const PAGE_COMMANDS: { codes: string[]; page: Page; label: string }[] = [
  { codes: ['DASH', 'HOME', 'WL'], page: 'dashboard', label: 'Market dashboard and your watchlist' },
  { codes: ['EQS', 'SCR'], page: 'screener', label: 'Screener' },
  { codes: ['IPO'], page: 'ipo', label: 'IPOs open and coming up' },
  { codes: ['GEO'], page: 'geo', label: 'Geopolitics engine' },
  { codes: ['RHP'], page: 'rhp', label: 'Prospectus scanner' },
  { codes: ['PT'], page: 'paper', label: 'Paper trading' },
  { codes: ['ANA', 'STOCK'], page: 'analysis', label: 'Stock analysis' },
  { codes: ['LEARN', 'HELP'], page: 'learn', label: 'Learn the metrics' },
  { codes: ['NICHE'], page: 'premium', label: 'Niche stocks' },
  { codes: ['PROF'], page: 'profile', label: 'Investment profile' },
];

const FUNCTIONS: { codes: string[]; tab: CompanyTab; label: string }[] = [
  { codes: ['', 'DES', 'SCORE'], tab: 'score', label: 'Score breakdown' },
  { codes: ['FA'], tab: 'financials', label: 'Financials' },
  { codes: ['HDS'], tab: 'holders', label: 'Holders' },
  { codes: ['DVD'], tab: 'dividends', label: 'Dividends' },
  { codes: ['EV', 'EVTS'], tab: 'events', label: 'Filings & insider trades' },
  { codes: ['RV', 'PEERS'], tab: 'peers', label: 'Peers' },
  { codes: ['N', 'NEWS'], tab: 'news', label: 'News' },
];

interface Option {
  key: string;
  code: string;
  label: string;
  hint?: string;
  run: () => void;
}

export function CommandBar({ onPage, onCompany }: { onPage: (p: Page) => void; onCompany: (symbol: string, tab: CompanyTab) => void }) {
  const [text, setText] = useState('');
  const [open, setOpen] = useState(false);
  const [found, setFound] = useState<{ q: string; items: StockOut[] }>({ q: '', items: [] });
  const [hi, setHi] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  // "/" or Ctrl/Cmd+K focuses the bar from anywhere that isn't a text field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
      if ((e.key === '/' && !typing) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        input.current?.focus();
        input.current?.select();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const parts = text.trim().toUpperCase().split(/\s+/).filter(Boolean);
  const head = parts[0] ?? '';
  const fn = parts.slice(1).join(' ');
  const func = FUNCTIONS.find(f => f.codes.includes(fn));

  // Look up companies for the first word.
  useEffect(() => {
    if (head.length < 1) return;
    const t = setTimeout(async () => {
      const r = await api.search(head, undefined);
      setFound({ q: head, items: r ?? [] });
      setHi(0);
    }, 150);
    return () => clearTimeout(t);
  }, [head]);

  const close = () => { setText(''); setOpen(false); (document.activeElement as HTMLElement | null)?.blur(); };

  const options: Option[] = [];
  if (!head) {
    PAGE_COMMANDS.forEach(p => options.push({ key: p.page, code: p.codes[0], label: p.label, run: () => { onPage(p.page); close(); } }));
  } else {
    if (parts.length === 1) {
      PAGE_COMMANDS.filter(p => p.codes.some(c => c.startsWith(head))).forEach(p =>
        options.push({ key: 'p-' + p.page, code: p.codes.find(c => c.startsWith(head)) ?? p.codes[0], label: p.label, run: () => { onPage(p.page); close(); } }));
    }
    const companies = found.q === head ? found.items : [];
    // An exact symbol goes first.
    const sorted = [...companies].sort((a, b) => Number(b.symbol === head) - Number(a.symbol === head));
    const targets = func ? [func] : fn ? [] : FUNCTIONS.slice(0, 1);
    sorted.slice(0, 6).forEach(c => targets.forEach(f =>
      options.push({
        key: `c-${c.symbol}-${f.tab}`, code: `${c.symbol}${f.codes[0] ? ' ' + f.codes[0] : ''}`,
        label: c.name ?? c.symbol, hint: f.label, run: () => { onCompany(c.symbol, f.tab); close(); },
      })));
    if (parts.length >= 2 && !func) {
      FUNCTIONS.filter(f => f.codes.some(c => c && c.startsWith(fn))).forEach(f => {
        const c = sorted[0];
        if (c) options.push({ key: `f-${f.tab}`, code: `${c.symbol} ${f.codes.find(x => x && x.startsWith(fn))}`, label: c.name ?? c.symbol, hint: f.label, run: () => { onCompany(c.symbol, f.tab); close(); } });
      });
    }
  }
  const sel = Math.min(hi, Math.max(0, options.length - 1));

  return (
    <div style={{ position: 'relative', flex: '0 1 380px', minWidth: 180 }}>
      <input
        ref={input}
        value={text}
        onChange={e => { setText(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={e => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setHi(h => Math.min(h + 1, options.length - 1)); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(h - 1, 0)); }
          else if (e.key === 'Enter') { e.preventDefault(); options[sel]?.run(); }
          else if (e.key === 'Escape') close();
        }}
        placeholder="Command — INFY, INFY FA, IPO, GEO…   ( / )"
        aria-label="Command bar"
        spellCheck={false}
        style={{ width: '100%', background: 'var(--s2)', border: '1px solid var(--border)', borderRadius: 5, padding: '6px 10px', fontSize: 11, color: 'var(--cream)', fontFamily: 'var(--f-mono)', outline: 'none' }}
      />
      {open && (
        <div role="listbox" style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4, zIndex: 50, background: 'var(--s2)', border: '1px solid var(--border-bright)', borderRadius: 6, overflow: 'hidden', minWidth: 300 }}>
          {options.map((o, i) => (
            <div key={o.key} role="option" aria-selected={i === sel} onMouseEnter={() => setHi(i)} onMouseDown={e => { e.preventDefault(); o.run(); }}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', cursor: 'pointer', background: i === sel ? 'rgba(201,168,76,0.08)' : 'transparent' }}>
              <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10.5, color: 'var(--gold)', minWidth: 92 }}>{o.code}</span>
              <span style={{ fontSize: 11, color: 'var(--cream)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.label}</span>
              {o.hint && <span style={{ fontSize: 9, color: 'var(--cream-mute)', textTransform: 'uppercase', letterSpacing: '1px' }}>{o.hint}</span>}
            </div>
          ))}
          {head && options.length === 0 && (
            <div style={{ padding: '8px 10px', fontSize: 11, color: 'var(--cream-mute)' }}>No company or command matches “{text.trim()}”.</div>
          )}
          <div style={{ padding: '7px 10px', borderTop: '1px solid var(--border)', fontSize: 9, color: 'var(--cream-mute)', lineHeight: 1.7, fontFamily: 'var(--f-mono)' }}>
            SYMBOL then: FA financials · HDS holders · DVD dividends · EV filings · RV peers · N news &nbsp;|&nbsp; ↑↓ choose · Enter open · Esc close
          </div>
        </div>
      )}
    </div>
  );
}
