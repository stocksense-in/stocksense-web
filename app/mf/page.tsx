import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function MFRoute() {
  return <StockSensePage initialPage={'mf' as Page} />
}
