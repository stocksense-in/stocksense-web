import os
import requests
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_nifty_price():
    url = "https://api.upstox.com/v2/market-quote/quotes"

    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    params = {
        "instrument_key": "NSE_INDEX|Nifty 50"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("❌ Error fetching data:", response.text)
        return None

    data = response.json()

    try:
        quote = data["data"]["NSE_INDEX|Nifty 50"]

        price = quote["last_price"]
        change = quote["net_change"]

        prev_close = price - change
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

        print(f"📈 NIFTY 50: ₹{price:.2f} ({change_pct:.2f}%)")

        return price, change_pct

    except Exception as e:
        print("❌ Parsing error:", e)
        return None


def store_in_supabase(price, change_pct):
    try:
        data = {
            "symbol": "NIFTY50",
            "price": price,
            "change_pct": change_pct
        }

        supabase.table("live_prices").upsert(data).execute()

        print(f"✅ Stored Nifty: {price}")

    except Exception as e:
        print("❌ Supabase error:", e)


if __name__ == "__main__":
    result = fetch_nifty_price()

    if result:
        price, change_pct = result
        store_in_supabase(price, change_pct)