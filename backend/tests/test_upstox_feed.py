import struct

from stocksense.sources.upstox_feed import decode


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _bytes_field(number: int, payload: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(payload)) + payload


def _double_field(number: int, value: float) -> bytes:
    return _varint(number << 3 | 1) + struct.pack("<d", value)


def _ltpc(ltp: float, cp: float) -> bytes:
    # ltt (field 2) is an int64 varint in v3 — include it to make sure it's skipped.
    return _double_field(1, ltp) + _varint(2 << 3 | 0) + _varint(1_700_000_000_000) + _double_field(4, cp)


def _response(entries: dict[str, bytes]) -> bytes:
    msg = _varint(1 << 3 | 0) + _varint(1)  # type enum
    for key, feed in entries.items():
        msg += _bytes_field(2, _bytes_field(1, key.encode()) + _bytes_field(2, feed))
    return msg


def test_decodes_ltpc_mode():
    msg = _response({"NSE_EQ|INE009A01021": _bytes_field(1, _ltpc(1842.5, 1816.0))})
    assert decode(msg) == {"NSE_EQ|INE009A01021": (1842.5, 1816.0)}


def test_decodes_full_mode_market_and_index():
    market = _bytes_field(2, _bytes_field(1, _bytes_field(1, _ltpc(934.0, 915.0))))
    index = _bytes_field(2, _bytes_field(2, _bytes_field(1, _ltpc(24762.0, 24560.0))))
    result = decode(_response({"NSE_EQ|A": market, "NSE_INDEX|Nifty 50": index}))
    assert result == {"NSE_EQ|A": (934.0, 915.0), "NSE_INDEX|Nifty 50": (24762.0, 24560.0)}


def test_ignores_garbage():
    assert decode(b"") == {}
