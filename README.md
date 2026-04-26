# StockSense 📈

> **Smart stock decision platform for Indian retail investors — powered by real-time NSE data, fundamental analysis, and AI-driven scoring.**

---

## Overview

StockSense is a full-stack web application that helps beginners make smarter stock investment decisions. It tracks **all 2,200+ NSE-listed stocks**, scores them using a multi-factor fundamental algorithm, and presents live prices, sector analysis, IPO data, mutual funds, and more — all in one clean dashboard.

---

## Features

| Feature | Description |
|---|---|
| 📊 **Live Prices** | Real-time prices for all NSE stocks + NIFTY50 & SENSEX |
| 🧮 **Fundamental Scoring** | PE, ROE, D/E, Net Margin, Promoter Holding, Revenue CAGR |
| 🔍 **Stock Screener** | Filter stocks by sector, score, market cap |
| 📈 **Analysis** | Deep-dive charts and metric breakdowns |
| 🏦 **Mutual Funds** | MF data and comparisons |
| 🚀 **IPO Tracker** | Upcoming and recent IPO listings |
| 🌍 **Geopolitics Engine** | Macro event impact on sectors |
| 📄 **RHP Analyser** | Red Herring Prospectus AI analyser |
| 🎮 **Paper Trading** | Simulated trading for practice |
| 👤 **Profile & Premium** | User accounts and premium features |

---

## Tech Stack

### Frontend
- **Framework**: [Next.js 16](https://nextjs.org/) + [React 19](https://react.dev/)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Database Client**: [@supabase/supabase-js](https://supabase.com/docs/reference/javascript)

### Backend / Data Pipeline
- **Language**: Python 3.11+
- **Data Source**: Yahoo Finance (`yfinance`), NSE official equity list, Screener.in
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **Key Libraries**: `yfinance`, `supabase`, `requests`, `python-dotenv`

---

## Project Structure

```
stocksense-web/
├── app/                        # Next.js app router pages
│   ├── page.tsx                # Main dashboard
│   ├── screener/               # Stock screener
│   ├── analysis/               # Stock analysis
│   ├── ipo/                    # IPO tracker
│   ├── mf/                     # Mutual funds
│   ├── paper-trading/          # Paper trading simulator
│   ├── geopolitics-engine/     # Macro/geopolitics module
│   ├── rhp-analyser/           # RHP AI analyser
│   └── premium/                # Premium features
├── components/                 # Shared React components
├── lib/                        # Utility functions & scoring logic
├── backend/                    # Data pipeline scripts
│   ├── nse_symbols.py          # Fetches all NSE symbols dynamically
│   ├── fetch_yfinance.py       # Main pipeline: fundamentals + prices
│   ├── fetch_nse.py            # Promoter holding & Revenue CAGR
│   ├── fetch_live_prices.py    # Live price updater (all NSE stocks)
│   ├── fetch_fundamentals.py   # Lightweight fundamentals fetcher
│   ├── scheduler.py            # Auto-scheduler (runs during market hours)
│   └── requirements.txt        # Python dependencies
├── .env.local                  # Environment variables (not committed)
└── README.md
```

---

## Getting Started

### 1. Clone & Install (Frontend)

```bash
git clone <repo-url>
cd stocksense-web
npm install
npm run dev
```

### 2. Set Up Environment Variables

Create `.env.local` in the project root:

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_SUPABASE_SERVICE_KEY=eyJ...   # service-role key (for Python scripts)
```

### 3. Set Up Python Environment

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Python Data Pipeline

All scripts live in `backend/` and share the `venv`. Run them from the `backend/` directory.

### Script Reference

| Script | Purpose | Run frequency |
|---|---|---|
| `nse_symbols.py` | Downloads & caches all 2,258 NSE equity symbols | Auto (cached 24h) |
| `fetch_yfinance.py` | Fetches PE, ROE, D/E, margin, price for all stocks | Daily / on-demand |
| `fetch_nse.py` | Fetches promoter holding % & revenue CAGR | Nightly |
| `fetch_live_prices.py` | Updates live prices for all stocks | Every 1–5 min (via scheduler) |
| `fetch_fundamentals.py` | Lightweight fundamentals refresh | On-demand |
| `scheduler.py` | **Auto-runs live prices during market hours** | Keep running |

---

### Recommended Run Order

```powershell
# Step 1 — Initial full fetch (run once, takes ~30-60 min)
venv\Scripts\python.exe fetch_yfinance.py

# Step 2 — Retry any stocks that failed
venv\Scripts\python.exe fetch_yfinance.py --retry-failed

# Step 3 — Fetch promoter holding + revenue CAGR
venv\Scripts\python.exe fetch_nse.py

# Step 4 — Start the live price scheduler (keep this running)
venv\Scripts\python.exe scheduler.py
```

---

### Scheduler (Auto Live Prices)

The scheduler automatically updates prices during **NSE market hours (9:15 AM – 3:30 PM IST, Mon–Fri)** and sleeps outside market hours.

```powershell
# Default: all stocks, every 5 minutes, market hours only
venv\Scripts\python.exe scheduler.py

# Every 1 minute
venv\Scripts\python.exe scheduler.py --interval 1

# Run 24/7 (for testing)
venv\Scripts\python.exe scheduler.py --no-market-check

# Also refresh fundamentals once per day at market open
venv\Scripts\python.exe scheduler.py --daily-fundamentals

# Only track specific symbols
venv\Scripts\python.exe scheduler.py --symbols INFY TCS HDFCBANK RELIANCE

# Stop: press Ctrl+C
```

---

### Fetch Script Flags

All pipeline scripts support these flags:

```powershell
# Only process specific stocks
--symbols INFY TCS RELIANCE

# Test run (first N stocks only)
--limit 20

# Force refresh NSE symbol list (ignore 24h cache)
--refresh-symbols

# Retry stocks that failed last run (fetch_yfinance.py only)
--retry-failed

# Tune concurrency
--workers 8 --batch-size 50
```

---

## Scoring Algorithm

Each stock receives a **composite score (0–100)** based on 6 weighted metrics:

| Metric | Weight | Logic |
|---|---|---|
| P/E Ratio | 20% | Lower is better (adjusted by sector) |
| ROE | 20% | Higher is better |
| Debt / Equity | 15% | Lower is better |
| Net Profit Margin | 20% | Higher is better |
| Promoter Holding | 10% | Higher is better |
| Revenue CAGR (3yr) | 15% | Higher is better |

Special rules:
- **New-age stocks** (Zomato etc.): P/E fixed at 40 (not penalised)
- **Banks / NBFCs**: D/E and P/E benchmarked differently (higher D/E is normal)

---

## Database (Supabase Tables)

| Table | Description |
|---|---|
| `stocks` | Fundamentals, scores, sector for all NSE stocks |
| `live_prices` | Latest price + daily change % per symbol |

---

## Coverage

- **NSE Equity Symbols**: ~2,258 (from NSE's official `EQUITY_L.csv`)
- **Successfully fetched via yfinance**: ~1,734+ stocks
- **Fallback chain**: NSE ticker → BSE ticker → price-only history → Screener.in
- **Failed symbols** (no Yahoo Finance data): logged to `failed_symbols.txt`

---

## License

Private project — all rights reserved.