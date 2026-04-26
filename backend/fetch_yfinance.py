"""
StockSense — fetch_yfinance.py
==============================
Fetches live price + fundamental data for ALL NSE-listed equity stocks
using yfinance, scores each using the StockSense algorithm, and upserts
results into Supabase.

The full NSE symbol list is loaded dynamically from nse_symbols.py
(which caches NSE's EQUITY_L.csv for 24 hours).

Usage:
    # Fetch ALL ~2000+ NSE stocks (long-running):
    python fetch_yfinance.py

    # Fetch a specific subset:
    python fetch_yfinance.py --symbols INFY TCS HDFCBANK

    # Test run — only process first N stocks:
    python fetch_yfinance.py --limit 20

    # Force refresh the NSE symbol list:
    python fetch_yfinance.py --refresh-symbols

    # Control batch size and concurrency:
    python fetch_yfinance.py --batch-size 50 --workers 5

Environment variables (.env or .env.local):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...   ← service-role key (bypasses RLS)
"""

import os
import sys
import time
import argparse
import logging
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import yfinance as yf
from supabase import create_client, Client

from nse_symbols import get_all_symbols

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Env loading ───────────────────────────────────────────────────────────────

def _load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(4):
        for name in (".env.local", ".env"):
            candidate = search / name
            if candidate.exists():
                load_dotenv(candidate, override=True)
                logging.getLogger(__name__).debug(f"Loaded {name} from {candidate}")
                return
        search = search.parent
    load_dotenv()

_load_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Sector mapping ────────────────────────────────────────────────────────────
# yfinance returns sector strings like "Technology", "Financial Services", etc.
# Map them to StockSense scoring categories.

YF_SECTOR_MAP: dict[str, str] = {
    "technology":           "it",
    "communication services": "it",
    "financial services":   "bank",
    "banks":                "bank",
    "consumer cyclical":    "auto",
    "consumer defensive":   "fmcg",
    "healthcare":           "pharma",
    "basic materials":      "materials",
    "industrials":          "industrial",
    "energy":               "energy",
    "real estate":          "realestate",
    "utilities":            "utilities",
}

BANK_SECTORS   = {"bank", "nbfc"}
NEWAGE_SECTORS = {"newage"}


def _map_sector(yf_sector: str | None) -> str:
    if not yf_sector:
        return "general"
    return YF_SECTOR_MAP.get(yf_sector.lower(), "general")


# ── Scoring algorithm ─────────────────────────────────────────────────────────

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def score_stock(metrics: dict, sector: str) -> dict:
    """
    Returns:
        {"individual": {"pe": 0-100, ...}, "composite": 0-100}
    Matches StockSense scoring algorithm (lib/scores.ts).
    """
    scores: dict[str, float] = {}

    # 1. P/E — lower is better
    pe = metrics.get("pe_ratio") or 0.0
    if sector in NEWAGE_SECTORS:
        scores["pe"] = 40.0
    elif sector in BANK_SECTORS:
        scores["pe"] = _clamp(100 - (pe - 8) / 30 * 100)
    else:
        scores["pe"] = _clamp(100 - (pe - 8) / 42 * 100)

    # 2. ROE — higher is better
    roe = metrics.get("roe") or 0.0
    scores["roe"] = _clamp(roe / 50 * 100)

    # 3. Debt/Equity — lower is better
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

    weights = {
        "pe": 0.20, "roe": 0.20, "de": 0.15,
        "margin": 0.20, "promoter": 0.10, "cagr": 0.15,
    }
    composite = sum(scores[k] * weights[k] for k in weights)

    return {
        "individual": {k: round(v, 1) for k, v in scores.items()},
        "composite":  round(composite),
    }


# ── yfinance helpers ──────────────────────────────────────────────────────────

def _safe_float(val, fallback=None):
    if val is None:
        return fallback
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except (TypeError, ValueError):
        return fallback


def _extract_from_info(symbol: str, info: dict) -> dict | None:
    """
    Build the data dict from a populated yfinance info dict.
    Returns None if no usable price is found.
    """
    price = (
        _safe_float(info.get("currentPrice"))
        or _safe_float(info.get("regularMarketPrice"))
    )
    if price is None:
        return None

    roe_raw    = _safe_float(info.get("returnOnEquity"))
    roe_pct    = round(roe_raw * 100, 2) if roe_raw is not None else None

    margin_raw = _safe_float(info.get("profitMargins"))
    margin_pct = round(margin_raw * 100, 2) if margin_raw is not None else None

    intraday = _safe_float(info.get("regularMarketChangePercent"))
    if intraday is not None:
        if abs(intraday) < 1:     # fraction → percent
            intraday = round(intraday * 100, 4)
        else:
            intraday = round(intraday, 4)

    market_cap_raw = _safe_float(info.get("marketCap"))
    market_cap_cr  = round(market_cap_raw / 1e7) if market_cap_raw else None

    yf_sector = info.get("sector") or info.get("industryDisp") or None

    return {
        "pe_ratio":         _safe_float(info.get("trailingPE")),
        "roe":              roe_pct,
        "debt_equity":      _safe_float(info.get("debtToEquity")),
        "net_margin":       margin_pct,
        "price":            price,
        "price_change_pct": intraday,
        "market_cap":       market_cap_cr,
        "yf_sector":        yf_sector,
        "promoter_holding": None,
        "revenue_cagr_3yr": None,
    }


def _price_from_history(ticker_sym: str) -> dict | None:
    """
    Last-resort fallback: use yf.download() for price + day change.
    Returns a price-only dict (fundamentals all None) or None.
    """
    try:
        import pandas as pd
        df = yf.download(ticker_sym, period="5d", progress=False, auto_adjust=True)
        if df.empty:
            return None
        closes = df["Close"].dropna()
        if closes.empty:
            return None
        price = float(closes.iloc[-1])
        change_pct = None
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            if prev:
                change_pct = round((price - prev) / prev * 100, 4)
        return {
            "pe_ratio":         None,
            "roe":              None,
            "debt_equity":      None,
            "net_margin":       None,
            "price":            round(price, 2),
            "price_change_pct": change_pct,
            "market_cap":       None,
            "yf_sector":        None,
            "promoter_holding": None,
            "revenue_cagr_3yr": None,
        }
    except Exception:
        return None


def fetch_ticker_data(symbol: str, yf_ticker: str) -> dict | None:
    """
    Pull fundamentals + live price from yfinance for one NSE stock.

    Fallback chain (maximises coverage):
      1. SYMBOL.NS  — full fundamentals via Ticker.info
      2. SYMBOL.BO  — BSE ticker, full fundamentals via Ticker.info
      3. SYMBOL.NS  — price-only via yf.download() (suspended/illiquid)
      4. SYMBOL.BO  — price-only via yf.download()
    """
    bo_ticker = symbol + ".BO"

    # ── Stage 1: .NS full info ────────────────────────────────────────────────
    try:
        info = yf.Ticker(yf_ticker).info
        if info:
            result = _extract_from_info(symbol, info)
            if result:
                return result
    except Exception:
        pass

    # ── Stage 2: .BO (BSE) full info ─────────────────────────────────────────
    try:
        info = yf.Ticker(bo_ticker).info
        if info:
            result = _extract_from_info(symbol, info)
            if result:
                log.debug(f"  {symbol}: used BSE (.BO) ticker")
                return result
    except Exception:
        pass

    # ── Stage 3: .NS price-only via download ──────────────────────────────────
    result = _price_from_history(yf_ticker)
    if result:
        log.debug(f"  {symbol}: price-only via NS download")
        return result

    # ── Stage 4: .BO price-only via download ──────────────────────────────────
    result = _price_from_history(bo_ticker)
    if result:
        log.debug(f"  {symbol}: price-only via BO download")
        return result

    return None


# ── Supabase helpers ──────────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_SERVICE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    if not url or not key:
        raise EnvironmentError(
            "Missing SUPABASE_URL / SUPABASE_SERVICE_KEY in environment / .env"
        )
    return create_client(url, key)


def upsert_stock(client: Client, symbol: str, name: str, sector: str,
                 raw: dict, score_result: dict) -> None:
    metrics = {k: raw.get(k) for k in (
        "pe_ratio", "roe", "debt_equity", "net_margin",
        "promoter_holding", "revenue_cagr_3yr",
    )}
    all_available = all(v is not None for v in metrics.values())

    full_row = {
        "symbol":           symbol,
        "name":             name,
        "sector":           sector,
        "market_cap":       raw.get("market_cap"),
        "pe_ratio":         raw.get("pe_ratio"),
        "roe":              raw.get("roe"),
        "debt_equity":      raw.get("debt_equity"),
        "net_margin":       raw.get("net_margin"),
        "promoter_holding": raw.get("promoter_holding"),
        "revenue_cagr_3yr": raw.get("revenue_cagr_3yr"),
        "price":            raw.get("price"),
        "price_change_pct": raw.get("price_change_pct"),
        "composite_score":  score_result["composite"] if all_available else None,
        "last_updated":     datetime.now(timezone.utc).isoformat(),
    }

    row_clean = {k: v for k, v in full_row.items() if v is not None}
    row_clean["symbol"] = symbol   # always include PK

    try:
        client.table("stocks").upsert(row_clean, on_conflict="symbol").execute()
    except Exception as exc:
        err_str = str(exc)
        if "PGRST204" in err_str or "schema cache" in err_str.lower():
            log.warning(f"  ⚠  Schema cache miss for {symbol} — reload schema cache in Supabase.")
            core = {"symbol", "name", "sector", "pe_ratio", "roe", "debt_equity",
                    "net_margin", "price", "price_change_pct", "composite_score", "last_updated"}
            try:
                client.table("stocks").upsert(
                    {k: v for k, v in row_clean.items() if k in core},
                    on_conflict="symbol",
                ).execute()
            except Exception as exc2:
                log.error(f"  ✗  Fallback upsert failed for {symbol}: {exc2}")
        else:
            log.error(f"  ✗  Supabase upsert failed for {symbol}: {exc}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_symbol(args_tuple) -> tuple[str, bool]:
    """Worker function for ThreadPoolExecutor — fetches + scores one stock."""
    symbol_info, client = args_tuple
    symbol    = symbol_info["symbol"]
    yf_ticker = symbol_info["yf"]
    name      = symbol_info.get("name", symbol)

    raw = fetch_ticker_data(symbol, yf_ticker)
    if raw is None:
        return symbol, False

    # Use yfinance sector if available, else fallback to nse_symbols.py default
    sector = _map_sector(raw.pop("yf_sector", None)) or symbol_info.get("sector", "general")

    metrics_for_scoring = {
        "pe_ratio":         raw.get("pe_ratio") or 0.0,
        "roe":              raw.get("roe") or 0.0,
        "debt_equity":      raw.get("debt_equity") or 0.0,
        "net_margin":       raw.get("net_margin") or 0.0,
        "promoter_holding": raw.get("promoter_holding") or 0.0,
        "revenue_cagr_3yr": raw.get("revenue_cagr_3yr") or 0.0,
    }
    score_result = score_stock(metrics_for_scoring, sector)
    upsert_stock(client, symbol, name, sector, raw, score_result)

    price = raw.get("price", "?")
    log.info(f"  ✓  {symbol:<14s}  ₹{price}  score={score_result['composite']}")
    return symbol, True


def run(
    symbols:         list[str] | None = None,
    limit:           int | None       = None,
    batch_size:      int               = 100,
    workers:         int               = 4,
    delay_between:   float             = 0.3,
    refresh_symbols: bool              = False,
) -> None:
    """
    Main entry point.

    symbols        – If given, only process these NSE symbols (overrides limit).
    limit          – Max number of stocks to process (useful for testing).
    batch_size     – How many stocks to send to ThreadPoolExecutor at once.
    workers        – Concurrent yfinance requests per batch.
    delay_between  – Seconds to sleep between batches (rate-limiting).
    refresh_symbols – Force re-download of NSE symbol list.
    """
    log.info("Loading NSE symbol list …")
    all_nse = get_all_symbols(force_refresh=refresh_symbols)

    # Filter to requested symbols if --symbols was passed
    if symbols:
        sym_set = {s.upper() for s in symbols}
        target = [s for s in all_nse if s["symbol"] in sym_set]
        # Add any explicitly requested symbols not found in NSE list
        found = {s["symbol"] for s in target}
        for sym in sym_set - found:
            log.warning(f"  Symbol {sym} not found in NSE equity list — skipping.")
    else:
        target = all_nse

    if limit:
        target = target[:limit]

    log.info(f"Processing {len(target)} stock(s) …  "
             f"[batch_size={batch_size}, workers={workers}]")

    client  = get_supabase_client()
    success = 0
    failed_symbols: list[str] = []

    # Process in batches to keep memory manageable and allow polite rate-limiting
    for batch_start in range(0, len(target), batch_size):
        batch = target[batch_start : batch_start + batch_size]
        batch_num    = batch_start // batch_size + 1
        total_batches = (len(target) + batch_size - 1) // batch_size
        log.info(f"\n── Batch {batch_num}/{total_batches} "
                 f"({batch[0]['symbol']} … {batch[-1]['symbol']}) ──")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
            futures = {
                exe.submit(process_symbol, (sym_info, client)): sym_info["symbol"]
                for sym_info in batch
            }
            for future in concurrent.futures.as_completed(futures):
                sym = futures[future]
                try:
                    returned_sym, ok = future.result()
                    if ok:
                        success += 1
                    else:
                        failed_symbols.append(returned_sym)
                except Exception as exc:
                    log.error(f"  Unhandled error for {sym}: {exc}")
                    failed_symbols.append(sym)

        if batch_start + batch_size < len(target):
            log.info(f"  Sleeping {delay_between}s before next batch …")
            time.sleep(delay_between)

    # ── Write failed symbols log ────────────────────────────────────────────────
    failed_log = Path(__file__).resolve().parent / "failed_symbols.txt"
    if failed_symbols:
        with open(failed_log, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(failed_symbols)))
        log.info(f"  {len(failed_symbols)} symbols with no data logged to: {failed_log.name}")
        log.info("  Re-run with:  python fetch_yfinance.py --symbols "
                 + " ".join(failed_symbols[:5]) + " ...  to retry just failures.")
    elif failed_log.exists():
        failed_log.unlink()   # clean up old log if everything succeeded

    log.info(f"\n{'='*50}")
    log.info(f"Done — {success} succeeded, {len(failed_symbols)} could not be fetched.")
    log.info(f"{'='*50}")



# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense yfinance pipeline — fetches ALL NSE stocks"
    )
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="Specific NSE symbols to fetch (default: all NSE equities)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Only process the first N stocks (useful for testing)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, metavar="N",
        help="Stocks per batch (default: 100)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, metavar="N",
        help="Concurrent yfinance threads per batch (default: 4)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.3, metavar="SEC",
        help="Sleep seconds between batches (default: 0.3)",
    )
    parser.add_argument(
        "--refresh-symbols", action="store_true",
        help="Force re-download of NSE equity list (ignore 24h cache)",
    )
    parser.add_argument(
        "--retry-failed", action="store_true",
        help="Retry only symbols listed in failed_symbols.txt from last run",
    )
    args = parser.parse_args()

    # --retry-failed: read symbols from the failed log and pass them in
    symbols_to_run = args.symbols
    if args.retry_failed:
        failed_log = Path(__file__).resolve().parent / "failed_symbols.txt"
        if not failed_log.exists():
            print("No failed_symbols.txt found — nothing to retry.")
        else:
            symbols_to_run = [
                line.strip()
                for line in failed_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            print(f"Retrying {len(symbols_to_run)} previously failed symbols …")

    run(
        symbols=symbols_to_run,
        limit=args.limit,
        batch_size=args.batch_size,
        workers=args.workers,
        delay_between=args.delay,
        refresh_symbols=args.refresh_symbols,
    )