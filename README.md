# StockSense

Stock research for Indian retail investors. Every NSE-listed company is scored on
six fundamentals, judged against what is healthy **for its own sector**, and
explained in plain language. Around that sit a screener, IPO scoring, a
geopolitical risk map, a prospectus (DRHP/RHP) scanner and a paper-trading
simulator.

> Educational tool — not investment advice. StockSense is not a SEBI-registered investment adviser.

---

## How it fits together

```
backend/  (Python)                                                frontend/  (Next.js, golden dark UI)
                                                                 
pipeline jobs ── NSE, Yahoo, Screener.in, Upstox ──► Supabase     reads live index prices from
                                                       │          Supabase; other panels still use
REST API (FastAPI) ◄── Supabase, news RSS, NSE IPOs ◄──┘          sample data in lib/constants.ts
   └── /market, /stocks, /news, /geopolitics, /ipos, /prospectus ──► ready for the frontend to call
```

* **Pipeline writes, everything else reads.** Only the pipeline holds the Supabase
  service key; the API and the website use the read-only anon key.
* The frontend is the original golden design (tag `baseline-2026-10-06`). The API
  serves everything its panels need with real data; wiring it in is the next step
  (see `backend/README.md` → "The API").

## Run it

```bash
# Website — http://localhost:3000
cd frontend
# .env.local: NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY (anon key only)
npm install
npm run dev
```

```bash
# Data pipeline
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # SUPABASE_URL + SUPABASE_SERVICE_KEY
python -m stocksense fundamentals --limit 20   # try it on 20 stocks
```

```bash
# REST API — http://localhost:8000/docs
cd backend && source .venv/bin/activate
python -m stocksense api --reload
```

First time with a new Supabase project: run [`backend/schema.sql`](backend/schema.sql) in the SQL editor.
Full pipeline docs: [`backend/README.md`](backend/README.md).

From the repo root, `npm run dev` / `npm run build` also work (they `cd frontend` first),
and `npm test` runs the backend tests.

## Where things are

```
frontend/
  app/page.tsx               landing page + the in-app shell (sidebar, top bar); every route
                             (app/dashboard, app/analysis, …) renders it with an initialPage
  components/sections/       one component per page: Dashboard, Analysis, Screener, IPO,
                             Geo, PaperTrading, RHP, Premium, Profile
  components/cards/          MetricCard, MetricOverlay (metric deep-dive), CandleChart
  components/landing/        Constellation background, custom cursor
  lib/constants.ts           sample stocks, IPOs, screener rows, geopolitics data
  lib/metricContent.ts, metricIntel.ts   long-form metric explanations
  app/globals.css            the golden theme (gold #C9A84C, green #00E676, cream text)

backend/
  stocksense/                the data pipeline package — see backend/README.md
  schema.sql                 tables, columns, access rules
  tests/                     pytest
```

## Status

| Area | State |
|---|---|
| Data pipeline (prices, fundamentals, scores for ~2,400 stocks) | Live in Supabase |
| REST API: overview, screener, stock detail, history, news/geopolitics, IPOs, prospectus scanner | Built and tested; not yet deployed |
| Dashboard index prices | Live from Supabase `live_prices` |
| Other frontend panels | Sample data in `lib/constants.ts` until wired to the API |
| Accounts / sign-in | Not built yet |

History of the big restructure, and how to go back to the earlier version:
[`docs/overhaul-2026-10-06.md`](docs/overhaul-2026-10-06.md).
