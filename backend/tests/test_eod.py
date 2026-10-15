from datetime import date

import pandas as pd
import pytest

from stocksense import eod
from stocksense.lake import Lake
from stocksense.sources import nse_corporate as nc


@pytest.mark.parametrize("subject, expected", [
    ("Bonus 1:1", 2.0),
    ("Bonus 3:1", 4.0),
    ("Bonus 1:2", 1.5),
    ("Bonus Issue 2 : 5", 1.4),
    ("Bonus Shares In The Ratio Of 1:1", 2.0),
    ("Face Value Split (Sub-Division) - From Rs10/- Per Share To Re 1/- Per Share", 10.0),
    ("Face Value Split From Rs.10/- To Rs.2/-", 5.0),
    ("Face Value Split (Sub-Division) - From Rs 2 Per Share To Rs 1 Per Share", 2.0),
    ("Sub-Division From Rs 10/- Per Share To Rs 2/- Per Share", 5.0),
    ("Bonus 1:1 And Face Value Split From Rs.10/- To Rs.5/-", 4.0),
    ("Bonus 1:1 /Dividend- Rs 29 Per Share", 2.0),
    ("Annual General Meeting / Dividend - Rs 5/- Per Share / Face Value Split - From Rs 10/- Per Share To Rs 2/- Per Share", 5.0),
    ("Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share", 0.1),
    ("Bonus Debentures 1:1", None),
    ("Bonus Preference Shares 1:1", None),
    ("Interim Dividend - Rs 10 Per Share", None),
    ("Rights 1:5 @ Premium Rs 50/-", None),
])
def test_share_multiplier(subject, expected):
    assert nc.share_multiplier(subject) == (pytest.approx(expected) if expected else None)


@pytest.mark.parametrize("subject, kind", [
    ("Bonus 1:1", "bonus"),
    ("Bonus 1:1 And Face Value Split From Rs.10/- To Rs.5/-", "bonus_split"),
    ("Face Value Split From Rs.10/- To Rs.2/-", "split"),
    ("Consolidation Of Equity Shares From Re 1 To Rs 10", "consolidation"),
    ("Interim Dividend - Rs 10 Per Share", "dividend"),
    ("Rights 1:5 @ Premium Rs 50/-", "rights"),
    ("Demerger", "restructuring"),
    ("Annual General Meeting", "other"),
    ("Bonus Debentures 1:1", "other"),
])
def test_classify(subject, kind):
    assert nc.classify(subject) == kind


def test_dividend_per_share():
    assert nc.dividend_per_share("Interim Dividend - Rs 3.50 Per Share") == 3.5
    assert nc.dividend_per_share("Bonus 1:1") is None


def test_actions_frame_types_and_dedupe():
    rows = [
        {"symbol": "tcs", "series": "EQ", "isin": "INE467B01029", "comp": "TCS", "exDate": "31-May-2018",
         "recDate": "01-Jun-2018", "faceVal": "1", "subject": "Bonus 1:1 /Dividend- Rs 29 Per Share"},
        {"symbol": "TCS", "series": "EQ", "isin": "INE467B01029", "comp": "TCS", "exDate": "31-May-2018",
         "recDate": "01-Jun-2018", "faceVal": "1", "subject": "Bonus 1:1 /Dividend- Rs 29 Per Share"},
        {"symbol": "X", "series": "EQ", "exDate": "-", "subject": "Bonus 1:1"},  # no ex-date: dropped
    ]
    df = nc.actions_frame(rows)
    assert len(df) == 1
    r = df.iloc[0]
    assert (r.symbol, r.ex_date, r.kind, r.multiplier, r.dividend) == ("TCS", date(2018, 5, 31), "bonus", 2.0, 29.0)


def changes(*rows):
    return pd.DataFrame(rows, columns=["old_symbol", "new_symbol", "effective_date"])


def test_symbol_map_follows_chains_and_respects_reuse():
    m = eod.resolve_symbol_map(changes(
        ("ZOMATO", "ETERNAL", date(2025, 4, 9)),
        ("A", "B", date(2012, 1, 1)), ("B", "C", date(2018, 1, 1)),
        ("A", "Z", date(2020, 1, 1)),  # "A" reused by another company, renamed again
    ))
    syms = pd.Series(["ZOMATO", "ZOMATO", "A", "B", "B", "A", "A"])
    days = pd.Series([date(2024, 1, 1), date(2025, 5, 1), date(2011, 6, 1), date(2015, 1, 1),
                      date(2019, 1, 1), date(2015, 1, 1), date(2021, 1, 1)])
    assert eod.map_symbols(syms, days, m).tolist() == ["ETERNAL", "ZOMATO", "C", "C", "B", "Z", "A"]


def prices(symbol, rows):
    return pd.DataFrame([{"date": pd.Timestamp(d), "symbol": symbol, "close": c, "prev_close": p} for d, c, p in rows])


def test_observed_ratio_uses_exchange_adjusted_prev_close():
    acts = pd.DataFrame({"symbol": ["NESTLEIND"], "ex_date": [date(2024, 1, 5)]})
    px = prices("NESTLEIND", [("2024-01-04", 25600.0, 25500.0), ("2024-01-05", 2580.0, 2560.0)])
    assert eod.observed_ratios(acts, px).iloc[0] == pytest.approx(10.0)
    # No price around the ex-date → unknown.
    far = prices("NESTLEIND", [("2023-01-02", 1, 1)])
    assert pd.isna(eod.observed_ratios(acts, far).iloc[0])


def test_choose_multipliers():
    acts = pd.DataFrame({
        "symbol": list("ABCDE"),
        "parsed": [2.0, 230.0, None, 5.0, None],
        "observed": [2.01, 23.0, 1.5, None, 1.001],
    })
    out = eod.choose_multipliers(acts)
    assert out["status"].tolist() == ["confirmed", "exchange", "exchange", "parsed", "skipped"]
    assert out["multiplier"].tolist()[:4] == [2.0, 23.0, 1.5, 5.0]
    assert pd.isna(out["multiplier"].iloc[4])


def test_factor_ranges_compound_later_actions():
    adj = pd.DataFrame({"symbol": ["INFY", "INFY", "INFY"],
                        "ex_date": [date(2014, 12, 2), date(2015, 6, 15), date(2018, 9, 4)],
                        "multiplier": [2.0, 2.0, 2.0]})
    f = eod.factor_ranges(adj)
    assert f["factor"].tolist() == [8.0, 4.0, 2.0]
    assert f["valid_to"].tolist() == [date(2014, 12, 2), date(2015, 6, 15), date(2018, 9, 4)]
    assert f["valid_from"].iloc[0] == eod.BEGINNING and f["valid_from"].iloc[1] == date(2014, 12, 2)


def test_adjusted_view_end_to_end(tmp_path):
    lake = Lake(tmp_path)
    # TCS 1:1 bonus, ex 31 May 2018; traded under an old name until 2018-01-01.
    days = [("2017-12-29", "OLDTCS", 2600.0, 2590.0), ("2018-05-30", "TCS", 3500.0, 3480.0),
            ("2018-05-31", "TCS", 1760.0, 1750.0)]
    for d, sym, close, prev in days:
        df = pd.DataFrame({"symbol": [sym], "series": ["EQ"], "isin": ["INE467B01029"], "open": [close],
                           "high": [close], "low": [close], "close": [close], "last": [close],
                           "prev_close": [prev], "volume": [100], "turnover": [close * 100], "trades": [10]})
        df["volume"] = df["volume"].astype("Int64")
        lake.write_parquet(df, "eod_prices", day=d)
    actions = nc.actions_frame([{"symbol": "TCS", "series": "EQ", "exDate": "31-May-2018",
                                 "subject": "Bonus 1:1 /Dividend- Rs 29 Per Share"}])
    eod.build_adjustments(lake, actions, changes(("OLDTCS", "TCS", date(2018, 1, 1))))

    adj = lake.query("select price_adjustments.status, observed from price_adjustments")
    assert adj["status"].tolist() == ["confirmed"] and adj["observed"].iloc[0] == pytest.approx(2.0, rel=0.01)
    out = eod.adjusted_history(lake, ["TCS"])
    assert out["traded_symbol"].tolist() == ["OLDTCS", "TCS", "TCS"]
    assert out["close"].tolist() == [1300.0, 1750.0, 1760.0]
    assert out["volume"].tolist() == [200, 200, 100]

    report = eod.check(lake)
    assert report["trading_days"] == 3 and report["duplicates"] == 0
    assert report["adjustments"] == {"confirmed": 1}
    assert report["unexplained_moves_over_40pct"] == 0
