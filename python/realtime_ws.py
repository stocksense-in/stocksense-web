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
from nse_symbols import get_all_symbols

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

print("Loading all NSE symbols...")
all_stocks = get_all_symbols()

INSTRUMENTS = [
    "NSE_INDEX|Nifty 50",    # NIFTY50
    "NSE_INDEX|Nifty Bank",  # BANKNIFTY
]

# Symbol mapping — instrument key (isin/name) → tumhara symbol name
SYMBOL_MAP = {
    "Nifty 50":     "NIFTY50",
    "Nifty Bank":   "BANKNIFTY",
}

for s in all_stocks:
    if s.get("isin"):
        inst_key = f"NSE_EQ|{s['isin']}"
        INSTRUMENTS.append(inst_key)
        SYMBOL_MAP[s['isin']] = s['symbol']

print(f"Loaded {len(INSTRUMENTS)} total instruments.")

# Throttle — same symbol ko 1 sec mein ek baar hi update karo
last_update: dict[str, float] = {}
THROTTLE_SEC = 1


def get_ws_url() -> str:
    """Upstox se WebSocket URL lo."""
    headers = {
        "Authorization": f"Bearer {UPSTOX_TOKEN}",
        "Accept": "application/json",
    }
    resp = requests.get(
        "https://api.upstox.com/v3/feed/market-data-feed/authorize",
        headers=headers, timeout=10
    )
    print("Status:", resp.status_code)
    data = resp.json()
    print("Auth Response:", data)     
    return data["data"]["authorizedRedirectUri"]


async def connect():
    ws_url = get_ws_url()
    print(f"WebSocket connecting...")

    async with websockets.connect(ws_url) as ws:
        # Subscribe in chunks to avoid Upstox websocket limits
        chunk_size = 100
        for i in range(0, len(INSTRUMENTS), chunk_size):
            chunk = INSTRUMENTS[i : i + chunk_size]
            sub_msg = {
                "guid":        f"stocksense-feed-{i}",
                "method":      "sub",
                "data": {
                    "mode":            "full",
                    "instrumentKeys":  chunk,
                }
            }
            await ws.send(json.dumps(sub_msg))
            await asyncio.sleep(0.1)  # small delay so we don't overwhelm

        print(f"Successfully sent subscription for {len(INSTRUMENTS)} instruments\n")

        async for message in ws:
            try:
                if isinstance(message, bytes):
                    # Upstox official protobuf decoder
                    from MarketDataFeed_pb2 import FeedResponse
                    feed_response = FeedResponse()
                    feed_response.ParseFromString(message)

                    rows = []
                    now  = datetime.now(timezone.utc)

                    import time
                    for instrument_key, feed in feed_response.feeds.items():
                        try:
                            # LTPC — Last Traded Price + Close
                            ltpc = feed.ff.market_ff.ltpc
                            ltp  = ltpc.ltp
                            cp   = ltpc.cp   # previous close

                            if not ltp:
                                continue

                            # Symbol map
                            key    = instrument_key.split("|")[-1]
                            symbol = SYMBOL_MAP.get(key)
                            if not symbol:
                                continue

                            # Throttle
                            now_ts = time.time()
                            if now_ts - last_update.get(symbol, 0) < THROTTLE_SEC:
                                continue
                            last_update[symbol] = now_ts

                            change_pct = 0.0
                            if cp and cp > 0:
                                change_pct = round((ltp - cp) / cp * 100, 2)

                            arrow = "▲" if change_pct >= 0 else "▼"
                            print(f"  {symbol:<14} ₹{ltp:>10.2f}  "
                                  f"{arrow} {change_pct:+.2f}%")

                            rows.append({
                                "symbol":     symbol,
                                "price":      round(ltp, 2),
                                "change_pct": change_pct,
                                "updated_at": now.isoformat(),
                            })

                        except Exception as e:
                            continue  # ek symbol fail ho toh baaki chalta rahe

                        # Bulk Supabase upsert
                        if rows:
                            sb.table("live_prices").upsert(rows).execute()
                            print(f"  → {len(rows)} prices updated")

                else:
                    # Text message — JSON
                    data = json.loads(message)
                    print(f"  Text msg: {data}")

            except Exception as e:
                print(f"  Error: {e}")


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