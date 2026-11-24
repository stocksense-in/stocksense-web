"""
NSE equity bhavcopy — the exchange's official end-of-day file: open, high, low,
close, volume and turnover for every listed security, one file per trading day.

Two formats in NSE's public archive:
  • until 5 Jul 2024: content/historical/EQUITIES/<YYYY>/<MON>/cm<DD><MON><YYYY>bhav.csv.zip
  • from  8 Jul 2024: content/cm/BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip ("UDiFF")
Days without a file are holidays (NSE answers 404).

`parse` turns either format into the same columns (see COLUMNS). Prices are as
traded, not adjusted for splits or bonuses — see stocksense/eod.py for that.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd

from ..symbols import _HEADERS as HEADERS  # browser-like headers the archive expects

ARCHIVE = "https://nsearchives.nseindia.com"
UDIFF_FROM = date(2024, 7, 8)

COLUMNS = ["symbol", "series", "isin", "open", "high", "low", "close", "last", "prev_close",
           "volume", "turnover", "trades"]

_OLD = {"SYMBOL": "symbol", "SERIES": "series", "ISIN": "isin", "OPEN": "open", "HIGH": "high",
        "LOW": "low", "CLOSE": "close", "LAST": "last", "PREVCLOSE": "prev_close",
        "TOTTRDQTY": "volume", "TOTTRDVAL": "turnover", "TOTALTRADES": "trades"}
_UDIFF = {"TckrSymb": "symbol", "SctySrs": "series", "ISIN": "isin", "OpnPric": "open",
          "HghPric": "high", "LwPric": "low", "ClsPric": "close", "LastPric": "last",
          "PrvsClsgPric": "prev_close", "TtlTradgVol": "volume", "TtlTrfVal": "turnover",
          "TtlNbOfTxsExctd": "trades"}


# Not strftime("%b"): that follows the machine's locale.
_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def file_name(day: date) -> str:
    if day >= UDIFF_FROM:
        return f"BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    return f"cm{day:%d}{_MONTHS[day.month - 1]}{day:%Y}bhav.csv.zip"


def url_for(day: date) -> str:
    if day >= UDIFF_FROM:
        return f"{ARCHIVE}/content/cm/{file_name(day)}"
    return f"{ARCHIVE}/content/historical/EQUITIES/{day:%Y}/{_MONTHS[day.month - 1]}/{file_name(day)}"


def parse(content: bytes) -> pd.DataFrame:
    """One day's zip (either format) → DataFrame with COLUMNS, numeric types, upper-case symbols."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        raw = pd.read_csv(z.open(csv_name), dtype=str, keep_default_na=False)
    raw.columns = [c.strip() for c in raw.columns]
    if "TckrSymb" in raw.columns:
        if "Sgmt" in raw.columns:
            raw = raw[raw["Sgmt"] == "CM"]
        df = raw.rename(columns=_UDIFF)
    else:
        df = raw.rename(columns=_OLD)
    # Files before mid-2011 have no ISIN or trade-count columns.
    for col in ("isin", "trades"):
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].copy()
    for col in ("symbol", "series", "isin"):
        df[col] = df[col].str.strip().str.upper().astype("string")
    for col in ("open", "high", "low", "close", "last", "prev_close", "turnover"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    for col in ("volume", "trades"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df[df["symbol"].str.len() > 0].reset_index(drop=True)
