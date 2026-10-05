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

Common options
    --symbols INFY TCS   only these stocks          --limit N    only the first N stocks
    --snapshot [PATH]    also write results to a JSON file (default: frontend/data/snapshot.json)
    --no-db              skip Supabase (use with --snapshot to work offline)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import FRONTEND_SNAPSHOT, get_settings
from .db import Store


def _add_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbols", nargs="+", metavar="SYM", help="only these NSE symbols")
    parser.add_argument("--limit", type=int, metavar="N", help="only the first N symbols")


def _add_storage(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--snapshot",
        nargs="?",
        const=str(FRONTEND_SNAPSHOT),
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
    return parser


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

    if args.job == "upstox-login":
        from .jobs import upstox_login

        upstox_login.run(show_status=args.status)
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
    elif args.job == "scheduler":
        from .jobs import scheduler

        scheduler.run(store)


if __name__ == "__main__":
    main()
