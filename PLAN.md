# StockSense — Plan

> An internal research terminal for Indian markets ("our own Bloomberg"), with a
> public StockSense site built on the parts we're allowed to publish.
>
> This file is the roadmap for everyone working on the repo, people and AI agents.
> Work one milestone at a time, on a branch, and open a PR. Tick boxes in the PR
> that completes them.

---

## 1. Rules for every session

1. **Keep the golden UI.** The frontend's look (dark, gold `#C9A84C`, green, cream text,
   Playfair Display / DM Sans / JetBrains Mono, constellation landing) is the design.
   Add features inside it; don't restyle. Two redesigns were tried and rejected.
2. **Branch → PR → review.** Never commit to `main` directly. One milestone per branch
   (`m2-fundamentals-xbrl`, …). PRs list which acceptance criteria they meet.
3. **No AI attribution** in commits, PRs, READMEs, changelogs or author fields.
4. **Secrets stay out of git.** `.env` files are copied by hand. If a key is ever
   printed or committed, say so and rotate it.
5. **Data must be legal for its use.** Check §4 before adding a source. No bypassing
   logins, paywalls, CAPTCHAs or bot protection; no extracting keys from other apps;
   no republishing paid data.
6. **Not investment advice.** Internal research is fine. Anything public describes
   ("historically, X tended to…"), never recommends ("buy X"). Public buy/sell calls
   would need SEBI research-analyst registration.
7. **Tests with every feature.** Backend: `cd backend && pytest` (offline, fast).
   Network calls are injected so tests use fixtures.
8. **Ask before destructive actions** on shared data (deleting rows, dropping tables,
   rewriting history).

---

## 2. Where things stand (18 Oct 2026)

| Area | State |
|---|---|
| Data pipeline (`backend/stocksense`) | Prices, fundamentals, ownership, scores for ~2,600 NSE stocks → Supabase. Upstox realtime feed. Engine lake (college PC): NSE prices 2010→ (adjusted), every NSE index 2012→, global macro, GDELT 2013→ (~45 GB). |
| REST API (`backend/stocksense/api`) | Overview, screener, stock detail + score breakdown + peers, history, news/geopolitics (rules), IPOs, prospectus scanner. Not deployed. |
| Frontend (`frontend/`) | Golden UI. Dashboard index prices are live; other panels use sample data in `lib/constants.ts`. |
| Geopolitics engine | Live: keyword rules over RSS (`geo.py`). Historical: event study (M3.1) — what each sector did after crude, rupee, US-market and conflict events since 2012 (`/geopolitics/analogues`). Market events show real effects; news-coverage events are near chance level. |
| Infra | Supabase free tier. CI on every PR (`.github/workflows/ci.yml`). Scheduled pipeline ready (`pipeline.yml`), waiting for repo secrets. No deployment yet. |
| College PC (engine) | Set up 14 Oct (M0.1–M0.3): repo at `C:\Users\PRO-LAB-2\stocksense-web`, Python 3.12 envs `backend/.venv` (API) and `backend/.venv-ml` (PyTorch CUDA 13.2), A5000 verified, every data source reachable without a proxy, data lake at `E:\stocksense\lake` with daily `live_prices` snapshots (`lake-prices`). No scheduler, backups or remote access yet (M0.4, M0.5). Details: `docs/college-pc-setup.md`. |

Open user actions: run `backend/schema.sql`; decide on `stocksense cleanup --apply`
(41 delisted stocks); rotate the old Upstox token and Superdesign key; add the
`SUPABASE_URL` and `SUPABASE_SERVICE_KEY` repository secrets to switch on the scheduled
pipeline; check college IT policy on long-running jobs and remote access before M0.4/M0.5.

---

## 3. Architecture

```
                    COLLEGE PC (engine — private)                         CLOUD (public)
┌──────────────────────────────────────────────────────────┐
│ Ingestion jobs (python -m stocksense <job>, scheduled)    │
│   prices · filings · holdings · deals · flows · news ·   │      ┌─────────────────────┐
│   F&O · macro · GDELT                                     │      │ Supabase            │
│        │                                                  │      │ (publishable layer) │
│        ▼                                                  │ ───► │ stocks, prices,     │
│ Data lake: Parquet + DuckDB (time series)                 │      │ scores, signals     │
│            LanceDB / pgvector (documents, embeddings)     │      └─────────┬───────────┘
│        │                                                  │                │
│        ▼                                                  │      ┌─────────▼───────────┐
│ GPU (A5000 24 GB): embeddings, local-LLM labelling,       │      │ Public API + site   │
│   fine-tuning, nightly inference, filings Q&A             │      │ (Render/Railway +   │
│        │                                                  │      │  Vercel)            │
│        ▼                                                  │      └─────────────────────┘
│ Internal API (FastAPI) + Terminal UI (golden UI)          │
│   reached only through Tailscale / Cloudflare Tunnel      │
└──────────────────────────────────────────────────────────┘
```

- **Two tiers of data.** *Internal* (anything we may use privately, incl. real-time
  from a personal broker API) stays on the college PC. *Publishable* (EOD/delayed
  prices, our own scores and analysis) is pushed to Supabase for the public site.
- **The college PC is the engine, not the server.** The public site never depends on
  it being up. Nightly backup of the data lake to cloud storage.
- **One code style everywhere:** each source is a module in `stocksense/sources`, each
  job in `stocksense/jobs`, pure logic in top-level modules, thin API routes.

Target repo layout (additions in **bold**):

```
backend/stocksense/
  sources/   nse_ipo, chart, news, yahoo, upstox, … **bhavcopy, xbrl, shareholding,
             announcements, deals, flows, fno, rbi, gdelt**
  jobs/      … **ingest_* per source, backup, train_*, infer_***
  **lake.py**        DuckDB/Parquet paths and helpers
  **models/**        geopolitics + filings models, each with train/eval/infer
  api/       app.py, schemas.py (+ routers as it grows)
**ml/**                notebooks/experiments that aren't production code yet
```

---

## 4. Data sources

"Internal" = fine for our own research. "Public" = fine to show on the public site.

| Source | What | Access | Internal | Public | Refresh |
|---|---|---|---|---|---|
| NSE bhavcopy archives | EOD prices, volumes, all stocks, 10+ yrs | Public download | ✅ | ✅ (EOD) | Daily |
| NSE F&O bhavcopy | EOD options/futures, open interest | Public download | ✅ | ✅ (EOD) | Daily |
| Upstox / Kite Connect | Real-time quotes and ticks | Personal API account | ✅ | ❌ needs redistribution licence | Live |
| NSE/BSE financial results (XBRL) | Quarterly P&L, balance sheet, cash flow | Public filings | ✅ | ✅ (derived figures) | Quarterly |
| Shareholding patterns, SAST | Promoter/FII/DII/MF holdings, pledges | Public filings | ✅ | ✅ | Quarterly / event |
| Insider trading (PIT), bulk & block deals | Who bought/sold | Public disclosures | ✅ | ✅ | Daily |
| Corporate announcements | Orders, results dates, board meetings | NSE/BSE feeds | ✅ | ✅ (headline + link) | Live |
| FII/DII flows | Daily cash-market flows | NSE reports | ✅ | ✅ | Daily |
| NSE IPO data | Open/upcoming issues, subscription | NSE website API | ✅ | ⚠️ prototype only; prefer filings/BSE for production | 5 min while open |
| SEBI DRHP/RHP PDFs | Prospectuses | Public | ✅ | ✅ (our analysis) | Per issue |
| Annual reports, concall transcripts | Text for Q&A / summaries | Company sites, exchange filings | ✅ | ✅ (our summaries, short quotes) | Per filing |
| Yahoo Finance | Fundamentals, charts, indices | yfinance / chart endpoint | ✅ | ⚠️ replace with filings + bhavcopy before going public | Daily |
| GDELT 2.0 | Global events, themes, tone since 2015 | Public | ✅ | ✅ | 15 min |
| News RSS (ET, Mint, BS, Google News) | Headlines | Public RSS | ✅ | ✅ (headline + link only) | 15 min |
| RBI DBIE, MOSPI, data.gov.in | Rates, CPI, IIP, forex, trade | Public | ✅ | ✅ | As released |
| Screener.in | Promoter/CAGR fallback | Scraping (light) | ⚠️ gaps only | ❌ | — |

Not allowed: logged-in/paid data from Trendlyne, Moneycontrol Pro, Bloomberg, Refinitiv,
broker back-ends; anything behind bot protection.

**Open decision (before Phase 5):** delayed/EOD prices on the public site (free, safe) or
licensed real-time (cost, paperwork).

---

## 5. Phases and milestones

Each milestone: one branch, one PR, acceptance criteria met, tests pass, docs updated.

### Phase 0 — Foundation

- [x] **M0.1 Merge & move.** PRs for `overhaul-2026-10-06` and `backend-api-2026-10-14`
  merged into `main`; repo cloned on the college PC; `.env` files copied by hand; keys
  rotated. *Accept:* `cd backend && pytest` passes on the college PC; `python -m stocksense api` serves `/health` with `data_source: supabase`.
  *Done 14 Oct: 71 tests pass; `/health` → supabase, 2,646 stocks. Key rotation not confirmed yet (§2).*
- [x] **M0.2 GPU & network check.** *Accept:* PyTorch sees the A5000 (`torch.cuda.is_available()`); NSE archives, Yahoo, GDELT, RSS all reachable from the campus network (or a documented workaround).
  *Done 14 Oct: all reachable, no proxy; only BSE's API refuses (its bot protection, not the campus).*
- [x] **M0.3 Data lake skeleton.** `stocksense/lake.py` with raw/clean/feature folders, DuckDB catalogue. *Accept:* one job writes Parquet and DuckDB can query it; layout documented in `backend/README.md`.
  *Done 14 Oct: `lake-prices` writes 2,648 rows to `clean/prices/`, `lake-query` reads them back.*
- [ ] **M0.4 Scheduler & backups.** Jobs run on a timetable (cron/systemd or the existing `scheduler`); nightly lake backup to cloud storage. *Accept:* a week of unattended runs with logs; restore tested once.
- [ ] **M0.5 Private access.** Tailscale or Cloudflare Tunnel to the internal API/UI. *Accept:* reachable from a laptop off-campus; not reachable from the open internet.

### Phase 1 — Core datasets (validation checks on every one: row counts, ranges, gaps, duplicates)

- [x] **M1.1 EOD prices** from bhavcopy, 10+ yrs, adjusted for splits/bonuses (corporate actions). *Accept:* spot checks against exchange data for 10 stocks; adjustment verified on 3 known splits.
  *Done 18 Oct: 4,167 trading days 2010→2026 in the lake (`eod_prices`, `eod_adjusted`); 8 of 10 large caps match Yahoo to the paisa, RELIANCE/ITC differ <2% only before their demergers (method noted); NESTLEIND, HDFCBANK, RELIANCE splits exact. `ml/checks/eod_spot_check.py`.*
- [ ] **M1.2 Fundamentals from XBRL** filings (quarterly + annual). *Accept:* revenue/profit for 20 large caps match published results; scoring switched from Yahoo to these numbers behind a flag, scores compared.
- [ ] **M1.3 Shareholding & pledges.** *Accept:* promoter %, FII %, DII %, pledge % history for any stock; matches filings for 10 samples.
- [ ] **M1.4 Announcements, insider trades, bulk/block deals, FII/DII flows.** *Accept:* daily ingestion, deduplicated, searchable by symbol and date.
  *Part done 19 Oct: 1.37 M announcements since 2015 and 337k insider trades (Nov 2015 → May 2026, NSE's feed stops there), daily, deduplicated, searchable (`filings SYMBOL`). FII/DII cash flows collected daily from 16 Oct 2026 (NSE serves only the latest day). Not possible yet: bulk/block deals — NSE's API is behind bot protection.*
- [x] **M1.5 F&O EOD** (option chain snapshots, OI, PCR). *Accept:* history for NIFTY/BANKNIFTY and F&O stocks.
  *Done 19 Oct: 4,163 days 2010→2026 of every contract (`fno_prices`) and a per-underlying summary (`fno_summary`: OI, put/call ratios, max-OI strikes). NIFTY/BANKNIFTY on every day; near-month futures sit 0.19%/0.22% (median) above spot, 99% of days within 0.9%. `fno_summary_current` maps renames (INFY history from 2010).*
- [ ] **M1.6 Macro** (RBI rates, CPI, IIP, forex reserves, crude, USD/INR). *Accept:* tidy time series with release dates (no look-ahead).
  *Part done 18 Oct: every NSE index since Feb 2012 (`index_prices`) and full daily history of crude, gold, copper, gas, USD/INR, dollar index, US 10y, S&P 500, VIX (`macro_prices`). Still to do: RBI rates, CPI, IIP, forex reserves with release dates.*

### Phase 2 — Terminal (inside the golden UI)

- [ ] **M2.1 Wire existing panels to the API**: dashboard, screener, stock analysis, IPO analyser, geopolitics, RHP scanner. *Accept:* no panel uses `lib/constants.ts` sample data; the look is unchanged.
- [ ] **M2.2 Command bar**: `INFY ⏎` opens a company, `INFY FA` financials, `INFY HDS` holders, `INFY N` news, `IPO`, `GEO`, `FLOWS`. Keyboard navigation throughout. *Accept:* every screen reachable without a mouse.
- [ ] **M2.3 Company page**: overview, financials (from M1.2), holders (M1.3), events, news, peers, score breakdown. *Accept:* parity with the data available for 20 sample stocks.
- [ ] **M2.4 Watchlists & alerts**: price moves, unusual volume, pledge changes, large orders, results dates. *Accept:* alerts fire on historical replay of a known event.

### Phase 3 — Intelligence (GPU)

- [x] **M3.1 Event study engine (no ML).** For each event type (crude spike, conflict, rate change, rupee move, tariff…), sector excess returns vs NIFTY over 1/3/10 days across history. *Accept:* "historical analogues" table per event type with sample sizes and confidence intervals; served by the API.
  *Done 18 Oct: 12 event types (crude, rupee, US markets, gold, GDELT conflict/India–Pakistan/China/Middle East/sanctions), 481 episodes since 2012, n + 95% CI per sector and horizon; `/geopolitics/analogues`. Rate changes and tariffs wait for M1.6's RBI data and a headline archive (M3.2). Results: `docs/event-study-2026-10.md`.*
- [ ] **M3.2 Labelled dataset.** Local LLM (e.g. Qwen 2.5 14B / Llama 3.1 8B) labels headlines + GDELT events with topic, region, affected sectors, direction. *Accept:* ≥50k labelled items; 500-item human-checked sample with measured agreement.
- [ ] **M3.3 Geopolitics models.** Fine-tuned FinBERT/DeBERTa-v3 classifier (topic/sector/direction) + embedding-based analogue retrieval + gradient-boosted model predicting next-day sector excess returns from daily features. *Accept:* see §6; beats the keyword-rule baseline (`geo.py`) on held-out later periods.
- [ ] **M3.4 Nightly signals.** Score new news, write `geo_signals` (sector, effect, strength, analogues, evidence links) to Supabase; `/geopolitics` serves models instead of rules. *Accept:* runs unattended for a week; model version recorded with every signal.
- [ ] **M3.5 Filings Q&A.** Vector index over annual reports, DRHPs, concall transcripts; local LLM answers with citations. *Accept:* 50 test questions, answers cite the right document/page ≥80% of the time.
- [ ] **M3.6 Concall summaries & guidance tracking.** *Accept:* summary + guidance changes for 50 companies' latest calls, spot-checked.
- [ ] **M3.7 Prospectus model.** Train on historical DRHPs + listing outcomes: which red flags actually preceded weak listings. *Accept:* evaluated on later IPOs; rules in `rhp.py` reweighted by evidence.

### Phase 4 — Public StockSense

- [ ] **M4.1 Deploy the API** (Docker on Render/Railway) with the read-only key and CORS for the site. *Accept:* `/health` public; uptime monitor.
- [ ] **M4.2 Deploy the site** (Vercel) pointed at the public API. *Accept:* every public page works with Supabase only (college PC off).
- [ ] **M4.3 Publishable layer only.** EOD/delayed prices, own scores/signals, headlines with links. *Accept:* checklist against §4 signed off.
- [ ] **M4.4 Accounts** (Supabase Auth): saved watchlists, paper-trading portfolios. *Accept:* data private per user (RLS tested).

---

## 6. How models are judged

- **Time-based splits only.** Train on earlier periods, test on later ones
  (walk-forward). Never shuffle across time; no feature may use information released
  after the prediction time.
- **Baselines first.** Every model is compared with (a) the keyword rules in `geo.py`
  and (b) "no change" / sector-average. If it doesn't beat both on held-out periods,
  it doesn't ship.
- **Metrics.** Classifiers: macro-F1 per label, on a human-checked test set. Return
  models: rank correlation (IC) between predicted and realised sector excess returns,
  hit rate, and stability across years — not a single lucky period.
- **Report honestly.** News-to-returns is noisy; a small, stable edge is a good result.
  Write results to `ml/reports/<model>-<date>.md` with data ranges and baselines.
- **Reproducible.** Fixed seeds, data snapshot IDs, model version stored with every
  prediction.

---

## 7. College PC setup checklist

- [ ] Confirm college IT policy allows long-running personal jobs, outbound internet to data sources, and storing personal API keys. Get it in writing if unsure.
- [ ] Install: git, Python 3.12, CUDA drivers + PyTorch (CUDA build), Node 22, DuckDB, Tailscale (or cloudflared), Docker (optional).
  *14 Oct: all but Tailscale/cloudflared (M0.5) and Docker; DuckDB is the Python package.*
- [x] `git clone https://github.com/stocksense-in/stocksense-web.git && cd stocksense-web`
- [x] Copy `backend/.env` and `frontend/.env.local` by hand (USB/password manager/remote desktop), never via git or chat. A repo-root `.env.local` isn't needed.
- [x] Python envs + tests: see `docs/college-pc-setup.md` (Windows, uv).
- [x] `python ml/gpu_check.py` → A5000, CUDA available
- [x] Reachability: NSE archives, Yahoo chart URL, GDELT, RSS feeds (table in `docs/college-pc-setup.md`).
- [x] Disk: lake on `E:` (408 GB free at setup).
- [ ] Power/reboots: jobs must resume safely (idempotent, checkpointed); note the machine's maintenance windows.
- [x] Claude Code logged in **locally** on this PC for GPU/data work (cloud sessions have no GPU).

---

## 8. How to run sessions (budget)

- **Cloud sessions** (≈$100 credit): application code — API endpoints, wiring the golden
  UI, tests. One milestone per session; stop when the PR is open.
- **Local sessions on the college PC**: data ingestion, training, anything needing the GPU
  or the lake.
- Start each session with: *"Read PLAN.md. Next milestone: M_._. Work on branch
  `<name>`; open a PR when the acceptance criteria pass."*
- Keep sessions small and specific; long open-ended sessions burn credit and drift.

---

## 9. Decisions log

| Date | Decision |
|---|---|
| 2026-10-06 | Backend restructured into one package; scores fixed (D/E units, missing-metric handling). |
| 2026-10-06 | Two UI redesigns tried and rejected; original golden UI kept. |
| 2026-10-14 | REST API added; geopolitics v0 = keyword rules over live news (the baseline). |
| 2026-10-14 | Direction: internal Indian-markets terminal + public StockSense on the publishable subset. Training/inference on the college A5000; public site never depends on it. |
| 2026-10-14 | College PC is the engine: Windows 11, Xeon W-2295 (18 cores), 128 GB RAM, RTX A5000 24 GB (driver 596.51, CUDA 13.2). Data lake root `E:\stocksense\lake` (Parquet + DuckDB, `STOCKSENSE_LAKE_DIR`). ML in a separate `backend/.venv-ml` (`requirements-ml.txt`, PyTorch 2.14.1+cu132) so the API env stays identical to its container. |
| 2026-10-18 | Price history from NSE bhavcopy (not Yahoo). Adjustments read from NSE's corporate-action wording and checked against the overnight price jump (the bhavcopy's prev_close is *not* adjusted on ex-dates); demergers and rights issues adjusted on price only; splits missing from the feed inferred from round overnight ratios. Dividends not adjusted. |
| 2026-10-18 | Event study before models (M3.1): 12 event types, declustered, bootstrap CIs, published as a JSON the API serves (public API never needs the engine). News signals are coverage spikes in GDELT dated by file day; the India signal counts hostile acts between India and Pakistan/China (6 of 7 known crises caught). |
| 2026-10-19 | F&O history from NSE's F&O bhavcopy with units checked across the 2024 format switch; summary per underlying computed with vectorised group-bys and built in parallel (whole history in ~4 min). |
| 2026-10-19 | Filings and flows from NSE's own APIs, one request per month, dated by when the market could know (broadcast / disclosure time). Bulk/block deals skipped rather than scraped past bot protection. |
| _open_ | Public prices: delayed/EOD vs licensed real-time. |
