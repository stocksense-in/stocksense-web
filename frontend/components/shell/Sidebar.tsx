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
                    className={`relative flex h-9 items-center gap-2.5 rounded-[10px] px-3 text-[0.9333rem] transition-colors ${
                      active
                        ? 'bg-brand-wash font-medium text-ink before:absolute before:inset-y-2 before:-left-3 before:w-0.5 before:rounded-full before:bg-brand'
                        : 'text-ink-2 hover:bg-raised hover:text-ink'
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
    <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-rule bg-surface/70 px-3 py-5 backdrop-blur lg:flex">
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
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] [animation:fade-in_150ms]" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-rule bg-surface px-3 py-5 shadow-pop [animation:sheet-in_180ms_ease-out]">
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
