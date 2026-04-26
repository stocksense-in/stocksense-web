import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function IPORoute() {
  return <StockSensePage initialPage={'ipo' as Page} />
}