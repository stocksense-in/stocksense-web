'use client';
import { supabase } from "@/lib/supabase"

import { useState, useEffect, useCallback, useRef } from 'react';

// ─── TYPES ──────────────────────────────────────────────────────────────────

type Page =
  | 'dashboard' | 'analysis' | 'ipo' | 'screener'
  | 'geo' | 'premium' | 'profile' | 'paper' | 'rhp';

type Sector = 'it' | 'bank' | 'auto' | 'newage' | 'fmcg' | 'pharma' | 'defence' | 'nbfc' | 'electronics';

interface StockData {
  ticker: string; sub: string; price: string; chg: string;
  score: number; sector: Sector;
  data: { pe: number; roe: number; de: number; margin: number; promoter: number; cagr: number };
  ctx: { idealPE: string; avgROE: number; idealDE: string; avgMargin: number; sectorCAGR: number; promoterNote: string; cagr: number; pe: number; margin: number };
}

interface Holding {
  sym: string; qty: number; avgCost: number; ltp: number;
  sl: number; daysHeld: number; hist: number[];
}

interface IPO {
  name: string; sector: string; open: string; size: string;
  score: number; gmp: number; qib: number; retail: number;
  fund: number; geo: number; verdict: string; band: string;
}

// ─── STATIC DATA ────────────────────────────────────────────────────────────

const SD: Record<string, StockData> = {
  'Infosys': {
    ticker: 'NSE: INFY', sub: 'IT Services · Large Cap', price: '₹1,842', chg: '+1.4%', score: 70, sector: 'it',
    data: { pe: 24.2, roe: 31, de: 0.08, margin: 17.2, promoter: 14.7, cagr: 12.8 },
    ctx: { idealPE: '18–28×', avgROE: 22, idealDE: '<0.3×', avgMargin: 18, sectorCAGR: 14, promoterNote: 'Institutionally governed — low promoter holding is intentional and not a governance concern.', cagr: 12.8, pe: 24.2, margin: 17.2 }
  },
  'HDFC Bank': {
    ticker: 'NSE: HDFCBANK', sub: 'Private Banking · Large Cap', price: '₹1,623', chg: '-0.3%', score: 75, sector: 'bank',
    data: { pe: 18.4, roe: 16.8, de: 9.2, margin: 22, promoter: 0, cagr: 18 },
    ctx: { idealPE: '12–20×', avgROE: 15, idealDE: 'N/A for banks', avgMargin: 20, sectorCAGR: 16, promoterNote: 'RBI prudential norms cap bank promoter holdings. Strong FII ownership is the confidence signal.', cagr: 18, pe: 18.4, margin: 22 }
  },
  'Tata Motors': {
    ticker: 'NSE: TATAMOTORS', sub: 'Auto Manufacturing · Large Cap', price: '₹934', chg: '+2.1%', score: 58, sector: 'auto',
    data: { pe: 8.2, roe: 38, de: 1.8, margin: 6.1, promoter: 46.4, cagr: 22 },
    ctx: { idealPE: '8–20×', avgROE: 14, idealDE: '<1.0×', avgMargin: 7, sectorCAGR: 11, promoterNote: 'Tata Sons holds 46.4% with zero pledging — strong long-term conviction.', cagr: 22, pe: 8.2, margin: 6.1 }
  },
  'Zomato': {
    ticker: 'NSE: ZOMATO', sub: 'Food Delivery · Mid Cap', price: '₹224', chg: '+0.8%', score: 48, sector: 'newage',
    data: { pe: 320, roe: 3.1, de: 0.02, margin: 4.2, promoter: 0, cagr: 68 },
    ctx: { idealPE: 'N/A', avgROE: 5, idealDE: '<0.2×', avgMargin: 2, sectorCAGR: 35, promoterNote: 'VC-backed — Info Edge 13%, Ant Financial 15%. Monitor bulk deal disclosures.', cagr: 68, pe: 320, margin: 4.2 }
  },
};

type MetricKey = 'pe' | 'roe' | 'de' | 'margin' | 'promoter' | 'cagr';

interface MetricMeta {
  name: string; unit: string; il: string; lo: string; hi: string;
  norm: (v: number, s?: string) => number;
  iz: (s?: string) => [number, number];
  plain: (v: number, s?: string) => string;
  verd: (v: number, s?: string) => string;
}

const MM: Record<MetricKey, MetricMeta> = {
  pe: {
    name: 'P/E Ratio', unit: '×', il: '10–28×', lo: 'Low', hi: 'High',
    norm: (v, s) => s === 'bank' ? Math.max(0, Math.min(100, 100 - (v - 8) / 30 * 100)) : s === 'newage' ? Math.max(0, Math.min(100, v > 200 ? 4 : v > 80 ? 18 : 38)) : Math.max(0, Math.min(100, 100 - (v - 8) / 42 * 100)),
    iz: (s) => s === 'bank' ? [52, 25] : [50, 28],
    plain: (v, s) => s === 'newage' ? 'Priced for future growth — standard for new-age platforms.' : v < 15 ? 'Cheap vs sector — verify earnings quality.' : v < 28 ? 'Fairly valued within sector norms.' : 'Premium multiple — growth must justify it.',
    verd: (v, s) => s === 'newage' ? 'Future growth priced in' : v < 28 ? 'Fairly valued' : 'High multiple — execution risk',
  },
  roe: {
    name: 'Return on Equity', unit: '%', il: '>15%', lo: 'Weak', hi: 'Excellent',
    norm: (v) => Math.max(0, Math.min(100, v < 0 ? 0 : v / 50 * 100)), iz: () => [32, 35],
    plain: (v) => v >= 25 ? 'Exceptional capital efficiency — top decile in Indian markets.' : v >= 15 ? 'Above the quality threshold.' : 'Below ideal — watch management efficiency trend.',
    verd: (v) => v >= 25 ? 'Excellent efficiency' : v >= 15 ? 'Healthy' : 'Needs monitoring',
  },
  de: {
    name: 'Debt / Equity', unit: '×', il: '<0.8×', lo: 'Safe', hi: 'Leveraged',
    norm: (v, s) => s === 'bank' ? Math.max(0, Math.min(100, 100 - (v - 3) / 12 * 100)) : Math.max(0, Math.min(100, Math.max(0, 100 - (v / 3.5) * 100))),
    iz: (s) => s === 'bank' ? [10, 20] : [65, 22],
    plain: (v, s) => s === 'bank' ? 'Banks carry natural leverage — evaluate NIM and GNPA.' : v < 0.3 ? 'Pristine balance sheet — exceptional safety.' : v < 0.8 ? 'Conservative and manageable.' : 'Elevated — stress-test against revenue scenarios.',
    verd: (v, s) => s === 'bank' ? 'Evaluate NIM & GNPA' : v < 0.8 ? 'Conservative balance sheet' : 'Monitor leverage',
  },
  margin: {
    name: 'Net Profit Margin', unit: '%', il: '>12%', lo: 'Thin', hi: 'Strong',
    norm: (v) => Math.max(0, Math.min(100, v < 0 ? 0 : v / 38 * 100)), iz: () => [35, 28],
    plain: (v, s) => s === 'newage' ? v < 5 ? 'Early-stage profitability — track quarterly trajectory.' : 'Improving — margin expansion in progress.' : v >= 20 ? 'Strong pricing power intact.' : v >= 12 ? 'Solid profitability.' : 'Below ideal — monitor cost structure.',
    verd: (v) => v >= 20 ? 'Strong pricing power' : v >= 12 ? 'Solid' : 'Pressure on margins',
  },
  promoter: {
    name: 'Promoter Holding', unit: '%', il: '40–75%', lo: 'Low', hi: 'High',
    norm: (v) => Math.max(0, Math.min(100, v / 80 * 100)), iz: () => [52, 28],
    plain: (v, s) => s === 'bank' ? 'RBI-regulated ceiling — focus on institutional holding composition.' : s === 'newage' ? 'VC structure — monitor bulk deal exit signals.' : v >= 40 ? 'Strong founder conviction evident.' : 'Lower stake — verify governance structure.',
    verd: (v, s) => s === 'bank' ? 'RBI cap applies' : v >= 40 ? 'Healthy alignment' : 'Review governance',
  },
  cagr: {
    name: 'Revenue CAGR 3yr', unit: '%', il: '>12%', lo: 'Slow', hi: 'Exceptional',
    norm: (v) => Math.max(0, Math.min(100, v < 0 ? 0 : v / 55 * 100)), iz: () => [26, 28],
    plain: (v) => v >= 30 ? 'Exceptional — well above sector growth rate.' : v >= 15 ? 'Strong momentum — outpacing peers.' : v >= 8 ? 'In line with sector average.' : 'Lagging sector — diagnose root cause.',
    verd: (v) => v >= 30 ? 'Exceptional growth' : v >= 15 ? 'Strong momentum' : 'Lagging peers',
  },
};

const IPOS: IPO[] = [
  { name: 'Ather Energy', sector: 'EV / Auto', open: 'Apr 28', size: '₹2,626 Cr', score: 72, gmp: 68, qib: 85, retail: 72, fund: 65, geo: 60, verdict: 'Subscribe', band: '₹304–321' },
  { name: 'Hexaware Technologies', sector: 'IT Services', open: 'May 5', size: '₹8,750 Cr', score: 68, gmp: 55, qib: 78, retail: 65, fund: 70, geo: 72, verdict: 'Subscribe', band: '₹674–708' },
  { name: 'Smartworks', sector: 'Real Estate', open: 'Apr 22', size: '₹583 Cr', score: 51, gmp: 42, qib: 55, retail: 68, fund: 48, geo: 55, verdict: 'Risky', band: '₹387–407' },
  { name: 'Swiggy OFS', sector: 'Food Tech', open: 'May 12', size: '₹1,200 Cr', score: 44, gmp: 30, qib: 48, retail: 60, fund: 38, geo: 50, verdict: 'Avoid', band: '₹390–410' },
];

const SCREENER = [
  { n: 'Infosys', s: 'IT', sc: 70, pe: 24.2, roe: 31, de: 0.08, sig: 'g' },
  { n: 'TCS', s: 'IT', sc: 74, pe: 28.1, roe: 45, de: 0.05, sig: 'g' },
  { n: 'HDFC Bank', s: 'Banking', sc: 75, pe: 18.4, roe: 16.8, de: 9.2, sig: 'g' },
  { n: 'Bajaj Finance', s: 'NBFC', sc: 62, pe: 31.2, roe: 22, de: 3.1, sig: 'gold' },
  { n: 'Tata Motors', s: 'Auto', sc: 58, pe: 8.2, roe: 38, de: 1.8, sig: 'gold' },
  { n: 'Sun Pharma', s: 'Pharma', sc: 66, pe: 33.4, roe: 14, de: 0.12, sig: 'gold' },
  { n: 'Zomato', s: 'Food Tech', sc: 48, pe: 320, roe: 3.1, de: 0.02, sig: 'r' },
  { n: 'IDFC First', s: 'Banking', sc: 45, pe: 22.1, roe: 9.8, de: 8.4, sig: 'r' },
];

const GEO_SECTORS = [
  { s: 'Oil & Gas', risk: 88, impact: 'HIGH RISK', note: 'Strait of Hormuz disruption threatens crude supply', c: 'r' },
  { s: 'Defence & Aerospace', risk: 78, impact: 'OPPORTUNITY', note: 'India procurement acceleration — HAL, BEL, MTAR', c: 'g' },
  { s: 'Gold / Silver', risk: 72, impact: 'SAFE HAVEN', note: 'Demand spike on geopolitical risk aversion', c: 'gold' },
  { s: 'Aviation', risk: 75, impact: 'HIGH RISK', note: 'Fuel cost surge + route disruption risks', c: 'r' },
  { s: 'IT Services', risk: 18, impact: 'LOW RISK', note: 'USD revenue hedge — minimal direct exposure', c: 'g' },
  { s: 'FMCG', risk: 14, impact: 'LOW RISK', note: 'Domestic demand insulated from global shocks', c: 'g' },
  { s: 'Banking', risk: 32, impact: 'MODERATE', note: 'Inflation from crude affects RBI rate trajectory', c: 'gold' },
  { s: 'Pharma', risk: 20, impact: 'LOW RISK', note: 'API imports from China — monitor trade routes', c: 'g' },
];

const GEO_EVENTS = [
  { title: 'Iran retaliatory strike — Hormuz closure risk elevated', tag: 'CONFLICT', cls: 'ev-red' },
  { title: 'India accelerates TEJAS Mk2 & Akash procurement', tag: 'DEFENCE', cls: '' },
  { title: 'Gold breaks ₹73,500 on safe-haven demand — MCX volumes 3×', tag: 'COMMODITY', cls: 'ev-gold' },
  { title: 'India-US trade pact framework — IT exports benefit in FY26', tag: 'TRADE', cls: '' },
  { title: 'Saudi Aramco cuts output 2% — Brent at $96/bbl', tag: 'OIL', cls: 'ev-red' },
  { title: 'Russia grain export deal collapses — agri commodity spike', tag: 'AGRI', cls: 'ev-gold' },
];

const NICHE = [
  { name: 'MTAR Technologies', sector: 'Defence · Space', match: 92, pe: 42, roe: 18, why: 'JLR recovery + ISRO contracts. Aligns with moderate risk + defence tailwind.', risk: 'Low', tag: 'Geo Tailwind' },
  { name: "Divi's Laboratories", sector: 'Pharma · API', match: 88, pe: 58, roe: 16, why: 'High ROCE, zero debt, FDA cleared. Perfect for capital preservation.', risk: 'Low', tag: 'Defensive Pick' },
  { name: 'Kaynes Technology', sector: 'Electronics · EMS', match: 84, pe: 68, roe: 22, why: "India's EMS boom. PLI beneficiary. Revenue CAGR 38%. Niche moat.", risk: 'Moderate', tag: 'Niche Growth' },
  { name: 'Radico Khaitan', sector: 'Alcobev · FMCG', match: 79, pe: 62, roe: 14, why: 'Premium spirits demand rising. Low geo-risk. Steady cash flows.', risk: 'Low', tag: 'Defensive' },
];

const PT_STOCKS: Record<string, { n: string; vol: number }> = {
  INFY: { n: 'Infosys', vol: 0.015 }, HDFCBANK: { n: 'HDFC Bank', vol: 0.012 },
  TATAMOTORS: { n: 'Tata Motors', vol: 0.022 }, ZOMATO: { n: 'Zomato', vol: 0.028 },
  RELIANCE: { n: 'Reliance', vol: 0.014 },
};

const PAGE_TITLES: Record<Page, string> = {
  dashboard: 'Dashboard', analysis: 'Stock Analysis', ipo: 'IPO Analyser',
  screener: 'Screener', geo: 'Geopolitics Engine', premium: 'Niche Stocks · Premium',
  profile: 'Investment Profile', paper: 'Paper Trading Simulator', rhp: 'RHP Scanner',
};

const NAV_ITEMS: { id: Page; icon: string; label: string; pro?: boolean }[] = [
  { id: 'dashboard', icon: '▦', label: 'Dashboard' },
  { id: 'analysis', icon: '◈', label: 'Stock Analysis' },
  { id: 'ipo', icon: '◆', label: 'IPO Analyser' },
  { id: 'screener', icon: '≡', label: 'Screener' },
  { id: 'geo', icon: '◉', label: 'Geopolitics Engine' },
  { id: 'premium', icon: '★', label: 'Niche Stocks', pro: true },
  { id: 'profile', icon: '⊕', label: 'Investment Profile' },
  { id: 'paper', icon: '◎', label: 'Paper Trading' },
  { id: 'rhp', icon: '▣', label: 'RHP Scanner' },
];

// ─── HELPER: CSS-in-JSX colour vars ─────────────────────────────────────────
const C = {
  blue: 'var(--blue)', gold: 'var(--gold)', green: 'var(--green)', red: 'var(--red)',
  ink: 'var(--ink)', ink2: 'var(--ink2)', ink3: 'var(--ink3)',
};

function pillClass(sig: string) {
  return sig === 'g' ? 'pill pill-g' : sig === 'gold' ? 'pill pill-gold' : sig === 'r' ? 'pill pill-r' : 'pill pill-b';
}

function getMetricStatus(mk: MetricKey, val: number, sector: string): 'green' | 'yellow' | 'red' {
  const m = MM[mk];
  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  if (n >= ip && n <= ip + iw) return 'green';
  if (n >= ip - 14 && n <= ip + iw + 14) return 'yellow';
  return 'red';
}

function scoreColor(score: number) {
  return score >= 65 ? C.green : score >= 50 ? C.gold : C.red;
}

function formatINR(n: number) {
  return '₹' + Math.round(n).toLocaleString('en-IN');
}

// ─── SUBCOMPONENTS ──────────────────────────────────────────────────────────

function Pill({ type, children }: { type: string; children: React.ReactNode }) {
  return <span className={pillClass(type)}>{children}</span>;
}

function StatRow({ label, value, valueStyle }: { label: string; value: React.ReactNode; valueStyle?: React.CSSProperties }) {
  return (
    <div className="stat-r">
      <span className="sl">{label}</span>
      <span className="sv" style={valueStyle}>{value}</span>
    </div>
  );
}

function SectionDiv({ label }: { label: string }) {
  return (
    <div className="sec-div">
      <span>{label}</span>
      <hr />
    </div>
  );
}

// ─── CANDLESTICK CHART ──────────────────────────────────────────────────────

function CandleChart() {
  const candles = Array.from({ length: 28 }, (_, i) => {
    const open = 1800 + Math.sin(i * 0.4) * 120 + (Math.random() - 0.5) * 60;
    const close = open + (Math.random() - 0.47) * 50;
    const high = Math.max(open, close) + Math.random() * 30;
    const low = Math.min(open, close) - Math.random() * 30;
    const up = close >= open;
    const range = 220, minP = 1620;
    const bodyH = Math.max(4, Math.abs(close - open) / range * 90);
    const wickTopH = (high - Math.max(open, close)) / range * 90;
    const wickBotH = (Math.min(open, close) - low) / range * 90;
    return { up, bodyH, wickTopH, wickBotH, dim: i < 6 };
  });

  return (
    <div className="chart-wrap">
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>
        Price Action · 30 Days
      </div>
      <div className="chart-grid-lines">
        {Array(5).fill(0).map((_, i) => <div key={i} className="chart-grid-line" />)}
      </div>
      <div className="candles">
        {candles.map((c, i) => (
          <div key={i} className="candle-g" style={{ height: '100%', justifyContent: 'flex-end' }}>
            <div className="wick" style={{ height: c.wickTopH }} />
            <div className="body-c" style={{ height: c.bodyH, background: c.up ? C.green : C.red, opacity: c.dim ? 0.35 : 0.85 }} />
            <div className="wick" style={{ height: c.wickBotH }} />
          </div>
        ))}
      </div>
      <div className="buy-zone">
        <div className="buy-zone-lbl"><div className="buy-zone-dot" />Institutional Buying Zone</div>
      </div>
    </div>
  );
}

// ─── METRIC CARD ────────────────────────────────────────────────────────────

function MetricCard({ mk, val, sector }: { mk: MetricKey; val: number; sector: string }) {
  const [open, setOpen] = useState(false);
  const m = MM[mk];
  const st = getMetricStatus(mk, val, sector);
  const dc = st === 'green' ? C.green : st === 'yellow' ? C.gold : C.red;
  const n = m.norm(val, sector);
  const [ip, iw] = m.iz(sector);
  const dl = Math.max(1, Math.min(97, n));
  const il = Math.max(0, Math.min(90, ip));
  const bcl = st === 'green' ? 'pill-g' : st === 'yellow' ? 'pill-gold' : 'pill-r';
  const bl = st === 'green' ? 'Healthy' : st === 'yellow' ? 'Monitor' : 'Concern';
  const borderColor = st === 'green' ? 'rgba(0,230,118,.2)' : st === 'yellow' ? 'rgba(212,175,55,.2)' : 'rgba(255,58,58,.2)';

  return (
    <div className={`mc${open ? ' open' : ''}`} style={{ borderColor }} onClick={() => setOpen(o => !o)}>
      <div className="mc-top">
        <span className="mc-name">{m.name}</span>
        <div className="status-dot" style={{ background: dc, boxShadow: `0 0 6px ${dc}` }} />
      </div>
      <div className="mc-val">{val}<sup> {m.unit}</sup></div>
      <div className="ideal-bar">
        <div className="ideal-bar-lbl">
          <span>{m.lo}</span>
          <span style={{ color: C.gold, fontSize: 8 }}>▌ Ideal zone</span>
          <span>{m.hi}</span>
        </div>
        <div className="ideal-track">
          <div className="ideal-zone" style={{ left: `${il}%`, width: `${iw}%`, background: dc }} />
          <div className="ideal-mid" style={{ left: `${il + iw / 2}%` }} />
          <div className="ideal-needle" style={{ left: `${dl}%`, background: dc, boxShadow: `0 0 6px ${dc}` }} />
        </div>
        <div className="ideal-ann">
          <span style={{ fontSize: 9, color: C.ink3 }}>Ideal: {m.il}</span>
          <span className={`pill ${bcl}`} style={{ fontSize: 8 }}>{bl}</span>
        </div>
      </div>
      <div className="mc-plain">{m.plain(val, sector)}</div>
      {open && (
        <div className="mc-expand">
          <div className="exp-body">{m.verd(val, sector)} — {m.plain(val, sector)}</div>
          <div className="exp-rule">
            <strong style={{ color: C.gold }}>Ideal range: {m.il}</strong> · This stock: {val}{m.unit} ·{' '}
            {st === 'green' ? 'Within the ideal zone for this sector.' : st === 'yellow' ? 'Near the boundary — watch closely.' : 'Outside the ideal range — understand why before investing.'}
          </div>
          <div className="exp-verd" style={{ color: dc }}>"{m.verd(val, sector)}"</div>
        </div>
      )}
    </div>
  );
}

// ─── PAGE COMPONENTS ────────────────────────────────────────────────────────

function DashboardPage({ onNav }: { onNav: (p: Page) => void }) {
  const [nifty, setNifty] = useState<number | null>(null)
  const [prices, setPrices] = useState({
  NIFTY50: null,
  SENSEX: null,
  BANKNIFTY: null,
})
  useEffect(() => {
  const fetchPrice = async () => {
    const { data, error } = await supabase
      .from("live_prices")
      .select("*")
      .eq("symbol", "NIFTY50")
      .single()

    if (!error && data) {
      setNifty(data.price)
    }
  }

  fetchPrice()

  const interval = setInterval(fetchPrice, 5000) // every 5 sec

  return () => clearInterval(interval)
}, [])
  const sectors = [['IT', '+2.1%', 'green'], ['FMCG', '+0.8%', 'green'], ['Auto', '+1.4%', 'green'], ['Pharma', '-0.3%', 'red'], ['Banking', '-0.6%', 'red'], ['Defence', '+3.8%', 'green']];
  const movers = [['RELIANCE', '₹2,934', '+3.2%', 'g'], ['MTAR TECH', '₹2,180', '+4.1%', 'g'], ['HAL', '₹4,620', '+2.8%', 'g'], ['INDIGO', '₹3,240', '-2.6%', 'r'], ['NTPC', '₹364', '-1.4%', 'r']];
  const news = [
    { t: 'RBI holds repo rate at 6.5% — neutral stance Q2', tag: 'MACRO', c: 'gold' },
    { t: 'Crude breaches $96 on Hormuz escalation — OMCs under pressure', tag: 'RISK', c: 'r' },
    { t: 'TCS Q4 PAT +8.2% YoY — double-digit FY26 guidance confirmed', tag: 'RESULT', c: 'g' },
    { t: 'Ather Energy IPO opens Apr 28 — GMP at +₹38 over issue price', tag: 'IPO', c: 'b' },
  ];

  return (
    <div>
      <div className="idx-strip">
  {[
    ['Nifty 50', nifty !== null ? `₹${nifty}` : 'Loading...', '▲ +197 · +0.82%', 'green'],
    ['Sensex', '80,116', '▲ +566 · +0.71%', 'green'],
    ['Bank Nifty', '52,480', '▼ -179 · -0.34%', 'red'],
    ['India VIX', '13.42', '— Moderate', 'ink2']
  ].map(([name, val, chg, c]) => (
    <div key={name} className="idx-card">
      <div className="idx-name">{name}</div>
      <div className="idx-val">{val}</div>
      <div className="idx-chg" style={{ color: `var(--${c})` }}>
        {chg}
      </div>
    </div>
  ))}
</div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Market Pulse · FII / DII</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
            <svg width="80" height="80" viewBox="0 0 80 80" style={{ flexShrink: 0 }}>
              <circle cx="40" cy="40" r="30" fill="none" stroke="var(--ink4)" strokeWidth="7" />
              <circle cx="40" cy="40" r="30" fill="none" stroke="var(--green)" strokeWidth="7"
                strokeDasharray="188.5" strokeDashoffset="53" strokeLinecap="round" transform="rotate(-90 40 40)"
                style={{ filter: 'drop-shadow(0 0 7px rgba(0,230,118,.4))' }} />
              <text x="40" y="37" textAnchor="middle" fontSize="15" fontWeight="800" fill="#EEF2FF" fontFamily="Inter,sans-serif">72%</text>
              <text x="40" y="51" textAnchor="middle" fontSize="8" fill="#8B9EC0" fontFamily="Inter,sans-serif">BULLISH</text>
            </svg>
            <div style={{ flex: 1 }}>
              <StatRow label="FII Net" value="+₹2,840 Cr" valueStyle={{ color: C.green }} />
              <StatRow label="DII Net" value="-₹1,120 Cr" valueStyle={{ color: C.red }} />
              <StatRow label="Advances" value="1,847" />
              <StatRow label="Declines" value="892" />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="ct">Sector Performance · Today</div>
          {sectors.map(([n, v, c]) => (
            <div key={n} className="stat-r">
              <span className="sl">{n}</span>
              <div style={{ flex: 1, margin: '0 10px' }}>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.abs(parseFloat(v)) / 4 * 100}%`, background: `var(--${c})` }} />
                </div>
              </div>
              <span className="sv" style={{ color: `var(--${c})` }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Top Movers</div>
          <table className="tbl">
            <thead><tr><th>Stock</th><th>Price</th><th>Change</th><th>Signal</th></tr></thead>
            <tbody>
              {movers.map(([n, p, c, s]) => (
                <tr key={n}>
                  <td style={{ fontWeight: 600 }}>{n}</td>
                  <td style={{ fontFamily: 'monospace' }}>{p}</td>
                  <td style={{ color: `var(--${s === 'g' ? 'green' : 'red'})`, fontWeight: 600 }}>{c}</td>
                  <td><Pill type={s}>{s === 'g' ? 'Buy' : 'Watch'}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="ct">Market Intelligence Feed</div>
          {news.map((item, i) => (
            <div key={i} className="stat-r" style={{ alignItems: 'flex-start', padding: '8px 0' }}>
              <span className={`pill pill-${item.c}`} style={{ flexShrink: 0, marginTop: 1 }}>{item.tag}</span>
              <span style={{ fontSize: 11, color: C.ink, marginLeft: 10, lineHeight: 1.5 }}>{item.t}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card card-gold" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div className="ct" style={{ color: C.gold }}>Active Geopolitical Risk Alert</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.ink, marginBottom: 4 }}>Middle East escalation — Oil, Gold, Defence sectors flagged</div>
          <div style={{ fontSize: 11, color: C.ink2 }}>Updated 2hr ago · Gold/Silver showing safe-haven demand surge</div>
        </div>
        <button className="btn-gold" onClick={() => onNav('geo')}>View Full Analysis →</button>
      </div>
      <p style={{fontSize:'10px', color:'#3D5070', marginTop:'20px'}}>
  StockSense v0.1 · Day 1 · Branch: frontend_kartikey
</p>
    </div>
  );
}

function AnalysisPage() {
  const [query, setQuery] = useState('Infosys');
  const [stock, setStock] = useState<{ key: string; data: StockData } | null>(null);

  const doAnalyse = useCallback((q: string) => {
    const key = Object.keys(SD).find(k => k.toLowerCase().includes(q.toLowerCase())) || 'Infosys';
    setStock({ key, data: SD[key] });
  }, []);

  useEffect(() => { doAnalyse('Infosys'); }, [doAnalyse]);

  const s = stock?.data;
  const key = stock?.key || '';
  const vs = s ? (s.score >= 70 ? ['pill-g', 'Strong'] : s.score >= 55 ? ['pill-gold', 'Moderate'] : ['pill-r', 'Risky']) : [];

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input className="fi" value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doAnalyse(query)}
          placeholder="Search — INFY · HDFCBANK · TATAMOTORS · ZOMATO" style={{ flex: 1 }} />
        <button className="btn-blue" onClick={() => doAnalyse(query)}>Analyse ↗</button>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 1, color: C.ink3, alignSelf: 'center' }}>QUICK:</span>
        {[['Infosys', 'INFY'], ['HDFC Bank', 'HDFCBANK'], ['Tata Motors', 'TATAMOTORS'], ['Zomato', 'ZOMATO']].map(([k, label]) => (
          <span key={k} className="pill pill-b" style={{ cursor: 'pointer', padding: '4px 10px' }}
            onClick={() => { setQuery(k); doAnalyse(k); }}>{label}</span>
        ))}
      </div>

      {s && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: 14, borderBottom: '1px solid var(--border)', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.blue, marginBottom: 4 }}>{s.ticker}</div>
              <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.3px' }}>{key} Ltd</div>
              <div style={{ fontSize: 11, color: C.ink2, marginTop: 3 }}>{s.sub}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>{s.price}</div>
              <div style={{ fontSize: 11, fontWeight: 600, marginTop: 2, color: s.chg.startsWith('-') ? C.red : C.green }}>{s.chg} today</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginTop: 6 }}>
                <span style={{ fontSize: 10, color: C.ink2 }}>Score</span>
                <span style={{ fontSize: 20, fontWeight: 800 }}>{s.score}</span>
                <span className={`pill ${vs[0]}`}>{vs[1]}</span>
              </div>
            </div>
          </div>

          <CandleChart />

          <div className="mc-grid">
            {(Object.keys(MM) as MetricKey[]).map(mk => (
              <MetricCard key={mk} mk={mk} val={s.data[mk]} sector={s.sector} />
            ))}
          </div>

          <div style={{ marginTop: 10, padding: '10px 14px', background: 'var(--red2)', border: '1px solid rgba(255,58,58,.15)', borderRadius: 8, fontSize: 10, color: C.ink2 }}>
            <strong style={{ color: C.red }}>Disclosure —</strong> StockSense is educational only. Not SEBI-registered investment advice. Consult a registered advisor before investing.
          </div>
        </div>
      )}
    </div>
  );
}

function IPOPage() {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div>
      <div className="g2" style={{ marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Active IPOs · Tap to Analyse</div>
          {IPOS.map((ipo, i) => (
            <div key={i} className={`ipo-card${selected === i ? ' sel' : ''}`} onClick={() => setSelected(i)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{ipo.name}</div>
                  <div style={{ fontSize: 10, color: C.ink3, marginTop: 2 }}>{ipo.sector} · Opens {ipo.open} · {ipo.size}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(ipo.score) }}>{ipo.score}</div>
                  <div style={{ fontSize: 8, fontWeight: 700, letterSpacing: 1, color: C.ink3 }}>SCORE</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Pill type={ipo.verdict === 'Subscribe' ? 'g' : ipo.verdict === 'Risky' ? 'gold' : 'r'}>{ipo.verdict}</Pill>
                <span style={{ fontSize: 10, color: C.ink3 }}>{ipo.band}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          {selected === null ? (
            <div style={{ fontSize: 11, color: C.ink3, padding: '20px 0', textAlign: 'center' }}>← Select an IPO to view full scoring</div>
          ) : (() => {
            const ipo = IPOS[selected];
            const sc = scoreColor(ipo.score);
            const sigs: [string, string, number][] = [['GMP Signal', '20%', ipo.gmp], ['QIB Subscription', '25%', ipo.qib], ['Retail Interest', '10%', ipo.retail], ['Fundamentals', '30%', ipo.fund], ['Geo Risk Score', '15%', ipo.geo]];
            return (
              <div>
                <div className="ct">IPO Analysis · {ipo.name}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 800 }}>{ipo.name}</div>
                    <div style={{ fontSize: 10, color: C.ink3, marginTop: 3 }}>{ipo.sector} · {ipo.band} · {ipo.size} · Opens {ipo.open}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 32, fontWeight: 800, color: sc }}>{ipo.score}</div>
                    <Pill type={ipo.verdict === 'Subscribe' ? 'g' : ipo.verdict === 'Risky' ? 'gold' : 'r'}>{ipo.verdict}</Pill>
                  </div>
                </div>
                {sigs.map(([lbl, w, v]) => (
                  <div key={lbl} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 10, color: C.ink2 }}>{lbl} <span style={{ color: C.ink3 }}>({w})</span></span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: v >= 65 ? C.green : v >= 45 ? C.gold : C.red }}>{v}/100</span>
                    </div>
                    <div className="bar-track" style={{ height: 5 }}>
                      <div className="bar-fill" style={{ width: `${v}%`, background: v >= 65 ? C.green : v >= 45 ? C.gold : C.red }} />
                    </div>
                  </div>
                ))}
                <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--gold2)', borderLeft: `2px solid ${C.gold}`, fontSize: 10, color: C.ink2, lineHeight: 1.7 }}>
                  <strong style={{ color: C.gold }}>Analyst note —</strong>{' '}
                  {ipo.verdict === 'Subscribe' ? 'Strong institutional interest and fair valuation. GMP positive. Suitable for listing gain + short-term hold.' : ipo.verdict === 'Risky' ? 'Mixed signals — QIB interest moderate. Suitable only for high risk tolerance.' : 'Poor QIB interest and weak fundamentals. Listing losses likely. Avoid.'}
                </div>
              </div>
            );
          })()}
        </div>
      </div>

      <div className="card">
        <div className="ct">Scoring Methodology</div>
        <div className="g4" style={{ textAlign: 'center' }}>
          {[['30%', 'FUNDAMENTALS', C.blue], ['25%', 'QIB SUBSCRIPTION', C.green], ['20%', 'GMP SIGNAL', C.gold], ['15%', 'GEO RISK', C.red]].map(([pct, label, color], i, arr) => (
            <div key={label} style={{ padding: 10, borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color }}>{pct}</div>
              <div style={{ fontSize: 9, fontWeight: 700, color: C.ink3, marginTop: 3, letterSpacing: 1 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScreenerPage() {
  return (
    <div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="ct">Filter Universe · NSE + BSE</div>
        <div className="g3" style={{ marginBottom: 12 }}>
          {[['Sector', ['All Sectors', 'IT Services', 'Banking', 'Auto', 'FMCG', 'Pharma', 'Defence']],
            ['Market Cap', ['All', 'Large Cap (>₹20K Cr)', 'Mid Cap', 'Small Cap']],
            ['Signal Quality', ['All', 'Strong (70+)', 'Moderate (50–70)', 'Weak']]].map(([label, opts]) => (
            <div key={label as string}>
              <div className="field-label">{label}</div>
              <select className="fi">
                {(opts as string[]).map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-blue">Run Screener ↗</button>
          <button className="btn-ghost">Reset</button>
        </div>
      </div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="ct" style={{ margin: 0 }}>Results · 8 Stocks</div>
          <span className="pill pill-b">Live NSE Data</span>
        </div>
        <table className="tbl">
          <thead><tr><th>Company</th><th>Sector</th><th>Score</th><th>P/E</th><th>ROE</th><th>D/E</th><th>Signal</th></tr></thead>
          <tbody>
            {SCREENER.map(r => (
              <tr key={r.n}>
                <td style={{ fontWeight: 600 }}>{r.n}</td>
                <td style={{ color: C.ink3, fontSize: 10 }}>{r.s}</td>
                <td><Pill type={r.sig}>{r.sc}</Pill></td>
                <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{r.pe}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 11, color: r.roe >= 20 ? C.green : r.roe >= 15 ? C.ink : C.gold }}>{r.roe}%</td>
                <td style={{ fontFamily: 'monospace', fontSize: 11, color: r.de < 0.5 ? C.green : r.de < 1.5 ? C.ink : C.gold }}>{r.de}</td>
                <td><Pill type={r.sig}>{r.sig === 'g' ? 'Strong' : r.sig === 'gold' ? 'Moderate' : 'Weak'}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GeoPage() {
  const hist = [
    ['Iran-Israel Apr 2024', '2 weeks', 'Oil +8%, Gold +6%, Aviation -4%', '-1.2%'],
    ['Russia-Ukraine Feb 2022', '3 months', 'Defence +22%, Oil +32%, Metals +14%', '-8.4%'],
    ['COVID Mar 2020', '6 months', 'Pharma +18%, Aviation -45%, IT -12%', '-38%'],
    ['India-China Galwan 2020', '1 month', 'Defence +15%, China-exposed -8%', '-3.6%'],
  ];

  return (
    <div>
      <div className="geo-alert">
        <div className="geo-alert-top">
          <div className="pulse-dot" />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: C.red }}>Active High Risk Alert</span>
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: C.ink, marginBottom: 3 }}>Middle East tensions elevated — Strait of Hormuz disruption risk</div>
        <div style={{ fontSize: 11, color: C.ink2 }}>Affects: Oil &amp; Gas · Aviation · Gold/Silver safe-haven · Defence opportunity | Updated 2 hours ago · 14 sources</div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Global Pulse Feed</div>
          {GEO_EVENTS.map((e, i) => (
            <div key={i} className={`event-card ${e.cls}`}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className={`pill ${e.tag === 'CONFLICT' || e.tag === 'OIL' ? 'pill-r' : e.tag === 'COMMODITY' || e.tag === 'AGRI' ? 'pill-gold' : 'pill-b'}`}>{e.tag}</span>
                {e.cls === 'ev-gold' && <span style={{ fontSize: 9, color: C.gold, fontWeight: 700 }}>● GOLD SAFE HAVEN</span>}
              </div>
              <div style={{ fontSize: 11, color: C.ink, lineHeight: 1.5 }}>{e.title}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="ct">Sector Risk Matrix · Live</div>
          {GEO_SECTORS.map(g => (
            <div key={g.s} className="stat-r">
              <span className="sl" style={{ minWidth: 110 }}>{g.s}</span>
              <div style={{ flex: 1, margin: '0 10px' }}>
                <div className="bar-track" style={{ height: 4 }}>
                  <div className="bar-fill" style={{ width: `${g.risk}%`, background: g.c === 'r' ? C.red : g.c === 'g' ? C.green : C.gold }} />
                </div>
              </div>
              <span className={`pill pill-${g.c}`} style={{ fontSize: 8, minWidth: 72, justifyContent: 'center' }}>{g.impact}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="ct">Historical Precedents — How Markets Reacted</div>
        <table className="tbl">
          <thead><tr><th>Event</th><th>Period</th><th>Key Sector Impact</th><th>Nifty Move</th></tr></thead>
          <tbody>
            {hist.map(([e, p, s, n]) => (
              <tr key={e}>
                <td style={{ fontWeight: 600 }}>{e}</td>
                <td style={{ color: C.ink2, fontSize: 11 }}>{p}</td>
                <td style={{ color: C.ink2, fontSize: 11 }}>{s}</td>
                <td style={{ fontWeight: 700, color: (n as string).startsWith('-') ? C.red : C.green }}>{n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PremiumPage({ onNav }: { onNav: (p: Page) => void }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, padding: '14px 18px', background: 'var(--gold2)', border: '1px solid var(--border-gold)', borderRadius: 10, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 20 }}>★</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.gold }}>Sovereign Intelligence · Premium Active</div>
          <div style={{ fontSize: 11, color: C.ink2, marginTop: 2 }}>Tailored to your investment profile · Geopolitics-adjusted · Updated daily</div>
        </div>
        <button className="btn-gold" onClick={() => onNav('profile')}>Edit Profile →</button>
      </div>

      <div className="g2" style={{ marginBottom: 14 }}>
        <div className="card">
          <div className="ct">Your Profile Summary</div>
          <StatRow label="Capital Range" value="₹50K – ₹2L" />
          <StatRow label="Horizon" value="1–3 Years" />
          <StatRow label="Risk Appetite" value="Moderate" />
          <StatRow label="Preferred Sectors" value="IT · Pharma · Auto" />
          <StatRow label="Geopolitics Adjusted" value="Yes ✓" valueStyle={{ color: C.green }} />
        </div>
        <div className="card card-gold">
          <div className="ct" style={{ color: C.gold }}>Tailored Matches Today</div>
          <div className="bn bn-gold" style={{ marginBottom: 6 }}>7</div>
          <div style={{ fontSize: 11, color: C.ink2, marginBottom: 10 }}>Niche picks calibrated to your risk, capital &amp; current geopolitical conditions</div>
          <div style={{ fontSize: 10, color: C.ink3 }}>3 flagged as current opportunity · 1 geo-risk warning</div>
        </div>
      </div>

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Tailored Matches · Niche Picks</div>
      <div className="g2">
        {NICHE.map(n => (
          <div key={n.name} className="niche-card">
            <div className="risk-match" style={{ background: 'rgba(0,230,118,.1)', color: C.green, border: '1px solid rgba(0,230,118,.2)' }}>{n.match}% Match</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 3, paddingRight: 80 }}>{n.name}</div>
            <div style={{ fontSize: 10, color: C.ink3, marginBottom: 8 }}>{n.sector}</div>
            <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.6, marginBottom: 10 }}>{n.why}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Pill type="g">{n.risk} Risk</Pill>
              <Pill type="gold">{n.tag}</Pill>
              <span style={{ fontSize: 10, color: C.ink3, alignSelf: 'center' }}>PE {n.pe}× · ROE {n.roe}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProfilePage({ onNav }: { onNav: (p: Page) => void }) {
  const [capital, setCapital] = useState(100000);
  const [risk, setRisk] = useState('Moderate');
  const [sectors, setSectors] = useState(['IT', 'Pharma', 'Auto']);
  const riskDescs: Record<string, string> = {
    Conservative: 'Conservative: Protects capital first. Targets 10–14% CAGR. Suitable for 3+ year horizon with low drawdown tolerance.',
    Moderate: 'Moderate: Accepts 15–20% drawdown for 18–24% CAGR. Best for 1–3 year horizon with quality focus.',
    Aggressive: 'Aggressive: Tolerates 30%+ drawdown for 30%+ CAGR. High-conviction bets. 3+ year horizon required.',
  };

  return (
    <div className="g2">
      <div>
        <div className="profile-step">
          <div className="ps-num">1</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Investment Capital</div>
          <div className="field-label">Available capital (₹)</div>
          <input type="range" className="range-input" style={{ width: '100%', margin: '10px 0 4px' }}
            min={10000} max={1000000} step={5000} value={capital} onChange={e => setCapital(Number(e.target.value))} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: C.ink3, marginBottom: 6 }}>
            <span>₹10K</span>
            <span style={{ color: C.blue, fontWeight: 700 }}>{formatINR(capital)}</span>
            <span>₹10L+</span>
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">2</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Investment Horizon</div>
          <div className="seg-row">
            {['3 Months', '1 Year', '3 Years', '5+ Years'].map(h => (
              <button key={h} className={`seg-btn${h === '1 Year' ? ' active' : ''}`}>{h}</button>
            ))}
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">3</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Risk Appetite</div>
          <div className="seg-row">
            {['Conservative', 'Moderate', 'Aggressive'].map(r => (
              <button key={r} className={`seg-btn${r === risk ? ' active' : ''}`} onClick={() => setRisk(r)}>{r}</button>
            ))}
          </div>
          <div style={{ marginTop: 10, padding: '9px 12px', background: 'var(--s2)', borderRadius: 7, fontSize: 10, color: C.ink2, lineHeight: 1.6 }}>
            {riskDescs[risk]}
          </div>
        </div>

        <div className="profile-step">
          <div className="ps-num">4</div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Sector Preferences</div>
          <div className="seg-row" style={{ flexWrap: 'wrap' }}>
            {['IT', 'Banking', 'Pharma', 'FMCG', 'Auto', 'Defence', 'Real Estate'].map(s => (
              <button key={s} className={`seg-btn${sectors.includes(s) ? ' active' : ''}`}
                onClick={() => setSectors(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])}>{s}</button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="card card-gold" style={{ marginBottom: 10 }}>
          <div className="ct" style={{ color: C.gold }}>Your Investment DNA</div>
          <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 5 }}>Balanced Growth</div>
          <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.7, marginBottom: 14 }}>Seeks steady compounding with managed downside. Focus on quality mid-caps with strong ROE and low debt. Suitable for 1–3 year horizon.</div>
          <StatRow label="Suggested allocation" value="60% Equity · 40% Hybrid" valueStyle={{ color: C.blue }} />
          <StatRow label="Expected CAGR (3yr)" value="18–24%" valueStyle={{ color: C.green }} />
          <StatRow label="Niche matches" value="7 stocks today" valueStyle={{ color: C.gold }} />
        </div>
        <div className="card" style={{ marginBottom: 10 }}>
          <div className="ct">Geopolitical Risk Overlay</div>
          <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.7, marginBottom: 10 }}>Current Middle East tensions have <strong style={{ color: C.gold }}>moderate impact</strong> on your sector preferences.</div>
          <StatRow label="Oil sensitivity" value={<Pill type="g">Low</Pill>} />
          <StatRow label="USD revenue exposure" value={<Pill type="g">High (IT)</Pill>} />
          <StatRow label="Defence opportunity" value={<Pill type="g">Yes ↑</Pill>} />
          <StatRow label="Gold safe-haven relevance" value={<Pill type="gold">Moderate</Pill>} />
        </div>
        <button className="btn-blue" style={{ width: '100%' }} onClick={() => onNav('premium')}>Get My Niche Matches ↗</button>
      </div>
    </div>
  );
}

function PaperTradingPage() {
  const [cash, setCash] = useState(100000);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [dayCount, setDayCount] = useState(0);
  const [completedMissions, setCompletedMissions] = useState<Set<string>>(new Set());
  const [ptStock, setPtStock] = useState('INFY|1842');
  const [ptQty, setPtQty] = useState(5);
  const [ptSl, setPtSl] = useState(7);
  const [toast, setToast] = useState<{ msg: string; color: string } | null>(null);
  const [insight, setInsight] = useState('');

  const showToast = (msg: string, color = C.blue) => {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 3200);
  };

  const [sym, priceStr] = ptStock.split('|');
  const price = parseFloat(priceStr);
  const estCost = Math.round(price * ptQty);

  const inv = holdings.reduce((s, h) => s + h.qty * h.avgCost, 0);
  const mkt = holdings.reduce((s, h) => s + h.qty * h.ltp, 0);
  const pnl = mkt - inv;
  const total = cash + mkt;
  const pnlPct = inv > 0 ? (pnl / inv * 100).toFixed(2) : '0.00';

  const updateInsight = (hs: Holding[]) => {
    const totalInvested = hs.reduce((s, h) => s + h.qty * h.avgCost, 0);
    for (const h of hs) {
      const pct = h.qty * h.avgCost / (totalInvested || 1);
      if (pct > 0.30) { setInsight(`${h.sym} is >${Math.round(pct * 100)}% of portfolio — consider reducing concentration.`); return; }
      const pp = ((h.ltp - h.avgCost) / h.avgCost * 100);
      if (pp > 15) { setInsight(`${h.sym} is up ${pp.toFixed(1)}% — consider booking partial profits.`); return; }
    }
    setInsight('');
  };

  const ptTrade = (side: 'BUY' | 'SELL') => {
    if (side === 'BUY') {
      const total = price * ptQty + 29;
      if (total > cash) { showToast('Insufficient capital', C.red); return; }
      setHoldings(prev => {
        const ex = prev.find(h => h.sym === sym);
        let next: Holding[];
        if (ex) {
          next = prev.map(h => h.sym === sym ? { ...h, qty: h.qty + ptQty, avgCost: (h.avgCost * h.qty + price * ptQty) / (h.qty + ptQty), sl: price * (1 - ptSl / 100) } : h);
        } else {
          next = [...prev, { sym, qty: ptQty, avgCost: price, ltp: price, sl: price * (1 - ptSl / 100), daysHeld: 0, hist: [price] }];
        }
        updateInsight(next);
        return next;
      });
      setCash(c => c - total);
      setCompletedMissions(m => new Set([...m, 'first-trade']));
      showToast(`Bought ${ptQty} × ${PT_STOCKS[sym]?.n || sym} @ ${formatINR(price)}`, C.green);
    } else {
      const h = holdings.find(h => h.sym === sym);
      if (!h) { showToast('No position in ' + sym, C.red); return; }
      setCash(c => c + h.ltp * h.qty - 29);
      setHoldings(prev => prev.filter(x => x.sym !== sym));
      showToast(`Exited ${sym}`, C.gold);
    }
  };

  const simDay = () => {
    if (!holdings.length) { showToast('No holdings to simulate'); return; }
    setDayCount(d => d + 1);
    const completed = new Set(completedMissions);
    setHoldings(prev => {
      let next = prev.map(h => {
        const vol = PT_STOCKS[h.sym]?.vol || 0.018;
        const ltp = Math.max(1, Math.round(h.ltp * (1 + (Math.random() - 0.47) * vol * 2)));
        const hist = [...h.hist, ltp].slice(-12);
        const daysHeld = h.daysHeld + 1;
        if (ltp <= h.sl) {
          setCash(c => c + ltp * h.qty - 29);
          showToast(`Stop loss: ${h.sym} exited @ ${formatINR(ltp)}`, C.red);
          completed.add('stop-loss');
        }
        if (daysHeld >= 3 && ltp < h.avgCost) completed.add('survive-red');
        return { ...h, ltp, hist, daysHeld };
      }).filter(h => h.ltp > h.sl);
      const sectors = new Set(next.map(h => h.sym));
      if (sectors.size >= 3) completed.add('diversify');
      setCompletedMissions(completed);
      updateInsight(next);
      return next;
    });
    showToast(`Day ${dayCount + 1} simulated — markets moved`, C.blue);
  };

  const quickExit = (exitSym: string) => {
    const h = holdings.find(x => x.sym === exitSym);
    if (!h) return;
    setCash(c => c + h.ltp * h.qty - 29);
    setHoldings(prev => prev.filter(x => x.sym !== exitSym));
    showToast('Exited ' + exitSym, C.gold);
  };

  const missions = [
    { id: 'first-trade', title: 'First Trade', desc: 'Execute your first buy order.', ic: 'm-ic-blue' },
    { id: 'diversify', title: 'Diversification', desc: 'Hold 3+ different stocks simultaneously.', ic: 'm-ic-blue' },
    { id: 'stop-loss', title: 'Stop Loss', desc: 'Watch a stop loss trigger in simulation.', ic: 'm-ic-gold' },
    { id: 'survive-red', title: 'Hold Through Red', desc: 'Keep a losing position for 3+ simulated days.', ic: 'm-ic-gold' },
    { id: 'golden-hour', title: 'Golden Hour', desc: 'Buy a stock during a market dip.', ic: 'm-ic-gold' },
    { id: 'week-profit', title: 'Green Week', desc: 'End 7 simulated days with overall profit.', ic: 'm-ic-blue' },
  ];

  return (
    <div>
      {toast && (
        <div className="toast show">
          <span style={{ color: toast.color }}>{toast.msg}</span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
        <div className="sim-badge"><div className="sim-dot" />Simulation Mode · Virtual ₹1,00,000</div>
        <button className="btn-ghost" style={{ fontSize: 10 }} onClick={simDay}>Simulate Next Day ↻</button>
      </div>

      <div className="g4" style={{ marginBottom: 12 }}>
        <div className="card card-blue">
          <div className="ct" style={{ color: C.blue }}>Virtual Capital</div>
          <div className="bn bn-blue">{formatINR(total)}</div>
          <div style={{ fontSize: 9, color: C.ink3, marginTop: 3 }}>Total portfolio value</div>
        </div>
        <div className="card card-gold">
          <div className="ct" style={{ color: C.gold }}>Savings Potential</div>
          <div className="bn bn-gold">{formatINR(total * 0.18)}</div>
          <div style={{ fontSize: 9, color: C.ink3, marginTop: 3 }}>Projected 1yr at 18% avg</div>
        </div>
        <div className="card">
          <div className="ct">Unrealised P&amp;L</div>
          <div className="bn" style={{ color: pnl >= 0 ? C.green : C.red }}>{pnl >= 0 ? '+' : '-'}{formatINR(Math.abs(pnl))}</div>
          <div style={{ fontSize: 9, marginTop: 3, color: pnl >= 0 ? C.green : C.red }}>{pnl >= 0 ? '+' : ''}{pnlPct}%</div>
        </div>
        <div className="card">
          <div className="ct">Available Cash</div>
          <div className="bn">{formatINR(cash)}</div>
          <div style={{ fontSize: 9, color: C.green, marginTop: 3 }}>Free to deploy</div>
        </div>
      </div>

      <div className="g2" style={{ marginBottom: 12 }}>
        <div className="card">
          <div className="ct">Execute Trade</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
            <div>
              <div className="field-label">Stock</div>
              <select className="fi" value={ptStock} onChange={e => setPtStock(e.target.value)}>
                <option value="INFY|1842">Infosys · ₹1,842</option>
                <option value="HDFCBANK|1623">HDFC Bank · ₹1,623</option>
                <option value="TATAMOTORS|934">Tata Motors · ₹934</option>
                <option value="ZOMATO|224">Zomato · ₹224</option>
                <option value="RELIANCE|2934">Reliance · ₹2,934</option>
              </select>
            </div>
            <div>
              <div className="field-label">Quantity</div>
              <input className="fi" type="number" value={ptQty} min={1} onChange={e => setPtQty(Number(e.target.value))} />
            </div>
            <div>
              <div className="field-label">Order Type</div>
              <select className="fi"><option>Market Order</option><option>Limit Order</option><option>Stop Loss</option></select>
            </div>
            <div>
              <div className="field-label">Stop Loss %</div>
              <input className="fi" type="number" value={ptSl} min={1} max={20} onChange={e => setPtSl(Number(e.target.value))} />
            </div>
          </div>
          <div className="nudge">Mission 1: Set a Stop Loss to protect your capital — every trade needs one.</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: C.ink3, margin: '9px 0 10px' }}>
            <span>Est. cost: <strong style={{ color: C.blue }}>{formatINR(estCost)}</strong></span>
            <span>Brokerage + STT: <strong style={{ color: C.ink2 }}>₹29</strong></span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <button className="btn-blue" onClick={() => ptTrade('BUY')}>Buy / Long ↗</button>
            <button className="btn-ghost" style={{ color: C.red, borderColor: 'rgba(255,58,58,.2)' }} onClick={() => ptTrade('SELL')}>Exit Position</button>
          </div>
        </div>

        <div className="card">
          <div className="ct">Holdings</div>
          {holdings.length === 0 ? (
            <div style={{ fontSize: 11, color: C.ink3, padding: '16px 0', textAlign: 'center' }}>No positions yet. Execute a trade to begin.</div>
          ) : (
            <>
              <table className="tbl">
                <thead><tr><th>Stock</th><th>Qty</th><th>Avg</th><th>LTP</th><th>P&amp;L</th><th>Exit</th></tr></thead>
                <tbody>
                  {holdings.map(h => {
                    const hPnl = (h.ltp - h.avgCost) * h.qty;
                    const hPnlPct = ((h.ltp - h.avgCost) / h.avgCost * 100).toFixed(1);
                    const hc = hPnl >= 0 ? C.green : C.red;
                    const mn = Math.min(...h.hist), mx = Math.max(...h.hist), r = mx - mn || 1;
                    return (
                      <tr key={h.sym}>
                        <td>
                          <div style={{ fontWeight: 600, fontSize: 11 }}>{h.sym}</div>
                          <div className="sparkline" style={{ marginTop: 3 }}>
                            {h.hist.map((v, i) => (
                              <div key={i} className="spark-b" style={{ height: `${Math.max(10, (v - mn) / r * 100)}%`, background: v >= h.avgCost ? C.green : C.red }} />
                            ))}
                          </div>
                        </td>
                        <td style={{ fontFamily: 'monospace' }}>{h.qty}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{formatINR(h.avgCost)}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{formatINR(h.ltp)}</td>
                        <td>
                          <div style={{ fontFamily: 'monospace', fontSize: 11, color: hc }}>{hPnl >= 0 ? '+' : '-'}{formatINR(Math.abs(hPnl))}</div>
                          <div style={{ fontFamily: 'monospace', fontSize: 9, color: hc }}>{hPnl >= 0 ? '+' : ''}{hPnlPct}%</div>
                        </td>
                        <td>
                          <button onClick={() => quickExit(h.sym)} style={{ background: 'transparent', border: '1px solid var(--border)', color: C.ink2, borderRadius: 5, padding: '3px 9px', fontSize: 9, cursor: 'pointer', fontFamily: 'var(--f)' }}>EXIT</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {insight && <div className="nudge" style={{ marginTop: 8 }}>{insight}</div>}
            </>
          )}
        </div>
      </div>

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.ink3, marginBottom: 10 }}>Learning Missions</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
        {missions.map(m => {
          const done = completedMissions.has(m.id);
          return (
            <div key={m.id} className={`mission-card${done ? ' done' : ''}`}>
              <div className={`m-ic ${done ? 'm-ic-green' : m.ic}`}>{done ? '✓' : '→'}</div>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>{m.title}</div>
              <div style={{ fontSize: 10, color: C.ink3, lineHeight: 1.5, marginBottom: 6 }}>{m.desc}</div>
              <div style={{ fontSize: 9, fontWeight: 700, color: done ? C.green : C.ink3 }}>
                {done ? 'COMPLETED' : m.id === 'diversify' ? `${holdings.length}/3 sectors` : 'In progress'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RHPPage() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<null | 'done'>(null);

  const rhpDemo = () => {
    setScanning(true);
    setTimeout(() => { setScanning(false); setResults('done'); }, 1400);
  };

  const risks = [
    { level: 'HIGH', c: 'r', title: 'Concentrated Revenue Risk', body: 'Top 3 customers account for 68% of total revenue — significant client concentration risk.' },
    { level: 'HIGH', c: 'r', title: 'Promoter Litigation Pending', body: '2 civil suits pending against promoter group for ₹42 Cr. Material if adverse judgment.' },
    { level: 'MED', c: 'gold', title: 'Use of Proceeds — Partial Clarity', body: '₹420 Cr for "general corporate purposes" lacks specific deployment plan in DRHP.' },
    { level: 'LOW', c: 'g', title: 'Peer Comparison Fair', body: 'Comparable company selection methodology is appropriate and disclosed transparently.' },
    { level: 'MED', c: 'gold', title: 'EV Market Dependency', body: '100% revenue from EV segment — highly sensitive to EV adoption rate changes and subsidy policy.' },
  ];

  return (
    <div className="g2">
      <div>
        <div className="rhp-upload" onClick={rhpDemo} style={{ opacity: scanning ? 0.5 : 1 }}>
          <div style={{ fontSize: 32, marginBottom: 10, opacity: 0.4 }}>📄</div>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 5 }}>Upload RHP / DRHP</div>
          <div style={{ fontSize: 11, color: C.ink2, marginBottom: 14 }}>AI extracts key risk factors in seconds. Drop a PDF or click to browse.</div>
          <button className="btn-blue" onClick={e => { e.stopPropagation(); rhpDemo(); }}>Try Demo: Ather Energy DRHP ↗</button>
        </div>
        <div className="card" style={{ marginTop: 12 }}>
          <div className="ct">What We Scan For</div>
          <StatRow label="Related party transactions" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Promoter litigation" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Revenue concentration" value={<Pill type="gold">Medium</Pill>} />
          <StatRow label="DRHP vs actual financials" value={<Pill type="r">High Risk</Pill>} />
          <StatRow label="Use of proceeds clarity" value={<Pill type="g">Low Risk</Pill>} />
          <StatRow label="Peer comparison fairness" value={<Pill type="gold">Medium</Pill>} />
        </div>
      </div>

      <div>
        {results === null ? (
          <div className="card" style={{ textAlign: 'center', padding: 36 }}>
            <div style={{ fontSize: 28, opacity: 0.2, marginBottom: 8 }}>◈</div>
            <div style={{ fontSize: 12, color: C.ink3 }}>Upload a DRHP or try the demo to see AI risk extraction</div>
          </div>
        ) : (
          <div className="card" style={{ marginBottom: 10 }}>
            <div className="ct">RHP Analysis · Ather Energy DRHP</div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
              <span className="pill pill-gold">Risk Score: 58/100</span>
              <span className="pill pill-gold">MODERATE RISK</span>
            </div>
            <div style={{ fontSize: 11, color: C.ink2, marginBottom: 12, lineHeight: 1.6 }}>AI extracted {risks.length} key risk factors from 342 pages. 2 high-severity items require attention before subscribing.</div>
            {risks.map(r => (
              <div key={r.title} className="rhp-risk-item">
                <div className="status-dot" style={{ background: r.c === 'r' ? C.red : r.c === 'g' ? C.green : C.gold, boxShadow: `0 0 5px ${r.c === 'r' ? C.red : r.c === 'g' ? C.green : C.gold}`, marginTop: 3, flexShrink: 0 }} />
                <div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: C.ink }}>{r.title}</span>
                    <span className={`pill pill-${r.c}`} style={{ fontSize: 8 }}>{r.level}</span>
                  </div>
                  <div style={{ fontSize: 11, color: C.ink2, lineHeight: 1.6 }}>{r.body}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── MAIN APP ────────────────────────────────────────────────────────────────

export default function StockSensePage() {
  const [inApp, setInApp] = useState(false);
  const [activePage, setActivePage] = useState<Page>('dashboard');
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  const navTo = (page: Page) => setActivePage(page);
  const enter = (page: Page) => { setInApp(true); setActivePage(page); };

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
        .mc-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
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