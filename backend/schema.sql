-- StockSense database schema (Supabase / Postgres).
-- Safe to run more than once: paste into Supabase → SQL Editor → Run.
-- Creates the tables on a fresh project, and adds any missing columns to an existing one.

-- ── stocks: one row per NSE stock, written by `fundamentals` and `ownership` ──
create table if not exists public.stocks (
  symbol            text primary key,              -- NSE symbol, e.g. INFY
  name              text,
  last_updated      timestamptz default now()
);

alter table public.stocks
  add column if not exists isin              text,
  add column if not exists sector            text,          -- StockSense code: it, bank, nbfc, fmcg… (backend/stocksense/sectors.py)
  add column if not exists industry          text,          -- Yahoo industry, e.g. "Banks - Regional"
  add column if not exists market_cap        bigint,        -- ₹ crore
  add column if not exists price             numeric,
  add column if not exists price_change_pct  numeric,
  add column if not exists week52_high       numeric,
  add column if not exists week52_low        numeric,
  add column if not exists pe_ratio          numeric,
  add column if not exists pb_ratio          numeric,
  add column if not exists roe               numeric,       -- %
  add column if not exists debt_equity       numeric,       -- ratio (0.4 = 0.4×)
  add column if not exists net_margin        numeric,       -- %
  add column if not exists dividend_yield    numeric,       -- %
  add column if not exists promoter_holding  numeric,       -- %
  add column if not exists revenue_cagr_3yr  numeric,       -- %
  add column if not exists composite_score   smallint,      -- 0–100, null when < 4 metrics known
  add column if not exists score_coverage    smallint;      -- how many of the 6 metrics were known

create index if not exists stocks_score_idx  on public.stocks (composite_score desc nulls last);
create index if not exists stocks_sector_idx on public.stocks (sector);

-- ── live_prices: latest price per symbol (stocks + indices), written by `prices` / `realtime` ──
create table if not exists public.live_prices (
  symbol      text primary key,                    -- NSE symbol, or NIFTY50 / SENSEX / BANKNIFTY / INDIAVIX
  price       numeric not null,
  change_pct  numeric,
  updated_at  timestamptz default now()
);

-- ── Access: anyone may read, only the service-role key (backend) may write ──
-- The website uses the anon key, so it can read but never modify data.
alter table public.stocks      enable row level security;
alter table public.live_prices enable row level security;

drop policy if exists "public read" on public.stocks;
create policy "public read" on public.stocks for select using (true);

drop policy if exists "public read" on public.live_prices;
create policy "public read" on public.live_prices for select using (true);

-- Tell the API layer about new columns immediately.
notify pgrst, 'reload schema';
