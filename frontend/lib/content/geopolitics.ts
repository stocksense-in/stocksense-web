/**
 * Geopolitical risk map. Hand-maintained sample data — the plan is to generate
 * it from a news feed; the page layout already expects this shape.
 */

export type Exposure = 'risk' | 'opportunity' | 'haven' | 'low';

export interface SectorExposure {
  sector: string;
  /** 0–100: how strongly current events move this sector. */
  sensitivity: number;
  exposure: Exposure;
  note: string;
}

export const EXPOSURE_LABEL: Record<Exposure, string> = {
  risk: 'At risk',
  opportunity: 'Opportunity',
  haven: 'Safe haven',
  low: 'Low exposure',
};

export const SECTOR_EXPOSURE: SectorExposure[] = [
  { sector: 'Oil & Gas', sensitivity: 88, exposure: 'risk', note: 'Strait of Hormuz disruption threatens crude supply.' },
  { sector: 'Defence & Aerospace', sensitivity: 78, exposure: 'opportunity', note: 'Faster domestic procurement — HAL, BEL, MTAR.' },
  { sector: 'Aviation', sensitivity: 75, exposure: 'risk', note: 'Fuel costs and route disruptions.' },
  { sector: 'Gold & Silver', sensitivity: 72, exposure: 'haven', note: 'Demand rises when investors get nervous.' },
  { sector: 'Banking', sensitivity: 32, exposure: 'low', note: 'Crude-led inflation could delay RBI rate cuts.' },
  { sector: 'Pharma', sensitivity: 20, exposure: 'low', note: 'Depends on Chinese APIs — watch trade routes.' },
  { sector: 'IT Services', sensitivity: 18, exposure: 'low', note: 'Dollar revenues act as a natural hedge.' },
  { sector: 'FMCG', sensitivity: 14, exposure: 'low', note: 'Domestic demand is insulated from global shocks.' },
];

export interface GeoEvent {
  title: string;
  topic: 'Conflict' | 'Defence' | 'Commodities' | 'Trade' | 'Oil' | 'Agriculture';
  affects: string[];
}

export const GEO_EVENTS: GeoEvent[] = [
  { title: 'Iran retaliatory strike raises Strait of Hormuz closure risk', topic: 'Conflict', affects: ['Oil & Gas', 'Aviation'] },
  { title: 'India accelerates Tejas Mk2 and Akash procurement', topic: 'Defence', affects: ['Defence & Aerospace'] },
  { title: 'Gold crosses ₹73,500 on safe-haven buying; MCX volumes triple', topic: 'Commodities', affects: ['Gold & Silver'] },
  { title: 'India–US trade framework: IT exports expected to benefit in FY26', topic: 'Trade', affects: ['IT Services'] },
  { title: 'Saudi Aramco cuts output 2%; Brent at $96 a barrel', topic: 'Oil', affects: ['Oil & Gas', 'Aviation'] },
  { title: 'Russia grain export deal collapses; agri commodities spike', topic: 'Agriculture', affects: ['FMCG'] },
];

export const PRECEDENTS = [
  { event: 'Iran–Israel, Apr 2024', lasted: '2 weeks', sectors: 'Oil +8%, Gold +6%, Aviation −4%', nifty: -1.2 },
  { event: 'Russia–Ukraine, Feb 2022', lasted: '3 months', sectors: 'Defence +22%, Oil +32%, Metals +14%', nifty: -8.4 },
  { event: 'India–China Galwan, Jun 2020', lasted: '1 month', sectors: 'Defence +15%, China-exposed −8%', nifty: -3.6 },
  { event: 'COVID crash, Mar 2020', lasted: '6 months', sectors: 'Pharma +18%, Aviation −45%, IT −12%', nifty: -38 },
];
