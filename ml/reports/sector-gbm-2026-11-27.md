# Sector GBM experiment — 2026-11-27

Can daily macro and news features predict next-day sector moves versus NIFTY 50?
Gradient-boosted trees (LightGBM), walk-forward by year (train on all earlier years,
test on the next). Data 2012-02-21 → 2026-11-26; 17 NSE sector indices.
Code: `ml/sector_gbm.py`. Timing rules are in its docstring (GDELT lagged one extra day;
India's repo rate, CPI, IIP, bond yield and reserves enter from their release dates).

Metrics: **IC** = average daily rank correlation between forecast and outcome across
sectors (t-stat over days); **hit** = sign accuracy; **R²** vs forecasting zero;
**spread** = average next-day excess return of the top-3 minus bottom-3 forecast sectors (%).

## Target: `next_day`

| Forecast | IC | IC t | Hit | R² vs zero | Spread % |
|---|---|---|---|---|---|
| model | 0.0471 | 7.46 | 0.5156 | -0.00738 | 0.1108 |
| trailing_mean | -0.0085 | -1.28 | 0.5 | -0.00104 | -0.0364 |
| momentum | 0.0196 | 3.09 | 0.5091 | -0.94625 | 0.0866 |
| zero | None | None | None | 0.0 | None |

Model by test year:

| Year | IC | Hit | R² vs zero | Spread % |
|---|---|---|---|---|
| 2016 | 0.0049 | 0.501 | -0.01723 | 0.062 |
| 2017 | 0.0306 | 0.511 | -0.02197 | -0.0157 |
| 2018 | 0.0495 | 0.5096 | -0.02254 | 0.1306 |
| 2019 | 0.0514 | 0.5268 | 0.00078 | 0.148 |
| 2020 | 0.0463 | 0.5226 | -0.006 | 0.1436 |
| 2021 | 0.0893 | 0.5406 | 0.01461 | 0.2445 |
| 2022 | 0.0437 | 0.5119 | -0.01531 | 0.1282 |
| 2023 | 0.0399 | 0.4912 | -0.01684 | 0.0829 |
| 2024 | 0.0777 | 0.5308 | -0.008 | 0.1066 |
| 2025 | 0.0529 | 0.5086 | 0.01178 | 0.1206 |
| 2026 | 0.0294 | 0.5151 | -0.01279 | 0.0616 |

IC positive in 11 of 11 test years.

## Target: `open_to_close`

| Forecast | IC | IC t | Hit | R² vs zero | Spread % |
|---|---|---|---|---|---|
| model | 0.0425 | 6.71 | 0.5192 | -0.00958 | 0.1075 |
| trailing_mean | 0.0234 | 3.54 | 0.5078 | 3e-05 | 0.023 |
| momentum | -0.0069 | -1.1 | 0.497 | -1.1769 | 0.0086 |
| zero | None | None | None | 0.0 | None |

Model by test year:

| Year | IC | Hit | R² vs zero | Spread % |
|---|---|---|---|---|
| 2016 | 0.0056 | 0.5021 | -0.02589 | 0.0225 |
| 2017 | 0.0161 | 0.5078 | -0.03351 | -0.0022 |
| 2018 | 0.0375 | 0.5157 | -0.0194 | 0.1565 |
| 2019 | 0.0541 | 0.5342 | -0.00502 | 0.1836 |
| 2020 | 0.0384 | 0.5103 | -0.00497 | 0.1647 |
| 2021 | 0.0765 | 0.5498 | 0.01154 | 0.1987 |
| 2022 | 0.0396 | 0.5308 | -0.01963 | 0.0675 |
| 2023 | 0.0201 | 0.4868 | -0.01796 | 0.0152 |
| 2024 | 0.0823 | 0.5358 | -0.00226 | 0.1864 |
| 2025 | 0.0701 | 0.5259 | 0.01263 | 0.1414 |
| 2026 | 0.0249 | 0.5074 | -0.02207 | 0.0398 |

IC positive in 11 of 11 test years.

## Where the signal comes from (ablation, same model, nested feature sets)

| Features | Target | IC | IC t | Hit | Spread % |
|---|---|---|---|---|---|
| market only | `next_day` | 0.044 | 7.21 | 0.5207 | 0.1113 |
| market only | `open_to_close` | 0.0479 | 7.6 | 0.5237 | 0.1142 |
| + macro | `next_day` | 0.0414 | 6.58 | 0.5158 | 0.1181 |
| + macro | `open_to_close` | 0.0458 | 7.15 | 0.5209 | 0.1099 |
| + macro + GDELT | `next_day` | 0.0446 | 7.1 | 0.5189 | 0.1156 |
| + macro + GDELT | `open_to_close` | 0.0429 | 6.76 | 0.5189 | 0.111 |
| + macro + GDELT + India macro | `next_day` | 0.0383 | 6.05 | 0.515 | 0.1187 |
| + macro + GDELT + India macro | `open_to_close` | 0.037 | 5.79 | 0.5164 | 0.0932 |

## Most used features (final `next_day` model, split gain)

- `sector`: 13778
- `nifty_1d`: 6037
- `india_vix_1d`: 4777
- `india_vix`: 4736
- `nifty_5d`: 4690
- `sp500_1d`: 4493
- `excess_1d`: 4266
- `conflict_share_z`: 3370
- `mideast_share_z`: 3353
- `excess_20d`: 3289
- `us_vix_1d`: 3087
- `us_vix`: 2961

## Reading this

Same model and timing rules as 18 Oct, with six more weeks of data. This run asks one new question: do India's
own macro series (M1.6) help? They were tried with each value entering from its release date: the repo rate level,
its three-month change and the days since it last moved, CPI inflation, IIP growth and the 10-year yield (each with
its change over three releases), and the three-month change in forex reserves.

- **They don't help.** Adding them lowered the IC on both targets: next day 0.0446 → 0.0383, open to close
  0.0429 → 0.0370 (last two ablation pairs). The series move monthly or less often, so in trees they mostly
  label regimes (high rates, high inflation). Those regimes are few and long, so the model learns past episodes
  that don't repeat, which is overfitting. The main model above therefore leaves them out; the ablation keeps
  measuring them, so a future run will show if that changes.
- **The edge is still small and steady.** Next-day IC 0.047 (t 7.5), positive in all 11 test years. The top-3
  minus bottom-3 sector spread is about 0.11% a day before costs, and R² vs forecasting zero is still negative.
  It's a ranking signal, not a forecast of size, and as in October most of it comes from market data
  (sector, NIFTY and India VIX moves, recent sector excess returns).
- **How much is noise.** The main model and the "+ macro + GDELT" ablation row use the same features, in a
  different column order. Their IC differs by 0.0025 (0.0471 vs 0.0446), because column sampling picks
  different columns. Differences of that size between rows are noise. The India macro drop is about twice that,
  in the same direction on both targets.
- **Next.** Where the rate data should matter is particular sectors (banks, property, autos) on decision days.
  M3.1's event study can now add RBI rate changes as an event type, which tests that directly instead of asking
  a daily model to find it.
