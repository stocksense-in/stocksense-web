import yfinance as yf
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
sb = create_client(
    os.getenv('SUPABASE_URL', os.getenv('NEXT_PUBLIC_SUPABASE_URL')),
    os.getenv('SUPABASE_KEY', os.getenv('NEXT_PUBLIC_SUPABASE_SERVICE_KEY'))
)

STOCKS = [
  {'symbol': 'INFY',       'nse_yahoo': 'INFY.NS',       'name': 'Infosys Ltd',      'sector': 'it'},
  {'symbol': 'HDFCBANK',   'nse_yahoo': 'HDFCBANK.NS',   'name': 'HDFC Bank Ltd',    'sector': 'bank'},
  {'symbol': 'TATAMOTORS', 'nse_yahoo': 'TATAMOTORS.NS', 'name': 'Tata Motors Ltd',  'sector': 'auto'},
  {'symbol': 'ZOMATO',     'nse_yahoo': 'ZOMATO.NS',     'name': 'Zomato Ltd',       'sector': 'newage'},
  {'symbol': 'RELIANCE',   'nse_yahoo': 'RELIANCE.NS',   'name': 'Reliance Industries', 'sector': 'energy'},
]

def score_stock(pe, roe, de, margin, promoter, cagr, sector):
    def cap(v): return max(0, min(100, v))

    if sector == 'newage':
        pe_score = 40
    elif sector == 'bank':
        pe_score = cap(100 - (pe - 8) / 30 * 100) if pe else 50
    else:
        pe_score = cap(100 - (pe - 8) / 42 * 100) if pe else 50

    roe_score      = cap(roe / 50 * 100)       if roe      else 0
    de_score       = cap(100 - (de / 3.5)*100) if de       else 80
    margin_score   = cap(margin / 38 * 100)    if margin   else 0
    promoter_score = cap(promoter / 80 * 100)  if promoter else 50
    cagr_score     = cap(cagr / 55 * 100)      if cagr     else 0

    composite = (
        pe_score      * 0.20 +
        roe_score     * 0.20 +
        de_score      * 0.15 +
        margin_score  * 0.20 +
        promoter_score* 0.10 +
        cagr_score    * 0.15
    )
    return round(composite)

for stock in STOCKS:
    print(f"Fetching {stock['symbol']}...")
    try:
        ticker = yf.Ticker(stock['nse_yahoo'])
        info = ticker.info

        pe       = info.get('trailingPE')
        roe      = round(info.get('returnOnEquity', 0) * 100, 1) if info.get('returnOnEquity') else None
        de       = info.get('debtToEquity')
        de       = round(de / 100, 2) if de else None
        margin   = round(info.get('profitMargins', 0) * 100, 1) if info.get('profitMargins') else None
        promoter = None  # yfinance does not have Indian promoter data — fill manually
        cagr     = None  # yfinance does not have 3yr CAGR directly — fill manually

        score = score_stock(pe, roe, de, margin, promoter, cagr, stock['sector'])

        row = {
            'symbol':            stock['symbol'],
            'name':              stock['name'],
            'sector':            stock['sector'],
            'pe_ratio':          round(pe, 1) if pe else None,
            'roe':               roe,
            'debt_equity':       de,
            'net_margin':        margin,
            'promoter_holding':  promoter,
            'revenue_cagr_3yr':  cagr,
            'composite_score':   score,
        }

        sb.table('stocks').upsert(row).execute()
        print(f"  Stored {stock['symbol']}: PE={pe}, ROE={roe}%, Score={score}")

    except Exception as e:
        print(f"  Error for {stock['symbol']}: {e}")

print("Done. All stocks stored in Supabase.")
