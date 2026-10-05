"""
Scheduler — runs the jobs on a market-hours timetable (IST). Leave it running in a terminal.

    08:45  check the Upstox token (prints a reminder if it has expired)
    09:15–15:30, every 5 min  prices (Yahoo, or Upstox if a token is valid)
    16:00  fundamentals for every stock
    18:00  ownership + revenue growth for every stock

    python -m stocksense scheduler
"""

from __future__ import annotations

import time
from datetime import datetime, time as clock
from zoneinfo import ZoneInfo

import schedule

from ..db import Store
from ..log import get_logger
from ..sources import upstox
from . import fundamentals, ownership, prices, upstox_login

log = get_logger(__name__)
IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN, MARKET_CLOSE = clock(9, 15), clock(15, 30)


def market_is_open() -> bool:
    now = datetime.now(IST)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


def _safely(job, *args, **kwargs):
    def wrapped():
        try:
            job(*args, **kwargs)
        except Exception:
            log.exception(f"{job.__module__} failed")

    return wrapped


def _prices(store: Store):
    if not market_is_open():
        return
    age = upstox.token_age_hours()
    source = "upstox" if age is not None and age < upstox.TOKEN_MAX_AGE_HOURS else "yahoo"
    prices.run(store, source=source)


def _ist(hhmm: str) -> str:
    """schedule uses local time; convert an IST HH:MM to this machine's clock."""
    h, m = map(int, hhmm.split(":"))
    ist = datetime.now(IST).replace(hour=h, minute=m, second=0, microsecond=0)
    return ist.astimezone().strftime("%H:%M")


def run(store: Store) -> None:
    schedule.every().day.at(_ist("08:45")).do(_safely(upstox_login.status))
    schedule.every(5).minutes.do(_safely(_prices, store))
    schedule.every().day.at(_ist("16:00")).do(_safely(fundamentals.run, store))
    schedule.every().day.at(_ist("18:00")).do(_safely(ownership.run, store))

    log.info("Scheduler running — Ctrl+C to stop.")
    for job in schedule.get_jobs():
        log.info(f"  {job}")
    _safely(_prices, store)()
    try:
        while True:
            schedule.run_pending()
            time.sleep(15)
    except KeyboardInterrupt:
        log.info("Stopped.")
