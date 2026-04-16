'use client';
import React from 'react';
import { Page } from '@/lib/types';
import { PAGE_TITLES, C } from '@/lib/constants';

export function Topbar({ activePage, setInApp }: { activePage: Page; setInApp: (val: boolean) => void }) {
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <div className="topbar">
      <div className="tb-title">{PAGE_TITLES[activePage]}</div>
      <div className="tb-r">
        <div className="live-badge">
          <div className="live-dot" />NSE Live
        </div>
        <div style={{ fontSize: 10, color: C.ink3 }}>{today}</div>
        <button className="btn-ghost" style={{ padding: '5px 12px', fontSize: 10 }} onClick={() => setInApp(false)}>← Home</button>
      </div>
    </div>
  );
}
