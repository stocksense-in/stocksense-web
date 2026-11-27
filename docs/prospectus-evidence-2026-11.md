# Prospectus red flags against real IPO outcomes (M3.7), Nov 2026

The prospectus checker (`backend/stocksense/rhp.py`) reads a red herring prospectus and raises 12 kinds of red flag. This note covers whether those flags would have warned you off IPOs that went on to do badly. The full tables are in `ml/reports/ipo-flags-2026-11-28.md`.

## What was tested

- **IPOs.** 472 mainboard IPOs listed on NSE since July 2020 were matched to their prospectus on SEBI's site. The match is by company name, within 120 days of the issue opening. 305 prospectuses have been downloaded and scanned so far. SEBI's site stopped resolving from the college network part-way through. A watcher re-runs the download when it's back, and the study is then re-run.
- **Outcomes.** Prices come from the adjusted daily prices in the lake, matched by ISIN.
  - **Listing-day gain:** the close on listing day against the issue price.
  - **Six-month excess return:** return over the six months after listing, minus NIFTY 50's.
  - **Weak:** more than 10 points behind NIFTY 50 after six months.
  - 277 IPOs have six months of trading.
- **Flagged** means the checker raised that flag at medium or high severity.
- **How each flag was judged.** Flagged and clear IPOs were compared on medians, not means, because a few multibaggers drag means around. Each comparison has a bootstrap 95% interval. A flag counts as "worse" only when the whole interval is below zero.
- **How all flags together were judged.** A logistic regression was fitted on IPOs listed before 2023 and scored on later ones (AUC).

## The checker had to be fixed first

The first version raised litigation, criminal-case, regulatory and auditor flags on almost every prospectus. Every prospectus has a litigation chapter and standard wording such as "there are no qualifications". The rules now work from the numbers the prospectus itself reports:

| Rule | How it now decides |
|---|---|
| **Criminal cases** | Uses the litigation summary table. High if cases are against the company or promoters; medium if against directors only. |
| **Litigation** | Compares the amount involved with the company's net worth. High at 10% or more, medium at 2% or more. |
| **Regulatory action** | High if SEBI has acted against the promoters; medium at three or more regulatory cases. |
| **Auditor concerns** | High only for a qualified or adverse opinion, or a disclaimer of opinion. An emphasis of matter is low. |
| **Related-party dealings** | Now reads the standard Risk Factors sentence, "related party transactions to our revenue from operations in Fiscal 2021, 2022 and 2023 was 20.77%, 25.39% and 16.18%". It now fires on 33 prospectuses, not 1. |

Sentences that deny something, or describe something that only might happen, no longer count. The test is on the sentence the match sits in.

## What we found

- **Six months after listing, no single flag reliably predicts a weak IPO.** Several flags point that way:

  | Flag | Median six-month excess return, flagged | Rest |
  |---|---:|---:|
  | Related-party dealings | −17% | −4% |
  | Supplier concentration | −14% | −3% |
  | Regulatory action | −10% | −3% |

  But every interval crosses zero, so none of these gaps can be told apart from chance yet.
- **Listing day is different.** Two flags go with a clearly weaker debut:

  | Flag | Close on listing day vs the rest (median) | 95% interval |
  |---|---:|---|
  | Criminal cases | 11 points lower | −16 to −4 |
  | Large litigation | 9 points lower | −15 to −3 |

- **The flags together don't help.** Scored on IPOs from 2023 on, the checker's own count of findings has an AUC of 0.55; 0.5 is a coin toss. The regression does no better (0.47), and nor does market mood before listing. The pre-2023 training set is only 63 IPOs, so this part will improve as more prospectuses come in.

## What changed in the product

The study did not give any rule a weight, so we did not reweight the rules. A flag's severity still describes how serious the disclosure is. Instead, every finding now carries its **track record**: a sentence from the study saying how past IPOs with that flag actually did.

For example, the criminal-case flag now says flagged IPOs did no worse over six months, but closed a median 11 points lower on listing day. The track records live in `backend/data/rhp_evidence.json`. The checker page shows them under each finding.

The IPO page now shows the medium and high flags from each recent listing's prospectus, with a link to the prospectus (`backend/data/ipo_prospectus.json`).

## Re-running

```powershell
cd backend; python -m stocksense ingest-rhp          # download new prospectuses, scan, export
cd ..; backend\.venv-ml\Scripts\python.exe ml\ipo_flags.py   # study, report, evidence file
```

`ingest-rhp --no-download` rescans what's already saved, for example after a rule changes.
