'use client';
// The watchlist lives in this browser (localStorage) until accounts exist (M4.4).
// useSyncExternalStore keeps every component — and other tabs — in step.
import { useCallback, useSyncExternalStore } from 'react';

const KEY = 'stocksense.watchlist';
const EVENT = 'stocksense:watchlist';
const MAX = 50;
const EMPTY: string[] = [];

let lastRaw: string | null = null;
let lastList: string[] = EMPTY;

function snapshot(): string[] {
  let raw: string | null = null;
  try { raw = localStorage.getItem(KEY); } catch { return EMPTY; }
  if (raw === lastRaw) return lastList;
  lastRaw = raw;
  try {
    const parsed = JSON.parse(raw ?? '[]');
    lastList = Array.isArray(parsed) ? parsed.filter((s): s is string => typeof s === 'string').slice(0, MAX) : EMPTY;
  } catch {
    lastList = EMPTY;
  }
  return lastList;
}

function subscribe(onChange: () => void) {
  window.addEventListener('storage', onChange);
  window.addEventListener(EVENT, onChange);
  return () => {
    window.removeEventListener('storage', onChange);
    window.removeEventListener(EVENT, onChange);
  };
}

function save(list: string[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch { /* private window or storage blocked: the change lasts until reload */ }
  window.dispatchEvent(new Event(EVENT));
}

export function useWatchlist() {
  const list = useSyncExternalStore(subscribe, snapshot, () => EMPTY);
  const toggle = useCallback((symbol: string) => {
    const s = symbol.toUpperCase();
    const now = snapshot();
    save(now.includes(s) ? now.filter(x => x !== s) : [...now, s]);
  }, []);
  const has = useCallback((symbol: string) => list.includes(symbol.toUpperCase()), [list]);
  return { list, has, toggle, full: list.length >= MAX };
}
