import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

TOKEN = os.getenv("NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}

# Example symbols
SYMBOLS = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "SENSEX": "BSE_INDEX|SENSEX",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "INFY": "NSE_EQ|INE009A01021",
    "RELIANCE": "NSE_EQ|INE002A01018",
}

def fetch_quote(symbol, instrument_key):
    url = "https://api.upstox.com/v2/market-quote/quotes"

    params = {
        "instrument_key": instrument_key
    }

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if "data" not in data:
        print("API Error:", data)
        return

    quotes = data["data"]

    # Take first returned object dynamically
    quote = list(quotes.values())[0]

    price = quote.get("last_price", 0)
    change = quote.get("net_change", 0)

    supabase.table("live_prices").upsert({
        "symbol": symbol,
        "price": price,
        "change_pct": change
    }).execute()

    print(f"✅ {symbol}: ₹{price} ({change})")

def run():
    while True:
        for symbol, key in SYMBOLS.items():
            try:
                fetch_quote(symbol, key)
            except Exception as e:
                print(symbol, e)

        time.sleep(5)   # change to 2 if needed


if __name__ == "__main__":
    run()