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
    live = df[(df["expiry"].notna()) & (df["expiry"] >= day)].copy()
    live["open_interest"] = live["open_interest"].fillna(0).astype("int64")
    live["contracts"] = live["contracts"].fillna(0).astype("int64")
    by = live.groupby("symbol", sort=True)
    out = pd.DataFrame(index=pd.Index(sorted(live["symbol"].unique()), name="symbol"))
    out["kind"] = np.where(by["instrument"].agg(lambda s: s.str.endswith("IDX").any()), "index", "stock")
    out["underlying"] = by["underlying"].first()  # first non-missing (UDiFF only)

    fut = live[live["instrument"].str.startswith("FUT")]
    near_fut = fut.sort_values(["symbol", "expiry"], kind="mergesort").groupby("symbol").first()
    out["fut_near_expiry"] = near_fut["expiry"]
    out["fut_near_close"] = near_fut["close"]
    out["fut_oi"] = fut.groupby("symbol")["open_interest"].sum()
    out["fut_contracts"] = fut.groupby("symbol")["contracts"].sum()

    opt = live[live["instrument"].str.startswith("OPT")]
    by_type = opt.groupby(["symbol", "option_type"])[["open_interest", "contracts"]].sum().unstack("option_type")
    for col, (field, kind) in {"call_oi": ("open_interest", "CE"), "put_oi": ("open_interest", "PE"),
                               "call_contracts": ("contracts", "CE"), "put_contracts": ("contracts", "PE")}.items():
        out[col] = by_type[(field, kind)] if (field, kind) in by_type.columns else 0
    for col in ("fut_oi", "fut_contracts", "call_oi", "put_oi", "call_contracts", "put_contracts"):
        out[col] = out[col].fillna(0).astype("int64")
    out["pcr_oi"] = out["put_oi"] / out["call_oi"].where(out["call_oi"] > 0)
    out["pcr_volume"] = out["put_contracts"] / out["call_contracts"].where(out["call_contracts"] > 0)

    # Nearest option expiry: its put/call ratio and the strikes with the most OI.
    out["opt_near_expiry"] = opt.groupby("symbol")["expiry"].min()
    near = opt[opt["expiry"] == opt["symbol"].map(out["opt_near_expiry"])]
    near_oi = near.groupby(["symbol", "option_type"])["open_interest"].sum().unstack("option_type")
    near_call = near_oi["CE"] if "CE" in near_oi else pd.Series(dtype="float64")
    near_put = near_oi["PE"] if "PE" in near_oi else pd.Series(dtype="float64")
    out["near_pcr_oi"] = near_put.reindex(out.index).fillna(0) / near_call.reindex(out.index).where(lambda s: s > 0)
    top = (near[near["open_interest"] > 0].sort_values("open_interest", ascending=False, kind="mergesort")
           .groupby(["symbol", "option_type"])["strike"].first().unstack("option_type"))
    out["max_call_oi_strike"] = top["CE"] if "CE" in top else np.nan
    out["max_put_oi_strike"] = top["PE"] if "PE" in top else np.nan
    out["turnover"] = by["turnover"].sum().astype("float64")
    out = out.reset_index()
    for col in ("fut_near_expiry", "opt_near_expiry"):
        out[col] = out[col].astype(object).where(out[col].notna(), None)
    return out
