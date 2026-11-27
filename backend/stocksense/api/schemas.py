"""Response shapes. They document the API at /docs and keep field names stable for clients."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StockOut(BaseModel):
    symbol: str
    name: str
    sector: str = Field(description="StockSense sector code, e.g. it, bank, fmcg")
    sector_label: str
    industry: str | None
    market_cap: float | None = Field(description="₹ crore")
    price: float | None
    change_pct: float | None = Field(description="Day change, %")
    week52_high: float | None
    week52_low: float | None
    pe: float | None
    pb: float | None
    roe: float | None = Field(description="%")
    de: float | None = Field(description="Debt to equity, ratio")
    margin: float | None = Field(description="Net profit margin, %")
    dividend_yield: float | None
    promoter: float | None = Field(description="Promoter holding, %")
    cagr: float | None = Field(description="3-year revenue CAGR, %")
    score: int | None = Field(description="StockSense score 0–100; null when too little data")
    updated_at: str | None
    stale: bool = Field(description="Data is over a week older than the latest refresh — usually delisted or renamed")


class IndexQuote(BaseModel):
    symbol: str
    label: str
    price: float
    change_pct: float | None
    updated_at: str | None


class Breadth(BaseModel):
    advancers: int
    decliners: int
    unchanged: int


class SectorMove(BaseModel):
    sector: str
    label: str
    change_pct: float
    advancers: int
    decliners: int


class Movers(BaseModel):
    gainers: list[StockOut]
    losers: list[StockOut]


class Overview(BaseModel):
    indices: list[IndexQuote]
    breadth: Breadth
    sectors: list[SectorMove]
    movers: Movers
    top_scored: list[StockOut]


class ScreenPage(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[StockOut]


class PeerContext(BaseModel):
    """Where the company's value sits among its sector peers (layer 1)."""
    group: str = Field(description="e.g. 'IT Services companies', or 'all NSE companies' for small sectors")
    peers: int
    p25: float
    median: float
    p75: float
    typical_range: str = Field(description="The middle half of peers, e.g. '14–28%'")
    better_than_pct: float | None = Field(description="Share of peers this company beats (direction-aware); None when not ranked, e.g. a loss-making P/E")
    standing: str | None = Field(description="top quarter | above median | below median | bottom quarter")
    text: str


class ScorePart(BaseModel):
    metric: str
    column: str
    value: float
    score: float = Field(description="0–100 for this metric: 70% peer_score + 30% absolute_score")
    peer_score: float | None = Field(None, description="Share of sector peers this company beats on the metric (0–100)")
    absolute_score: float = Field(description="The fixed scoring curve's 0–100 for this value")
    weight: float = Field(description="Share of the final score after re-normalising for missing metrics")
    points: float = Field(description="score × weight; parts sum to the composite")
    label: str = Field(description="Plain name, e.g. 'Return on equity'")
    measures: str = Field(description="What the metric tells a beginner")
    verdict: str = Field(description="How the blended sub-score reads: strong (70+) | fair (40+) | weak | unclear | not judged")
    healthy_range: str | None = Field(description="The fixed curve's strong / fair / weak bands for this sector (the 30% absolute part)")
    note: str | None = Field(None, description="Caveat for this kind of company (lenders, one-off profits, …)")
    peers: PeerContext | None = Field(None, description="Layer 1: standing among sector peers")
    stage_note: str | None = Field(None, description="Layer 2: what the company's stage means for this metric")
    market_note: str | None = Field(None, description="Layer 3 (P/E only): the sector's valuation today vs its own history")
    history_note: str | None = Field(None, description="The company against its own history (promoter stake over a year)")
    guardrail: str | None = Field(None, description="An absolute warning that holds whatever peers do")


class ScoreDetail(BaseModel):
    value: int | None
    verdict: str | None = Field(description="Strong (65+), Fair (45–64) or Weak")
    coverage: int = Field(description="How many of the six metrics were available")
    missing: list[str] = Field(default_factory=list, description="Metrics with no data, by label")
    coverage_note: str | None = Field(None, description="What the missing metrics mean for this score")
    not_applicable: list[str] = Field(default_factory=list, description="Metrics that don't apply to this company (e.g. promoter holding with no promoter group)")
    stage: str | None = Field(None, description="loss-making | high growth | steady | unknown — how to read the metrics")
    stage_text: str | None = None
    breakdown: list[ScorePart]


class MetricGuide(BaseModel):
    metric: str
    label: str
    measures: str
    higher_is_better: bool
    weight: float = Field(description="Weight in the StockSense score")
    healthy_range: str | None = Field(description="The score's strong / fair / weak bands for this sector")
    peers: PeerContext | None = Field(description="What's typical among this sector's companies (no company value, so not ranked)")
    watch_for: str | None = Field(None, description="The common trap when reading this metric")


class FinancialQuarter(BaseModel):
    period_end: str
    revenue: float | None = Field(description="₹ crore; for lenders net interest income + other income")
    net_profit: float | None = Field(description="₹ crore, owners' share")
    eps: float | None
    margin_pct: float | None


class FinancialYear(BaseModel):
    fiscal_year: int = Field(description="Year ending 31 March")
    revenue: float | None
    net_profit: float | None
    margin_pct: float | None


class FilingMetrics(BaseModel):
    as_of: str = Field(description="Quarter end of the latest four quarters used")
    net_margin: float | None
    revenue_cagr_3yr: float | None
    roe: float | None
    debt_equity: float | None


class MarginHistory(BaseModel):
    now: float | None
    low: float | None
    median: float | None
    high: float | None
    since: str
    percentile: int = Field(description="Share of the last five years' trailing margins below today's")
    includes_excise: bool = Field(False, description="Measured on revenue including excise duty (older years can't be netted)")


class ResultReaction(BaseModel):
    period_end: str
    filed: str = Field(description="When the result reached the exchange (IST)")
    revenue_yoy_pct: float | None
    profit_yoy_pct: float | None
    move_1d_pct: float | None
    excess_1d_pct: float | None = Field(description="The share's move minus NIFTY 50's, next trading day")
    move_5d_pct: float | None
    excess_5d_pct: float | None


class Financials(BaseModel):
    symbol: str
    source: str
    unit: str
    basis: str = Field(description="consolidated or standalone — never a mix")
    kind: str
    revenue_means: str
    quarters: list[FinancialQuarter]
    years: list[FinancialYear]
    margin_history: MarginHistory | None = None
    reactions: list[ResultReaction] = []
    reaction_note: str | None = None
    metrics: FilingMetrics


class HolderQuarter(BaseModel):
    quarter_end: str
    promoter_pct: float | None
    public_pct: float | None
    employee_trusts_pct: float | None
    fii_pct: float | None = Field(None, description="Foreign institutions (FPIs); latest quarters only")
    dii_pct: float | None = Field(None, description="Domestic institutions: mutual funds, insurers, banks, pension funds")
    mutual_funds_pct: float | None = None
    insurance_pct: float | None = None
    small_retail_pct: float | None = Field(None, description="Individuals holding up to ₹2 lakh of share capital")
    government_pct: float | None = None


class Pledge(BaseModel):
    as_of: str
    pledged_pct_of_promoter: float | None = Field(description="Share of the promoters' own stake pledged")
    pledged_pct_of_total: float | None
    all_pledges_pct_of_total: float | None = Field(description="Every depository pledge by any holder — context only")


class Holders(BaseModel):
    symbol: str
    source: str
    quarters: list[HolderQuarter]
    pledge: Pledge | None
    trend_note: str | None
    pledge_warning: str | None


class LearnMetrics(BaseModel):
    sector: str
    sector_label: str
    market_note: str | None = Field(description="How the sector (or market) is valued today vs its own history")
    stages: dict[str, str] = Field(description="How a company's stage changes the reading")
    metrics: list[MetricGuide]


class Available(BaseModel):
    financials: bool = Field(description="GET /stocks/{symbol}/financials has filed results for this company")
    holders: bool = Field(description="GET /stocks/{symbol}/holders has shareholding filings for this company")
    dividends: bool = Field(False, description="GET /stocks/{symbol}/dividends has corporate actions for this company")
    events: bool = Field(False, description="GET /stocks/{symbol}/events has announcements or insider trades")


class DividendYear(BaseModel):
    fiscal_year: int = Field(description="Year ending 31 March, by ex-date")
    per_share: float


class LastDividend(BaseModel):
    ex_date: str
    per_share: float


class CapitalAction(BaseModel):
    ex_date: str
    kind: str = Field(description="split, bonus, rights, restructuring (demerger/merger), consolidation")
    subject: str


class Dividends(BaseModel):
    symbol: str
    source: str
    years: list[DividendYear]
    ttm_per_share: float
    paid_years_in_a_row: int
    streak_since_data_start: bool = Field(False, description="The streak reaches back to where the data starts")
    data_from_fiscal_year: int | None = None
    last_dividend: LastDividend | None
    capital_actions: list[CapitalAction]
    note: str | None = Field(None, description="The dividend habit and yield at today's price, in one line")


class StockDetail(BaseModel):
    stock: StockOut
    score: ScoreDetail
    peers: list[StockOut]
    available: Available = Field(description="Which company-page panels have data, so the UI can skip the rest")


class PricePoint(BaseModel):
    t: int = Field(description="Unix seconds")
    close: float


class History(BaseModel):
    symbol: str
    range: str
    points: list[PricePoint]


class SectorEffect(BaseModel):
    sector: str
    code: str | None = Field(description="Screener sector code, when one exists")
    effect: str = Field(description="risk | opportunity | haven | watch")
    label: str


class Alert(BaseModel):
    date: str
    symbol: str
    kind: str = Field(description="price_move | unusual_volume | results_filed | large_order | promoter_stake | pledge_change")
    value: float | None
    text: str = Field(description="What happened, written for a beginner")


class Alerts(BaseModel):
    generated_at: str | None
    days: list[str] = Field(description="Trading sessions covered, newest first")
    alerts: list[Alert]


class CompanyHeadline(BaseModel):
    title: str
    link: str
    source: str = Field(description="Publisher")
    published: str | None


class NewsEvent(BaseModel):
    title: str
    link: str
    source: str
    published: str | None
    topics: list[str]
    sectors: list[SectorEffect]


class Exposure(BaseModel):
    sector: str
    code: str | None
    sensitivity: int = Field(description="Share of recent macro news about this sector, 0–100")
    effect: str
    label: str
    headlines: int


class Geopolitics(BaseModel):
    updated_at: str
    exposure: list[Exposure]
    events: list[NewsEvent]


class AnalogueCell(BaseModel):
    """How a sector did after past events of one type, versus NIFTY 50."""
    sector: str
    horizon_days: int
    n: int = Field(description="Past occurrences with data for this sector")
    mean_excess_pct: float = Field(description="Average return minus NIFTY 50's, in percent")
    median_excess_pct: float
    hit_rate: float = Field(description="Share of occurrences where the sector beat NIFTY 50")
    ci_low_pct: float = Field(description="95% confidence interval of the mean, low end")
    ci_high_pct: float
    baseline_pct: float = Field(description="The sector's average excess return over all days")
    notable: bool = Field(description="The confidence interval excludes the baseline")


class AnalogueEvidence(BaseModel):
    actors: str
    place: str | None
    articles: int
    url: str


class AnalogueOccurrence(BaseModel):
    date: str
    evidence: list[AnalogueEvidence]


class AnalogueSummary(BaseModel):
    code: str
    label: str
    rule: str
    occurrences: int
    first: str | None
    last: str | None


class AnalogueDetail(AnalogueSummary):
    recent: list[AnalogueOccurrence]
    sectors: list[AnalogueCell]


class Analogues(BaseModel):
    generated_at: str
    data_from: str
    data_through: str
    benchmark: str
    horizons_days: list[int]
    method: str
    notable_share: dict[str, float] = Field(
        default_factory=dict,
        description="Per horizon (days), share of sector cells flagged notable; ~0.05 is what chance alone gives",
    )
    sector_sources: dict[str, str]
    events: list[AnalogueSummary]


class Evidence(BaseModel):
    page: int
    quote: str


class Finding(BaseModel):
    id: str
    title: str
    severity: str = Field(description="high | medium | low")
    summary: str
    why: str
    evidence: list[Evidence]
    track_record: str | None = Field(None, description="How past IPOs with this flag did in the six months after listing")


class ScanResult(BaseModel):
    pages: int
    findings: list[Finding]
    clear: list[dict]


class Health(BaseModel):
    status: str
    data_source: str = Field(description="supabase | snapshot | fixture")
    stocks: int
    stale: int
    scored: int
    prices_updated_at: str | None


class Subscription(BaseModel):
    """Times subscribed per category: 2.5 means bids for 2.5× the shares on offer."""

    qib: float | None = Field(description="Qualified institutional buyers")
    nii: float | None = Field(description="Non-institutional (HNI) investors")
    retail: float | None
    employees: float | None
    total: float | None
    updated_at: str | None


class Demand(BaseModel):
    level: str = Field(description="strong | moderate | weak | early — demand so far, not a recommendation")
    summary: str


class Ipo(BaseModel):
    symbol: str
    name: str
    board: str = Field(description="mainboard | sme")
    status: str = Field(description="open | upcoming | closed")
    opens: str | None
    closes: str | None
    price_low: float | None
    price_high: float | None
    shares_offered: float | None
    size_crore: float | None = Field(description="Issue size at the top of the price band, ₹ crore")
    subscription: Subscription
    demand: Demand


class IpoBoard(BaseModel):
    updated_at: str
    open: list[Ipo]
    upcoming: list[Ipo]


class ProspectusFlag(BaseModel):
    id: str
    title: str
    severity: str = Field(description="high | medium")
    summary: str


class ListingProspectus(BaseModel):
    url: str = Field(description="The red herring prospectus on SEBI's site")
    flags: list[ProspectusFlag] = Field(description="Medium and high findings of the prospectus checker")


class Listing(BaseModel):
    symbol: str
    name: str
    board: str
    listed: str
    issue_price: float | None
    price: float | None = Field(description="Latest price, when StockSense tracks the stock")
    return_pct: float | None = Field(description="Return from issue price to latest price, %")
    prospectus: ListingProspectus | None = Field(None, description="Its prospectus, scanned (mainboard IPOs)")


class Announcement(BaseModel):
    at: str = Field(description="When NSE published it (IST)")
    group: str = Field(description="warning | exchange | legal | results | orders | deals | capital | rating | management | business")
    category: str = Field(description="NSE's category")
    title: str
    link: str | None = Field(description="The filing (PDF) on NSE's archive")


class InsiderTrade(BaseModel):
    date: str
    person: str
    role: str = Field(description="Promoters | Promoter Group | Director | Key Managerial Personnel")
    side: Literal["buy", "sell"]
    value_cr: float | None
    pct_after: float | None = Field(description="The person's holding afterwards, % of the company")


class Deal(BaseModel):
    date: str
    kind: str = Field(description="bulk (over 0.5% of the company in a day) | block (₹10 crore+ in the block window)")
    client: str = Field(description="Who bought or sold, as NSE reports it")
    side: str = Field(description="buy | sell")
    quantity: int
    price: float
    value_cr: float


class Insiders(BaseModel):
    bought_cr: float | None
    sold_cr: float | None
    buys: int
    sells: int
    trades: list[InsiderTrade]


class Events(BaseModel):
    symbol: str
    source: str
    since: str | None = Field(description="Announcements from this day on")
    insiders_until: str | None = Field(description="Last day of NSE's insider-trading feed in the data")
    counts: dict[str, int] = Field(description="Notable announcements in the past year, by group")
    announcements: list[Announcement]
    insiders: Insiders | None
    insider_note: str | None
    deals: list[Deal] = Field(default_factory=list, description="Latest bulk/block deals, newest first")
    deals_since: str | None = Field(None, description="First day of bulk/block deals in the data (collected daily)")


class EconomySeries(BaseModel):
    series: str = Field(description="repo_rate | cpi_inflation | iip_growth | fx_reserves | gsec_10y")
    label: str
    unit: str
    value: float
    period: str = Field(description="The month (or day, for the repo rate) the value is for")
    year_ago: float | None
    released: str = Field(description="When it became public (estimated from the usual release lag)")
    source: str
    note: str = Field(description="Where it stands now, for a beginner")
    why: str = Field(description="Why it matters for shares")
    history: list[tuple[str, float]] = Field(description="[period, value], oldest first")


class Economy(BaseModel):
    as_of: str | None
    series: list[EconomySeries]
