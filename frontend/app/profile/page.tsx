import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function ProfileRoute() {
  return <StockSensePage initialPage={'profile' as Page} />
}
