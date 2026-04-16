import re
import os

with open('app/page.tsx', 'r') as f:
    code = f.read()

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

mkdir('lib')
mkdir('components/ui')
mkdir('components/cards')
mkdir('components/sections')

def extract_match(regex):
    match = re.search(regex, code)
    return match.group(0) if match else ''

# Types
types_code = """export type Page = 'dashboard' | 'analysis' | 'ipo' | 'screener'
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
"""
with open('lib/types.ts', 'w') as f: f.write(types_code)

# Constants
sd_code = extract_match(r'const SD: Record<string, StockData> = [\s\S]*?};\n')
mm_code = extract_match(r'const MM: Record<MetricKey, MetricMeta> = [\s\S]*?};\n')
ipos_code = extract_match(r'const IPOS: IPO\[\] = [\s\S]*?];\n')
screener_code = extract_match(r'const SCREENER = [\s\S]*?];\n')
geosectors_code = extract_match(r'const GEO_SECTORS = [\s\S]*?];\n')
geoevents_code = extract_match(r'const GEO_EVENTS = [\s\S]*?];\n')
niche_code = extract_match(r'const NICHE = [\s\S]*?];\n')
ptstocks_code = extract_match(r'const PT_STOCKS: Record<string, { n: string; vol: number }> = [\s\S]*?};\n')
pagetitles_code = extract_match(r'const PAGE_TITLES: Record<Page, string> = [\s\S]*?};\n')
navitems_code = extract_match(r'const NAV_ITEMS: [\s\S]*?];\n')
c_code = extract_match(r'const C = [\s\S]*?};\n')

constants_code = f"""import {{ StockData, MetricKey, MetricMeta, IPO, Page }} from './types';

export {sd_code.replace('const SD', 'const SD')}
export {mm_code.replace('const MM', 'const MM')}
export {ipos_code.replace('const IPOS', 'const IPOS')}
export {screener_code.replace('const SCREENER', 'const SCREENER')}
export {geosectors_code.replace('const GEO_SECTORS', 'const GEO_SECTORS')}
export {geoevents_code.replace('const GEO_EVENTS', 'const GEO_EVENTS')}
export {niche_code.replace('const NICHE', 'const NICHE')}
export {ptstocks_code.replace('const PT_STOCKS', 'const PT_STOCKS')}
export {pagetitles_code.replace('const PAGE_TITLES', 'const PAGE_TITLES')}
export {navitems_code.replace('const NAV_ITEMS', 'const NAV_ITEMS')}
export {c_code.replace('const C', 'const C')}
"""
with open('lib/constants.ts', 'w') as f: f.write(constants_code)

# Utils
u1 = extract_match(r'function pillClass[\s\S]*?}')
u2 = extract_match(r'function getMetricStatus[\s\S]*?return \'red\';\n}')
u3 = extract_match(r'function scoreColor[\s\S]*?}')
u4 = extract_match(r'function formatINR[\s\S]*?}')

utils_code = f"""import {{ MetricKey }} from './types';
import {{ MM, C }} from './constants';

export {u1}

export {u2}

export {u3}

export {u4}
"""
with open('lib/utils.ts', 'w') as f: f.write(utils_code)

p1 = extract_match(r'function Pill[\s\S]*?}')
if p1:
    with open('components/ui/Pill.tsx', 'w') as f:
        f.write("'use client';\nimport React from 'react';\nimport { pillClass } from '@/lib/utils';\n\nexport " + p1)

s1 = extract_match(r'function StatRow[\s\S]*?}\n')
if s1:
    with open('components/ui/StatRow.tsx', 'w') as f:
        f.write("'use client';\nimport React from 'react';\n\nexport " + s1.strip())

se1 = extract_match(r'function SectionDiv[\s\S]*?}\n')
if se1:
    with open('components/ui/SectionDiv.tsx', 'w') as f:
        f.write("'use client';\nimport React from 'react';\n\nexport " + se1.strip())

c1 = extract_match(r'function CandleChart\(\) {[\s\S]*?}\n\n')
if c1:
    with open('components/cards/CandleChart.tsx', 'w') as f:
        f.write("'use client';\nimport React from 'react';\nimport { C } from '@/lib/constants';\n\nexport " + c1.strip())

m1 = extract_match(r'function MetricCard[\s\S]*?}\n\n')
if m1:
    with open('components/cards/MetricCard.tsx', 'w') as f:
        f.write("'use client';\nimport React, { useState } from 'react';\nimport { MetricKey } from '@/lib/types';\nimport { MM, C } from '@/lib/constants';\nimport { getMetricStatus, pillClass } from '@/lib/utils';\n\nexport " + m1.strip())

# Sections
sections = ['DashboardPage', 'AnalysisPage', 'IPOPage', 'ScreenerPage', 'GeoPage', 'PremiumPage', 'ProfilePage', 'PaperTradingPage', 'RHPPage']

for sec in sections:
    reg = rf'function {sec}\([\s\S]*?\n}}\n\n(?:function |\/\/ ─── MAIN APP)'
    match = re.search(reg, code)
    if match:
        content = match.group(0)
        content = re.sub(r'\n\n(?:function |\/\/ ─── MAIN APP)$', '', content)
    else:
        continue

    imports = """'use client';
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

"""
    with open(f'components/sections/{sec}.tsx', 'w') as f:
        f.write(imports + 'export ' + content.strip() + '\n')

import_block = """'use client';
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

"""
app_code = extract_match(r'export default function StockSensePage[\s\S]*')
if app_code:
    with open('app/page.tsx', 'w') as f:
        f.write(import_block + app_code)

print("Extraction complete.")
