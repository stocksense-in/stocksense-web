import json

import numpy as np
import pandas as pd
import pytest

from stocksense import valuation as v


def pe_frame(index, values, start="2021-04-01"):
    dates = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({"date": dates, "index": index, "pe": values})


def test_summary_reads_today_against_comparable_history():
    # Four years around 20; today 30 → expensive. Pre-2021 values (standalone earnings) must be ignored.
    old = pe_frame("NIFTY_IT", [60.0] * 300, start="2019-01-01")
    recent = pe_frame("NIFTY_IT", list(np.linspace(18, 22, 1040)) + [30.0])
    s = v.summarise(pd.concat([old, recent]).set_index("date")["pe"])
    assert s["since"] == "2021-04-01" and s["pe"] == 30.0
    assert s["higher_than_pct_of_days"] == 100 and s["reading"] == "expensive by its own history"
    assert s["median_pe"] == pytest.approx(20.0, abs=0.1)


def test_too_little_history_says_nothing():
    assert v.summarise(pe_frame("NIFTY_X", [20.0] * 200).set_index("date")["pe"]) is None


def test_build_and_sector_note():
    frames = [pe_frame("NIFTY_50", list(np.linspace(20, 24, 1040)) + [19.0]),
              pe_frame("NIFTY_FMCG", list(np.linspace(38, 44, 1040)) + [31.0])]
    doc = v.build(pd.concat(frames))
    assert doc["sector_index"] == {"fmcg": "NIFTY_FMCG"}
    assert doc["indices"]["NIFTY_FMCG"]["reading"] == "cheap by its own history"
    note = v.sector_note("fmcg", doc)
    assert note.startswith("The FMCG sector trades at a P/E of 31") and "since 2021" in note
    assert v.sector_note("electronics", doc).startswith("The market as a whole")  # no index → market
    assert v.sector_note("it", None) is None
    json.dumps(doc)  # publishable as-is
