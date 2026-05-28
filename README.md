<div align="center">

# 📈 StockSense

### Smart AI-Powered Equities Platform for Indian Retail Investors

[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://supabase.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Private-ff69b4?style=for-the-badge)](#-license)

**StockSense democratises institutional-grade analysis for the retail investor. It processes 2,200+ NSE stocks in real-time, computes multi-factor fundamental scores, and provides intelligent screeners, AI RHP analysis, and a simulated trading environment.**

[Getting Started](#-getting-started) · [Architecture](#-architecture) · [Algorithm](#-scoring-algorithm) · [Data Pipeline](#-python-data-pipeline)

---

> <img width="1470" height="835" alt="image" src="https://github.com/user-attachments/assets/4a2de7c2-2769-4047-abf1-6a1f21f68dac" />

>
> <img width="1470" height="835" alt="image" src="https://github.com/user-attachments/assets/ffe256b9-7b42-4b9b-8713-cb5eaf682d9e" />

>
> <img width="1470" height="835" alt="image" src="https://github.com/user-attachments/assets/425b85d2-c1e4-46ea-9d5d-f42bb3e94a67" />


</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Engineering Highlights](#-engineering-highlights)
- [Core Features](#-core-features)
- [Scoring Algorithm](#-scoring-algorithm)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Python Data Pipeline](#-python-data-pipeline)
- [License](#-license)

---

## 🎯 Overview

The Indian stock market has over **2,200 listed companies**. Most beginners rely on tipsters or face analysis paralysis. StockSense solves this by programmatically evaluating every NSE-listed stock against strict fundamental criteria, serving it through an ultra-fast, visually stunning Next.js dashboard.

### The Problem

| Traditional Process | Pain Point |
|---|---|
| Manual Screening | Takes hours to find fundamentally strong stocks |
| Fragmented Data | Checking prices, IPOs, and MF data across 5 different sites |
| Complex RHPs | IPO prospectuses are 400+ pages of dense legal jargon |
| "Gut Feeling" Trading | Real money lost due to lack of a safe practice environment |

### The Solution

StockSense aggregates data from Yahoo Finance, NSE, and Screener.in via a custom **Python data pipeline**. It runs a proprietary **6-factor algorithm** to score stocks (0-100), offers an **AI-powered RHP analyser** for instant IPO summaries, and features a **Paper Trading module** to validate strategies safely.

---

## 🏗 Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Next.js)                         │
│              TypeScript · App Router · Tailwind CSS v4           │
│         Dashboard · Screener · Analysis · Paper Trading          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS (REST / Server Actions)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SUPABASE (PostgreSQL)                       │
│                                                                  │
│  • RLS Auth      • stocks table        • live_prices table       │
│  • User Profiles • Portfolios          • Watchlists              │
└──────────────┬─────────────────────────────┬────────────────────┘
               │ Write                       │ Write
               ▼                             ▼
┌──────────────────────────┐      ┌──────────────────────────────┐
│   ASYNC DATA PIPELINE    │      │    LIVE PRICE SCHEDULER      │
│      (Python 3.11+)      │      │       (scheduler.py)         │
│                          │      │                              │
│ • yfinance integration   │      │ • 1-5 min intervals          │
│ • NSE/BSE fallbacks      │      │ • Active ONLY during market  │
│ • Fundamental scoring    │      │   hours (9:15 AM - 3:30 PM)  │
└──────────────────────────┘      └──────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js + React 19 | Server-side rendering, App Router |
| **Styling** | Tailwind CSS v4 | Utility-first responsive design, modern UI |
| **Language** | TypeScript / Python | Type-safe UI / Robust data processing |
| **Database** | Supabase (PostgreSQL) | Managed Postgres with Row Level Security |
| **Data Source 1** | `yfinance` | Primary provider for PE, ROE, D/E, margins |
| **Data Source 2** | NSE API | Official equity list, promoter holding, CAGR |
| **AI Analysis** | OpenAI/LLM | RHP Analyser for parsing dense IPO documents |
| **Pipeline** | Python Scheduler | Concurrent data fetching and syncing |

---

## ⚡ Engineering Highlights

### 1. Proprietary 6-Factor Scoring Algorithm
Every stock is evaluated dynamically across 6 weighted parameters. 

- **Specialized Industry Handling**: Banks/NBFCs are benchmarked differently (higher D/E is ignored), and new-age tech stocks (Zomato, Paytm) have their P/E capped to avoid unfair penalization.

### 2. High-Concurrency Python Pipeline
Fetching data for 2,200+ symbols synchronously takes hours. The `fetch_yfinance.py` pipeline utilizes asynchronous concurrency and chunking, reducing total sync time significantly. It employs a **fallback chain**: `NSE Ticker → BSE Ticker → Price-only history → Screener.in`.

### 3. Smart Market-Hours Scheduler
The `scheduler.py` daemon doesn't blindly ping APIs 24/7. It incorporates Indian Standard Time (IST) awareness, automatically waking up at **9:15 AM** and hibernating at **3:30 PM Mon-Fri**, saving API rate limits and compute.

### 4. AI-Powered RHP Analyser
IPO prospectuses are notoriously dense. The RHP Analyser ingests complex PDFs and outputs digestible summaries: risk factors, promoter background, object of the issue, and valuation metrics, slashing research time from hours to minutes.

---

## 🚀 Core Features

| Feature | Description |
|---|---|
| 📊 **Real-Time Prices** | Live NIFTY50, SENSEX, and individual stock tracking |
| 🧮 **Fundamental Scoring** | 0-100 composite score based on PE, ROE, D/E, Net Margin, Promoter Holding, and Revenue CAGR |
| 🔍 **Advanced Screener** | Instantly filter 2,200+ stocks by sector, score, market cap, and valuation metrics |
| 🎮 **Paper Trading** | Zero-risk simulated trading environment with P&L tracking |
| 🌍 **Geopolitics Engine** | Tracks macro events and their projected impact on specific Indian sectors |
| 🚀 **IPO Tracker** | Pipeline of upcoming and newly listed IPOs with GMP insights |
| 🏦 **Mutual Funds** | Comprehensive MF comparisons and NAV tracking |
| 👤 **Premium Tiers** | User authentication with premium feature gating (Supabase Auth) |

---

## 🧮 Scoring Algorithm

Each stock receives a **composite score (0–100)** based on 6 weighted metrics.

| Metric | Weight | Logic |
|---|---|---|
| P/E Ratio | 20% | Lower is better (adjusted by sector average) |
| ROE | 20% | Higher is better (>15% preferred) |
| Net Profit Margin | 20% | Higher is better |
| Debt / Equity | 15% | Lower is better (<1 preferred, ignored for Banks/NBFCs) |
| Revenue CAGR (3yr) | 15% | Higher is better (consistent growth) |
| Promoter Holding | 10% | Higher is better (skin in the game) |

---

## 📁 Project Structure

```text
stocksense-web/
├── app/                        # Next.js App Router (Frontend)
│   ├── page.tsx                # Main dashboard
│   ├── screener/               # Stock screener
│   ├── analysis/               # Stock analysis deep-dive
│   ├── ipo/                    # IPO tracker
│   ├── mf/                     # Mutual funds
│   ├── paper-trading/          # Simulated trading module
│   ├── geopolitics-engine/     # Macro/geopolitics impact tracker
│   ├── rhp-analyser/           # AI-powered IPO prospectus analyser
│   └── premium/                # Premium features & paywalls
├── components/                 # Shared React UI components
├── lib/                        # Utility functions & frontend scoring logic
├── backend/                    # Python Data Pipeline
│   ├── nse_symbols.py          # Fetches all NSE symbols dynamically
│   ├── fetch_yfinance.py       # Main pipeline: fundamentals + prices
│   ├── fetch_nse.py            # Promoter holding & Revenue CAGR
│   ├── fetch_live_prices.py    # Live price updater
│   ├── fetch_fundamentals.py   # Lightweight fundamentals fetcher
│   ├── scheduler.py            # Auto-scheduler for market hours
│   └── requirements.txt        # Python dependencies
├── .env.local                  # Environment variables
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js ≥ 20.x
- Python ≥ 3.11
- Git

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
NEXT_PUBLIC_SUPABASE_SERVICE_KEY=eyJ...   # Used by Python scripts for DB writes
```

### 3. Set Up Python Environment

```powershell
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
# source venv/bin/activate

pip install -r requirements.txt
```

---

## 🐍 Python Data Pipeline

The backbone of StockSense. All scripts live in `backend/` and share the `venv`.

### Recommended First-Time Run Order

```powershell
# Step 1 — Initial full fetch (fetches 2,200+ stocks, takes ~30-60 min)
venv\Scripts\python.exe fetch_yfinance.py

# Step 2 — Retry any stocks that hit rate limits or failed
venv\Scripts\python.exe fetch_yfinance.py --retry-failed

# Step 3 — Fetch promoter holding + revenue CAGR from NSE
venv\Scripts\python.exe fetch_nse.py

# Step 4 — Start the live price scheduler (keep this running in background)
venv\Scripts\python.exe scheduler.py
```

### The Scheduler (Auto Live Prices)

The scheduler automatically updates prices during **NSE market hours (9:15 AM – 3:30 PM IST, Mon–Fri)**.

```powershell
# Default: all stocks, every 5 minutes, market hours only
venv\Scripts\python.exe scheduler.py

# Aggressive mode: Every 1 minute
venv\Scripts\python.exe scheduler.py --interval 1

# Run 24/7 (bypass market hours check for weekend testing)
venv\Scripts\python.exe scheduler.py --no-market-check

# Targeted symbols only
venv\Scripts\python.exe scheduler.py --symbols INFY TCS HDFCBANK RELIANCE
```

---

## 📄 License

**Private Project** — All rights reserved.

<div align="center">

*Empowering retail investors with data-driven insights.*

</div>
