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

Results from Mar 2025 on come from SEBI's integrated filing (sources/nse_integrated.py:
an XBRL file per filing, saved raw under raw/nse_integrated/), so one run covers 2005 to
the latest quarter.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable

import httpx
import pandas as pd

from ..lake import Lake
from ..log import get_logger
from ..sources import nse_integrated, nse_results

log = get_logger(__name__)

SOURCE = "nse_results"
INTEGRATED = "nse_integrated"
DATASET = "financial_results"
PAUSE_SECONDS = 1.0
MAX_FAILURES_IN_A_ROW = 3  # then NSE is refusing us, not hiccuping: stop and let a later run resume


class NseUnavailable(Exception):
    pass


class Breaker:
    """Counts failures in a row; on 25 Nov 2026 NSE timed out every request for 40 minutes,
    and retrying each one for a minute is neither polite nor useful."""

    def __init__(self, limit: int = MAX_FAILURES_IN_A_ROW):
        self.limit, self.in_a_row = limit, 0

    def ok(self) -> None:
        self.in_a_row = 0

    def fail(self, what: str, exc: Exception) -> None:
        log.warning(f"{what} failed: {exc}")
        if _answered(exc):  # NSE replied (e.g. a filing's XBRL link is a 404): it isn't refusing us
            self.in_a_row = 0
            return
        self.in_a_row += 1
        if self.in_a_row >= self.limit:
            raise NseUnavailable(f"{self.in_a_row} requests in a row failed")


def _answered(exc: Exception) -> bool:
    """A definite answer about one file (404, 410…) rather than NSE refusing or not replying
    (timeouts, 403, 429, 5xx). On 26 Nov three dead XBRL links for one company stopped a run."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return 400 <= status < 500 and status not in (403, 429)
    return False


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


REST_SECONDS = 15 * 60  # NSE throttles long runs for a while, then answers again


def recent_filings(filings: list[dict], quarters: int) -> list[dict]:
    """The last `quarters` quarter-ends, one filing each: consolidated where filed, else standalone."""
    best: dict = {}
    for f in filings:
        end = nse_integrated._d(f.get("qe_Date"))
        if end is None or not f.get("xbrl"):
            continue
        if end not in best or (f.get("consolidated") == "Consolidated" and best[end].get("consolidated") != "Consolidated"):
            best[end] = f
    return [best[e] for e in sorted(best, reverse=True)[:quarters]]


def fetch(lake: Lake, symbols: Iterable[str], pause: float = PAUSE_SECONDS, rests: int = 0,
          rest_seconds: float = REST_SECONDS, recent: int | None = None) -> int:
    """Download filings not already in raw/. Returns how many were fetched.

    If NSE fails MAX_FAILURES_IN_A_ROW requests in a row, wait `rest_seconds` and carry on
    from the same company, up to `rests` times; then stop, keeping what it has.

    `recent`: only the last N quarters from integrated filings, one basis per quarter — enough
    for trailing margin, ROE and debt to equity across the whole market in one night."""
    symbols = list(symbols)
    fetched, position = 0, 0
    while True:
        breaker = Breaker()
        try:
            with nse_results.client() as c:
                while position < len(symbols):
                    if recent:
                        fetched += fetch_integrated(c, lake, symbols[position], pause, breaker, recent)
                    else:
                        fetched += _fetch_company(c, lake, symbols[position], pause, breaker)
                    position += 1
            return fetched
        except NseUnavailable as exc:
            if rests <= 0:
                log.warning(f"{SOURCE}: stopping — NSE is not responding ({exc}); a later run resumes from here")
                return fetched
            rests -= 1
            log.warning(f"{SOURCE}: NSE is not responding ({exc}); resting {rest_seconds / 60:.0f} min "
                        f"before {symbols[position]} ({rests} rests left)")
            time.sleep(rest_seconds)


def _fetch_company(c, lake: Lake, symbol: str, pause: float, breaker: Breaker) -> int:
    """One company's filings from both feeds."""
    try:
        filings = quarterly(nse_results.fetch_filings(c, symbol))
        breaker.ok()
    except Exception as exc:  # NSE hiccup: skip this feed for the company, the next run retries
        breaker.fail(f"{SOURCE}: {symbol} filing list", exc)
        filings = []
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
            breaker.ok()
        except Exception as exc:
            breaker.fail(f"{SOURCE}: {symbol} {end}", exc)
            continue
        path.write_text(json.dumps({"filing": f, "detail": detail}), encoding="utf-8")
        new += 1
        time.sleep(pause)
    log.info(f"{SOURCE}: {symbol} — {len(filings)} filings, {new} new")
    time.sleep(pause)
    return new + fetch_integrated(c, lake, symbol, pause, breaker)


def fetch_integrated(c, lake: Lake, symbol: str, pause: float = PAUSE_SECONDS, breaker: Breaker | None = None,
                     recent: int | None = None) -> int:
    """Integrated filings (Mar 2025 on) not already in raw/: filing metadata + XBRL text."""
    breaker = breaker or Breaker()
    try:
        filings = nse_integrated.fetch_filings(c, symbol)
        breaker.ok()
    except Exception as exc:
        breaker.fail(f"{INTEGRATED}: {symbol} filing list", exc)
        return 0
    if recent:
        filings = recent_filings(filings, recent)
    new = 0
    for f in filings:
        end = nse_integrated._d(f.get("qe_Date"))
        if end is None or not f.get("xbrl"):
            continue
        path = lake.raw_dir(INTEGRATED, end) / f"{symbol}_{f.get('seq_Id')}.json"
        if path.exists():
            continue
        try:
            xml = nse_integrated.fetch_xbrl(c, f)
            breaker.ok()
        except Exception as exc:
            breaker.fail(f"{INTEGRATED}: {symbol} {end}", exc)
            continue
        path.write_text(json.dumps({"filing": f, "xml": xml}), encoding="utf-8")
        new += 1
        time.sleep(pause)
    log.info(f"{INTEGRATED}: {symbol} — {len(filings)} filings, {new} new")
    time.sleep(pause)
    return new


def consistent_kind(df: pd.DataFrame) -> pd.DataFrame:
    """One statement kind per company: a lender stays a lender even in a quarter NSE tagged
    as a plain company (Bajaj Finance, Mar 2023) — otherwise that quarter's revenue isn't netted."""
    special = df[df["kind"] != "company"].sort_values("period_end").groupby("symbol")["kind"].last()
    df = df.copy()
    df["kind"] = df["symbol"].map(special).fillna(df["kind"])
    df["bank"] = df["kind"] == "bank"
    if "excise_duty" not in df:
        df["excise_duty"] = None
    df["net_revenue"] = [nse_results.net_revenue(r) for r in
                         df[["kind", "revenue", "finance_cost", "other_income", "excise_duty"]].to_dict("records")]
    return df


SUSPECT_FACTOR = 4  # a large company's revenue 4× off its neighbours is a filing error, not a business change


def suspect(df: pd.DataFrame) -> pd.Series:
    """Quarters whose revenue is over 4× off the median of the surrounding two years (same
    company and basis) — e.g. L&T's consolidated Jun 2022 filing at ₹83 crore instead of
    ~₹35,850 crore, Sun Pharma's at ₹1,921 crore instead of ~₹11,000 crore. Kept in the
    table, flagged, and left out of sums."""
    df = df.sort_values(["symbol", "consolidated", "period_end"])
    median = (df.groupby(["symbol", "consolidated"])["revenue"]
                .transform(lambda s: s.rolling(9, center=True, min_periods=3).median()))
    ratio = df["revenue"] / median
    flag = (median > 0) & (df["revenue"] > 0) & ((ratio < 1 / SUSPECT_FACTOR) | (ratio > SUSPECT_FACTOR))
    return flag.reindex(df.index).fillna(False).astype(bool)


def build(lake: Lake) -> pd.DataFrame:
    """Rebuild clean/financial_results from every raw filing."""
    rows = []
    # Integrated filings second, so they win if both feeds carry a quarter.
    for rank, (source, parse) in enumerate([
        (SOURCE, lambda doc: nse_results.normalise(doc["filing"], doc["detail"])),
        (INTEGRATED, lambda doc: nse_integrated.normalise(doc["filing"], doc["xml"])),
    ]):
        for path in sorted((lake.raw / source).glob("*/*.json")):
            try:
                row = parse(json.loads(path.read_text(encoding="utf-8")))
            except Exception as exc:  # a broken file: report it, keep going
                log.warning(f"{source}: could not read {path.name}: {exc}")
                continue
            rows.append({**row, "source": source, "_rank": rank})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["_seq"] = pd.to_numeric(df["seq"], errors="coerce")
        df = (df.sort_values(["symbol", "period_end", "consolidated", "_rank", "_seq"])
                .drop_duplicates(["symbol", "period_end", "consolidated"], keep="last")
                .drop(columns=["_seq", "_rank"]))
        df = consistent_kind(df)
        df["suspect"] = suspect(df)
        lake.write_table(df.reset_index(drop=True), DATASET)
    log.info(f"{DATASET}: {len(df)} filings for {df['symbol'].nunique() if len(df) else 0} companies")
    return df


def resume_from(targets: list[str], start: str | None) -> list[str]:
    """The targets from `start` on, to pick up a run NSE cut short: from that symbol's place in
    the list if it's there (any order), else every symbol after it alphabetically."""
    if not start:
        return targets
    start = start.upper()
    if start in targets:
        return targets[targets.index(start):]
    return [t for t in targets if t >= start]


def largest_first(targets: list[str], caps: dict[str, float]) -> list[str]:
    """Largest market cap first, companies without one after them in their original order —
    so a multi-night backfill NSE cuts short has already covered the companies that matter most."""
    known = sorted((t for t in targets if caps.get(t)), key=lambda t: caps[t], reverse=True)
    return known + [t for t in targets if not caps.get(t)]


def market_caps() -> dict[str, float]:
    from ..market import MarketData

    return {s.symbol: s.market_cap for s in MarketData().stocks() if s.market_cap}


def run(symbols: list[str] | None = None, top: int = 20, lake: Lake | None = None, rests: int = 0,
        everything: bool = False, recent: int | None = None, start: str | None = None,
        by_size: bool = False) -> pd.DataFrame:
    lake = lake or Lake.from_settings()
    if symbols:
        targets = [s.upper() for s in symbols]
    elif everything:
        from ..symbols import select

        targets = [s.symbol for s in select()]
    else:
        targets = top_symbols(top)
    if by_size:
        targets = largest_first(targets, market_caps())
    targets = resume_from(targets, start)
    log.info(f"{SOURCE}: {len(targets)} companies" + (f", last {recent} quarters" if recent else ""))
    fetch(lake, targets, rests=rests, recent=recent)
    return build(lake)
