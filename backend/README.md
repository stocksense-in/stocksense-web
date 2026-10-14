# StockSense backend

Two parts, one Python package (`stocksense/`):

1. **Data pipeline** — jobs that fetch NSE market data, score every stock and
   store the results in Supabase. The only code that **writes** data.
2. **REST API** — a read-only FastAPI service the website (or anything else)
   calls: market overview, screener, stock detail, price history, news-driven
   geopolitics, IPOs and the prospectus scanner.

```
Yahoo Finance ─┐                                   ┌─► Supabase `stocks`, `live_prices`
Screener.in  ──┼─► python -m stocksense <job> ──────┤
Upstox       ──┘                                   └─► backend/data/snapshot.json (offline copy)

Supabase (read-only key) ─┐
News RSS feeds ───────────┼─► python -m stocksense api ─► JSON over HTTP ─► website / apps
NSE IPO data ─────────────┤
Yahoo charts ─────────────┘
```

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in the values below
```

| Variable | Used by | Notes |
|---|---|---|
| `SUPABASE_URL` | both | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | pipeline | Writes data. Server-side only, never `NEXT_PUBLIC_` |
| `SUPABASE_ANON_KEY` | API | Read-only. The API prefers it, so a leaked API host can't write |
| `API_CORS_ORIGINS` | API | Comma-separated origins allowed to call the API from a browser. Default `http://localhost:3000` |
| `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_REDIRECT_URI` | pipeline | Only for real-time Upstox prices |

Then run [`schema.sql`](schema.sql) once in **Supabase → SQL Editor**: it creates
the tables (or adds missing columns to existing ones) and makes them read-only
for the anon key.

## The API

```bash
python -m stocksense api --reload        # http://localhost:8000/docs — interactive docs for every endpoint
```

| Endpoint | Returns |
|---|---|
| `GET /health` | Data source (supabase / snapshot), stock counts, last price update |
| `GET /market/indices` | NIFTY 50, SENSEX, BANK NIFTY, India VIX |
| `GET /market/overview` | Indices, breadth, cap-weighted sector moves, gainers/losers, top-scored stocks |
| `GET /sectors` | Sector codes and labels with stock counts (for filter menus) |
| `GET /stocks` | Screener: `sector`, `cap` (large/mid/small), `min_score`, `max_pe`, `min_roe`, `max_de`, `sort`, `order`, `page`, `page_size` |
| `GET /stocks/search?q=` | Symbol / company-name search |
| `GET /stocks/{symbol}` | One stock, its score broken down metric by metric, and sector peers |
| `GET /stocks/{symbol}/history?range=` | Closing prices: `1d` (5-min), `5d`, `1mo`, `6mo`, `1y`, `5y`. Works for indices too (`NIFTY50`) |
| `GET /news` | Market-moving headlines tagged with topics and affected sectors (`topic=`, `sector=` filters) |
| `GET /geopolitics` | Sector exposure computed from the last few days of news, plus the headlines behind it |
| `GET /ipos` | Open and upcoming NSE IPOs with live category-wise subscription and a demand reading |
| `GET /ipos/listings?days=` | Recent IPOs: return from issue price to today |
| `GET /prospectus/rules` | What the prospectus scanner checks |
| `POST /prospectus/scan` | Upload a DRHP/RHP PDF (form field `file`); get red flags with page-numbered quotes |

Example from the website:

```ts
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/stocks/TCS`);
const { stock, score, peers } = await res.json();
// score.breakdown → [{ metric: 'pe', score: 81, weight: 0.2, points: 16.2 }, …]
```

Behaviour worth knowing:

- **Caching.** Fundamentals are cached 5 min, prices 30 s, news 15 min, IPOs 5 min,
  charts 1 h (2 min for intraday).
- **Outages.** If Supabase is down, the API serves `data/snapshot.json` (~70 large caps)
  and `/health` reports `data_source: snapshot`. If NSE blocks the IPO requests, `/ipos`
  answers 503 with a readable message.
- **Stale stocks.** A stock whose data is over 7 days older than the latest pipeline run
  is usually delisted or renamed. It's left out of rankings and the screener, and
  flagged `stale: true` on its own page. `python -m stocksense cleanup` lists them.
- **Not advice.** IPO "demand" describes subscription so far; it is not a recommendation.

### Deploying the API

`backend/Dockerfile` builds a container that serves the API on `$PORT`
(Render, Railway, Fly.io and Cloud Run all set it):

```bash
docker build -t stocksense-api backend
docker run -p 8000:8000 -e SUPABASE_URL=… -e SUPABASE_ANON_KEY=… -e API_CORS_ORIGINS=https://your-site stocksense-api
```

Without Docker: `pip install -r requirements.txt` then
`uvicorn stocksense.api:app --host 0.0.0.0 --port $PORT`.

## Pipeline jobs

| Command | What it does | How often |
|---|---|---|
| `python -m stocksense fundamentals` | Price, P/E, ROE, D/E, margin, promoter holding → score | Daily after close (~20 min for all stocks) |
| `python -m stocksense ownership` | Promoter holding + 3-yr revenue CAGR (Yahoo → Screener.in → fallback table) → re-score | Weekly (slow) |
| `python -m stocksense prices` | Latest price and day change for all stocks + the four indices | Every few minutes in market hours |
| `python -m stocksense prices --source upstox` | Same, real-time from Upstox | Needs today's Upstox login |
| `python -m stocksense realtime` | Streams Upstox ticks into `live_prices` (1 write/sec) | Runs until stopped |
| `python -m stocksense upstox-login` | Opens Upstox sign-in and saves the day's token | Every morning |
| `python -m stocksense scheduler` | Runs the jobs above on an IST market-hours timetable | Leave running |
| `python -m stocksense rescore` | Recomputes every stored score after a change to `scoring.py` (seconds, no Yahoo) | After scoring changes |
| `python -m stocksense cleanup` | Lists stocks no longer on NSE's list; `--apply` deletes them | Occasionally |
| `python -m stocksense snapshot` | Copies ~70 large caps into `data/snapshot.json`, the API's offline data | After a fundamentals run |
| `python -m stocksense api` | Serves the REST API | Always on, in production |

Jobs accept `--symbols INFY TCS` or `--limit 20` to work on a few stocks,
`--snapshot` to also write results to the JSON file, and `--no-db` to skip Supabase.

## Code map

```
stocksense/
  __main__.py        CLI — every job and its options
  config.py          reads .env (the only file that touches environment variables)
  scoring.py         the StockSense score — single source of truth, documented curves + weights
  sectors.py         Yahoo sector/industry → StockSense sector code
  symbols.py         NSE equity list (EQUITY_L.csv), cached 24h in _nse_symbols_cache.json
  db.py              write side: Store saves rows to Supabase and/or a JSON snapshot
  market.py          read side: typed Stock/Quote objects, caching, snapshot fallback, staleness
  analytics.py       screener, movers, breadth, sector moves, search, peers, score breakdown
  geo.py             news → topics → affected sectors → sector exposure
  ipo.py             IPO parsing, demand reading, recent-listing returns
  rhp.py             prospectus (DRHP/RHP) red-flag scanner
  sources/
    yahoo.py         fundamentals, revenue CAGR, batch prices (yfinance, rate-limited)
    chart.py         price history from Yahoo's chart endpoint
    news.py          RSS headlines (Economic Times, Livemint, Business Standard, Google News)
    nse_ipo.py       NSE IPO endpoints
    screener.py      Screener.in scraping — fallback for promoter holding / sales growth
    fallbacks.py     hardcoded large-cap ownership values (last resort, goes stale)
    upstox.py        OAuth token storage, REST quotes, WebSocket URL
    upstox_feed.py   decoder for Upstox WebSocket (protobuf v3) messages
  jobs/              one module per pipeline job
  api/               FastAPI app (app.py) and response schemas (schemas.py)
tests/               pytest — `pytest` runs everything offline in under a second
schema.sql           database tables, columns, and access rules
Dockerfile           API container
```

## The score

Six metrics, each mapped to 0–100, weighted: P/E 20%, ROE 20%, net margin 20%,
D/E 15%, revenue CAGR 15%, promoter holding 10%. Banks and NBFCs are allowed more
leverage; new-age platforms aren't judged on P/E. Missing metrics are skipped and
the other weights re-normalised; a stock needs at least 4 metrics, including ROE or
D/E, to be scored. A P/E below 4 (usually one-off profits) scores neutral.
Details and exact curves: [`stocksense/scoring.py`](stocksense/scoring.py).
`GET /stocks/{symbol}` returns the per-metric breakdown.

## Data units

`roe`, `net_margin`, `promoter_holding`, `revenue_cagr_3yr`, `*_change_pct` are
percentages (31.2 = 31.2%). `debt_equity` is a ratio (0.4 = 0.4×) — Yahoo reports it
as a percentage and `sources/yahoo.py` converts it. `market_cap` is in ₹ crore.
