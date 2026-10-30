"""Read the pixels of a PNG the engine wrote, without an imaging library: 8-bit RGB or RGBA, not interlaced (what
scene-render writes). Decoding runs in plain Python, so a test renders a small frame (a crop of the scene) to read."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {2: 3, 6: 4}  # colour type: bytes per pixel at 8 bits


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def read_png(path: Path) -> tuple[int, int, list[bytes]]:
    """``(width, height, rows)``: each row is the RGB(A) bytes of one line of pixels, top first."""
    data = Path(path).read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError(f"{path} is not a PNG")
    at, chunks, head = len(SIGNATURE), [], None
    while at < len(data):
        (size,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + size]
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            chunks.append(body)
        at += 12 + size
    if head is None:
        raise ValueError(f"{path} has no header")
    width, height, depth, colour, _, _, interlace = head
    if depth != 8 or colour not in CHANNELS or interlace:
        raise ValueError(f"{path}: only 8-bit RGB or RGBA, not interlaced, is read; got {head}")
    bpp = CHANNELS[colour]
    raw = zlib.decompress(b"".join(chunks))
    stride = width * bpp
    rows: list[bytes] = []
    prior = bytearray(stride)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = prior[i]
            corner = prior[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                line[i] = (line[i] + _paeth(left, up, corner)) & 255
            elif kind != 0:
                raise ValueError(f"{path}: unknown filter {kind} on line {y}")
        rows.append(bytes(line))
        prior = line
    return width, height, rows


def pixel(rows: list[bytes], x: int, y: int, bpp: int = 4) -> tuple[int, ...]:
    return tuple(rows[y][x * bpp : x * bpp + 3])
