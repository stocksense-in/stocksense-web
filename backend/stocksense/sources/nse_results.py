"""
NSE financial results — every quarterly result a company has filed (TCS: 162 filings
since Mar 2005, standalone and consolidated), with the full profit-and-loss figures.

  • GET /api/corporates-financial-results?index=equities&symbol=<S>&period=Quarterly
    lists the filings (period, standalone/consolidated, audited, format, ids).
  • GET /api/corporates-financial-results-data?…params=…&seq_id=… returns one filing's
    figures in `resultsData2` — the same structure for old (pre-Ind-AS) and new filings,
    with a few field names that differ (handled in `normalise`).

NSE stores the figures in ₹ lakh; `normalise` converts to ₹ crore. Checked against
TCS's published Q3 FY25 consolidated results: revenue ₹63,973 crore, profit ₹12,444
crore (₹12,380 crore attributable to owners).
"""

from __future__ import annotations

from datetime import date, datetime

import httpx

from .nse_ipo import _HEADERS as HEADERS

BASE = "https://www.nseindia.com/api"
LAKH_PER_CRORE = 100
# The filing's format: banks and finance companies file different statements.
KIND = {"B": "bank", "Y": "bank", "F": "finance", "I": "insurance"}


def client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True)


def fetch_filings(c: httpx.Client, symbol: str) -> list[dict]:
    resp = c.get(f"{BASE}/corporates-financial-results",
                 params={"index": "equities", "symbol": symbol, "period": "Quarterly"})
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])


def fetch_detail(c: httpx.Client, filing: dict) -> dict:
    resp = c.get(f"{BASE}/corporates-financial-results-data", params={
        "index": "equities", "params": filing["params"], "seq_id": filing["seqNumber"],
        "industry": filing.get("industry") or "-", "frOldNewFlag": filing.get("oldNewFlag") or "N",
        "ind": filing.get("reInd") or "N", "format": filing.get("format") or "New",
    })
    resp.raise_for_status()
    return resp.json()


def _d(value: str | None) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d-%b-%Y").date()
    except (AttributeError, ValueError):
        return None


def _num(fields: dict, *names: str) -> float | None:
    """First of `names` present as a number, in ₹ crore (NSE reports ₹ lakh)."""
    for name in names:
        value = fields.get(name)
        if value in (None, "", "-"):
            continue
        try:
            return float(str(value).replace(",", "")) / LAKH_PER_CRORE
        except ValueError:
            continue
    return None


def _profit(fields: dict, *names: str) -> float | None:
    """Like _num, but a 0 is a placeholder when a later field has the actual profit
    (Bajaj Finance's Dec 2022 consolidated filing: owners' share "0", profit ₹2,973 crore)."""
    values = [_num(fields, n) for n in names]
    present = [v for v in values if v is not None]
    return next((v for v in present if v != 0), present[0] if present else None)


def _raw(fields: dict, name: str) -> float | None:
    try:
        return float(fields[name])
    except (KeyError, TypeError, ValueError):
        return None


def normalise(filing: dict, detail: dict) -> dict:
    """One filing → one row of standard columns (amounts in ₹ crore)."""
    f = detail.get("resultsData2") or detail.get("resultsData") or {}
    kind = KIND.get(filing.get("bank") or "", "company")
    tax = _num(f, "re_tax")
    if tax is None and (f.get("re_curr_tax") is not None or f.get("re_deff_tax") is not None):
        tax = (_num(f, "re_curr_tax") or 0) + (_num(f, "re_deff_tax") or 0)
    row = {
        "symbol": (filing.get("symbol") or "").upper(),
        "period_from": _d(filing.get("fromDate")),
        "period_end": _d(filing.get("toDate")),
        "consolidated": filing.get("consolidated") == "Consolidated",
        "audited": filing.get("audited") == "Audited",
        "ind_as": "Ind-AS" in (filing.get("indAs") or ""),
        "kind": kind,
        "bank": kind == "bank",
        "filed_at": filing.get("filingDate"),
        "seq": str(filing.get("seqNumber") or ""),
        # Banks report interest earned instead of sales.
        "revenue": _num(f, "re_net_sale", "re_int_earned"),
        "other_income": _num(f, "re_oth_inc_new", "re_oth_inc"),
        "total_income": _num(f, "re_total_inc", "re_tot_inc", "re_gro_inc"),
        "total_expenses": _num(f, "re_oth_tot_exp", "re_oper_exp"),
        "depreciation": _num(f, "re_depr_und_exp"),
        "finance_cost": _num(f, "re_int_new", "re_int", "re_int_expd"),
        "profit_before_tax": _num(f, "re_pro_loss_bef_tax"),
        "tax": tax,
        # What EPS is based on: new filings split out the owners' share; in old consolidated
        # filings the reported profit is already after minority interest.
        "net_profit": _profit(f, "re_pl_own_par", "re_con_pro_loss", "re_net_profit"),
        "eps": _raw(f, "re_bsc_eps_bfr_exi") or _raw(f, "re_basic_eps_for_cont_dic_opr") or _raw(f, "re_basic_eps"),
        "paid_up_capital": _num(f, "re_pdup"),
        "face_value": _raw(f, "re_face_val"),
    }
    row["net_revenue"] = net_revenue(row)
    return row


def net_revenue(row: dict) -> float | None:
    """The revenue a margin is measured on. For lenders (banks and finance companies), net
    interest income + other income — gross interest would make every lender look
    low-margin, and it's what Yahoo's margins use; for everyone else, revenue."""
    if row["kind"] not in ("bank", "finance"):
        # Net of excise duty where the filing separates it (integrated filings from Mar 2025).
        excise = row.get("excise_duty")
        has_excise = isinstance(excise, (int, float)) and excise == excise and excise > 0  # NaN != NaN
        return row["revenue"] - excise if row["revenue"] is not None and has_excise else row["revenue"]
    if row["revenue"] is None or row["finance_cost"] is None:
        return None
    return row["revenue"] - row["finance_cost"] + (row["other_income"] or 0)
