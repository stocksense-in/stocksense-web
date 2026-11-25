"""
Results ingest job — companies' quarterly P&L history from NSE filings (M1.2).

    python -m stocksense ingest-results                    # the 20 largest companies
    python -m stocksense ingest-results --top 100
    python -m stocksense ingest-results --symbols TCS INFY

For each company: list its quarterly filings, keep one per quarter and basis (standalone
and consolidated — many companies filed consolidated figures only some quarters, so a
year's sum must not mix the two), and fetch the figures — one request a second. Each
filing is saved raw (raw/nse_results/<quarter end>/<SYMBOL>_<seq>.json, filing metadata
+ figures), so reruns only fetch what's new. Then clean/financial_results is rebuilt from
all raw files: one row per company, quarter and basis, amounts in ₹ crore.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable

import pandas as pd

from ..lake import Lake
from ..log import get_logger
from ..sources import nse_results

log = get_logger(__name__)

SOURCE = "nse_results"
DATASET = "financial_results"
PAUSE_SECONDS = 1.0


def _seq(f: dict) -> int:
    try:
        return int(f.get("seqNumber") or 0)
    except ValueError:
        return 0


def quarterly(filings: list[dict]) -> list[dict]:
    """One filing per quarter and basis (the latest, if a result was refiled); quarterly, not cumulative."""
    best: dict[tuple, dict] = {}
    for f in filings:
        if (f.get("cumulative") or "Non-cumulative").lower().startswith("cumulative"):
            continue
        if not f.get("toDate"):
            continue
        key = (f["toDate"], f.get("consolidated") == "Consolidated")
        if key not in best or _seq(f) > _seq(best[key]):
            best[key] = f
    return list(best.values())


def top_symbols(n: int) -> list[str]:
    from ..market import MarketData

    stocks = sorted((s for s in MarketData().fresh_stocks() if s.market_cap), key=lambda s: s.market_cap, reverse=True)
    return [s.symbol for s in stocks[:n]]


def fetch(lake: Lake, symbols: Iterable[str], pause: float = PAUSE_SECONDS) -> int:
    """Download filings not already in raw/. Returns how many were fetched."""
    fetched = 0
    with nse_results.client() as c:
        for symbol in symbols:
            try:
                filings = quarterly(nse_results.fetch_filings(c, symbol))
            except Exception as exc:  # NSE hiccup: skip this company, the next run retries
                log.warning(f"{SOURCE}: {symbol} filing list failed: {exc}")
                continue
            new = 0
            for f in filings:
                end = nse_results._d(f.get("toDate"))
                if end is None:
                    continue
                path = lake.raw_dir(SOURCE, end) / f"{symbol}_{f.get('seqNumber')}.json"
                if path.exists():
                    continue
                try:
                    detail = nse_results.fetch_detail(c, f)
                except Exception as exc:
                    log.warning(f"{SOURCE}: {symbol} {end} failed: {exc}")
                    continue
                path.write_text(json.dumps({"filing": f, "detail": detail}), encoding="utf-8")
                new += 1
                time.sleep(pause)
            fetched += new
            log.info(f"{SOURCE}: {symbol} — {len(filings)} filings, {new} new")
            time.sleep(pause)
    return fetched


def build(lake: Lake) -> pd.DataFrame:
    """Rebuild clean/financial_results from every raw filing."""
    rows = []
    for path in sorted((lake.raw / SOURCE).glob("*/*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            rows.append(nse_results.normalise(doc["filing"], doc["detail"]))
        except Exception as exc:  # a broken file: report it, keep going
            log.warning(f"{SOURCE}: could not read {path.name}: {exc}")
    df = pd.DataFrame(rows)
    if not df.empty:
        df["_seq"] = pd.to_numeric(df["seq"], errors="coerce")
        df = (df.sort_values(["symbol", "period_end", "consolidated", "_seq"])
                .drop_duplicates(["symbol", "period_end", "consolidated"], keep="last").drop(columns="_seq"))
        lake.write_table(df.reset_index(drop=True), DATASET)
    log.info(f"{DATASET}: {len(df)} filings for {df['symbol'].nunique() if len(df) else 0} companies")
    return df


def run(symbols: list[str] | None = None, top: int = 20, lake: Lake | None = None) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    targets = [s.upper() for s in symbols] if symbols else top_symbols(top)
    log.info(f"{SOURCE}: {len(targets)} companies")
    fetch(lake, targets)
    return build(lake)
