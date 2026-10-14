# Extractable components

## Sidebar
- Source: `frontend/components/shell/Sidebar.tsx`
- Category: layout
- Description: Left nav with logo, grouped links (Markets / Research / You), disclaimer
- Extractable props: activeItem (string, default: "dashboard")
- Hardcoded: nav labels and lucide icons, Pro tag on Matched picks

## AppHeader
- Source: `frontend/app/(app)/layout.tsx` + `frontend/components/shell/SearchBox.tsx` + `IndexBar.tsx`
- Category: layout
- Description: Sticky header with stock search and index ticker strip (NIFTY 50, SENSEX, BANK NIFTY, India VIX)
- Extractable props: none
- Hardcoded: indices, placeholder text

## LandingNav
- Source: `frontend/app/page.tsx` (header)
- Category: layout
- Description: Logo, Stocks/Screener/IPOs/Paper trading links, Sign in, Open StockSense CTA
- Extractable props: none

## Panel
- Source: `.panel` class in `frontend/app/globals.css`
- Category: basic
- Description: Bordered surface card

## StockTable
- Source: `frontend/components/ui/StockTable.tsx`
- Category: basic
- Description: Symbol/name, price, day change, optional score meter

## MetricGauge
- Source: `frontend/components/ui/MetricGauge.tsx`
- Category: basic
- Description: Ruler with hatched ideal range and status-colored marker

## StatusBadge
- Source: `frontend/components/ui/StatusBadge.tsx`
- Category: basic
- Description: Healthy / Watch / Concern pill
