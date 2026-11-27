"""
StockSense pipeline CLI.

    python -m stocksense <job> [options]

Jobs
    fundamentals   price + P/E, ROE, D/E, margin → score         (daily, ~20 min for all stocks)
    ownership      promoter holding + revenue CAGR → re-score    (daily, slow)
    prices         latest prices for stocks and indices          (every few minutes in market hours)
    realtime       stream Upstox ticks into live_prices          (runs until stopped)
    upstox-login   sign in to Upstox and save today's token
    scheduler      run everything above on a market-hours timetable
    api            serve the REST API (docs at http://localhost:8000/docs)
    cleanup        list (or --apply delete) stocks no longer listed on NSE
    rescore        recompute every stored score after a scoring.py change (seconds, no Yahoo)
    snapshot       copy ~70 large caps from Supabase into backend/data/snapshot.json (API offline data)
    lake-prices    copy today's live_prices into the local data lake (STOCKSENSE_LAKE_DIR)  (daily)
    lake-query     run SQL against the data lake, e.g. "select date, count(*) from prices group by date"
    ingest-bhavcopy  NSE end-of-day prices for every security, 2010 → today, into the lake  (daily)
    ingest-corporate-actions  splits/bonuses/renames → adjusted price history (eod_adjusted)  (weekly)
    check-eod      data checks on the price history: gaps, duplicates, bad prices, unexplained jumps
    ingest-indices NSE index closes (every sector index), 2012 → today, into the lake  (daily)
    ingest-macro   crude, gold, rupee, US rates and equities — full daily history  (daily)
    ingest-gdelt   world news events (GDELT) since 2013 → daily aggregates + salient events  (daily)
    event-study    what sectors did after past crude spikes, rupee moves, conflict flare-ups…  (weekly)
    valuation-context  each sector's P/E today vs its own history → data/valuation_context.json  (weekly)
    financials-export  quarterly + yearly results from filings → data/financials.json  (weekly)
    holders-export     promoter holding over time + pledges → data/holders.json  (weekly)
    alerts-export      alerts over the last 10 sessions, every company → data/alerts.json  (daily)
    events-export      each company's notable announcements + insider trades → data/events.json  (daily)
    economy-export     latest repo rate, inflation, output, reserves, bond yield → data/economy.json  (weekly)
    ingest-india-macro RBI repo rate, CPI, IIP, forex reserves, 10y yield (with release dates) → lake  (weekly)
    dividends-export   dividends by year + splits/bonuses → data/dividends.json  (weekly)
    alerts         what happened to companies on a day: big moves, volume, results, orders, stakes, pledges
    ingest-results quarterly P&L history since 2005 from NSE filings (default: 20 largest companies)
    ingest-shareholding  promoter holding by quarter + promoter pledges (default: 50 largest; --all)
    engine-daily   update every lake source for the last N days, check the data, log the run  (daily)
    check-lake     data checks on the index, macro and GDELT datasets
    ingest-fno     NSE futures & options end-of-day file, 2010 → today: OI, put/call ratios  (daily)
    ingest-filings NSE announcements + insider trades since 2015, today's FII/DII flows  (daily)
    filings        a company's latest announcements and insider trades, e.g. `filings TCS`

Common options
    --symbols INFY TCS   only these stocks          --limit N    only the first N stocks
    --snapshot [PATH]    also write results to a JSON file (default: backend/data/snapshot.json)
    --no-db              skip Supabase (use with --snapshot to work offline)
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .config import SNAPSHOT_PATH, get_settings
from .db import Store


def _add_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbols", nargs="+", metavar="SYM", help="only these NSE symbols")
    parser.add_argument("--limit", type=int, metavar="N", help="only the first N symbols")


def _add_storage(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--snapshot",
        nargs="?",
        const=str(SNAPSHOT_PATH),
        metavar="PATH",
        help="also merge results into a JSON snapshot file",
    )
    parser.add_argument("--no-db", action="store_true", help="don't write to Supabase")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stocksense", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    jobs = parser.add_subparsers(dest="job", required=True, metavar="job")

    p = jobs.add_parser("fundamentals", help="fetch fundamentals and score stocks")
    _add_selection(p)
    _add_storage(p)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--refresh-symbols", action="store_true", help="re-download the NSE list")

    p = jobs.add_parser("ownership", help="fetch promoter holding and revenue CAGR")
    _add_selection(p)
    _add_storage(p)
    p.add_argument("--workers", type=int, default=4)

    p = jobs.add_parser("prices", help="fetch latest prices")
    _add_selection(p)
    _add_storage(p)
    p.add_argument("--source", choices=["yahoo", "upstox"], default="yahoo")

    p = jobs.add_parser("realtime", help="stream Upstox prices")
    _add_selection(p)
    _add_storage(p)

    p = jobs.add_parser("upstox-login", help="sign in to Upstox")
    p.add_argument("--status", action="store_true", help="only show the saved token's age")

    p = jobs.add_parser("scheduler", help="run jobs on a timetable")
    _add_storage(p)

    p = jobs.add_parser("api", help="serve the REST API")
    p.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to accept outside connections")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="restart on code changes (development)")

    p = jobs.add_parser("cleanup", help="find delisted/renamed stocks")
    p.add_argument("--apply", action="store_true", help="actually delete them")

    p = jobs.add_parser("rescore", help="recompute stored scores without refetching")
    p.add_argument("--fundamentals", choices=["yahoo", "filings"], default="yahoo",
                   help="where margin, growth, ROE and D/E come from (filings: compare only unless --apply)")
    p.add_argument("--apply", action="store_true", help="with --fundamentals filings: save the scores")
    p.add_argument("--metrics", nargs="+", choices=["net_margin", "cagr", "roe", "de", "promoter"],
                   help="with --fundamentals filings: switch only these metrics (e.g. promoter)")
    _add_storage(p)

    p = jobs.add_parser("snapshot", help="refresh the frontend's offline data file")
    p.add_argument("--symbols", nargs="+", metavar="SYM", help="instead of the default large caps")

    jobs.add_parser("lake-prices", help="copy today's live_prices into the data lake")

    p = jobs.add_parser("lake-query", help="run SQL against the data lake")
    p.add_argument("sql", help="each clean dataset is a view, e.g. prices")

    p = jobs.add_parser("ingest-bhavcopy", help="NSE end-of-day prices into the lake")
    _add_range(p)
    p.add_argument("--download-only", action="store_true", help="only fill raw/, don't build clean/")
    p.add_argument("--build-only", action="store_true", help="only build clean/ from files already downloaded")
    p.add_argument("--rebuild", action="store_true", help="rebuild days already in clean/")

    jobs.add_parser("ingest-corporate-actions", help="corporate actions → adjusted price history")
    jobs.add_parser("check-eod", help="data checks on the price history")

    p = jobs.add_parser("ingest-indices", help="NSE index closes into the lake")
    _add_range(p)
    p.add_argument("--rebuild", action="store_true", help="rebuild days already in clean/")
    jobs.add_parser("ingest-macro", help="global macro series into the lake")

    p = jobs.add_parser("ingest-gdelt", help="GDELT world news events into the lake")
    _add_range(p)
    p.add_argument("--download-only", action="store_true", help="only fill raw/, don't build clean/")
    p.add_argument("--build-only", action="store_true", help="only build clean/ from files already downloaded")
    p.add_argument("--rebuild", action="store_true", help="rebuild days already in clean/")
    p.add_argument("--workers", type=int, default=8, help="parallel processes for the build")

    jobs.add_parser("event-study", help="historical sector reactions to event types")
    jobs.add_parser("valuation-context", help="sector valuations vs their history, for the API")
    jobs.add_parser("financials-export", help="company financials from filings, for the API")
    jobs.add_parser("holders-export", help="promoter holding and pledges, for the API")
    jobs.add_parser("alerts-export", help="alerts over the last 10 sessions, for the API")
    jobs.add_parser("events-export", help="notable announcements and insider trades per company, for the API")
    jobs.add_parser("economy-export", help="India macro at a glance, for the API")
    jobs.add_parser("ingest-india-macro", help="RBI repo rate, CPI, IIP, forex reserves, 10y yield, with release dates")
    jobs.add_parser("dividends-export", help="dividends and capital actions, for the API")
    p = jobs.add_parser("alerts", help="alerts for a day (any past day replays)")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--symbols", nargs="+", metavar="SYM", help="only these companies (a watchlist)")

    p = jobs.add_parser("ingest-results", help="quarterly P&L history from NSE filings")
    p.add_argument("--symbols", nargs="+", metavar="SYM", help="these companies (default: the largest by market cap)")
    p.add_argument("--top", type=int, default=20, help="how many of the largest companies")
    p.add_argument("--rests", type=int, default=0,
                   help="when NSE stops answering, rest 15 min and resume, up to this many times")
    p.add_argument("--all", action="store_true", help="every NSE equity (use with --recent)")
    p.add_argument("--from", dest="start", metavar="SYM", help="start at this symbol (resume a run NSE cut short)")
    p.add_argument("--largest-first", action="store_true",
                   help="largest companies first (a multi-night --all backfill covers what matters most early)")
    p.add_argument("--recent", type=int, metavar="N",
                   help="only the last N quarters from integrated filings, one basis each (fast, whole market)")

    p = jobs.add_parser("ingest-shareholding", help="promoter holding by quarter and promoter pledges")
    p.add_argument("--symbols", nargs="+", metavar="SYM", help="these companies")
    p.add_argument("--top", type=int, default=50, help="how many of the largest companies")
    p.add_argument("--all", action="store_true", help="every NSE equity")
    p.add_argument("--rests", type=int, default=0,
                   help="when NSE stops answering, rest 15 min and resume, up to this many times")

    p = jobs.add_parser("engine-daily", help="update the whole lake and check it")
    p.add_argument("--days", type=int, default=10, help="how many recent days to fetch (catch-up after downtime)")
    p.add_argument("--weekly", action="store_true", help="also corporate actions and the event study")
    jobs.add_parser("check-lake", help="data checks on the index, macro and GDELT datasets")

    p = jobs.add_parser("ingest-fno", help="NSE F&O end-of-day prices and OI into the lake")
    _add_range(p)
    p.add_argument("--download-only", action="store_true", help="only fill raw/, don't build clean/")
    p.add_argument("--build-only", action="store_true", help="only build clean/ from files already downloaded")
    p.add_argument("--rebuild", action="store_true", help="rebuild days already in clean/")
    p.add_argument("--workers", type=int, default=8, help="parallel processes for the build")

    p = jobs.add_parser("ingest-filings", help="NSE announcements, insider trades and FII/DII flows")
    _add_range(p)

    p = jobs.add_parser("filings", help="a company's latest announcements and insider trades")
    p.add_argument("symbol")
    p.add_argument("--since", type=date.fromisoformat, metavar="YYYY-MM-DD", help="default: a year ago")
    p.add_argument("--limit", type=int, default=20)
    return parser


def _add_range(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", type=date.fromisoformat, metavar="YYYY-MM-DD", help="first day")
    parser.add_argument("--end", type=date.fromisoformat, metavar="YYYY-MM-DD", help="last day (default today)")


def _store(args: argparse.Namespace) -> Store:
    use_db = not args.no_db
    if use_db and not get_settings().has_supabase:
        raise SystemExit(
            "Supabase isn't configured (SUPABASE_URL / SUPABASE_SERVICE_KEY).\n"
            "Add them to backend/.env, or run with --no-db --snapshot to write a local file."
        )
    snapshot = Path(args.snapshot) if args.snapshot else None
    if not use_db and not snapshot:
        raise SystemExit("--no-db needs --snapshot, otherwise results go nowhere.")
    return Store(use_db=use_db, snapshot_path=snapshot)


def main() -> None:
    args = _build_parser().parse_args()

    if args.job == "api":
        import uvicorn

        uvicorn.run("stocksense.api:app", host=args.host, port=args.port, reload=args.reload)
        return

    if args.job == "cleanup":
        from .jobs import cleanup

        cleanup.run(apply=args.apply)
        return

    if args.job == "snapshot":
        from .jobs import snapshot

        snapshot.run(args.symbols)
        return

    if args.job == "upstox-login":
        from .jobs import upstox_login

        upstox_login.run(show_status=args.status)
        return

    if args.job == "lake-prices":
        from .jobs import lake_prices

        lake_prices.run()
        return

    if args.job == "lake-query":
        from .jobs import lake_prices

        lake_prices.query(args.sql)
        return

    if args.job == "ingest-bhavcopy":
        from .jobs import ingest_bhavcopy

        ingest_bhavcopy.run(args.start, args.end, download_only=args.download_only,
                            build_only=args.build_only, rebuild=args.rebuild)
        return

    if args.job in ("ingest-corporate-actions", "check-eod"):
        from .jobs import ingest_corporate_actions

        if args.job == "check-eod":
            ingest_corporate_actions.check()
        else:
            ingest_corporate_actions.run()
        return

    if args.job in ("ingest-indices", "ingest-macro"):
        from .jobs import ingest_market

        if args.job == "ingest-indices":
            ingest_market.run_indices(args.start, args.end, rebuild=args.rebuild)
        else:
            ingest_market.run_macro()
        return

    if args.job == "ingest-gdelt":
        from .jobs import ingest_gdelt

        ingest_gdelt.run(args.start, args.end, download_only=args.download_only, build_only=args.build_only,
                         rebuild=args.rebuild, workers=args.workers)
        return

    if args.job == "ingest-shareholding":
        from .jobs import ingest_shareholding

        ingest_shareholding.run(args.symbols, args.top, everything=args.all, rests=args.rests)
        return

    if args.job == "ingest-results":
        from .jobs import ingest_results

        ingest_results.run(args.symbols, args.top, rests=args.rests, everything=args.all, recent=args.recent,
                           start=args.start, by_size=args.largest_first)
        return

    if args.job == "alerts":
        from datetime import date as _date

        from . import alerts
        from .lake import Lake

        day = _date.fromisoformat(args.date) if args.date else _date.today()
        found = alerts.for_day(Lake.from_settings(), day, args.symbols)
        for a in found:
            print(f"{a['symbol']:<12} {a['kind']:<15} {a['text']}")
        print(f"{len(found)} alerts for {day}")
        return

    if args.job == "dividends-export":
        from . import dividends
        from .lake import Lake

        doc = dividends.write(Lake.from_settings())
        print(f"Wrote dividends for {len(doc['companies'])} companies to {dividends.OUTPUT}")
        return

    if args.job == "ingest-india-macro":
        from .jobs import ingest_india_macro

        df = ingest_india_macro.run()
        print(df.groupby("series")["period"].agg(["min", "max", "count"]).to_string())
        return

    if args.job == "alerts-export":
        from . import alerts
        from .lake import Lake

        doc = alerts.write(Lake.from_settings())
        print(f"Wrote {len(doc['alerts'])} alerts over {len(doc['days'])} sessions to {alerts.OUTPUT}")
        return

    if args.job == "economy-export":
        from . import economy
        from .lake import Lake

        doc = economy.write_from_lake(Lake.from_settings())
        print(f"Wrote {len(doc['series'])} series to {economy.OUTPUT}")
        return

    if args.job == "events-export":
        from . import events
        from .lake import Lake

        doc = events.write(Lake.from_settings())
        print(f"Wrote events for {len(doc['companies'])} companies to {events.OUTPUT}")
        return

    if args.job == "holders-export":
        from . import holders
        from .lake import Lake

        doc = holders.write(Lake.from_settings())
        print(f"Wrote holders for {len(doc['companies'])} companies to {holders.OUTPUT}")
        return

    if args.job == "financials-export":
        from . import financials
        from .lake import Lake

        doc = financials.write(Lake.from_settings())
        print(f"Wrote financials for {len(doc['companies'])} companies to {financials.OUTPUT}")
        return

    if args.job == "valuation-context":
        from . import valuation
        from .lake import Lake

        doc = valuation.write(Lake.from_settings())
        print(f"Wrote {len(doc['indices'])} index valuations to {valuation.OUTPUT}")
        return

    if args.job == "event-study":
        from .jobs import event_study

        event_study.run()
        return

    if args.job in ("ingest-filings", "filings"):
        from .jobs import ingest_filings

        if args.job == "filings":
            ingest_filings.show(args.symbol, args.since, args.limit)
        else:
            ingest_filings.run(args.start, args.end)
        return

    if args.job == "ingest-fno":
        from .jobs import ingest_fno

        ingest_fno.run(args.start, args.end, download_only=args.download_only, build_only=args.build_only,
                       rebuild=args.rebuild, workers=args.workers)
        return

    if args.job == "engine-daily":
        from .jobs import engine_daily

        raise SystemExit(engine_daily.run(days=args.days, weekly=args.weekly))

    if args.job == "check-lake":
        import json

        from . import lake_checks
        from .lake import Lake

        print(json.dumps(lake_checks.check_all(Lake.from_settings()), indent=1, ensure_ascii=False))
        return

    store = _store(args)
    if args.job == "fundamentals":
        from .jobs import fundamentals

        fundamentals.run(store, args.symbols, args.limit, args.workers,
                         refresh_symbols=args.refresh_symbols)
    elif args.job == "ownership":
        from .jobs import ownership

        ownership.run(store, args.symbols, args.limit, args.workers)
    elif args.job == "prices":
        from .jobs import prices

        prices.run(store, args.symbols, args.limit, source=args.source)
    elif args.job == "realtime":
        from .jobs import realtime

        realtime.run(store, args.symbols, args.limit)
    elif args.job == "rescore":
        from .jobs import rescore

        rescore.run(store, args.fundamentals, args.apply, args.metrics)
    elif args.job == "scheduler":
        from .jobs import scheduler

        scheduler.run(store)


if __name__ == "__main__":
    main()
