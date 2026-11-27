# Fundamentals from filings — verification and score comparison (M1.2, Nov 2026)

## What was built

`clean/financial_results` holds every quarterly result a company has filed with NSE,
standalone and consolidated, from 2005 to Sep 2026, in ₹ crore:

- **2005 → Dec 2024** from NSE's results endpoint (`sources/nse_results.py`).
- **Mar 2025 → now** from SEBI's integrated filing (`sources/nse_integrated.py`), one
  XBRL file per filing. Half-year filings include the balance sheet.

17 of the 20 largest companies are in (2,138 filings). NSE started timing out every
request after long bursts on 25 Nov; the job now stops after three failures in a row and
the weekly engine run picks up the rest.

## Update, 26 Nov: 50 companies

The backfill now covers the 50 largest companies (6,252 filings). On the wider set:
**profit 154 of 168 within 2% (92%)**, revenue 88 of 151 (58%), 76% overall (48 companies).
The revenue misses are systematic: ours is higher in 55 of 63, typically by 2–4%, most at
IOC (+14%) and ITC (+13%), where filed revenue from operations includes excise duty and
Yahoo nets it out, and TVS Motor (+20%, consolidated financing arm). Profit agreeing while
revenue differs one way points to a definition gap, not bad data; a next step is to read
the excise and other-operating-revenue lines and match Yahoo's net revenue.

Excise is now taken out wherever the filing separates it (integrated filings, Mar 2025 on,
where companies list it among other expenses by description): IOC FY2026 matches within
1.3% (was +14%) and ITC within 0.8% (was +13%). Revenue overall: 90 of 151. Years before
FY2026 can't be netted — the old feed lumps excise into other expenses — and ONGC (+9%,
probably royalty/levies), TVS Motor (+18%, consolidated finance arm) and Maruti (+3.5%)
differ for other reasons.

## Check against published annual results

`ml/checks/results_spot_check.py` sums four quarters per fiscal year (FY2023–FY2026) and
compares them with Yahoo's annual income statement.

**78 of 89 judged comparisons are within 2% (88%) across 16 companies: profit 49 of 53,
revenue 29 of 36.** TCS, Reliance, Bharti, ICICI Bank, Axis Bank, Adani Ports, L&T
(FY24–26) and Sun Pharma (FY24–26) match to the crore; the only profit misses are HDFC
Bank's, explained below.
FY2025 sums three quarters from the old feed and one from integrated filings, and it
matches as well as the other years.

The remaining misses:

| Company | What differs | Why |
|---|---|---|
| HDFC Bank, profit (−7% to +8%) | Yahoo's figure | Ours equals the bank's reported consolidated profit (FY23 ₹45,997 cr, FY24 ₹64,062 cr). |
| Bajaj Finance, revenue (+5–8%) | Definition | Our lender revenue = interest income − finance costs + other income; Yahoo nets more. Profit matches exactly. |
| Hindustan Unilever, revenue (+3–4%) | Definition | Probably other operating revenue. Profit matches exactly. |

Shown but not judged: years with only standalone figures (Yahoo is consolidated), bank
revenue (SBI's and Kotak's consolidated other income includes their insurers' premiums,
which Yahoo leaves out), and Infosys (Yahoo reports its statements in USD).

### Data problems found and handled

- **Mixed bases.** Banks filed consolidated results only some quarters. A first version
  summed three consolidated quarters with one standalone and got HDFC Bank's revenue 40%
  wrong. Now a year or trailing window uses one basis, never a mix.
- **Bad filings.** L&T's consolidated Jun 2022 filing reports ₹83 crore of revenue
  (actual ≈ ₹35,850 crore), Sun Pharma's ₹1,921 crore (≈ ₹11,000 crore). Quarters more
  than 4× off their neighbours are flagged `suspect` and left out of sums.
- **Mis-tagged splits.** Adani Ports filed its other-comprehensive-income split as the
  Jun 2025 profit split (₹53 crore to owners on ₹3,311 crore profit). When owners' plus
  minority share doesn't add up to the period's profit, the total is used.
- **Placeholders.** Bajaj Finance's Dec 2022 consolidated filing has the owners'-profit
  field as "0", with the real figure in another field.
- **Formats.** NSE marks banks "B", NBFCs "F"; insurers file a fourth XBRL taxonomy; NSE
  tagged one Bajaj Finance quarter as a plain company.

## Score comparison

`rescore --fundamentals filings` recomputes every score with margin, 3-year growth, ROE
and debt to equity from filings where available, and Yahoo's values elsewhere. It saves
nothing unless `--apply` is given.

**Across the 17 companies the median score moves 2 points; the largest move is 13
(Titan).** Margins agree closely for non-financials (TCS 18.22% both ways). The
differences are explainable:

- **Filings fill gaps.** Titan has no ROE in the stored Yahoo data; from filings it is
  45%, which (with lower D/E) lifts its score from 38 to 51. HUL (+7) is the same story.

- **Debt to equity** is 0 from filings for TCS, Infosys and HUL, against Yahoo's 0.03–0.10.
  Yahoo counts lease liabilities as debt; filings' "borrowings" don't include them.
- **Growth** uses trailing-twelve-month revenue over exactly three years; Yahoo's uses
  annual statements. HDFC Bank's jumps (23% vs 17%) because of the 2023 HDFC Ltd merger.
- **Banks' ROE** stays Yahoo's: bank filings carry no balance sheet in the results XBRL.

## Decision

The published score stays on Yahoo for now. Filing-based inputs exist for only 13
companies, so switching would compare those 13 on one definition against their peers on
another. Next: finish the 20, then extend to the whole universe and switch once peers
share a definition. Point-in-time history also makes the blend-ratio backtest possible
(PLAN §9).

## Update, 27 Nov: the whole market

The results run now covers every listed equity: **17,301 filings for 2,347 companies**, with
filing-based inputs (latest four quarters) for 2,094 of them. Most companies have only their
last five filings (`--all --recent 5`), which is enough for margin, ROE and debt to equity but
not for three-year growth, so growth comes from filings for 48 companies and stays Yahoo's
elsewhere.

`rescore --fundamentals filings` (comparison only, nothing saved), excluding the promoter metric,
which has its own memo:

| | Results-based inputs only | Plus filed promoter holding |
|---|---|---|
| Companies scored both ways | 2,005 | 2,243 |
| Median score move | 1 | 1 |
| Within 2 points | 85% | 71% |
| Within 5 points | 94% | 91% |
| Verdict band changes (Strong / Fair / Weak) | 98 (5%) | 174 (8%) |
| Largest move | 28 | 27 |

Input agreement where both sources have a figure: margin within 1 point for 87%, ROE within 2
points for 93%, debt to equity within 0.1 for 85%. Filings add ROE for 92 companies and debt to
equity for 49 that Yahoo leaves blank.

Where they differ, it's mostly definitions, not errors:

- **Debt to equity 0 in filings, above 0 on Yahoo** (51 companies above 0.1): debt-free
  companies with lease liabilities. Yahoo counts leases as debt; filed borrowings don't (Bata
  1.1 vs 0, CRISIL, 3M India, AstraZeneca). For a beginner's "how much has it borrowed", the
  filed figure is the honest one.
- **Big moves come from one-off items in tiny companies.** ABREL's trailing margin is +64% on
  Yahoo and −53% in filings (an exceptional item in different quarters); PROZONER's 282% Yahoo
  margin comes from a one-off gain the filed latest four quarters no longer include.
- 21 companies' filing figures are older than the publishing limit
  (`filing_metrics.MAX_AGE_DAYS`); `--apply` keeps their current values.

## Decision, 27 Nov

Peers now share a definition, which was the condition set on 25 Nov: 2,094 companies have
filed inputs, and those without them are mostly the smallest and newest. Switching moves the
median score by 1 point and changes the verdict band for 5% of companies. It is one command:

    python -m stocksense rescore --fundamentals filings --metrics net_margin cagr roe de --apply

Switching writes to Supabase, so it waits for an explicit go-ahead, as does the promoter switch
(`docs/promoter-holding-switch-2026-11.md`). Filing-based growth needs the older quarters:
a `--all` backfill (without `--recent`) takes several nights at NSE's pace.

