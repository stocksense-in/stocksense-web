'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useId, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { Change } from '@/components/ui/Change';
import { inr } from '@/lib/format';

interface Result {
  symbol: string;
  name: string;
  price: number | null;
  changePct: number | null;
}

/** Find any NSE stock by symbol or name. Press "/" anywhere to focus. */
export function SearchBox() {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
      if (e.key === '/' && !typing) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        setResults(await res.json());
        setActive(0);
      } catch {
        /* aborted by the next keystroke */
      }
    }, 120);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const go = (symbol: string) => {
    setOpen(false);
    setQuery('');
    inputRef.current?.blur();
    router.push(`/stocks/${encodeURIComponent(symbol)}`);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[active]) {
      go(results[active].symbol);
    } else if (e.key === 'Escape') {
      inputRef.current?.blur();
    }
  };

  const showList = open && query.trim().length > 0;

  return (
    <div className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" />
      <input
        ref={inputRef}
        className="field h-9 bg-surface pr-9 pl-9"
        placeholder="Search 2,600 NSE stocks"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-label="Search stocks"
      />
      <kbd className="pointer-events-none absolute top-1/2 right-2.5 hidden -translate-y-1/2 rounded border border-rule px-1.5 text-[0.7333rem] text-ink-3 sm:block">
        /
      </kbd>
      {showList && (
        <ul id={listId} role="listbox" className="absolute top-full right-0 left-0 z-40 mt-1.5 overflow-hidden rounded-[10px] border border-rule bg-surface py-1 shadow-pop">
          {results.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-ink-3">No NSE stock matches “{query}”.</li>
          ) : (
            results.map((r, i) => (
              <li
                key={r.symbol}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault();
                  go(r.symbol);
                }}
                onMouseEnter={() => setActive(i)}
                className={`flex cursor-pointer items-center gap-3 px-3 py-2 ${i === active ? 'bg-sunken' : ''}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-ink">{r.symbol}</div>
                  <div className="truncate text-[0.8rem] text-ink-3">{r.name}</div>
                </div>
                <div className="text-right text-sm">
                  <div className="num text-ink">{inr(r.price)}</div>
                  <Change value={r.changePct} className="text-[0.8rem]" />
                </div>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
