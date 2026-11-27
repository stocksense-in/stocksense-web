# Publishable layer: what the public site may show (M4.3), 27 Nov 2026

M4.3 asks that the public site serve only what PLAN §4 marks as publishable: EOD or delayed
prices, our own scores and signals, and headlines with links. This audit goes through every API
endpoint, names the source behind each field, and gives its §4 status. Sign-off is the owner's
call; the four changes at the end are what stands between today's API and a public one.

Legend: ✅ publishable as is · ⚠️ allowed for now, replace before going public · ❌ must not be public.

## Endpoint by endpoint

| Endpoint | What it serves | Source | §4 | Note |
|---|---|---|---|---|
| `/health` | status, data source | — | ✅ | |
| `/market/indices`, `/market/overview`, `/sectors` | index levels, day change, breadth, sector moves | Supabase `live_prices`: written by `prices` (Yahoo, ~15 min delayed) or by `realtime` / the scheduler's Upstox path when a token is fresh | ❌ when from Upstox, ⚠️ when from Yahoo | Upstox quotes need a redistribution licence. **Change 1** |
| `/stocks`, `/stocks/search`, screener filters | price, change, market cap, ratios, score | `live_prices` as above; ratios and score inputs from Supabase `stocks` (`fundamentals` job: Yahoo; promoter holding: Yahoo "insiders", Screener.in fallback for gaps) | ❌ / ⚠️ | Screener.in is ❌ for public; Yahoo ⚠️. **Changes 1, 2** |
| `/stocks/{symbol}` | the above plus the score breakdown | as above | ❌ / ⚠️ | **Changes 1, 2** |
| `/stocks/{symbol}/history` | price chart | Yahoo's chart endpoint, fetched live by the API (`sources/chart.py`) | ⚠️ | **Change 3** |
| `/stocks/{symbol}/financials` | quarterly and yearly results | NSE results feed + SEBI integrated-filing XBRL (`data/financials.json`) | ✅ | derived figures |
| `/stocks/{symbol}/holders` | promoter %, FII/DII split, pledges | NSE shareholding patterns (`data/holders.json`) | ✅ | |
| `/stocks/{symbol}/events` | notable filings (title + link), insider trades, bulk/block deals | NSE announcements, SEBI PIT disclosures, NSE deals files (`data/events.json`) | ✅ | headlines link to the filing |
| `/stocks/{symbol}/dividends` | dividends, splits, bonuses | NSE corporate actions (`data/dividends.json`) | ✅ | |
| `/stocks/{symbol}/news`, `/news` | headlines | public RSS (ET, Mint, BS, Google News) | ✅ | headline + link only, as served |
| `/alerts` | moves, volume, results, orders, stakes, pledges, big deals | lake-derived from bhavcopy and NSE filings (`data/alerts.json`) | ✅ | EOD |
| `/economy` | repo rate, CPI, IIP, forex reserves, 10-year yield | BIS, MoSPI, IMF and OECD via FRED (`data/economy.json`) | ✅ | public statistics; keep the source line shown |
| `/geopolitics`, `/geopolitics/analogues*` | sector signals and past analogues | RSS headlines + GDELT + bhavcopy (`data/geo_analogues.json`) | ✅ | our own analysis |
| `/learn/metrics` | teaching content | ours | ✅ | |
| `/ipos` | open and upcoming issues, live subscription | NSE website API (`sources/nse_ipo.py`) | ⚠️ | §4: prototype only. **Change 4** |
| `/ipos/listings` | recent listings and gains | NSE past issues + `live_prices` | ⚠️ | follows Changes 1 and 4 |
| `/prospectus/rules`, `/prospectus/scan` | rule list; scan of a PDF the user uploads (not stored) | our rules (`rhp.py`) | ✅ | |

## The four changes before going public

1. **EOD prices in Supabase, never Upstox.** The public deployment must not read quotes the
   `realtime` job or the scheduler's Upstox path wrote. The simplest safe layout is to keep
   Upstox quotes in a table the public API never reads, and have the engine publish each day's
   close and change from the bhavcopy (already in the lake) into the table it does read. Yahoo's
   delayed quotes can bridge the gap but are ⚠️. *Writes to Supabase: needs the owner's go-ahead.*
2. **Fundamentals and promoter holding from filings.** Done in the lake and compared across the
   market (M1.2, M1.3); switching the published score is one `rescore --fundamentals filings
   ... --apply` and the promoter switch is one more (`docs/fundamentals-from-filings-2026-11.md`,
   `docs/promoter-holding-switch-2026-11.md`). That also retires the Screener.in fallback for
   anything shown. *Supabase writes: awaiting the owner.*
3. **Charts from our own EOD history.** The API fetches Yahoo charts live. A public API with the
   college PC off can't read the lake, so the engine would publish adjusted daily closes (one row
   per stock per day, about 2,600 rows a day) to Supabase or a static file the API serves, the
   same way `financials.json` is served today. Intraday ranges (1d, 5d) would then be dropped or
   shown as EOD only.
4. **IPO data from filings, not NSE's site API.** For production, build open/upcoming issues from
   SEBI's offer documents (the register `ingest-rhp` already reads) and exchange circulars; keep
   live subscription numbers out of the public site until a sanctioned source is found.

## Checklist for sign-off

- [ ] No public endpoint serves Upstox data (Change 1)
- [ ] No public field comes from Screener.in (Change 2)
- [ ] Yahoo removed from scores (Change 2), quotes (Change 1) and charts (Change 3)
- [ ] IPO pages use filings, or are marked as a prototype (Change 4)
- [x] Filings, holdings, events, dividends, alerts, economy, geopolitics and news already
      publishable as served (headlines and filings shown as title + link)
- [x] Nothing behind bot protection is collected (NSE's deals API is skipped for its public
      archive files; BSE's API isn't used)
