"""Drawing a wire model's strokes on a canvas: the checks on where and how big, and one stroked path per ink.

The wire car and the wire jet props share this. Every measure is in canvas pixels. The lines are plain strokes with no
fill, so the scene behind the model shows through it: the prop is a drawing of the model's geometry, not a solid.
"""

from __future__ import annotations

import math
import re
import struct
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from .canvas import Canvas
from .wire_view import BANDS, NO_CEL, Drawing, WireError

__all__ = [
    "REFERENCE_WIDTH",
    "Anchor",
    "Placement",
    "Plate",
    "anchor_of",
    "band",
    "cel_plate",
    "edge_below",
    "place",
    "stroke",
]

REFERENCE_WIDTH = 1300.0  # the width a model is drawn at when its ink weights are as the generators wrote them
MIN_STROKE = 0.8


@dataclass(frozen=True)
class Placement:
    """Where a model goes, checked: its centre, its width and the scale of its strokes."""

    x: float
    y: float
    size: float
    weight: float


def _finite(value: object, what: str, error: type[WireError]) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise error(f"{what} must be a finite number, got {value!r}")
    return float(value)


def place(
    at: object, width: object, weight: object, *, narrowest: int, widest: int, error: type[WireError]
) -> Placement:
    """The checked centre, width and stroke scale of a model, or ``error`` saying which one cannot be drawn."""
    if not isinstance(at, tuple | list) or len(at) != 2:
        raise error(f"at is an (x, y) pair, got {at!r}")
    x, y = _finite(at[0], "at x", error), _finite(at[1], "at y", error)
    size = _finite(width, "width", error)
    if not narrowest <= size <= widest:
        raise error(f"width must be from {narrowest} to {widest} pixels, got {width!r}")
    scale = _finite(weight, "weight", error)
    if scale <= 0:
        raise error(f"weight must be above 0, got {weight!r}")
    return Placement(x, y, size, scale)


def stroke(
    cv: Canvas,
    parent,
    drawing: Drawing,
    placement: Placement,
    *,
    colours: Mapping[str, str],
    weights: Mapping[str, float],
    id: str,
):
    """A group centred on the placement with one stroked, unfilled path per ink of ``drawing``."""
    group = cv.group(parent, id, x=placement.x, y=placement.y)
    for name, lines in drawing.strokes.items():
        d = " ".join(
            "M" + " L".join(f"{px - drawing.width / 2:.2f} {py - drawing.height / 2:.2f}" for px, py in line)
            for line in lines
        )
        sw = max(MIN_STROKE, weights[name] * placement.weight * placement.size / REFERENCE_WIDTH)
        cv.path(group, d, cv.clear, colours[name], sw)
    return group


@dataclass(frozen=True)
class Anchor:
    """A named point of a placed model in canvas pixels, and the pixels in a metre there: where a person sits."""

    x: float
    y: float
    scale: float


def anchor_of(drawing: Drawing, placement: Placement, name: str, error: type[WireError]) -> Anchor:
    """Where the model's anchor ``name`` falls when ``drawing`` is stroked at ``placement``, or ``error``."""
    if name not in drawing.anchors:
        raise error(f"unknown anchor {name!r}; one of {', '.join(drawing.anchors)}")
    px, py = drawing.anchors[name]
    scale = drawing.anchor_scale.get(name, drawing.scale)
    return Anchor(placement.x + px - drawing.width / 2, placement.y + py - drawing.height / 2, scale)


def _rows(line, top: float, bottom: float) -> list[list[tuple[float, float]]]:
    """The runs of ``line`` that lie from row ``top`` to row ``bottom``."""
    runs: list[list[tuple[float, float]]] = []
    run: list[tuple[float, float]] = []
    for (x0, y0), (x1, y1) in zip(line, line[1:], strict=False):
        if y0 == y1:
            lo, hi = (0.0, 1.0) if top <= y0 <= bottom else (1.0, 0.0)
        else:
            a, b = (top - y0) / (y1 - y0), (bottom - y0) / (y1 - y0)
            lo, hi = max(0.0, min(a, b)), min(1.0, max(a, b))
        if lo > hi:
            if len(run) > 1:
                runs.append(run)
            run = []
            continue
        start = (x0 + (x1 - x0) * lo, y0 + (y1 - y0) * lo)
        end = (x0 + (x1 - x0) * hi, y0 + (y1 - y0) * hi)
        if not run or run[-1] != start:
            if len(run) > 1:
                runs.append(run)
            run = [start]
        run.append(end)
        if hi < 1.0:
            runs.append(run)
            run = []
    if len(run) > 1:
        runs.append(run)
    return runs


def band(drawing: Drawing, rows: object, error: type[WireError], tilt: object = 0.0) -> Drawing:
    """``drawing`` cut to ``rows``, a (top, bottom) pair of heights in pixels from the middle of its picture (where the
    prop is placed): a stroke that crosses either is cut there. A person can sit between the two halves of one drawing:
    the upper behind him, the lower in front. A ``tilt`` (pixels of height for each pixel across, from the middle of the
    picture) slopes both cuts, for an edge that a camera in perspective sees slanted."""
    if not isinstance(rows, tuple | list) or len(rows) != 2:
        raise error(f"rows is a (top, bottom) pair, got {rows!r}")
    first, last = _finite(rows[0], "top row", error), _finite(rows[1], "bottom row", error)
    slope = _finite(tilt, "tilt", error)
    middle = drawing.width / 2
    centre = drawing.height / 2
    if first >= last:
        raise error(f"rows run from a row to a lower one, got {rows!r}")
    strokes = {}
    for ink, lines in drawing.strokes.items():
        # a shear by the tilt makes the slanted cut level, and the cut is made there
        sheared = [[(x, y - slope * (x - middle)) for x, y in line] for line in lines]
        kept = tuple(
            tuple((x, y + slope * (x - middle)) for x, y in run)
            for line in sheared
            for run in _rows(line, first + centre, last + centre)
        )
        if kept:
            strokes[ink] = kept
    cel = drawing.cel
    if cel:  # the surfaces outside the rows go too
        width, height = drawing.width, drawing.height
        out = bytearray([NO_CEL]) * len(cel)
        for y in range(height):
            for x in range(width):
                if first + centre <= y - slope * (x - middle) <= last + centre:
                    out[y * width + x] = cel[y * width + x]
        cel = bytes(out)
    return replace(drawing, strokes=strokes, cel=cel)


def edge_below(
    drawing: Drawing, placement: Placement, point: Anchor, *, reach: float, below: float, error: type[WireError]
):
    """The top edge of the paint under ``point`` (an anchor): ``(row, tilt)`` for :func:`band`, measured in the cel
    raster over ``reach`` metres either side of it. From ``below`` metres under the point, each column goes up while it
    stays paint; the tops are fitted by a line, dropping those that stand apart from it (a pillar that joins the
    door)."""
    if not drawing.cel:
        raise error("the drawing has no cel raster: look at the model with a light")
    width, height = drawing.width, drawing.height
    cx = point.x - placement.x + width / 2
    cy = point.y - placement.y + height / 2
    start = int(cy + below * point.scale)
    tops: list[tuple[float, float]] = []
    for x in range(max(0, int(cx - reach * point.scale)), min(width, int(cx + reach * point.scale) + 1)):
        y = start
        if not 0 <= y < height or drawing.cel[y * width + x] // BANDS != 0:
            continue
        while y > 0 and drawing.cel[(y - 1) * width + x] // BANDS == 0:
            y -= 1
        tops.append((float(x), float(y)))
    if len(tops) < 8:
        raise error(f"there is no paint {below} m under the anchor to find an edge in")
    for _ in range(3):
        n = len(tops)
        mx, my = sum(x for x, _ in tops) / n, sum(y for _, y in tops) / n
        var = sum((x - mx) ** 2 for x, _ in tops)
        slope = sum((x - mx) * (y - my) for x, y in tops) / var if var else 0.0
        fit = [abs(y - (my + slope * (x - mx))) for x, y in tops]
        limit = max(2.0, sorted(fit)[len(fit) // 2] * 3)
        tops = [t for t, d in zip(tops, fit, strict=True) if d <= limit]
        if len(tops) < 8:
            raise error("the edge under the anchor is not a line")
    n = len(tops)
    mx, my = sum(x for x, _ in tops) / n, sum(y for _, y in tops) / n
    var = sum((x - mx) ** 2 for x, _ in tops)
    slope = sum((x - mx) * (y - my) for x, y in tops) / var if var else 0.0
    row = my + slope * (width / 2 - mx) - height / 2
    return row, slope


@dataclass(frozen=True)
class Plate:
    """A model's surfaces as a picture: ``png`` is ``width`` by ``height`` pixels, to be drawn with its corner at
    ``x``, ``y`` on the canvas, at the same scale as the strokes of the model placed the same way."""

    png: bytes
    x: float
    y: float
    width: int
    height: int


_COLOUR = re.compile(r"#[0-9a-fA-F]{6}")


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def cel_plate(drawing: Drawing, placement: Placement, ramps: Sequence[Sequence[str]], error: type[WireError]) -> Plate:
    """The cel raster of ``drawing`` painted from ``ramps`` (for each material, its :data:`BANDS` tones darkest first,
    as ``#rrggbb``) and placed where the strokes go. Where no surface is, the picture is clear."""
    if not drawing.cel:
        raise error("the drawing has no cel raster: look at the model with a light")
    if len(ramps) < 1 or any(len(r) != BANDS or not all(_COLOUR.fullmatch(str(c)) for c in r) for r in ramps):
        raise error(f"ramps are, for each material, {BANDS} tones as #rrggbb, darkest first")
    table = {}
    for code in set(drawing.cel):
        if code == NO_CEL:
            table[code] = b"\x00\x00\x00\x00"
            continue
        kind, tone = divmod(code, BANDS)
        if kind >= len(ramps):
            raise error(f"the surfaces use material {kind}, but only {len(ramps)} ramps were given")
        table[code] = bytes.fromhex(ramps[kind][tone][1:]) + b"\xff"
    width, height = drawing.width, drawing.height
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(b"".join(table[c] for c in drawing.cel[y * width : (y + 1) * width]))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + _chunk(b"IEND", b"")
    )
    return Plate(png, placement.x - width / 2, placement.y - height / 2, width, height)
