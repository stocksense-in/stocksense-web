"""
Alerts (M2.4) — what happened to a company on a given day that a watcher would want to
know, computed from the lake:

  • price_move       the share moved 5% or more (and how that compares with NIFTY 50)
  • unusual_volume   traded volume at least 3× its median of the previous 20 sessions
  • results_filed    the company filed a quarterly result (with the profit change)
  • large_order      an order/contract-win announcement
  • promoter_stake   a new shareholding pattern with the promoters' stake up or down 1+ point
  • pledge_change    promoters' pledged share of their stake moved 2+ points between snapshots

    python -m stocksense alerts --date 2023-01-27 --symbols ADANIENT ADANIPORTS

Each alert is {date, symbol, kind, value, text}; `text` is written for a beginner. The
same rules run on any past day, which is how they are tested (ml/checks/alerts_replay.py
replays the January 2023 Adani sell-off).
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .lake import Lake
from .results_reaction import filed_time

PRICE_MOVE = 5.0        # % one-day move
VOLUME_MULTIPLE = 3.0   # × median volume of the previous sessions
VOLUME_LOOKBACK = 20    # sessions
MIN_HISTORY = 10        # sessions needed before volume is judged
STAKE_MOVE = 1.0        # percentage points, quarter on quarter
PLEDGE_MOVE = 2.0       # percentage points of the promoters' stake
ORDER_CATEGORIES = ("Bagging/Receiving of orders/contracts", "Awarding of order(s)/contract(s)")


def _alert(day: date, symbol: str, kind: str, value, text: str) -> dict:
    return {"date": day.isoformat(), "symbol": symbol, "kind": kind,
            "value": None if value is None else round(float(value), 2), "text": text}


def price_and_volume(prices: pd.DataFrame, nifty: pd.Series, day: date) -> list[dict]:
    """`prices`: date, symbol, close, volume for the day and enough sessions before it."""
    out = []
    p = prices.assign(date=pd.to_datetime(prices["date"])).sort_values(["symbol", "date"])
    target = pd.Timestamp(day)
    market = None
    if target in nifty.index:
        before = nifty[nifty.index < target]
        if len(before):
            market = 100 * (nifty[target] / before.iloc[-1] - 1)
    for symbol, g in p.groupby("symbol"):
        g = g.set_index("date")
        if target not in g.index:
            continue
        prior = g[g.index < target]
        if not len(prior):
            continue
        move = 100 * (g.at[target, "close"] / prior["close"].iloc[-1] - 1)
        if abs(move) >= PRICE_MOVE:
            vs = "" if market is None else f" (NIFTY 50 {market:+.1f}%)"
            word = "rose" if move > 0 else "fell"
            out.append(_alert(day, symbol, "price_move", move, f"{symbol} {word} {abs(move):.1f}% today{vs}."))
        recent = prior["volume"].tail(VOLUME_LOOKBACK).dropna()
        if len(recent) >= MIN_HISTORY and recent.median() > 0:
            multiple = g.at[target, "volume"] / recent.median()
            if multiple >= VOLUME_MULTIPLE:
                out.append(_alert(day, symbol, "unusual_volume", multiple,
                                  f"{symbol} traded {multiple:.1f}× its usual volume — something is drawing attention."))
    return out


def results_filed(results: pd.DataFrame, day: date) -> list[dict]:
    if results is None or not len(results):
        return []
    df = results.copy()
    df["filed"] = df["filed_at"].map(filed_time)
    df = df.dropna(subset=["filed"])
    first = df.sort_values("filed").drop_duplicates(["symbol", "period_end"])
    today = first[first["filed"].map(lambda t: t.date()) == day]
    out = []
    for r in today.itertuples():
        quarter = pd.Timestamp(r.period_end).strftime("%b %Y")
        out.append(_alert(day, r.symbol, "results_filed", None,
                          f"{r.symbol} filed its results for the quarter to {quarter}."))
    return out


def large_orders(announcements: pd.DataFrame, day: date) -> list[dict]:
    if announcements is None or not len(announcements):
        return []
    a = announcements[(pd.to_datetime(announcements["date"]).dt.date == day)
                      & announcements["category"].isin(ORDER_CATEGORIES)]
    return [_alert(day, r.symbol, "large_order", None,
                   f"{r.symbol} announced an order or contract: {(r.summary or '').strip()[:160]}")
            for r in a.drop_duplicates(["symbol", "summary"]).itertuples()]


def promoter_stake(shareholding: pd.DataFrame, day: date) -> list[dict]:
    if shareholding is None or not len(shareholding) or "submitted" not in shareholding:
        return []
    sh = shareholding.copy()
    sh["submitted"] = pd.to_datetime(sh["submitted"]).dt.date
    sh = sh.sort_values(["symbol", "quarter_end"])
    sh["previous"] = sh.groupby("symbol")["promoter_pct"].shift(1)
    new = sh[(sh["submitted"] == day) & sh["previous"].notna()]
    out = []
    for r in new.itertuples():
        change = r.promoter_pct - r.previous
        if abs(change) >= STAKE_MOVE:
            word = "raised" if change > 0 else "cut"
            out.append(_alert(day, r.symbol, "promoter_stake", change,
                              f"Promoters {word} their stake in {r.symbol} from {r.previous:.1f}% to {r.promoter_pct:.1f}%."))
    return out


def pledge_change(pledges: pd.DataFrame, day: date) -> list[dict]:
    if pledges is None or not len(pledges):
        return []
    p = pledges.copy()
    p["fetched"] = pd.to_datetime(p["fetched"]).dt.date
    p = p.dropna(subset=["pledged_pct_of_promoter"]).sort_values(["symbol", "fetched"])
    p["previous"] = p.groupby("symbol")["pledged_pct_of_promoter"].shift(1)
    new = p[(p["fetched"] == day) & p["previous"].notna()]
    out = []
    for r in new.itertuples():
        change = r.pledged_pct_of_promoter - r.previous
        if abs(change) >= PLEDGE_MOVE:
            word = "more" if change > 0 else "less"
            out.append(_alert(day, r.symbol, "pledge_change", change,
                              f"Promoters of {r.symbol} now pledge {r.pledged_pct_of_promoter:.1f}% of their stake "
                              f"({abs(change):.1f} points {word} than before)."))
    return out


def for_day(lake: Lake, day: date, symbols: list[str] | None = None) -> list[dict]:
    """Every alert for `day`, optionally only for `symbols` (a watchlist)."""
    present = set(lake.datasets())
    wanted = pd.DataFrame({"symbol": [s.upper() for s in symbols]}) if symbols else None
    where = " and symbol in (select symbol from wanted)" if symbols else ""
    frames = {"wanted": wanted} if symbols else None
    start = day - timedelta(days=45)  # ~30 sessions: enough for the volume median
    alerts: list[dict] = []
    if "eod_prices" in present:
        prices = lake.query(f"select date, symbol, close, volume from eod_adjusted where series = 'EQ' "
                            f"and date between ? and ?{where}", [start, day], frames=frames)
        nifty = lake.query("select date, close from index_prices where index = 'NIFTY_50' and date between ? and ?",
                           [start, day])
        nifty = nifty.assign(date=pd.to_datetime(nifty["date"])).set_index("date")["close"].sort_index()
        alerts += price_and_volume(prices, nifty, day)
    if "financial_results" in present:
        alerts += results_filed(lake.query(f"select symbol, period_end, filed_at from financial_results where 1=1{where}",
                                           frames=frames), day)
    if "announcements" in present:
        alerts += large_orders(lake.query(f"select date, symbol, category, summary from announcements "
                                          f"where date = ?{where}", [day], frames=frames), day)
    if "shareholding" in present:
        alerts += promoter_stake(lake.query(f"select * from shareholding where 1=1{where}", frames=frames), day)
    if "pledges" in present:
        alerts += pledge_change(lake.query(f"select * from pledges where 1=1{where}", frames=frames), day)
    order = {"price_move": 0, "unusual_volume": 1, "results_filed": 2, "promoter_stake": 3, "pledge_change": 4,
             "large_order": 5}
    return sorted(alerts, key=lambda a: (a["symbol"], order.get(a["kind"], 9)))
