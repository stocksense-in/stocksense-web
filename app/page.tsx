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
    dashboard: '/',
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased}
        :root{
          --bg:#080C14;--s1:#0D1220;--s2:#111827;--s3:#18202E;--s4:#1F2B3E;
          --blue:#00D4FF;--blue2:rgba(0,212,255,.07);--blue3:rgba(0,212,255,.14);
          --gold:#D4AF37;--gold2:rgba(212,175,55,.07);--gold3:rgba(212,175,55,.15);
          --green:#00E676;--green2:rgba(0,230,118,.08);
          --red:#FF3A3A;--red2:rgba(255,58,58,.08);
          --ink:#EEF2FF;--ink2:#8B9EC0;--ink3:#3D5070;--ink4:#1A2540;
          --border:rgba(0,212,255,.07);--border2:rgba(0,212,255,.18);
          --border-gold:rgba(212,175,55,.2);
          --f:'Inter',sans-serif;--sidebar:218px;
        }
        html,body{background:var(--bg);color:var(--ink);font-family:var(--f);font-size:13px;}
        body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,.022) 1px,transparent 1px);background-size:44px 44px;pointer-events:none;z-index:0;}

        /* LANDING */
        .land-nav{position:fixed;top:0;left:0;right:0;padding:18px 48px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,12,20,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);z-index:10;}
        .land-logo{font-size:17px;font-weight:800;color:var(--ink);letter-spacing:-.3px;}
        .land-logo span{color:var(--blue);}
        .land-links{display:flex;gap:20px;align-items:center;}
        .land-links a{font-size:12px;color:var(--ink2);cursor:pointer;transition:color .15s;font-weight:500;}
        .land-links a:hover{color:var(--ink);}
        .land-links a.gold{color:var(--gold);}
        .hero{text-align:center;max-width:800px;padding-top:60px;}
        .hero-badge{display:inline-flex;align-items:center;gap:7px;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--blue);border:1px solid rgba(0,212,255,.3);padding:5px 14px;border-radius:20px;margin-bottom:28px;background:var(--blue2);}
        .badge-dot{width:6px;height:6px;border-radius:50%;background:var(--blue);animation:blink 2s infinite;}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
        .hero h1{font-size:54px;font-weight:800;line-height:1.06;letter-spacing:-.8px;margin-bottom:20px;color:var(--ink);}
        .hero h1 .b{color:var(--blue);}
        .hero h1 .g{color:var(--gold);}
        .hero p{font-size:16px;color:var(--ink2);line-height:1.7;max-width:520px;margin:0 auto 36px;}
        .hero-btns{display:flex;gap:12px;justify-content:center;margin-bottom:56px;flex-wrap:wrap;}
        .btn-glow{background:var(--blue);color:#000;border:none;border-radius:9px;padding:13px 28px;font-family:var(--f);font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 0 28px rgba(0,212,255,.45),0 0 60px rgba(0,212,255,.15);transition:all .2s;letter-spacing:.2px;}
        .btn-glow:hover{box-shadow:0 0 40px rgba(0,212,255,.65),0 0 80px rgba(0,212,255,.2);transform:translateY(-2px);}
        .btn-gold-border{background:transparent;color:var(--gold);border:1px solid var(--gold);border-radius:9px;padding:13px 28px;font-family:var(--f);font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;}
        .btn-gold-border:hover{background:var(--gold2);}
        .feat-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;width:100%;max-width:900px;}
        .feat-card{border:1px solid var(--border-gold);border-radius:10px;padding:16px;background:var(--gold2);cursor:pointer;transition:all .2s;text-align:center;}
        .feat-card:hover{border-color:var(--gold);background:var(--gold3);transform:translateY(-2px);}
        .feat-icon{font-size:20px;margin-bottom:7px;}
        .feat-name{font-size:11px;font-weight:700;color:var(--gold);letter-spacing:.3px;margin-bottom:3px;}
        .feat-desc{font-size:10px;color:var(--ink3);line-height:1.4;}

        /* APP SHELL */
        .app-shell{display:flex;height:100vh;overflow:hidden;position:relative;z-index:1;}
        .sidebar{width:var(--sidebar);background:var(--s1);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}
        .sb-brand{padding:18px 16px 14px;border-bottom:1px solid var(--border);}
        .sb-logo{font-size:16px;font-weight:800;color:var(--ink);}
        .sb-logo span{color:var(--blue);}
        .sb-tier{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--blue);opacity:.6;margin-top:2px;}
        .sb-user{display:flex;align-items:center;gap:9px;padding:11px 16px;border-bottom:1px solid var(--border);}
        .sb-av{width:30px;height:30px;border-radius:50%;background:var(--blue3);border:1px solid rgba(0,212,255,.3);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--blue);flex-shrink:0;}
        .sb-un{font-size:12px;font-weight:600;}
        .sb-us{font-size:9px;color:var(--ink3);margin-top:1px;}
        .sb-nav{flex:1;padding:8px 0;overflow-y:auto;}
        .nav-sec{font-size:9px;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;color:var(--ink3);padding:10px 16px 4px;}
        .ni{display:flex;align-items:center;gap:8px;padding:8px 16px;cursor:pointer;color:var(--ink2);font-size:12px;font-weight:500;transition:all .15s;border-left:2px solid transparent;user-select:none;}
        .ni:hover{background:var(--blue2);color:var(--ink);}
        .ni.active{background:var(--blue2);color:var(--blue);border-left-color:var(--blue);}
        .ni-ic{width:14px;text-align:center;font-size:11px;opacity:.6;}
        .pro-tag{font-size:8px;font-weight:700;letter-spacing:.5px;background:linear-gradient(135deg,var(--gold),#b8941e);color:#000;padding:1px 5px;border-radius:3px;margin-left:auto;}
        .sb-bottom{padding:10px;}
        .sb-promo{background:var(--gold2);border:1px solid var(--border-gold);border-radius:8px;padding:12px;}
        .sb-promo-t{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--gold);margin-bottom:4px;}
        .sb-promo-d{font-size:10px;color:var(--ink2);line-height:1.5;margin-bottom:8px;}
        .sb-promo-btn{width:100%;background:var(--gold);color:#000;border:none;border-radius:6px;padding:8px;font-family:var(--f);font-size:10px;font-weight:700;cursor:pointer;}
        .main-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
        .topbar{height:50px;background:var(--s1);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 22px;flex-shrink:0;}
        .tb-title{font-size:14px;font-weight:700;color:var(--ink);}
        .tb-r{display:flex;align-items:center;gap:12px;}
        .live-badge{display:flex;align-items:center;gap:5px;font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--green);}
        .live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);animation:blink 2s infinite;}
        .content{flex:1;overflow-y:auto;padding:20px;}

        /* UTILITIES */
        .g2{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
        .g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;}
        .g4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
        .card{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:16px 18px;}
        .card-blue{border-color:rgba(0,212,255,.2);background:var(--blue2);}
        .card-gold{border-color:var(--border-gold);background:var(--gold2);}
        .card-green{border-color:rgba(0,230,118,.2);background:var(--green2);}
        .card-red{border-color:rgba(255,58,58,.2);background:var(--red2);}
        .ct{font-size:9px;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;}
        .bn{font-size:26px;font-weight:800;line-height:1;}
        .bn-blue{color:var(--blue);}
        .bn-gold{color:var(--gold);}
        .bn-green{color:var(--green);}
        .stat-r{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(0,212,255,.04);}
        .stat-r:last-child{border-bottom:none;}
        .sl{font-size:11px;color:var(--ink2);}
        .sv{font-size:11px;font-weight:600;color:var(--ink);}
        .pill{display:inline-flex;align-items:center;font-size:9px;font-weight:700;letter-spacing:.5px;padding:2px 8px;border-radius:4px;text-transform:uppercase;}
        .pill-g{background:rgba(0,230,118,.1);color:var(--green);border:1px solid rgba(0,230,118,.2);}
        .pill-r{background:rgba(255,58,58,.1);color:var(--red);border:1px solid rgba(255,58,58,.2);}
        .pill-b{background:var(--blue2);color:var(--blue);border:1px solid rgba(0,212,255,.2);}
        .pill-gold{background:var(--gold2);color:var(--gold);border:1px solid rgba(212,175,55,.2);}
        .bar-track{height:4px;background:var(--ink4);border-radius:2px;margin:5px 0;}
        .bar-fill{height:100%;border-radius:2px;transition:width .5s;}
        .tbl{width:100%;border-collapse:collapse;}
        .tbl th{font-size:9px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;color:var(--ink3);padding:7px 10px;text-align:left;border-bottom:1px solid var(--border);}
        .tbl td{padding:10px;border-bottom:1px solid rgba(0,212,255,.04);font-size:11px;vertical-align:middle;}
        .tbl tr:hover td{background:var(--blue2);}
        .sec-div{display:flex;align-items:center;gap:10px;margin:18px 0 12px;}
        .sec-div span{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);white-space:nowrap;}
        .sec-div hr{flex:1;border:none;border-top:1px solid var(--border);}
        .field-label{font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
        .fi{width:100%;background:var(--s2);border:1px solid var(--border);border-radius:7px;padding:9px 12px;color:var(--ink);font-family:var(--f);font-size:12px;outline:none;transition:border-color .15s;}
        .fi:focus{border-color:var(--border2);box-shadow:0 0 0 3px rgba(0,212,255,.06);}
        .fi::placeholder{color:var(--ink3);}
        .btn-blue{background:var(--blue);color:#000;border:none;border-radius:7px;padding:10px 20px;font-family:var(--f);font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 0 16px rgba(0,212,255,.25);transition:all .15s;}
        .btn-blue:hover{box-shadow:0 0 26px rgba(0,212,255,.4);}
        .btn-gold{background:transparent;color:var(--gold);border:1px solid var(--gold);border-radius:7px;padding:10px 20px;font-family:var(--f);font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;}
        .btn-gold:hover{background:var(--gold2);}
        .btn-ghost{background:transparent;color:var(--ink2);border:1px solid var(--border);border-radius:7px;padding:9px 14px;font-family:var(--f);font-size:11px;cursor:pointer;transition:all .15s;}
        .btn-ghost:hover{border-color:var(--border2);color:var(--ink);}
        .seg-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;}
        .seg-btn{font-size:11px;font-weight:500;padding:6px 14px;border-radius:6px;border:1px solid var(--border);color:var(--ink2);cursor:pointer;transition:all .15s;background:transparent;font-family:var(--f);}
        .seg-btn.active{background:var(--blue);color:#000;border-color:var(--blue);font-weight:700;box-shadow:0 0 12px rgba(0,212,255,.3);}
        .idx-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;}
        .idx-card{background:var(--s1);border:1px solid var(--border);border-radius:8px;padding:12px 14px;}
        .idx-name{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
        .idx-val{font-size:19px;font-weight:800;color:var(--ink);}
        .idx-chg{font-size:10px;font-weight:600;margin-top:3px;}

        /* METRIC CARDS */
        .mc-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:start;}
        .mc{background:var(--s1);border-radius:10px;padding:15px 17px;cursor:pointer;transition:all .2s;border:1px solid var(--border);}
        .mc:hover,.mc.open{background:var(--s2);}
        .mc.open{border-color:var(--border2);}
        .mc-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
        .mc-name{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);}
        .status-dot{width:9px;height:9px;border-radius:50%;}
        .mc-val{font-size:28px;font-weight:800;color:var(--ink);line-height:1;margin-bottom:10px;letter-spacing:-.5px;}
        .mc-val sup{font-size:13px;font-weight:400;letter-spacing:0;}
        .ideal-bar{margin-bottom:8px;}
        .ideal-bar-lbl{display:flex;justify-content:space-between;font-size:9px;color:var(--ink3);margin-bottom:4px;}
        .ideal-track{position:relative;height:5px;background:var(--ink4);border-radius:3px;overflow:visible;}
        .ideal-zone{position:absolute;top:0;height:100%;border-radius:3px;opacity:.4;}
        .ideal-needle{position:absolute;top:50%;transform:translate(-50%,-50%);width:12px;height:12px;border-radius:50%;border:2px solid var(--bg);z-index:2;transition:left .5s;}
        .ideal-mid{position:absolute;top:-4px;width:1px;height:13px;background:rgba(238,242,255,.18);}
        .ideal-ann{display:flex;justify-content:space-between;align-items:center;margin-top:6px;}
        .mc-plain{font-size:11px;color:var(--ink2);line-height:1.65;margin-top:7px;}
        .mc-expand{border-top:1px solid var(--border);margin-top:11px;padding-top:11px;}
        .exp-body{font-size:11px;color:var(--ink);line-height:1.8;}
        .exp-rule{margin-top:9px;padding:9px 12px;background:rgba(212,175,55,.05);border-left:2px solid var(--gold);font-size:10px;color:var(--ink2);line-height:1.7;}
        .exp-verd{margin-top:8px;font-size:12px;font-weight:700;font-style:italic;}

        /* CANDLESTICK */
        .chart-wrap{position:relative;background:var(--s2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;overflow:hidden;}
        .candles{display:flex;align-items:flex-end;gap:3px;height:130px;padding-bottom:32px;}
        .candle-g{display:flex;flex-direction:column;align-items:center;flex:1;}
        .wick{width:1.5px;background:var(--ink3);border-radius:1px;}
        .body-c{width:75%;border-radius:2px;}
        .buy-zone{position:absolute;bottom:0;left:0;right:0;height:32px;background:linear-gradient(transparent,rgba(212,175,55,.08));border-top:1px solid rgba(212,175,55,.25);}
        .buy-zone-lbl{position:absolute;bottom:8px;left:16px;font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--gold);display:flex;align-items:center;gap:6px;}
        .buy-zone-dot{width:6px;height:6px;border-radius:50%;background:var(--gold);box-shadow:0 0 8px rgba(212,175,55,.6);}
        .chart-grid-lines{position:absolute;top:16px;left:16px;right:16px;bottom:32px;display:flex;flex-direction:column;justify-content:space-between;pointer-events:none;}
        .chart-grid-line{height:1px;background:rgba(0,212,255,.04);}

        /* IPO */
        .ipo-card{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .2s;margin-bottom:6px;}
        .ipo-card:hover,.ipo-card.sel{background:var(--s2);border-color:var(--border2);}

        /* GEO */
        .geo-alert{background:rgba(255,58,58,.05);border:1px solid rgba(255,58,58,.18);border-radius:10px;padding:14px 16px;margin-bottom:14px;}
        .geo-alert-top{display:flex;align-items:center;gap:8px;margin-bottom:5px;}
        .pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red);animation:blink 1.5s infinite;flex-shrink:0;}
        .event-card{border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:6px;cursor:pointer;transition:border-color .2s;background:var(--s1);}
        .event-card:hover{border-color:var(--border2);}
        .event-card.ev-gold{border-color:rgba(212,175,55,.3);background:var(--gold2);}
        .event-card.ev-red{border-color:rgba(255,58,58,.15);background:rgba(255,58,58,.04);}

        /* NICHE */
        .niche-card{position:relative;background:var(--s1);border:1px solid var(--border-gold);border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .2s;overflow:hidden;}
        .niche-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent);}
        .niche-card:hover{border-color:var(--gold);background:var(--gold2);}
        .risk-match{position:absolute;top:12px;right:12px;font-size:10px;font-weight:700;padding:3px 9px;border-radius:5px;}

        /* PAPER TRADING */
        .sim-badge{display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--blue);background:var(--blue2);border:1px solid rgba(0,212,255,.2);border-radius:20px;padding:4px 12px;}
        .sim-dot{width:5px;height:5px;border-radius:50%;background:var(--blue);animation:blink 2s infinite;}
        .nudge{background:rgba(212,175,55,.06);border:1px solid rgba(212,175,55,.2);border-radius:7px;padding:9px 13px;font-size:10px;color:var(--gold);line-height:1.5;}
        .mission-card{background:var(--s2);border:1px solid var(--border);border-radius:9px;padding:13px 15px;cursor:pointer;transition:border-color .2s;}
        .mission-card.done{border-color:rgba(0,230,118,.3);}
        .mission-card:hover{border-color:var(--border2);}
        .m-ic{width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;margin-bottom:7px;}
        .m-ic-blue{background:var(--blue2);color:var(--blue);border:1px solid rgba(0,212,255,.15);}
        .m-ic-green{background:rgba(0,230,118,.1);color:var(--green);border:1px solid rgba(0,230,118,.2);}
        .m-ic-gold{background:var(--gold2);color:var(--gold);border:1px solid rgba(212,175,55,.2);}
        .sparkline{display:flex;align-items:flex-end;gap:2px;height:22px;}
        .spark-b{flex:1;border-radius:1px 1px 0 0;min-height:2px;}

        /* PROFILE */
        .profile-step{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin-bottom:10px;}
        .ps-num{width:26px;height:26px;border-radius:6px;background:var(--blue2);border:1px solid rgba(0,212,255,.2);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--blue);margin-bottom:10px;}
        .range-input{width:100%;accent-color:var(--blue);}

        /* RHP */
        .rhp-upload{border:2px dashed rgba(0,212,255,.18);border-radius:10px;padding:32px 20px;text-align:center;cursor:pointer;transition:all .2s;background:var(--blue2);}
        .rhp-upload:hover{border-color:rgba(0,212,255,.4);background:var(--blue3);}
        .rhp-risk-item{display:flex;align-items:flex-start;gap:12px;padding:11px 0;border-bottom:1px solid rgba(0,212,255,.04);}
        .rhp-risk-item:last-child{border-bottom:none;}

        /* TOAST */
        .toast{position:fixed;bottom:20px;right:20px;background:var(--s3);border:1px solid var(--border2);border-radius:9px;padding:11px 16px;font-size:11px;color:var(--ink);opacity:0;pointer-events:none;transition:opacity .3s;z-index:999;max-width:300px;}
        .toast.show{opacity:1;}
      `}</style>

      {/* ── LANDING ── */}
      {!inApp && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', overflow: 'auto' }}>
          <nav className="land-nav">
            <div className="land-logo">Stock<span>Sense</span></div>
            <div className="land-links">
              <a onClick={() => enter('analysis')}>Analysis</a>
              <a onClick={() => enter('ipo')}>IPO Scorer</a>
              <a onClick={() => enter('geo')}>Geopolitics</a>
              <a onClick={() => enter('paper')}>Paper Trading</a>
              <a onClick={() => enter('premium')} className="gold">Premium ↗</a>
            </div>
          </nav>
          <div className="hero">
            <div className="hero-badge"><div className="badge-dot" />India's Geopolitical Intelligence Platform</div>
            <h1>StockSense: Master<br />the Market with<br /><span className="b">Geopolitical</span> <span className="g">Intelligence</span></h1>
            <p>Understand every number. Spot every risk. Trade with institutional-grade confidence — built for Indian retail investors.</p>
            <div className="hero-btns">
              <button className="btn-glow" onClick={() => enter('paper')}>Start Paper Trading ↗</button>
              <button className="btn-gold-border" onClick={() => enter('premium')}>Premium Geopolitical Insights</button>
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
              <div className="sb-logo">Stock<span>Sense</span></div>
              <div className="sb-tier">India Equities Platform</div>
            </div>
            <div className="sb-user">
              <div className="sb-av">VS</div>
              <div><div className="sb-un">Vikram S.</div><div className="sb-us">Free Member</div></div>
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

          <div className="main-area">
            <div className="topbar">
              <div className="tb-title">{PAGE_TITLES[activePage]}</div>
              <div className="tb-r">
                <div className="live-badge"><div className="live-dot" />NSE Live</div>
                <div style={{ fontSize: 10, color: C.ink3 }}>{today}</div>
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