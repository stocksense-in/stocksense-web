"""
scheduler.py
============
Automatically keeps live stock prices updated in Supabase by calling
fetch_live_prices.py on a loop during NSE market hours.

NSE Market Hours: Monday–Friday, 09:15 – 15:30 IST (UTC+5:30)
Pre-open session:  09:00 – 09:15 IST

Usage:
    # Update every 5 minutes (default):
    python scheduler.py

    # Update every 1 minute (more real-time):
    python scheduler.py --interval 1

    # Run outside market hours too (24/7 mode, useful for testing):
    python scheduler.py --no-market-check

    # Only update specific symbols fast:
    python scheduler.py --interval 1 --symbols INFY TCS HDFCBANK

    # Also run fundamentals refresh once per day at market open:
    python scheduler.py --daily-fundamentals

Stop with Ctrl+C.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo          # Python 3.9+

# ── Constants ─────────────────────────────────────────────────────────────────

IST = ZoneInfo("Asia/Kolkata")

# NSE session windows (IST)
PREOPEN_START  = dtime(9,  0)
MARKET_OPEN    = dtime(9, 15)
MARKET_CLOSE   = dtime(15, 30)
AFTER_CLOSE    = dtime(15, 45)   # slight buffer after close

PYTHON = sys.executable           # same venv interpreter that's running this
SCRIPT_DIR = Path(__file__).resolve().parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def now_ist() -> datetime:
    return datetime.now(IST)


def is_market_open(dt: datetime | None = None) -> bool:
    """Return True if NSE market is currently open."""
    dt = dt or now_ist()
    if dt.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    t = dt.time()
    return MARKET_OPEN <= t < MARKET_CLOSE


def is_market_day(dt: datetime | None = None) -> bool:
    """Return True if today is a weekday (not checking holidays)."""
    dt = dt or now_ist()
    return dt.weekday() < 5


def seconds_until_market_open(dt: datetime | None = None) -> float:
    """Return seconds until next NSE market open."""
    dt = dt or now_ist()

    # Build today's open time in IST
    today_open = dt.replace(
        hour=MARKET_OPEN.hour,
        minute=MARKET_OPEN.minute,
        second=0, microsecond=0,
    )

    if dt < today_open and dt.weekday() < 5:
        return (today_open - dt).total_seconds()

    # Next weekday open
    days_ahead = 1
    next_dt = dt + timedelta(days=days_ahead)
    while next_dt.weekday() >= 5:
        days_ahead += 1
        next_dt = dt + timedelta(days=days_ahead)

    next_open = next_dt.replace(
        hour=MARKET_OPEN.hour,
        minute=MARKET_OPEN.minute,
        second=0, microsecond=0,
    )
    return (next_open - dt).total_seconds()


def fmt_duration(seconds: float) -> str:
    """Format seconds as h:mm:ss."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m:02d}m {s:02d}s"


def run_live_prices(symbols: list[str] | None = None,
                    workers: int = 8) -> int:
    """Run fetch_live_prices.py and return exit code."""
    cmd = [PYTHON, str(SCRIPT_DIR / "fetch_live_prices.py"),
           "--workers", str(workers)]
    if symbols:
        cmd += ["--symbols"] + symbols
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode


def run_fundamentals() -> int:
    """Run fetch_yfinance.py for a lightweight fundamentals refresh."""
    cmd = [PYTHON, str(SCRIPT_DIR / "fetch_yfinance.py")]
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode


def print_banner(interval: int, no_market_check: bool, symbols: list[str] | None) -> None:
    print("=" * 60)
    print("  StockSense Live Price Scheduler")
    print("=" * 60)
    print(f"  Interval          : every {interval} minute(s)")
    print(f"  Market hours only : {'NO (24/7 mode)' if no_market_check else 'YES (09:15-15:30 IST)'}")
    print(f"  Symbols           : {'ALL NSE stocks' if not symbols else ', '.join(symbols)}")
    print(f"  Started at        : {now_ist().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    print()


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_scheduler(
    interval: int = 5,
    no_market_check: bool = False,
    symbols: list[str] | None = None,
    workers: int = 8,
    daily_fundamentals: bool = False,
) -> None:
    print_banner(interval, no_market_check, symbols)

    interval_secs    = interval * 60
    last_fundamentals_date = None   # track if we've done today's fundamentals run
    run_count = 0

    try:
        while True:
            now = now_ist()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S IST")

            # ── Check market hours ────────────────────────────────────────────
            if not no_market_check and not is_market_open(now):
                wait = seconds_until_market_open(now)
                print(f"[{timestamp}]  Market closed -- sleeping {fmt_duration(wait)} until next open ...")
                # Sleep in chunks so Ctrl+C still works
                sleep_chunks(wait)
                continue

            # ── Optional: once-per-day fundamentals at market open ────────────
            if daily_fundamentals and is_market_open(now):
                today = now.date()
                if last_fundamentals_date != today and now.time() < dtime(9, 30):
                    print(f"[{timestamp}]  Running daily fundamentals refresh ...")
                    run_fundamentals()
                    last_fundamentals_date = today

            # ── Fetch live prices ─────────────────────────────────────────────
            run_count += 1
            print(f"[{timestamp}]  --- Run #{run_count} --- fetching live prices ...")
            t_start = time.monotonic()

            exit_code = run_live_prices(symbols=symbols, workers=workers)
            elapsed = time.monotonic() - t_start

            status = "[OK]" if exit_code == 0 else f"[WARN] exited {exit_code}"
            print(f"[{now_ist().strftime('%H:%M:%S IST')}]  {status}  "
                  f"(took {elapsed:.1f}s) -- next run in {interval}m\n")

            # ── Sleep until next interval ─────────────────────────────────────
            # Subtract elapsed fetch time so intervals stay accurate
            sleep_secs = max(0, interval_secs - elapsed)
            sleep_chunks(sleep_secs)

    except KeyboardInterrupt:
        print(f"\n[{now_ist().strftime('%H:%M:%S IST')}]  Scheduler stopped by user. "
              f"Total runs: {run_count}")


def sleep_chunks(total_seconds: float, chunk: float = 5.0) -> None:
    """Sleep in small chunks so Ctrl+C is responsive."""
    remaining = total_seconds
    while remaining > 0:
        time.sleep(min(chunk, remaining))
        remaining -= chunk


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockSense — automatic live price scheduler"
    )
    parser.add_argument(
        "--interval", type=int, default=5, metavar="MINUTES",
        help="How often to fetch prices in minutes (default: 5)",
    )
    parser.add_argument(
        "--no-market-check", action="store_true",
        help="Fetch prices 24/7, ignoring market hours (useful for testing)",
    )
    parser.add_argument(
        "--symbols", nargs="*", metavar="SYM",
        help="Only update these symbols (default: all NSE stocks)",
    )
    parser.add_argument(
        "--workers", type=int, default=8, metavar="N",
        help="Concurrent threads for price fetching (default: 8)",
    )
    parser.add_argument(
        "--daily-fundamentals", action="store_true",
        help="Also run fetch_yfinance.py once per day at market open",
    )
    args = parser.parse_args()

    run_scheduler(
        interval=args.interval,
        no_market_check=args.no_market_check,
        symbols=args.symbols,
        workers=args.workers,
        daily_fundamentals=args.daily_fundamentals,
    )
