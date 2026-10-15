"""
End-of-day price history: corporate-action adjustment, symbol continuity and
data checks, on top of clean/eod_prices (prices as traded, from the bhavcopy).

A 1:1 bonus halves a share's price overnight, which looks like a crash to any
model. So the `eod_adjusted` view divides every price before an action by the
number of shares one old share became (and multiplies volume by it):

    adjusted price(t) = traded price(t) / product of multipliers of actions with ex_date > t

and reports history under today's symbol (rows traded as ZOMATO show as ETERNAL).

Reference tables (clean/, built by `python -m stocksense ingest-corporate-actions`):
    corporate_actions    every NSE corporate action, with kind / multiplier / dividend
    symbol_changes       NSE's old → new symbol list
    symbol_map           (traded symbol, valid_from, until) → current symbol, renames resolved
    price_adjustments    one row per share-count change: multiplier used and how it was checked
    adjustment_factors   (symbol, valid_from, valid_to, factor) ranges the view joins on

How a multiplier is checked: on the ex-date NSE quotes a previous close already
adjusted for the action, so (last close before ex-date) / (ex-date prev_close)
shows the exchange's own ratio. Where both exist they must agree within 3%.
"""

from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from .lake import Lake
from .log import get_logger

log = get_logger(__name__)

SHARE_KINDS = ("split", "bonus", "bonus_split", "consolidation")
EQUITY_SERIES = ("EQ", "BE", "BZ", "SM", "ST")
BEGINNING = date(1900, 1, 1)
FOREVER = date(9999, 12, 31)
AGREE_WITHIN = 0.03  # parsed vs exchange ratio
MAX_RENAME_CHAIN = 20


# ── symbols ─────────────────────────────────────────────────────────────────

def resolve_symbol_map(changes: pd.DataFrame) -> pd.DataFrame:
    """
    NSE's rename list → rows (traded_symbol, valid_from, until, current_symbol):
    a row traded as `traded_symbol` on a day in [valid_from, until) belongs to the
    company now trading as `current_symbol`. Chains (A→B→C) are followed; a symbol
    reused later by another company only maps its own period.
    """
    if changes.empty:
        return pd.DataFrame(columns=["traded_symbol", "valid_from", "until", "current_symbol"])
    by_old: dict[str, list[tuple[date, str]]] = {}
    for r in changes.itertuples(index=False):
        by_old.setdefault(r.old_symbol, []).append((r.effective_date, r.new_symbol))
    for v in by_old.values():
        v.sort()

    def follow(symbol: str, since: date) -> str:
        for _ in range(MAX_RENAME_CHAIN):
            later = [(d, new) for d, new in by_old.get(symbol, []) if d > since]
            if not later:
                return symbol
            since, symbol = later[0]
        return symbol

    rows = []
    for old, renames in by_old.items():
        start = BEGINNING
        for d, new in renames:
            if d > start:
                rows.append((old, start, d, follow(new, d)))
            start = d
    out = pd.DataFrame(rows, columns=["traded_symbol", "valid_from", "until", "current_symbol"])
    return out[out["traded_symbol"] != out["current_symbol"]].reset_index(drop=True)


def map_symbols(symbols: pd.Series, days: pd.Series, symbol_map: pd.DataFrame) -> pd.Series:
    """Current symbol for each (symbol, day) pair."""
    out = symbols.copy()
    for r in symbol_map.itertuples(index=False):
        hit = (symbols == r.traded_symbol) & (days >= r.valid_from) & (days < r.until)
        out[hit] = r.current_symbol
    return out


# ── adjustments ─────────────────────────────────────────────────────────────

def _normalise_subject(subject: str) -> str:
    return re.sub(r"\(.*?\)", "", subject).strip().lower()


def share_actions(actions: pd.DataFrame) -> pd.DataFrame:
    """One row per (symbol, ex_date) with a share-count change; duplicate listings merged."""
    df = actions[actions["kind"].isin(SHARE_KINDS) & (actions["series"] == "EQ")].copy()
    if df.empty:
        return pd.DataFrame(columns=["symbol", "ex_date", "parsed", "subject"])
    df["_norm"] = df["subject"].map(_normalise_subject)
    df = df.drop_duplicates(subset=["symbol", "ex_date", "_norm"])
    grouped = df.groupby(["symbol", "ex_date"], sort=True)
    out = grouped.agg(
        parsed=("multiplier", lambda m: float(np.prod(m.dropna())) if m.notna().any() else np.nan),
        subject=("subject", " | ".join),
    ).reset_index()
    return out


def observed_ratios(actions: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """
    The exchange's ratio for each action: last close before the ex-date divided by
    the ex-date's (already adjusted) previous close. NaN when either day is missing.
    `prices` has date, symbol, close, prev_close for the traded symbols.
    """
    prices = prices.sort_values(["symbol", "date"])
    ratios = []
    by_symbol = {s: g for s, g in prices.groupby("symbol", sort=False)}
    for a in actions.itertuples(index=False):
        g = by_symbol.get(a.symbol)
        if g is None:
            ratios.append(np.nan)
            continue
        dates = g["date"].to_numpy()
        i = int(np.searchsorted(dates, np.datetime64(a.ex_date), side="left"))
        if i == 0 or i >= len(g) or (dates[i] - np.datetime64(a.ex_date)) > np.timedelta64(10, "D"):
            ratios.append(np.nan)
            continue
        before, on = g.iloc[i - 1], g.iloc[i]
        ok = before["close"] > 0 and on["prev_close"] > 0
        ratios.append(before["close"] / on["prev_close"] if ok else np.nan)
    return pd.Series(ratios, index=actions.index, dtype="float64")


def choose_multipliers(acts: pd.DataFrame) -> pd.DataFrame:
    """
    Pick the multiplier to use and say why:
      confirmed — parsed ratio and exchange ratio agree (parsed used)
      exchange  — they disagree, or nothing parsed; the exchange's visible jump used
      parsed    — no price data around the ex-date; parsed ratio used unchecked
      skipped   — neither gives a share-count change
    """
    acts = acts.copy()
    parsed, observed = acts["parsed"], acts["observed"]
    clear_jump = observed.notna() & ((observed - 1).abs() > 0.02) & observed.between(0.02, 60)
    agree = parsed.notna() & observed.notna() & ((observed / parsed - 1).abs() <= AGREE_WITHIN)
    acts["status"] = np.select(
        [agree, clear_jump, parsed.notna() & observed.isna()],
        ["confirmed", "exchange", "parsed"],
        default="skipped",
    )
    acts["multiplier"] = np.select(
        [acts["status"] == "confirmed", acts["status"] == "exchange", acts["status"] == "parsed"],
        [parsed, observed, parsed],
        default=np.nan,
    )
    return acts


def factor_ranges(adjustments: pd.DataFrame) -> pd.DataFrame:
    """
    Used multipliers → (symbol, valid_from, valid_to, factor): a price on a day in
    [valid_from, valid_to) is divided by `factor`. Days on/after the last ex-date
    need no row (factor 1).
    """
    rows = []
    used = adjustments.dropna(subset=["multiplier"]).sort_values(["symbol", "ex_date"])
    for symbol, g in used.groupby("symbol", sort=False):
        ex_dates = list(g["ex_date"])
        mults = list(g["multiplier"])
        start = BEGINNING
        for i, ex in enumerate(ex_dates):
            rows.append((symbol, start, ex, float(np.prod(mults[i:]))))
            start = ex
    return pd.DataFrame(rows, columns=["symbol", "valid_from", "valid_to", "factor"])


ADJUSTED_VIEW = """
create or replace view eod_adjusted as
select p.date,
       coalesce(m.current_symbol, p.symbol) as symbol,
       p.symbol as traded_symbol,
       p.series, p.isin,
       p.open  / coalesce(f.factor, 1) as open,
       p.high  / coalesce(f.factor, 1) as high,
       p.low   / coalesce(f.factor, 1) as low,
       p.close / coalesce(f.factor, 1) as close,
       p.volume * coalesce(f.factor, 1) as volume,
       p.turnover, p.trades,
       p.close as close_traded,
       coalesce(f.factor, 1) as adj_factor
from eod_prices p
left join symbol_map m
  on m.traded_symbol = p.symbol and p.date >= m.valid_from and p.date < m.until
left join adjustment_factors f
  on f.symbol = coalesce(m.current_symbol, p.symbol) and p.date >= f.valid_from and p.date < f.valid_to
"""


def create_view(lake: Lake) -> bool:
    """(Re)create the eod_adjusted view once its inputs exist. Returns whether it did."""
    needed = {"eod_prices", "symbol_map", "adjustment_factors"}
    if not needed <= set(lake.datasets()):
        return False
    lake.execute(ADJUSTED_VIEW)
    return True


def build_adjustments(lake: Lake, actions: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """Compute and store symbol_map, price_adjustments and adjustment_factors."""
    symbol_map = resolve_symbol_map(changes)
    acts = share_actions(actions)
    if acts.empty:
        log.warning("No share-count actions found")
    traded = sorted(acts["symbol"].unique().tolist())
    prices = pd.DataFrame(columns=["date", "symbol", "close", "prev_close"])
    if traded and "eod_prices" in lake.datasets():
        prices = lake.query(
            "select date, symbol, close, prev_close, volume from eod_prices "
            f"where series in {EQUITY_SERIES} and symbol in (select symbol from wanted)",
            frames={"wanted": pd.DataFrame({"symbol": traded})},
        )
        prices["date"] = pd.to_datetime(prices["date"])
        # One row per symbol and day (a stock can move between EQ and BE): keep the busiest.
        prices = prices.sort_values("volume").drop_duplicates(["symbol", "date"], keep="last")
    acts["observed"] = observed_ratios(acts, prices)
    acts = choose_multipliers(acts)
    acts["traded_symbol"] = acts["symbol"]
    acts["symbol"] = map_symbols(acts["symbol"], acts["ex_date"], symbol_map)
    factors = factor_ranges(acts)

    lake.write_table(symbol_map, "symbol_map", refresh=False)
    lake.write_table(acts, "price_adjustments", refresh=False)
    lake.write_table(factors, "adjustment_factors", refresh=False)
    lake.refresh_catalog()
    create_view(lake)
    counts = acts["status"].value_counts().to_dict()
    log.info(f"Adjustments: {len(acts)} share-count actions → {counts}; {len(symbol_map)} symbol mappings")
    return acts


# ── checks ──────────────────────────────────────────────────────────────────

def check(lake: Lake, big_move: float = 0.40) -> dict:
    """
    Data checks on the price history. Returns a dict of findings; the CLI prints it.
    """
    q = lake.query
    days = q("""
        select date, count(*) as rows, count(*) filter (where series = 'EQ') as eq
        from eod_prices group by date order by date
    """)
    days["date"] = pd.to_datetime(days["date"])
    report: dict = {
        "trading_days": len(days),
        "first_day": str(days["date"].min().date()) if len(days) else None,
        "last_day": str(days["date"].max().date()) if len(days) else None,
        "eq_rows_per_day": {k: int(v) for k, v in days["eq"].describe()[["min", "50%", "max"]].items()},
    }
    gaps = days["date"].diff().dt.days
    report["calendar_gaps_over_5_days"] = [
        f"{(d - pd.Timedelta(days=int(g))).date()} → {d.date()}" for d, g in zip(days["date"], gaps) if g > 5
    ]
    median = days["eq"].rolling(21, min_periods=5, center=True).median()
    report["thin_days"] = [str(d.date()) for d, n, m in zip(days["date"], days["eq"], median) if m and n < 0.5 * m]
    report["duplicates"] = int(q("""
        select count(*) from (select date, symbol, series from eod_prices group by 1, 2, 3 having count(*) > 1)
    """).iloc[0, 0])
    report["bad_prices"] = q("""
        select count(*) filter (where close <= 0 or open <= 0) as non_positive,
               count(*) filter (where low > high) as low_above_high,
               count(*) filter (where close > high * 1.0001 or close < low * 0.9999) as close_outside_range
        from eod_prices where series = 'EQ' and volume > 0
    """).iloc[0].astype(int).to_dict()
    if "price_adjustments" in lake.datasets():
        adj = q("select status, count(*) as n from price_adjustments group by status")
        report["adjustments"] = dict(zip(adj["status"], adj["n"].astype(int)))
    if "eod_adjusted" in _views(lake):
        moves = q(f"""
            with r as (
              select symbol, date, close,
                     close / lag(close) over (partition by symbol order by date) - 1 as ret
              from eod_adjusted where series = 'EQ'
            )
            select symbol, date, ret from r where abs(ret) > {big_move} order by abs(ret) desc
        """)
        report["unexplained_moves_over_40pct"] = len(moves)
        report["largest_unexplained_moves"] = [
            f"{r.symbol} {pd.Timestamp(r.date).date()} {r.ret:+.0%}" for r in moves.head(10).itertuples()
        ]
    return report


def _views(lake: Lake) -> set[str]:
    return set(lake.query("select view_name from duckdb_views() where not internal")["view_name"])


def adjusted_history(lake: Lake, symbols: list[str], start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """Adjusted daily OHLCV for these (current) symbols, EQ series, as a DataFrame."""
    sql = "select * from eod_adjusted where series = 'EQ' and symbol in (select symbol from wanted)"
    params: list = []
    if start:
        sql += " and date >= ?"
        params.append(start)
    if end:
        sql += " and date <= ?"
        params.append(end)
    df = lake.query(sql + " order by symbol, date", params, frames={"wanted": pd.DataFrame({"symbol": symbols})})
    df["date"] = pd.to_datetime(df["date"])
    return df
