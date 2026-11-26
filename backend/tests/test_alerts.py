from datetime import date

import pandas as pd

from stocksense import alerts

DAYS = pd.bdate_range("2023-01-02", "2023-01-27")


def prices(symbol="ADANIENT", last_close=2677.0, last_volume=14_764_368):
    rows = [{"date": d.date(), "symbol": symbol, "close": 3300.0, "volume": 1_500_000} for d in DAYS[:-1]]
    rows.append({"date": DAYS[-1].date(), "symbol": symbol, "close": last_close, "volume": last_volume})
    return pd.DataFrame(rows)


NIFTY = pd.Series(18000.0, index=DAYS)
NIFTY.iloc[-1] = 17604.0
DAY = date(2023, 1, 27)


def test_big_fall_on_heavy_volume():
    found = alerts.price_and_volume(prices(), NIFTY, DAY)
    kinds = {a["kind"]: a for a in found}
    assert kinds["price_move"]["value"] == round(100 * (2677 / 3300 - 1), 2)
    assert "fell 18.9% today (NIFTY 50 -2.2%)" in kinds["price_move"]["text"]
    assert kinds["unusual_volume"]["value"] > 9


def test_quiet_day_no_alerts():
    assert alerts.price_and_volume(prices(last_close=3320.0, last_volume=1_600_000), NIFTY, DAY) == []


def test_results_orders_stakes_pledges():
    results = pd.DataFrame([{"symbol": "TCS", "period_end": date(2026, 9, 30), "filed_at": "08-Oct-2026 22:07:30"},
                            {"symbol": "TCS", "period_end": date(2026, 9, 30), "filed_at": "08-Oct-2026 22:07:33"}])
    assert [a["kind"] for a in alerts.results_filed(results, date(2026, 10, 8))] == ["results_filed"]
    ann = pd.DataFrame([{"date": date(2026, 10, 8), "symbol": "LT", "category": "Bagging/Receiving of orders/contracts",
                         "summary": "Order worth Rs 5,000 crore"},
                        {"date": date(2026, 10, 8), "symbol": "LT", "category": "Press Release", "summary": "x"}])
    assert [a["symbol"] for a in alerts.large_orders(ann, date(2026, 10, 8))] == ["LT"]
    sh = pd.DataFrame([{"symbol": "X", "quarter_end": date(2026, 6, 30), "promoter_pct": 60.0, "submitted": date(2026, 7, 20)},
                       {"symbol": "X", "quarter_end": date(2026, 9, 30), "promoter_pct": 57.5, "submitted": date(2026, 10, 19)}])
    stake = alerts.promoter_stake(sh, date(2026, 10, 19))
    assert stake[0]["value"] == -2.5 and "cut their stake" in stake[0]["text"]
    pl = pd.DataFrame([{"symbol": "X", "fetched": date(2026, 11, 26), "pledged_pct_of_promoter": 12.0},
                       {"symbol": "X", "fetched": date(2026, 12, 3), "pledged_pct_of_promoter": 15.5}])
    assert alerts.pledge_change(pl, date(2026, 12, 3))[0]["value"] == 3.5


def test_export_covers_recent_sessions_newest_first(tmp_path, monkeypatch):
    import json
    days = [date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 26)]
    monkeypatch.setattr(alerts, "sessions", lambda lake, count, today=None: days[-count:])
    monkeypatch.setattr(alerts, "for_day", lambda lake, day, symbols=None: [alerts._alert(day, "TCS", "price_move", 5.5, f"moved on {day}")])
    out = tmp_path / "alerts.json"
    doc = alerts.write(object(), output=out, count=2)
    assert doc["days"] == ["2026-11-26", "2026-11-25"]
    assert [a["date"] for a in doc["alerts"]] == ["2026-11-26", "2026-11-25"]
    assert json.loads(out.read_text(encoding="utf-8"))["alerts"][0]["text"] == "moved on 2026-11-26"
