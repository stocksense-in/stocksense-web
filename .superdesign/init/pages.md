# Pages — dependency trees

## /stocks/[symbol]
Entry: frontend/app/(app)/stocks/[symbol]/page.tsx
- frontend/components/charts/PriceChart.tsx
- frontend/components/stock/RangeBar.tsx
- frontend/components/stock/ReportCard.tsx
  - frontend/components/ui/MetricGauge.tsx
  - frontend/components/ui/StatusBadge.tsx
  - frontend/components/stock/MetricSheet.tsx
    - frontend/lib/metricContent.ts, frontend/lib/metricIntel.ts
- frontend/components/stock/ScoreBreakdown.tsx
- frontend/components/stock/PeerTable.tsx
- frontend/components/ui/Change.tsx, frontend/components/ui/ScoreMeter.tsx
- frontend/lib/data/chart.ts, frontend/lib/data/queries.ts, frontend/lib/format.ts, frontend/lib/sectors.ts, frontend/lib/metrics.ts, frontend/lib/scoring.ts

## /dashboard
Entry: frontend/app/(app)/dashboard/page.tsx
- frontend/components/charts/SectorBars.tsx
- frontend/components/ui/StockTable.tsx (Change, ScoreMeter)
- frontend/lib/data/queries.ts, frontend/lib/content/geopolitics.ts

## / (landing)
Entry: frontend/app/page.tsx
- frontend/components/landing/HeroReportCard.tsx (Change, StatusBadge, metrics, scoring, sectors)
- frontend/components/shell/Logo.tsx
- frontend/lib/data/queries.ts, frontend/lib/metrics.ts, frontend/lib/scoring.ts

## /screener
Entry: frontend/app/(app)/screener/page.tsx
- frontend/components/ui/AutoSubmitForm.tsx, Change.tsx, ScoreMeter.tsx
- frontend/lib/data/queries.ts, frontend/lib/format.ts, frontend/lib/sectors.ts

## /paper-trading
Entry: frontend/app/(app)/paper-trading/page.tsx
- frontend/components/paper/PaperTrading.tsx (Change, lib/paperTrading.ts, lib/format.ts)

## /ipo
Entry: frontend/app/(app)/ipo/page.tsx
- frontend/components/ui/StatusBadge.tsx, frontend/lib/content/ipos.ts

All (app) pages are wrapped by frontend/app/(app)/layout.tsx (Sidebar, MobileNav, SearchBox, IndexBar).
