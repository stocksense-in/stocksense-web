import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function PremiumRoute() {
  return <StockSensePage initialPage={'premium' as Page} />
}
