"""
M1.2 acceptance check: revenue and profit from NSE filings vs published annual results.

    backend\\.venv\\Scripts\\python ml\\checks\\results_spot_check.py      # from the repo root

For each company in clean/financial_results, the four quarters of FY2023–FY2026
(April–March) are summed — consolidated if all four quarters have consolidated figures,
else standalone, never a mix — and compared with Yahoo's annual income statement
("Total Revenue", "Net Income": consolidated, owners' share). Revenue is `net_revenue`:
for banks, net interest income + other income, which is what Yahoo calls total revenue.
Quarters flagged `suspect` (filing errors) are left out. Not judged, only shown: years
where we only have standalone figures (Yahoo is consolidated), bank revenue (consolidated "other income" includes insurance subsidiaries' premiums, which
Yahoo leaves out — profit is still judged), and companies whose Yahoo statements are not
in rupees (Infosys reports in USD there). Prints a table; exits non-zero if fewer than
80% of judged comparisons are within 2%.
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from stocksense.lake import Lake  # noqa: E402

YEARS = (2023, 2024, 2025, 2026)  # FY ending 31 Mar; FY2025 joins the old feed and integrated filings
TOLERANCE = 0.02


def fy_sums(df: pd.DataFrame, fy: int) -> pd.DataFrame:
    """Sum of the four quarters Apr (fy-1) – Mar fy on one basis, for companies with all four."""
    q = df[(df["period_end"] > date(fy - 1, 3, 31)) & (df["period_end"] <= date(fy, 3, 31))]
    g = q.groupby(["symbol", "consolidated"]).agg(quarters=("period_end", "nunique"), revenue=("net_revenue", "sum"),
                                                  net_profit=("net_profit", "sum")).reset_index()
    g = g[g["quarters"] == 4].sort_values("consolidated")  # consolidated last → kept
    return g.drop_duplicates("symbol", keep="last").set_index("symbol")


def yahoo_annual(symbol: str) -> pd.DataFrame | None:
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        stmt = ticker.income_stmt
        currency = ticker.info.get("financialCurrency", "INR")
    except Exception:  # noqa: BLE001 — Yahoo hiccup: skip this company
        return None
    if stmt is None or stmt.empty or currency != "INR":
        if currency != "INR":
            print(f"{symbol}: Yahoo statements in {currency}, not compared")
        return None
    out = {}
    for col in stmt.columns:
        fy = col.year if col.month <= 3 else col.year + 1
        out[fy] = {"revenue": stmt.at["Total Revenue", col] / 1e7 if "Total Revenue" in stmt.index else None,
                   "net_profit": stmt.at["Net Income", col] / 1e7 if "Net Income" in stmt.index else None}
    return pd.DataFrame(out).T


def main() -> int:
    lake = Lake.from_settings()
    df = lake.query("select * from financial_results")
    df["period_end"] = pd.to_datetime(df["period_end"]).dt.date
    if "suspect" in df:
        df = df[~df["suspect"].fillna(False).astype(bool)]
    banks = set(df.loc[df["bank"].fillna(False).astype(bool), "symbol"])
    ours = {fy: fy_sums(df, fy) for fy in YEARS}
    rows = []
    for symbol in sorted(df["symbol"].unique()):
        y = yahoo_annual(symbol)
        time.sleep(0.5)
        for fy in YEARS:
            if y is None or fy not in y.index or symbol not in ours[fy].index:
                continue
            for metric in ("revenue", "net_profit"):
                theirs, mine = y.at[fy, metric], ours[fy].at[symbol, metric]
                if theirs and pd.notna(theirs) and pd.notna(mine):
                    basis = "cons" if ours[fy].at[symbol, "consolidated"] else "standalone"
                    rows.append({"symbol": symbol, "fy": fy, "basis": basis, "metric": metric, "ours_cr": round(mine),
                                 "yahoo_cr": round(theirs), "diff_pct": round(100 * (mine / theirs - 1), 1),
                                 # Yahoo is consolidated; bank revenue has no shared definition.
                                 "judged": basis == "cons" and not (metric == "revenue" and symbol in banks)})
    out = pd.DataFrame(rows)
    if out.empty:
        print("No overlapping years to compare.")
        return 1
    out["ok"] = out["diff_pct"].abs() <= TOLERANCE * 100
    with pd.option_context("display.width", 140, "display.max_rows", 200):
        print(out.to_string(index=False))
    judged = out[out["judged"]]
    share = judged["ok"].mean()
    print(f"\n{judged['ok'].sum()} of {len(judged)} judged comparisons within {TOLERANCE:.0%} ({share:.0%}); "
          f"{out['symbol'].nunique()} companies, FY{YEARS[0]}–FY{YEARS[-1]}")
    for metric in ("revenue", "net_profit"):
        m = judged[judged["metric"] == metric]
        print(f"  {metric}: {m['ok'].sum()} of {len(m)}")
    return 0 if share >= 0.8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
