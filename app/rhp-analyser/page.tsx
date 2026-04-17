import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function RHPRoute() {
  return <StockSensePage initialPage={'rhp' as Page} />
}
