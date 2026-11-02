"""Verify bounded static RGBA8 PNG streams in the composition worker."""

from __future__ import annotations

import hashlib
import struct
import zlib

from . import composition as c

MAX_BYTES = 8 * 1024**2


def verify(data: bytes, width: int, height: int) -> str:
    def fail() -> c.CompositionError:
        return c._fail('image', None, 'a complete bounded RGBA8 PNG at the declared dimensions', 'composition.payload')

    if (
        type(data) is not bytes
        or not 8 <= len(data) <= MAX_BYTES
        or data[:8] != b'\x89PNG\r\n\x1a\n'
        or any(type(v) is not int or not 1 <= v <= 8192 for v in (width, height))
    ):
        raise fail()
    position, chunks, state = 8, 0, 'header'
    compressed = bytearray()
    seen = set()
    while position + 12 <= len(data):
        count = struct.unpack_from('>I', data, position)[0]
        kind = data[position + 4 : position + 8]
        end = position + 8 + count
        if end + 4 > len(data) or chunks >= 4096:
            raise fail()
        body = data[position + 8 : end]
        if zlib.crc32(kind + body) != struct.unpack_from('>I', data, end)[0]:
            raise fail()
        position, chunks = end + 4, chunks + 1
        if state == 'header':
            if kind != b'IHDR' or count != 13 or struct.unpack('>IIBBBBB', body) != (width, height, 8, 6, 0, 0, 0):
                raise fail()
            state = 'before-data'
        elif kind == b'IDAT' and state in ('before-data', 'data'):
            compressed.extend(body)
            state = 'data'
        elif kind in (b'sRGB', b'gAMA', b'pHYs') and state == 'before-data':
            if kind in seen or count != {b'sRGB': 1, b'gAMA': 4, b'pHYs': 9}[kind]:
                raise fail()
            seen.add(kind)
        elif kind == b'IEND' and count == 0 and state == 'data' and position == len(data):
            state = 'end'
            break
        else:
            raise fail()
    if state != 'end':
        raise fail()
    expected = (width * 4 + 1) * height
    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(compressed, expected + 1)
    except zlib.error as error:
        raise fail() from error
    if (
        len(raw) != expected
        or not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
        or any(value > 4 for value in raw[:: width * 4 + 1])
    ):
        raise fail()
    return hashlib.sha256(data).hexdigest()
