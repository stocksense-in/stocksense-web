import { MetricKey } from './types';

export interface MetricIntel {
  definition: string;
  sectorAvg: (sector: string) => { avg: string; top: string; label: string };
  trend: (val: number, sector: string) => { direction: 'improving' | 'stable' | 'declining'; insight: string };
  rangeLogic: (sector: string) => string;
  risks: string[];
  drivers: { label: string; desc: string }[];
  impact: string;
  action: (val: number, sector: string) => { label: string; color: 'green' | 'gold' | 'red'; text: string };
}

export const METRIC_INTEL: Record<MetricKey, MetricIntel> = {
  pe: {
    definition:
      'Price-to-Earnings ratio measures how much you pay for every rupee of the company\'s annual profit. ' +
      'A PE of 24 means you\'re paying ₹24 for ₹1 of earnings. It signals market expectations — premium PEs imply high growth expectations, while low PEs may indicate undervaluation or structural risk.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '14–18×', top: '20–22×', label: 'Private Banks' }
      : s === 'newage'? { avg: 'N/A–200×', top: '300×+', label: 'New-Age Tech' }
      : s === 'it'    ? { avg: '22–28×', top: '30–38×', label: 'IT Services' }
      : s === 'auto'  ? { avg: '10–18×', top: '20–25×', label: 'Auto OEM' }
      :                 { avg: '18–28×', top: '30×+', label: 'Indian Equities' },

    trend: (v, s) =>
      s === 'newage' ? { direction: 'stable', insight: 'New-age PE multiples remain elevated; driven by growth expectations, not current earnings. Monitor path to profitability.' }
      : v < 15 ? { direction: 'improving', insight: 'Compressed PE may indicate recent earnings growth outpacing price. Strong signal if fundamentals intact.' }
      : v < 28 ? { direction: 'stable', insight: 'PE within the fair-value corridor. Market pricing in steady growth without speculative excess.' }
      :           { direction: 'declining', insight: 'Elevated PE increases downside risk if earnings miss estimates. Any guidance cut can compress the multiple sharply.' },

    rangeLogic: (s) =>
      s === 'bank'
        ? 'Banks are valued on book value (PB) and NIM quality — PE of 12–20× is standard. Above 22× signals excessive optimism.'
        : s === 'newage'
        ? 'Hyper-growth companies price in 5–10 year earnings. Standard PE is irrelevant — use EV/GMV or PS ratio instead.'
        : 'Earnings quality and sector growth rate determine the fair PE band. 10–28× captures value-to-moderate-growth stocks. Above 30× requires visible earnings acceleration to justify.',

    risks: [
      'If earnings disappoint, a high PE compresses violently — "multiple contraction" can erase 30–40% in weeks.',
      'Artificially low PE due to one-time gains creates a "value trap" — the real PE is much higher.',
      'Forward PE vs trailing PE divergence indicates analyst optimism that may not materialize.',
      'Sector rotation by FIIs can de-rate entire sector PEs regardless of individual company performance.',
    ],

    drivers: [
      { label: 'Earnings Growth', desc: 'Higher EPS growth justifies higher PE. Market pays a premium for compounding earnings.' },
      { label: 'Sector Tailwinds', desc: 'Sectors with structural growth (EV, defence, digital infra) command PE premium vs cyclicals.' },
      { label: 'Interest Rates', desc: 'High rates compress PE as risk-free return rises. Rate-cut cycles expand multiples.' },
      { label: 'Promoter / FII Confidence', desc: 'High institutional ownership and promoter confidence support sustained premium valuation.' },
    ],

    impact:
      'PE directly governs entry price risk. Buying at a high PE locks you into an assumption of flawless execution. ' +
      'For long-term investors, mean reversion is a constant force — sectors rarely sustain extreme multiples for more than 2–3 years without earnings catching up.',

    action: (v, s) =>
      s === 'newage'
        ? { label: 'Monitor Path to Profit', color: 'gold', text: 'Ignore absolute PE. Track quarterly EBITDA margin trajectory and GMV growth rate.' }
        : v < 15
        ? { label: 'Potential Value Entry', color: 'green', text: 'Low PE with strong fundamentals — investigate whether it\'s undervaluation or earnings risk before entering.' }
        : v < 28
        ? { label: 'Fair Value Zone', color: 'green', text: 'Reasonable entry if revenue and margin trajectory are positive. Not cheap, but not speculative.' }
        : { label: 'Caution — High Multiple', color: 'red', text: 'Entry at this PE demands perfect execution. Any earnings miss triggers severe drawdown. Wait for consolidation.' },
  },

  roe: {
    definition:
      'Return on Equity tells you how many rupees of profit the company generates for every ₹100 of shareholder money deployed. ' +
      'An ROE of 30% means ₹30 earned for every ₹100 of equity. It\'s the purest measure of management\'s capital allocation efficiency — Warren Buffett\'s preferred metric for identifying compounders.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '12–16%', top: '18–22%', label: 'Private Banks' }
      : s === 'newage'? { avg: '2–8%',   top: '10–15%', label: 'New-Age Platforms' }
      : s === 'it'    ? { avg: '22–30%', top: '35–50%', label: 'IT Services' }
      : s === 'auto'  ? { avg: '10–18%', top: '25–40%', label: 'Auto OEM' }
      :                 { avg: '12–18%', top: '25%+',   label: 'Indian Large Cap' },

    trend: (v) =>
      v >= 25 ? { direction: 'improving', insight: 'Top-decile capital efficiency. Compounding at this level creates exponential long-term wealth.' }
      : v >= 15 ? { direction: 'stable', insight: 'Healthy ROE above the quality threshold. Indicates consistent reinvestment returns above cost of capital.' }
      :            { direction: 'declining', insight: 'Below-threshold ROE signals capital is not earning adequate returns. May indicate structural margin pressure or asset bloat.' },

    rangeLogic: (s) =>
      s === 'bank'
        ? 'Bank ROE is constrained by regulatory capital requirements (Basel III). 15%+ is exceptional for banks; compare against CET1 ratios for quality context.'
        : '>15% ROE ensures the business earns above its cost of equity (~12–14% for Indian markets). Below this, value is destroyed for shareholders over time.',

    risks: [
      'High ROE driven by leverage (not operational efficiency) amplifies downside in downturns — always check D/E.',
      'ROE can be artificially inflated by share buybacks that reduce the equity base without improving operations.',
      'Single-year ROE spikes from asset sales or one-time gains are misleading — use 5-year average.',
      'Declining ROE despite revenue growth signals margin erosion or capital misallocation by management.',
    ],

    drivers: [
      { label: 'Net Profit Margin', desc: 'Higher margins directly boost ROE. Pricing power and cost discipline are the levers.' },
      { label: 'Asset Turnover', desc: 'Revenue generated per rupee of assets. Asset-light businesses (IT, FMCG) naturally score higher.' },
      { label: 'Financial Leverage', desc: 'Debt amplifies ROE — productive if funded assets earn more than interest cost, destructive otherwise.' },
      { label: 'Reinvestment Rate', desc: 'Companies reinvesting FCF at high ROE rates compound shareholder wealth geometrically.' },
    ],

    impact:
      'ROE is the single strongest predictor of long-term stock returns in Indian markets. Studies show top-quintile ROE companies outperform the Nifty 500 by 4–7% CAGR over 10-year periods. ' +
      'It drives P/B expansion — the market re-rates high-ROE businesses at premium book values.',

    action: (v) =>
      v >= 25
        ? { label: 'Strong Buy Signal for Long-Term Horizon', color: 'green', text: 'Top-decile compounding machine. Add on dips, hold through cycles. This is the quality moat.' }
        : v >= 15
        ? { label: 'Hold / Accumulate', color: 'green', text: 'Healthy quality threshold met. Monitor that it doesn\'t slip below 15% for 2 consecutive quarters.' }
        : { label: 'Monitor Closely', color: 'gold', text: 'Below quality threshold. Check if it\'s a cycle trough (recoverable) or structural decline before investing.' },
  },

  de: {
    definition:
      'Debt-to-Equity ratio measures how much borrowed capital the company uses relative to shareholder equity. ' +
      'A D/E of 1.0× means ₹1 of debt for every ₹1 of equity. Lower D/E = stronger balance sheet and higher resilience to economic shocks. ' +
      'For banks, this metric is structurally different — banking is inherently a leveraged business.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '8–12×', top: '4–7× (strong)', label: 'Banking (leverage ratio)' }
      : s === 'newage'? { avg: '0.0–0.1×', top: '0×', label: 'New-Age / VC-backed' }
      : s === 'it'    ? { avg: '0.0–0.2×', top: '0×', label: 'IT Services' }
      : s === 'auto'  ? { avg: '0.5–1.5×', top: '<0.5×', label: 'Auto Manufacturing' }
      :                 { avg: '0.3–1.0×', top: '<0.3×', label: 'Indian Large Cap' },

    trend: (v, s) =>
      s === 'bank'
        ? { direction: 'stable', insight: 'Banking leverage is regulatory-governed. Evaluate GNPA and NIM trends instead.' }
        : v < 0.3
        ? { direction: 'improving', insight: 'Near debt-free balance sheet. Maximum financial flexibility — can absorb shocks or fund acquisitions from internal accruals.' }
        : v < 0.8
        ? { direction: 'stable', insight: 'Conservative leverage within manageable bounds. Interest coverage likely healthy.' }
        : { direction: 'declining', insight: 'Elevated leverage increases fixed interest burden. In high-rate environments, this compresses the margin significantly.' },

    rangeLogic: (s) =>
      s === 'bank'
        ? 'Banks borrow to lend — leverage is the core business model. Regulate by GNPA (<2% ideal), CASA ratio (>40% strong) and CET1 capital adequacy (>13%).'
        : 'Below 0.8× keeps interest coverage ratio above 5×, meaning the company earns 5× its interest in operating profit. Beyond 1.5×, risk of debt spiral in rate-hike cycles increases sharply.',

    risks: [
      'High D/E in capital-intensive industries can trigger covenant breaches if revenue falls, forcing distress sales.',
      'Debt taken for unproductive acquisitions (empire building) destroys ROE without improving earnings.',
      'In rising interest rate environments, variable-rate debt directly compresses net margins.',
      'Pledged promoter shares with high debt are a catastrophic risk signal — stock can crash 80%+ overnight.',
    ],

    drivers: [
      { label: 'Capex Cycle', desc: 'Heavy infrastructure investment phases require debt. Watch if debt is productive (capacity expansion) vs defensive (refinancing).' },
      { label: 'Working Capital', desc: 'Poor receivables management inflates working capital debt. Negative WC (FMCG) is a powerful indicator of business quality.' },
      { label: 'Dividend Policy', desc: 'Companies paying high dividends without FCF often borrow to sustain payouts — a red flag.' },
      { label: 'Industry Structure', desc: 'Utilities and infra inherently carry higher debt due to long payback assets. Normalize by sector.' },
    ],

    impact:
      'D/E is the primary balance sheet risk metric. During market crises (COVID 2020, Lehman 2008), highly leveraged companies saw 70–90% drawdowns while debt-free companies recovered 2–3× faster. ' +
      'Pristine balance sheets give management the strategic option to acquire distressed competitors during downturns.',

    action: (v, s) =>
      s === 'bank'
        ? { label: 'Evaluate NIM & GNPA Instead', color: 'gold', text: 'D/E is not the right lens for banks. Use net interest margin, GNPA trend, and CASA ratio for balance sheet quality.' }
        : v < 0.3
        ? { label: 'Balance Sheet Strength: Exceptional', color: 'green', text: 'Near debt-free with full financial flexibility. Add quality context (ROE, FCF) to confirm capital efficiency.' }
        : v < 0.8
        ? { label: 'Conservative & Investable', color: 'green', text: 'Manageable debt load. Confirm interest coverage ratio >4× before committing capital.' }
        : { label: 'Stress Test Before Investing', color: 'red', text: 'Run a 20% revenue decline scenario to check if the company can service its debt. High risk in recession cycles.' },
  },

  margin: {
    definition:
      'Net Profit Margin tells you what percentage of revenue actually reaches shareholders after all costs, tax, interest, and depreciation. ' +
      'A 17% margin means ₹17 flows free for every ₹100 in sales. It\'s the intersection of pricing power, cost efficiency, and competitive advantage.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '18–24%', top: '26%+', label: 'Private Banks (NIM-driven)' }
      : s === 'newage'? { avg: '0–5%',   top: '8–12%', label: 'New-Age Platforms' }
      : s === 'it'    ? { avg: '15–20%', top: '22%+', label: 'IT Services' }
      : s === 'auto'  ? { avg: '4–8%',   top: '10%+', label: 'Auto Manufacturing' }
      :                 { avg: '10–16%', top: '20%+', label: 'Indian Large Cap' },

    trend: (v, s) =>
      s === 'newage' && v < 5
        ? { direction: 'improving', insight: 'Early-stage margin inflection. The critical question: is it improving quarter-on-quarter? Trajectory matters more than absolute level.' }
        : v >= 20
        ? { direction: 'stable', insight: 'Exceptional margin profile — pricing power is clearly intact. Durable competitive advantage is likely present.' }
        : v >= 12
        ? { direction: 'stable', insight: 'Solid profitability in the quality zone. Monitor for input cost pressure or pricing erosion from competition.' }
        : { direction: 'declining', insight: 'Sub-threshold margin suggests cost structure vulnerability or weak pricing power. Needs structural investigation.' },

    rangeLogic: (s) =>
      s === 'newage'
        ? 'New-age businesses are in scale investment phase — margins are intentionally negative initially. The key metric is contribution margin and unit economics, not net margin.'
        : s === 'auto'
        ? 'Auto manufacturing carries heavy fixed costs (R&D amortization, steel costs). A 6–10% net margin is healthy for the sector; above 12% signals premiumization or EV leadership advantage.'
        : '>12% net margin is the threshold where a business has demonstrably crossed the pricing power barrier. Below 8% leaves little buffer for economic shocks, rate hikes, or competitive pressure.',

    risks: [
      'Commodity input cost spike (steel, crude, chemicals) compresses margins faster than pricing can adjust.',
      'Competitor pricing pressure in hypercompetitive sectors (telecom, retail) erodes margins structurally.',
      'Employee cost inflation in skilled-labour sectors (IT, pharma) with fixed-price contracts creates margin drag.',
      'Currency depreciation inflates import costs — particularly for auto, pharma API, and electronics companies.',
    ],

    drivers: [
      { label: 'Pricing Power', desc: 'Premium brands (Titan, Page Industries) pass costs to consumers. Commodity businesses cannot — structurally capped margins.' },
      { label: 'Operating Leverage', desc: 'Fixed costs spread over higher revenue improves margins in upcycles. The reverse destroys them in downturns.' },
      { label: 'Product Mix', desc: 'Higher-margin product share (ex: specialty pharma vs generics) directly lifts blended margin.' },
      { label: 'Operational Efficiency', desc: 'Lean supply chains, automation, and procurement advantages create durable margin superiority.' },
    ],

    impact:
      'Margin is the most direct driver of earnings quality. A company growing revenue at 18% but with margins declining 200bps annually will have stagnant EPS. ' +
      'Margin expansion stories (Zomato, Paytm, Jio) are among the most powerful re-rating catalysts — stocks can 2–3× as profitability inflects from negative to positive.',

    action: (v, s) =>
      s === 'newage' && v < 5
        ? { label: 'Track Margin Trajectory, Not Absolute', color: 'gold', text: 'Check if margin improved by ≥100 bps QoQ for 3 consecutive quarters — that\'s the real buy signal.' }
        : v >= 20
        ? { label: 'Premium Quality — Hold Core Position', color: 'green', text: 'Strong pricing power confirmed. This is the kind of business that outperforms in downturns too.' }
        : v >= 12
        ? { label: 'Healthy — Monitor Cost Structure', color: 'green', text: 'Good margin. Monitor if raw material costs or wage inflation are narrowing the gap.' }
        : { label: 'Caution — Diagnose Root Cause', color: 'red', text: 'Below ideal. Is it temporary (commodity cycle) or structural (losing market share)? The answer determines action.' },
  },

  promoter: {
    definition:
      'Promoter Holding % measures the founding family, parent company, or institutional promoter\'s ownership stake. ' +
      'It reflects conviction — promoters who don\'t sell are implicitly signalling belief in future value. ' +
      'However, very high promoter holding with pledged shares is a serious red flag, not a bullish indicator.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '0% (RBI mandated)', top: 'N/A', label: 'Banking (regulated)' }
      : s === 'newage'? { avg: '10–25%', top: '>30%', label: 'VC/PE backed platforms' }
      : s === 'it'    ? { avg: '12–25%', top: 'N/A', label: 'IT Services (institutional)' }
      :                 { avg: '40–60%', top: '50–70% (unpledged)', label: 'Indian Promoter-led' },

    trend: (v, s) =>
      s === 'bank'
        ? { direction: 'stable', insight: 'RBI mandates that no entity holds >26% in a bank. Zero promoter holding is standard — evaluate FII/DII ownership instead.' }
        : s === 'newage'
        ? { direction: 'stable', insight: 'VC-held platforms show low promoter holding by design. Monitor bulk deal disclosures and lock-in expiry schedules.' }
        : v >= 50
        ? { direction: 'stable', insight: 'High promoter conviction. The family/group has skin in the game. Check pledge % — zero pledge + high holding = ideal.' }
        : v >= 35
        ? { direction: 'improving', insight: 'Moderate holding above quality floor. Ensure no creeping dilution through ESOPs or preferential allotments.' }
        : { direction: 'declining', insight: 'Low promoter holding without a structural reason (MNC, bank, startup) warrants investigation into governance signals.' },

    rangeLogic: (s) =>
      s === 'bank'
        ? 'RBI prudential norms cap bank promoter holdings at 26% long-term. Zero promoter holding is not a risk — assess FII ownership (>25% is strong).'
        : s === 'newage'
        ? 'VC-backed companies have VCs as "promoters" with planned exits. The risk is concentrated selling post lock-in expiry.'
        : '40–75% holding with zero pledge is the ideal governance range. Above 75% risks SEBI mandatory open offer; below 30% without institutional backing raises control questions.',

    risks: [
      'Pledged promoter shares are catastrophic — if stock falls, lenders force-sell, triggering a cascade (Yes Bank, DHFL pattern).',
      'Creeping dilution via QIP and ESOP issuances steadily erodes EPS even when reported profits grow.',
      'Related-party transactions in promoter-heavy companies can extract value from minority shareholders.',
      'Sudden promoter share sale (block deal without advance notice) is always a bearish signal — insider information asymmetry.',
    ],

    drivers: [
      { label: 'Founder Vision', desc: 'Founders staying invested signals long-term conviction. Founder exits after 5–7 years post-IPO are routine, not alarming.' },
      { label: 'Institutional Confidence', desc: 'High FII/DII holding compensates for low promoter holding. TCS, Infosys are institutional confidence models.' },
      { label: 'Corporate Governance', desc: 'Independent board members, audit committee quality, and RPT disclosures are more important than raw holding %.' },
      { label: 'Dividend History', desc: 'Consistent dividends to promoters signals the business is genuinely profitable — not accounting-driven.' },
    ],

    impact:
      'Promoter holding acts as a behavioral signal more than a financial metric. Markets re-rate stocks sharply when promoters increase buying (positive re-rating) or sell unexpectedly (de-rating). ' +
      'SEBI now mandates real-time disclosure of promoter transactions above 1% — monitor BSE announcements as a leading indicator.',

    action: (v, s) =>
      s === 'bank'
        ? { label: 'Not Applicable — Use FII Ownership Data', color: 'gold', text: 'Check FII ownership and institutional investor quality instead. RBI limits make raw holding meaningless.' }
        : s === 'newage'
        ? { label: 'Monitor Bulk Deal Alerts', color: 'gold', text: 'Set NSE block deal alerts for VC exits. Any >2% sale in one session is a signal to reassess.' }
        : v >= 45
        ? { label: 'Governance Aligned — Examine Pledge', color: 'green', text: 'Strong holding is positive. Verify ZERO pledge in CDSL/NSDL disclosures to confirm quality.' }
        : v >= 30
        ? { label: 'Acceptable — Verify Institutional Backup', color: 'gold', text: 'Moderate stake. Look for FII/mutual fund ownership >20% to offset lower promoter conviction.' }
        : { label: 'Governance Red Flag — Deep Dive Required', color: 'red', text: 'Below 30% without institutional backing. Audit RPT disclosures and check for recent block deals.' },
  },

  cagr: {
    definition:
      'Revenue CAGR (Compound Annual Growth Rate) over 3 years shows the compounded pace at which the company has been growing its top line. ' +
      'Unlike year-on-year growth, CAGR smooths out cyclical distortions and gives a clean compound growth picture. ' +
      'It\'s the velocity indicator — businesses with high ROE AND high CAGR are the true compounders.',

    sectorAvg: (s) =>
      s === 'bank'    ? { avg: '12–18%', top: '20%+', label: 'Private Banks' }
      : s === 'newage'? { avg: '40–80%', top: '80–120%', label: 'New-Age Platforms' }
      : s === 'it'    ? { avg: '10–16%', top: '20%+', label: 'IT Services' }
      : s === 'auto'  ? { avg: '8–14%', top: '18%+', label: 'Auto Manufacturing' }
      :                 { avg: '10–16%', top: '20%+', label: 'Indian Large Cap' },

    trend: (v) =>
      v >= 30
        ? { direction: 'improving', insight: 'Exceptional top-line velocity — well above GDP and sector average. Likely gaining market share or entering new geographies.' }
        : v >= 15
        ? { direction: 'stable', insight: 'Strong, sustainable growth compounding above inflation and sector average. Quality business in expansion mode.' }
        : v >= 8
        ? { direction: 'stable', insight: 'In line with sector average. Not a growth story — evaluate for value characteristics (high dividend, low PE) instead.' }
        : { direction: 'declining', insight: 'Below inflation growth in revenue terms. Diagnose: market share loss, industry headwind, or one-time base effect.' },

    rangeLogic: (s) =>
      s === 'newage'
        ? 'New-age companies are valued on GMV/revenue multiples at hypergrowth phase. >40% CAGR is the expectation. Deceleration below 30% triggers severe de-rating.'
        : '>12% revenue CAGR ensures the business grows faster than India\'s nominal GDP (~14%), indicating real market share gains. Below 8% means shrinking in real economic terms.',

    risks: [
      'Revenue CAGR built on a single large customer or government contract — concentration risk.',
      'Growth via acquisitions (inorganic) inflates CAGR but may not reflect organic competitive strength.',
      'High CAGR in cyclical sectors (steel, realty, infra) often reverses sharply — mean reversion risk.',
      'If CAGR is outpacing margin expansion, the growth may not be profitable — check operating leverage.',
    ],

    drivers: [
      { label: 'Market Share Gains', desc: 'Capturing competitor revenue is the highest quality growth driver — durable and compounding.' },
      { label: 'Geographic Expansion', desc: 'Entering new markets (international, tier-2/3 India) creates a multi-year CAGR tailwind.' },
      { label: 'Product Innovation', desc: 'New product lines with superior unit economics raise both revenue and margin trajectory.' },
      { label: 'Industry Tailwinds', desc: 'Riding structural sector growth (EV, defence, digital infra) adds a sector-level CAGR boost.' },
    ],

    impact:
      'Revenue CAGR is the primary growth-quality signal for long-term investors. Consistently high-CAGR companies are re-rated by institutional investors, resulting in PE expansion (multiple re-rating on top of EPS growth). ' +
      'This dual driver — earnings growth + PE expansion — is what creates 5–10× wealth creation stocks in Indian markets.',

    action: (v, s) =>
      s === 'newage' && v >= 40
        ? { label: 'Hypergrowth Phase — Monitor Unit Economics', color: 'green', text: 'CAGR is strong. Pivot focus to contribution margin and path to EBITDA breakeven.' }
        : v >= 25
        ? { label: 'Strong Compounder — Long-Term Hold', color: 'green', text: 'Exceptional growth at scale. This is the engine of future wealth creation. Hold and add on corrections.' }
        : v >= 15
        ? { label: 'Solid Growth — Accumulate on Dips', color: 'green', text: 'Above sector average. Strong candidate for SIP-style accumulation over 3–5 year horizon.' }
        : { label: 'Watch Before Adding', color: 'gold', text: 'Below ideal growth threshold. Understand if it\'s a temporary headwind or structural deceleration before increasing allocation.' },
  },
};
