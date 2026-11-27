# Filings Q&A citation test — 28 Nov 2026

50 test questions about 12 IPO prospectuses (`ml/data/filings_qa_questions.json`), answered by `stocksense.filings_qa`: BM25 over the pages of the company's prospectus, with the company's name counting half and plain English mapped to prospectus terms.

**The top page cites the answer for 56% of questions**, which misses the PLAN's 80% bar. One of the top 3 pages does for 80%, and the top 5 for 88%. So search alone won't meet the bar; an LLM reading the top 5 pages could. (Dev set, 90 questions about 27 other prospectuses: 44%, 79%, 90%.)

| Test set | Questions | Hit@1 | Hit@3 | Hit@5 |
|---|---:|---:|---:|---:|
| All | 50 | 56% | 80% | 88% |
| Kind: brlm | 9 | 89% | 100% | 100% |
| Kind: registrar | 9 | 56% | 89% | 100% |
| Kind: auditor | 8 | 75% | 88% | 88% |
| Kind: net_worth | 8 | 25% | 38% | 50% |
| Kind: criminal | 8 | 25% | 75% | 88% |
| Kind: incorporated | 8 | 62% | 88% | 100% |
| Phrasing: prospectus words | 25 | 60% | 84% | 92% |
| Phrasing: plain English | 25 | 52% | 76% | 84% |

The plain-English questions reuse a few templates, and the glossary was written knowing them, so real readers' plain-English questions will do worse than the plain-English row.

## What each part adds

| Search | Test hit@1 | @3 | @5 | Dev hit@1 | @3 | @5 |
|---|---:|---:|---:|---:|---:|---:|
| As shipped | 56% | 80% | 88% | 44% | 79% | 90% |
| No glossary | 54% | 76% | 82% | 39% | 71% | 84% |
| Company name dropped | 40% | 70% | 82% | 36% | 77% | 93% |
| Company name at full weight | 60% | 86% | 94% | 48% | 74% | 84% |

Word pairs ("registrar offer") and re-ranking pages where the question's words sit close together were tried on the dev set and didn't help, so they're not used.

## Settings (chosen on the dev set only)

BM25's b decides how much long pages are marked down; cover pages and summary tables are long and hold many answers. The name weight is how much the company's own name counts in the question. Both were chosen on the dev set, never on the test questions: b = 0.0, name weight 0.5 (the best top-3 rate, and a better top page than dropping the name for a small loss in the top 5).

| Dev set | Hit@1 | Hit@3 | Hit@5 |
|---|---:|---:|---:|
| b = 0.75 | 22% | 67% | 82% |
| b = 0.5 | 24% | 69% | 87% |
| b = 0.25 | 31% | 72% | 88% |
| b = 0.0 | 44% | 79% | 90% |
| name weight 0.0 | 36% | 77% | 93% |
| name weight 0.25 | 33% | 77% | 91% |
| name weight 0.5 | 44% | 79% | 90% |
| name weight 0.75 | 49% | 76% | 89% |
| name weight 1.0 | 48% | 74% | 84% |

## Test questions the top page missed

| Question | Answer | Answer on pages | Cited |
|---|---|---|---|
| How many criminal cases are pending against Dharmaj Crop Guard? | 1 | 28, 43 | 311, 313, 43, 314, 312 |
| When was Muthoot Microfin incorporated? | April 6, 1992 | 3, 89, 226, 445, 500 | 254, 3, 182, 226, 294 |
| Which investment banks are running Muthoot Microfin's share sale? | ICICI Securities Limited | 2, 3, 10, 13, 81, 132 … | 486, 3, 86, 464, 480 |
| Who is the registrar to Muthoot Microfin's offer? | KFin Technologies | 2, 3, 15, 16, 81 | 500, 3, 492, 15, 464 |
| Which audit firm signs off Muthoot Microfin's accounts? | Sharp & Tannan Associates | 8, 80, 85, 102, 105, 112 … | 241, 501, 240, 223, 192 |
| How much is Muthoot Microfin's net worth? | 18,420.95 | 27, 73, 77, 117, 189, 262 … | 116, 391, 452, 263, 78 |
| Is Suraksha Diagnostic facing any criminal proceedings? | 0 | 26, 43, 382 | 384, 385, 382, 381, 383 |
| What is Suraksha Diagnostic's net worth as per the restated financial information? | 1,870.50 | 23, 83, 300, 342, 377 | 127, 24, 394, 395, 381 |
| How many criminal cases are pending against Sai Parenteral's? | 0 | 34, 49, 50 | 413, 407, 411, 60, 410 |
| When was Global Surfaces incorporated? | August 23, 1991 | 2, 84, 213, 258, 331, 400 | 220, 331, 5, 214, 258 |
| Which firm handles share allotment and refunds for Sai Parenteral's IPO? | Bigshare Services | 2, 3, 15, 16, 103 | 436, 296, 445, 473, 3 |
| Who are Sai Parenteral's statutory auditors? | R Kabra & Co. | 2, 5, 38, 39, 73, 74 … | 401, 502, 5, 105, 33 |
| How much is Sai Parenteral's net worth? | 2,093.71 | 33, 95, 171, 173, 231, 312 … | 226, 225, 232, 170, 175 |
| Which firm handles share allotment and refunds for JNK India's IPO? | Link Intime India | 1, 2, 12, 89 | 87, 400, 2, 1, 373 |
| How much is JNK India's net worth? | 1,685.61 | 24, 81, 256, 306, 308, 310 | 122, 309, 24, 362, 121 |
| How many criminal cases are pending against Global Surfaces? | 0 | 29, 48, 326 | 329, 326, 327, 48, 325 |
| How much is Gandhar Oil Refinery (India)'s net worth? | 8,107.93 | 21, 22, 89, 95, 288, 362 … | 146, 463, 16, 3, 551 |
| Is Sambhv Steel Tubes facing any criminal proceedings? | 0 | 27, 91, 491, 492 | 494, 493, 492, 491, 91 |
| Which firm handles share allotment and refunds for Global Surfaces' IPO? | Bigshare Services | 1, 2, 13, 14, 85, 86 | 345, 352, 2, 379, 377 |
| How much is Global Surfaces' net worth? | 1,489.30 | 28, 81, 254, 299, 302 | 134, 138, 133, 301, 28 |
| How many criminal cases are pending against Bansal Wire Industries? | 0 | 29, 55 | 395, 396, 397, 55, 82 |
| When was Abans Holdings incorporated? | September 24, 2009 | 2, 75, 142, 144, 164, 177 … | 183, 184, 41, 198, 158 |
