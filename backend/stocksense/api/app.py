"""
Routes. Each handler is thin: fetch from MarketData / news / charts, call a pure
function in analytics, geo or rhp, return a schema.

State lives on app.state so tests can inject fixtures:
    create_app(market=MarketData(rows=[...]), headlines=lambda: [...])
"""

from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .. import analytics, benchmarks, geo, ipo, rhp
from .. import dividends as dividends_mod
from .. import holders as own
from .. import valuation as valuation_mod
from ..config import DATA_DIR, get_settings
from ..market import MarketData, Stock, TTLCache
from ..scoring import GUIDE, WEIGHTS, healthy_range, score_stock
from ..sectors import SECTOR_LABELS
from ..sources import chart, news, nse_ipo
from . import schemas

NEWS_TTL_SECONDS = 15 * 60
IPO_TTL_SECONDS = 5 * 60  # subscription numbers update through the bidding day
LISTINGS_TTL_SECONDS = 6 * 3600
CHART_TTL_SECONDS = {"1d": 120, "5d": 600}  # intraday refreshes often; daily ranges hourly
MAX_UPLOAD_BYTES = 60 * 1024 * 1024  # DRHPs run 10–40 MB
MAX_CONCURRENT_SCANS = 2  # PDF text extraction is CPU-heavy; don't let a burst starve other requests
ANALOGUES_PATH = DATA_DIR / "geo_analogues.json"  # written by `python -m stocksense event-study`
VALUATION_PATH = DATA_DIR / "valuation_context.json"  # written by `python -m stocksense valuation-context`
FINANCIALS_PATH = DATA_DIR / "financials.json"  # written by `python -m stocksense financials-export`
HOLDERS_PATH = DATA_DIR / "holders.json"  # written by `python -m stocksense holders-export`
DIVIDENDS_PATH = DATA_DIR / "dividends.json"  # written by `python -m stocksense dividends-export`
BENCHMARKS_TTL_SECONDS = 5 * 60  # peer quartiles change only when fundamentals do

Range = Literal["1d", "5d", "1mo", "6mo", "1y", "5y"]
SortField = Literal["score", "market_cap", "change_pct", "pe", "roe", "de", "name"]
CapBand = Literal["large", "mid", "small"]


def _stock_out(s: Stock) -> schemas.StockOut:
    return schemas.StockOut(**s.to_dict(), sector_label=SECTOR_LABELS.get(s.sector, "Other"))


def _coverage_note(score: int | None, missing: list[str]) -> str | None:
    """Plain words for a score built on fewer than six metrics."""
    if not missing:
        return None
    names = ", ".join(m[0].lower() + m[1:] if not m.isupper() and not m[:3].isupper() else m for m in missing)
    if score is None:
        return f"Not enough data to score this company (missing: {names})."
    return (f"This score uses {6 - len(missing)} of 6 metrics — {names} isn't available, so the others carry "
            "its weight. Treat it as a rougher guide." if len(missing) == 1 else
            f"This score uses {6 - len(missing)} of 6 metrics — missing: {names}. The others carry their weight, "
            "so treat it as a rougher guide.")


def _verdict(score: int | None) -> str | None:
    if score is None:
        return None
    return "Strong" if score >= 65 else "Fair" if score >= 45 else "Weak"


_json_cache: dict[Path, tuple[float, dict]] = {}


def _load_json(path: Path) -> dict | None:
    """A published JSON file, re-read only when it changes on disk."""
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return None
    cached = _json_cache.get(path)
    if cached is None or cached[0] != mtime:
        _json_cache[path] = (mtime, json.loads(path.read_text(encoding="utf-8")))
    return _json_cache[path][1]


def load_analogues(path: Path = ANALOGUES_PATH) -> dict | None:
    """The published event study (backend/data/geo_analogues.json)."""
    return _load_json(path)


def load_valuation(path: Path = VALUATION_PATH) -> dict | None:
    """Sector valuations vs their history (backend/data/valuation_context.json)."""
    return _load_json(path)


def load_financials(path: Path = FINANCIALS_PATH) -> dict | None:
    """Company financials from filings (backend/data/financials.json)."""
    return _load_json(path)


def load_holders(path: Path = HOLDERS_PATH) -> dict | None:
    """Promoter holding over time and pledges (backend/data/holders.json)."""
    return _load_json(path)


def load_dividends(path: Path = DIVIDENDS_PATH) -> dict | None:
    """Dividends and capital actions (backend/data/dividends.json)."""
    return _load_json(path)


def _warm(app: FastAPI) -> None:
    try:
        app.state.market.stocks()
    except Exception:  # noqa: BLE001 — warming is best-effort; requests will retry the load
        pass


def create_app(
    market: MarketData | None = None,
    headlines: Callable[[], list[news.Headline]] | None = None,
    history: Callable[[str, str], list[tuple[int, float]]] | None = None,
    nse=nse_ipo,
    analogues: Callable[[], dict | None] | None = None,
    valuation: Callable[[], dict | None] | None = None,
    financials: Callable[[], dict | None] | None = None,
    holders: Callable[[], dict | None] | None = None,
    dividends: Callable[[], dict | None] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load the ~2,600 stocks in the background so the first visitor doesn't wait ~3 s.
        threading.Thread(target=_warm, args=(app,), daemon=True).start()
        yield

    app = FastAPI(
        lifespan=lifespan,
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
    app.state.nse = nse
    app.state.analogues = analogues or load_analogues
    app.state.valuation = valuation or load_valuation
    app.state.financials = financials or load_financials
    app.state.holders = holders or load_holders
    app.state.dividends = dividends or load_dividends
    app.state.scan_slots = threading.BoundedSemaphore(MAX_CONCURRENT_SCANS)

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
            stale=sum(1 for s in stocks if s.stale),
            scored=sum(1 for s in stocks if s.score is not None and not s.stale),
            prices_updated_at=updated,
        )

    # ── market ──────────────────────────────────────────────────────────────

    @app.get("/market/indices", response_model=list[schemas.IndexQuote], tags=["market"])
    def indices(request: Request):
        return market_of(request).indices()

    @app.get("/market/overview", response_model=schemas.Overview, tags=["market"])
    def overview(request: Request, movers: int = Query(5, ge=1, le=20), top: int = Query(8, ge=1, le=30)):
        m = market_of(request)
        stocks = m.fresh_stocks()
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
        for s in market_of(request).fresh_stocks():
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
        rows = analytics.screen(market_of(request).fresh_stocks(), filters)
        start = (page - 1) * page_size
        return schemas.ScreenPage(
            total=len(rows), page=page, page_size=page_size,
            results=[_stock_out(s) for s in rows[start : start + page_size]],
        )

    @app.get("/stocks/search", response_model=list[schemas.StockOut], tags=["stocks"])
    def search(request: Request, q: str = Query(..., min_length=1, max_length=40), limit: int = Query(8, ge=1, le=25)):
        return [_stock_out(s) for s in analytics.search(market_of(request).stocks(), q, limit)]

    def _benchmarks(request: Request) -> benchmarks.Benchmarks:
        return request.app.state.cache.get("benchmarks", BENCHMARKS_TTL_SECONDS,
                                           lambda: benchmarks.build(market_of(request).fresh_stocks()))

    @app.get("/learn/metrics", response_model=schemas.LearnMetrics, tags=["learn"])
    def learn_metrics(request: Request, sector: str = Query("general", description="Sector code from /sectors, e.g. it, bank, fmcg")):
        """
        How to read a company in this sector: each metric's meaning, its weight in the
        score, the score's healthy range, what's typical among the sector's companies,
        how a company's stage changes the reading, and whether the sector itself is
        cheap or expensive today versus its own history. Teaching, not advice.
        """
        code = sector.lower()
        peer = _benchmarks(request)
        return schemas.LearnMetrics(
            sector=code,
            sector_label=SECTOR_LABELS.get(code, "All companies"),
            market_note=valuation_mod.sector_note(code, request.app.state.valuation()),
            stages={k: v for k, v in benchmarks.STAGE_TEXT.items() if v},
            metrics=[
                schemas.MetricGuide(
                    metric=m, label=GUIDE[m]["label"], measures=GUIDE[m]["measures"],
                    higher_is_better=GUIDE[m]["higher_is_better"], weight=WEIGHTS[m],
                    healthy_range=(r := healthy_range(m, code)) and r["text"],
                    peers=_typical(m, code, peer),
                    watch_for=GUIDE[m].get("watch_for"),
                )
                for m in WEIGHTS
            ],
        )

    def _typical(metric: str, sector: str, peer: benchmarks.Benchmarks) -> dict | None:
        """The sector's typical range for a metric, without ranking any company."""
        bench = benchmarks.benchmark_for(peer, sector, metric)
        if bench is None:
            return None
        ctx = benchmarks.peer_context(metric, bench.quantile(0.5), sector, peer)
        return {**ctx, "better_than_pct": None, "standing": None,
                "text": f"Typical for {ctx['group']}: {ctx['typical_range']} (median of {ctx['peers']})."}

    def _financials_of(request: Request, symbol: str) -> dict | None:
        return ((request.app.state.financials() or {}).get("companies") or {}).get(symbol.upper())

    def _dividends_of(request: Request, symbol: str) -> dict | None:
        return ((request.app.state.dividends() or {}).get("companies") or {}).get(symbol.upper())

    @app.get("/stocks/{symbol}/dividends", response_model=schemas.Dividends, tags=["stocks"])
    def stock_dividends(request: Request, symbol: str):
        """Dividend per share by fiscal year, the last 12 months, the paying streak, and recent splits/bonuses."""
        entry = _dividends_of(request, symbol)
        if entry is None:
            raise HTTPException(404, f"No corporate actions for {symbol.upper()}")
        stock = market_of(request).stock(symbol)
        return {"symbol": symbol.upper(), "source": request.app.state.dividends()["source"], **entry,
                "note": dividends_mod.note(entry, stock.price if stock else None)}

    def _holders_of(request: Request, symbol: str) -> dict | None:
        return ((request.app.state.holders() or {}).get("companies") or {}).get(symbol.upper())

    @app.get("/stocks/{symbol}/holders", response_model=schemas.Holders, tags=["stocks"])
    def stock_holders(request: Request, symbol: str):
        """Promoter holding by quarter and the promoters' pledges, from shareholding filings."""
        entry = _holders_of(request, symbol)
        if entry is None:
            raise HTTPException(404, f"No shareholding filings for {symbol.upper()} yet")
        return {"symbol": symbol.upper(), "source": request.app.state.holders()["source"], **entry,
                "trend_note": own.trend_note(entry), "pledge_warning": own.pledge_warning(entry)}

    @app.get("/stocks/{symbol}/financials", response_model=schemas.Financials, tags=["stocks"])
    def stock_financials(request: Request, symbol: str):
        """Quarterly and yearly revenue and profit from the company's own filings, on one basis."""
        doc = request.app.state.financials() or {}
        data = _financials_of(request, symbol)
        if data is None:
            raise HTTPException(404, f"No filed results for {symbol.upper()} yet")
        return {"symbol": symbol.upper(), "source": doc["source"], "unit": doc["unit"], **data}

    @app.get("/stocks/{symbol}", response_model=schemas.StockDetail, tags=["stocks"])
    def stock_detail(request: Request, symbol: str, peers: int = Query(6, ge=0, le=15)):
        """One stock with its score explained metric by metric, and its largest sector peers."""
        m = market_of(request)
        stock = m.stock(symbol)
        if stock is None:
            raise HTTPException(404, f"No NSE stock with symbol {symbol.upper()}.")
        metrics = {"pe": stock.pe, "roe": stock.roe, "de": stock.de, "margin": stock.margin, "promoter": stock.promoter, "cagr": stock.cagr}
        coverage = score_stock(metrics, stock.sector).coverage
        stage = benchmarks.stage(stock)
        financials, holders = _financials_of(request, stock.symbol), _holders_of(request, stock.symbol)
        return schemas.StockDetail(
            stock=_stock_out(stock),
            score=schemas.ScoreDetail(
                value=stock.score, verdict=_verdict(stock.score), coverage=coverage,
                missing=(missing := [GUIDE[k]["label"] for k, v in metrics.items() if v is None]),
                coverage_note=_coverage_note(stock.score, missing),
                stage=stage, stage_text=benchmarks.STAGE_TEXT.get(stage),
                breakdown=analytics.score_breakdown(stock, _benchmarks(request), request.app.state.valuation(),
                                                    holders, financials),
            ),
            peers=[_stock_out(s) for s in analytics.peers(m.fresh_stocks(), stock, peers)] if peers else [],
            available=schemas.Available(financials=financials is not None, holders=holders is not None,
                                        dividends=_dividends_of(request, stock.symbol) is not None),
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

    def _analogues(request: Request) -> dict:
        doc = request.app.state.analogues()
        if not doc:
            raise HTTPException(503, "The historical event study hasn't been published yet.")
        return doc

    @app.get("/geopolitics/analogues", response_model=schemas.Analogues, tags=["geopolitics"])
    def analogues(request: Request):
        """
        Event types the historical event study covers (crude spikes, rupee moves,
        conflict flare-ups, …), how often each happened and over which period.
        """
        doc = _analogues(request)
        return {**doc, "events": [{k: e[k] for k in schemas.AnalogueSummary.model_fields} for e in doc["events"]]}

    @app.get("/geopolitics/analogues/{code}", response_model=schemas.AnalogueDetail, tags=["geopolitics"])
    def analogue(
        request: Request,
        code: str,
        horizon: int | None = Query(None, description="Only this horizon (1, 3 or 10 trading days)"),
        notable: bool = Query(False, description="Only cells whose confidence interval excludes the baseline"),
    ):
        """
        What each sector did versus NIFTY 50 after past events of this type: average
        and median excess return, hit rate, 95% confidence interval and sample size,
        plus the latest occurrences with news evidence. Historical tendency, not a forecast.
        """
        event = next((e for e in _analogues(request)["events"] if e["code"] == code), None)
        if event is None:
            raise HTTPException(404, f"Unknown event type: {code}")
        cells = [c for c in event["sectors"]
                 if (horizon is None or c["horizon_days"] == horizon) and (not notable or c["notable"])]
        cells.sort(key=lambda c: (c["horizon_days"], c["mean_excess_pct"]))
        return {**event, "sectors": cells}

    # ── IPOs ────────────────────────────────────────────────────────────────

    def _nse(request: Request, key: str, ttl: int, load: Callable):
        try:
            return request.app.state.cache.get(key, ttl, load)
        except nse_ipo.NseUnavailable as exc:
            raise HTTPException(503, "NSE's IPO data is unavailable right now. Try again in a few minutes.") from exc

    @app.get("/ipos", response_model=schemas.IpoBoard, tags=["ipos"])
    def ipos(request: Request):
        """Open and upcoming IPOs on NSE, with live category-wise subscription for open mainboard issues."""
        nse = request.app.state.nse

        def load():
            current = {r["symbol"]: r for r in nse.current_issues()}
            listed = {r["symbol"]: r for r in nse.upcoming_issues()}
            issues = []
            for symbol in {**listed, **current}:
                raw = {**listed.get(symbol, {}), **current.get(symbol, {})}
                issue = ipo.build_issue(raw)
                if issue.status == "open" and issue.board == "mainboard":
                    try:
                        issue = ipo.build_issue(raw, ipo.parse_subscription(nse.category_subscription(symbol)))
                    except nse_ipo.NseUnavailable:
                        pass  # keep the overall figure from current_issues
                issues.append(issue)
            return issues

        issues = _nse(request, "ipos", IPO_TTL_SECONDS, load)
        by_date = lambda i: (i.closes or i.opens or "", i.name)  # noqa: E731
        return schemas.IpoBoard(
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            open=[i.to_dict() for i in sorted((i for i in issues if i.status == "open"), key=by_date)],
            upcoming=[i.to_dict() for i in sorted((i for i in issues if i.status == "upcoming"), key=by_date)],
        )

    @app.get("/ipos/listings", response_model=list[schemas.Listing], tags=["ipos"])
    def ipo_listings(request: Request, days: int = Query(90, ge=1, le=365), board: Literal["mainboard", "sme"] | None = None):
        """How recent IPOs have done: return from issue price to the latest price."""
        past = _nse(request, "ipo-past", LISTINGS_TTL_SECONDS, request.app.state.nse.past_issues)
        prices = {s.symbol: s.price for s in market_of(request).stocks() if s.price is not None}
        rows = ipo.recent_listings(past, prices, days)
        return [r for r in rows if board is None or r["board"] == board]

    # ── prospectus scanner ──────────────────────────────────────────────────

    @app.get("/prospectus/rules", tags=["prospectus"])
    def prospectus_rules():
        """What the scanner looks for."""
        return [{"id": r.id, "title": r.title, "why": r.why} for r in rhp.RULES]

    @app.post("/prospectus/scan", response_model=schemas.ScanResult, tags=["prospectus"])
    def prospectus_scan(request: Request, file: UploadFile = File(..., description="DRHP or RHP as a text PDF")):
        """Upload a prospectus PDF; get its red flags with page-numbered quotes. The file is not stored."""
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "That file is over 60 MB. Upload the DRHP or RHP PDF only.")
        slots = request.app.state.scan_slots
        if not slots.acquire(timeout=30):
            raise HTTPException(503, "The scanner is busy with other prospectuses. Try again in a minute.")
        try:
            return rhp.scan_pdf(data).to_dict()
        except rhp.ScanError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            slots.release()

    return app


app = create_app()
