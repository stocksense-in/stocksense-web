import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function DashboardRoute() {
  return <StockSensePage initialPage={'dashboard' as Page} />
}
