import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function PaperTradingRoute() {
  return <StockSensePage initialPage={'paper' as Page} />
}
