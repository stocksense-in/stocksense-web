"""
Data checks for the lake's other datasets (prices have their own in eod.check):
row counts, gaps, duplicates, impossible values and staleness — PLAN.md Phase 1's
"validation checks on every one".

    python -m stocksense check-lake

Each check returns a dict of findings plus a list of `problems` (strings). An empty
`problems` list means the dataset looks healthy; the daily runner reports the rest.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .lake import Lake

MAIN_INDICES = ("NIFTY_50", "NIFTY_BANK", "NIFTY_IT", "NIFTY_AUTO", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_METAL")
STALE_AFTER_DAYS = 5  # a daily series whose latest value is older than this is flagged
THIN_DAY_SHARE = 0.3  # a GDELT day with < 30% of its 30-day median events is flagged
CAN_BE_NEGATIVE = ("US10Y", "WTI")


def _gaps(days: pd.Series, max_days: int) -> list[str]:
    d = pd.to_datetime(days).sort_values().reset_index(drop=True)
    gap = d.diff().dt.days
    return [f"{(b - pd.Timedelta(days=int(g))).date()} → {b.date()}" for b, g in zip(d, gap) if g > max_days]


def check_indices(lake: Lake, today: date | None = None) -> dict:
    today = today or date.today()
    q = lake.query
    summary = q("select count(distinct date) as days, min(date) as first, max(date) as last, count(distinct index) as indices "
                "from index_prices").iloc[0]
    days = q("select distinct date from index_prices")["date"]
    dupes = int(q("select count(*) from (select date, index from index_prices group by 1, 2 having count(*) > 1)").iloc[0, 0])
    bad = int(q("select count(*) from index_prices where close <= 0 or low > high").iloc[0, 0])
    main = q("select index, count(*) as days, max(date) as last from index_prices where index in (select i from main) group by index",
             frames={"main": pd.DataFrame({"i": list(MAIN_INDICES)})})
    big = q("""
        with r as (select index, date, close / lag(close) over (partition by index order by date) - 1 as ret
                   from index_prices where index in (select i from main))
        select index, date, ret from r where abs(ret) > 0.15 order by abs(ret) desc
    """, frames={"main": pd.DataFrame({"i": list(MAIN_INDICES)})})
    problems = []
    missing = sorted(set(MAIN_INDICES) - set(main["index"]))
    if missing:
        problems.append(f"main indices missing: {', '.join(missing)}")
    if dupes:
        problems.append(f"{dupes} duplicate (date, index) rows")
    if bad:
        problems.append(f"{bad} rows with close <= 0 or low > high")
    last = pd.Timestamp(summary["last"]).date()
    if (today - last).days > STALE_AFTER_DAYS:
        problems.append(f"latest day {last} is more than {STALE_AFTER_DAYS} days old")
    gaps = _gaps(days, 5)
    if len(gaps) > 3:  # Diwali/holiday weeks give a few
        problems.append(f"{len(gaps)} gaps over 5 days")
    return {
        "days": int(summary["days"]), "first": str(pd.Timestamp(summary["first"]).date()), "last": str(last),
        "indices": int(summary["indices"]), "gaps_over_5_days": gaps[:10], "duplicates": dupes, "bad_rows": bad,
        "main_index_moves_over_15pct": [f"{r.index} {pd.Timestamp(r.date).date()} {r.ret:+.0%}" for r in big.itertuples()][:10],
        "problems": problems,
    }


def check_macro(lake: Lake, today: date | None = None) -> dict:
    today = today or date.today()
    q = lake.query
    # Series that can legitimately be zero or negative: yields, and WTI (settled at −$37.63 on 20 Apr 2020).
    allowed = ", ".join(f"'{s}'" for s in CAN_BE_NEGATIVE)
    per = q("select series, count(*) as days, min(date) as first, max(date) as last, "
            f"count(*) - count(distinct date) as dupes, count(*) filter (where close <= 0 and series not in ({allowed})) as bad "
            "from macro_prices group by series order by series")
    problems = []
    series = {}
    for r in per.itertuples(index=False):
        last = pd.Timestamp(r.last).date()
        series[r.series] = {"days": int(r.days), "first": str(pd.Timestamp(r.first).date()), "last": str(last)}
        if (today - last).days > STALE_AFTER_DAYS:
            problems.append(f"{r.series} latest value {last} is stale")
        if r.dupes:
            problems.append(f"{r.series}: {int(r.dupes)} duplicate days")
        if r.bad:
            problems.append(f"{r.series}: {int(r.bad)} non-positive closes")
    return {"series": series, "problems": problems}


def check_gdelt(lake: Lake, today: date | None = None) -> dict:
    today = today or date.today()
    q = lake.query
    daily = q("select date, sum(events) as events from gdelt_daily group by date order by date")
    daily["date"] = pd.to_datetime(daily["date"])
    median = daily["events"].rolling(30, min_periods=10, center=True).median()
    thin = daily.loc[daily["events"] < THIN_DAY_SHARE * median, "date"].dt.date.astype(str).tolist()
    expected = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    missing = sorted(str(d.date()) for d in set(expected) - set(daily["date"]))
    salient = int(q("select count(*) from gdelt_events").iloc[0, 0]) if "gdelt_events" in lake.datasets() else 0
    last = daily["date"].max().date()
    problems = []
    if (today - last).days > STALE_AFTER_DAYS:
        problems.append(f"latest GDELT day {last} is stale")
    if len(missing) > 60:  # GDELT itself skipped a few dozen days in 2013–2014
        problems.append(f"{len(missing)} calendar days missing")
    return {
        "days": int(len(daily)), "first": str(daily["date"].min().date()), "last": str(last),
        "events": int(daily["events"].sum()), "salient_events": salient,
        "missing_days": missing[:15] + ([f"… {len(missing) - 15} more"] if len(missing) > 15 else []),
        "thin_days": thin[:15], "problems": problems,
    }


def check_fno(lake: Lake, today: date | None = None) -> dict:
    today = today or date.today()
    q = lake.query
    per_day = q("select date, count(*) as underlyings, "
                "count(*) filter (where symbol in ('NIFTY', 'BANKNIFTY')) as main_indices "
                "from fno_summary group by date order by date")
    per_day["date"] = pd.to_datetime(per_day["date"])
    dupes = int(q("select count(*) from (select date, symbol from fno_summary group by 1, 2 having count(*) > 1)").iloc[0, 0])
    odd_pcr = int(q("select count(*) from fno_summary where symbol in ('NIFTY', 'BANKNIFTY') "
                    "and (pcr_oi <= 0.1 or pcr_oi >= 5)").iloc[0, 0])
    missing_main = per_day.loc[per_day["main_indices"] < 2, "date"].dt.date.astype(str).tolist()
    last = per_day["date"].max().date()
    problems = []
    if (today - last).days > STALE_AFTER_DAYS:
        problems.append(f"latest F&O day {last} is stale")
    if dupes:
        problems.append(f"{dupes} duplicate (date, symbol) summary rows")
    if missing_main:
        problems.append(f"NIFTY or BANKNIFTY missing on {len(missing_main)} days")
    if odd_pcr:
        problems.append(f"{odd_pcr} NIFTY/BANKNIFTY days with put/call OI ratio outside 0.1–5")
    return {
        "days": int(len(per_day)), "first": str(per_day["date"].min().date()), "last": str(last),
        "underlyings_per_day": {k: int(v) for k, v in per_day["underlyings"].describe()[["min", "50%", "max"]].items()},
        "days_missing_nifty_or_banknifty": missing_main[:10], "duplicates": dupes, "problems": problems,
    }


def check_filings(lake: Lake, today: date | None = None) -> dict:
    """Announcements must be fresh; insider trades are reported, not failed (NSE's feed stops in ~Mar 2026)."""
    today = today or date.today()
    q = lake.query
    present = set(lake.datasets())
    ann = q("select date, count(*) as n from announcements group by date order by date")
    ann["date"] = pd.to_datetime(ann["date"])
    dupes = int(q("select count(*) from (select seq_id, symbol from announcements group by 1, 2 having count(*) > 1)").iloc[0, 0])
    last = ann["date"].max().date()
    problems = []
    if (today - last).days > STALE_AFTER_DAYS:
        problems.append(f"latest announcement {last} is stale")
    if dupes:
        problems.append(f"{dupes} duplicate announcements")
    out = {
        "announcement_days": int(len(ann)), "first": str(ann["date"].min().date()), "last": str(last),
        "announcements": int(ann["n"].sum()), "per_day_median": int(ann["n"].median()), "duplicates": dupes,
    }
    if "insider_trades" in present:
        ins = q("select count(*) as n, min(date) as first, max(date) as last from insider_trades").iloc[0]
        out["insider_trades"] = {"rows": int(ins["n"]), "first": str(pd.Timestamp(ins["first"]).date()),
                                 "last": str(pd.Timestamp(ins["last"]).date())}
    if "fii_dii" in present:
        out["fii_dii_days"] = int(q("select count(distinct date) from fii_dii").iloc[0, 0])
    out["problems"] = problems
    return out


CHECKS = {"index_prices": check_indices, "macro_prices": check_macro, "gdelt_daily": check_gdelt,
          "fno_summary": check_fno, "announcements": check_filings}


def check_all(lake: Lake, today: date | None = None) -> dict[str, dict]:
    """Run every check whose dataset exists. Keys are dataset names."""
    present = set(lake.datasets())
    return {name: fn(lake, today) for name, fn in CHECKS.items() if name in present}
