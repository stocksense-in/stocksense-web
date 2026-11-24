"""
Lake prices job — copies the `live_prices` table from Supabase into the local data
lake as clean/prices/date=<today, IST>/part-0.parquet. `live_prices` only holds the
latest price per symbol, so one run a day builds a daily history. Running it again
the same day replaces that day.

    python -m stocksense lake-prices
    python -m stocksense lake-query "select date, count(*) from prices group by date"
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from ..lake import Lake
from ..log import get_logger

log = get_logger(__name__)

IST = ZoneInfo("Asia/Kolkata")
DATASET = "prices"


def to_frame(rows: list[dict], snapshot_at: datetime) -> pd.DataFrame:
    """Typed DataFrame of live_prices rows, stamped with when the copy was taken."""
    df = pd.DataFrame(rows, columns=["symbol", "price", "change_pct", "updated_at"])
    return df.assign(
        symbol=df["symbol"].astype("string"),
        price=pd.to_numeric(df["price"], errors="coerce").astype("float64"),
        change_pct=pd.to_numeric(df["change_pct"], errors="coerce").astype("float64"),
        updated_at=pd.to_datetime(df["updated_at"], utc=True, errors="coerce"),
        snapshot_at=pd.Timestamp(snapshot_at).tz_convert("UTC"),
    )


def run(lake: Lake | None = None, rows: list[dict] | None = None, now: datetime | None = None) -> list[Path]:
    """Tests pass `lake`, `rows` and `now`; in production all three come from the environment."""
    lake = lake or Lake.from_settings()
    if rows is None:
        from ..db import fetch_all

        rows = fetch_all("live_prices", "symbol,price,change_pct,updated_at")
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(IST).date()

    written = lake.write_parquet(to_frame(rows, now), DATASET, day=day)
    log.info(f"Saved {len(rows)} live prices for {day} to {lake.clean / DATASET}")
    return written


def query(sql: str, lake: Lake | None = None) -> None:
    """Print the result of a SQL query against the lake catalogue."""
    lake = lake or Lake.from_settings()
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(lake.query(sql).to_string(index=False))
