import { getPriceHistory, type Range } from '@/lib/data/chart';

const VALID: Range[] = ['1d', '1mo', '6mo', '1y', '5y'];

/** GET /api/chart/INFY?range=6mo → [{ t, close }, …] */
export async function GET(request: Request, ctx: RouteContext<'/api/chart/[symbol]'>) {
  const { symbol } = await ctx.params;
  const requested = new URL(request.url).searchParams.get('range') as Range | null;
  const range = requested && VALID.includes(requested) ? requested : '1y';
  return Response.json(await getPriceHistory(symbol.toUpperCase(), range));
}
