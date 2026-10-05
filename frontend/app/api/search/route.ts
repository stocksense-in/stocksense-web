import { searchStocks } from '@/lib/data/queries';

/** GET /api/search?q=infy → up to 8 matching stocks for the search box. */
export async function GET(request: Request) {
  const q = new URL(request.url).searchParams.get('q') ?? '';
  const results = await searchStocks(q.slice(0, 40));
  return Response.json(
    results.map((s) => ({ symbol: s.symbol, name: s.name, price: s.price, changePct: s.changePct })),
  );
}
