'use client';
import React from 'react';
import { Page } from '@/lib/types';
import { NAV_ITEMS } from '@/lib/constants';

export function Sidebar({ activePage, navTo }: { activePage: Page; navTo: (p: Page) => void }) {
  const navSections = [
    { label: 'Core', items: NAV_ITEMS.slice(0, 4) },
    { label: 'Intelligence', items: NAV_ITEMS.slice(4, 7) },
    { label: 'Learning', items: NAV_ITEMS.slice(7) },
  ];

  return (
    <div className="sidebar">
      <div className="sb-brand">
        <div className="sb-logo">Stock<span>Sense</span></div>
        <div className="sb-tier">India Equities Platform</div>
      </div>
      <div className="sb-user">
        <div className="sb-av">VS</div>
        <div>
          <div className="sb-un">Vikram S.</div>
          <div className="sb-us">Free Member</div>
        </div>
      </div>
      <div className="sb-nav">
        {navSections.map(({ label, items }) => (
          <div key={label}>
            <div className="nav-sec">{label}</div>
            {items.map(item => (
              <div key={item.id} className={`ni${activePage === item.id ? ' active' : ''}`} onClick={() => navTo(item.id)}>
                <span className="ni-ic">{item.icon}</span>
                {item.label}
                {item.pro && <span className="pro-tag">PRO</span>}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="sb-bottom">
        <div className="sb-promo">
          <div className="sb-promo-t">Go Sovereign</div>
          <div className="sb-promo-d">Niche picks, geopolitics alerts &amp; IPO intelligence tailored to you.</div>
          <button className="sb-promo-btn" onClick={() => navTo('premium')}>Upgrade to Pro ↗</button>
        </div>
      </div>
    </div>
  );
}
