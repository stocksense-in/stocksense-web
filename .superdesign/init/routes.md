# Routes (Next.js file-based, App Router)

| Path | File | Layout | Renders |
|---|---|---|---|
| `/` | `frontend/app/page.tsx` | root (no shell) | Landing: hero headline + live report card demo, score weights, sector-aware example, toolkit list, footer |
| `/dashboard` | `frontend/app/(app)/dashboard/page.tsx` | (app) | Market today: breadth bar, sector diverging bars, gainers/losers tables, top scored table, geopolitics panel |
| `/stocks` | `frontend/app/(app)/stocks/page.tsx` | (app) | Familiar names + largest by market cap tables, sector chips |
| `/stocks/[symbol]` | `frontend/app/(app)/stocks/[symbol]/page.tsx` | (app) | Stock report: header, 52w range, price chart, score + breakdown, 6-metric report card, peers table, key facts |
| `/screener` | `frontend/app/(app)/screener/page.tsx` | (app) | Filter form + sortable results table + pagination |
| `/ipo` | `frontend/app/(app)/ipo/page.tsx` | (app) | IPO list + selected IPO detail with signal breakdown |
| `/geopolitics` | `frontend/app/(app)/geopolitics/page.tsx` | (app) | Sector exposure list, events, precedents table |
| `/paper-trading` | `frontend/app/(app)/paper-trading/page.tsx` | (app) | Summary tiles, order ticket, holdings, missions |
| `/rhp-analyser` | `frontend/app/(app)/rhp-analyser/page.tsx` | (app) | PDF drop zone, rule list, findings |
| `/profile` | `frontend/app/(app)/profile/page.tsx` | (app) | 4-step investor profile form |
| `/premium` | `frontend/app/(app)/premium/page.tsx` | (app) | Matched picks grid |
| `/login` | `frontend/app/login/page.tsx` | root | Sign-in placeholder |

API: `/api/search`, `/api/chart/[symbol]`, `/api/rhp`. Redirects in next.config.ts: /analysis→/stocks, /geopolitics-engine→/geopolitics.
