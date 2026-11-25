# Fundamentals from filings — verification and score comparison (M1.2, Nov 2026)

## What was built

`clean/financial_results` holds every quarterly result a company has filed with NSE,
standalone and consolidated, from 2005 to Sep 2026, in ₹ crore:

- **2005 → Dec 2024** from NSE's results endpoint (`sources/nse_results.py`).
- **Mar 2025 → now** from SEBI's integrated filing (`sources/nse_integrated.py`), one
  XBRL file per filing. Half-year filings include the balance sheet.

13 of the 20 largest companies are in (1,580 filings). The rest wait for a rerun: NSE
started timing out every request mid-run on 25 Nov, and the job was stopped rather than
kept retrying.

## Check against published annual results

`ml/checks/results_spot_check.py` sums four quarters per fiscal year (FY2023–FY2026) and
compares them with Yahoo's annual income statement.

**53 of 63 judged comparisons are within 2% (84%): profit 34 of 38, revenue 19 of 25.**
TCS, Reliance, Bharti, ICICI Bank, L&T (FY24–26) and Sun Pharma match to the crore.
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
  (actual ≈ ₹35,850 crore). Quarters more than 10× off their neighbours are flagged
  `suspect` and left out of sums.
- **Placeholders.** Bajaj Finance's Dec 2022 consolidated filing has the owners'-profit
  field as "0", with the real figure in another field.
- **Formats.** NSE marks banks "B", NBFCs "F"; insurers file a fourth XBRL taxonomy; NSE
  tagged one Bajaj Finance quarter as a plain company.

## Score comparison

`rescore --fundamentals filings` recomputes every score with margin, 3-year growth, ROE
and debt to equity from filings where available, and Yahoo's values elsewhere. It saves
nothing unless `--apply` is given.

**Across the 13 companies the median score moves 2 points; the largest move is 7
(Hindustan Unilever).** Margins agree closely for non-financials (TCS 18.22% both ways).
The differences are explainable:

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
