"""
Routes. Each handler is thin: fetch from MarketData / news / charts, call a pure
function in analytics, geo or rhp, return a schema.

State lives on app.state so tests can inject fixtures:
    create_app(market=MarketData(rows=[...]), headlines=lambda: [...])
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .. import analytics, geo, rhp
from ..config import get_settings
from ..market import MarketData, Stock, TTLCache
from ..scoring import score_stock
from ..sectors import SECTOR_LABELS
from ..sources import chart, news
from . import schemas

NEWS_TTL_SECONDS = 15 * 60
CHART_TTL_SECONDS = {"1d": 120, "5d": 600}  # intraday refreshes often; daily ranges hourly
MAX_UPLOAD_BYTES = 60 * 1024 * 1024  # DRHPs run 10–40 MB

Range = Literal["1d", "5d", "1mo", "6mo", "1y", "5y"]
SortField = Literal["score", "market_cap", "change_pct", "pe", "roe", "de", "name"]
CapBand = Literal["large", "mid", "small"]


def _stock_out(s: Stock) -> schemas.StockOut:
    return schemas.StockOut(**s.to_dict(), sector_label=SECTOR_LABELS.get(s.sector, "Other"))


def _verdict(score: int | None) -> str | None:
    if score is None:
        return None
    return "Strong" if score >= 65 else "Fair" if score >= 45 else "Weak"


def create_app(
    market: MarketData | None = None,
    headlines: Callable[[], list[news.Headline]] | None = None,
    history: Callable[[str, str], list[tuple[int, float]]] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="StockSense API",
        version="1.0.0",
        description=(
            "Read-only market data for NSE stocks, StockSense scores, news-driven sector "
            "exposure and a prospectus risk scanner. For learning, not investment advice."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(get_settings().api_cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.market = market or MarketData()
    app.state.headlines = headlines or news.fetch_headlines
    app.state.history = history or chart.history
    app.state.cache = TTLCache()

    def market_of(request: Request) -> MarketData:
        return request.app.state.market

    # ── health ──────────────────────────────────────────────────────────────

    @app.get("/health", response_model=schemas.Health, tags=["meta"])
    def health(request: Request):
        m = market_of(request)
        stocks = m.stocks()
        quotes = m.quotes()
        updated = max((q.updated_at for q in quotes.values() if q.updated_at), default=None)
        return schemas.Health(
            status="ok",
            data_source=m.source,
            stocks=len(stocks),
            scored=sum(1 for s in stocks if s.score is not None),
            prices_updated_at=updated,
        )

    # ── market ──────────────────────────────────────────────────────────────

    @app.get("/market/indices", response_model=list[schemas.IndexQuote], tags=["market"])
    def indices(request: Request):
        return market_of(request).indices()

    @app.get("/market/overview", response_model=schemas.Overview, tags=["market"])
    def overview(request: Request, movers: int = Query(5, ge=1, le=20), top: int = Query(8, ge=1, le=30)):
        m = market_of(request)
        stocks = m.stocks()
        moves = analytics.movers(stocks, movers)
        return schemas.Overview(
            indices=m.indices(),
            breadth=analytics.breadth(stocks),
            sectors=analytics.sector_moves(stocks),
            movers=schemas.Movers(
                gainers=[_stock_out(s) for s in moves["gainers"]],
                losers=[_stock_out(s) for s in moves["losers"]],
            ),
            top_scored=[_stock_out(s) for s in analytics.top_scored(stocks, top)],
        )

    @app.get("/sectors", tags=["market"])
    def sectors(request: Request):
        """Sector codes with labels and how many stocks each has — for filter dropdowns."""
        counts: dict[str, int] = {}
        for s in market_of(request).stocks():
            counts[s.sector] = counts.get(s.sector, 0) + 1
        return [
            {"code": code, "label": label, "stocks": counts.get(code, 0)}
            for code, label in sorted(SECTOR_LABELS.items(), key=lambda kv: kv[1])
            if code != "general"
        ]

    # ── stocks ──────────────────────────────────────────────────────────────

    @app.get("/stocks", response_model=schemas.ScreenPage, tags=["stocks"])
    def screen(
        request: Request,
        sector: str | None = Query(None, description="Sector code from /sectors"),
        cap: CapBand | None = None,
        min_score: float | None = Query(None, ge=0, le=100),
        max_pe: float | None = Query(None, gt=0),
        min_roe: float | None = None,
        max_de: float | None = Query(None, ge=0),
        sort: SortField = "score",
        order: Literal["asc", "desc"] | None = Query(None, description="Defaults to the natural order for `sort`"),
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
    ):
        """The screener: every NSE stock passing the filters, sorted and paginated."""
        filters = analytics.ScreenFilters(
            sector=sector, cap=cap, min_score=min_score, max_pe=max_pe, min_roe=min_roe, max_de=max_de,
            sort=sort, descending=None if order is None else order == "desc",
        )
        rows = analytics.screen(market_of(request).stocks(), filters)
        start = (page - 1) * page_size
        return schemas.ScreenPage(
            total=len(rows), page=page, page_size=page_size,
            results=[_stock_out(s) for s in rows[start : start + page_size]],
        )

    @app.get("/stocks/search", response_model=list[schemas.StockOut], tags=["stocks"])
    def search(request: Request, q: str = Query(..., min_length=1, max_length=40), limit: int = Query(8, ge=1, le=25)):
        return [_stock_out(s) for s in analytics.search(market_of(request).stocks(), q, limit)]

    @app.get("/stocks/{symbol}", response_model=schemas.StockDetail, tags=["stocks"])
    def stock_detail(request: Request, symbol: str, peers: int = Query(6, ge=0, le=15)):
        """One stock with its score explained metric by metric, and its largest sector peers."""
        m = market_of(request)
        stock = m.stock(symbol)
        if stock is None:
            raise HTTPException(404, f"No NSE stock with symbol {symbol.upper()}.")
        metrics = {"pe": stock.pe, "roe": stock.roe, "de": stock.de, "margin": stock.margin, "promoter": stock.promoter, "cagr": stock.cagr}
        coverage = score_stock(metrics, stock.sector).coverage
        return schemas.StockDetail(
            stock=_stock_out(stock),
            score=schemas.ScoreDetail(
                value=stock.score, verdict=_verdict(stock.score), coverage=coverage,
                breakdown=analytics.score_breakdown(stock),
            ),
            peers=[_stock_out(s) for s in analytics.peers(m.stocks(), stock, peers)] if peers else [],
        )

    @app.get("/stocks/{symbol}/history", response_model=schemas.History, tags=["stocks"])
    def stock_history(request: Request, symbol: str, range: Range = "1y"):  # noqa: A002 — public query name
        """Closing prices. Also works for indices: NIFTY50, SENSEX, BANKNIFTY, INDIAVIX."""
        sym = symbol.upper()
        ttl = CHART_TTL_SECONDS.get(range, 3600)
        points = request.app.state.cache.get(f"chart:{sym}:{range}", ttl, lambda: request.app.state.history(sym, range))
        return schemas.History(symbol=sym, range=range, points=[{"t": t, "close": c} for t, c in points])

    # ── news & geopolitics ──────────────────────────────────────────────────

    def _events(request: Request) -> list[geo.Event]:
        def load():
            return geo.relevant_events(request.app.state.headlines())

        return request.app.state.cache.get("news", NEWS_TTL_SECONDS, load)

    @app.get("/news", response_model=list[schemas.NewsEvent], tags=["geopolitics"])
    def news_feed(
        request: Request,
        topic: str | None = Query(None, description="e.g. Conflict, Oil, Trade, Interest rates"),
        sector: str | None = Query(None, description="e.g. Oil & Gas, IT Services"),
        limit: int = Query(30, ge=1, le=100),
    ):
        """Market-moving headlines, tagged with topics and the sectors they affect."""
        events = _events(request)
        if topic:
            events = [e for e in events if any(t.lower() == topic.lower() for t in e.topics)]
        if sector:
            events = [e for e in events if any(s.lower() == sector.lower() for s in e.sectors)]
        return [e.to_dict() for e in events[:limit]]

    @app.get("/geopolitics", response_model=schemas.Geopolitics, tags=["geopolitics"])
    def geopolitics(request: Request, events: int = Query(12, ge=0, le=50)):
        """Sector exposure computed from recent news, plus the headlines behind it."""
        all_events = _events(request)
        return schemas.Geopolitics(
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            exposure=geo.exposure(all_events),
            events=[e.to_dict() for e in all_events[:events]],
        )

    # ── prospectus scanner ──────────────────────────────────────────────────

    @app.get("/prospectus/rules", tags=["prospectus"])
    def prospectus_rules():
        """What the scanner looks for."""
        return [{"id": r.id, "title": r.title, "why": r.why} for r in rhp.RULES]

    @app.post("/prospectus/scan", response_model=schemas.ScanResult, tags=["prospectus"])
    def prospectus_scan(file: UploadFile = File(..., description="DRHP or RHP as a text PDF")):
        """Upload a prospectus PDF; get its red flags with page-numbered quotes. The file is not stored."""
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "That file is over 60 MB. Upload the DRHP or RHP PDF only.")
        try:
            return rhp.scan_pdf(data).to_dict()
        except rhp.ScanError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
