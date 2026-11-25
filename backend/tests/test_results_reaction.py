from datetime import date

import pandas as pd
import pytest

from stocksense import results_reaction as rr

DAYS = pd.bdate_range("2026-07-06", "2026-07-17")


def prices(jump_on: str, jump: float):
    rows, close = [], 100.0
    for d in DAYS:
        if d == pd.Timestamp(jump_on):
            close *= 1 + jump
        rows.append({"date": d.date(), "symbol": "TCS", "close": close})
    return pd.DataFrame(rows)


NIFTY = pd.DataFrame({"date": [d.date() for d in DAYS], "close": 20000.0})


def results(filed_at: str):
    return pd.DataFrame([
        {"symbol": "TCS", "period_end": date(2025, 6, 30), "consolidated": True, "revenue": 100.0, "net_profit": 10.0,
         "filed_at": "10-Jul-2025 18:00:00"},
        {"symbol": "TCS", "period_end": date(2026, 6, 30), "consolidated": True, "revenue": 110.0, "net_profit": 12.0,
         "filed_at": filed_at},
        {"symbol": "TCS", "period_end": date(2026, 6, 30), "consolidated": False, "revenue": 90.0, "net_profit": 9.0,
         "filed_at": filed_at.replace(":36:", ":30:")},  # standalone, minutes earlier
    ])


def test_after_hours_filing_reacts_next_day():
    r = rr.reactions(results("09-Jul-2026 18:36:12"), prices("2026-07-10", -0.06), NIFTY)
    row = r[r["period_end"] == date(2026, 6, 30)].iloc[0]
    assert row["filed"] == "2026-07-09 18:30:12"  # the first release
    assert row["profit_yoy_pct"] == pytest.approx(20.0) and row["revenue_yoy_pct"] == pytest.approx(10.0)
    assert row["excess_1d_pct"] == pytest.approx(-6.0)  # fell despite profit up 20%


def test_filing_in_market_hours_counts_from_the_previous_close():
    r = rr.reactions(results("09-Jul-2026 11:36:00"), prices("2026-07-09", 0.04), NIFTY)
    assert r[r["period_end"] == date(2026, 6, 30)].iloc[0]["move_1d_pct"] == pytest.approx(4.0)


def test_note_counts_strong_and_contrary_moves():
    rows = [{"excess_1d_pct": -6.0, "profit_yoy_pct": 20.0}, {"excess_1d_pct": 1.0, "profit_yoy_pct": 5.0},
            {"excess_1d_pct": 7.0, "profit_yoy_pct": 15.0}, {"excess_1d_pct": -0.5, "profit_yoy_pct": -3.0}]
    text = rr.note(rows)
    assert "After 2 of its last 4 results" in text and "Once it moved the opposite way" in text
    assert rr.note(rows[:3]) is None
    calm = [{"excess_1d_pct": -0.5, "profit_yoy_pct": 10.0}] * 4  # small moves aren't "the opposite way"
    assert rr.note(calm) == "None of its last 4 results moved the share 5% or more against the market the next day."
