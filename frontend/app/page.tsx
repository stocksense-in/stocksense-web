'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Page, StockData, Holding, IPO, MetricKey, MetricMeta, Sector } from '@/lib/types';
import { SD, MM, IPOS, SCREENER, GEO_SECTORS, GEO_EVENTS, NICHE, PT_STOCKS, PAGE_TITLES, NAV_ITEMS, C } from '@/lib/constants';
import { pillClass, getMetricStatus, scoreColor, formatINR } from '@/lib/utils';
import { supabase } from '@/lib/supabase';
import { Pill } from '@/components/ui/Pill';
import { StatRow } from '@/components/ui/StatRow';
import { SectionDiv } from '@/components/ui/SectionDiv';
import { CandleChart } from '@/components/cards/CandleChart';
import { MetricCard } from '@/components/cards/MetricCard';
import { DashboardPage } from '@/components/sections/DashboardPage';
import { AnalysisPage } from '@/components/sections/AnalysisPage';
import { IPOPage } from '@/components/sections/IPOPage';
import { ScreenerPage } from '@/components/sections/ScreenerPage';
import { GeoPage } from '@/components/sections/GeoPage';
import { PremiumPage } from '@/components/sections/PremiumPage';
import { ProfilePage } from '@/components/sections/ProfilePage';
import { PaperTradingPage } from '@/components/sections/PaperTradingPage';
import { RHPPage } from '@/components/sections/RHPPage';
import { useRouter } from 'next/navigation'


export default function StockSensePage({ 
  initialPage 
}: { 
  initialPage?: Page 
} = {}) {
const router = useRouter()

  const [inApp, setInApp] = useState(!!initialPage);
  const [activePage, setActivePage] = useState<Page>(initialPage ?? 'dashboard');
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  const navTo = (page: Page) => {
  setActivePage(page);
  const routeMap: Record<Page, string> = {
    dashboard: '/dashboard',
    analysis: '/analysis',
    ipo: '/ipo',
    paper: '/paper-trading',
    rhp: '/rhp-analyser',
    geo: '/geopolitics-engine',
    screener: '/screener',
    premium: '/premium',
    profile: '/profile',
    mf: '/mf',
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



  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
        :root{
          --bg:#060810;--s1:#090E1A;--s2:#0D1322;--s3:#12192E;--s4:#18223C;--s5:#1E2B4A;
          --blue:#00C8F5;--blue-d:rgba(0,200,245,.07);--blue-m:rgba(0,200,245,.13);--blue-g:rgba(0,200,245,.28);
          --gold:#C9991E;--gold-d:rgba(201,153,30,.07);--gold-m:rgba(201,153,30,.15);
          --green:#00D97E;--green-d:rgba(0,217,126,.08);
          --red:#F04438;--red-d:rgba(240,68,56,.08);
          --ink:#DCE5F8;--ink2:#60789E;--ink3:#2E4266;--ink4:#162038;
          --border:rgba(255,255,255,.07);--border-a:rgba(0,200,245,.32);--border-g:rgba(201,153,30,.22);
          --sh1:0 1px 2px rgba(0,0,0,.5),0 2px 6px rgba(0,0,0,.3);
          --sh2:0 2px 4px rgba(0,0,0,.55),0 6px 24px rgba(0,0,0,.35);
          --sh3:0 4px 8px rgba(0,0,0,.65),0 12px 40px rgba(0,0,0,.45);
          --r1:6px;--r2:10px;--r3:14px;--r4:22px;
          --f:'Inter',system-ui,sans-serif;--mono:'JetBrains Mono','Fira Code',monospace;
          --sidebar:224px;--topbar:54px;
        }
        html,body{background:var(--bg);color:var(--ink);font-family:var(--f);font-size:13px;line-height:1.5;}
        body::before{content:'';position:fixed;inset:0;background-image:radial-gradient(ellipse 80% 50% at 50% -10%,rgba(0,200,245,.07),transparent),linear-gradient(rgba(0,200,245,.013) 1px,transparent 1px),linear-gradient(90deg,rgba(0,200,245,.013) 1px,transparent 1px);background-size:100% 100%,44px 44px,44px 44px;pointer-events:none;z-index:0;}
        body::after{content:'';position:fixed;inset:0;opacity:.022;pointer-events:none;z-index:1;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E");background-repeat:repeat;background-size:180px 180px;}

        /* ── LANDING ── */
        .land-nav{position:fixed;top:0;left:0;right:0;padding:0 52px;height:60px;display:flex;align-items:center;justify-content:space-between;background:rgba(6,8,16,.82);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid var(--border);z-index:10;}
        .land-logo{display:flex;align-items:center;gap:8px;font-size:16px;font-weight:800;color:var(--ink);letter-spacing:-.4px;}
        .land-logo::before{content:'◈';font-size:14px;color:var(--blue);}
        .land-logo span{color:var(--blue);}
        .land-links{display:flex;gap:28px;align-items:center;}
        .land-links a{font-size:12px;color:var(--ink2);cursor:pointer;transition:color .15s;font-weight:500;text-decoration:none;letter-spacing:.01em;}
        .land-links a:hover{color:var(--ink);}
        .land-links a.gold{color:var(--gold);font-weight:600;}
        .land-cta{background:var(--blue);color:#000;border:none;border-radius:var(--r2);padding:7px 18px;font-family:var(--f);font-size:12px;font-weight:700;cursor:pointer;letter-spacing:.02em;transition:opacity .15s;}
        .land-cta:hover{opacity:.88;}
        .hero{position:relative;text-align:center;max-width:820px;padding-top:80px;z-index:2;}
        .hero-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:10px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--blue);border:1px solid rgba(0,200,245,.2);padding:6px 16px;border-radius:var(--r4);margin-bottom:32px;background:rgba(0,200,245,.06);}
        .badge-dot{width:5px;height:5px;border-radius:50%;background:var(--blue);animation:pulse 2.4s infinite;}
        @keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,200,245,.5)}50%{opacity:.5;box-shadow:0 0 0 6px rgba(0,200,245,0)}}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
        .hero h1{font-size:58px;font-weight:800;line-height:1.04;letter-spacing:-1.2px;margin-bottom:22px;color:var(--ink);}
        .hero h1 .b{background:linear-gradient(135deg,var(--blue),rgba(0,200,245,.7));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .hero h1 .g{background:linear-gradient(135deg,var(--gold),rgba(201,153,30,.7));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .hero p{font-size:16px;color:var(--ink2);line-height:1.75;max-width:500px;margin:0 auto 40px;font-weight:400;}
        .hero-btns{display:flex;gap:12px;justify-content:center;margin-bottom:64px;flex-wrap:wrap;}
        .btn-glow{background:var(--blue);color:#000;border:none;border-radius:var(--r2);padding:14px 32px;font-family:var(--f);font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 0 20px rgba(0,200,245,.35),0 0 60px rgba(0,200,245,.1);transition:box-shadow .2s,transform .15s;letter-spacing:.02em;}
        .btn-glow:hover{box-shadow:0 0 30px rgba(0,200,245,.55),0 0 80px rgba(0,200,245,.16);transform:translateY(-1px);}
        .btn-gold-border{background:transparent;color:var(--gold);border:1px solid rgba(201,153,30,.4);border-radius:var(--r2);padding:14px 32px;font-family:var(--f);font-size:13px;font-weight:600;cursor:pointer;transition:background .15s,border-color .15s;}
        .btn-gold-border:hover{background:var(--gold-d);border-color:rgba(201,153,30,.65);}
        .feat-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;width:100%;max-width:880px;}
        .feat-card{border:1px solid var(--border-g);border-radius:var(--r3);padding:18px 14px;background:linear-gradient(160deg,rgba(201,153,30,.07),rgba(201,153,30,.02));cursor:pointer;transition:border-color .18s,transform .15s,background .18s;text-align:center;position:relative;overflow:hidden;}
        .feat-card::before{content:'';position:absolute;top:0;left:25%;right:25%;height:1px;background:linear-gradient(90deg,transparent,rgba(201,153,30,.4),transparent);}
        .feat-card:hover{border-color:rgba(201,153,30,.4);transform:translateY(-3px);background:linear-gradient(160deg,rgba(201,153,30,.1),rgba(201,153,30,.04));}
        .feat-icon{font-size:22px;margin-bottom:10px;display:block;}
        .feat-name{font-size:11px;font-weight:700;color:var(--gold);letter-spacing:.3px;margin-bottom:5px;}
        .feat-desc{font-size:10px;color:var(--ink3);line-height:1.45;}

        /* ── APP SHELL ── */
        .app-shell{display:flex;height:100vh;overflow:hidden;position:relative;z-index:1;}
        .sidebar{width:var(--sidebar);background:var(--s1);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}
        .sb-brand{padding:0 18px;height:var(--topbar);display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--border);flex-shrink:0;}
        .sb-brand-icon{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,rgba(0,200,245,.2),rgba(0,200,245,.05));border:1px solid rgba(0,200,245,.2);display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--blue);flex-shrink:0;}
        .sb-logo{font-size:15px;font-weight:800;color:var(--ink);letter-spacing:-.4px;}
        .sb-logo span{color:var(--blue);}
        .sb-nav{flex:1;padding:10px 0;overflow-y:auto;scrollbar-width:none;}
        .sb-nav::-webkit-scrollbar{display:none;}
        .nav-sec{font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);padding:16px 18px 6px;}
        .ni{display:flex;align-items:center;gap:10px;padding:9px 18px;cursor:pointer;color:var(--ink2);font-size:12.5px;font-weight:500;transition:color .12s,background .12s;border-left:2px solid transparent;user-select:none;margin:1px 0;letter-spacing:.01em;}
        .ni:hover{color:var(--ink);background:rgba(255,255,255,.04);}
        .ni.active{color:var(--ink);background:rgba(0,200,245,.09);border-left-color:var(--blue);font-weight:700;}
        .ni-ic{width:16px;text-align:center;font-size:13px;opacity:.55;flex-shrink:0;}
        .ni.active .ni-ic{opacity:1;color:var(--blue);}
        .pro-tag{font-size:8px;font-weight:700;letter-spacing:.4px;background:linear-gradient(135deg,#C9991E,#7A5B08);color:#fff;padding:2px 7px;border-radius:3px;margin-left:auto;}
        .sb-bottom{flex-shrink:0;border-top:1px solid var(--border);}
        .sb-user{display:flex;align-items:center;gap:10px;padding:14px 18px;}
        .sb-av{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,rgba(0,200,245,.18),rgba(0,200,245,.05));border:1px solid rgba(0,200,245,.2);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--blue);flex-shrink:0;}
        .sb-un{font-size:12px;font-weight:600;color:var(--ink);}
        .sb-us{font-size:9px;color:var(--ink3);margin-top:1px;}
        .sb-promo{margin:0 12px 12px;background:linear-gradient(135deg,rgba(201,153,30,.1),rgba(201,153,30,.04));border:1px solid var(--border-g);border-radius:var(--r2);padding:12px 14px;position:relative;overflow:hidden;}
        .sb-promo::before{content:'';position:absolute;top:0;left:10%;right:10%;height:1px;background:linear-gradient(90deg,transparent,rgba(201,153,30,.4),transparent);}
        .sb-promo-t{font-size:10px;font-weight:700;color:var(--gold);margin-bottom:4px;}
        .sb-promo-d{font-size:9px;color:var(--ink2);line-height:1.5;margin-bottom:10px;}
        .sb-promo-btn{width:100%;background:var(--gold);color:#000;border:none;border-radius:var(--r1);padding:8px;font-family:var(--f);font-size:10px;font-weight:700;cursor:pointer;transition:opacity .15s;}
        .sb-promo-btn:hover{opacity:.88;}
        .main-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
        .topbar{height:var(--topbar);background:var(--s1);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 24px;flex-shrink:0;gap:16px;}
        .tb-left{display:flex;align-items:center;gap:12px;min-width:0;}
        .tb-title{font-size:15px;font-weight:700;color:var(--ink);letter-spacing:-.3px;white-space:nowrap;}
        .tb-sep{width:1px;height:16px;background:var(--border);flex-shrink:0;}
        .tb-sub{font-size:11px;color:var(--ink3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        .tb-r{display:flex;align-items:center;gap:10px;flex-shrink:0;}
        .live-badge{display:flex;align-items:center;gap:5px;font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--green);background:rgba(0,217,126,.08);border:1px solid rgba(0,217,126,.15);border-radius:var(--r4);padding:4px 10px;}
        .live-dot{width:5px;height:5px;border-radius:50%;background:var(--green);box-shadow:0 0 5px var(--green);animation:pulse 2s infinite;}
        .tb-date{font-size:10px;color:var(--ink3);font-family:var(--mono);}
        .content{flex:1;overflow-y:auto;padding:24px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.06) transparent;}
        .content::-webkit-scrollbar{width:3px;}
        .content::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:2px;}

        /* ── UTILITIES ── */
        .g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
        .g3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
        .g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
        .card{background:var(--s1);border:1px solid var(--border);border-radius:var(--r3);padding:18px 20px;box-shadow:var(--sh2);position:relative;overflow:hidden;}
        .card::before{content:'';position:absolute;top:0;left:15%;right:15%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent);pointer-events:none;}
        .card-blue{border-color:rgba(0,200,245,.16);background:linear-gradient(160deg,rgba(0,200,245,.09),rgba(0,200,245,.03));}
        .card-blue::before{background:linear-gradient(90deg,transparent,rgba(0,200,245,.2),transparent);}
        .card-gold{border-color:rgba(201,153,30,.18);background:linear-gradient(160deg,rgba(201,153,30,.1),rgba(201,153,30,.03));}
        .card-gold::before{background:linear-gradient(90deg,transparent,rgba(201,153,30,.3),transparent);}
        .card-green{border-color:rgba(0,217,126,.15);background:linear-gradient(160deg,rgba(0,217,126,.08),rgba(0,217,126,.02));}
        .card-red{border-color:rgba(240,68,56,.15);background:linear-gradient(160deg,rgba(240,68,56,.08),rgba(240,68,56,.02));}
        .ct{font-size:8px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:14px;}
        .bn{font-size:28px;font-weight:800;line-height:1;font-family:var(--mono);letter-spacing:-1px;}
        .bn-blue{color:var(--blue);}
        .bn-gold{color:var(--gold);}
        .bn-green{color:var(--green);}
        .stat-r{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05);}
        .stat-r:last-child{border-bottom:none;}
        .sl{font-size:11px;color:var(--ink2);}
        .sv{font-size:11px;font-weight:600;color:var(--ink);}
        .pill{display:inline-flex;align-items:center;font-size:8.5px;font-weight:700;letter-spacing:.6px;padding:2px 7px;border-radius:4px;text-transform:uppercase;white-space:nowrap;}
        .pill-g{background:rgba(0,217,126,.09);color:var(--green);border:1px solid rgba(0,217,126,.18);}
        .pill-r{background:rgba(240,68,56,.09);color:var(--red);border:1px solid rgba(240,68,56,.18);}
        .pill-b{background:var(--blue-d);color:var(--blue);border:1px solid rgba(0,200,245,.18);}
        .pill-gold{background:var(--gold-d);color:var(--gold);border:1px solid rgba(201,153,30,.18);}
        .bar-track{height:3px;background:var(--ink4);border-radius:2px;overflow:hidden;}
        .bar-fill{height:100%;border-radius:2px;transition:width .45s cubic-bezier(.4,0,.2,1);}
        .tbl{width:100%;border-collapse:collapse;}
        .tbl th{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);padding:9px 14px;text-align:left;border-bottom:1px solid var(--border);background:rgba(255,255,255,.015);}
        .tbl td{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.04);font-size:11.5px;vertical-align:middle;}
        .tbl tr:last-child td{border-bottom:none;}
        .tbl tbody tr:hover td{background:rgba(0,200,245,.04);}
        .sec-div{display:flex;align-items:center;gap:12px;margin:22px 0 14px;}
        .sec-div span{font-size:8px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);white-space:nowrap;}
        .sec-div hr{flex:1;border:none;border-top:1px solid var(--border);}
        .field-label{font-size:8.5px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:6px;}
        .fi{width:100%;background:var(--s2);border:1px solid var(--border);border-radius:var(--r2);padding:10px 13px;color:var(--ink);font-family:var(--f);font-size:12px;outline:none;transition:border-color .15s,box-shadow .15s;}
        .fi:focus{border-color:var(--border-a);box-shadow:0 0 0 3px rgba(0,200,245,.07);}
        .fi::placeholder{color:var(--ink3);}
        .btn-blue{background:var(--blue);color:#000;border:none;border-radius:var(--r2);padding:10px 22px;font-family:var(--f);font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 0 14px rgba(0,200,245,.22);transition:box-shadow .15s,transform .12s;letter-spacing:.02em;}
        .btn-blue:hover{box-shadow:0 0 24px rgba(0,200,245,.4);transform:translateY(-1px);}
        .btn-gold{background:transparent;color:var(--gold);border:1px solid rgba(201,153,30,.4);border-radius:var(--r2);padding:10px 22px;font-family:var(--f);font-size:12px;font-weight:600;cursor:pointer;transition:background .15s,border-color .15s;}
        .btn-gold:hover{background:var(--gold-d);border-color:rgba(201,153,30,.65);}
        .btn-ghost{background:transparent;color:var(--ink2);border:1px solid var(--border);border-radius:var(--r2);padding:8px 14px;font-family:var(--f);font-size:11px;cursor:pointer;transition:border-color .15s,color .15s;}
        .btn-ghost:hover{border-color:rgba(255,255,255,.12);color:var(--ink);}
        .seg-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;}
        .seg-btn{font-size:11px;font-weight:500;padding:7px 15px;border-radius:var(--r2);border:1px solid var(--border);color:var(--ink2);cursor:pointer;transition:all .15s;background:var(--s2);font-family:var(--f);}
        .seg-btn:hover{border-color:rgba(255,255,255,.1);color:var(--ink);}
        .seg-btn.active{background:var(--blue);color:#000;border-color:var(--blue);font-weight:700;box-shadow:0 0 10px rgba(0,200,245,.25);}
        .idx-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px;}
        .idx-card{background:var(--s1);border:1px solid var(--border);border-radius:var(--r2);padding:14px 16px;box-shadow:var(--sh1);transition:border-color .15s;position:relative;overflow:hidden;}
        .idx-card::before{content:'';position:absolute;top:0;left:10%;right:10%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);pointer-events:none;}
        .idx-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;border-radius:0 0 var(--r2) var(--r2);}
        .idx-card.bull::after{background:linear-gradient(90deg,transparent,rgba(0,217,126,.5),transparent);}
        .idx-card.bear::after{background:linear-gradient(90deg,transparent,rgba(240,68,56,.45),transparent);}
        .idx-name{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;}
        .idx-val{font-size:20px;font-weight:800;color:var(--ink);font-family:var(--mono);letter-spacing:-.5px;}
        .idx-chg{font-size:10px;font-weight:600;margin-top:5px;font-family:var(--mono);display:flex;align-items:center;gap:4px;}

        /* ── METRIC CARDS ── */
        .mc-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;width:100%;}
        .mc{background:var(--s1);border-radius:var(--r3);padding:18px;cursor:pointer;transition:transform .15s,background .15s,border-color .15s,box-shadow .15s;border:1px solid var(--border);width:100%;box-shadow:var(--sh2);position:relative;overflow:hidden;}
        .mc::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.06),transparent);}
        .mc:hover{background:var(--s2);transform:translateY(-2px);box-shadow:var(--sh3);border-color:rgba(255,255,255,.1);}
        .mc.open{background:var(--s2);border-color:var(--border-a);}
        .mc-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;}
        .mc-name{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);line-height:1;}
        .mc-status{display:flex;align-items:center;gap:5px;}
        .status-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
        .mc-val{font-size:32px;font-weight:800;color:var(--ink);line-height:1;margin-bottom:18px;letter-spacing:-1.5px;font-family:var(--mono);}
        .mc-val sup{font-size:13px;font-weight:400;letter-spacing:0;color:var(--ink2);vertical-align:baseline;margin-left:3px;font-family:var(--f);}
        .ideal-bar{margin-bottom:14px;}
        .ideal-bar-lbl{display:flex;justify-content:space-between;align-items:center;font-size:8.5px;color:var(--ink3);margin-bottom:7px;line-height:1;}
        .ideal-track{position:relative;height:4px;background:var(--ink4);border-radius:4px;overflow:visible;}
        .ideal-zone{position:absolute;top:0;height:100%;border-radius:4px;opacity:.3;}
        .ideal-needle{position:absolute;top:50%;transform:translate(-50%,-50%);width:10px;height:10px;border-radius:50%;border:2px solid var(--bg);z-index:2;transition:left .4s cubic-bezier(.4,0,.2,1);}
        .ideal-mid{position:absolute;top:-5px;width:1px;height:14px;background:rgba(255,255,255,.1);}
        .ideal-ann{display:flex;justify-content:space-between;align-items:center;margin-top:9px;}
        .mc-plain{font-size:11px;color:var(--ink2);line-height:1.7;margin:0;padding:0;}
        .mc-expand{border-top:1px solid rgba(255,255,255,.05);margin-top:14px;padding-top:14px;}
        .exp-body{font-size:11px;color:var(--ink);line-height:1.8;}
        .exp-rule{box-sizing:border-box;width:100%;margin-top:10px;padding:10px 14px;background:rgba(201,153,30,.04);border-left:2px solid var(--gold);font-size:10px;color:var(--ink2);line-height:1.75;border-radius:0 var(--r1) var(--r1) 0;}
        .exp-verd{margin-top:10px;font-size:12px;font-weight:700;font-style:italic;}

        /* ── CANDLESTICK ── */
        .chart-wrap{position:relative;background:var(--s2);border:1px solid var(--border);border-radius:var(--r3);padding:18px;margin-bottom:14px;overflow:hidden;box-shadow:var(--sh2);}
        .candles{display:flex;align-items:flex-end;gap:3px;height:130px;padding-bottom:34px;}
        .candle-g{display:flex;flex-direction:column;align-items:center;flex:1;}
        .wick{width:1.5px;background:var(--ink3);border-radius:1px;}
        .body-c{width:75%;border-radius:2px;}
        .buy-zone{position:absolute;bottom:0;left:0;right:0;height:34px;background:linear-gradient(transparent,rgba(201,153,30,.06));border-top:1px solid rgba(201,153,30,.16);}
        .buy-zone-lbl{position:absolute;bottom:10px;left:18px;font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--gold);display:flex;align-items:center;gap:6px;}
        .buy-zone-dot{width:5px;height:5px;border-radius:50%;background:var(--gold);box-shadow:0 0 6px rgba(201,153,30,.6);}
        .chart-grid-lines{position:absolute;top:18px;left:18px;right:18px;bottom:34px;display:flex;flex-direction:column;justify-content:space-between;pointer-events:none;}
        .chart-grid-line{height:1px;background:rgba(0,200,245,.03);}

        /* ── IPO ── */
        .ipo-card{background:var(--s1);border:1px solid var(--border);border-radius:var(--r2);padding:14px 16px;cursor:pointer;transition:border-color .15s,background .15s,transform .12s;margin-bottom:8px;box-shadow:var(--sh1);}
        .ipo-card:hover{background:var(--s2);border-color:rgba(255,255,255,.1);transform:translateX(2px);}
        .ipo-card.sel{background:var(--s2);border-color:var(--border-a);}

        /* ── GEO ── */
        .geo-alert{background:linear-gradient(135deg,rgba(240,68,56,.07),rgba(240,68,56,.02));border:1px solid rgba(240,68,56,.16);border-radius:var(--r3);padding:18px 20px;margin-bottom:18px;display:flex;align-items:flex-start;gap:16px;}
        .geo-alert-icon{width:36px;height:36px;border-radius:10px;background:rgba(240,68,56,.12);border:1px solid rgba(240,68,56,.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px;}
        .geo-alert-top{display:flex;align-items:center;gap:8px;margin-bottom:5px;}
        .pulse-dot{width:7px;height:7px;border-radius:50%;background:var(--red);box-shadow:0 0 7px var(--red);animation:pulse 1.5s infinite;flex-shrink:0;}
        .event-card{border:1px solid var(--border);border-radius:var(--r2);padding:13px 15px;margin-bottom:7px;cursor:pointer;transition:border-color .15s,background .15s;background:var(--s1);}
        .event-card:hover{border-color:rgba(255,255,255,.1);background:var(--s2);}
        .event-card.ev-gold{border-color:rgba(201,153,30,.18);background:rgba(201,153,30,.04);}
        .event-card.ev-gold:hover{border-color:rgba(201,153,30,.32);}
        .event-card.ev-red{border-color:rgba(240,68,56,.14);background:rgba(240,68,56,.03);}
        .event-card.ev-red:hover{border-color:rgba(240,68,56,.26);}

        /* ── NICHE / PREMIUM ── */
        .niche-card{position:relative;background:var(--s1);border:1px solid var(--border-g);border-radius:var(--r3);padding:18px 20px;cursor:pointer;transition:border-color .15s,background .15s,transform .12s;overflow:hidden;box-shadow:var(--sh1);}
        .niche-card::before{content:'';position:absolute;top:0;left:20%;right:20%;height:1px;background:linear-gradient(90deg,transparent,rgba(201,153,30,.5),transparent);}
        .niche-card:hover{border-color:rgba(201,153,30,.35);background:rgba(201,153,30,.04);transform:translateY(-2px);}
        .risk-match{position:absolute;top:14px;right:14px;font-size:8.5px;font-weight:700;padding:3px 9px;border-radius:var(--r1);letter-spacing:.4px;}

        /* ── PAPER TRADING ── */
        .sim-badge{display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--blue);background:var(--blue-d);border:1px solid rgba(0,200,245,.15);border-radius:var(--r4);padding:5px 12px;}
        .sim-dot{width:5px;height:5px;border-radius:50%;background:var(--blue);animation:pulse 2s infinite;}
        .nudge{background:rgba(201,153,30,.05);border:1px solid rgba(201,153,30,.15);border-radius:var(--r2);padding:11px 14px;font-size:10px;color:var(--gold);line-height:1.6;}
        .mission-card{background:var(--s2);border:1px solid var(--border);border-radius:var(--r2);padding:15px 16px;cursor:pointer;transition:border-color .15s,background .15s;}
        .mission-card.done{border-color:rgba(0,217,126,.2);background:rgba(0,217,126,.03);}
        .mission-card:hover{border-color:rgba(255,255,255,.1);}
        .m-ic{width:26px;height:26px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;margin-bottom:9px;}
        .m-ic-blue{background:var(--blue-d);color:var(--blue);border:1px solid rgba(0,200,245,.14);}
        .m-ic-green{background:rgba(0,217,126,.08);color:var(--green);border:1px solid rgba(0,217,126,.16);}
        .m-ic-gold{background:var(--gold-d);color:var(--gold);border:1px solid rgba(201,153,30,.16);}
        .sparkline{display:flex;align-items:flex-end;gap:2px;height:24px;}
        .spark-b{flex:1;border-radius:1px 1px 0 0;min-height:2px;}

        /* ── PROFILE ── */
        .profile-step{background:var(--s1);border:1px solid var(--border);border-radius:var(--r3);padding:20px 22px;margin-bottom:12px;box-shadow:var(--sh1);}
        .ps-num{width:28px;height:28px;border-radius:8px;background:var(--blue-d);border:1px solid rgba(0,200,245,.16);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--blue);margin-bottom:12px;font-family:var(--mono);}
        .range-input{width:100%;accent-color:var(--blue);}

        /* ── RHP ── */
        .rhp-upload{border:2px dashed rgba(0,200,245,.13);border-radius:var(--r3);padding:36px 24px;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;background:linear-gradient(160deg,rgba(0,200,245,.05),rgba(0,200,245,.015));}
        .rhp-upload:hover{border-color:rgba(0,200,245,.3);background:rgba(0,200,245,.07);}
        .rhp-risk-item{display:flex;align-items:flex-start;gap:14px;padding:13px 0;border-bottom:1px solid rgba(255,255,255,.05);}
        .rhp-risk-item:last-child{border-bottom:none;}

        /* ── TOAST ── */
        .toast{position:fixed;bottom:24px;right:24px;background:var(--s3);border:1px solid var(--border-a);border-radius:var(--r2);padding:12px 18px;font-size:11.5px;color:var(--ink);opacity:0;pointer-events:none;transition:opacity .25s,transform .25s;transform:translateY(8px);z-index:999;max-width:320px;box-shadow:var(--sh3);}
        .toast.show{opacity:1;transform:translateY(0);}
      `}</style>


      {/* ── LANDING ── */}
      {!inApp && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', overflow: 'auto' }}>
          <nav className="land-nav">
            <div className="land-logo"><div>Stock<span>Sense</span></div></div>
            <div className="land-links">
              <a onClick={() => enter('analysis')}>Analysis</a>
              <a onClick={() => enter('ipo')}>IPO Scorer</a>
              <a onClick={() => enter('geo')}>Geopolitics</a>
              <a onClick={() => enter('paper')}>Paper Trading</a>
              <button className="land-cta" onClick={() => enter('premium')}>Get Premium →</button>
            </div>
          </nav>
          <div className="hero">
            <div className="hero-eyebrow"><div className="badge-dot" />India&apos;s Geopolitical Intelligence Platform</div>
            <h1>Trade Smarter with<br /><span className="b">Geopolitical</span> <span className="g">Intelligence</span></h1>
            <p>Institutional-grade stock analysis, IPO scoring, and geopolitical risk mapping &mdash; purpose-built for Indian retail investors.</p>
            <div className="hero-btns">
              <button className="btn-glow" onClick={() => enter('paper')}>Start Paper Trading ↗</button>
              <button className="btn-gold-border" onClick={() => enter('analysis')}>Analyse a Stock →</button>
            </div>
            <div className="feat-grid">
              {[['📊', 'Stock Report Card', 'PE, ROE, D/E with ideal vs actual bars', 'analysis'],
                ['◆', 'IPO Analyser', 'GMP, QIB & fundamentals scoring', 'ipo'],
                ['📄', 'RHP Scanner', 'AI risk extraction from prospectus', 'rhp'],
                ['◉', 'Geo Risk Engine', 'Live sector risk from global events', 'geo'],
                ['◈', 'Tax Harvester', 'LTCG/STCG optimisation alerts', 'premium']].map(([icon, name, desc, pg]) => (
                <div key={name} className="feat-card" onClick={() => enter(pg as Page)}>
                  <div className="feat-icon">{icon}</div>
                  <div className="feat-name">{name}</div>
                  <div className="feat-desc">{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── APP SHELL ── */}
      {inApp && (
        <div className="app-shell">
          <div className="sidebar">
            <div className="sb-brand">
              <div className="sb-brand-icon">◈</div>
              <div className="sb-logo">Stock<span>Sense</span></div>
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
                <div className="tb-sep" />
                <div className="tb-sub">StockSense India</div>
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