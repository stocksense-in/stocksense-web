# Layouts

## Root layout: fonts (IBM Plex Sans, Bricolage Grotesque), html/body

### `frontend/app/layout.tsx`

```tsx
import type { Metadata } from 'next';
import { Bricolage_Grotesque, IBM_Plex_Sans } from 'next/font/google';
import './globals.css';

const plex = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex',
  display: 'swap',
});

const bricolage = Bricolage_Grotesque({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-bricolage',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'StockSense — Know what you’re buying', template: '%s · StockSense' },
  description:
    'Every NSE stock scored on six fundamentals against its own sector, explained in plain language. Plus IPO scoring, geopolitical risk and a paper-trading simulator.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={`${plex.variable} ${bricolage.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

## App shell: sidebar + sticky header (search, index bar) + main container

### `frontend/app/(app)/layout.tsx`

```tsx
import { IndexBar } from '@/components/shell/IndexBar';
import { SearchBox } from '@/components/shell/SearchBox';
import { MobileNav, Sidebar } from '@/components/shell/Sidebar';

/** Shell for every signed-in page: sidebar, search, index bar. The landing page (/) sits outside it. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-rule bg-paper/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-3 px-4 sm:px-6">
            <MobileNav />
            <SearchBox />
          </div>
          <div className="mx-auto max-w-[1240px] px-4 pb-2.5 sm:px-6">
            <IndexBar />
          </div>
        </header>
        <main className="mx-auto max-w-[1240px] px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
```

## Desktop sidebar nav + mobile slide-over nav

### `frontend/components/shell/Sidebar.tsx`

```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Logo } from './Logo';
import { NAV } from './nav';

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-6" aria-label="Main">
      {NAV.map(({ group, items }) => (
        <div key={group}>
          <div className="mb-1.5 px-3 text-[0.8rem] text-ink-3">{group}</div>
          <ul className="flex flex-col gap-0.5">
            {items.map(({ href, label, icon: Icon, pro }) => {
              const active = pathname === href || pathname.startsWith(href + '/');
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? 'page' : undefined}
                    className={`flex h-9 items-center gap-2.5 rounded-[7px] px-3 text-[0.9333rem] transition-colors ${
                      active ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--color-rule)]' : 'text-ink-2 hover:bg-surface/60 hover:text-ink'
                    }`}
                  >
                    <Icon className={`size-4 ${active ? 'text-brand' : 'text-ink-3'}`} strokeWidth={1.75} />
                    {label}
                    {pro && <span className="ml-auto rounded bg-brand-wash px-1.5 text-[0.7333rem] font-medium text-brand-ink">Pro</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** Fixed sidebar, desktop only. */
export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-rule px-3 py-5 lg:flex">
      <Link href="/" className="mb-7 px-3">
        <Logo />
      </Link>
      <NavLinks />
      <p className="mt-auto px-3 text-[0.8rem] leading-relaxed text-ink-3">
        For learning, not advice. StockSense is not a SEBI-registered adviser.
      </p>
    </aside>
  );
}

/** Menu button + slide-over navigation for small screens. */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button className="btn btn-quiet btn-sm -ml-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
        <Menu className="size-5" />
      </button>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-ink/30 [animation:fade-in_150ms]" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col bg-paper px-3 py-5 shadow-pop [animation:sheet-in_180ms_ease-out]">
            <div className="mb-6 flex items-center justify-between px-3">
              <Logo />
              <button className="btn btn-quiet btn-sm" onClick={() => setOpen(false)} aria-label="Close menu">
                <X className="size-5" />
              </button>
            </div>
            <NavLinks onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
```

## Nav items and groups

### `frontend/components/shell/nav.ts`

```ts
import {
  ChartLine,
  Earth,
  FileSearch,
  LayoutDashboard,
  Rocket,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Wallet,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  pro?: boolean;
}

/** The app's sections, in sidebar order. Add a page here to put it in the navigation. */
export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: 'Markets',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/stocks', label: 'Stocks', icon: ChartLine },
      { href: '/screener', label: 'Screener', icon: SlidersHorizontal },
    ],
  },
  {
    group: 'Research',
    items: [
      { href: '/ipo', label: 'IPOs', icon: Rocket },
      { href: '/rhp-analyser', label: 'Prospectus scanner', icon: FileSearch },
      { href: '/geopolitics', label: 'Geopolitics', icon: Earth },
    ],
  },
  {
    group: 'You',
    items: [
      { href: '/paper-trading', label: 'Paper trading', icon: Wallet },
      { href: '/profile', label: 'Investor profile', icon: UserRound },
      { href: '/premium', label: 'Matched picks', icon: Sparkles, pro: true },
    ],
  },
];
```

## Stock search combobox

### `frontend/components/shell/SearchBox.tsx`

```tsx
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
    if (!query.trim()) return;
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
      setActive((i) => Math.min(i + 1, visible.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && visible[active]) {
      go(visible[active].symbol);
    } else if (e.key === 'Escape') {
      inputRef.current?.blur();
    }
  };

  const showList = open && query.trim().length > 0;
  const visible = query.trim() ? results : [];

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
          {visible.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-ink-3">No NSE stock matches “{query}”.</li>
          ) : (
            visible.map((r, i) => (
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
```

## NIFTY/SENSEX/BANKNIFTY/VIX strip

### `frontend/components/shell/IndexBar.tsx`

```tsx
import { Change } from '@/components/ui/Change';
import { getIndices, getLastUpdated } from '@/lib/data/queries';
import { usingSnapshot } from '@/lib/data/source';
import { ago, num } from '@/lib/format';

/** NIFTY, SENSEX, BANK NIFTY, VIX across the top of every app page. */
export async function IndexBar() {
  const [indices, updated] = await Promise.all([getIndices(), getLastUpdated()]);
  return (
    <div className="flex items-center gap-6 overflow-x-auto text-sm [scrollbar-width:none]">
      {indices.map((q) => (
        <div key={q.symbol} className="flex shrink-0 items-baseline gap-2">
          <span className="text-ink-3">{q.label}</span>
          <span className="num font-medium text-ink">{num(q.price)}</span>
          <Change value={q.changePct} className="text-[0.8667rem]" />
        </div>
      ))}
      <span className="ml-auto shrink-0 text-[0.8rem] text-ink-3">
        {usingSnapshot ? 'Offline snapshot' : `Prices ${ago(updated)}`}
      </span>
    </div>
  );
}
```

## Logo mark + wordmark

### `frontend/components/shell/Logo.tsx`

```tsx
/**
 * The mark is a tiny metric gauge — a ruler, its ideal range, and a reading —
 * the same device used for every metric in the product.
 */
export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden>
        <rect width="22" height="22" rx="6" fill="var(--color-ink)" />
        <rect x="4" y="10" width="14" height="2" rx="1" fill="#ffffff" opacity="0.35" />
        <rect x="8" y="9" width="6" height="4" rx="1" fill="#ffffff" opacity="0.55" />
        <circle cx="12.5" cy="11" r="2.6" fill="var(--color-brand)" stroke="var(--color-ink)" strokeWidth="1.2" />
      </svg>
      <span className="font-display text-[1.1rem] font-semibold tracking-[-0.02em] text-ink">StockSense</span>
    </span>
  );
}
```

