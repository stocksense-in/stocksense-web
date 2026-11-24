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

How a multiplier is checked: against the price jump the market actually shows,
(last close before the ex-date) / (open on the ex-date). The bhavcopy's prev_close
is NOT adjusted on the ex-date (NESTLEIND, 5 Jan 2024: prev_close 27,116.40, open
2,754), so it can't be used. The jump also holds one night's ordinary market move,
hence the 10% tolerance — enough to catch a misread ratio (2 vs 1.5, 10 vs 5).
"""

from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from .lake import Lake
from .log import get_logger
from .sources.nse_corporate import rights_terms as nc_rights_terms

log = get_logger(__name__)

SHARE_KINDS = ("split", "bonus", "bonus_split", "consolidation")
EQUITY_SERIES = ("EQ", "BE", "BZ", "SM", "ST")
BEGINNING = date(1900, 1, 1)
FOREVER = date(9999, 12, 31)
AGREE_WITHIN = 0.10  # parsed ratio vs the overnight price jump (which includes a normal day's move)
LIKELY_WITHIN = 0.35  # …same-direction jumps this close still confirm the action happened
CLEAR_JUMP = 0.25  # an unexplained overnight jump this big is taken as the action's ratio
DEMERGER_MIN_DROP = 0.03  # a named demerger with at least this overnight drop is adjusted for
INFERRED_RATIOS = (2, 4, 5, 10, 20, 50, 100)  # split ratios recognised from the price alone
INFER_MIN_PRICE = 10  # below ₹10, one 5-paise tick can look like a split
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

_DEMERGER = r"(?i)demerg|scheme of arrangement"


def _normalise_subject(subject: str) -> str:
    return re.sub(r"\(.*?\)", "", subject).strip().lower()


def share_actions(actions: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (symbol, ex_date) that needs a price adjustment, duplicate listings
    merged: share-count changes (split, bonus, consolidation) and demergers.
    `price_only` marks demergers: the price steps down, the share count doesn't change.
    """
    demerger = (actions["kind"] == "restructuring") & actions["subject"].str.contains(_DEMERGER, regex=True)
    df = actions[(actions["kind"].isin(SHARE_KINDS) | demerger) & (actions["series"] == "EQ")].copy()
    if df.empty:
        return pd.DataFrame(columns=["symbol", "ex_date", "parsed", "subject", "price_only"])
    df["_norm"] = df["subject"].map(_normalise_subject)
    df["_price_only"] = ~df["kind"].isin(SHARE_KINDS)
    df = df.drop_duplicates(subset=["symbol", "ex_date", "_norm"])
    grouped = df.groupby(["symbol", "ex_date"], sort=True)
    out = grouped.agg(
        parsed=("multiplier", lambda m: float(np.prod(m.dropna())) if m.notna().any() else np.nan),
        subject=("subject", " | ".join),
        price_only=("_price_only", "all"),
    ).reset_index()
    return out


def observed_ratios(actions: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """
    The price jump the market shows for each action: last close before the ex-date
    divided by the open on the first trading day from the ex-date. NaN when either
    day is missing (or the first trade is more than 10 days after the ex-date).
    `prices` has date, symbol, open, close for the traded symbols.
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
        ok = before["close"] > 0 and on["open"] > 0
        ratios.append(before["close"] / on["open"] if ok else np.nan)
    return pd.Series(ratios, index=actions.index, dtype="float64")


def choose_multipliers(acts: pd.DataFrame) -> pd.DataFrame:
    """
    Pick the multiplier to use and say why:
      confirmed — the parsed ratio matches the overnight price jump within 10% (parsed used)
      likely    — the price jumped the same way and within 35% of the parsed ratio:
                  the action happened and the gap is the day's own move (parsed used)
      exchange  — a big jump (>25%) and nothing parsed, or a parsed ratio far from it:
                  the jump itself is used
      parsed    — no prices around the ex-date; parsed ratio used unchecked
      no_jump   — parsed, but the price didn't move that way: not applied (applying it
                  would create a fake crash; usually a cancelled or re-dated action)
      demerger  — a demerger with a big overnight drop: the drop is used (price only)
      skipped   — nothing to apply
    """
    acts = acts.copy()
    if "price_only" not in acts:
        acts["price_only"] = False
    parsed, observed = acts["parsed"], acts["observed"]
    both = parsed.notna() & observed.notna()
    gap = (np.log(observed) - np.log(parsed)).abs()
    clear_jump = observed.notna() & ((observed - 1).abs() > CLEAR_JUMP) & observed.between(0.02, 60)
    agree = both & (gap <= np.log(1 + AGREE_WITHIN))
    same_way = both & (np.sign(np.log(observed)) == np.sign(np.log(parsed))) & ((observed - 1).abs() > 0.02)
    likely = same_way & (gap <= np.log(1 + LIKELY_WITHIN))
    demerger = acts["price_only"].astype(bool)
    # "Demerger" says the price will step down, so a modest drop counts (RELIANCE / Jio
    # Financial, Jul 2023: ~10%). A vaguer "Scheme of Arrangement" is often a merger with
    # no price effect, so it needs a big drop.
    named = acts["subject"].str.contains(r"(?i)demerg", regex=True) if "subject" in acts else False
    demerger_drop = observed.notna() & observed.between(0.02, 60) & (
        (named & (observed > 1 + DEMERGER_MIN_DROP)) | (observed > 1 + CLEAR_JUMP))
    acts["status"] = np.select(
        [demerger & demerger_drop, demerger,
         agree, likely, clear_jump, parsed.notna() & observed.isna(), parsed.notna()],
        ["demerger", "skipped", "confirmed", "likely", "exchange", "parsed", "no_jump"],
        default="skipped",
    )
    status = acts["status"]
    acts["multiplier"] = np.select(
        [status.isin(["confirmed", "likely", "parsed"]), status.isin(["exchange", "demerger"])],
        [parsed, observed],
        default=np.nan,
    )
    return acts


def rights_adjustments(actions: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Rights issues below the market price transfer value to holders, so the price
    steps down on the ex-date. The standard adjustment: factor = P / TERP, where P is
    the last close before the ex-date and TERP = (held·P + new·issue price) / (held + new),
    issue price = face value + premium. Price only (`price_only`). `actions` holds
    rights rows with today's symbol; `prices` date, symbol, close.
    """
    cols = ["symbol", "traded_symbol", "ex_date", "parsed", "observed", "subject", "price_only", "status", "multiplier"]
    rows = []
    by_symbol = {s: g.sort_values("date") for s, g in prices.groupby("symbol", sort=False)}
    for a in actions.itertuples(index=False):
        terms = nc_rights_terms(a.subject)
        g = by_symbol.get(a.symbol)
        if terms is None or g is None or pd.isna(a.face_value):
            continue
        before = g[g["date"] < pd.Timestamp(a.ex_date)]
        if before.empty or (pd.Timestamp(a.ex_date) - before["date"].iloc[-1]).days > 10:
            continue
        new, held, premium = terms
        p, issue = float(before["close"].iloc[-1]), float(a.face_value) + premium
        terp = (held * p + new * issue) / (held + new)
        factor = p / terp
        if factor > 1.0005:
            rows.append((a.symbol, a.traded_symbol, a.ex_date, round(factor, 6), np.nan, a.subject, True, "rights",
                         round(factor, 6)))
    return pd.DataFrame(rows, columns=cols)


def infer_splits(jumps: pd.DataFrame, known: pd.DataFrame, within_days: int = 10) -> pd.DataFrame:
    """
    Splits missing from NSE's feed (ETF unit splits, a few old equity splits such as
    JSWSTEEL 1:10 in Jan 2017): an overnight price ratio within 3% of a round split
    ratio, with no recorded action for that symbol within `within_days`.
    `jumps`: symbol (current), ex_date, observed. `known`: symbol, ex_date of recorded actions.
    """
    cols = ["symbol", "ex_date", "parsed", "observed", "subject", "price_only", "status", "multiplier"]
    if jumps.empty:
        return pd.DataFrame(columns=cols)
    ratios = np.array(INFERRED_RATIOS)
    nearest = ratios[np.abs(np.log(jumps["observed"].to_numpy()[:, None]) - np.log(ratios)).argmin(axis=1)]
    close = np.abs(jumps["observed"] / nearest - 1) <= 0.03
    cand = jumps[close.to_numpy()].assign(multiplier=nearest[close.to_numpy()])
    if not known.empty:
        k = known.assign(ex_date=pd.to_datetime(known["ex_date"]))
        merged = cand.assign(_d=pd.to_datetime(cand["ex_date"])).merge(k, on="symbol", how="left", suffixes=("", "_k"))
        near = (merged["_d"] - merged["ex_date_k"]).abs() <= pd.Timedelta(days=within_days)
        recorded = set(merged.loc[near, ["symbol", "ex_date"]].itertuples(index=False, name=None))
        cand = cand[[(s, d) not in recorded for s, d in zip(cand["symbol"], cand["ex_date"])]]
    return cand.assign(parsed=np.nan, subject="(inferred from the price: no action in NSE's feed)",
                       price_only=False, status="inferred")[cols].reset_index(drop=True)


def factor_ranges(adjustments: pd.DataFrame) -> pd.DataFrame:
    """
    Used multipliers → (symbol, valid_from, valid_to, factor, volume_factor): a price
    on a day in [valid_from, valid_to) is divided by `factor`, its volume multiplied
    by `volume_factor` (share-count actions only; a demerger doesn't change the share
    count). Days on/after the last ex-date need no row.
    """
    rows = []
    used = adjustments.dropna(subset=["multiplier"]).sort_values(["symbol", "ex_date"])
    if "price_only" not in used:
        used = used.assign(price_only=False)
    for symbol, g in used.groupby("symbol", sort=False):
        ex_dates = list(g["ex_date"])
        mults = list(g["multiplier"])
        shares = [1.0 if p else m for m, p in zip(mults, g["price_only"])]
        start = BEGINNING
        for i, ex in enumerate(ex_dates):
            rows.append((symbol, start, ex, float(np.prod(mults[i:])), float(np.prod(shares[i:]))))
            start = ex
    return pd.DataFrame(rows, columns=["symbol", "valid_from", "valid_to", "factor", "volume_factor"])


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
       p.volume * coalesce(f.volume_factor, 1) as volume,
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
    # Work in today's symbols: an action may be listed under a company's new name
    # while it still traded under the old one on the ex-date (MINDAIND → UNOMINDA).
    acts["traded_symbol"] = acts["symbol"]
    acts["symbol"] = map_symbols(acts["symbol"], acts["ex_date"], symbol_map)
    rights = actions[(actions["kind"] == "rights") & (actions["series"] == "EQ")].copy()
    rights["traded_symbol"] = rights["symbol"]
    rights["symbol"] = map_symbols(rights["symbol"], rights["ex_date"], symbol_map)
    current = set(acts["symbol"]) | set(rights["symbol"])
    old_names = symbol_map.loc[symbol_map["current_symbol"].isin(current), "traded_symbol"]
    wanted = sorted(current | set(acts["traded_symbol"]) | set(rights["traded_symbol"]) | set(old_names))

    prices = pd.DataFrame(columns=["date", "symbol", "open", "close"])
    last_day = None
    if wanted and "eod_prices" in lake.datasets():
        prices = lake.query(
            "select date, symbol, open, close, volume from eod_prices "
            f"where series in {EQUITY_SERIES} and symbol in (select symbol from wanted)",
            frames={"wanted": pd.DataFrame({"symbol": wanted})},
        )
        prices["date"] = pd.to_datetime(prices["date"])
        relevant = symbol_map[symbol_map["traded_symbol"].isin(set(prices["symbol"]))]
        prices["symbol"] = map_symbols(prices["symbol"], prices["date"].dt.date, relevant)
        # One row per symbol and day (a stock can move between EQ and BE): keep the busiest.
        prices = prices.sort_values("volume").drop_duplicates(["symbol", "date"], keep="last")
        last_day = lake.query("select max(date) from eod_prices").iloc[0, 0]
    acts["observed"] = observed_ratios(acts, prices)
    acts = choose_multipliers(acts)
    acts = pd.concat([acts, rights_adjustments(rights, prices)], ignore_index=True)
    if "eod_prices" in lake.datasets():
        jumps = lake.query(f"""
            with r as (
              select symbol, date, open, lag(close) over w as prev_close, lag(date) over w as prev_date
              from eod_prices where series in {EQUITY_SERIES}
              window w as (partition by symbol order by date)
            )
            select symbol, date as ex_date, prev_close / open as observed from r
            where open > 0 and prev_close >= {INFER_MIN_PRICE} and datediff('day', prev_date, date) <= 5
              and prev_close / open > 1.8
        """)
        jumps["ex_date"] = pd.to_datetime(jumps["ex_date"]).dt.date
        relevant = symbol_map[symbol_map["traded_symbol"].isin(set(jumps["symbol"]))]
        jumps["traded_symbol"] = jumps["symbol"]
        jumps["symbol"] = map_symbols(jumps["symbol"], jumps["ex_date"], relevant)
        inferred = infer_splits(jumps, acts[["symbol", "ex_date"]])
        inferred["traded_symbol"] = inferred["symbol"]
        acts = pd.concat([acts, inferred], ignore_index=True)
    if last_day is not None:
        # Announced ahead: not in effect until its ex-date is in the price history.
        upcoming = pd.to_datetime(acts["ex_date"]) > pd.Timestamp(last_day)
        acts.loc[upcoming, ["status", "multiplier"]] = ["upcoming", np.nan]
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
        # EQ-series stocks have a 20% daily price band (F&O stocks a dynamic one), so a
        # bigger move between consecutive sessions usually means an action not adjusted
        # for (capital reduction, demerger) or a reused symbol. Moves across trading
        # suspensions (previous trade > 5 days earlier) are left out.
        # Sub-₹10 stocks trade in 5-paise ticks, so one tick can be a 40%+ move there;
        # those are counted separately.
        all_moves = q(f"""
            with r as (
              select symbol, date, close,
                     lag(close) over w as prev, lag(close_traded) over w as prev_traded,
                     lag(date) over w as prev_date
              from eod_adjusted where series = 'EQ'
              window w as (partition by symbol order by date)
            )
            select symbol, date, prev_traded, close / prev - 1 as ret from r
            where datediff('day', prev_date, date) <= 5 and abs(close / prev - 1) > {big_move}
            order by abs(close / prev - 1) desc
        """)
        moves = all_moves[all_moves["prev_traded"] >= 10]
        report["penny_stock_moves_over_40pct"] = int((all_moves["prev_traded"] < 10).sum())
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
