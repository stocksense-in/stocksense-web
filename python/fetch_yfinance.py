"""
StockSense — fetch_yfinance.py
Pipeline: python/pipeline/fetch_yfinance.py

Fetches live price + fundamental data for a watchlist of NSE stocks
using yfinance, scores each stock using the StockSense algorithm,
and upserts results into Supabase.

Usage:
    # Install deps first (once):
    pip install yfinance supabase python-dotenv

    # Run manually:
    python fetch_yfinance.py

    # Scheduled (see scheduler.py):
    python fetch_yfinance.py --symbols INFY HDFCBANK TATAMOTORS ZOMATO

Environment variables (.env in project root):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...   ← service-role key (bypasses RLS)
"""

import os
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import yfinance as yf
from supabase import create_client, Client

# Load .env — search this file's directory AND up to 3 parent dirs.
# Covers both:  python/fetch_yfinance.py  (needs ../.. /.env at project root)
# and running directly from the project root.
def _load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(4):
        candidate = search / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            logging.getLogger(__name__).debug(f"Loaded .env from {candidate}")
            return
        search = search.parent
    load_dotenv()  # fallback: let python-dotenv find it via CWD

_load_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────────────────────

# NSE tickers must have the .NS suffix for yfinance
WATCHLIST: dict[str, dict] = {
    "INFY":        {"yf": "INFY.NS",      "name": "Infosys Ltd",          "sector": "it"},
    "HDFCBANK":    {"yf": "HDFCBANK.NS",  "name": "HDFC Bank Ltd",        "sector": "bank"},
    "TATAMOTORS":  {"yf": "TATAMOTORS.NS","name": "Tata Motors Ltd",      "sector": "auto"},
    "ZOMATO":      {"yf": "ZOMATO.NS",    "name": "Zomato Ltd",           "sector": "newage"},
    "TCS":         {"yf": "TCS.NS",       "name": "Tata Consultancy Svcs","sector": "it"},
    "BAJFINANCE":  {"yf": "BAJFINANCE.NS","name": "Bajaj Finance Ltd",    "sector": "nbfc"},
    "SUNPHARMA":   {"yf": "SUNPHARMA.NS", "name": "Sun Pharmaceutical",   "sector": "pharma"},
    "MTAR":        {"yf": "MTAR.NS",      "name": "MTAR Technologies",    "sector": "defence"},
    "DIVI":        {"yf": "DIVISLAB.NS",  "name": "Divi's Laboratories",  "sector": "pharma"},
    "KALYANKJIL":  {"yf": "KALYANKJIL.NS","name": "Kaynes Technology",    "sector": "electronics"},
}

# Sector classification used by scoring algorithm
BANK_SECTORS  = {"bank", "nbfc"}
NEWAGE_SECTORS = {"newage"}


# ──────────────────────────────────────────────────────────────
#  Scoring algorithm  (mirrors lib/scores.ts exactly)
# ──────────────────────────────────────────────────────────────

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def score_stock(metrics: dict, sector: str) -> dict:
    """
    Returns:
        {
          "individual": {"pe": 0-100, "roe": ..., ...},
          "composite":  0-100  (int)
        }
    Exactly matches Section 6 scoring algorithm in the brief.
    """
    scores: dict[str, float] = {}

    # 1. P/E  —  lower is better (except new-age: fixed 40)
    pe = metrics.get("pe_ratio") or 0.0
    if sector in NEWAGE_SECTORS:
        scores["pe"] = 40.0
    elif sector in BANK_SECTORS:
        scores["pe"] = _clamp(100 - (pe - 8) / 30 * 100)
    else:
        scores["pe"] = _clamp(100 - (pe - 8) / 42 * 100)

    # 2. ROE  —  higher is better
    roe = metrics.get("roe") or 0.0
    scores["roe"] = _clamp(roe / 50 * 100)

    # 3. Debt/Equity  —  lower is better (banks scored differently)
    de = metrics.get("debt_equity") or 0.0
    if sector in BANK_SECTORS:
        scores["de"] = _clamp(100 - (de - 3) / 12 * 100)
    else:
        scores["de"] = _clamp(100 - (de / 3.5) * 100)

    # 4. Net Profit Margin
    margin = metrics.get("net_margin") or 0.0
    scores["margin"] = _clamp(margin / 38 * 100)

    # 5. Promoter Holding
    promoter = metrics.get("promoter_holding") or 0.0
    scores["promoter"] = _clamp(promoter / 80 * 100)

    # 6. Revenue CAGR (3yr)
    cagr = metrics.get("revenue_cagr_3yr") or 0.0
    scores["cagr"] = _clamp(cagr / 55 * 100)

    # Weighted composite
    weights = {
        "pe": 0.20, "roe": 0.20, "de": 0.15,
        "margin": 0.20, "promoter": 0.10, "cagr": 0.15
    }
    composite = sum(scores[k] * weights[k] for k in weights)

    return {
        "individual": {k: round(v, 1) for k, v in scores.items()},
        "composite": round(composite),
    }


# ──────────────────────────────────────────────────────────────
#  yfinance helpers
# ──────────────────────────────────────────────────────────────

def _safe_float(val, fallback: float | None = None) -> float | None:
    """Convert yfinance field to float, returning fallback on None/NaN."""
    if val is None:
        return fallback
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except (TypeError, ValueError):
        return fallback


def fetch_ticker_data(symbol: str, yf_ticker: str) -> dict | None:
    """
    Pull fundamentals from yfinance for one NSE stock.

    yfinance fields used:
        info.trailingPE          → PE ratio
        info.returnOnEquity      → ROE (decimal, e.g. 0.31 = 31%)
        info.debtToEquity        → D/E (already a ratio)
        info.profitMargins       → Net margin (decimal)
        info.currentPrice        → Live price
        info.52WeekChange        → Price change %
        info.marketCap           → Market cap in INR (for .NS tickers)

    Revenue CAGR and promoter holding require Screener.in scraper
    (fetch_screener.py). Here we set sensible defaults and let the
    screener script overwrite them in a nightly run.
    """
    log.info(f"Fetching {symbol} ({yf_ticker}) …")
    try:
        ticker = yf.Ticker(yf_ticker)
        info   = ticker.info
    except Exception as exc:
        log.error(f"  yfinance error for {symbol}: {exc}")
        return None

    if not info or info.get("regularMarketPrice") is None:
        log.warning(f"  No data returned for {symbol} — skipping.")
        return None

    # yfinance returns ROE as a decimal fraction (0.31 → 31%)
    roe_raw = _safe_float(info.get("returnOnEquity"))
    roe_pct = round(roe_raw * 100, 2) if roe_raw is not None else None

    margin_raw = _safe_float(info.get("profitMargins"))
    margin_pct = round(margin_raw * 100, 2) if margin_raw is not None else None

    price_change_raw = _safe_float(info.get("52WeekChange"))
    # Use regularMarketChangePercent for intraday % change; fall back to 52w change
    intraday_chg = _safe_float(info.get("regularMarketChangePercent"))
    if intraday_chg is not None:
        intraday_chg = round(intraday_chg * 100, 4)  # some versions return decimal

    price = (
        _safe_float(info.get("currentPrice"))
        or _safe_float(info.get("regularMarketPrice"))
    )

    market_cap_raw = _safe_float(info.get("marketCap"))
    market_cap_cr  = round(market_cap_raw / 1e7) if market_cap_raw else None  # ₹ → crores

    return {
        "pe_ratio":         _safe_float(info.get("trailingPE")),
        "roe":              roe_pct,
        "debt_equity":      _safe_float(info.get("debtToEquity")),
        "net_margin":       margin_pct,
        "price":            price,
        "price_change_pct": intraday_chg,
        "market_cap":       market_cap_cr,
        # Filled in by fetch_screener.py later:
        "promoter_holding": None,
        "revenue_cagr_3yr": None,
    }


# ──────────────────────────────────────────────────────────────
#  Supabase upsert
# ──────────────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment / .env"
        )
    return create_client(url, key)


def upsert_stock(client: Client, symbol: str, meta: dict, raw: dict, score_result: dict) -> None:
    """
    Upsert one row into the stocks table.
    Only sets composite_score if all 6 metrics are available (non-None).

    Handles Supabase PGRST204 schema-cache errors automatically:
    - If PostgREST hasn't reloaded after your schema migration, some columns
      temporarily appear "missing". The fix is:
        Supabase dashboard → Settings → API → "Reload schema cache"
      OR:  run `NOTIFY pgrst, 'reload schema';` in the SQL editor.
    - As a fallback this function retries once with only the core columns
      that were present in the original schema, so you always get a partial
      write rather than a total failure.
    """
    metrics = {k: raw.get(k) for k in ("pe_ratio","roe","debt_equity","net_margin","promoter_holding","revenue_cagr_3yr")}
    all_available = all(v is not None for v in metrics.values())

    full_row = {
        "symbol":            symbol,
        "name":              meta["name"],
        "sector":            meta["sector"],
        "market_cap":        raw.get("market_cap"),
        "pe_ratio":          raw.get("pe_ratio"),
        "roe":               raw.get("roe"),
        "debt_equity":       raw.get("debt_equity"),
        "net_margin":        raw.get("net_margin"),
        "promoter_holding":  raw.get("promoter_holding"),
        "revenue_cagr_3yr":  raw.get("revenue_cagr_3yr"),
        "price":             raw.get("price"),
        "price_change_pct":  raw.get("price_change_pct"),
        "composite_score":   score_result["composite"] if all_available else None,
        "last_updated":      datetime.now(timezone.utc).isoformat(),
    }

    # Remove None values — avoids overwriting existing data with null
    row_clean = {k: v for k, v in full_row.items() if v is not None}
    row_clean["symbol"] = symbol  # always include PK

    score_str = str(score_result["composite"]) if all_available else "pending screener"

    try:
        client.table("stocks").upsert(row_clean, on_conflict="symbol").execute()
        log.info(f"  ✓  {symbol:12s}  price=₹{raw.get('price','?')}  score={score_str}")

    except Exception as exc:
        err_str = str(exc)

        # PGRST204 = PostgREST schema cache is stale — column exists in DB
        # but PostgREST hasn't reloaded yet.
        if "PGRST204" in err_str or "schema cache" in err_str.lower():
            log.warning(
                f"  ⚠  Schema cache miss for {symbol}. "
                "Fix: Supabase dashboard → Settings → API → 'Reload schema cache' "
                "OR run `NOTIFY pgrst, 'reload schema';` in the SQL editor. "
                "Retrying with core columns only…"
            )
            # Fallback: only the columns that definitely exist after a fresh migration
            core_columns = {"symbol", "name", "sector", "pe_ratio", "roe",
                            "debt_equity", "net_margin", "price", "price_change_pct",
                            "composite_score", "last_updated"}
            row_core = {k: v for k, v in row_clean.items() if k in core_columns}
            try:
                client.table("stocks").upsert(row_core, on_conflict="symbol").execute()
                log.info(
                    f"  ✓  {symbol:12s}  (core columns only — reload schema cache to fix)  "
                    f"price=₹{raw.get('price','?')}  score={score_str}"
                )
            except Exception as exc2:
                log.error(f"  ✗  Fallback upsert also failed for {symbol}: {exc2}")
        else:
            log.error(f"  ✗  Supabase upsert failed for {symbol}: {exc}")


# ──────────────────────────────────────────────────────────────
#  Main entry point
# ──────────────────────────────────────────────────────────────

def run(symbols: list[str] | None = None) -> None:
    """
    Fetch and upsert fundamentals for every symbol in WATCHLIST
    (or the subset passed via --symbols).
    """
    target = {
        sym: meta
        for sym, meta in WATCHLIST.items()
        if (symbols is None or sym in symbols)
    }

    if not target:
        log.warning("No matching symbols found. Check --symbols argument.")
        return

    log.info(f"Starting pipeline for {len(target)} stock(s): {list(target.keys())}")
    client = get_supabase_client()
    success, failed = 0, 0

    for symbol, meta in target.items():
        raw = fetch_ticker_data(symbol, meta["yf"])
        if raw is None:
            failed += 1
            continue

        # Merge raw data with metrics dict for scoring
        # Revenue CAGR + promoter will be None until fetch_screener.py runs —
        # pass 0.0 as safe defaults so score() doesn't crash, but we won't
        # store composite_score until both fields are populated.
        metrics_for_scoring = {
            "pe_ratio":         raw.get("pe_ratio") or 0.0,
            "roe":              raw.get("roe") or 0.0,
            "debt_equity":      raw.get("debt_equity") or 0.0,
            "net_margin":       raw.get("net_margin") or 0.0,
            "promoter_holding": raw.get("promoter_holding") or 0.0,
            "revenue_cagr_3yr": raw.get("revenue_cagr_3yr") or 0.0,
        }
        score_result = score_stock(metrics_for_scoring, meta["sector"])

        upsert_stock(client, symbol, meta, raw, score_result)
        success += 1

    log.info(f"\nDone — {success} succeeded, {failed} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StockSense yfinance pipeline")
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="NSE symbols to fetch (default: all in WATCHLIST)",
    )
    args = parser.parse_args()
    run(symbols=args.symbols)