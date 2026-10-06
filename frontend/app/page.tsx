'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Page } from '@/lib/types';
import { PAGE_TITLES, NAV_ITEMS } from '@/lib/constants';
import { DashboardPage } from '@/components/sections/DashboardPage';
import { AnalysisPage } from '@/components/sections/AnalysisPage';
import { IPOPage } from '@/components/sections/IPOPage';
import { ScreenerPage } from '@/components/sections/ScreenerPage';
import { GeoPage } from '@/components/sections/GeoPage';
import { PremiumPage } from '@/components/sections/PremiumPage';
import { ProfilePage } from '@/components/sections/ProfilePage';
import { PaperTradingPage } from '@/components/sections/PaperTradingPage';
import { RHPPage } from '@/components/sections/RHPPage';
import { useRouter } from 'next/navigation';
import { Constellation } from '@/components/landing/Constellation';
import { CustomCursor } from '@/components/landing/CustomCursor';

/* ══ TIMELINE DATA ══ */
const STEPS = [
  {
    num: '01', icon: '◈', tag: 'DISCOVERY',
    title: 'Search any stock or IPO',
    body: 'Type a ticker like INFY, HDFCBANK, or an upcoming IPO name. StockSense instantly pulls real-time price data, sector classification, and 52-week range — giving you a complete identity card for every listed company on NSE and BSE.',
    features: ['2,800+ NSE/BSE stocks indexed', 'Live price feeds with <3s latency', 'Auto-complete with sector tags'],
  },
  {
    num: '02', icon: '▦', tag: 'ANALYSIS',
    title: 'See the full metric breakdown',
    body: 'Every fundamental metric — PE Ratio, Return on Equity, Debt/Equity, Net Profit Margin, Promoter Holding, and Revenue CAGR — is plotted on an ideal-range gauge calibrated specifically for that stock\'s sector. A banking stock\'s D/E of 9× is normal; the same ratio in IT is a red flag. StockSense knows the difference.',
    features: ['6 institutional-grade metrics per stock', 'Sector-calibrated ideal zones', 'Click any metric for deep-dive intelligence'],
  },
  {
    num: '03', icon: '◉', tag: 'GEOPOLITICS',
    title: 'Get live geopolitical context',
    body: 'Most retail investors ignore geopolitics until it\'s too late. StockSense\'s Geopolitics Engine maps real-time global events — Iran tensions, Hormuz closure risk, OPEC output cuts, India-US trade pacts — directly to affected Indian sectors. Defence rallies on conflict. Aviation bleeds on crude spikes. You see it before the market prices it in.',
    features: ['8 sectors tracked against 14 geo-risk sources', 'Historical precedent matching (2020 COVID, 2022 Russia)', 'Sector risk matrix updated every 2 hours'],
  },
  {
    num: '04', icon: '★', tag: 'VERDICT',
    title: 'Read the AI verdict',
    body: 'StockSense synthesizes all 6 metrics, sector context, and geopolitical overlay into a single institutional-grade verdict: Strong Buy, Moderate, or Risky. But we don\'t just give you a label — we show the plain-language reasoning behind it. "PE is 24× against a sector ideal of 18–28× — fairly valued. ROE at 31% is top-decile. Zero debt concern. Verdict: Strong Buy."',
    features: ['Weighted scoring: Fundamentals 60% + Geo 20% + Sentiment 20%', 'Plain-language reasoning for every verdict', 'Click-through to 3-layer metric intelligence'],
  },
  {
    num: '05', icon: '◎', tag: 'SIMULATION',
    title: 'Paper trade before risking capital',
    body: 'Start with virtual ₹1,00,000 and trade in simulated market conditions. Set stop-losses, track P&L, and learn position sizing — all without risking a single real rupee. Our coach system guides you through learning missions: execute your first trade, survive a red day, diversify across 3 sectors, and watch a stop-loss trigger. By the time you deploy real capital, you\'ve already built conviction.',
    features: ['Virtual ₹1,00,000 with realistic brokerage', '6 learning missions with progress tracking', 'AI coach insights on concentration and profit-booking'],
  },
];

/* ══ TYPEWRITER DATA ══ */
const FEATURES = [
  { cat: 'STOCK REPORT CARD', txt: 'See exactly where every metric sits — ideal vs actual, in plain language. PE, ROE, D/E explained for your sector.' },
  { cat: 'GEOPOLITICS RISK ENGINE', txt: 'Iran tensions? Oil spike? We map live global events to Indian sector risk before the market prices it in.' },
  { cat: 'IPO ANALYSER', txt: 'GMP, QIB, HNI, fundamentals — scored into one verdict. Subscribe, Risky, or Avoid. No more FOMO.' },
  { cat: 'PAPER TRADING', txt: 'Trade with virtual ₹1,00,000 in real market conditions. Learn stop-losses and sizing before it costs you.' },
  { cat: 'RHP SCANNER', txt: 'Drop any DRHP. Our AI reads 300+ pages and flags related-party risks, litigation, and revenue concentration.' },
];

export default function StockSensePage({
  initialPage
}: {
  initialPage?: Page
} = {}) {
  const router = useRouter();
  const [inApp, setInApp] = useState(!!initialPage);
  const [activePage, setActivePage] = useState<Page>(initialPage ?? 'dashboard');
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  const navTo = (page: Page) => {
    setActivePage(page);
    const routeMap: Record<Page, string> = {
      dashboard: '/dashboard', analysis: '/analysis', ipo: '/ipo',
      paper: '/paper-trading', rhp: '/rhp-analyser', geo: '/geopolitics-engine',
      screener: '/screener', premium: '/premium', profile: '/profile', mf: '/mf',
    };
    router.push(routeMap[page]);
  };

  const enter = (page: Page) => {
    setInApp(true);
    navTo(page);
  };

  const navSections = [
    { label: 'Core', items: NAV_ITEMS.slice(0, 4) },
    { label: 'Intelligence', items: NAV_ITEMS.slice(4, 7) },
    { label: 'Learning', items: NAV_ITEMS.slice(7) },
  ];

  /* ── Typewriter ── */
  const [twCat, setTwCat] = useState(FEATURES[0].cat);
  const [twDisp, setTwDisp] = useState('');
  const twRef = useRef({ fi: 0, ci: 0, phase: 'type' as 'type' | 'pause' | 'erase', pauseAt: 0 });

  useEffect(() => {
    if (inApp) return;
    let raf: number;
    let last = 0;
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const s = twRef.current;
      const spd = s.phase === 'erase' ? 15 : 33;
      if (now - last < spd) return;
      last = now;
      const full = FEATURES[s.fi].txt;
      if (s.phase === 'type') {
        if (s.ci < full.length) { s.ci++; }
        else { s.phase = 'pause'; s.pauseAt = now; }
      } else if (s.phase === 'pause') {
        if (now - s.pauseAt > 2300) s.phase = 'erase';
      } else {
        if (s.ci > 0) s.ci--;
        else { s.fi = (s.fi + 1) % FEATURES.length; s.phase = 'type'; setTwCat(FEATURES[s.fi].cat); }
      }
      setTwDisp(full.slice(0, s.ci));
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [inApp]);

  /* ── Timeline IntersectionObserver ── */
  const timelineRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (inApp || !timelineRef.current) return;
    // Small delay to ensure DOM is fully rendered after hydration
    const timer = setTimeout(() => {
      if (!timelineRef.current) return;
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) e.target.classList.add('visible');
        });
      }, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });
      const steps = timelineRef.current.querySelectorAll('.timeline-step');
      steps.forEach(s => observer.observe(s));
      return () => observer.disconnect();
    }, 100);
    return () => clearTimeout(timer);
  }, [inApp]);

  /* ── Scroll indicator fade ── */
  useEffect(() => {
    if (inApp) return;
    const handler = () => {
      const el = document.querySelector('.scroll-indicator') as HTMLElement | null;
      if (el) { const p = window.scrollY / window.innerHeight; el.style.opacity = String(1 - Math.min(p * 2, 1)); }
    };
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, [inApp]);

  return (
    <>
      {/* ── LANDING ── */}
      {!inApp && (
        <div style={{ background: 'var(--bg)', minHeight: '100vh', position: 'relative', overflow: 'hidden' }}>
          {/* Constellation canvas background — fixed, full viewport */}
          <Constellation />
          {/* Custom gold dot + ring cursor */}
          <CustomCursor />
          <nav className="land-nav">
            <div className="logo">Stock<span className="logo-gold">Sense</span></div>
            <div className="nav-links">
              <a onClick={() => enter('analysis')}>Analysis</a>
              <a onClick={() => enter('ipo')}>IPO Scorer</a>
              <a onClick={() => enter('geo')}>Geopolitics</a>
              <a onClick={() => enter('paper')}>Paper Trading</a>
            </div>
            <div className="nav-right">
              <button className="btn-ghost-nav">Sign in</button>
              <button className="btn-nav-cta" onClick={() => enter('premium')}><span>Get Premium →</span></button>
            </div>
          </nav>

          <section className="hero">
            <div className="hero-inner">
              <div className="eyebrow"><div className="eye-dot" />India&apos;s Geopolitical Intelligence Platform</div>
              <div className="headline-block"><span className="hl-main">The Market Moves on</span></div>
              <div className="tagline-line">
                <span className="hl-intelligence">Intelligence</span>
                <span className="sep-comma">,</span>
                <span className="hl-not">not</span>
                <span className="hl-luck">Luck.</span>
              </div>
              <div className="div-rule" />
              <p className="sub">Real fundamentals, live geopolitics, institutional tools —<br />built for Indian retail investors.</p>
              <div className="tw-wrap">
                <div className="tw-category">{twCat}</div>
                <div className="tw-text">{twDisp}<span className="tw-cursor" /></div>
              </div>
              <div className="btns">
                <button className="btn-primary" onClick={() => enter('paper')}><span>Start Paper Trading ↗</span></button>
                <button className="btn-outline" onClick={() => enter('analysis')}><span>Analyse a Stock →</span></button>
              </div>
            </div>
            <div className="scroll-indicator"><div className="scroll-line" /><span>Scroll</span></div>
          </section>

          {/* ── TIMELINE ── */}
          <section className="timeline-section" style={{ position: 'relative', zIndex: 10 }}>
            <div className="timeline-inner" ref={timelineRef}>
              <div className="timeline-line" />
              <div className="timeline-eyebrow">HOW IT WORKS</div>
              <div className="timeline-title">Five steps to investing<br />with intelligence.</div>

              {STEPS.map((s, i) => (
                <div key={s.num} className="timeline-step" style={{ transitionDelay: `${i * 0.12}s` }}>
                  <div className="step-dot">
                    <span className="step-dot-icon">{s.icon}</span>
                    <span className="step-dot-num">{s.num}</span>
                  </div>
                  <div className="step-content">
                    <div className="step-tag">{s.tag}</div>
                    <div className="step-title">{s.title}</div>
                    <div className="step-body">{s.body}</div>
                    {s.features && (
                      <div className="step-features">
                        {s.features.map((f, fi) => (
                          <div key={fi} className="step-feature">
                            <span className="step-feature-dot" />
                            <span>{f}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              <div className="timeline-cta">
                <button className="btn-primary" onClick={() => enter('analysis')}><span>Start for free →</span></button>
                <div className="timeline-cta-note">No account needed to analyse your first stock.</div>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ── APP SHELL ── */}
      {inApp && (
        <div className="app-shell">
          <div className="sidebar">
            <div className="sb-brand">
              <div className="sb-logo">Stock<span>Sense</span></div>
              <div className="sb-tier">India Equities Platform</div>
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
                <div className="sb-promo-t">Upgrade to Sovereign</div>
                <div className="sb-promo-d">Niche picks, geo-adjusted alerts &amp; IPO intelligence tailored to your profile.</div>
                <button className="sb-promo-btn" onClick={() => navTo('premium')}>Go Premium ↗</button>
              </div>
              <div className="sb-user">
                <div className="sb-av">VS</div>
                <div><div className="sb-un">Vikram S.</div><div className="sb-us">Free Member</div></div>
              </div>
            </div>
          </div>

          <div className="main-area">
            <div className="topbar">
              <div className="tb-left">
                <div className="tb-title">{PAGE_TITLES[activePage]}</div>
              </div>
              <div className="tb-r">
                <div className="live-badge"><div className="live-dot" />NSE Live</div>
                <div className="tb-date">{today}</div>
                <button className="btn-ghost" style={{ padding: '5px 12px', fontSize: 10 }} onClick={() => setInApp(false)}>← Home</button>
              </div>
            </div>
            <div className="content">
              {activePage === 'dashboard'  && <DashboardPage onNav={navTo} />}
              {activePage === 'analysis'   && <AnalysisPage />}
              {activePage === 'ipo'        && <IPOPage />}
              {activePage === 'screener'   && <ScreenerPage />}
              {activePage === 'geo'        && <GeoPage />}
              {activePage === 'premium'    && <PremiumPage onNav={navTo} />}
              {activePage === 'profile'    && <ProfilePage onNav={navTo} />}
              {activePage === 'paper'      && <PaperTradingPage />}
              {activePage === 'rhp'        && <RHPPage />}
            </div>
          </div>
        </div>
      )}
    </>
  );
}