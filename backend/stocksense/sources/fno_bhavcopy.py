"""
NSE F&O bhavcopy — the exchange's end-of-day file for every futures and options
contract: prices, settlement price, contracts traded, turnover and open interest.

Two formats in NSE's public archive (same switch date as the equity bhavcopy):
  • until 5 Jul 2024: content/historical/DERIVATIVES/<YYYY>/<MON>/fo<DD><MON><YYYY>bhav.csv.zip
  • from  8 Jul 2024: content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip ("UDiFF")

Units, checked across the switch (NIFTY July 2024 future, 5 vs 8 Jul):
  contracts      number of contracts in both formats
  open_interest  in shares/units in both formats (not contracts)
  turnover       ₹ — the old format reports ₹ lakh, converted here
  underlying, lot_size — only in UDiFF (NaN before 8 Jul 2024)
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

import numpy as np
import pandas as pd

from ..symbols import _HEADERS as HEADERS  # browser-like headers the archive expects

ARCHIVE = "https://nsearchives.nseindia.com"
UDIFF_FROM = date(2024, 7, 8)
_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
# UDiFF instrument codes → the classic names
_INSTRUMENTS = {"IDF": "FUTIDX", "STF": "FUTSTK", "IDO": "OPTIDX", "STO": "OPTSTK"}

COLUMNS = ["instrument", "symbol", "expiry", "strike", "option_type", "open", "high", "low", "close", "settle",
           "contracts", "turnover", "open_interest", "oi_change", "underlying", "lot_size"]


def file_name(day: date) -> str:
    if day >= UDIFF_FROM:
        return f"BhavCopy_NSE_FO_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    return f"fo{day:%d}{_MONTHS[day.month - 1]}{day:%Y}bhav.csv.zip"


def url_for(day: date) -> str:
    if day >= UDIFF_FROM:
        return f"{ARCHIVE}/content/fo/{file_name(day)}"
    return f"{ARCHIVE}/content/historical/DERIVATIVES/{day:%Y}/{_MONTHS[day.month - 1]}/{file_name(day)}"


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def parse(content: bytes) -> pd.DataFrame:
    """One day's zip (either format) → DataFrame with COLUMNS."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        raw = pd.read_csv(z.open(name), dtype=str, keep_default_na=False)
    raw.columns = [c.strip() for c in raw.columns]
    if "TckrSymb" in raw.columns:
        df = pd.DataFrame({
            "instrument": raw["FinInstrmTp"].str.strip().map(_INSTRUMENTS).fillna(raw["FinInstrmTp"].str.strip()),
            "symbol": raw["TckrSymb"], "expiry": pd.to_datetime(raw["XpryDt"], errors="coerce"),
            "strike": _num(raw["StrkPric"]), "option_type": raw["OptnTp"],
            "open": _num(raw["OpnPric"]), "high": _num(raw["HghPric"]), "low": _num(raw["LwPric"]),
            "close": _num(raw["ClsPric"]), "settle": _num(raw["SttlmPric"]),
            "contracts": _num(raw["TtlTradgVol"]), "turnover": _num(raw["TtlTrfVal"]),
            "open_interest": _num(raw["OpnIntrst"]), "oi_change": _num(raw["ChngInOpnIntrst"]),
            "underlying": _num(raw["UndrlygPric"]), "lot_size": _num(raw["NewBrdLotQty"]),
        })
    else:
        df = pd.DataFrame({
            "instrument": raw["INSTRUMENT"], "symbol": raw["SYMBOL"],
            "expiry": pd.to_datetime(raw["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce"),
            "strike": _num(raw["STRIKE_PR"]), "option_type": raw["OPTION_TYP"],
            "open": _num(raw["OPEN"]), "high": _num(raw["HIGH"]), "low": _num(raw["LOW"]),
            "close": _num(raw["CLOSE"]), "settle": _num(raw["SETTLE_PR"]),
            "contracts": _num(raw["CONTRACTS"]), "turnover": _num(raw["VAL_INLAKH"]) * 1e5,
            "open_interest": _num(raw["OPEN_INT"]), "oi_change": _num(raw["CHG_IN_OI"]),
            "underlying": np.nan, "lot_size": np.nan,
        })
    for col in ("instrument", "symbol", "option_type"):
        df[col] = df[col].astype(str).str.strip().str.upper().astype("string")
    df["option_type"] = df["option_type"].where(df["option_type"].isin(["CE", "PE"]), "")  # futures: "XX" / blank
    df["expiry"] = df["expiry"].dt.date
    futures = df["instrument"].str.startswith("FUT")
    df.loc[futures, "strike"] = np.nan
    for col in ("contracts", "open_interest", "oi_change", "lot_size"):
        df[col] = df[col].round().astype("Int64")
    for col in ("strike", "open", "high", "low", "close", "settle", "turnover", "underlying"):
        df[col] = df[col].astype("float64")
    return df[df["symbol"].str.len() > 0][COLUMNS].reset_index(drop=True)


def summarise(df: pd.DataFrame, day: date) -> pd.DataFrame:
    """
    One row per underlying for the day: near-month future (close, OI), total futures
    OI, call/put open interest and volume with put/call ratios (all expiries, and the
    nearest expiry), and the near-expiry strikes with the most call and put OI.
    """
    rows = []
    live = df[(df["expiry"].notna()) & (df["expiry"] >= day)]
    for symbol, g in live.groupby("symbol", sort=True):
        fut = g[g["instrument"].str.startswith("FUT")].sort_values("expiry")
        opt = g[g["instrument"].str.startswith("OPT")]
        calls, puts = opt[opt["option_type"] == "CE"], opt[opt["option_type"] == "PE"]
        near = opt["expiry"].min() if not opt.empty else None
        nc, np_ = calls[calls["expiry"] == near], puts[puts["expiry"] == near]
        call_oi, put_oi = calls["open_interest"].sum(), puts["open_interest"].sum()
        near_call_oi, near_put_oi = nc["open_interest"].sum(), np_["open_interest"].sum()
        rows.append({
            "symbol": symbol,
            "kind": "index" if g["instrument"].str.endswith("IDX").any() else "stock",
            "underlying": g["underlying"].dropna().iloc[0] if g["underlying"].notna().any() else np.nan,
            "fut_near_expiry": fut["expiry"].iloc[0] if not fut.empty else None,
            "fut_near_close": fut["close"].iloc[0] if not fut.empty else np.nan,
            "fut_oi": int(fut["open_interest"].sum()) if not fut.empty else 0,
            "fut_contracts": int(fut["contracts"].sum()) if not fut.empty else 0,
            "call_oi": int(call_oi), "put_oi": int(put_oi),
            "call_contracts": int(calls["contracts"].sum()), "put_contracts": int(puts["contracts"].sum()),
            "pcr_oi": put_oi / call_oi if call_oi else np.nan,
            "pcr_volume": puts["contracts"].sum() / calls["contracts"].sum() if calls["contracts"].sum() else np.nan,
            "opt_near_expiry": near,
            "near_pcr_oi": near_put_oi / near_call_oi if near_call_oi else np.nan,
            "max_call_oi_strike": nc.loc[nc["open_interest"].idxmax(), "strike"] if near_call_oi else np.nan,
            "max_put_oi_strike": np_.loc[np_["open_interest"].idxmax(), "strike"] if near_put_oi else np.nan,
            "turnover": float(g["turnover"].sum()),
        })
    return pd.DataFrame(rows)
