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
    scored: int
    prices_updated_at: str | None
