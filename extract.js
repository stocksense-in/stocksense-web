const fs = require('fs');

const code = fs.readFileSync('app/page.tsx', 'utf-8');

const mkdir = p => !fs.existsSync(p) && fs.mkdirSync(p, { recursive: true });
mkdir('lib');
mkdir('components/ui');
mkdir('components/cards');
mkdir('components/sections');

const extract = (regex) => {
  const match = code.match(regex);
  return match ? match[0] : '';
};

// Types
const typesCode = `export type Page = 'dashboard' | 'analysis' | 'ipo' | 'screener'
  | 'geo' | 'premium' | 'profile' | 'paper' | 'rhp';

export type Sector = 'it' | 'bank' | 'auto' | 'newage' | 'fmcg' | 'pharma' | 'defence' | 'nbfc' | 'electronics';

export interface StockData {
  ticker: string; sub: string; price: string; chg: string;
  score: number; sector: Sector;
  data: { pe: number; roe: number; de: number; margin: number; promoter: number; cagr: number };
  ctx: { idealPE: string; avgROE: number; idealDE: string; avgMargin: number; sectorCAGR: number; promoterNote: string; cagr: number; pe: number; margin: number };
}

export interface Holding {
  sym: string; qty: number; avgCost: number; ltp: number;
  sl: number; daysHeld: number; hist: number[];
}

export interface IPO {
  name: string; sector: string; open: string; size: string;
  score: number; gmp: number; qib: number; retail: number;
  fund: number; geo: number; verdict: string; band: string;
}

export type MetricKey = 'pe' | 'roe' | 'de' | 'margin' | 'promoter' | 'cagr';

export interface MetricMeta {
  name: string; unit: string; il: string; lo: string; hi: string;
  norm: (v: number, s?: string) => number;
  iz: (s?: string) => [number, number];
  plain: (v: number, s?: string) => string;
  verd: (v: number, s?: string) => string;
}
`;
fs.writeFileSync('lib/types.ts', typesCode);

// Extract constants
const sdCode = extract(/const SD: Record<string, StockData> = [\s\S]*?};\n/);
const mmCode = extract(/const MM: Record<MetricKey, MetricMeta> = [\s\S]*?};\n/);
const iposCode = extract(/const IPOS: IPO\[\] = [\s\S]*?];\n/);
const screenerCode = extract(/const SCREENER = [\s\S]*?];\n/);
const geosectorsCode = extract(/const GEO_SECTORS = [\s\S]*?];\n/);
const geoeventsCode = extract(/const GEO_EVENTS = [\s\S]*?];\n/);
const nicheCode = extract(/const NICHE = [\s\S]*?];\n/);
const ptstocksCode = extract(/const PT_STOCKS: Record<string, { n: string; vol: number }> = [\s\S]*?};\n/);
const pagetitlesCode = extract(/const PAGE_TITLES: Record<Page, string> = [\s\S]*?};\n/);
const navitemsCode = extract(/const NAV_ITEMS: [\s\S]*?];\n/);
const cCode = extract(/const C = [\s\S]*?};\n/);

const constantsCode = `import { StockData, MetricKey, MetricMeta, IPO, Page } from './types';

export ${sdCode.replace('const SD', 'const SD')}
export ${mmCode.replace('const MM', 'const MM')}
export ${iposCode.replace('const IPOS', 'const IPOS')}
export ${screenerCode.replace('const SCREENER', 'const SCREENER')}
export ${geosectorsCode.replace('const GEO_SECTORS', 'const GEO_SECTORS')}
export ${geoeventsCode.replace('const GEO_EVENTS', 'const GEO_EVENTS')}
export ${nicheCode.replace('const NICHE', 'const NICHE')}
export ${ptstocksCode.replace('const PT_STOCKS', 'const PT_STOCKS')}
export ${pagetitlesCode.replace('const PAGE_TITLES', 'const PAGE_TITLES')}
export ${navitemsCode.replace('const NAV_ITEMS', 'const NAV_ITEMS')}
export ${cCode.replace('const C', 'const C')}
`;
fs.writeFileSync('lib/constants.ts', constantsCode);

const utilsCode = `import { MetricKey } from './types';
import { MM, C } from './constants';

export ${extract(/function pillClass[\s\S]*?}/)}

export ${extract(/function getMetricStatus[\s\S]*?return 'red';\n}/)}

export ${extract(/function scoreColor[\s\S]*?}/)}

export ${extract(/function formatINR[\s\S]*?}/)}
`;
fs.writeFileSync('lib/utils.ts', utilsCode);

// UI Components
const pillCode = `'use client';\nimport React from 'react';\nimport { pillClass } from '@/lib/utils';\n\nexport ${extract(/function Pill[\s\S]*?}/)}`;
fs.writeFileSync('components/ui/Pill.tsx', pillCode);

const statRowCode = `'use client';\nimport React from 'react';\n\nexport ${extract(/function StatRow[\s\S]*?}\n\n/)}`.trim();
fs.writeFileSync('components/ui/StatRow.tsx', statRowCode);

const sectionDivCode = `'use client';\nimport React from 'react';\n\nexport ${extract(/function SectionDiv[\s\S]*?}\n\n/)}`.trim();
fs.writeFileSync('components/ui/SectionDiv.tsx', sectionDivCode);


// Cards
const candleChartCode = `'use client';\nimport React from 'react';\nimport { C } from '@/lib/constants';\n\nexport ${extract(/function CandleChart\(\) {[\s\S]*?}\n\n/)}`.trim();
fs.writeFileSync('components/cards/CandleChart.tsx', candleChartCode);

const metricCardCode = `'use client';\nimport React, { useState } from 'react';\nimport { MetricKey } from '@/lib/types';\nimport { MM, C } from '@/lib/constants';\nimport { getMetricStatus, pillClass } from '@/lib/utils';\n\nexport ${extract(/function MetricCard\({ mk, val, sector }: { mk: MetricKey; val: number; sector: string }\) {[\s\S]*?}\n\n/)}`.trim();
fs.writeFileSync('components/cards/MetricCard.tsx', metricCardCode);

// Sections
const sections = ['DashboardPage', 'AnalysisPage', 'IPOPage', 'ScreenerPage', 'GeoPage', 'PremiumPage', 'ProfilePage', 'PaperTradingPage', 'RHPPage'];

sections.forEach(sec => {
  let fnRegex = new RegExp(\`function \${sec}\\([\\s\\S]*?\\n}\\n\\nfunction \`);
  let content = extract(fnRegex);
  if (!content) {
    if (sec === 'DashboardPage') {
      let reg = new RegExp(\`function \${sec}\\([\\s\\S]*?\\n}\\n\\nfunction AnalysisPage\`);
      content = extract(reg).replace(/\\n\\nfunction AnalysisPage$/, '');
    } else if (sec === 'PremiumPage') {
      let reg = new RegExp(\`function \${sec}\\([\\s\\S]*?\\n}\\n\\nfunction ProfilePage\`);
      content = extract(reg).replace(/\\n\\nfunction ProfilePage$/, '');
    } else if (sec === 'RHPPage') {
      let reg = new RegExp(\`function \${sec}\\([\\s\\S]*?\\n}\\n\\n\\/\\/ ─── MAIN APP\`);
      content = extract(reg).replace(/\\n\\n\\/\\/ ─── MAIN APP$/, '');
    } else {
      let reg = new RegExp(\`function \${sec}\\([\\s\\S]*?\\n}\\n\\nfunction \`);
      content = extract(reg).replace(/\\n\\nfunction $/, '');
    }
  } else {
    content = content.replace(/\\n\\nfunction $/, '');
  }

  let imports = \`'use client';\\nimport React, { useState, useEffect, useCallback, useRef } from 'react';\\nimport { Page, StockData, Holding, IPO, MetricKey, MetricMeta, Sector } from '@/lib/types';\\nimport { SD, MM, IPOS, SCREENER, GEO_SECTORS, GEO_EVENTS, NICHE, PT_STOCKS, PAGE_TITLES, NAV_ITEMS, C } from '@/lib/constants';\\nimport { pillClass, getMetricStatus, scoreColor, formatINR } from '@/lib/utils';\\nimport { supabase } from '@/lib/supabase';\\nimport { Pill } from '@/components/ui/Pill';\\nimport { StatRow } from '@/components/ui/StatRow';\\nimport { SectionDiv } from '@/components/ui/SectionDiv';\\nimport { CandleChart } from '@/components/cards/CandleChart';\\nimport { MetricCard } from '@/components/cards/MetricCard';\\n\n\`;
  fs.writeFileSync(\`components/sections/\${sec}.tsx\`, imports + 'export ' + content);
});

console.log("Done extracting.");
