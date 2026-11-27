"""
Prospectus model (M3.7): which red flags in a red herring prospectus actually preceded weak
IPOs, judged on later issues.

    backend/.venv-ml/Scripts/python.exe ml/ipo_flags.py

Inputs (the lake): ipo_prospectus (each mainboard IPO's prospectus scanned with the rules in
backend/stocksense/rhp.py; `python -m stocksense ingest-rhp`), eod_adjusted and NIFTY 50.

Outcomes per IPO, from our own price history (followed by ISIN, so renames don't break it):
  listing_gain   listing-day close over the issue price, minus one (what the allotment made on day one)
  excess_3m/6m/12m  return from the listing-day close over 63 / 126 / 252 sessions, minus NIFTY 50's
                 over the same days (adjusted prices): how the company did once the listing pop was over
  weak           excess_6m below -10%: the six months after listing went clearly worse than the market

Judged three ways:
  1. Each rule alone: flagged IPOs against clear ones, difference in median six-month excess with a
     bootstrap 95% interval, and the share that turned out weak.
  2. All rules together, a logistic regression fitted on IPOs listed before 2023 and scored on
     2023 onwards by AUC (0.5 = no better than chance), against the checker's current score (the
     number of high and medium findings a user sees) and a model with listing gain alone.
  3. Per rule, a plain verdict for the checker: "worse" when flagged IPOs did worse and the
     interval excludes zero, "no clear difference" otherwise.

Writes ml/reports/ipo-flags-<date>.md and backend/data/rhp_evidence.json (read by rhp.py, which
shows each finding's track record).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense import rhp  # noqa: E402
from stocksense.lake import Lake  # noqa: E402

HORIZONS = {"excess_3m": 63, "excess_6m": 126, "excess_12m": 252}
WEAK = -0.10
SPLIT = pd.Timestamp("2023-01-01")
LEVEL = {"low": 1, "medium": 2, "high": 3}
BOOTSTRAP = 4000
SEED = 7
EVIDENCE = REPO / "backend" / "data" / "rhp_evidence.json"


def load(lake: Lake) -> pd.DataFrame:
    ipos = lake.query("select * from ipo_prospectus where pages > 0")
    ipos["listing_date"] = pd.to_datetime(ipos["listing_date"])
    first = lake.query(
        "select e.symbol, e.traded_symbol, e.isin, e.date, e.close_traded from eod_adjusted e "
        "join (select symbol, listing_date from ipo_prospectus where pages > 0) i "
        "on e.traded_symbol = i.symbol and e.date between i.listing_date and i.listing_date + interval 10 day "
        "where e.series in ('EQ', 'BE') qualify row_number() over (partition by e.traded_symbol order by e.date) = 1")
    first = first.rename(columns={"traded_symbol": "ipo_symbol", "date": "first_day", "close_traded": "first_close"})
    df = ipos.merge(first[["ipo_symbol", "isin", "first_day", "first_close"]], left_on="symbol", right_on="ipo_symbol",
                    how="left")
    df["listing_gain"] = df["first_close"] / df["issue_price"] - 1

    isins = pd.DataFrame({"isin": df["isin"].dropna().unique()})
    prices = lake.query("select isin, date, close from eod_adjusted where isin in (select isin from wanted) "
                        "and series in ('EQ', 'BE') order by isin, date", frames={"wanted": isins})
    nifty = lake.query("select date, close from index_prices where index = 'NIFTY_50' order by date")
    nifty = nifty.assign(date=pd.to_datetime(nifty["date"])).set_index("date")["close"]
    prices["date"] = pd.to_datetime(prices["date"])
    by_isin = {k: g.set_index("date")["close"] for k, g in prices.groupby("isin")}
    for name, sessions in HORIZONS.items():
        values = []
        for r in df.itertuples():
            s = by_isin.get(r.isin)
            if s is None or pd.isna(r.first_day):
                values.append(np.nan)
                continue
            s = s[s.index >= pd.Timestamp(r.first_day)]
            if len(s) <= sessions:
                values.append(np.nan)  # not enough history yet
                continue
            d0, d1 = s.index[0], s.index[sessions]
            n = nifty.reindex([d0, d1], method="ffill")
            values.append(s.iloc[sessions] / s.iloc[0] - (n.iloc[1] / n.iloc[0]))
        df[name] = values
    # market mood at listing: NIFTY 50 over the 63 sessions before the first trading day
    before = []
    for r in df.itertuples():
        if pd.isna(r.first_day):
            before.append(np.nan)
            continue
        past = nifty[nifty.index < pd.Timestamp(r.first_day)]
        before.append(past.iloc[-1] / past.iloc[-64] - 1 if len(past) > 64 else np.nan)
    df["nifty_3m_before"] = before
    df["weak"] = df["excess_6m"] < WEAK
    for rule in rhp.RULES:
        df[f"lvl_{rule.id}"] = df[rule.id].map(LEVEL).fillna(0).astype(int)
        df[f"is_{rule.id}"] = (df[f"lvl_{rule.id}"] >= 2).astype(int)  # medium or high; low is a "check the chapter" hint
    df["shown_score"] = sum((df[f"lvl_{r.id}"] >= 2).astype(int) for r in rhp.RULES)  # high + medium findings
    return df


def bootstrap_diff(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    """Median(a) - median(b) and its percentile bootstrap 95% interval. Medians, because IPO returns are
    heavily skewed: a few multibaggers swing a mean (customer concentration's mean said "better" while
    its median said "worse")."""
    diffs = np.array([np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))) for _ in range(BOOTSTRAP)])
    return float(np.median(a) - np.median(b)), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def per_rule(df: pd.DataFrame, outcome: str = "excess_6m") -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    d = df.dropna(subset=[outcome])
    rows = []
    for rule in rhp.RULES:
        flagged, clear = d[d[f"is_{rule.id}"] == 1], d[d[f"is_{rule.id}"] == 0]
        row = {"rule": rule.id, "title": rule.title, "flagged": len(flagged), "clear": len(clear)}
        if len(flagged) >= 10 and len(clear) >= 10:
            diff, lo, hi = bootstrap_diff(flagged[outcome].to_numpy(), clear[outcome].to_numpy(), rng)
            row.update({"mean_flagged": flagged[outcome].mean(), "mean_clear": clear[outcome].mean(),
                        "median_flagged": flagged[outcome].median(), "median_clear": clear[outcome].median(),
                        "weak_flagged": flagged["weak"].mean(), "weak_clear": clear["weak"].mean(),
                        "diff": diff, "lo": lo, "hi": hi,
                        "verdict": "worse" if hi < 0 else "better" if lo > 0 else "no clear difference"})
        else:
            row["verdict"] = "too few to judge"
        rows.append(row)
    return pd.DataFrame(rows)


def auc(y: np.ndarray, score: np.ndarray) -> float:
    """Probability a weak IPO scores higher than a non-weak one (ties count half)."""
    pos, neg = score[y == 1], score[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(greater / (len(pos) * len(neg)))


def auc_ci(y: np.ndarray, score: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    vals = []
    for _ in range(1000):
        i = rng.integers(0, len(y), len(y))
        vals.append(auc(y[i], score[i]))
    vals = np.array([v for v in vals if not np.isnan(v)])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def model(df: pd.DataFrame) -> dict:
    from sklearn.linear_model import LogisticRegression

    d = df.dropna(subset=["excess_6m", "listing_gain", "nifty_3m_before"]).copy()
    # litigation summary as numbers: amount at stake against net worth (capped), any criminal case
    def col(name: str) -> pd.Series:
        return pd.to_numeric(d[name], errors="coerce") if name in d else pd.Series(np.nan, index=d.index)

    d["lit_share_f"] = col("lit_share").fillna(0).clip(upper=1.0)
    d["lit_criminal_f"] = (col("lit_criminal").fillna(0) > 0).astype(int)
    train, test = d[d["listing_date"] < SPLIT], d[d["listing_date"] >= SPLIT]
    flags = [f"is_{r.id}" for r in rhp.RULES]
    rng = np.random.default_rng(SEED)
    out = {"train": len(train), "test": len(test), "weak_train": float(train["weak"].mean()),
           "weak_test": float(test["weak"].mean()), "rows": []}
    y = test["weak"].astype(int).to_numpy()

    def add(name: str, score: np.ndarray) -> None:
        lo, hi = auc_ci(y, score, rng)
        out["rows"].append({"model": name, "auc": auc(y, score), "lo": lo, "hi": hi})

    add("Checker's current score (high + medium findings)", test["shown_score"].to_numpy().astype(float))
    for name, cols in [("Rules together (logistic regression)", flags),
                       ("Listing-day gain alone", ["listing_gain"]),
                       ("Rules + listing-day gain", flags + ["listing_gain"]),
                       ("Market mood alone (NIFTY 3 months before listing)", ["nifty_3m_before"]),
                       ("Rules + listing-day gain + market mood", flags + ["listing_gain", "nifty_3m_before"]),
                       ("Litigation numbers alone (amount vs net worth, criminal cases)", ["lit_share_f", "lit_criminal_f"])]:
        m = LogisticRegression(C=0.5, max_iter=2000).fit(train[cols], train["weak"].astype(int))
        add(name, m.predict_proba(test[cols])[:, 1])
        if name == "Rules together (logistic regression)":
            out["weights"] = dict(zip([c[3:] for c in cols], [float(w) for w in m.coef_[0]]))
    return out


def evidence(rules: pd.DataFrame, n_ipos: int, since: str, until: str, listing: pd.DataFrame | None = None) -> dict:
    out = {"as_of": date.today().isoformat(), "ipos": n_ipos, "listed_from": since, "listed_to": until,
           "outcome": "return over the six months after listing, minus NIFTY 50's", "rules": {}}
    for r in rules.itertuples():
        entry = {"flagged": int(r.flagged), "clear": int(r.clear), "verdict": r.verdict}
        if r.verdict != "too few to judge":
            entry.update({"median_flagged": round(float(r.median_flagged), 4), "median_clear": round(float(r.median_clear), 4),
                          "weak_flagged": round(float(r.weak_flagged), 3), "weak_clear": round(float(r.weak_clear), 3),
                          "diff": round(float(r.diff), 4), "lo": round(float(r.lo), 4), "hi": round(float(r.hi), 4)})
        out["rules"][r.rule] = entry
    for r in (listing.itertuples() if listing is not None else ()):
        if r.rule in out["rules"] and r.verdict != "too few to judge":
            out["rules"][r.rule]["listing"] = {"flagged": int(r.flagged), "verdict": r.verdict, "diff": round(float(r.diff), 4),
                                               "lo": round(float(r.lo), 4), "hi": round(float(r.hi), 4)}
    return out


def pct(x: float) -> str:
    return "–" if pd.isna(x) else f"{100 * x:+.1f}%"


def report(df: pd.DataFrame, rules: pd.DataFrame, listing: pd.DataFrame, fit: dict) -> str:
    judged = df.dropna(subset=["excess_6m"])
    lines = [f"# Prospectus red flags and IPO outcomes — {date.today():%d %b %Y}", "",
             f"{len(df)} mainboard IPOs listed {df['listing_date'].min():%b %Y} – {df['listing_date'].max():%b %Y} whose "
             f"red herring prospectus is on SEBI's site were scanned with the {len(rhp.RULES)} rules of the prospectus "
             f"checker (`backend/stocksense/rhp.py`). {len(judged)} have six months of trading to judge.", "",
             f"Median listing-day gain {pct(df['listing_gain'].median())}; median six-month excess return after "
             f"listing {pct(judged['excess_6m'].median())}; {judged['weak'].mean():.0%} were weak (six months more than "
             f"10 points behind NIFTY 50).", "",
             "## Each rule alone (six months after listing, against NIFTY 50)", "",
             "| Rule | Flagged | Clear | Median flagged | Median clear | Weak if flagged | Weak if clear | Difference in medians (95% CI) | Verdict |",
             "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in rules.itertuples():
        if r.verdict == "too few to judge":
            lines.append(f"| {r.title} | {r.flagged} | {r.clear} | | | | | | too few to judge |")
            continue
        lines.append(f"| {r.title} | {r.flagged} | {r.clear} | {pct(r.median_flagged)} | {pct(r.median_clear)} | "
                     f"{r.weak_flagged:.0%} | {r.weak_clear:.0%} | {pct(r.diff)} ({pct(r.lo)} to {pct(r.hi)}) | {r.verdict} |")
    lines += ["", "## Each rule alone, listing day (close against the issue price)", "",
              "| Rule | Flagged | Difference in medians (95% CI) | Verdict |", "|---|---:|---|---|"]
    for r in listing.itertuples():
        if r.verdict == "too few to judge":
            continue
        lines.append(f"| {r.title} | {r.flagged} | {pct(r.diff)} ({pct(r.lo)} to {pct(r.hi)}) | {r.verdict} |")
    lines += ["", "## All rules together, judged on later IPOs", "",
              f"Fitted on {fit['train']} IPOs listed before {SPLIT:%b %Y} ({fit['weak_train']:.0%} weak), scored on "
              f"{fit['test']} listed since ({fit['weak_test']:.0%} weak). AUC is the chance a weak IPO scores higher than "
              "one that wasn't; 0.5 is a coin toss.", "",
              "| Score | AUC on later IPOs (95% CI) |", "|---|---|"]
    for r in fit["rows"]:
        lines.append(f"| {r['model']} | {r['auc']:.2f} ({r['lo']:.2f} to {r['hi']:.2f}) |")
    lines += ["", "Weights the regression gave each flag (positive = more likely weak):", ""]
    for k, w in sorted(fit.get("weights", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- {k}: {w:+.2f}")
    return "\n".join(lines) + "\n"


def main() -> None:
    lake = Lake.from_settings()
    df = load(lake)
    rules = per_rule(df, "excess_6m")
    listing = per_rule(df, "listing_gain")
    fit = model(df)
    out = REPO / "ml" / "reports" / f"ipo-flags-{date.today():%Y-%m-%d}.md"
    out.write_text(report(df, rules, listing, fit), encoding="utf-8")
    judged = df.dropna(subset=["excess_6m"])
    EVIDENCE.write_text(json.dumps(evidence(rules, len(judged), f"{judged['listing_date'].min():%Y-%m}",
                                            f"{judged['listing_date'].max():%Y-%m}", listing), indent=1), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
