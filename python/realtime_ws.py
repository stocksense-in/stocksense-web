"""
realtime_ws.py
==============
Upstox WebSocket se real-time prices — Supabase mein update karta hai.
Upstox API already connected hai tumhara.

Run karo:
    python realtime_ws.py
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import websockets
import requests

def _load_env():
    search = Path(__file__).resolve().parent
    for _ in range(4):
        for name in (".env.local", ".env"):
            if (search / name).exists():
                load_dotenv(search / name, override=True)
                return
        search = search.parent
    load_dotenv()

_load_env()

sb = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL", ""),
    os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY", "")
)

UPSTOX_TOKEN = os.getenv("NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN", "")

# NSE instrument keys (Upstox format)
INSTRUMENTS = [
    "NSE_EQ|INE009A01021",   # INFY
    "NSE_EQ|INE040A01034",   # HDFCBANK
    "NSE_EQ|INE028A01039",   # TATAMOTORS
    "NSE_EQ|INE758T01015",   # ZOMATO
    "NSE_EQ|INE002A01018",   # RELIANCE
    "NSE_INDEX|Nifty 50",    # NIFTY50
    "NSE_INDEX|Nifty Bank",  # BANKNIFTY
]

# Symbol mapping — instrument key → tumhara symbol name
SYMBOL_MAP = {
    "INE009A01021": "INFY",
    "INE040A01034": "HDFCBANK",
    "INE028A01039": "TATAMOTORS",
    "INE758T01015": "ZOMATO",
    "INE002A01018": "RELIANCE",
    "Nifty 50":     "NIFTY50",
    "Nifty Bank":   "BANKNIFTY",
}

# Throttle — same symbol ko 3 sec mein ek baar hi update karo
last_update: dict[str, float] = {}
THROTTLE_SEC = 3


def get_ws_url() -> str:
    """Upstox se WebSocket URL lo."""
    headers = {
        "Authorization": f"Bearer {UPSTOX_TOKEN}",
        "Accept": "application/json",
    }
    resp = requests.get(
        "https://api.upstox.com/v2/feed/market-data-feed/authorize",
        headers=headers, timeout=10
    )
    print("Status:", resp.status_code)
    print("Response:", resp.json())     
    return resp.json()["data"]["authorizedRedirectUri"]


async def connect():
    ws_url = get_ws_url()
    print(f"WebSocket connecting...")

    async with websockets.connect(ws_url) as ws:
        # Subscribe karo
        sub_msg = {
            "guid":        "stocksense-feed",
            "method":      "sub",
            "data": {
                "mode":            "full",
                "instrumentKeys":  INSTRUMENTS,
            }
        }
        await ws.send(json.dumps(sub_msg))
        print(f"Subscribed to {len(INSTRUMENTS)} instruments\n")

        async for message in ws:
            try:
                data = json.loads(message)
                feeds = data.get("feeds", {})

                rows = []
                now = datetime.now(timezone.utc)

                for instrument_key, feed_data in feeds.items():
                    # Last traded price nikalo
                    ltp = (feed_data.get("ff", {})
                                    .get("marketFF", {})
                                    .get("ltpc", {})
                                    .get("ltp"))

                    close = (feed_data.get("ff", {})
                                      .get("marketFF", {})
                                      .get("ltpc", {})
                                      .get("cp"))  # previous close

                    if ltp is None:
                        continue

                    # Symbol map karo
                    key = instrument_key.split("|")[-1]
                    symbol = SYMBOL_MAP.get(key)
                    if not symbol:
                        continue

                    # Throttle check
                    import time
                    now_ts = time.time()
                    if now_ts - last_update.get(symbol, 0) < THROTTLE_SEC:
                        continue
                    last_update[symbol] = now_ts

                    change_pct = 0.0
                    if close and close > 0:
                        change_pct = round((ltp - close) / close * 100, 2)

                    print(f"  {symbol:<12} ₹{ltp:>10.2f}  "
                          f"({'+'if change_pct>=0 else ''}{change_pct:.2f}%)")

                    rows.append({
                        "symbol":     symbol,
                        "price":      round(ltp, 2),
                        "change_pct": change_pct,
                        "updated_at": now.isoformat(),
                    })

                # Supabase update
                if rows:
                    sb.table("live_prices").upsert(rows).execute()

            except json.JSONDecodeError:
                pass  # Binary message — ignore
            except Exception as e:
                print(f"Error: {e}")


# Reconnect logic — connection toot jaaye toh dobara connect karo
async def main():
    while True:
        try:
            await connect()
        except Exception as e:
            print(f"Connection lost: {e} — 5 sec mein reconnect...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    print("StockSense Real-time Feed — Ctrl+C se band karo\n")
    asyncio.run(main())