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

    if args.job == "event-study":
        from .jobs import event_study

        event_study.run()
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

        rescore.run(store)
    elif args.job == "scheduler":
        from .jobs import scheduler

        scheduler.run(store)


if __name__ == "__main__":
    main()
