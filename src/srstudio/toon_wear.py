"""What a Toon character wears per pose (:data:`srstudio.toon.WEAR`): glasses, a sweat drop, a flush.

The items are drawn about a :class:`Face` (where the eyes and the mouth are, in reference pixels), so a brush
character (:func:`face_of` its :class:`~srstudio.toon_cast.Look`) and the traced cat (:data:`CAT_FACE`, measured
from its art) wear the same things. :func:`wear_layers` gives two runs of layers: what goes under the mouth, nose
and whiskers (the flush on the cheeks, clear of a blink's lids) and what goes over the face (the glasses, kept on
over the lids, and the sweat drop), under any paws raised to the face. The items draw in :data:`WEAR` order
whatever order a pose lists them in; an unknown item or one listed twice is refused (:class:`ToonDataError`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import brush
from .brush import Point
from .toon import WEAR, ToonDataError
from .toon_cast import FINE, INK, Layer, Look, _tear

__all__ = ["Face", "CAT_FACE", "SWEAT", "FLUSH", "FLUSH_LINE", "face_of", "check", "wear_layers"]

SWEAT = "#bfe6ff"
FLUSH = "#f47a86"
FLUSH_LINE = "#d0455a"
GLASS_AIR = 0.18  # the room between an eye's rim and its lens, in eye radii; a shocked eye bulges past it


@dataclass(frozen=True)
class Face:
    """Where a face is: the two eye centres (left first), the eye radius, the mouth's centre and width."""

    eyes: tuple[Point, Point]
    eye_r: float
    mouth: Point
    mouth_w: float


# measured from assets/toon/cat.json: the centres of the "wide" eye whites and of the "flat" mouth's ink
CAT_FACE = Face(((166.0, 586.8), (253.7, 586.9)), 22.2, (203.5, 629.4), 58.0)


def face_of(look: Look) -> Face:
    return Face(look.eyes, look.eye_r, look.mouth, look.mouth_w)


def check(items: Sequence[str]) -> None:
    """Refuse an item that is not in :data:`WEAR`, or one listed twice."""
    for item in items:
        if item not in WEAR:
            raise ToonDataError(f"wear {item!r} is not one of {WEAR}")
        if list(items).count(item) > 1:
            raise ToonDataError(f"wears {item!r} twice")


def _glasses(face: Face) -> list[Layer]:
    """Round lenses framing both eyes, a bridge between them, the arms running back, a glint on each glass."""
    r = face.eye_r
    lens = r * (1 + GLASS_AIR) + INK
    (lx, ly), (rx, ry) = face.eyes
    frames: list[Layer] = []
    glints: list[Layer] = []
    for ex, ey in face.eyes:
        ring = [(ex + lens * math.cos(a), ey + lens * math.sin(a)) for a in (2 * math.pi * k / 16 for k in range(19))]
        frames.append((brush.stroke(ring, INK * 0.8, brush.EVEN), "ink"))
        glint = [(ex - 0.55 * lens, ey - 0.15 * lens), (ex - 0.15 * lens, ey - 0.55 * lens)]
        glints.append((brush.stroke(glint, FINE, brush.EVEN, steps=3), "white"))
    bridge = [(lx + lens, ly), ((lx + rx) / 2, (ly + ry) / 2 - 4.0), (rx - lens, ry)]
    frames.append((brush.stroke(bridge, INK * 0.7, brush.EVEN), "ink"))
    for x, y, out in ((lx - lens, ly, -1.0), (rx + lens, ry, 1.0)):
        frames.append((brush.stroke([(x, y), (x + out * 16.0, y - 5.0)], INK * 0.7, brush.EVEN, steps=3), "ink"))
    return frames + glints


def _sweat(face: Face) -> list[Layer]:
    """A drop by the far temple, above the eye line."""
    (ex, ey), r = face.eyes[1], face.eye_r
    drop = _tear(ex + r + INK + 8.0, ey - r - 26.0, 1.2)
    x0, y0, x1, y1 = brush.bounds(brush.outline(drop))
    glint = brush.ellipse(x0 + (x1 - x0) * 0.38, y0 + (y1 - y0) * 0.62, 2.0, 3.0)
    return [(brush.rim(drop, FINE), "ink"), (brush.outline(drop), SWEAT), (glint, "white")]


def _flush(face: Face) -> list[Layer]:
    """A red patch hatched across each cheek, a little out from under the eye and low enough that a blink's lids
    leave it showing."""
    r = face.eye_r
    out: list[Layer] = []
    for (ex, ey), inner in zip(face.eyes, (1.0, -1.0), strict=True):
        cx, cy = ex - inner * 0.5 * r, ey + r + INK + 2.0 + 0.45 * r
        out.append((brush.ellipse(cx, cy, 1.1 * r, 0.45 * r), FLUSH))
        for k in (-1.0, 0.0, 1.0):
            x = cx + k * 0.45 * r
            line = [(x + 0.18 * r, cy - 0.3 * r), (x - 0.18 * r, cy + 0.3 * r)]
            out.append((brush.stroke(line, FINE * 0.8, brush.EVEN, steps=3), FLUSH_LINE))
    return out


def wear_layers(face: Face, items: Sequence[str]) -> tuple[list[Layer], list[Layer]]:
    """The ``items`` worn on ``face`` as (under the mouth, over the face) runs of layers, reference pixels."""
    check(items)
    under = _flush(face) if "flush" in items else []
    over = (_glasses(face) if "glasses" in items else []) + (_sweat(face) if "sweat" in items else [])
    return under, over
