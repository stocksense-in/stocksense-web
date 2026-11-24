import logging
import sys

# Windows terminals default to cp1252 and fail on "₹" — force UTF-8. Log lines go to
# stderr, so it needs the same treatment.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
# yfinance logs an error line for every delisted ticker; keep our output readable.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("pypdf").setLevel(logging.ERROR)  # malformed-PDF chatter; we report errors ourselves


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
