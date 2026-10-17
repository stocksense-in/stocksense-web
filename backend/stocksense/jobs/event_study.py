"""
Event study job — runs stocksense/event_study.py on the lake's history and
publishes the result.

    python -m stocksense event-study

Inputs (all from the lake): clean/index_prices (NSE sector indices), clean/eod_adjusted
via stocksense/eod.py (baskets for sectors without an index), clean/macro_prices
(crude, rupee, US markets, gold) and clean/gdelt_daily / gdelt_events (news signals
and evidence links).

Outputs:
  • clean/geo_analogues    one row per event type × sector × horizon
  • clean/geo_event_dates  every counted occurrence
  • backend/data/geo_analogues.json — the publishable summary the API serves
    (/geopolitics/analogues), so the public API never needs this machine.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .. import eod, event_study
from ..config import DATA_DIR
from ..lake import Lake
from ..log import get_logger
from ..sources.gdelt import CONFLICT_ROOTS

log = get_logger(__name__)

OUTPUT = DATA_DIR / "geo_analogues.json"
BENCHMARK = "NIFTY_50"

# Display names follow stocksense/geo.py where the sector exists there.
INDEX_SECTORS = {
    "Banking": "NIFTY_BANK", "PSU Banks": "NIFTY_PSU_BANK", "Financial Services": "NIFTY_FINANCIAL_SERVICES",
    "IT Services": "NIFTY_IT", "Pharma": "NIFTY_PHARMA", "Automobile": "NIFTY_AUTO",
    "Metals & Materials": "NIFTY_METAL", "Energy": "NIFTY_ENERGY", "FMCG": "NIFTY_FMCG",
    "Real Estate": "NIFTY_REALTY", "Media": "NIFTY_MEDIA", "Infrastructure": "NIFTY_INFRASTRUCTURE",
    "PSU Companies": "NIFTY_PSE", "Commodities": "NIFTY_COMMODITIES", "Consumption": "NIFTY_INDIA_CONSUMPTION",
    "Midcaps": "NIFTY_MIDCAP_100", "Smallcaps": "NIFTY_SMALLCAP_100",
}
# Equal-weight baskets of today's constituents (survivorship bias: companies that
# failed earlier aren't in them). Used only where NSE has no long-running index.
BASKETS = {
    "Oil & Gas": ["RELIANCE", "ONGC", "BPCL", "IOC", "HINDPETRO", "GAIL", "OIL", "PETRONET", "IGL", "MGL"],
    "Aviation": ["INDIGO", "SPICEJET"],
    "Defence & Aerospace": ["HAL", "BEL", "BDL", "MAZDOCK", "COCHINSHIP", "BEML", "GRSE", "DATAPATTNS",
                            "ASTRAMICRO", "MIDHANI", "PARAS", "SOLARINDS"],
    "Paints & Chemicals": ["ASIANPAINT", "BERGEPAINT", "KANSAINER", "PIDILITIND", "AKZOINDIA", "INDIGOPNTS"],
}
GOLD_SECTOR = "Gold & Silver"  # gold in rupees: GOLD (USD) × USDINR

MIDDLE_EAST = ("IS", "IR", "IZ", "SY", "LE", "YM", "SA", "JO", "KU", "QA", "AE", "BA", "MU", "GZ", "WE")
_HOSTILE = "(" + ", ".join(f"'{r}'" for r in sorted(CONFLICT_ROOTS)) + ")"
_ME = "(" + ", ".join(f"'{c}'" for c in MIDDLE_EAST) + ")"
# Hostile events between India and Pakistan or China (CAMEO actor country codes).
_INDIA_BORDER = (f"root in {_HOSTILE} and ((actor1_country = 'IND' and actor2_country in ('PAK', 'CHN')) "
                 "or (actor2_country = 'IND' and actor1_country in ('PAK', 'CHN')))")
EVIDENCE_FILTERS = {
    "conflict": "quad = 4",
    "india": _INDIA_BORDER,
    "mideast": f"quad = 4 and country in {_ME}",
    "sanctions": "root = '16'",
}
MAX_DAILY_RETURN = 0.5  # basket members' |daily return| above this is treated as a data error


def _pivot(df: pd.DataFrame, column: str) -> pd.DataFrame:
    df = df.assign(date=pd.to_datetime(df["date"]))
    return df.pivot_table(index="date", columns=column, values="close", aggfunc="last").sort_index()


def load_closes(lake: Lake) -> tuple[pd.DataFrame, pd.Series, dict[str, str]]:
    """Sector levels on NIFTY 50's trading days, the benchmark, and where each sector comes from."""
    codes = list(INDEX_SECTORS.values()) + [BENCHMARK]
    idx = _pivot(lake.query("select date, index, close from index_prices where index in (select c from codes)",
                            frames={"codes": pd.DataFrame({"c": codes})}), "index")
    bench = idx.pop(BENCHMARK).dropna()
    calendar = bench.index
    closes = pd.DataFrame(index=calendar)
    sources = {}
    for name, code in INDEX_SECTORS.items():
        if code in idx:
            closes[name] = idx[code].reindex(calendar)
            sources[name] = f"NSE index {code}"

    if "eod_adjusted" in eod._views(lake):
        members = sorted({s for m in BASKETS.values() for s in m})
        px = eod.adjusted_history(lake, members)
        wide = px.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").reindex(calendar)
        rets = wide.pct_change(fill_method=None)
        rets = rets.where(rets.abs() <= MAX_DAILY_RETURN)
        for name, syms in BASKETS.items():
            have = [s for s in syms if s in rets]
            if not have:
                continue
            daily = rets[have].mean(axis=1, skipna=True)
            level = (1 + daily.fillna(0)).cumprod()
            first = rets[have].notna().any(axis=1).idxmax() if rets[have].notna().any().any() else None
            closes[name] = level.where(level.index >= first) if first is not None else np.nan
            sources[name] = f"equal-weight basket: {', '.join(have)}"

    macro = _pivot(lake.query("select date, series, close from macro_prices where series in ('GOLD', 'USDINR')"), "series")
    if {"GOLD", "USDINR"} <= set(macro.columns):
        gold_inr = (macro["GOLD"] * macro["USDINR"]).dropna()
        closes[GOLD_SECTOR] = gold_inr.reindex(calendar, method="ffill", limit=3)
        sources[GOLD_SECTOR] = "gold in rupees (Yahoo GC=F × INR=X)"
    return closes.ffill(limit=3), bench, sources


def load_inputs(lake: Lake) -> dict[str, pd.Series]:
    macro = _pivot(lake.query("select date, series, close from macro_prices"), "series")
    inputs = {c: macro[c].dropna() for c in macro.columns}
    if "gdelt_daily" in lake.datasets():
        g = lake.query(f"""
            select date,
                   sum(mentions) as total,
                   sum(mentions) filter (where quad = 4) as conflict,
                   sum(mentions) filter (where india and root in {_HOSTILE}) as india_hostile,
                   sum(mentions) filter (where quad = 4 and country in {_ME}) as mideast,
                   sum(mentions) filter (where root = '16') as sanctions
            from gdelt_daily group by date order by date
        """)
        g["date"] = pd.to_datetime(g["date"])
        g = g.set_index("date")
        total = g["total"].where(g["total"] > 0)
        for col in ("conflict", "india_hostile", "mideast", "sanctions"):
            inputs[f"{col}_share"] = (g[col].fillna(0) / total).dropna()
    if {"gdelt_daily", "gdelt_events"} <= set(lake.datasets()):
        # Articles about India–Pakistan/China hostility, as a share of all articles that day.
        b = lake.query(f"""
            select d.date, coalesce(e.arts, 0) as arts, d.total from
              (select date, sum(articles) as total from gdelt_daily group by date) d
            left join (select date, sum(articles) as arts from gdelt_events where {_INDIA_BORDER} group by date) e
              on e.date = d.date
            order by d.date
        """)
        b["date"] = pd.to_datetime(b["date"])
        b = b.set_index("date")
        inputs["india_border_share"] = (b["arts"] / b["total"].where(b["total"] > 0)).dropna()
    return inputs


def evidence(lake: Lake, kind: str, day: str, limit: int = 3) -> list[dict]:
    """The most widely covered matching GDELT events in the 4 days from `day`."""
    if "gdelt_events" not in lake.datasets():
        return []
    df = lake.query(f"""
        select actor1, actor2, place, articles, url from gdelt_events
        where date between cast(? as date) and cast(? as date) + interval 3 day and {EVIDENCE_FILTERS[kind]}
        order by articles desc limit 50
    """, [day, day])
    out, seen = [], set()
    for r in df.itertuples(index=False):
        if r.url in seen or not str(r.url).startswith("http"):
            continue
        seen.add(r.url)
        out.append({"actors": " → ".join(a for a in (r.actor1, r.actor2) if a), "place": r.place,
                    "articles": int(r.articles), "url": r.url})
        if len(out) == limit:
            break
    return out


def run(lake: Lake | None = None, output: Path = OUTPUT, recent: int = 5) -> dict:
    lake = lake or Lake.from_settings()
    closes, bench, sources = load_closes(lake)
    inputs = load_inputs(lake)
    results = event_study.run(closes, bench, inputs)
    kinds = {et.code: et.evidence for et in event_study.EVENT_TYPES}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows, dates = [], []
    for r in results:
        for s in r["sectors"]:
            rows.append({"event": r["code"], **s, "computed_at": now})
        dates += [{"event": r["code"], "base_date": d} for d in r["dates"]]
        r["recent"] = [
            {"date": d, "evidence": evidence(lake, kinds[r["code"]], d) if kinds[r["code"]] else []}
            for d in r["dates"][-recent:][::-1]
        ]
        del r["dates"]
    if rows:
        lake.write_table(pd.DataFrame(rows), "geo_analogues", refresh=False)
        lake.write_table(pd.DataFrame(dates).assign(base_date=lambda d: pd.to_datetime(d["base_date"]).dt.date),
                         "geo_event_dates", refresh=False)
        lake.refresh_catalog()

    doc = {
        "generated_at": now,
        "data_from": str(bench.index.min().date()),
        "data_through": str(bench.index.max().date()),
        "benchmark": "NIFTY 50",
        "horizons_days": list(event_study.HORIZONS),
        "method": (
            "For each past occurrence, the sector's return minus NIFTY 50's over the next 1, 3 and 10 "
            "trading days, measured from the last Indian close on or before the signal. Repeats within "
            f"{event_study.DECLUSTER_DAYS} trading days count once. 95% bootstrap confidence intervals; "
            "baseline = the sector's average excess return over all days. Historical tendency, not a forecast."
        ),
        "sector_sources": sources,
        "events": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    log.info(f"Event study: {len(results)} event types, {len(rows)} sector/horizon rows → {output}")
    return doc
