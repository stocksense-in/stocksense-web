import type { SectorCode } from './types';

/** Mirrors SECTOR_LABELS in backend/stocksense/sectors.py. */
export const SECTOR_LABELS: Record<SectorCode, string> = {
  it: 'IT Services',
  bank: 'Banking',
  nbfc: 'NBFC',
  finance: 'Financial Services',
  newage: 'New-age Tech',
  defence: 'Defence',
  electronics: 'Electronics',
  auto: 'Automobile',
  telecom: 'Telecom & Media',
  consumer: 'Consumer Discretionary',
  fmcg: 'FMCG',
  pharma: 'Pharma & Healthcare',
  materials: 'Metals & Materials',
  industrial: 'Industrials',
  energy: 'Energy',
  realestate: 'Real Estate',
  utilities: 'Utilities',
  general: 'Other',
};

export function sectorLabel(code: string | null | undefined): string {
  return SECTOR_LABELS[(code ?? 'general') as SectorCode] ?? 'Other';
}

export const SECTOR_OPTIONS = (Object.keys(SECTOR_LABELS) as SectorCode[])
  .filter((s) => s !== 'general')
  .sort((a, b) => SECTOR_LABELS[a].localeCompare(SECTOR_LABELS[b]));
