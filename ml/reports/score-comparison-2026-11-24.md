# Sector-relative score — what would change (2026-11-24)

2352 scored NSE stocks. Current = fixed curves; relative = share of sector peers beaten
on each metric; **blend = 70% relative + 30% current** (the candidate). Code:
`ml/score_comparison.py`. Nothing in production has changed.

- Rank agreement between current and blend (Spearman): **0.92**.
- Median absolute change: **4 points**; 3% of stocks move 15+ points.

## Sector averages (sectors with 20+ scored stocks)

Fixed curves systematically favour some sectors (cheap-looking, high-margin businesses)
and penalise others (FMCG's high P/Es, thin-margin industries). The blend evens that out.

| Sector | Stocks | Current avg | Blend avg | Shift |
|---|---|---|---|---|
| NBFC | 77 | 67.6 | 55.6 | -12.0 |
| Financial Services | 122 | 57.6 | 52.6 | -5.0 |
| Energy | 57 | 57.6 | 52.8 | -4.8 |
| Real Estate | 88 | 53.5 | 51.0 | -2.5 |
| Banking | 27 | 54.7 | 53.6 | -1.1 |
| IT Services | 144 | 50.7 | 50.4 | -0.3 |
| Industrials | 482 | 47.9 | 49.5 | +1.6 |
| Metals & Materials | 393 | 47.2 | 49.0 | +1.8 |
| Pharma & Healthcare | 178 | 47.0 | 48.9 | +1.9 |
| Telecom & Media | 57 | 48.2 | 50.3 | +2.1 |
| Utilities | 42 | 47.5 | 49.6 | +2.1 |
| FMCG | 165 | 47.0 | 49.6 | +2.6 |
| Consumer Discretionary | 343 | 45.5 | 48.7 | +3.2 |
| Automobile | 115 | 45.2 | 48.5 | +3.3 |
| Electronics | 25 | 41.3 | 47.1 | +5.8 |

## Verdict changes (rows: current, columns: blend)

| current \ blend | Fair | Strong | Weak |
|---|---|---|---|
| Fair | 902 | 146 | 110 |
| Strong | 76 | 236 | 0 |
| Weak | 179 | 0 | 703 |

## Large caps that gain most

| symbol | sector | current | relative | blend |
|---|---|---|---|---|
| BOSCHLTD | Automobile | 41 | 61 | 55 |
| ADANIGREEN | Utilities | 25 | 42 | 37 |
| ABB | Industrials | 48 | 65 | 60 |
| POLYCAB | Industrials | 48 | 65 | 60 |
| CUMMINSIND | Industrials | 45 | 61 | 56 |
| SIEMENS | Industrials | 40 | 56 | 51 |
| PIDILITIND | Metals & Materials | 43 | 59 | 54 |
| VBL | FMCG | 44 | 60 | 55 |

## Large caps that lose most

| symbol | sector | current | relative | blend |
|---|---|---|---|---|
| CHOLAFIN | NBFC | 69 | 39 | 48 |
| BAJFINANCE | NBFC | 67 | 43 | 50 |
| JIOFIN | Financial Services | 56 | 34 | 41 |
| PFC | NBFC | 79 | 59 | 65 |
| TATACAP | NBFC | 65 | 46 | 52 |
| SHRIRAMFIN | NBFC | 63 | 52 | 55 |
| MUTHOOTFIN | NBFC | 85 | 74 | 77 |
| BPCL | Energy | 52 | 40 | 44 |

## Reading this

- A purely relative score answers "how good is this company *for its sector*" — every
  sector then averages ~50, which hides that some industries are genuinely better
  businesses. The blend keeps 30% of the absolute view for that reason.
- Relative sub-scores need enough peers: sectors under 10 usable values use the whole
  market (benchmarks.MIN_PEERS).
- Decision needed before switching: blend weight, and whether the frontend's
  `lib/scoring.ts` mirror moves to the API (it can't compute peer percentiles itself).
