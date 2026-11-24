# Sector GBM experiment — 2026-10-18

Can daily macro and news features predict next-day sector moves versus NIFTY 50?
Gradient-boosted trees (LightGBM), walk-forward by year (train on all earlier years,
test on the next). Data 2012-02-21 → 2026-10-15; 17 NSE sector indices.
Code: `ml/sector_gbm.py`. Timing rules are in its docstring (GDELT lagged one extra day).

Metrics: **IC** = average daily rank correlation between forecast and outcome across
sectors (t-stat over days); **hit** = sign accuracy; **R²** vs forecasting zero;
**spread** = average next-day excess return of the top-3 minus bottom-3 forecast sectors (%).

## Target: `next_day`

| Forecast | IC | IC t | Hit | R² vs zero | Spread % |
|---|---|---|---|---|---|
| model | 0.0449 | 7.15 | 0.5173 | -0.00825 | 0.1212 |
| trailing_mean | -0.0088 | -1.32 | 0.5002 | -0.00105 | -0.0384 |
| momentum | 0.0197 | 3.1 | 0.5094 | -0.94345 | 0.0877 |
| zero | None | None | None | 0.0 | None |

Model by test year:

| Year | IC | Hit | R² vs zero | Spread % |
|---|---|---|---|---|
| 2016 | -0.0071 | 0.4955 | -0.03033 | -0.0166 |
| 2017 | 0.0336 | 0.5108 | -0.03262 | 0.0117 |
| 2018 | 0.0336 | 0.5044 | -0.01768 | 0.1081 |
| 2019 | 0.0445 | 0.5294 | -0.00444 | 0.1674 |
| 2020 | 0.0453 | 0.5142 | -0.00623 | 0.1693 |
| 2021 | 0.0673 | 0.5339 | 0.007 | 0.2041 |
| 2022 | 0.067 | 0.5157 | -0.01137 | 0.1496 |
| 2023 | 0.029 | 0.4859 | -0.02418 | 0.0283 |
| 2024 | 0.0911 | 0.5483 | 0.00198 | 0.1814 |
| 2025 | 0.0533 | 0.5136 | 0.01329 | 0.1642 |
| 2026 | 0.0332 | 0.5403 | 0.00304 | 0.1751 |

IC positive in 10 of 11 test years.

## Target: `open_to_close`

| Forecast | IC | IC t | Hit | R² vs zero | Spread % |
|---|---|---|---|---|---|
| model | 0.0453 | 7.02 | 0.5215 | -0.00737 | 0.1129 |
| trailing_mean | 0.0237 | 3.57 | 0.5081 | 3e-05 | 0.0222 |
| momentum | -0.0066 | -1.04 | 0.4972 | -1.1719 | 0.0098 |
| zero | None | None | None | 0.0 | None |

Model by test year:

| Year | IC | Hit | R² vs zero | Spread % |
|---|---|---|---|---|
| 2016 | -0.008 | 0.5066 | -0.02842 | -0.0204 |
| 2017 | 0.0415 | 0.5223 | -0.03393 | 0.0161 |
| 2018 | 0.0253 | 0.5039 | -0.01419 | 0.1124 |
| 2019 | 0.044 | 0.5325 | -0.00702 | 0.17 |
| 2020 | 0.0507 | 0.514 | -0.0017 | 0.2385 |
| 2021 | 0.0611 | 0.5375 | -0.00104 | 0.1219 |
| 2022 | 0.0614 | 0.5256 | -0.01305 | 0.1041 |
| 2023 | 0.0276 | 0.4945 | -0.01948 | 0.0484 |
| 2024 | 0.0872 | 0.5419 | 0.00591 | 0.1858 |
| 2025 | 0.072 | 0.5351 | 0.01775 | 0.1708 |
| 2026 | 0.0311 | 0.5203 | 0.00027 | 0.0851 |

IC positive in 10 of 11 test years.

## Where the signal comes from (ablation, same model, nested feature sets)

| Features | Target | IC | IC t | Hit | Spread % |
|---|---|---|---|---|---|
| market only | `next_day` | 0.0441 | 7.17 | 0.5208 | 0.1108 |
| market only | `open_to_close` | 0.0483 | 7.61 | 0.524 | 0.1144 |
| + macro | `next_day` | 0.048 | 7.66 | 0.5163 | 0.1226 |
| + macro | `open_to_close` | 0.0475 | 7.33 | 0.5209 | 0.1182 |
| + macro + GDELT | `next_day` | 0.0449 | 7.15 | 0.5173 | 0.1212 |
| + macro + GDELT | `open_to_close` | 0.0453 | 7.02 | 0.5215 | 0.1129 |

## Most used features (final `next_day` model, split gain)

- `sector`: 14606
- `nifty_1d`: 6058
- `india_vix_1d`: 4838
- `nifty_5d`: 4782
- `india_vix`: 4748
- `excess_1d`: 4276
- `sp500_1d`: 3795
- `brent_1d`: 3447
- `conflict_share_z`: 3350
- `mideast_share_z`: 3342
- `excess_20d`: 3045
- `india_border_share_z`: 2985

## Reading this

**There is a small, stable ranking signal — but it isn't news.** The model ranks
tomorrow's sector moves slightly better than chance (IC ≈ 0.045, positive in 10 of 11
test years; 51.7–52% sign accuracy). The ablation shows where it comes from: **market
state alone** (which sector, its recent moves against NIFTY, NIFTY's own recent moves,
India VIX) gives the same IC. Overnight macro (S&P 500, crude) adds ~0.004 IC to the
close-to-close target and nothing to open-to-close; **daily GDELT coverage adds nothing**.
This agrees with the event study, where the news-based event types were at chance level.

What it probably is: short-term sector reversal/rotation after market moves, plus beta —
high-beta sectors move more with whatever NIFTY does next.

**Not a trading result.**
- R² against forecasting zero is negative: the *rankings* carry information, the
  *sizes* don't. Use it, if at all, to order sectors, never as a return forecast.
- The top-3 minus bottom-3 spread (~0.11–0.12% a day) is before costs. Rotating
  sector exposure daily through ETFs or futures would eat most of it.
- `open_to_close` uses NSE's index "open", which at 09:15 includes stocks that haven't
  traded yet at yesterday's price. Part of that move is the stale open catching up, so
  the tradable signal is smaller than it looks.
- 2016 (the first test year, least training data) was slightly negative.

**What this means for the geopolitics engine (M3.3):** coverage counts from GDELT are
too blunt to predict next-day sector moves. The next step is meaning, not volume —
M3.2: label headlines and GDELT events (topic, region, affected sectors, direction)
with a local LLM on the A5000, then test whether *labelled* events beat this
market-state baseline. Any future model must beat **this** report's market-only IC,
not just zero.
