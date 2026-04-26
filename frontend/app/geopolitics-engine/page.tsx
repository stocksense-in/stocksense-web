import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function GeoRoute() {
  return <StockSensePage initialPage={'geo' as Page} />
}
