"""
India's macro series with release dates (M1.6), so models never see a number before it was public.

  * repo_rate        RBI policy repo rate, daily (BIS central bank policy rates, WS_CBPOL)
  * cpi              CPI (combined, all India, general index) and inflation % (MoSPI API, base 2012)
  * iip              Index of Industrial Production and growth % (MoSPI API; base 2022-23 from 2023,
                     2011-12 before; compare growth rates across bases, not index levels)
  * fx_reserves      foreign exchange reserves excluding gold, US$ million (IMF via FRED, monthly)
  * gsec_10y         10-year government bond yield %, monthly (OECD via FRED)

`available_from` is when a value became public, from each series' usual release lag, set on the
cautious side: repo the day it takes effect; CPI on the 12th of the next month; IIP 45 days after
the month; reserves 45 days after the month (IMF's monthly figure lags RBI's weekly one); the
monthly bond yield the day after the month ends.

All sources are public and free; no key is needed. MoSPI moved CPI to base 2024 in 2026, which its
API doesn't serve yet, so CPI currently ends in December 2025.
"""
from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import date, timedelta

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (StockSense research)"}
BIS_POLICY_URL = "https://stats.bis.org/api/v1/data/WS_CBPOL/D.IN?format=csv&startPeriod={start}"
MOSPI = "https://api.mospi.gov.in/api"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_SERIES = {"fx_reserves": ("TRESEGINM052N", "US$ million", 45), "gsec_10y": ("INDIRLTLT01STM", "%", 1)}
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], start=1)}


def month_end(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _row(series: str, period: date, value: float, unit: str, available: date, source: str) -> dict:
    return {"series": series, "period": period, "value": float(value), "unit": unit,
            "available_from": available, "source": source}


# -- RBI repo rate (BIS) -------------------------------------------------------

def parse_policy_csv(text: str) -> list[dict]:
    """BIS daily policy rate -> one row per change (the rate holds until the next row)."""
    rows, last = [], None
    for r in csv.DictReader(io.StringIO(text)):
        try:
            day, value = date.fromisoformat(r["TIME_PERIOD"]), float(r["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
        if value != value:  # BIS writes NaN on holidays
            continue
        if value != last:
            rows.append(_row("repo_rate", day, value, "%", day, "BIS WS_CBPOL (Reserve Bank of India)"))
            last = value
    return rows


def fetch_policy_rate(client: httpx.Client, start: str = "2005-01-01") -> list[dict]:
    resp = client.get(BIS_POLICY_URL.format(start=start))
    resp.raise_for_status()
    return parse_policy_csv(resp.text)


# -- MoSPI CPI and IIP ---------------------------------------------------------

def _mospi_pages(client: httpx.Client, path: str, params: dict) -> list[dict]:
    out, page = [], 1
    while True:
        resp = client.get(f"{MOSPI}/{path}", params={**params, "page": page, "format": "json"})
        resp.raise_for_status()
        body = resp.json()
        out += body.get("data") or []
        pages = (body.get("meta_data") or {}).get("totalPages") or 1
        if page >= pages:
            return out
        page += 1


def parse_cpi(records: list[dict]) -> list[dict]:
    """MoSPI CPI rows (all India, combined, general) -> index and inflation rows."""
    rows = []
    for r in records:
        if r.get("state") != "All India" or r.get("sector") != "Combined" or r.get("group") != "General":
            continue
        month = MONTHS.get(r.get("month", ""))
        if not month:
            continue
        end = month_end(int(r["year"]), month)
        released = date(end.year + 1, 1, 12) if end.month == 12 else date(end.year, end.month + 1, 12)
        source = f"MoSPI CPI (base {r.get('baseyear')})"
        if r.get("index") not in (None, ""):
            rows.append(_row("cpi", end, float(r["index"]), f"index, {r.get('baseyear')}=100", released, source))
        if r.get("inflation") not in (None, ""):
            rows.append(_row("cpi_inflation", end, float(r["inflation"]), "% year on year", released, source))
    return rows


def fetch_cpi(client: httpx.Client, year: int) -> list[dict]:
    return parse_cpi(_mospi_pages(client, "cpi/getCPIIndex",
                                  {"base_year": 2012, "year": year, "state_code": 99, "sector_code": 3, "group_code": 0}))


def iip_base(year: int) -> str:
    return "2022-23" if year >= 2023 else "2011-12"


def parse_iip(records: list[dict]) -> list[dict]:
    """MoSPI IIP general index rows -> index and growth rows, released 45 days after the month."""
    rows = []
    for r in records:
        if r.get("type") != "General" or r.get("category") != "General":
            continue
        month = MONTHS.get(r.get("month", ""))
        if not month:
            continue
        end = month_end(int(r["year"]), month)
        released = end + timedelta(days=45)
        source = f"MoSPI IIP (base {r.get('base_year')})"
        if r.get("index") not in (None, ""):
            rows.append(_row("iip", end, float(r["index"]), f"index, {r.get('base_year')}=100", released, source))
        if r.get("growth_rate") not in (None, ""):
            rows.append(_row("iip_growth", end, float(r["growth_rate"]), "% year on year", released, source))
    return rows


def fetch_iip(client: httpx.Client, year: int) -> list[dict]:
    return parse_iip(_mospi_pages(client, "iip/getIIPMonthly", {"base_year": iip_base(year), "year": year, "type": "General"}))


# -- FRED (IMF reserves, OECD bond yield) --------------------------------------

def parse_fred_csv(text: str, series: str, unit: str, lag_days: int, fred_id: str) -> list[dict]:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) != 2 or r[0] == "observation_date" or r[1] in ("", "."):
            continue
        try:
            first, value = date.fromisoformat(r[0]), float(r[1])
        except ValueError:
            continue
        end = month_end(first.year, first.month)
        rows.append(_row(series, end, value, unit, end + timedelta(days=lag_days), f"FRED {fred_id}"))
    return rows


def fetch_fred(client: httpx.Client, series: str) -> list[dict]:
    fred_id, unit, lag = FRED_SERIES[series]
    resp = client.get(FRED_CSV.format(series=fred_id))
    resp.raise_for_status()
    return parse_fred_csv(resp.text, series, unit, lag, fred_id)
