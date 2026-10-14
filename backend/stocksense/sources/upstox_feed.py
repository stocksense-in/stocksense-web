"""
Decoder for Upstox market-data WebSocket messages (protobuf, feed v3).

We only need last price and previous close, so instead of compiling Upstox's
.proto file this walks the protobuf wire format directly. Relevant schema
(MarketDataFeedV3.proto, field numbers in brackets):

    FeedResponse { type[1]; map<string, Feed> feeds[2]; currentTs[3] }
    Feed         { LTPC ltpc[1] | FullFeed fullFeed[2] | FirstLevelWithGreeks[3] }
    FullFeed     { MarketFullFeed marketFF[1] | IndexFullFeed indexFF[2] }   → each has LTPC ltpc[1]
    LTPC         { double ltp[1]; int64 ltt[2]; int64 ltq[3]; double cp[4] }
"""

from __future__ import annotations

import struct
from typing import Iterator

VARINT, FIXED64, BYTES, FIXED32 = 0, 1, 2, 5


def _varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def _fields(buf: bytes) -> Iterator[tuple[int, int, object]]:
    """Yield (field_number, wire_type, value) for each field in a message."""
    pos = 0
    while pos < len(buf):
        tag, pos = _varint(buf, pos)
        field, wire = tag >> 3, tag & 7
        if wire == VARINT:
            value, pos = _varint(buf, pos)
        elif wire == FIXED64:
            value, pos = buf[pos : pos + 8], pos + 8
        elif wire == BYTES:
            length, pos = _varint(buf, pos)
            value, pos = buf[pos : pos + length], pos + length
        elif wire == FIXED32:
            value, pos = buf[pos : pos + 4], pos + 4
        else:
            return  # groups are not used by Upstox; stop rather than misread
        yield field, wire, value


def _ltpc(buf: bytes) -> tuple[float, float]:
    ltp = cp = 0.0
    for field, wire, value in _fields(buf):
        if wire == FIXED64 and field == 1:
            ltp = struct.unpack("<d", value)[0]
        elif wire == FIXED64 and field == 4:
            cp = struct.unpack("<d", value)[0]
    return ltp, cp


def _first_bytes_field(buf: bytes, number: int) -> bytes | None:
    for field, wire, value in _fields(buf):
        if field == number and wire == BYTES:
            return value
    return None


def _feed_ltpc(feed: bytes) -> tuple[float, float] | None:
    for field, wire, value in _fields(feed):
        if wire != BYTES:
            continue
        if field == 1:  # ltpc mode
            return _ltpc(value)
        if field == 2:  # full mode → marketFF or indexFF → ltpc
            for _, inner_wire, inner in _fields(value):
                if inner_wire == BYTES:
                    ltpc = _first_bytes_field(inner, 1)
                    return _ltpc(ltpc) if ltpc else None
        if field == 3:  # option greeks mode → ltpc
            ltpc = _first_bytes_field(value, 1)
            return _ltpc(ltpc) if ltpc else None
    return None


def decode(message: bytes) -> dict[str, tuple[float, float]]:
    """{instrument_key: (last_price, previous_close)} for every instrument in the message."""
    out: dict[str, tuple[float, float]] = {}
    try:
        _decode_into(message, out)
    except (IndexError, struct.error):
        pass  # truncated/corrupt frame — keep whatever decoded cleanly
    return out


def _decode_into(message: bytes, out: dict[str, tuple[float, float]]) -> None:
    for field, wire, entry in _fields(message):
        if field != 2 or wire != BYTES:
            continue
        key, feed = "", b""
        for f, w, v in _fields(entry):
            if f == 1 and w == BYTES:
                key = v.decode("utf-8", "replace")
            elif f == 2 and w == BYTES:
                feed = v
        prices = _feed_ltpc(feed) if feed else None
        if key and prices and prices[0]:
            out[key] = prices
