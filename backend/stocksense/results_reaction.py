"""
How the market reacted to each quarterly result — the company's move against NIFTY 50
over the 1 and 5 trading days after the filing, next to the year-on-year change in
revenue and profit. For the company page: good results don't always lift the price
(expectations were higher), and weak ones don't always sink it.

The baseline is the last close before the market could react: a filing during market
hours (before 15:30 IST) is measured from the previous day's close, one after the close
from that day's close. The first release of a quarter counts (standalone and
consolidated are filed minutes apart).
"""

from __future__ import annotations

from datetime import datetime, time

import pandas as pd

MARKET_CLOSE = time(15, 30)
HORIZONS = (1, 5)
BIG_MOVE = 5.0  # % excess move that counts as a strong reaction
CLEAR_MOVE = 2.0  # % excess move that counts as a direction at all (smaller is noise)
SHOWN = 8       # results per company in the export


def filed_time(value: str | None) -> datetime | None:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M"):
        try:
            return datetime.strptime(value.strip().title(), fmt)
        except (AttributeError, ValueError):
            continue
    return None


def _yoy(rows: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year revenue and profit change within each basis (same quarter, a year earlier)."""
    out = []
    for _, g in rows.groupby(["symbol", "consolidated"]):
        g = g.sort_values("period_end").set_index("period_end")
        for end, r in g.iterrows():
            year_ago = end - pd.DateOffset(years=1)
            prev = g[(g.index >= year_ago - pd.Timedelta(days=10)) & (g.index <= year_ago + pd.Timedelta(days=10))]
            rev = profit = None
            if len(prev):
                p = prev.iloc[-1]
                if p["revenue"] and p["revenue"] > 0 and pd.notna(r["revenue"]):
                    rev = 100 * (r["revenue"] / p["revenue"] - 1)
                if p["net_profit"] and p["net_profit"] > 0 and pd.notna(r["net_profit"]):
                    profit = 100 * (r["net_profit"] / p["net_profit"] - 1)
            out.append({"symbol": r["symbol"], "period_end": end, "consolidated": r["consolidated"],
                        "revenue_yoy_pct": rev, "profit_yoy_pct": profit})
    return pd.DataFrame(out)


def reactions(results: pd.DataFrame, prices: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    """One row per company and quarter: filing time, YoY growth, and the move after filing.

    `prices`: date, symbol, close (adjusted). `index`: date, close (NIFTY 50)."""
    df = results.copy()
    df["period_end"] = pd.to_datetime(df["period_end"])
    if "suspect" in df:
        df = df[~df["suspect"].fillna(False).astype(bool)]
    if "net_revenue" in df:
        df["revenue"] = df["net_revenue"]
    df["filed"] = df["filed_at"].map(filed_time)
    growth = _yoy(df)
    # Consolidated growth where it exists for the quarter, else standalone.
    growth = (growth.sort_values("consolidated").dropna(subset=["profit_yoy_pct", "revenue_yoy_pct"], how="all")
                    .drop_duplicates(["symbol", "period_end"], keep="last"))
    first = df.dropna(subset=["filed"]).groupby(["symbol", "period_end"])["filed"].min().reset_index()
    out = first.merge(growth, on=["symbol", "period_end"], how="left")

    px = prices.assign(date=pd.to_datetime(prices["date"])).pivot_table(index="date", columns="symbol", values="close")
    nifty = index.assign(date=pd.to_datetime(index["date"])).set_index("date")["close"].sort_index()
    days = px.index.intersection(nifty.index).sort_values()
    rows = []
    for r in out.itertuples():
        filed = r.filed
        base_day = pd.Timestamp(filed.date())
        before = days[days <= base_day] if filed.time() >= MARKET_CLOSE else days[days < base_day]
        after = days[days > before[-1]] if len(before) else days[:0]
        row = {"symbol": r.symbol, "period_end": r.period_end.date(), "filed": filed.isoformat(sep=" "),
               "revenue_yoy_pct": r.revenue_yoy_pct, "profit_yoy_pct": r.profit_yoy_pct}
        for h in HORIZONS:
            row[f"move_{h}d_pct"] = row[f"excess_{h}d_pct"] = None
            if r.symbol in px.columns and len(before) and len(after) >= h:
                b, a = before[-1], after[h - 1]
                stock = px.at[a, r.symbol] / px.at[b, r.symbol] - 1 if pd.notna(px.at[b, r.symbol]) else None
                market = nifty[a] / nifty[b] - 1
                if stock is not None and pd.notna(stock):
                    row[f"move_{h}d_pct"] = round(100 * stock, 2)
                    row[f"excess_{h}d_pct"] = round(100 * (stock - market), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def note(company_reactions: list[dict]) -> str | None:
    """How often results moved the share strongly against the market."""
    measured = [r for r in company_reactions if r.get("excess_1d_pct") is not None]
    if len(measured) < 4:
        return None
    big = [r for r in measured if abs(r["excess_1d_pct"]) >= BIG_MOVE]
    against = [r for r in measured if r.get("profit_yoy_pct") is not None and abs(r["excess_1d_pct"]) >= CLEAR_MOVE
               and (r["profit_yoy_pct"] > 0) != (r["excess_1d_pct"] > 0)]
    if big:
        text = (f"After {len(big)} of its last {len(measured)} results the share moved {BIG_MOVE:.0f}% or more "
                "against the market the next day.")
    else:
        text = (f"None of its last {len(measured)} results moved the share {BIG_MOVE:.0f}% or more against the "
                "market the next day.")
    if against:
        times = {1: "Once", 2: "Twice"}.get(len(against), f"{len(against)} times")
        text += (f" {times} it moved the opposite way to the profit change — prices react to what investors "
                 "expected, not only to the numbers.")
    return text
