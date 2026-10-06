import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function ScreenerRoute() {
  return <StockSensePage initialPage={'screener' as Page} />
}
