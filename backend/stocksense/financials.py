"""
Company financials for the company page — quarterly and yearly revenue and profit from
the companies' own filings (clean/financial_results, M1.2), written to
backend/data/financials.json, which the API serves. The public API never reads the
lake; the engine publishes this file, as it does the valuation context.

    python -m stocksense financials-export

Per company: the last 12 quarters and last 6 fiscal years (April–March) on one basis —
consolidated where the latest four quarters all have it, else standalone — plus the
filing-based score inputs (margin, growth, ROE, D/E) with their as-of date.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import filing_metrics
from . import results_reaction
from .config import DATA_DIR

OUTPUT = DATA_DIR / "financials.json"
QUARTERS = 12
YEARS = 6
HISTORY_YEARS = 5   # the company's own range: trailing margins over the last five years
MIN_HISTORY = 8     # trailing-margin points needed before a range means anything


def _num(value, digits: int = 1):
    return None if value is None or pd.isna(value) else round(float(value), digits)


def _fiscal_year(d: date) -> int:
    """FY ending 31 March: Jun 2025 → FY2026."""
    return d.year + 1 if d.month > 3 else d.year


def margin_history(rows: pd.DataFrame, basis: bool) -> dict | None:
    """Trailing-twelve-month margin now vs its own range over the last five years."""
    # Reported revenue throughout, so years before excise could be separated compare like with like.
    ttm = filing_metrics.trailing_twelve_months(rows[rows["consolidated"] == basis], net=False)
    ttm = ttm.dropna(subset=["revenue", "net_profit"])
    ttm = ttm[ttm["revenue"] > 0]
    if not len(ttm):
        return None
    end = ttm["period_end"].max()
    window = ttm[ttm["period_end"] > end - pd.DateOffset(years=HISTORY_YEARS)]
    if len(window) < MIN_HISTORY:
        return None
    margins = 100 * window["net_profit"] / window["revenue"]
    now = margins.iloc[-1]
    excise = "excise_duty" in rows and (pd.to_numeric(rows["excise_duty"], errors="coerce") > 0).any()
    return {"now": _num(now), "low": _num(margins.min()), "median": _num(margins.median()), "high": _num(margins.max()),
            "since": window["period_end"].min().date().isoformat(),
            "percentile": int(round(100 * (margins < now).mean())),
            "includes_excise": bool(excise)}


def margin_note(entry: dict | None) -> str | None:
    """Plain-language: where today's margin sits in the company's own five-year range."""
    h = (entry or {}).get("margin_history")
    if not h:
        return None
    where = ("near the top of" if h["percentile"] >= 75 else "near the bottom of" if h["percentile"] <= 25
             else "in the middle of")
    text = (f"Its trailing margin of {h['now']:.1f}% is {where} its own range since {h['since'][:4]} "
            f"({h['low']:.1f}%–{h['high']:.1f}%, median {h['median']:.1f}%).")
    if h.get("includes_excise"):
        text += (" Measured on revenue including excise duty, the only way older years can be compared, "
                 "so these figures run lower than a margin on net sales.")
    return text


def company(rows: pd.DataFrame, latest: dict) -> dict:
    """One company's published financials, on the basis its latest metrics use."""
    basis = bool(latest["consolidated"])
    q = rows[rows["consolidated"] == basis].sort_values("period_end")
    quarters = [{"period_end": r.period_end.isoformat(), "revenue": _num(r.net_revenue),
                 "net_profit": _num(r.net_profit), "eps": _num(r.eps, 2),
                 "margin_pct": _num(100 * r.net_profit / r.net_revenue) if r.net_revenue and r.net_revenue > 0
                 and pd.notna(r.net_profit) else None}
                for r in q.tail(QUARTERS).itertuples()]
    q = q.assign(fy=q["period_end"].map(_fiscal_year))
    years = []
    for fy, g in q.groupby("fy"):
        if g["period_end"].nunique() != 4:  # an incomplete year would understate the totals
            continue
        revenue, profit = g["net_revenue"].sum(min_count=4), g["net_profit"].sum(min_count=4)
        years.append({"fiscal_year": int(fy), "revenue": _num(revenue), "net_profit": _num(profit),
                      "margin_pct": _num(100 * profit / revenue) if revenue and revenue > 0 and pd.notna(profit) else None})
    kind = rows["kind"].iloc[-1] if "kind" in rows else "company"
    return {
        "basis": "consolidated" if basis else "standalone",
        "kind": kind,
        "revenue_means": ("net interest income + other income" if kind in ("bank", "finance") else
                          "total income" if kind == "insurance" else "revenue from operations"),
        "quarters": quarters,
        "years": years[-YEARS:],
        "margin_history": margin_history(rows, basis),
        "metrics": {"as_of": latest["as_of"].isoformat(), "net_margin": _num(latest["net_margin"], 2),
                    "revenue_cagr_3yr": _num(latest["revenue_cagr_3yr"], 2), "roe": _num(latest["roe"], 2),
                    "debt_equity": _num(latest["debt_equity"], 3)},
    }


def _reaction_rows(reactions: pd.DataFrame | None, symbol: str) -> list[dict]:
    if reactions is None or not len(reactions):
        return []
    r = reactions[reactions["symbol"] == symbol].sort_values("period_end").tail(results_reaction.SHOWN)
    return [{k: (v.isoformat() if isinstance(v, date) else None if v is None or (isinstance(v, float) and pd.isna(v))
                 else round(v, 2) if isinstance(v, float) else v)
             for k, v in row.items() if k != "symbol"} for row in r.to_dict("records")]


def build(df: pd.DataFrame, today: date | None = None, reactions: pd.DataFrame | None = None) -> dict:
    df = df.copy()
    df["period_end"] = pd.to_datetime(df["period_end"]).dt.date
    if "suspect" in df:
        df = df[~df["suspect"].fillna(False).astype(bool)]
    if "net_revenue" not in df:
        df["net_revenue"] = df["revenue"]
    latest = filing_metrics.latest(df).set_index("symbol").to_dict("index")
    companies = {}
    for symbol, rows in df.groupby("symbol"):
        if symbol not in latest:
            continue
        entry = company(rows, latest[symbol])
        entry["reactions"] = _reaction_rows(reactions, symbol)
        entry["reaction_note"] = results_reaction.note(entry["reactions"])
        companies[symbol] = entry
    return {"generated": (today or date.today()).isoformat(),
            "source": "Company filings with NSE (results to Dec 2024; SEBI integrated filing after)",
            "unit": "₹ crore", "companies": companies}


def write(lake, output: Path = OUTPUT) -> dict:
    results = lake.query("select * from financial_results")
    reactions = None
    present = set(lake.datasets())
    if "index_prices" in present and ("eod_adjusted" in present or "eod_prices" in present):
        symbols = pd.DataFrame({"symbol": sorted(results["symbol"].unique())})
        prices = lake.query("select date, symbol, close from eod_adjusted where series = 'EQ' "
                            "and symbol in (select symbol from wanted)", frames={"wanted": symbols})
        nifty = lake.query("select date, close from index_prices where index = 'NIFTY_50'")
        reactions = results_reaction.reactions(results, prices, nifty)
    doc = build(results, reactions=reactions)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")  # compact: whole market
    return doc
