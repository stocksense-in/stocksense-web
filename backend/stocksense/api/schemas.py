"""Response shapes. They document the API at /docs and keep field names stable for clients."""

from __future__ import annotations

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


class ScorePart(BaseModel):
    metric: str
    column: str
    value: float
    score: float = Field(description="0–100 for this metric")
    weight: float = Field(description="Share of the final score after re-normalising for missing metrics")
    points: float = Field(description="score × weight; parts sum to the composite")


class ScoreDetail(BaseModel):
    value: int | None
    verdict: str | None = Field(description="Strong (65+), Fair (45–64) or Weak")
    coverage: int = Field(description="How many of the six metrics were available")
    breakdown: list[ScorePart]


class StockDetail(BaseModel):
    stock: StockOut
    score: ScoreDetail
    peers: list[StockOut]


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


class Listing(BaseModel):
    symbol: str
    name: str
    board: str
    listed: str
    issue_price: float | None
    price: float | None = Field(description="Latest price, when StockSense tracks the stock")
    return_pct: float | None = Field(description="Return from issue price to latest price, %")
