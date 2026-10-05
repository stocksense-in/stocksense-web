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
               backend/  (Python, runs on a schedule)                    frontend/  (Next.js 16)
┌──────────────────────────────────────────────────┐        ┌───────────────────────────────────────┐
│ NSE symbol list ─┐                               │        │ lib/data/source.ts                    │
│ Yahoo Finance  ──┼─► python -m stocksense <job> ─┼──────► │   reads Supabase (anon key, read-only)│
│ Screener.in    ──┤      scores every stock       │ Supa-  │   or data/snapshot.json when offline  │
│ Upstox (live)  ──┘                               │ base   │ lib/data/queries.ts → pages           │
└──────────────────────────────────────────────────┘        └───────────────────────────────────────┘
```

* **Python writes, Next.js reads.** The backend is the only thing with the
  Supabase service key. The website reads with the public anon key, which row-level
  security limits to `select`.
* **Works without a database.** If Supabase isn't configured (or is down), the
  site serves `frontend/data/snapshot.json`, real numbers for ~70 large caps.

## Run it

```bash
# Website — http://localhost:3000
cd frontend
cp .env.example .env.local        # optional: add SUPABASE_URL + SUPABASE_ANON_KEY
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

From the repo root, `npm run dev` / `npm run build` also work (they `cd frontend` first).

## Where things are

```
frontend/
  app/
    page.tsx                 landing page
    (app)/                   everything with the sidebar — the folder name doesn't appear in URLs
      layout.tsx             sidebar, search, index bar
      dashboard/             market breadth, sector moves, movers, top scores
      stocks/                stock list, and stocks/[symbol] — the report-card page
      screener/              filters over every stock, all state in the URL
      ipo/  geopolitics/     IPO scores, sector risk map (curated sample data for now)
      paper-trading/         simulator — logic in lib/paperTrading.ts
      rhp-analyser/          prospectus scanner — rules in lib/rhp.ts
      profile/  premium/     investor profile (cookie) → Matched picks
    api/                     search, chart history, prospectus upload
  components/
    shell/                   sidebar + nav list (nav.ts), search box, index bar, logo
    stock/                   report card, metric side panel, score breakdown
    ui/                      small shared pieces: Change, StatusBadge, MetricGauge, ScoreMeter, StockTable
  lib/
    data/                    the only code that fetches data (server-side)
    metrics.ts               sector ideal ranges + plain-language readings for each metric
    scoring.ts               score curves — mirror of backend/stocksense/scoring.py
    metricContent.ts, metricIntel.ts   long-form explanations shown in the metric panel
    content/                 hand-maintained IPO and geopolitics data
  app/globals.css            design tokens (colours, fonts, radii) + a few shared classes

backend/
  stocksense/                the pipeline package — see backend/README.md
  schema.sql                 tables, columns, access rules
  tests/                     pytest
```

## Design system

Light, number-first, and quiet. The tokens live in `frontend/app/globals.css`
and are usable as Tailwind classes (`bg-paper`, `text-ink-2`, `border-rule`…).

| Token | Use |
|---|---|
| `paper` `#F3F4F1`, `surface` `#FFFFFF` | page and panel backgrounds |
| `ink` / `ink-2` / `ink-3` | primary, secondary, muted text |
| `brand` `#2B3FD6` | actions, links, focus — nothing else |
| `up` / `down` | real price moves and healthy / concern status only |
| `watch` | the in-between status, always shown with a word |
| `.ideal-band` | hatched texture marking a sector's healthy range on every gauge |

Fonts: **Bricolage Grotesque** for headings, **IBM Plex Sans** for everything
else, with tabular figures (`.num`) wherever numbers line up.

## Status

| Area | State |
|---|---|
| Stock scores, report card, screener, dashboard | Live data from the pipeline |
| Price charts | Live from Yahoo Finance |
| Prospectus scanner | Works on real DRHP/RHP PDFs (pattern rules, not AI) |
| Paper trading, profile, matched picks | Working; saved on the device |
| IPO list, geopolitics events | Curated sample data — feeds still to build |
| Accounts / sign-in | Not built yet (planned: Supabase Auth) |

History of the big restructure, and how to go back to the earlier version:
[`docs/overhaul-2026-10-06.md`](docs/overhaul-2026-10-06.md).
