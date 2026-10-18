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
| `GET /geopolitics/analogues` | Event types in the historical event study (crude spikes, rupee moves, conflict flare-ups…) with how often each happened |
| `GET /geopolitics/analogues/{code}` | What each sector did vs NIFTY 50 after past events of that type: mean/median excess return, hit rate, 95% CI, n, latest occurrences with news evidence (`horizon=`, `notable=` filters) |
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
| `python -m stocksense lake-prices` | Copies `live_prices` into the local data lake (`clean/prices/date=<IST day>/`) | Daily, after the close |
| `python -m stocksense lake-query "SQL"` | Runs SQL against the data lake and prints the result | Ad hoc |
| `python -m stocksense ingest-bhavcopy` | NSE end-of-day prices for every security, 2010 → today, into the lake (resumable; `--start`, `--end`, `--download-only`, `--build-only`, `--rebuild`) | Daily, after ~18:00 IST |
| `python -m stocksense ingest-corporate-actions` | NSE corporate actions + symbol changes → split/bonus adjustment and the `eod_adjusted` view | Weekly, after `ingest-bhavcopy` |
| `python -m stocksense check-eod` | Data checks on the price history: gaps, thin days, duplicates, impossible prices, unexplained jumps | After each ingest |
| `python -m stocksense ingest-indices` | NSE closing values of every index (sector indices, VIX…), 2012 → today, into the lake | Daily, after ~18:00 IST |
| `python -m stocksense ingest-macro` | Full daily history of crude, gold, copper, gas, USD/INR, dollar index, US 10-year, S&P 500, VIX | Daily |
| `python -m stocksense ingest-gdelt` | GDELT world news events since Apr 2013 → daily aggregates + widely covered events, into the lake (`--workers N` for the build) | Daily |
| `python -m stocksense event-study` | Historical sector reactions to each event type → lake tables + `data/geo_analogues.json` (what the API serves) | Weekly, after the ingests |
| `python -m stocksense engine-daily` | Every lake source for the last 10 days (`--days N`), then the data checks; `--weekly` adds corporate actions and the event study. Logs to `<lake>/runs.jsonl`; non-zero exit on failures | Daily, after ~19:00 IST |
| `python -m stocksense check-lake` | Data checks on the index, macro, GDELT and F&O datasets (gaps, duplicates, impossible values, staleness) | After each ingest |
| `python -m stocksense ingest-fno` | NSE futures & options end-of-day file, 2010 → today: every contract plus a per-underlying summary (OI, put/call ratios, max-OI strikes) | Daily, after ~19:00 IST |
| `python -m stocksense ingest-filings` | NSE corporate announcements and insider trades since 2015 (monthly windows; the latest two months refetched), plus today's FII/DII cash flows | Daily |
| `python -m stocksense filings TCS` | A company's latest announcements and insider trades from the lake (`--since`, `--limit`) | Ad hoc |

Jobs accept `--symbols INFY TCS` or `--limit 20` to work on a few stocks,
`--snapshot` to also write results to the JSON file, and `--no-db` to skip Supabase.

## Data lake (engine machine only)

Long histories (price history, GDELT, filings, features, model weights) are too big
for Supabase's free tier, so the engine machine keeps them in a local lake: Parquet
files plus a DuckDB catalogue. Only finished, publishable results go to Supabase.
The API and its container don't use the lake.

Set `STOCKSENSE_LAKE_DIR` in `backend/.env` to a folder **outside the repo** with a few
hundred GB free (college PC: `E:\stocksense\lake`). The layout:

```
<STOCKSENSE_LAKE_DIR>/
  raw/<source>/<YYYY-MM-DD>/…                       files exactly as downloaded (csv, zip, json, pdf)
  clean/<dataset>/date=<YYYY-MM-DD>/part-0.parquet  typed tables, one folder per day
  features/<name>/…                                 model inputs built from clean/
  models/<name>/<version>/…                         weights, metrics, eval reports
  catalog.duckdb                                    one DuckDB view per clean dataset
```

- **Rerunnable.** Writing a day again replaces that day's partition (atomically), so a
  job that crashed halfway can simply run again.
- **Typed date.** The `date=` folder becomes a `DATE` column in queries.
- **Schemas can grow.** Days written with extra columns read fine next to older days
  (missing values are `NULL`).
- **Names** of sources and datasets are lowercase `snake_case`; they become folder and
  view names.

From code (`stocksense/lake.py`):

```python
from stocksense.lake import Lake

lake = Lake.from_settings()                         # reads STOCKSENSE_LAKE_DIR
lake.write_parquet(df, "prices", day="2026-10-14")  # one day, e.g. a snapshot
lake.write_parquet(bars, "bars", date_col="ts")     # split by a timestamp column (UTC date)
lake.raw_dir("gdelt", "2026-10-14")                 # where to save raw downloads
lake.query("select * from prices where date = ?", [date(2026, 10, 14)])  # → DataFrame
```

From the shell, or the DuckDB CLI pointed at `catalog.duckdb`:

```bash
python -m stocksense lake-query "select date, count(*) as n, avg(change_pct) from prices group by date order by date"
```

The ML/GPU environment (`requirements-ml.txt`, PyTorch with CUDA) is separate from
this one so the API container stays small. See `docs/college-pc-setup.md`.

Reference tables that aren't split by day are stored whole as
`clean/<dataset>/data.parquet` (`lake.write_table(df, name)`). Jobs running side by
side wait for DuckDB's file lock instead of failing.

### Price history (M1.1)

| Dataset | What | Built by |
|---|---|---|
| `raw/nse_bhavcopy/<day>/` | NSE's daily bhavcopy zip, untouched (old `cm…bhav.csv` format until 5 Jul 2024, UDiFF after) | `ingest-bhavcopy` |
| `eod_prices` | Every security on the bhavcopy, **as traded**: open, high, low, close, last, prev_close, volume, turnover (₹), trades | `ingest-bhavcopy` |
| `corporate_actions` | Every NSE corporate action since 2010: kind (split, bonus, dividend, rights…), share multiplier, dividend per share | `ingest-corporate-actions` |
| `symbol_changes`, `symbol_map` | NSE's renames, resolved to today's symbol (chains followed; a reused symbol only maps its own period) | `ingest-corporate-actions` |
| `price_adjustments` | One row per split/bonus/consolidation: the multiplier used and how it was checked | `ingest-corporate-actions` |
| `eod_adjusted` (view) | Prices adjusted for splits and bonuses, under today's symbol | `ingest-corporate-actions` |

**Adjustment.** A price before an ex-date is divided by the number of shares one old
share became (Bonus 1:1 → 2, split ₹10 → ₹1 → 10), compounded over every later action;
volume is multiplied by the same factor. The multiplier is read from NSE's wording of
the action and **checked against the exchange itself**: on the ex-date NSE quotes a
previous close already adjusted for the action, so (last close before) ÷ (ex-date
prev_close) is the exchange's own ratio. `price_adjustments.status` says what was used:
`confirmed` (the two agree within 3%), `exchange` (they disagree or nothing parsed —
the exchange's ratio wins), `parsed` (no prices around the ex-date) or `skipped`.
Dividends, rights issues and demergers are recorded but **not** adjusted for yet.

```python
from stocksense import eod
eod.adjusted_history(lake, ["TCS", "INFY"], start=date(2015, 1, 1))  # EQ series, adjusted OHLCV
```

### Index and macro series (M1.6, part)

| Dataset | What | Source |
|---|---|---|
| `index_prices` | Every NSE index each day: open, high, low, close, change %, volume, turnover (₹ cr), P/E, P/B, dividend yield. ~47 indices in 2015, ~165 now | NSE's daily `ind_close_all_<DDMMYYYY>.csv` |
| `macro_prices` | One table, all series: `BRENT`, `WTI`, `GOLD`, `COPPER`, `NATGAS`, `USDINR`, `DXY`, `US10Y`, `SP500`, `US_VIX`, `NIFTY50_YF` (cross-check) | Yahoo chart endpoint (internal use only, PLAN §4) |

- **Stable index codes.** NSE renamed its "CNX …" indices to "Nifty …" in late 2015;
  both map to one code (`CNX Bank`, `Nifty Bank` → `NIFTY_BANK`). See `sources/nse_indices.py`.
- **Why not Yahoo for sector indices:** Yahoo only has full history for NIFTY 50, SENSEX,
  Bank Nifty, India VIX, IT and Pharma; NSE's own files cover every index.
- **Futures are front-month continuous series**, so a contract roll can add a small jump.
- Still to do for M1.6: RBI policy rates, CPI, IIP and forex reserves, with release dates
  (no look-ahead).

```bash
python -m stocksense lake-query "select index, count(*) as days, min(date) as since from index_prices group by index order by since limit 20"
```

### Futures & options (M1.5)

| Dataset | What |
|---|---|
| `fno_prices` | Every F&O contract each day: instrument (`FUTIDX`, `FUTSTK`, `OPTIDX`, `OPTSTK`), symbol, expiry, strike, option type, OHLC, settlement, contracts, turnover, open interest and its change; underlying price and lot size from 8 Jul 2024 |
| `fno_summary` | One row per underlying per day: near-month future (expiry, close), total futures OI, call/put OI and volume, put/call ratio by OI and by volume (all expiries and the nearest), the nearest expiry's max-call-OI and max-put-OI strikes |

- **Units are the same across NSE's July 2024 format switch** (checked on the NIFTY
  July 2024 future): `contracts` = number of contracts, `open_interest` = shares/units,
  `turnover` = ₹ (the old file's ₹ lakh converted). Turnover is the notional value NSE
  reports, which for options is far larger than the premium paid.
- An option chain for any day is a query on `fno_prices`:

```bash
python -m stocksense lake-query "select strike, option_type, close, open_interest from fno_prices where date = '2026-10-16' and symbol = 'NIFTY' and expiry = (select min(expiry) from fno_prices where date = '2026-10-16' and symbol = 'NIFTY' and option_type = 'CE') order by strike, option_type"
```

### Announcements, insider trades, FII/DII flows (M1.4)

| Dataset | What | Partitioned by |
|---|---|---|
| `announcements` | Every NSE filing since 2015 (1.37 M by Oct 2026): category ("Outcome of Board Meeting", "Bagging/Receiving of orders/contracts", "Press Release", …), one-line summary, PDF link, XBRL flag | broadcast date (IST) |
| `insider_trades` | SEBI PIT disclosures: person, role, buy/sell, mode (market, ESOP, …), quantity, value, holdings before/after | disclosure date — when the market could know |
| `fii_dii` | Provisional FII and DII cash-market buy / sell / net, ₹ crore | trading date |

- **Known gaps.** Insider trades run from Nov 2015 (SEBI's PIT regulations) to 2 May 2026;
  NSE's endpoint returns nothing after that (a change on NSE's side; `check-lake` reports
  the last date). Yearly insider counts fall from ~58k (2018) to ~14k (2025) as disclosure
  rules changed, so don't compare volumes across years naively. FII/DII history starts the day this
  job first ran, because NSE serves only the latest day. **Bulk and block deals** aren't
  ingested: NSE's historical deals API answers 503 outside a browser session (bot
  protection, PLAN §1.5).
- Searchable by symbol and date: `python -m stocksense filings ACMESOLAR --since 2026-09-01`,
  or SQL on the datasets above.

### The daily run (prep for M0.4)

`engine-daily` is the one command a scheduler should call each evening. Steps run in
order and independently (a failing source doesn't stop the others); every step is
resumable, so `--days 30` catches up after the machine was off. Each run appends one
line to `<lake>/runs.jsonl`:

```json
{"started_at": "...", "seconds": 43.1, "weekly": false, "ok": true,
 "steps": [{"step": "bhavcopy", "ok": true, "seconds": 4.7}, ...], "problems": {"index_prices": [], ...}}
```

The exit code is non-zero when a step failed or a check found a problem, so a scheduler
can alert. No scheduler is installed yet (M0.4 needs approval).

### News events (GDELT)

GDELT codes every news-reported event worldwide: who did what to whom (CAMEO codes),
where, how intense (Goldstein scale), how widely covered and in what tone. One file a
day since 1 Apr 2013 (~37 GB in `raw/gdelt/`).

| Dataset | What |
|---|---|
| `gdelt_daily` | Per day × country × CAMEO root × quad class × India involved: events, mentions, articles, mention-weighted Goldstein and tone |
| `gdelt_events` | Widely covered (≥10 articles) root events that are hostile (threats, protest, force posture, sanctions, coercion, violence) or involve India — with source URLs, for evidence links |

Everything is dated by the **file day** (when it was known), not the event's own date:
a day's file also reports older events. Note GDELT's daily file for day *t* is
published around 15:30 IST on *t*+1.

### Event study (M3.1)

`stocksense/event_study.py` answers "historically, after events like this, what did each
sector do versus NIFTY 50?" — no machine learning, every number with its sample size.

- **Event types** (`EVENT_TYPES`): crude spike / crash (Brent ±5% in a day), sharp rupee
  fall / rally (USD/INR ±1%), global risk-off (S&P 500 −3%), US volatility jump (VIX +30%),
  US yield jump (+0.15 pt), gold spike (+3%), and four news signals from GDELT — global
  conflict, India–Pakistan/China tension, Middle East conflict, sanctions — each a day when
  that topic's share of world coverage is 3σ above its previous 90 days. (The India signal
  counts hostile acts *between* India and Pakistan or China; checked against known crises
  in `docs/event-study-2026-10.md`.)
- **Sectors**: NSE sector indices; equal-weight baskets of today's constituents where NSE
  has no long-running index (Oil & Gas, Aviation, Defence, Paints — survivorship bias
  noted); gold in rupees.
- **Measurement**: sector return minus NIFTY 50's over the next 1, 3 and 10 trading days,
  from the last Indian close on or before the signal. Repeats within 10 trading days count
  once. 95% bootstrap CI of the mean; `notable` when the CI excludes the sector's average
  excess return over all days (its baseline). Cells with fewer than 5 events are left out.
  About 5% of cells would be notable by chance; `notable_share` in the output says how many
  are (12.5% at 1 day in the first run, mostly from crude, rupee and US-market events).
- **Publishing**: `event-study` writes `clean/geo_analogues`, `clean/geo_event_dates` and
  `backend/data/geo_analogues.json`. The API serves the JSON, so the public API never needs
  the engine machine; rerun the job and commit the JSON to update it.

Read results as historical tendencies, not forecasts or advice (PLAN §1.6).

## Code map

```
stocksense/
  __main__.py        CLI — every job and its options
  config.py          reads .env (the only file that touches environment variables)
  scoring.py         the StockSense score — single source of truth, documented curves + weights
  sectors.py         Yahoo sector/industry → StockSense sector code
  symbols.py         NSE equity list (EQUITY_L.csv), cached 24h in _nse_symbols_cache.json
  db.py              write side: Store saves rows to Supabase and/or a JSON snapshot
  lake.py            local data lake: Parquet layout, partitioned writes, DuckDB queries
  downloads.py       polite, resumable archive downloads into the lake's raw/ folder
  eod.py             price history: split/bonus adjustment, symbol continuity, data checks
  event_study.py     event detection + sector excess returns after each event type, with CIs
  lake_checks.py     data checks for the index, macro, GDELT, F&O and filings datasets
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
    bhavcopy.py      NSE end-of-day bhavcopy (both archive formats)
    nse_corporate.py NSE corporate actions and symbol changes; split/bonus ratio parsing
    nse_indices.py   NSE daily closing values of every index; stable codes across renames
    yahoo_history.py full daily history of global macro series (crude, gold, rupee, US markets)
    gdelt.py         GDELT 1.0 daily event files → daily aggregates and salient events
    fno_bhavcopy.py  NSE F&O bhavcopy (both formats) and the per-underlying summary
    nse_filings.py   NSE announcements, insider trades (PIT) and FII/DII flows
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
