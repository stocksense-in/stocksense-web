import StockSensePage from '@/app/page'
import type { Page } from '@/lib/types'

export default function AnalysisRoute() {
  return <StockSensePage initialPage={'analysis' as Page} />
}