import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # for pdf_fixture

from stocksense.market import MarketData


def row(symbol, sector="it", cap=50_000, price=100.0, chg=1.0, score=60, **metrics):
    return {
        "symbol": symbol, "name": f"{symbol} Limited", "sector": sector, "market_cap": cap,
        "price": price, "price_change_pct": chg, "composite_score": score,
        "pe_ratio": metrics.get("pe", 20), "roe": metrics.get("roe", 18), "debt_equity": metrics.get("de", 0.3),
        "net_margin": metrics.get("margin", 15), "promoter_holding": metrics.get("promoter", 50),
        "revenue_cagr_3yr": metrics.get("cagr", 12), "last_updated": "2026-10-14T00:00:00",
    }


ROWS = [
    row("TCS", "it", cap=800_000, price=2100, chg=1.9, score=70, pe=15, roe=47, de=0.1),
    row("INFY", "it", cap=420_000, price=1020, chg=-1.4, score=57, pe=14, roe=32),
    row("WIPRO", "it", cap=250_000, price=250, chg=0.0, score=55),
    row("HDFCBANK", "bank", cap=1_080_000, price=705, chg=-2.3, score=51, de=None, roe=14),
    row("SBIN", "bank", cap=900_000, price=950, chg=0.8, score=60, de=None),
    row("ICICIBANK", "bank", cap=950_000, price=1310, chg=0.5, score=62, de=None),
    row("TINYCO", "it", cap=500, price=12, chg=19.0, score=40),  # micro-cap: never a "mover"
    row("NOPRICE", "fmcg", price=None, score=None),
    # Delisted months ago: its last reading was a crash, which must not show up as a "faller".
    {**row("GONE", "energy", cap=26_000, price=383, chg=-22.1, score=50), "last_updated": "2026-04-27T10:00:00"},
]
PRICES = [
    {"symbol": "NIFTY50", "price": 22721.95, "change_pct": 1.6, "updated_at": "2026-10-14T01:00:00"},
    {"symbol": "TCS", "price": 2114.4, "change_pct": 2.0, "updated_at": "2026-10-14T01:00:00"},
]


@pytest.fixture
def market():
    return MarketData(rows=ROWS, price_rows=PRICES)
