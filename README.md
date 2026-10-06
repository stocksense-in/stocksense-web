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
backend/  (Python, runs on a schedule)                         frontend/  (Next.js 16, golden dark UI)
NSE symbols, Yahoo Finance, Screener.in, Upstox                  pages read live index prices from
        │                                                        Supabase `live_prices`; most panels
        ▼                                                        use sample data in lib/constants.ts
python -m stocksense <job>  ──►  Supabase `stocks`, `live_prices`
```

* **Python writes, the website reads.** The backend is the only thing with the
  Supabase service key; the website uses the public anon key.
* The frontend is the original golden design (tag `baseline-2026-10-06`). It does
  not yet use the scored `stocks` table — wiring that in is the next step.

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
| Dashboard index prices | Live from Supabase `live_prices` |
| Other frontend panels | Sample data in `lib/constants.ts` |
| Accounts / sign-in | Not built yet |

History of the big restructure, and how to go back to the earlier version:
[`docs/overhaul-2026-10-06.md`](docs/overhaul-2026-10-06.md).
