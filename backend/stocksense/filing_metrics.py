"""
Score inputs computed from companies' own quarterly filings (clean/financial_results)
instead of Yahoo's summary fields (M1.2).

Two of the six score metrics come from the profit-and-loss statement:

  • net margin      — trailing-twelve-month profit ÷ trailing-twelve-month revenue
  • revenue growth  — 3-year CAGR of trailing-twelve-month revenue

Both use the latest four consecutive quarters a company has filed, so `as_of` says how
current each figure is. NSE's per-company filing feed ends at Dec 2024 (later results
moved to SEBI's integrated filing), which is why `rescore --fundamentals filings`
refuses to publish figures older than MAX_AGE_DAYS.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

MAX_AGE_DAYS = 200      # a quarter's results are due within 45–60 days; 200 means a missed filing
CAGR_YEARS = 3
# Four quarter-ends in a row span ~273 days (31 Mar → 31 Dec); allow month-end jitter.
FOUR_QUARTERS_DAYS = (260, 290)

COLUMNS = {"net_margin": "net_margin", "cagr": "revenue_cagr_3yr"}


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["period_end"]).copy()
    df["period_end"] = pd.to_datetime(df["period_end"])
    if "consolidated" not in df:
        df["consolidated"] = True
    # Banks are measured on net interest + other income (see nse_results._net_revenue).
    if "net_revenue" in df:
        df["revenue"] = df["net_revenue"]
    return df


def trailing_twelve_months(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling four-quarter revenue and profit per company and basis (standalone/consolidated);
    NaN where the four quarters aren't consecutive."""
    df = _prepare(df).sort_values(["symbol", "consolidated", "period_end"])
    out = []
    for (symbol, consolidated), g in df.groupby(["symbol", "consolidated"], sort=False):
        g = g.drop_duplicates("period_end").set_index("period_end")
        span = g.index.to_series().diff(3).dt.days.values
        ttm = g[["revenue", "net_profit"]].rolling(4, min_periods=4).sum()
        ok = (span >= FOUR_QUARTERS_DAYS[0]) & (span <= FOUR_QUARTERS_DAYS[1])
        ttm.loc[~ok] = float("nan")
        ttm["symbol"], ttm["consolidated"] = symbol, consolidated
        out.append(ttm.reset_index())
    if not out:
        return pd.DataFrame(columns=["symbol", "consolidated", "period_end", "revenue", "net_profit"])
    return pd.concat(out, ignore_index=True)


def _cagr(g: pd.DataFrame, end: pd.Timestamp) -> float | None:
    """3-year growth of trailing revenue to `end`, within one basis."""
    if end not in g.index:
        return None
    then = end - pd.DateOffset(years=CAGR_YEARS)
    earlier = g[(g.index >= then - pd.Timedelta(days=10)) & (g.index <= then + pd.Timedelta(days=10))]
    now, past = g.at[end, "revenue"], (earlier.iloc[-1]["revenue"] if len(earlier) else None)
    if past is None or not past > 0 or not now > 0:
        return None
    return 100 * ((now / past) ** (1 / CAGR_YEARS) - 1)


def latest(df: pd.DataFrame) -> pd.DataFrame:
    """Per company, as of its latest complete four quarters: net_margin and revenue_cagr_3yr (percent).

    Consolidated figures where the four quarters all have them, else standalone — never a mix.
    Growth comes from the same basis, falling back to the other basis at the same date."""
    ttm = trailing_twelve_months(df).dropna(subset=["revenue"])
    rows = []
    for symbol, s in ttm.groupby("symbol"):
        bases = {c: g.set_index("period_end").sort_index() for c, g in s.groupby("consolidated")}
        end = max(g.index[-1] for g in bases.values())
        basis = True if True in bases and end in bases[True].index else False
        now = bases[basis].loc[end]
        margin = (100 * now["net_profit"] / now["revenue"]
                  if now["revenue"] > 0 and pd.notna(now["net_profit"]) else None)
        cagr = _cagr(bases[basis], end)
        if cagr is None and (not basis) in bases:
            cagr = _cagr(bases[not basis], end)
        rows.append({"symbol": symbol, "as_of": end.date(), "consolidated": bool(basis),
                     "ttm_revenue": round(float(now["revenue"]), 1),
                     "ttm_net_profit": round(float(now["net_profit"]), 1) if pd.notna(now["net_profit"]) else None,
                     "net_margin": round(margin, 2) if margin is not None else None,
                     "revenue_cagr_3yr": round(cagr, 2) if cagr is not None else None})
    return pd.DataFrame(rows, columns=["symbol", "as_of", "consolidated", "ttm_revenue", "ttm_net_profit",
                                       "net_margin", "revenue_cagr_3yr"])


def overlay(rows: list[dict], metrics: pd.DataFrame) -> tuple[list[dict], int]:
    """Copies of `rows` with filing-based margin and growth where a company has them; returns (rows, replaced)."""
    by_symbol = metrics.set_index("symbol").to_dict("index") if len(metrics) else {}
    out, replaced = [], 0
    for row in rows:
        m = by_symbol.get(row.get("symbol"))
        if not m:
            out.append(row)
            continue
        new = dict(row)
        for column in COLUMNS.values():
            if m.get(column) is not None and pd.notna(m.get(column)):
                new[column] = m[column]
        replaced += 1
        out.append(new)
    return out, replaced


def stale(metrics: pd.DataFrame, today: date | None = None, max_age_days: int = MAX_AGE_DAYS) -> list[str]:
    """Companies whose latest filing-based figures are too old to publish."""
    today = today or date.today()
    return [r.symbol for r in metrics.itertuples() if (today - r.as_of).days > max_age_days]
