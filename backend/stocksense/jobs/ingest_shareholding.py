"""
Shareholding ingest job — promoter holding by quarter and promoter pledges (M1.3).

    python -m stocksense ingest-shareholding --top 50
    python -m stocksense ingest-shareholding --all --rests 6     # every NSE equity, ~2 h
    python -m stocksense ingest-shareholding --symbols TCS ADANIENT
    python -m stocksense ingest-shareholding --top 1000 --history 20 --rests 6   # FII/DII split history

`--history N` reads the full pattern for each company's last N quarters (NSE lists about
five years), from the quarterly lists already saved: no new list requests, one XBRL file a
second, only the parsed categories kept. That turns the FII/DII/mutual fund split from
"latest quarter only" into a trend.

Two requests per company (shareholding patterns, pledge position), one a second, plus
the latest quarter's full pattern (XBRL, ~1 MB) once per quarter for the FII/DII split —
only the parsed categories are kept (raw/nse_shp_categories/<quarter>/<SYMBOL>.json). Raw
responses are saved per fetch day (raw/nse_shareholding/<day>/<SYMBOL>.json), so a
company already fetched today is skipped and pledge snapshots accumulate into history.
Then two clean tables are rebuilt from every raw file:

  • shareholding — one row per company and quarter: promoter %, public %, employee trusts %,
                   and for quarters whose full pattern was read, FII %, DII %, mutual funds %,
                   insurers %, small retail %, government %
  • pledges      — one row per company and fetch day: promoter shares pledged, as % of
                   the promoters' holding and of all shares
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import date

import pandas as pd

from ..lake import Lake
from ..log import get_logger
from ..sources import nse_shareholding
from .ingest_results import Breaker, NseUnavailable

log = get_logger(__name__)

SOURCE = "nse_shareholding"
CATEGORIES = "nse_shp_categories"
PAUSE_SECONDS = 1.0
REST_SECONDS = 15 * 60  # NSE throttles long runs for a while, then answers again


def _fetch_company(c, lake: Lake, symbol: str, today: date, pause: float, breaker: Breaker) -> bool:
    path = lake.raw_dir(SOURCE, today) / f"{symbol}.json"
    if path.exists():  # fetched today already; still pick up the pattern split if it's missing
        try:
            master = json.loads(path.read_text(encoding="utf-8")).get("master") or []
        except (OSError, ValueError):
            master = []
        _fetch_categories(c, lake, symbol, master, pause, breaker)
        return False
    doc = {"symbol": symbol, "fetched": today.isoformat()}
    for key, fetch in (("master", nse_shareholding.fetch_master), ("pledges", nse_shareholding.fetch_pledges)):
        try:
            doc[key] = fetch(c, symbol)
            breaker.ok()
        except Exception as exc:  # a hiccup: save what we have; the next day's run retries
            breaker.fail(f"{SOURCE}: {symbol} {key}", exc)
        time.sleep(pause)
    if "master" not in doc and "pledges" not in doc:
        return False
    path.write_text(json.dumps(doc), encoding="utf-8")
    _fetch_categories(c, lake, symbol, doc.get("master") or [], pause, breaker)
    return True


def _save_categories(c, lake: Lake, symbol: str, row: dict, pause: float, breaker: Breaker) -> bool:
    """One quarter's full pattern (FII/DII split), unless already saved. True if fetched."""
    path = lake.raw_dir(CATEGORIES, row["quarter_end"]) / f"{symbol}.json"
    if path.exists():
        return False
    try:
        cats = nse_shareholding.categories(nse_shareholding.fetch_xbrl(c, row["xbrl"]))
        breaker.ok()
    except Exception as exc:
        breaker.fail(f"{CATEGORIES}: {symbol} {row['quarter_end']}", exc)
        return False
    finally:
        time.sleep(pause)
    path.write_text(json.dumps({"symbol": symbol, "quarter_end": row["quarter_end"].isoformat(),
                                "xbrl": row["xbrl"], **cats}), encoding="utf-8")
    return True


def _fetch_categories(c, lake: Lake, symbol: str, master: list[dict], pause: float, breaker: Breaker,
                      quarters: int = 1) -> int:
    """The FII/DII split for the last `quarters` quarters (the latest only, by default)."""
    rows = [r for r in nse_shareholding.holdings(master) if r.get("xbrl")]
    return sum(_save_categories(c, lake, symbol, r, pause, breaker) for r in rows[-quarters:])


def latest_master(lake: Lake, symbol: str) -> list[dict] | None:
    """The most recently saved quarterly list for a company, if any."""
    files = sorted((lake.raw / SOURCE).glob(f"*/{symbol}.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8")).get("master")


def fetch_history(lake: Lake, symbols: Iterable[str], quarters: int, pause: float = PAUSE_SECONDS,
                  rests: int = 0, rest_seconds: float = REST_SECONDS) -> int:
    """Full patterns for each company's last `quarters` quarters, from its saved list. Returns files fetched."""
    symbols = list(symbols)
    fetched, position = 0, 0
    while True:
        breaker = Breaker()
        try:
            with nse_shareholding.client() as c:
                while position < len(symbols):
                    master = latest_master(lake, symbols[position])
                    if master:
                        fetched += _fetch_categories(c, lake, symbols[position], master, pause, breaker, quarters)
                    position += 1
                    if position % 50 == 0:
                        log.info(f"{CATEGORIES}: {position} of {len(symbols)} companies, {fetched} patterns read")
            return fetched
        except NseUnavailable as exc:
            if rests <= 0:
                log.warning(f"{CATEGORIES}: stopping — NSE is not responding ({exc}); a later run resumes")
                return fetched
            rests -= 1
            log.warning(f"{CATEGORIES}: NSE is not responding ({exc}); resting {rest_seconds / 60:.0f} min ({rests} left)")
            time.sleep(rest_seconds)


def fetch(lake: Lake, symbols: Iterable[str], today: date | None = None, pause: float = PAUSE_SECONDS,
          rests: int = 0, rest_seconds: float = REST_SECONDS) -> int:
    """Save today's responses for companies not yet fetched today. Returns how many were saved."""
    today = today or date.today()
    symbols = list(symbols)
    saved, position = 0, 0
    while True:
        breaker = Breaker()
        try:
            with nse_shareholding.client() as c:
                while position < len(symbols):
                    saved += _fetch_company(c, lake, symbols[position], today, pause, breaker)
                    position += 1
                    if position % 100 == 0:
                        log.info(f"{SOURCE}: {position} of {len(symbols)} companies")
            return saved
        except NseUnavailable as exc:
            if rests <= 0:
                log.warning(f"{SOURCE}: stopping — NSE is not responding ({exc}); a later run resumes")
                return saved
            rests -= 1
            log.warning(f"{SOURCE}: NSE is not responding ({exc}); resting {rest_seconds / 60:.0f} min ({rests} left)")
            time.sleep(rest_seconds)


def build(lake: Lake) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild clean/shareholding and clean/pledges from every raw file."""
    holdings, pledges = [], []
    for path in sorted((lake.raw / SOURCE).glob("*/*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning(f"{SOURCE}: could not read {path}: {exc}")
            continue
        fetched = date.fromisoformat(doc["fetched"])
        holdings.extend({**r, "fetched": fetched} for r in nse_shareholding.holdings(doc.get("master") or []))
        p = nse_shareholding.pledge(doc.get("pledges") or [], doc["symbol"], fetched)
        if p:
            pledges.append(p)
    h, p = pd.DataFrame(holdings), pd.DataFrame(pledges)
    if len(h):
        # A later fetch carries any revision, so the newest fetch of a quarter wins.
        h = (h.sort_values(["symbol", "quarter_end", "fetched"]).drop_duplicates(["symbol", "quarter_end"], keep="last")
              .drop(columns="fetched").reset_index(drop=True))
        cats = []
        for path in sorted((lake.raw / CATEGORIES).glob("*/*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            doc.pop("xbrl", None)
            doc["quarter_end"] = date.fromisoformat(doc["quarter_end"])
            values = {k: v for k, v in doc.items() if k not in ("symbol", "quarter_end") and v is not None}
            if values and max(values.values()) > 100:  # saved before the unit fix: percentages ×100
                doc.update({k: round(v / 100, 2) for k, v in values.items()})
            cats.append(doc)
        if cats:
            h = h.merge(pd.DataFrame(cats).drop_duplicates(["symbol", "quarter_end"], keep="last"),
                        on=["symbol", "quarter_end"], how="left")
        lake.write_table(h, "shareholding")
    if len(p):
        p = p.sort_values(["symbol", "fetched"]).drop_duplicates(["symbol", "fetched"], keep="last").reset_index(drop=True)
        lake.write_table(p, "pledges")
    log.info(f"shareholding: {len(h)} company-quarters for {h['symbol'].nunique() if len(h) else 0} companies; "
             f"pledges: {len(p)} snapshots")
    return h, p


def run(symbols: list[str] | None = None, top: int | None = 50, everything: bool = False,
        lake: Lake | None = None, rests: int = 0, history: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`history`: instead of today's lists, read the last N quarters' full patterns from the saved
    lists (largest companies first when `top` picks them, as top_symbols orders by size)."""
    lake = lake or Lake.from_settings()
    if symbols:
        targets = [s.upper() for s in symbols]
    elif everything:
        from ..symbols import select

        targets = [s.symbol for s in select()]
    else:
        from .ingest_results import top_symbols

        targets = top_symbols(top or 50)
    log.info(f"{SOURCE}: {len(targets)} companies" + (f", last {history} quarters' full patterns" if history else ""))
    if history:
        fetch_history(lake, targets, history, rests=rests)
    else:
        fetch(lake, targets, rests=rests)
    return build(lake)
