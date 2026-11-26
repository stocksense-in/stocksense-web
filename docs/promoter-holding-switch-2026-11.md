# Promoter holding: switch the score from Yahoo to filed shareholding patterns?

*26 Nov 2026 — decision memo. Nothing has been published; switching is one command.*

## The problem

The StockSense score gives promoter holding a 10% weight. Today the number comes from
Yahoo's `heldPercentInsiders`, which is not what Indian filings mean by promoter holding
(the founders or parent company and their group). The filed figure is in every company's
quarterly shareholding pattern, which StockSense now ingests (M1.3).

## What the comparison shows (1,345 companies so far)

| | |
|---|---|
| Median gap between Yahoo and the filed figure | **5.3 points** |
| Companies off by more than 5 points | **665 (49%)** |
| Companies off by more than 20 points | **161** |
| Score change if switched: median | 1 point |
| Score change: companies moving 5+ points | 81 (largest +11 / −12) |

Examples of the gap: FACT — 90% government-owned, Yahoo 0%. Bharat Rasayan and GKW —
75% promoter-held, Yahoo 0%. ITC — no promoter group at all, Yahoo 29%. Hindustan Zinc —
61% filed, Yahoo 89%.

The filed figures are checked: every pattern adds to 100%, and the summary matches the
filed XBRL pattern exactly for 45 of 45 sampled large caps (`ml/checks/shareholding_spot_check.py`).

## Why switching this one metric now is safe

Scores compare each company with its sector peers, so a metric should switch only when
peers share one definition. Shareholding patterns cover the whole listed universe (the
first full pass finishes tonight), unlike quarterly results (50 companies so far). Margin,
growth, ROE and debt to equity stay on Yahoo until results coverage catches up.

Companies whose latest pattern is over 200 days old (suspended or non-filing, mostly NSE's
BZ series) keep their current value.

## The command

```
python -m stocksense rescore --fundamentals filings --metrics promoter            # compare (no writes)
python -m stocksense rescore --fundamentals filings --metrics promoter --apply    # publish
```

After publishing, the weekly engine run keeps patterns current; re-run the command after it
(or add it to the weekly steps) so new patterns reach the score.

## Recommendation

Switch promoter holding to filed patterns once the universe pass completes. It corrects a
wrong input for about half the market at the cost of a small, explainable score change.
