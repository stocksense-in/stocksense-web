import { MetricKey } from './types';

export interface MetricCardContent {
  insight: string;
  risk: string;
}

export interface MetricMediumContent {
  why: string;
  priceImpact: string;
  risks: string[];
}

export interface MetricFullContent {
  coreInsight: string;
  mechanism: string;
  sector: string;
  drivers: string;
  risks: string[];
  fakeSignals: string[];
  verdict: string;
}

export interface MetricLayerContent {
  card: MetricCardContent;
  medium: MetricMediumContent;
  full: MetricFullContent;
}

// Covers all MetricKeys + cfo for future use
export const METRIC_CONTENT: Record<MetricKey | 'cfo', MetricLayerContent> = {

  pe: {
    card: {
      insight: 'Market is paying this much for every ₹1 of earnings — high PE means high expectations already priced in.',
      risk: 'Any earnings miss at elevated PE triggers double-digit de-rating, not a dip.',
    },
    medium: {
      why: 'PE is not a valuation number — it is a market consensus statement about future earnings. A high PE means institutional investors already expect flawless execution. A low PE either signals undervaluation or a deteriorating earnings trajectory. The difference determines whether you are buying value or catching a falling knife.',
      priceImpact: 'PE affects price through two mechanisms simultaneously: earnings revision (EPS changes) and multiple re-rating (how much the market is willing to pay per rupee of earnings). A guidance cut at high PE triggers both — EPS estimate drops AND the multiple compresses. This double-negative is why high-PE stocks can fall 30-40% on a single quarter miss.',
      risks: [
        'Elevated PE + negative earnings surprise = multiple contraction + EPS cut firing simultaneously. Institutional exits are non-gradual.',
        'FII-driven PE expansion across a sector masks individual company weakness — when FII flows reverse, all PEs compress regardless of fundamentals.',
        'Trailing PE is misleading in cyclicals — strip commodity supercycle earnings before applying the ratio.',
      ],
    },
    full: {
      coreInsight: 'PE is a forward earnings contract disguised as a ratio. Its level only matters relative to the sector ceiling and earnings trajectory — in isolation it tells you nothing.',
      mechanism: 'Re-rating catalyst: consecutive positive earnings surprises with PE below sector average → institutional demand → multiple expansion on top of EPS growth. De-rating cascade: guidance reduction at premium PE → consensus EPS revised down → PE ceiling re-priced lower → forced selling by growth mandates → gap-down, not a grind. At high PE, the risk is asymmetric: upside is capped by the existing premium, downside is unbounded if the earnings narrative breaks.',
      sector: 'Banking: PE is secondary — P/B and NIM quality govern. A 15× bank PE tells you nothing without NPA context. New-age: standard PE is inapplicable pre-profitability — use P/S or EV/GMV. FMCG: 40-50× is structurally normal given earnings visibility and pricing power. Commodities: PE is cycle-distorted — supercycle EPS inflates denominator, compressing PE artificially into a value-trap.',
      drivers: 'Three forces move PE: (1) Earnings surprises — positive surprises expand multiples, any miss compresses them. (2) RBI repo rate — the single largest macro lever; rate cuts expand PE across markets, hikes compress them universally. (3) FII flows — large sector inflows mechanically lift PEs of all constituents regardless of individual quality. A rising-PE stock during FII inflow periods is not re-rating on merit.',
      risks: [
        'PE above sector ceiling with no earnings acceleration catalyst = pure sentiment premium, maximum de-rating exposure.',
        'Low PE from one-time gains (asset sales, deferred tax reversal) — strip non-recurring items; the real operating PE may be 2× higher.',
        'Sector-level PE compression disguised as individual stock cheapening — buying "cheap vs own history" in a de-rating sector is not value investing.',
        'Forward PE rising every quarter on declining earnings — historical PE becomes irrelevant, only trough-earnings forward PE matters.',
      ],
      fakeSignals: [
        '"Cheap PE" value trap: reported earnings inflated by non-recurring items. Real operating PE is significantly higher once stripped.',
        'Low PE in a cyclical commodity company at peak cycle — the denominator (EPS) will mean-revert; the PE will spike when it does.',
        'Sector rotation de-rating: the stock appears cheap vs its own history, but the entire sector multiple has structurally re-priced lower. Buying on historical PE comparison is the wrong frame.',
      ],
      verdict: 'Strong: PE within sector band + positive earnings surprise history + FII accumulation → multiple expansion probable, add on dips. Average: PE at sector mean, no catalyst → hold, do not add. Dangerous: PE above sector ceiling + rate-hike cycle + any guidance softening → AVOID; the AdjustedScore will be severely compressed by elevated risk.',
    },
  },

  roe: {
    card: {
      insight: 'Shows how many rupees of profit are generated per ₹100 of shareholder capital. The primary compounder identification signal.',
      risk: 'ROE above 30% in capital-intensive sectors almost always includes a leverage or one-time boost — verify the DuPont split.',
    },
    medium: {
      why: 'ROE is the framework\'s primary metric for identifying compounding businesses. It tells you whether management earns more on equity than the cost of that equity (~12-14% in Indian markets). Below 12%, the business destroys long-term shareholder value even as it grows revenue. Above 20% sustained over 3+ years, quality fund mandates re-rate the stock on P/B — not just EPS.',
      priceImpact: 'High and sustained ROE attracts quality institutional mandates — index inclusions, ESG funds, and long-only allocations. These buyers are sticky and slow to exit, creating price support floors during volatility. ROE improvement from 12% to 18% triggers institutional reclassification from "cyclical" to "quality compounder" — a category shift that expands the P/B multiple significantly. Conversely, two consecutive years of ROE decline signals management capital misallocation; quality mandates exit, and the price distribution is non-gradual.',
      risks: [
        'ROE rising while D/E is rising simultaneously — leverage is doing the work, not operations. Fragile in rate-hike environments.',
        'Buyback-inflated ROE: equity base shrinks mechanically, lifting ROE without any operational change. Cross-check with ROCE.',
        'Single-year ROE spike in a cyclical sector — cycle earnings, not business quality. Multi-year average is the only valid signal.',
      ],
    },
    full: {
      coreInsight: 'ROE above 15% confirms the business earns above its cost of equity. Above 20% sustained for 3+ years qualifies as a compounder. It is the single highest-weighted individual metric in the long-term scoring model.',
      mechanism: 'Compounding premium: consistent high ROE attracts quality fund mandates (Nifty 50 inclusions, long-only institutions) who are slow to exit during volatility — creates natural price floor. Re-rating: ROE inflection from below-threshold to above 18% triggers institutional reclassification — P/B expansion occurs separately from EPS growth, creating dual-driver price multiplication. De-rating: declining ROE for 2+ consecutive years activates quality fund exit. The distribution is into a market with declining institutional demand, creating protracted price erosion rather than sharp crashes.',
      sector: 'Banking: ROE is constrained by Basel III capital requirements; 15%+ is exceptional. ROA is the more appropriate profitability metric for banks. IT Services: below 20% ROE signals either margin collapse or cash accumulation without deployment — both are red flags in an asset-light model. Infra/Capital Goods: long asset-payback cycles mean ROE lags revenue by 3-5 years; a 10% ROE with a strong order book is acceptable. New-age: ROE is not interpretable at negative or near-zero equity companies.',
      drivers: 'DuPont decomposition governs ROE: (1) Net Profit Margin — pricing power and cost structure. (2) Asset Turnover — capital efficiency; asset-light models (IT, FMCG) structurally outperform. (3) Financial Leverage — amplifies returns in good times, destroys them in downturns. The critical forensic question: which of these three is driving ROE movement? Leverage-driven ROE with declining margin is a distress setup.',
      risks: [
        'ROE rising while D/E is rising — leverage inflation, not operational quality. Vulnerable to rate hikes and revenue shocks.',
        'Buyback-inflated ROE: equity base reduced without operational improvement. ROCE flat while ROE rises is the tell.',
        'One-year cyclical spike — commodity or auto sector at peak cycle. Mean reversion of cycle EPS will expose the real structural ROE.',
        'Declining ROE despite rising revenue — margin erosion or capital misallocation absorbing the growth benefit.',
      ],
      fakeSignals: [
        'Leverage-inflated ROE: D/E of 2× with 28% ROE is not a compounder — the debt is generating the return. Strip leverage via DuPont; if operating ROE is below 12%, the business earns nothing independently.',
        'Buyback ROE: compare ROE to ROCE. If ROCE is flat or declining while ROE rises, equity reduction (not profit growth) is the cause.',
        'Supercycle ROE in commodities: steel, cement, or oil companies at peak demand report exceptional ROE that evaporates in the following 2-3 years. Single-year ROE is a lagging indicator of cycle position, not business quality.',
      ],
      verdict: 'Strong: >20% sustained 3+ years, D/E below 0.5×, confirmed by operating margin expansion — compounder qualification met, hold core and add on corrections. Average: 12-19% stable → investable but not a compounder; monitor margin direction. Dangerous: <12% or declining trend with management citing macro for 2+ years → capital destruction; the FQ block will suppress AdjustedScore regardless of other metrics.',
    },
  },

  de: {
    card: {
      insight: 'Measures borrowed capital vs shareholder equity. Low D/E = financial resilience; high D/E = amplified losses in downturns.',
      risk: 'Pledged promoter shares + high corporate D/E is the kill-switch combination — exits before any formal distress signal.',
    },
    medium: {
      why: 'D/E measures how much of the company\'s risk is being carried by borrowed money with fixed, senior claims against equity. In a rate-hike cycle or revenue shock, high D/E converts a manageable dip into an existential threat. The framework treats it as the primary balance sheet fragility diagnostic — not a performance measure but a survivability measure.',
      priceImpact: 'Debt reduction through FCF deployment is one of the strongest re-rating catalysts in Indian markets. Markets re-price balance sheet optionality — the ability to acquire competitors in downturns, fund growth without dilution, and survive multiple bad quarters. Conversely, credit rating downgrades triggered by D/E covenant breaches force debt fund liquidation, which cascades into equity selling simultaneously. This cross-asset liquidation creates crashes, not corrections.',
      risks: [
        'High D/E + rising interest rates = operating leverage and financial leverage compounding simultaneously. Even a 15% revenue decline can push interest coverage below 1.0×.',
        'Pledged promoter shares represent shadow D/E not on company books. If stock declines, lenders force-sell pledged shares — triggering a price cascade independent of fundamentals.',
        'Working capital D/E in B2B companies: receivables stretched by government or large corporate customers appear as operating efficiency but are actually funded by bank debt.',
      ],
    },
    full: {
      coreInsight: 'D/E is a survivability metric, not a performance one. It answers: if revenue falls 20%, can this business service its debt and continue operations? The answer determines whether a correction becomes a permanent capital loss.',
      mechanism: 'Re-rating: FCF-funded debt reduction creates re-rating events as the market prices in future financial flexibility. Companies deleveraging from 2× to 0.5× over 3 years have historically re-rated 40-70% on multiple expansion alone. Crash risk: the path is non-linear. A D/E covenant breach triggers bank-mandated asset sales, credit rating downgrades, and concurrent debt-fund liquidation into equity. By the time retail investors see the news, institutional selling is complete. Kill-switch adjacency: promoter pledge >30% with stock near 52-week low is a binary AVOID — no composite score overrides it.',
      sector: 'Banking: D/E is the business model; GNPA, NIM, and CET1 capital adequacy are the correct metrics — do not apply standard D/E. Infra/Capital Goods: 2-4× D/E is sector-normal due to long payback assets; assess against order book coverage and project asset-liability matching. IT Services: near-zero D/E is the baseline; any debt signals either acquisition activity (evaluate quality) or distress (investigate). Energy/Commodities: assess D/E against cycle phase — high debt at commodity cycle peak with declining prices is severe risk.',
      drivers: 'Three root causes: (1) Productive capex debt — capacity expansion backed by visible demand; acceptable if order book covers repayment. (2) Working capital debt — chronic stretching of receivables or inventory buildup; signals business model weakness if persistent. (3) Refinancing/acquisition debt — taking loans to pay dividends or fund premium acquisitions; capital misallocation captured in the Governance sub-block.',
      risks: [
        'D/E rising while revenue growth is flat — debt not generating incremental revenue; either WC deterioration or unproductive capex.',
        'Interest coverage below 3× with D/E above 1.0× — insufficient buffer for any revenue shock; one bad quarter can trigger covenant breach.',
        'Promoter pledge rising concurrently with corporate D/E — both company and promoter are leveraged; compound KILL-01 risk.',
        'Variable-rate debt with rising RBI repo trend — debt service cost expands in real-time, compressing margins every quarter without a business decline.',
      ],
      fakeSignals: [
        '"Debt-free" disguise: off-balance-sheet liabilities (Ind AS 116 lease capitalization, factored receivables, contingent guarantees) make a company look clean while carrying real fixed obligations. Check notes to accounts.',
        'D/E declining via equity dilution (QIP), not debt repayment: the ratio improves arithmetically but absolute debt is unchanged and leverage risk is identical. Always track absolute debt levels alongside the ratio.',
        'Low D/E from under-investment: a company not investing in its business appears debt-free but is harvesting its competitive position. Low D/E + zero capex + declining revenue CAGR = managed decline, not financial health.',
      ],
      verdict: 'Strong: D/E <0.3× with rising interest coverage, zero pledge → balance sheet optionality confirmed; add on dips in down cycles. Average: D/E 0.5-1.0× with stable coverage → investable; confirm sector justification and monitor quarterly. Dangerous: D/E >2.0× with coverage <3× in rate-hike cycle, OR any promoter pledge >30% → AVOID unconditionally — kill-switch territory regardless of composite score.',
    },
  },

  margin: {
    card: {
      insight: 'What percentage of revenue reaches shareholders after all costs. Margin is the operational proof of competitive advantage.',
      risk: 'Revenue growing but margin declining is the most common signal of a business losing pricing power or over-investing to maintain growth.',
    },
    medium: {
      why: 'Net profit margin is the intersection of pricing power, cost efficiency, and competitive advantage. A company growing revenue at 18% annually while margins decline 200bps per year has stagnant EPS growth — the entire revenue effort is being consumed by cost inflation or competitive pressure. Margin is the metric that separates businesses with moats from businesses on treadmills.',
      priceImpact: 'Margin expansion stories are among the most powerful re-rating catalysts in Indian markets. A new-age company inflecting from negative to positive margin can 2-3× as institutional investors reclassify it from "pre-profitability" to "compounding universe." For established companies, 100bps of annual margin expansion compounding over 4 years creates an EPS growth rate that is materially faster than revenue growth alone — the market re-rates the PE multiple simultaneously, amplifying price appreciation.',
      risks: [
        'Commodity input cost spikes (crude, steel, APIs) compress margins faster than pricing adjustments can offset — there is always a lagged pass-through that creates a margin trough.',
        'Competitor pricing pressure in hypercompetitive segments (telecom, quick commerce, generic pharma) erodes margins structurally — these are permanent, not cyclical.',
        'Employee cost inflation in fixed-price contracts (IT, engineering) — wage growth exceeds billing rate growth, creating a multi-year margin headwind that cannot be immediately recovered.',
      ],
    },
    full: {
      coreInsight: 'Margin is the proof of moat, not the measure of growth. Revenue tells you the size of the business; margin tells you whether it has any structural advantage. A business growing top-line without expanding margin is running faster to stay in place.',
      mechanism: 'Re-rating: margin expansion confirms pricing power and operational efficiency — both re-rate the PE multiple as institutional investors apply a quality premium. The most powerful re-rating sequence is: negative margin → breakeven → 5% → 12% (new-age platforms), where each threshold shift triggers a reclassification by institutional screeners. Crash risk: downward margin guidance revision causes a de-rating disproportionate to the absolute earnings impact — because the market reprices the entire future earnings stream assuming the deterioration continues. A 200bps margin cut today implies a structurally lower long-term earnings trajectory.',
      sector: 'IT Services: 20-25% operating margin is the sector baseline for large-cap. Below 15% signals pricing pressure or wage inflation exceeding billing rate growth. FMCG: margin above 20% defines the premium tier; pricing power determines whether this is sustainable or cyclical. Auto: 6-10% net margin is healthy given heavy fixed costs and steel exposure; above 12% signals premiumization or EV technology leadership. New-age: absolute net margin is inapplicable pre-profitability — track contribution margin and unit economics instead. Energy/Commodities: cycle-driven, do not interpret without cycle-position context.',
      drivers: '(1) Pricing power — premium brands can pass cost inflation to consumers; commodity businesses cannot and are structurally capped. (2) Operating leverage — fixed costs spread over higher revenue improve margins in upcycles; the reverse is equally powerful and equally fast. (3) Product mix shift — higher-margin product share (specialty pharma vs generics, premium auto vs value) directly lifts blended margin. (4) Input cost structure — companies with commodity inputs are margin price-takers; the macro block tracks crude oil at 25-35% weight precisely for this transmission.',
      risks: [
        'Margin declining while revenue growing — unit economics deteriorating; growth is being bought at the expense of profitability.',
        'Operating margin stable but net margin declining — debt service cost growing faster than operating income; D/E stress accumulating beneath the surface.',
        'Gross margin expanding but operating margin contracting — SG&A and distribution costs consuming gross efficiency gains; management execution problem.',
        'Temporary margin boost from deferred costs (cut R&D, capex, or marketing) — inflates current quarter metric while eroding future competitive position.',
      ],
      fakeSignals: [
        'Net margin boosted by treasury income: IT giants with large cash piles generate significant interest income that inflates net margin above operating margin. Strip other income to see true business margin.',
        'One-quarter margin spike from commodity price lag: a manufacturing company locks input prices 90 days ahead; a sudden commodity correction creates a windfall quarter with zero structural improvement. The following quarter reverts sharply.',
        'Margin "improvement" from deferred capex: cutting maintenance spend flows directly to margin improvement. The CFO/PAT cross-check catches this — if operational cash is not rising alongside reported margin, costs are being deferred, not eliminated.',
      ],
      verdict: 'Strong: net margin >20% sustained with operating leverage evident — pricing power confirmed, hold core position, add in sector corrections. Average: 10-18% stable, sector-appropriate → investable; monitor input cost and competitive environment quarterly. Dangerous: below 5% in a non-new-age company with rising D/E → near-junk; one revenue shock removes all debt service coverage. AVOID unless clear structural turnaround catalyst with verified unit economics.',
    },
  },

  promoter: {
    card: {
      insight: 'Promoter holding reflects founder conviction. High unpledged holding = long-term skin in the game.',
      risk: 'Any promoter pledge above 20% paired with declining stock price is an early warning before any formal distress announcement.',
    },
    medium: {
      why: 'Promoter holding is a behavioral signal more than a financial ratio. Promoters who do not sell are implicitly signalling belief in future value. The critical modifier is pledge percentage — high holding with pledged shares is not a bullish indicator; it is a catastrophic risk disguised as conviction. Zero pledge + high holding is the institutional quality signal.',
      priceImpact: 'Markets re-rate stocks sharply on promoter buying events (positive re-rating) and sell on unexpected promoter selling (de-rating). The asymmetry is strong: a promoter buying 1% open-market triggers a 3-5% re-rating; an unexpected block sale triggers 8-15% de-rating on the same day. SEBI\'s real-time disclosure mandate means institutional investors act before retail investors process the news.',
      risks: [
        'Pledged promoter shares: if stock declines, lenders force-sell pledged collateral, triggering a price cascade that is independent of business fundamentals — the kill-switch condition.',
        'Creeping dilution via ESOP or QIP issuances steadily erodes EPS even when reported profits grow, and reduces effective promoter conviction without the block-sale signal.',
        'VC lock-in expiry for new-age platforms: institutional "promoters" with planned exit timelines create concentrated selling pressure that retail can observe in bulk deal disclosures.',
      ],
    },
    full: {
      coreInsight: 'Promoter holding is a governance proxy, not a valuation metric. The only version that supports conviction sizing is: high holding (>45%) + zero pledge + no creeping dilution. Any other combination requires deeper governance investigation before capital allocation.',
      mechanism: 'Re-rating: open-market promoter buying in quantity signals asymmetric information — the promoter believes the market is mispricing the stock. Institutional investors interpret this as a fundamental catalyst and begin accumulation, creating a sustained re-rating. De-rating: block deal without advance notice is always bearish — it signals promoter is reducing exposure before a negative event that has not yet reached consensus. Cascade risk: pledge-triggered force selling is the most violent price event in Indian small and mid caps — examples include Yes Bank, DHFL, and multiple ADAG group companies where the cascade was irreversible once initiated.',
      sector: 'Banking: RBI mandates cap at 26% — zero promoter holding is standard, not a risk. Evaluate FII/DII quality instead. New-age (VC-backed): VCs are classified as promoters with planned exit mandates. Low holding is structural; monitor bulk deal disclosures and lock-in expiry schedules. IT Services: institutional governance model (Infosys, TCS) with 12-15% founder holding and high FII ownership is the quality benchmark — low absolute holding compensated by institutional confidence.',
      drivers: '(1) Founder vision: founders staying invested post-IPO signals long-term compounding belief — routine exits 5-7 years post-IPO are not alarming. (2) Institutional compensation: high FII/DII ownership offsets low promoter holding; TCS and Infosys models demonstrate this. (3) Corporate governance quality: independent board, audit committee effectiveness, and RPT disclosure quality matter more than raw holding %. (4) Dividend consistency: regular dividends to promoters confirm the business generates genuine cash — not accounting-driven.',
      risks: [
        'Pledged shares cascade: lender force-sell on declining collateral value creates price independent of business quality — KILL-01 condition.',
        'Creeping ESOP dilution: gradual equity expansion reduces effective promoter concentration without triggering block-sale disclosure requirements.',
        'Related-party transactions extracting minority shareholder value — captured in Governance sub-block but often visible only in detailed notes to accounts.',
        'Sudden promoter reduction via institutional placement — insider information asymmetry means the seller knows something the buyer does not.',
      ],
      fakeSignals: [
        'High promoter holding inflated by cross-holdings: group companies holding each other\'s shares (circular cross-holdings) inflate effective promoter holding without increasing economic exposure. Check the actual beneficiary ownership structure.',
        'Promoter "buying" via fresh allotment at discount: rights issues and preferential allotments can show promoter stake increasing while actual cash contribution is minimal relative to market price.',
        'Low holding as "intentional institutional model": a popular narrative that ignores the real risk — if institutional holders exit simultaneously (mandate change, index rebalancing), there is no promoter buffer below to stabilise price.',
      ],
      verdict: 'Strong: >45% holding, zero pledge, no bulk deal history → governance aligned, add on dips. Average: 30-44% with institutional backing >20% FII → acceptable; verify pledge status in CDSL/NSDL. Dangerous: any pledge >20% with stock in 12-month downtrend, OR promoter holding declining without explanation → governance red flag; exit or avoid before formal distress signals emerge.',
    },
  },

  cagr: {
    card: {
      insight: '3-year compounded revenue growth rate. Businesses with high ROE AND high CAGR are the true compounders in Indian markets.',
      risk: 'Inorganic CAGR (acquisition-driven) inflates the metric without confirming organic competitive advantage.',
    },
    medium: {
      why: 'Revenue CAGR is the velocity indicator. It tells you whether the business is gaining real market share (growing faster than GDP + sector growth) or just existing. The framework\'s compounder thesis requires both high ROE and high CAGR — one without the other is incomplete. High CAGR with low ROE means growth is not profitable; high ROE with low CAGR means the business is efficient but shrinking in relative economic importance.',
      priceImpact: 'Consistently high CAGR companies attract institutional re-rating via two simultaneous drivers: EPS growth from the expanded revenue base AND PE multiple expansion as the market prices in future growth continuation. This dual driver is the engine of 5-10× wealth creation in Indian markets. Deceleration from high CAGR to average CAGR (e.g., 35% to 15%) triggers a severe de-rating as growth mandates exit — the PE multiple they paid assumed continued elevated growth.',
      risks: [
        'Revenue CAGR concentrated in a single customer or government contract — any renewal failure or payment delay collapses growth trajectory immediately.',
        'High CAGR in cyclical sectors (steel, cement, infra) reverses sharply with the commodity cycle — mean reversion risk is structural.',
        'CAGR outpacing margin expansion — growth is not translating to profitability; the business may be buying market share at the expense of unit economics.',
      ],
    },
    full: {
      coreInsight: 'Revenue CAGR above 12% confirms the business is growing faster than India\'s nominal GDP, indicating real market share gains. Below 8% in real terms, the business is shrinking in economic relevance. The metric has its highest impact in the compounder horizon where FQ dominates the scoring formula.',
      mechanism: 'Re-rating: consistent high CAGR with margin expansion creates the dual driver of EPS growth + PE expansion. A business growing at 25% CAGR for 5 years at stable margins delivers EPS compounding that forces institutional re-rating — Nifty inclusion, style box reclassification, and fresh mandate entries all pile into the same stock. De-rating: CAGR deceleration is the single most common trigger for growth-mandate exits. The exit is front-run by institutional investors who model forward CAGR using earnings call guidance tone — retail investors typically exit 2-3 quarters after the deceleration is confirmed by actuals.',
      sector: 'New-age: 40%+ CAGR is the category expectation; deceleration below 30% triggers severe de-rating as the growth premium built into the PE compresses instantly. IT Services: 10-16% is the sector range; above 20% signals market share gains or new geography entry. Banking: 12-18% loan book CAGR reflects credit cycle positioning. Auto: 8-14% is sector norm; above 18% signals EV transition or premiumization leadership.',
      drivers: '(1) Market share gains — capturing competitor revenue is the highest quality growth driver; durable and compounding independent of overall market growth. (2) Geographic expansion — new markets (international, tier-2/3 India) create multi-year CAGR tailwinds. (3) Product innovation — new product lines with superior unit economics raise both revenue and margin trajectory. (4) Industry structural tailwind — riding sector growth (EV, defence, digital infra) adds a sector-level CAGR floor that individual companies benefit from without independent competitive effort.',
      risks: [
        'Customer concentration: top customer >25% of revenue — any churn or renegotiation immediately collapses CAGR.',
        'Inorganic CAGR: acquisition-driven growth inflates the metric without reflecting competitive strength; integrations often destroy margin before CAGR benefit materializes.',
        'Cyclical CAGR at peak cycle: commodity and auto companies report exceptional 3-year CAGR at cycle peaks that mean-revert to near-zero in the following 2 years.',
        'CAGR above margin expansion rate — growth is being subsidized; sustainable only while capital (debt or equity) is available to fund the gap.',
      ],
      fakeSignals: [
        'Acquisition-inflated CAGR: a company that acquired a ₹500 Cr revenue business shows institutional growth in the reported CAGR that has no competitive basis. Organic CAGR (excluding M&A) is the only valid signal.',
        'Base effect distortion: a company recovering from a pandemic or regulatory disruption reports 40-60% CAGR. The absolute revenue level may still be below pre-disruption trend. Compare to 5-year CAGR, not 3-year.',
        'Revenue recognition timing: B2B companies, especially in IT and engineering, can accelerate milestone billing to inflate reported CAGR in one year while CFO/PAT diverges downward — the cash is not arriving at the rate revenue is being recorded.',
      ],
      verdict: 'Strong: >20% organic CAGR with margin stability → compounder confirmation; institutional mandates accumulate, hold and add on corrections. Average: 12-18% CAGR at sector average → investable for SIP/systematic accumulation; not a re-rating candidate without a catalyst. Dangerous: below 8% in nominal terms with no structural recovery catalyst → the business is declining in real economic terms; do not invest on valuation alone without CAGR recovery evidence.',
    },
  },

  // CFO/PAT — not a current MetricKey but included for future metric expansion
  cfo: {
    card: {
      insight: 'Cash conversion quality: how much of reported profit is actually collected as real cash. The forensic audit metric.',
      risk: 'CFO/PAT below 0.6× for 3 consecutive years is an explicit forensic manipulation signal — not a performance concern, a fraud pre-indicator.',
    },
    medium: {
      why: 'CFO/PAT is the framework\'s most important forensic metric. It does not measure how well the business is performing — it audits whether the reported profits are real. A company can legally report growing PAT while collecting zero cash, using aggressive revenue recognition and accrual accounting. CFO/PAT catches this gap. Below 0.6× sustained for 3 years, the framework explicitly flags forensic manipulation risk — not a yellow flag, a red one.',
      priceImpact: 'Companies with CFO/PAT consistently above 1.0× are compounding real cash, not accounting profits. Quality mandates that screen on FCF Yield discover them — creating sustained institutional accumulation and price support. When CFO/PAT deteriorates while reported PAT grows, institutional investors with full cash flow analysis exit before retail participants understand the divergence. The eventual accounting restatement or auditor qualification triggers a 30-60% crash that is non-recoverable in the near term.',
      risks: [
        'CFO/PAT declining for 3 years while PAT rises → explicit forensic manipulation signal; immediate investigation required, not a monitoring note.',
        'Accounts receivable growing faster than revenue → customers are not paying; revenue is being recognized before cash collection is probable.',
        'FCF negative (CFO minus capex) while PAT positive → the business consumes more capital than it earns; every rupee of "profit" is funded by debt or equity issuance.',
      ],
    },
    full: {
      coreInsight: 'Every profitable business must eventually collect its profits in cash. Persistent CFO/PAT divergence below 0.6× for 3 years means one of three things: the company is not collecting receivables, is recognising revenue prematurely, or is masking cost as capital. All three are existential risks to equity holders.',
      mechanism: 'Re-rating: CFO/PAT consistently above 1.0× drives FCF yield re-rating — quality mandates increase FCF Yield screening weight as markets mature. Companies with high FCF yield get re-rated as "capital return" candidates (dividend growth, buyback), creating dual valuation support. Crash sequence: CFO/PAT deterioration below 0.6× creates an information asymmetry — institutions with full cash flow models identify the divergence 2-4 quarters before an auditor qualification or restatement. They exit into a still-rising stock price. The crash when the news breaks is from a higher price base than the fundamental deterioration warrants, amplifying the percentage loss for those who missed the signal.',
      sector: 'IT Services: CFO/PAT should consistently exceed 0.95× — an asset-light service business with milestone billing has no structural reason for cash-profit divergence; anything below 0.8% requires immediate investigation. Real Estate/Infra: structurally lower due to long project cycles and deferred revenue recognition; forensic threshold is more forgiving, but 3-year divergence still signals project cash leakage. Manufacturing: WC-intensive growth phases create natural CFO/PAT pressure — distinguish between WC investment (growth-driven, temporary) and structural cash leakage (business model problem, permanent).',
      drivers: '(1) Receivables stretching — revenue recognised but unpaid; common in government-contractor and B2B companies with weak billing leverage. (2) Inventory buildup — goods produced but not sold, included in profit via production accounting. (3) Accrual inflation — the gap between accrual accounting and cash reality that management can sustain and widen for several years before auditors or market forces intervene. (4) Related-party transactions — sales to affiliate companies recorded as revenue but not cash-settled; the Governance sub-block is designed to cross-reference this.',
      risks: [
        'CFO/PAT below 0.6× for any rolling 3-year window → framework-defined forensic signal; exit or avoid immediately.',
        'FCF negative while PAT positive → capital-destroying operation disguised as profitability.',
        'CFO spike from aggressive Q4 collections followed by Q1 WC rebuild → one-time cash harvest masking chronic underlying weakness.',
        'Rising receivables days (DSO) alongside positive PAT → revenue recognition outpacing collection; the profit number is not economically real.',
      ],
      fakeSignals: [
        'CFO inflated by deferred capex: cutting maintenance spend flows to CFO improvement. Cross-check: if capex is declining while reported CFO rises, the asset base is deteriorating — not business quality improving.',
        'One-year CFO spike from WC reduction: aggressive Q4 collections create a year-end CFO blip. Following year rebuilds WC and CFO reverts. Only 3-year trailing average is valid.',
        'CFO and PAT both distorted by capitalised operating expenses: companies capitalise what should be operating costs (R&D, customer acquisition) — this reduces operating expense (inflating PAT) and increases capex (not affecting CFO). Both numerator and denominator are simultaneously distorted, making the ratio appear acceptable while the underlying manipulation is significant.',
      ],
      verdict: 'Strong: CFO/PAT >1.0× sustained 3+ years with growing FCF yield → earnings quality confirmed; this is the foundation of any compounder thesis; hold through cycles. Average: 0.7-0.95× stable with sector-justified explanation → investable with monitoring; check DSO and inventory days quarterly. Dangerous: below 0.6× for any rolling 3-year window → framework forensic signal; do not wait for auditor qualification; the institutional exit is already underway before the news breaks.',
    },
  },

};
