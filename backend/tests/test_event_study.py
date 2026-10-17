import numpy as np
import pandas as pd
import pytest

from stocksense import event_study as es


def days(n, start="2020-01-01"):
    return pd.bdate_range(start, periods=n)


def test_threshold_dates_pct_and_diff():
    s = pd.Series([100, 106, 106, 99, 99], index=days(5))
    assert list(es.threshold_dates(s, 0.05)) == [s.index[1]]
    assert list(es.threshold_dates(s, -0.05)) == [s.index[3]]
    y = pd.Series([4.00, 4.20, 4.25], index=days(3))
    assert list(es.threshold_dates(y, 0.15, change="diff")) == [y.index[1]]


def test_spike_dates_use_only_the_past():
    rng = np.random.default_rng(0)
    s = pd.Series(1 + rng.normal(0, 0.01, 200), index=days(200))
    s.iloc[150] = 2.0  # one huge day
    assert list(es.spike_dates(s)) == [s.index[150]]
    # A spike inside the warm-up window can't be scored.
    s2 = s.copy()
    s2.iloc[10] = 5.0
    assert s2.index[10] not in es.spike_dates(s2)


def test_to_base_dates_maps_weekends_to_previous_close():
    cal = days(10)  # Wed 2020-01-01 …
    saturday = pd.Timestamp("2020-01-04")
    out = es.to_base_dates(pd.DatetimeIndex([saturday, pd.Timestamp("2019-12-01")]), cal)
    assert list(out) == [pd.Timestamp("2020-01-03")]


def test_decluster_keeps_first_of_each_episode():
    cal = days(40)
    out = es.decluster(pd.DatetimeIndex([cal[0], cal[3], cal[10], cal[11], cal[30]]), cal, gap=10)
    assert list(out) == [cal[0], cal[11], cal[30]]


def test_forward_excess_is_sector_minus_benchmark():
    cal = days(4)
    closes = pd.DataFrame({"IT": [100, 110, 121, 121]}, index=cal)
    bench = pd.Series([100, 105, 105, 105], index=cal)
    ex = es.forward_excess(closes, bench, horizons=(1, 2))
    assert ex[1]["IT"].iloc[0] == pytest.approx(5.0)          # +10% vs +5%
    assert ex[2]["IT"].iloc[0] == pytest.approx(21.0 - 5.0)   # +21% vs +5%
    assert np.isnan(ex[2]["IT"].iloc[-1])                     # window runs past the data


def synthetic_market(n_events=12, effect=2.0, seed=1):
    """NIFTY random walk; 'Aviation' falls `effect`% vs NIFTY on the day after each crude spike."""
    rng = np.random.default_rng(seed)
    cal = days(1500)
    bench_ret = rng.normal(0, 0.01, len(cal))
    noise = rng.normal(0, 0.002, len(cal))
    spikes = np.sort(rng.choice(np.arange(100, len(cal) - 20, 40), n_events, replace=False))
    sector_ret = bench_ret + noise
    sector_ret[spikes + 1] -= effect / 100
    bench = pd.Series(100 * np.cumprod(1 + bench_ret), index=cal)
    closes = pd.DataFrame({"Aviation": 100 * np.cumprod(1 + sector_ret),
                           "IT": 100 * np.cumprod(1 + bench_ret + noise)}, index=cal)
    brent_ret = rng.normal(0, 0.01, len(cal))
    brent_ret[spikes] = 0.08
    brent = pd.Series(80 * np.cumprod(1 + brent_ret), index=cal)
    return closes, bench, {"BRENT": brent}, cal[spikes]


def test_run_recovers_a_planted_effect():
    closes, bench, inputs, spike_days = synthetic_market()
    crude = next(et for et in es.EVENT_TYPES if et.code == "crude_spike")
    [result] = es.run(closes, bench, inputs, [crude])
    assert result["occurrences"] == len(spike_days)
    cell = {(r["sector"], r["horizon_days"]): r for r in result["sectors"]}
    avi = cell[("Aviation", 1)]
    assert avi["n"] == len(spike_days)
    assert avi["mean_excess_pct"] == pytest.approx(-2.0, abs=0.3)
    assert avi["hit_rate"] < 0.2 and avi["notable"]
    assert avi["ci_low_pct"] < avi["mean_excess_pct"] < avi["ci_high_pct"]
    it = cell[("IT", 1)]
    assert not it["notable"] and abs(it["mean_excess_pct"]) < 0.3


def test_run_skips_thin_cells_and_missing_inputs():
    closes, bench, inputs, _ = synthetic_market(n_events=3)
    results = es.run(closes, bench, inputs)
    crude = next(r for r in results if r["code"] == "crude_spike")
    assert crude["occurrences"] == 3 and crude["sectors"] == []  # fewer than MIN_EVENTS
    conflict = next(r for r in results if r["code"] == "global_conflict")
    assert conflict["occurrences"] == 0 and conflict["first"] is None  # no GDELT input given


def test_notable_share_per_horizon():
    from stocksense.jobs.event_study import notable_share

    rows = [{"horizon_days": 1, "notable": True}, {"horizon_days": 1, "notable": False},
            {"horizon_days": 3, "notable": False}]
    assert notable_share(rows) == {"1": 0.5, "3": 0.0}
