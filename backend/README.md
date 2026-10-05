# StockSense backend — data pipeline

Python jobs that fetch NSE market data, score every stock, and store the results
in Supabase. The website only **reads** that data; this folder is the only thing
that **writes** it.

```
Yahoo Finance ─┐                         ┌─► Supabase `stocks`       ─┐
Screener.in  ──┼─► python -m stocksense ─┤                            ├─► website (frontend/)
Upstox       ──┘                         └─► Supabase `live_prices`  ─┘
                                          └─► frontend/data/snapshot.json (optional, offline fallback)
```

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in SUPABASE_URL and SUPABASE_SERVICE_KEY
```

Then run [`schema.sql`](schema.sql) once in **Supabase → SQL Editor**. It creates the
tables (or adds missing columns to existing ones) and makes them read-only for the
public anon key.

## Jobs

| Command | What it does | How often |
|---|---|---|
| `python -m stocksense fundamentals` | Price, P/E, ROE, D/E, margin, promoter holding → score | Daily after close (~20 min for all stocks) |
| `python -m stocksense ownership` | Promoter holding + 3-yr revenue CAGR (Yahoo → Screener.in → fallback table) → re-score | Daily / weekly (slow) |
| `python -m stocksense prices` | Latest price and day change for all stocks + NIFTY 50, SENSEX, BANK NIFTY, India VIX | Every few minutes in market hours |
| `python -m stocksense prices --source upstox` | Same, real-time from Upstox | Needs today's Upstox login |
| `python -m stocksense realtime` | Streams Upstox ticks into `live_prices` (1 write/sec) | Runs until stopped |
| `python -m stocksense upstox-login` | Opens Upstox sign-in and saves the day's token | Every morning |
| `python -m stocksense scheduler` | Runs all of the above on an IST market-hours timetable | Leave running |

Every job accepts `--symbols INFY TCS` or `--limit 20` to work on a few stocks,
and `--snapshot` to also write results into `frontend/data/snapshot.json`.
Add `--no-db` to skip Supabase entirely (useful offline).

```bash
python -m stocksense fundamentals --symbols INFY TCS HDFCBANK
python -m stocksense prices --limit 50 --no-db --snapshot /tmp/prices.json
```

## Code map

```
stocksense/
  __main__.py        CLI — the list of jobs and their options
  config.py          reads .env (the only file that touches environment variables)
  scoring.py         the StockSense score — single source of truth, documented curves + weights
  sectors.py         Yahoo sector/industry → StockSense sector code
  symbols.py         NSE equity list (EQUITY_L.csv), cached 24h in _nse_symbols_cache.json
  db.py              Store: writes rows to Supabase and/or a JSON snapshot
  sources/
    yahoo.py         fundamentals, revenue CAGR, batch prices (via yfinance)
    screener.py      Screener.in scraping — fallback for promoter holding / sales growth
    fallbacks.py     hardcoded large-cap ownership values (last resort, goes stale)
    upstox.py        OAuth token storage, REST quotes, WebSocket URL
    upstox_feed.py   decoder for Upstox WebSocket (protobuf v3) messages
  jobs/              one module per CLI job
tests/               pytest — run with `pytest`
schema.sql           database tables, columns, and access rules
```

## The score

Six metrics, each mapped to 0–100, weighted: P/E 20%, ROE 20%, net margin 20%,
D/E 15%, revenue CAGR 15%, promoter holding 10%. Banks and NBFCs are allowed more
leverage; new-age platforms aren't judged on P/E. Missing metrics are skipped and
the other weights re-normalised; fewer than 4 known metrics → no score.
Details and exact curves: [`stocksense/scoring.py`](stocksense/scoring.py).
The frontend mirrors these curves in `frontend/lib/scoring.ts` — change both together.

## Data units

`roe`, `net_margin`, `promoter_holding`, `revenue_cagr_3yr`, `*_change_pct` are
percentages (31.2 = 31.2%). `debt_equity` is a ratio (0.4 = 0.4×) — Yahoo reports it
as a percentage and `sources/yahoo.py` converts it. `market_cap` is in ₹ crore.
