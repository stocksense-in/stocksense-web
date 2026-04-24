
"""
scheduler.py
============
Prices fetch karta hai + har subah token refresh check karta hai.

Run karo:
    python scheduler.py
"""

import schedule
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PYTHON     = sys.executable

MARKET_OPEN  = (9, 15)
MARKET_CLOSE = (15, 30)


def is_market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    h, m = now.hour, now.minute
    return (h, m) >= MARKET_OPEN and (h, m) <= MARKET_CLOSE


def run_script(script_name: str, args: list[str] = []):
    script = SCRIPT_DIR / script_name
    result = subprocess.run(
        [PYTHON, str(script)] + args,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=120
    )
    for line in result.stdout.splitlines():
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:300]}")


def fetch_prices():
    if not is_market_open():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Market closed — skip")
        return
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching prices...")
    run_script("fetch_live_prices.py", [
        "--symbols", "INFY", "HDFCBANK", "TATAMOTORS", "ZOMATO", "RELIANCE"
    ])


def check_token():
    """Har subah 8:45 AM — token valid hai ya nahi check karo."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Token check...")
    run_script("upstox_auth.py", ["--refresh"])


# ── Schedule ──────────────────────────────────────────────

# Prices — har 5 minute
schedule.every(5).minutes.do(fetch_prices)

# Token check — har subah 8:45 AM (market open se pehle)
schedule.every().day.at("08:45").do(check_token)

# Market open/close pe ek baar
schedule.every().day.at("09:15").do(fetch_prices)
schedule.every().day.at("15:30").do(fetch_prices)

print("=" * 50)
print("StockSense Scheduler")
print("=" * 50)
print(f"Prices: har 5 min (market hours mein)")
print(f"Token:  check har subah 8:45 AM")
print(f"Ctrl+C se band karo\n")

# Turant ek baar run
fetch_prices()

while True:
    schedule.run_pending()
    time.sleep(30)