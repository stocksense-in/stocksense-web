"""
Experiment: can daily macro and news features predict next-day sector moves
versus NIFTY 50? A gradient-boosted model (LightGBM), judged by PLAN.md §6.

    backend\\.venv-ml\\Scripts\\python ml\\sector_gbm.py            # from the repo root

Panel: one row per (market day t, NSE sector index). Target, in percent, either
  • next_day:      sector minus NIFTY 50, Indian close t → close t+1 (includes the overnight gap)
  • open_to_close: sector minus NIFTY 50, Indian open t+1 → close t+1 (the part tradable after the news)

What the model may know before the Indian open on t+1:
  • macro closes of day t (US markets close ~02:00 IST, before the Indian open)
  • GDELT up to day t-1 only: the day-t file is published ~15:30 IST on t+1, after the session
  • Indian market data up to close t

Walk-forward: for each test year Y, train on every earlier year, test on Y. Baselines:
zero (no excess move), each sector's trailing mean, and yesterday's excess move
(momentum). Metrics: daily cross-sectional rank correlation (IC), sign hit rate,
out-of-sample R² against the zero forecast, and a top-3 minus bottom-3 spread.
The keyword rules in geo.py can't be backtested (no headline archive), so they
aren't a baseline here.

Writes ml/reports/sector-gbm-<date>.md and the final model + feature importance to
the lake under models/sector_gbm/<date>/.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense.jobs import event_study as job  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

SEED = 7
FIRST_TEST_YEAR = 2016
PARAMS = dict(objective="regression", learning_rate=0.03, n_estimators=400, num_leaves=15,
              min_child_samples=300, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
              reg_lambda=1.0, random_state=SEED, verbose=-1)


def load_panel(lake: Lake) -> tuple[pd.DataFrame, list[str]]:
    codes = list(job.INDEX_SECTORS.values()) + [job.BENCHMARK, "INDIA_VIX"]
    raw = lake.query("select date, index, open, close from index_prices where index in (select c from codes)",
                     frames={"codes": pd.DataFrame({"c": codes})})
    raw["date"] = pd.to_datetime(raw["date"])
    close = raw.pivot_table(index="date", columns="index", values="close", aggfunc="last").sort_index()
    open_ = raw.pivot_table(index="date", columns="index", values="open", aggfunc="last").sort_index()
    cal = close[job.BENCHMARK].dropna().index
    close, open_ = close.reindex(cal), open_.reindex(cal)
    bench_c, bench_o = close[job.BENCHMARK], open_[job.BENCHMARK]

    # Market-wide features known at close t.
    inputs = job.load_inputs(lake)
    macro = pd.DataFrame(index=cal)

    def asof(series: pd.Series, lag_days: int = 0) -> pd.Series:
        s = series.dropna().sort_index()
        if lag_days:
            s.index = s.index + pd.Timedelta(days=lag_days)
        return s.reindex(cal, method="ffill")

    for name, col, kind in [("brent", "BRENT", "pct"), ("usdinr", "USDINR", "pct"), ("sp500", "SP500", "pct"),
                            ("gold", "GOLD", "pct"), ("dxy", "DXY", "pct"), ("us10y", "US10Y", "diff")]:
        s = inputs[col].dropna()
        one = s.pct_change() if kind == "pct" else s.diff()
        macro[f"{name}_1d"] = asof(one)
        macro[f"{name}_5d"] = asof(s.pct_change(5) if kind == "pct" else s.diff(5))
    macro["us_vix"] = asof(inputs["US_VIX"])
    macro["us_vix_1d"] = asof(inputs["US_VIX"].pct_change())
    for col in ("conflict_share", "india_border_share", "mideast_share", "sanctions_share"):
        if col in inputs:
            s = inputs[col]
            past = s.shift(1).rolling(90, min_periods=60)
            macro[f"{col}_z"] = asof((s - past.mean()) / past.std(), lag_days=1)  # day t-1's file
    macro["india_vix"] = close["INDIA_VIX"]
    macro["india_vix_1d"] = close["INDIA_VIX"].pct_change(fill_method=None)
    macro["nifty_1d"] = bench_c.pct_change(fill_method=None)
    macro["nifty_5d"] = bench_c.pct_change(5, fill_method=None)

    rows = []
    for sector, code in job.INDEX_SECTORS.items():
        if code not in close:
            continue
        c, o = close[code], open_[code]
        excess = (c.pct_change(fill_method=None) - bench_c.pct_change(fill_method=None)) * 100
        df = macro.copy()
        df["sector"] = sector
        df["excess_1d"] = excess
        df["excess_5d"] = (c.pct_change(5, fill_method=None) - bench_c.pct_change(5, fill_method=None)) * 100
        df["excess_20d"] = (c.pct_change(20, fill_method=None) - bench_c.pct_change(20, fill_method=None)) * 100
        df["next_day"] = excess.shift(-1)
        df["open_to_close"] = ((c / o - 1) - (bench_c / bench_o - 1)).shift(-1) * 100
        df["trailing_mean"] = excess.expanding(min_periods=60).mean()
        rows.append(df)
    panel = pd.concat(rows).reset_index(names="date")
    panel["sector"] = panel["sector"].astype("category")
    features = [c for c in panel.columns if c not in ("date", "next_day", "open_to_close", "trailing_mean")]
    return panel, features


def daily_ic(df: pd.DataFrame, pred: str, target: str) -> pd.Series:
    def ic(g):
        if g[pred].nunique() < 3:
            return np.nan
        return g[pred].rank().corr(g[target].rank())
    return df.groupby("date").apply(ic, include_groups=False).dropna()


def evaluate(df: pd.DataFrame, pred: str, target: str) -> dict:
    ok = df[[pred, target]].notna().all(axis=1)
    d = df[ok]
    ics = daily_ic(d, pred, target)
    sse = ((d[target] - d[pred]) ** 2).sum()
    sse0 = (d[target] ** 2).sum()
    nonzero = d[d[target] != 0]
    spread = d.groupby("date").apply(
        lambda g: g.nlargest(3, pred)[target].mean() - g.nsmallest(3, pred)[target].mean()
        if g[pred].nunique() >= 6 else np.nan, include_groups=False).dropna()
    return {
        "rows": int(len(d)),
        "ic_mean": round(float(ics.mean()), 4) if len(ics) else None,
        "ic_t": round(float(ics.mean() / ics.std() * np.sqrt(len(ics))), 2) if len(ics) > 2 else None,
        "hit_rate": round(float((np.sign(nonzero[pred]) == np.sign(nonzero[target])).mean()), 4),
        "r2_vs_zero": round(float(1 - sse / sse0), 5),
        "top3_minus_bottom3_pct": round(float(spread.mean()), 4) if len(spread) else None,
    }


def walk_forward(panel: pd.DataFrame, features: list[str], target: str) -> tuple[pd.DataFrame, list[dict]]:
    data = panel.dropna(subset=[target])
    years = sorted(y for y in data["date"].dt.year.unique() if y >= FIRST_TEST_YEAR)
    preds, per_year = [], []
    for y in years:
        train = data[data["date"].dt.year < y]
        test = data[data["date"].dt.year == y].copy()
        if len(train) < 5000 or test.empty:
            continue
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(train[features], train[target])
        test["model"] = model.predict(test[features])
        test["momentum"] = test["excess_1d"]
        preds.append(test)
        per_year.append({"year": int(y), "train_rows": int(len(train)), **evaluate(test, "model", target)})
    return pd.concat(preds), per_year


def report(results: dict, out: Path, data_range: tuple[str, str], importance: pd.Series) -> None:
    lines = [
        f"# Sector GBM experiment — {date.today()}",
        "",
        "Can daily macro and news features predict next-day sector moves versus NIFTY 50?",
        "Gradient-boosted trees (LightGBM), walk-forward by year (train on all earlier years,",
        f"test on the next). Data {data_range[0]} → {data_range[1]}; {len(job.INDEX_SECTORS)} NSE sector indices.",
        "Code: `ml/sector_gbm.py`. Timing rules are in its docstring (GDELT lagged one extra day).",
        "",
        "Metrics: **IC** = average daily rank correlation between forecast and outcome across",
        "sectors (t-stat over days); **hit** = sign accuracy; **R²** vs forecasting zero;",
        "**spread** = average next-day excess return of the top-3 minus bottom-3 forecast sectors (%).",
        "",
    ]
    for target, r in results.items():
        if target == "ablation":
            continue
        lines += [f"## Target: `{target}`", "", "| Forecast | IC | IC t | Hit | R² vs zero | Spread % |", "|---|---|---|---|---|---|"]
        for name, m in r["overall"].items():
            lines.append(f"| {name} | {m['ic_mean']} | {m['ic_t']} | {m['hit_rate']} | {m['r2_vs_zero']} | {m['top3_minus_bottom3_pct']} |")
        lines += ["", "Model by test year:", "", "| Year | IC | Hit | R² vs zero | Spread % |", "|---|---|---|---|---|"]
        for y in r["by_year"]:
            lines.append(f"| {y['year']} | {y['ic_mean']} | {y['hit_rate']} | {y['r2_vs_zero']} | {y['top3_minus_bottom3_pct']} |")
        pos = sum(1 for y in r["by_year"] if (y["ic_mean"] or 0) > 0)
        lines += ["", f"IC positive in {pos} of {len(r['by_year'])} test years.", ""]
    if "ablation" in results:
        lines += ["## Where the signal comes from (ablation, same model, nested feature sets)", "",
                  "| Features | Target | IC | IC t | Hit | Spread % |", "|---|---|---|---|---|---|"]
        for key, m in results["ablation"].items():
            name, target = key.split(" | ")
            lines.append(f"| {name} | `{target}` | {m['ic_mean']} | {m['ic_t']} | {m['hit_rate']} | {m['top3_minus_bottom3_pct']} |")
        lines.append("")
    lines += ["## Most used features (final `next_day` model, split gain)", ""]
    lines += [f"- `{k}`: {v:.0f}" for k, v in importance.head(12).items()]
    lines += ["", "## Reading this", "", "_Fill in by hand after looking at the numbers._", ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    lake = Lake.from_settings()
    panel, features = load_panel(lake)
    data_range = (str(panel["date"].min().date()), str(panel["date"].max().date()))
    print(f"panel: {len(panel)} rows, {len(features)} features, {data_range}")
    results = {}
    for target in ("next_day", "open_to_close"):
        preds, by_year = walk_forward(panel, features, target)
        overall = {name: evaluate(preds, name, target) for name in ("model", "trailing_mean", "momentum")}
        overall["zero"] = {"rows": overall["model"]["rows"], "ic_mean": None, "ic_t": None, "hit_rate": None,
                           "r2_vs_zero": 0.0, "top3_minus_bottom3_pct": None}
        results[target] = {"overall": overall, "by_year": by_year}
        print(target, json.dumps(overall["model"]), "| trailing:", overall["trailing_mean"]["ic_mean"],
              "| momentum:", overall["momentum"]["ic_mean"])

    # Ablation: where does the signal come from? Same model, nested feature sets.
    gdelt = [f for f in features if f.endswith("_share_z")]
    market = ["sector", "excess_1d", "excess_5d", "excess_20d", "nifty_1d", "nifty_5d", "india_vix", "india_vix_1d"]
    macro = [f for f in features if f not in market and f not in gdelt]
    ablation = {}
    for name, cols in (("market only", market), ("+ macro", market + macro), ("+ macro + GDELT", features)):
        for target in ("next_day", "open_to_close"):
            preds, _ = walk_forward(panel, cols, target)
            ablation[(name, target)] = evaluate(preds, "model", target)
            print("ablation", name, target, ablation[(name, target)]["ic_mean"], ablation[(name, target)]["ic_t"])
    results["ablation"] = {f"{n} | {t}": m for (n, t), m in ablation.items()}

    final = lgb.LGBMRegressor(**PARAMS).fit(panel.dropna(subset=["next_day"])[features],
                                            panel.dropna(subset=["next_day"])["next_day"])
    importance = pd.Series(final.booster_.feature_importance("gain"), index=features).sort_values(ascending=False)
    folder = lake.model_dir("sector_gbm", str(date.today()))
    final.booster_.save_model(str(folder / "model.txt"))
    (folder / "metrics.json").write_text(json.dumps({"data": data_range, "features": features, "params": PARAMS,
                                                     "results": results}, indent=1), encoding="utf-8")
    out = REPO / "ml" / "reports" / f"sector-gbm-{date.today()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    report(results, out, data_range, importance)
    print(f"report: {out}\nmodel: {folder}")


if __name__ == "__main__":
    main()
