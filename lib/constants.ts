import { StockData, MetricKey, MetricMeta, IPO, Page } from './types';

export const SD: Record<string, StockData> = {
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

export const MM: Record<MetricKey, MetricMeta> = {
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

export const IPOS: IPO[] = [
  { name: 'Ather Energy', sector: 'EV / Auto', open: 'Apr 28', size: '₹2,626 Cr', score: 72, gmp: 68, qib: 85, retail: 72, fund: 65, geo: 60, verdict: 'Subscribe', band: '₹304–321' },
  { name: 'Hexaware Technologies', sector: 'IT Services', open: 'May 5', size: '₹8,750 Cr', score: 68, gmp: 55, qib: 78, retail: 65, fund: 70, geo: 72, verdict: 'Subscribe', band: '₹674–708' },
  { name: 'Smartworks', sector: 'Real Estate', open: 'Apr 22', size: '₹583 Cr', score: 51, gmp: 42, qib: 55, retail: 68, fund: 48, geo: 55, verdict: 'Risky', band: '₹387–407' },
  { name: 'Swiggy OFS', sector: 'Food Tech', open: 'May 12', size: '₹1,200 Cr', score: 44, gmp: 30, qib: 48, retail: 60, fund: 38, geo: 50, verdict: 'Avoid', band: '₹390–410' },
];

export const SCREENER = [
  { n: 'Infosys', s: 'IT', sc: 70, pe: 24.2, roe: 31, de: 0.08, sig: 'g' },
  { n: 'TCS', s: 'IT', sc: 74, pe: 28.1, roe: 45, de: 0.05, sig: 'g' },
  { n: 'HDFC Bank', s: 'Banking', sc: 75, pe: 18.4, roe: 16.8, de: 9.2, sig: 'g' },
  { n: 'Bajaj Finance', s: 'NBFC', sc: 62, pe: 31.2, roe: 22, de: 3.1, sig: 'gold' },
  { n: 'Tata Motors', s: 'Auto', sc: 58, pe: 8.2, roe: 38, de: 1.8, sig: 'gold' },
  { n: 'Sun Pharma', s: 'Pharma', sc: 66, pe: 33.4, roe: 14, de: 0.12, sig: 'gold' },
  { n: 'Zomato', s: 'Food Tech', sc: 48, pe: 320, roe: 3.1, de: 0.02, sig: 'r' },
  { n: 'IDFC First', s: 'Banking', sc: 45, pe: 22.1, roe: 9.8, de: 8.4, sig: 'r' },
];

export const GEO_SECTORS = [
  { s: 'Oil & Gas', risk: 88, impact: 'HIGH RISK', note: 'Strait of Hormuz disruption threatens crude supply', c: 'r' },
  { s: 'Defence & Aerospace', risk: 78, impact: 'OPPORTUNITY', note: 'India procurement acceleration — HAL, BEL, MTAR', c: 'g' },
  { s: 'Gold / Silver', risk: 72, impact: 'SAFE HAVEN', note: 'Demand spike on geopolitical risk aversion', c: 'gold' },
  { s: 'Aviation', risk: 75, impact: 'HIGH RISK', note: 'Fuel cost surge + route disruption risks', c: 'r' },
  { s: 'IT Services', risk: 18, impact: 'LOW RISK', note: 'USD revenue hedge — minimal direct exposure', c: 'g' },
  { s: 'FMCG', risk: 14, impact: 'LOW RISK', note: 'Domestic demand insulated from global shocks', c: 'g' },
  { s: 'Banking', risk: 32, impact: 'MODERATE', note: 'Inflation from crude affects RBI rate trajectory', c: 'gold' },
  { s: 'Pharma', risk: 20, impact: 'LOW RISK', note: 'API imports from China — monitor trade routes', c: 'g' },
];

export const GEO_EVENTS = [
  { title: 'Iran retaliatory strike — Hormuz closure risk elevated', tag: 'CONFLICT', cls: 'ev-red' },
  { title: 'India accelerates TEJAS Mk2 & Akash procurement', tag: 'DEFENCE', cls: '' },
  { title: 'Gold breaks ₹73,500 on safe-haven demand — MCX volumes 3×', tag: 'COMMODITY', cls: 'ev-gold' },
  { title: 'India-US trade pact framework — IT exports benefit in FY26', tag: 'TRADE', cls: '' },
  { title: 'Saudi Aramco cuts output 2% — Brent at $96/bbl', tag: 'OIL', cls: 'ev-red' },
  { title: 'Russia grain export deal collapses — agri commodity spike', tag: 'AGRI', cls: 'ev-gold' },
];

export const NICHE = [
  { name: 'MTAR Technologies', sector: 'Defence · Space', match: 92, pe: 42, roe: 18, why: 'JLR recovery + ISRO contracts. Aligns with moderate risk + defence tailwind.', risk: 'Low', tag: 'Geo Tailwind' },
  { name: "Divi's Laboratories", sector: 'Pharma · API', match: 88, pe: 58, roe: 16, why: 'High ROCE, zero debt, FDA cleared. Perfect for capital preservation.', risk: 'Low', tag: 'Defensive Pick' },
  { name: 'Kaynes Technology', sector: 'Electronics · EMS', match: 84, pe: 68, roe: 22, why: "India's EMS boom. PLI beneficiary. Revenue CAGR 38%. Niche moat.", risk: 'Moderate', tag: 'Niche Growth' },
  { name: 'Radico Khaitan', sector: 'Alcobev · FMCG', match: 79, pe: 62, roe: 14, why: 'Premium spirits demand rising. Low geo-risk. Steady cash flows.', risk: 'Low', tag: 'Defensive' },
];

export const PT_STOCKS: Record<string, { n: string; vol: number }> = {
  INFY: { n: 'Infosys', vol: 0.015 }, HDFCBANK: { n: 'HDFC Bank', vol: 0.012 },
  TATAMOTORS: { n: 'Tata Motors', vol: 0.022 }, ZOMATO: { n: 'Zomato', vol: 0.028 },
  RELIANCE: { n: 'Reliance', vol: 0.014 },
};

export const PAGE_TITLES: Record<Page, string> = {
  dashboard: 'Dashboard', analysis: 'Stock Analysis', ipo: 'IPO Analyser',
  screener: 'Screener', geo: 'Geopolitics Engine', premium: 'Niche Stocks · Premium',
  profile: 'Investment Profile', paper: 'Paper Trading Simulator', rhp: 'RHP Scanner',
};

export const NAV_ITEMS: { id: Page; icon: string; label: string; pro?: boolean }[] = [
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

export const C = {
  blue: 'var(--blue)', gold: 'var(--gold)', green: 'var(--green)', red: 'var(--red)',
  ink: 'var(--ink)', ink2: 'var(--ink2)', ink3: 'var(--ink3)',
};

