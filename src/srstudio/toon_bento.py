"""Bento, a capybara in a blazer, drawn by the operator and ported to the Toon style (ADR 0062).

He is drawn from the operator's geometry and colours, placed in reference pixels by :func:`_at`: a broad muzzle with
two front teeth, caramel fur, small round ears, a tailored blue blazer and tiny paws. A path here is plain numbers
(:data:`Path`), each step a line, a quadratic or a cubic, turned into a :data:`srstudio.brush.Shape`; a line of a given
weight is a :func:`srstudio.brush.stroke`, and a gradient a :class:`srstudio.toon_cast.Ramp`.

What he does is data:

* :data:`MOODS`, 36 typed :class:`Mood` records: where each brow and lid sits, the gaze, the mouth, the head's tilt, the
  pupil's size, the marks (cheeks, flush, tears, sweat, bags under the eyes, a wrinkled nose) and the gesture that goes
  with it. :func:`mood` refuses a name it does not know;
* :data:`EYE_STATES`, 12 ways the eyes can look or shut over any mood;
* :data:`GESTURES`, 9 poses of the arms.

A pose names them: ``eyes`` is a mood, a state, or ``mood/state`` (:func:`pose_of`), ``mouth`` one of
:data:`MOUTH_KINDS` and ``arms`` a gesture. Every shared kind of :data:`srstudio.toon.EYES`,
:data:`srstudio.toon.MOUTHS` and :data:`srstudio.toon.ARMS` draws on him too, as the nearest thing he has, so a sketch's
poses work unchanged.

His head lies over the body with its own chin, and his muzzle rides in the face group, so his mouth is always on it
(:data:`BENTO_RIG`). The registered drawing is that rig with a still plan: one drawing, whether or not the head moves.

His hands are a pair from version 2 (ADR 0097): a :class:`Paw` is on an :class:`Arm` and shows a :class:`Facing`, and
the drawing follows from those two, so a thumb follows its side. :data:`BENTO_RIG_2` is that version; version 1 keeps
its one hand on both arms, as first approved.
"""

from __future__ import annotations

import enum
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from types import MappingProxyType
from typing import TYPE_CHECKING

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .contracts import Operation, ParameterContract, PartContract
from .head_motion import HeadPlan, HeadStyle, Spring
from .registry import register
from .toon import ARMS, Pose, ToonDataError
from .toon_cast import CENTRE, HEART, SHOULDERS, Layer, Look, Mouths, Ramp, _heart
from .toon_head import HeadRig, figure

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "Arm",
    "BENTO",
    "BENTO_2",
    "BENTO_MOTION",
    "BENTO_RIG",
    "BENTO_RIG_2",
    "CENTRED",
    "DRAWN_FOR",
    "EAR",
    "EYE_STATES",
    "EyeState",
    "Facing",
    "GESTURES",
    "Gesture",
    "HEAD",
    "MARKS",
    "MOODS",
    "MOUTH_KINDS",
    "MUZZLE",
    "MUZZLE_LAP",
    "Mood",
    "Paw",
    "SCLERA",
    "SHIRT",
    "TILT_REACH",
    "TOOTH",
    "bento",
    "mood",
    "pose_of",
    "skull_layers",
    "trunk_layers",
]

Path = tuple[tuple[float, ...], ...]  # the start, then each step: (x, y), a line; 4 numbers, a quad; 6, a cubic
Place = Callable[[float, float], Point]

SIZE = 0.85  # reference pixels to one of his drawing's
PIVOT_X = 298.0  # the drawing's axis and the bottom of its chin go to the Toon axis and to CHIN_Y
CHIN = 457.0
CHIN_Y = 700.0
CENTRED = 111.0  # how far a framing moves him to stand in the middle of the frame, reference pixels
TILT_REACH = 7.0  # the most any mood tilts his head, degrees
MUZZLE_LAP = 6.0  # how far past the head's line his muzzle reaches at the ends of a nod and a glance; it laps the
# line by 3.6 reference pixels at rest, as he is drawn
FACE_SLIDE = 0.2  # his muzzle fills his head: a nod carries it with the skull and slides it only this much further

FUR = ((0.0, "#E2AB75"), (1.0, "#C78C58"))
SNOUT = ((0.0, "#EABE88"), (1.0, "#D59B66"))
JACKET = ((0.0, "#204CC4"), (1.0, "#14265A"))
FUR_FLAT = "#D49A65"
SNOUT_FLAT = "#DFAC77"
JACKET_FLAT = "#1A398F"
DARK_FUR = "#754B33"
HEAD_LINE = "#A56B45"
MUZZLE_LINE = "#B47D51"
PAW_LINE = "#A16A44"
SLEEVE_LINE = "#132B60"
EAR = "#9D6545"
SCLERA = "#FFF9EB"
IRIS = "#66513C"
PUPIL = "#102638"
SHIRT = "#F8FAFF"
TOOTH = "#FFF9E8"
THROAT = "#653C30"
TONGUE = "#C86D62"
RIM = "#947748"  # his wire glasses
SHADOW = "#10204126"  # the soft shadow under a plate, at its strength

MARKS = frozenset({"cheeks", "flush", "tears", "sweat", "bags", "wrinkle"})
SHUT_KINDS = ("", "happy", "soft")
LEVEL_BROWS = frozenset({"neutral", "deadpan", "bored", "tired"})


# -- the geometry ------------------------------------------------------------------------------------------------------
def _at(x: float, y: float) -> Point:
    """A point of his drawing in reference pixels."""
    return CENTRE + (x - PIVOT_X) * SIZE, CHIN_Y + (y - CHIN) * SIZE


def _off(point: Point) -> Point:
    """A reference pixel as a point of his drawing."""
    return PIVOT_X + (point[0] - CENTRE) / SIZE, CHIN + (point[1] - CHIN_Y) / SIZE


def _same(x: float, y: float) -> Point:
    return x, y


def _moved(x: float, y: float, angle: float = 0.0, scale: float = 1.0, flip: float | None = None) -> Place:
    """What places a part drawn about its own origin: reflected across the vertical at ``flip`` if there is one,
    scaled, turned ``angle`` degrees clockwise, then moved."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)

    def place(px: float, py: float) -> Point:
        if flip is not None:
            px = 2.0 * flip - px
        px, py = px * scale, py * scale
        return x + px * c - py * s, y + px * s + py * c

    return place


def _cubics(path: Path, place: Place = _same) -> list[tuple[Point, Point, Point, Point]]:
    """``path`` as cubic pieces, in reference pixels."""
    start = place(path[0][0], path[0][1])
    here = (path[0][0], path[0][1])
    out = []
    for step in path[1:]:
        if len(step) == 2:
            to = (step[0], step[1])
            a = (here[0] + (to[0] - here[0]) / 3, here[1] + (to[1] - here[1]) / 3)
            b = (here[0] + (to[0] - here[0]) * 2 / 3, here[1] + (to[1] - here[1]) * 2 / 3)
        elif len(step) == 4:
            q, to = (step[0], step[1]), (step[2], step[3])
            a = (here[0] + (q[0] - here[0]) * 2 / 3, here[1] + (q[1] - here[1]) * 2 / 3)
            b = (to[0] + (q[0] - to[0]) * 2 / 3, to[1] + (q[1] - to[1]) * 2 / 3)
        else:
            a, b, to = (step[0], step[1]), (step[2], step[3]), (step[4], step[5])
        out.append((place(*here), place(*a), place(*b), place(*to)))
        here = to
    if not out:
        raise ToonDataError(f"a path needs a step after its start {start!r}")
    return out


def _mapped(place: Place) -> Place:
    def into(x: float, y: float) -> Point:
        return _at(*place(x, y))

    return into


def _shape(path: Path, place: Place = _same) -> Shape:
    """``path`` closed, as a brush shape in reference pixels."""
    pieces = _cubics(path, _mapped(place))
    flat: list[float] = list(pieces[0][0])
    for _, a, b, to in pieces:
        flat += [*a, *b, *to]
    if pieces[-1][3] != pieces[0][0]:
        start, end = pieces[0][0], pieces[-1][3]
        flat += [*end, *start, *start]
    return tuple(round(v, 3) for v in flat)


def _samples(path: Path, place: Place = _same, per_piece: int = 8) -> list[Point]:
    """Points along ``path`` in the coordinates ``place`` gives."""
    out: list[Point] = []
    for p0, p1, p2, p3 in _cubics(path, place):
        for k in range(per_piece + 1):
            if out and k == 0:
                continue
            t = k / per_piece
            m = 1.0 - t
            a, b, c, d = m * m * m, 3 * m * m * t, 3 * m * t * t, t * t * t
            out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _outline(path: Path, place: Place = _same) -> tuple[Point, ...]:
    """The contour of ``path`` in reference pixels, what a rig measures."""
    return tuple(_samples(path, _mapped(place)))


def _line(path: Path, colour: str, width: float, place: Place = _same) -> Layer:
    """An open line of ``width`` in his drawing's pixels."""
    return brush.stroke(_samples(path, _mapped(place)), width * SIZE, brush.EVEN, steps=2), colour


def _trace(points: Sequence[Point], colour: str, width: float) -> Layer:
    """A line through points of his drawing."""
    return brush.stroke([_at(x, y) for x, y in points], width * SIZE, brush.EVEN, steps=2), colour


def _edge(path: Path, colour: str, width: float, place: Place = _same) -> Layer:
    """The line round a closed ``path``, centred on its edge the way a stroked shape's is."""
    points = _samples(path, _mapped(place))
    if points[0] != points[-1]:
        points.append(points[0])
    return brush.stroke(points, width * SIZE, brush.EVEN, steps=2), colour


def _ringed(path: Path, colour: str, width: float, place: Place = _same) -> Layer:
    """The line right round a closed ``path``. :func:`_edge` stops a segment short of its start, because a stroke drops
    a last point that repeats its first (:func:`srstudio.brush.stroke`), so this one laps past the start instead."""
    points = _samples(path, _mapped(place))
    return brush.stroke([*points, *points[:2]], width * SIZE, brush.EVEN, steps=2), colour


def _oval(x: float, y: float, rx: float, ry: float, colour: str, place: Place = _same, tilt: float = 0.0) -> Layer:
    cx, cy = _at(*place(x, y))
    return brush.ellipse(cx, cy, rx * SIZE, ry * SIZE, tilt), colour


def _ramp(kind: str, stops: Sequence[tuple[float, str]], flat: str, shape: Shape, share: float = 1.0) -> Ramp:
    """A gradient across ``shape``'s box: down it, or from the top left when ``kind`` is not the snout's."""
    x0, y0, x1, y1 = brush.bounds(shape)
    across = 0.0 if kind == "snout" else share
    box = (round(x0, 1), round(y0, 1), round(x0 + (x1 - x0) * across, 1), round(y1, 1))
    return Ramp(flat, f"bento-{kind}-{box[0]:g}-{box[1]:g}-{box[2]:g}-{box[3]:g}", stops, box)


def _furred(path: Path, line: str, place: Place = _same) -> list[Layer]:
    """A bare part: caramel fur, its gradient across it, a thin brown line."""
    shape = _shape(path, place)
    return [(shape, _ramp("fur", FUR, FUR_FLAT, shape, 0.8)), _edge(path, line, 2.0, place)]


def _sleeve(path: Path, line: str = SLEEVE_LINE, kind: str = "sleeve") -> list[Layer]:
    shape = _shape(path)
    return [(shape, _ramp(kind, JACKET, JACKET_FLAT, shape)), _edge(path, line, 3.0)]


def _shadow(path: Path) -> Layer:
    """The drop shadow a plate casts on what is under it, its edge unblurred."""
    return brush.shift(_shape(path), 3.0 * SIZE, 6.0 * SIZE), SHADOW


def _span(polygon: Sequence[Point], x: float) -> tuple[float, float] | None:
    """Where the vertical at ``x`` enters and leaves ``polygon``."""
    hits = []
    for (x0, y0), (x1, y1) in zip(polygon, [*polygon[1:], polygon[0]], strict=True):
        if (x0 <= x) != (x1 <= x):
            hits.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
    return (min(hits), max(hits)) if hits else None


def _meet(a: Sequence[Point], b: Sequence[Point], columns: int = 40) -> list[Point]:
    """The part of ``b`` inside ``a``, read off in columns: what a clip does, for shapes with a top and a bottom."""
    if not a or not b:
        return []
    lo = max(min(x for x, _ in a), min(x for x, _ in b)) + 1e-6
    hi = min(max(x for x, _ in a), max(x for x, _ in b)) - 1e-6
    tops: list[Point] = []
    bottoms: list[Point] = []
    for k in range(columns + 1):
        x = lo + (hi - lo) * k / columns
        first, second = _span(a, x), _span(b, x)
        if first is None or second is None:
            continue
        top, bottom = max(first[0], second[0]), min(first[1], second[1])
        if bottom > top:
            tops.append((x, top))
            bottoms.append((x, bottom))
    return tops + bottoms[::-1] if len(tops) >= 2 else []


def _ring(x: float, y: float, rx: float, ry: float, n: int = 36) -> list[Point]:
    return [(x + rx * math.cos(2 * math.pi * k / n), y + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _patch(points: Sequence[Point], colour: str) -> list[Layer]:
    """Points of his drawing filled as they stand, or nothing where a clip left nothing."""
    if len(points) < 3:
        return []
    placed = [_at(x, y) for x, y in points]
    flat: list[float] = list(placed[0])
    for (x0, y0), (x1, y1) in zip(placed, [*placed[1:], placed[0]], strict=True):
        flat += [x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3, x0 + (x1 - x0) * 2 / 3, y0 + (y1 - y0) * 2 / 3, x1, y1]
    return [(tuple(round(v, 3) for v in flat), colour)]


def _rounded(x: float, y: float, w: float, h: float, r: float) -> Path:
    k = r * (1.0 - brush.KAPPA)
    return (
        (x + r, y),
        (x + w - r, y),
        (x + w - k, y, x + w, y + k, x + w, y + r),
        (x + w, y + h - r),
        (x + w, y + h - k, x + w - k, y + h, x + w - r, y + h),
        (x + r, y + h),
        (x + k, y + h, x, y + h - k, x, y + h - r),
        (x, y + r),
        (x, y + k, x + k, y, x + r, y),
    )


# -- the head ----------------------------------------------------------------------------------------------------------
HEAD: Path = (
    (180.0, 189.0),
    (208.0, 161.0, 356.0, 150.0, 402.0, 187.0),
    (442.0, 220.0, 459.0, 281.0, 449.0, 349.0),
    (447.0, 403.0, 413.0, 443.0, 345.0, 457.0),
    (240.0, 452.0),
    (170.0, 436.0, 140.0, 392.0, 143.0, 333.0),
    (143.0, 277.0, 147.0, 225.0, 180.0, 189.0),
)
MUZZLE: Path = (
    (169.0, 306.0),
    (205.0, 289.0, 279.0, 294.0, 318.0, 307.0),
    (363.0, 315.0, 400.0, 335.0, 409.0, 374.0),
    (420.0, 415.0, 383.0, 439.0, 319.0, 443.0),
    (245.0, 441.0),
    (185.0, 437.0, 146.0, 412.0, 147.0, 373.0),
    (146.0, 343.0, 152.0, 321.0, 169.0, 306.0),
)
_MUZZLE_TOP: Path = (MUZZLE[0], MUZZLE[1], MUZZLE[2])
_TUFTS: Path = (
    (238.0, 176.0),
    (248.0, 156.0),
    (264.0, 170.0),
    (278.0, 148.0),
    (291.0, 168.0),
    (309.0, 156.0),
    (318.0, 173.0),
)
_EARS = ((177.0, 193.0, -13.0), (403.0, 187.0, 13.0))
_GLASSES: tuple[Path, Path] = (
    ((173.0, 313.0), (205.0, 328.0, 237.0, 312.0)),
    ((336.0, 312.0), (368.0, 327.0, 400.0, 312.0)),
)
_BRIDGE: Path = ((238.0, 311.0), (285.0, 302.0, 335.0, 311.0))


def _head_ramp() -> Ramp:
    return _ramp("fur", FUR, FUR_FLAT, _shape(HEAD), 0.8)


def _snout_ramp() -> Ramp:
    return _ramp("snout", SNOUT, SNOUT_FLAT, _shape(MUZZLE))


@cache
def skull_layers() -> tuple[Layer, ...]:
    """His ears and head, without the muzzle."""
    out: list[Layer] = [_shadow(HEAD)]
    for x, y, tilt in _EARS:
        place = _moved(x, y, tilt)
        out += [
            _oval(0.0, 0.0, 42.0, 47.0, EAR, place, tilt),
            _oval(-2.0, -5.0, 28.0, 31.0, "#C68D61", place, tilt),
            _oval(-2.0, -8.0, 16.0, 20.0, "#8C5B43", place, tilt),
        ]
    out += [(_shape(HEAD), _head_ramp()), _edge(HEAD, HEAD_LINE, 3.0)]
    out.append(_line(((179.0, 220.0), (266.0, 177.0, 389.0, 208.0)), "#F2C5948C", 5.0))
    out.append((_shape(_TUFTS), "#D39A66"))
    for x, y in ((155.0, 315.0), (160.0, 329.0), (435.0, 311.0), (430.0, 326.0)):
        out.append(_line(((x, y), (x + 5.0, y + 8.0)), "#B68052", 2.0))
    return tuple(out)


@cache
def _muzzle_layers() -> tuple[Layer, ...]:
    """His muzzle, in the face group, with what lies on it and does not change."""
    out: list[Layer] = [_shadow(MUZZLE), (_shape(MUZZLE), _snout_ramp()), _edge(MUZZLE, MUZZLE_LINE, 2.0)]
    out.append(_line(((168.0, 343.0), (230.0, 319.0, 302.0, 338.0)), "#F3D1A099", 4.0))
    out += [_oval(171.0, 384.0, 20.0, 11.0, "#D18B66A6"), _oval(384.0, 384.0, 15.0, 10.0, "#D18B668C")]
    out += [_oval(199.0, 353.0, 8.0, 5.0, "#704D3B", tilt=-13.0), _oval(275.0, 355.0, 7.0, 4.5, "#704D3B", tilt=11.0)]
    for x, y in ((173.0, 365.0), (186.0, 375.0), (286.0, 378.0), (299.0, 368.0)):
        out.append(_oval(x, y, 1.6, 1.7, "#A77451"))
    out.append(_line(_BRIDGE, RIM, 2.2))
    return tuple(out)


# -- the body ----------------------------------------------------------------------------------------------------------
_BLAZER: Path = (
    (215.0, 416.0),
    (149.0, 446.0, 145.0, 540.0),
    (146.0, 690.0),
    (147.0, 732.0, 203.0, 739.0),
    (405.0, 739.0),
    (454.0, 728.0, 455.0, 685.0),
    (453.0, 526.0),
    (450.0, 449.0, 382.0, 418.0),
)
_BLAZER_TOP: tuple[Point, ...] = tuple(_at(x, y) for x, y in ((215.0, 416.0), (298.0, 416.0), (382.0, 418.0)))
_BLAZER_PARTS: tuple[tuple[Path, str], ...] = (
    (((267.0, 418.0), (328.0, 418.0), (365.0, 681.0), (300.0, 705.0, 237.0, 682.0)), SHIRT),
    (((259.0, 428.0), (291.0, 466.0), (267.0, 514.0), (231.0, 453.0)), "#FFFFFF"),
    (((338.0, 427.0), (306.0, 466.0), (334.0, 516.0), (365.0, 455.0)), "#CCD9F0"),
    (((291.0, 461.0), (306.0, 461.0), (320.0, 482.0), (301.0, 501.0), (282.0, 481.0)), "#EE3D32"),
    (((291.0, 493.0), (311.0, 493.0), (333.0, 638.0), (302.0, 667.0), (276.0, 637.0)), "#BA2528"),
)
_LAPELS: tuple[tuple[Path, str], ...] = (
    (
        (
            (230.0, 422.0),
            (266.0, 493.0),
            (235.0, 520.0),
            (263.0, 544.0),
            (218.0, 688.0),
            (190.0, 670.0),
            (202.0, 448.0),
        ),
        "#315DE0",
    ),
    (
        (
            (370.0, 420.0),
            (335.0, 493.0),
            (365.0, 521.0),
            (339.0, 547.0),
            (380.0, 686.0),
            (407.0, 670.0),
            (394.0, 446.0),
        ),
        "#1A3690",
    ),
)
_POCKET: Path = ((363.0, 559.0), (372.0, 544.0), (380.0, 558.0), (392.0, 548.0), (399.0, 559.0))


@cache
def _blazer_layers() -> tuple[Layer, ...]:
    shape = _shape(_BLAZER)
    out: list[Layer] = [
        _shadow(_BLAZER),
        (shape, _ramp("jacket", JACKET, JACKET_FLAT, shape)),
        _edge(_BLAZER, "#143348", 3.0),
    ]
    out += [(_shape(path), colour) for path, colour in _BLAZER_PARTS]
    out.append(_line(((299.0, 505.0), (311.0, 620.0)), "#FF8570", 4.0))
    out += [(_shape(path), colour) for path, colour in _LAPELS]
    out.append(_line(((232.0, 431.0), (258.0, 490.0), (229.0, 517.0)), "#6387E7", 2.0))
    out.append(_line(((365.0, 434.0), (344.0, 491.0), (370.0, 516.0)), "#6387E7", 2.0))
    out.append((_shape(_rounded(354.0, 559.0, 54.0, 9.0, 3.0)), "#142E43"))
    out.append((_shape(_POCKET), "#EDB85F"))
    out.append(_oval(304.0, 694.0, 5.0, 5.0, "#D7B475"))
    return tuple(out)


def _leg(x: float) -> list[Layer]:
    trouser: Path = ((x, 700.0), (x - 9.0, 776.0, x + 1.0, 844.0), (x + 79.0, 844.0), (x + 69.0, 700.0))
    foot: Path = (
        (x + 3.0, 814.0),
        (x - 19.0, 838.0, x - 18.0, 876.0, x + 10.0, 881.0),
        (x + 84.0, 880.0),
        (x + 101.0, 862.0, x + 80.0, 841.0),
        (x + 67.0, 820.0),
    )
    out: list[Layer] = [(_shape(trouser), "#101F49"), *_furred(foot, PAW_LINE)]
    out += [_line(((x + dx, 858.0), (x + dx, 875.0)), "#9F6D48", 3.0) for dx in (25.0, 46.0, 66.0)]
    out.append(_line(((x + 7.0, 822.0), (x + 45.0, 831.0, x + 72.0, 822.0)), "#3654A0", 4.0))
    return out


@cache
def trunk_layers() -> tuple[Layer, ...]:
    """What stays on his body whatever his arms do: legs, feet and the blazer."""
    return (*_leg(218.0), *_leg(328.0), *_blazer_layers())


# -- hands -------------------------------------------------------------------------------------------------------------
_OPEN: Path = (
    (-22.0, 18.0),
    (-30.0, 4.0, -25.0, -9.0),
    (-31.0, -26.0, -22.0, -29.0),
    (-14.0, -30.0, -10.0, -14.0),
    (-11.0, -35.0),
    (-9.0, -45.0, -2.0, -40.0),
    (4.0, -17.0),
    (9.0, -38.0),
    (13.0, -47.0, 20.0, -38.0),
    (17.0, -13.0),
    (24.0, -32.0, 31.0, -27.0),
    (38.0, -21.0, 28.0, -1.0),
    (42.0, -7.0, 44.0, 1.0),
    (45.0, 10.0, 28.0, 20.0),
    (12.0, 38.0, -3.0, 31.0),
)
_OPEN_LINES: tuple[Path, ...] = (
    ((-13.0, 13.0), (-2.0, 4.0, 12.0, 13.0)),
    ((6.0, -9.0), (4.0, 5.0)),
    ((17.0, -7.0), (14.0, 6.0)),
)
_BACK_LINES = _OPEN_LINES[1:]  # the crease is the palm's
_FIST: Path = (
    (-20.0, 13.0),
    (-29.0, -1.0, -24.0, -15.0),
    (-22.0, -25.0, -13.0, -20.0),
    (-11.0, -28.0, -1.0, -23.0),
    (4.0, -29.0, 11.0, -22.0),
    (22.0, -25.0, 25.0, -13.0),
    (25.0, 9.0),
    (18.0, 27.0, 0.0, 27.0),
    (-14.0, 26.0, -20.0, 13.0),
)
_FIST_LINES: tuple[Path, ...] = (
    ((-12.0, -16.0), (-10.0, 0.0)),
    ((0.0, -20.0), (1.0, -3.0)),
    ((12.0, -19.0), (12.0, -2.0)),
    ((-22.0, 4.0), (-8.0, -7.0, 4.0, 5.0)),
)


_WRIST_X = 3.0  # where a drawn hand meets its cuff, across the hand: a mirrored hand stays on the cuff it had


class Arm(enum.Enum):
    """The arm a hand is on, by the side of the frame it leaves from. His right arm is on the frame's left. The value
    is the arm's place in :attr:`Gesture.sleeves`."""

    LEFT = 0
    RIGHT = 1


class Facing(enum.Enum):
    """What the camera sees of a hand."""

    PALM = "palm"  # raised and shown: the crease shows, and with the fingers up the thumb is on the inside
    BACK = "back"  # pressed to something, or hanging: no crease, and with the fingers up the thumb is on the outside


# The arm each drawing is of, palm to the camera: the open hand has its thumb on the +x side, inward on the frame's
# left, and the fist has it on the -x side, inward on the frame's right.
DRAWN_FOR: Mapping[str, Arm] = MappingProxyType({"open": Arm.LEFT, "fist": Arm.RIGHT})


@dataclass(frozen=True)
class Paw:
    """One of his pair of hands: its arm, its wrist at ``(x, y)`` of his drawing, its fingers up at angle 0. On the
    other arm, or turned over, a hand is the same drawing mirrored, and :attr:`mirrored` works that out, so no caller
    can draw a hand of the wrong side. Version 1 reads only where the paw is and draws one hand on both arms."""

    arm: Arm
    x: float
    y: float
    angle: float = 0.0
    fist: bool = False
    scale: float = 1.0
    facing: Facing = Facing.PALM

    def __post_init__(self) -> None:
        if not isinstance(self.arm, Arm):
            raise ToonDataError(f"a hand is on an Arm, not {self.arm!r}")
        if not isinstance(self.facing, Facing):
            raise ToonDataError(f"a hand shows a Facing, not {self.facing!r}")
        if self.fist and self.facing is Facing.BACK:
            raise ToonDataError("a fist is drawn from its fingers: there is no back of a fist to show")

    @property
    def mirrored(self) -> bool:
        """Whether the drawing is reflected: a hand on the other arm is, and a hand's back is its palm's mirror."""
        other_arm = self.arm is not DRAWN_FOR["fist" if self.fist else "open"]
        return other_arm != (self.facing is Facing.BACK)


def _hand(x: float, y: float, angle: float = 0.0, fist: bool = False, scale: float = 1.0) -> list[Layer]:
    """A tiny paw at ``(x, y)`` of his drawing, its fingers up at angle 0: version 1's one hand."""
    place = _moved(x, y, angle, scale)
    out = _furred(_FIST if fist else _OPEN, PAW_LINE, place)
    return out + [_line(path, PAW_LINE, 2.0, place) for path in (_FIST_LINES if fist else _OPEN_LINES)]


def _placing(paw: Paw, number: int) -> Place:
    """What places the drawing of ``paw`` in version ``number``."""
    flip = _WRIST_X if number >= 2 and paw.mirrored else None
    return _moved(paw.x, paw.y, paw.angle, paw.scale, flip)


def _paw_layers(paw: Paw, number: int) -> list[Layer]:
    """``paw`` as version ``number`` draws it: from version 2 the hand of its arm, a back showing no crease."""
    if number < 2:
        return _hand(paw.x, paw.y, paw.angle, paw.fist, paw.scale)
    place = _placing(paw, number)
    lines = _FIST_LINES if paw.fist else _BACK_LINES if paw.facing is Facing.BACK else _OPEN_LINES
    fill, _ = _furred(_FIST if paw.fist else _OPEN, PAW_LINE, place)
    ink = _ringed(_FIST if paw.fist else _OPEN, PAW_LINE, 2.0, place)
    return [fill, ink, *(_line(path, PAW_LINE, 2.0, place) for path in lines)]


def _nearest(paw: Paw, sleeve: Path) -> float:
    """How far the wrist of ``paw`` is from ``sleeve``, in his drawing's pixels."""
    return min(math.hypot(x - paw.x, y - paw.y) for x, y in _samples(sleeve))


# -- the gestures ------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Gesture:
    """A pose of his arms. ``sleeves`` go over him in ``under`` order, the frame's left arm then the frame's right, then
    ``held`` (what he holds) under the paws; ``hands`` are his :class:`Paw`, and ``paws`` paws drawn whole, each with a
    shape of its own and no thumb to follow a side. A hand must be at the end of its own arm's sleeve: one on the other
    arm, or two on one, is refused here, when the gesture is built."""

    name: str
    title: str
    sleeves: tuple[Path, ...]
    hands: tuple[Paw, ...] = ()
    paws: tuple[Path, ...] = ()
    held: bool = False

    def __post_init__(self) -> None:
        if len(self.sleeves) != 2 or not self.sleeves[0][0][0] < PIVOT_X < self.sleeves[1][0][0]:
            raise ToonDataError(f"{self.name}: its two sleeves run from the frame's left arm to its right")
        for paw in self.hands:
            if not isinstance(paw, Paw):
                raise ToonDataError(f"{self.name}: a hand is a Paw, not {paw!r}")
            own, other = self.sleeves[paw.arm.value], self.sleeves[1 - paw.arm.value]
            if _nearest(paw, other) < _nearest(paw, own):
                raise ToonDataError(f"{self.name}: the hand at ({paw.x}, {paw.y}) is on the other arm, not {paw.arm}")
        if len({paw.arm for paw in self.hands}) != len(self.hands):
            raise ToonDataError(f"{self.name}: two hands on one arm")


_READY_SLEEVES: tuple[Path, Path] = (
    (
        (183.0, 444.0),
        (128.0, 460.0, 113.0, 518.0),
        (103.0, 678.0),
        (107.0, 704.0, 142.0, 701.0),
        (179.0, 676.0),
        (192.0, 530.0),
    ),
    (
        (421.0, 447.0),
        (473.0, 472.0, 480.0, 532.0),
        (487.0, 673.0),
        (477.0, 700.0, 444.0, 697.0),
        (411.0, 669.0),
        (410.0, 531.0),
    ),
)
_READY_PAWS: tuple[Path, Path] = (
    ((112.0, 673.0), (97.0, 697.0, 110.0, 719.0), (130.0, 742.0, 154.0, 725.0), (171.0, 704.0), (164.0, 684.0)),
    ((437.0, 680.0), (427.0, 704.0, 444.0, 725.0), (465.0, 741.0, 487.0, 718.0), (491.0, 690.0), (476.0, 675.0)),
)
_TUCKED = Paw(Arm.LEFT, 133.0, 692.0, 180.0, scale=0.75, facing=Facing.BACK)  # hanging while the other does the work
GESTURES: dict[str, Gesture] = {
    gesture.name: gesture
    for gesture in (
        Gesture("ready", "Ready", _READY_SLEEVES, paws=_READY_PAWS),
        Gesture(
            "present",
            "Presenting",
            (
                (
                    (182.0, 448.0),
                    (130.0, 460.0, 117.0, 516.0),
                    (97.0, 664.0),
                    (117.0, 696.0, 157.0, 675.0),
                    (184.0, 535.0),
                ),
                (
                    (420.0, 449.0),
                    (457.0, 463.0, 466.0, 515.0),
                    (477.0, 555.0),
                    (537.0, 492.0),
                    (562.0, 522.0),
                    (492.0, 617.0),
                    (469.0, 639.0, 444.0, 613.0),
                    (410.0, 536.0),
                ),
            ),
            hands=(
                Paw(Arm.RIGHT, 550.0, 490.0, -16.0),
                Paw(Arm.LEFT, 125.0, 696.0, 180.0, scale=0.75, facing=Facing.BACK),
            ),
        ),
        Gesture(
            "empathy",
            "Hand to heart",
            (
                (
                    (180.0, 449.0),
                    (136.0, 452.0, 119.0, 511.0),
                    (120.0, 652.0),
                    (141.0, 681.0, 171.0, 650.0),
                    (186.0, 533.0),
                ),
                (
                    (421.0, 447.0),
                    (467.0, 462.0, 475.0, 530.0),
                    (464.0, 611.0),
                    (453.0, 638.0, 422.0, 617.0),
                    (312.0, 552.0),
                    (331.0, 516.0),
                    (425.0, 563.0),
                    (411.0, 522.0),
                ),
            ),
            hands=(
                Paw(Arm.RIGHT, 311.0, 530.0, -64.0, scale=0.84, facing=Facing.BACK),
                Paw(Arm.LEFT, 148.0, 674.0, 180.0, scale=0.72, facing=Facing.BACK),
            ),
        ),
        Gesture(
            "shrug",
            "The shrug",
            (
                (
                    (183.0, 449.0),
                    (151.0, 437.0, 135.0, 477.0),
                    (105.0, 541.0),
                    (58.0, 502.0),
                    (33.0, 538.0),
                    (112.0, 602.0),
                    (141.0, 618.0, 164.0, 589.0),
                    (201.0, 513.0),
                ),
                (
                    (418.0, 448.0),
                    (452.0, 438.0, 467.0, 475.0),
                    (502.0, 542.0),
                    (552.0, 503.0),
                    (577.0, 540.0),
                    (496.0, 605.0),
                    (468.0, 621.0, 446.0, 588.0),
                    (400.0, 515.0),
                ),
            ),
            hands=(Paw(Arm.LEFT, 38.0, 497.0, -67.0, scale=0.86), Paw(Arm.RIGHT, 573.0, 499.0, 67.0, scale=0.86)),
        ),
        Gesture(
            "folded",
            "Arms folded",
            (
                (
                    (180.0, 449.0),
                    (136.0, 462.0, 125.0, 520.0),
                    (131.0, 606.0),
                    (139.0, 641.0, 187.0, 636.0),
                    (372.0, 590.0),
                    (359.0, 547.0),
                    (184.0, 582.0),
                    (193.0, 525.0),
                ),
                (
                    (420.0, 449.0),
                    (468.0, 468.0, 474.0, 523.0),
                    (473.0, 610.0),
                    (460.0, 640.0, 418.0, 627.0),
                    (221.0, 588.0),
                    (228.0, 547.0),
                    (423.0, 574.0),
                    (407.0, 520.0),
                ),
            ),
            paws=(
                (
                    (352.0, 548.0),
                    (388.0, 526.0, 402.0, 541.0),
                    (410.0, 553.0, 397.0, 561.0),
                    (411.0, 567.0, 399.0, 580.0),
                    (369.0, 590.0),
                ),
                (
                    (229.0, 548.0),
                    (202.0, 533.0, 185.0, 548.0),
                    (177.0, 558.0, 194.0, 565.0),
                    (182.0, 577.0, 198.0, 587.0),
                    (222.0, 589.0),
                ),
            ),
        ),
        Gesture(
            "firm",
            "Firm objection",
            (
                (
                    (182.0, 448.0),
                    (130.0, 462.0, 115.0, 518.0),
                    (104.0, 672.0),
                    (125.0, 700.0, 161.0, 678.0),
                    (193.0, 531.0),
                ),
                (
                    (419.0, 446.0),
                    (453.0, 442.0, 469.0, 487.0),
                    (487.0, 535.0),
                    (516.0, 444.0),
                    (555.0, 456.0),
                    (528.0, 597.0),
                    (514.0, 629.0, 478.0, 611.0),
                    (414.0, 531.0),
                ),
            ),
            hands=(
                Paw(Arm.RIGHT, 536.0, 423.0, -5.0, fist=True, scale=1.03),
                Paw(Arm.LEFT, 130.0, 696.0, 180.0, scale=0.75, facing=Facing.BACK),
            ),
        ),
        Gesture(
            "panic",
            "Panic",
            (
                (
                    (180.0, 449.0),
                    (154.0, 438.0, 136.0, 468.0),
                    (106.0, 504.0),
                    (69.0, 371.0),
                    (29.0, 382.0),
                    (65.0, 563.0),
                    (80.0, 598.0, 112.0, 580.0),
                    (190.0, 517.0),
                ),
                (
                    (418.0, 449.0),
                    (448.0, 440.0, 467.0, 469.0),
                    (500.0, 506.0),
                    (535.0, 371.0),
                    (576.0, 383.0),
                    (538.0, 565.0),
                    (522.0, 600.0, 491.0, 582.0),
                    (411.0, 517.0),
                ),
            ),
            hands=(Paw(Arm.LEFT, 45.0, 346.0, -14.0, scale=1.05), Paw(Arm.RIGHT, 558.0, 347.0, 14.0, scale=1.05)),
        ),
        Gesture(
            "facepalm",
            "Facepalm",
            (
                (
                    (180.0, 450.0),
                    (136.0, 460.0, 116.0, 518.0),
                    (107.0, 668.0),
                    (132.0, 695.0, 160.0, 675.0),
                    (190.0, 531.0),
                ),
                (
                    (417.0, 449.0),
                    (460.0, 449.0, 478.0, 483.0),
                    (499.0, 531.0),
                    (506.0, 551.0, 482.0, 562.0),
                    (454.0, 558.0),
                    (434.0, 498.0, 386.0, 455.0),
                    (305.0, 320.0),
                    (344.0, 299.0),
                    (423.0, 420.0),
                ),
            ),
            hands=(Paw(Arm.RIGHT, 308.0, 284.0, -29.0, scale=1.2, facing=Facing.BACK), _TUCKED),
        ),
        Gesture(
            "tablet",
            "Reading",
            (
                (
                    (182.0, 449.0),
                    (140.0, 457.0, 121.0, 511.0),
                    (129.0, 621.0),
                    (143.0, 646.0, 181.0, 628.0),
                    (220.0, 586.0),
                    (194.0, 555.0),
                    (164.0, 582.0),
                    (195.0, 524.0),
                ),
                (
                    (418.0, 450.0),
                    (463.0, 461.0, 477.0, 516.0),
                    (469.0, 619.0),
                    (456.0, 645.0, 424.0, 626.0),
                    (386.0, 584.0),
                    (409.0, 555.0),
                    (442.0, 580.0),
                    (411.0, 524.0),
                ),
            ),
            paws=(
                (
                    (208.0, 569.0),
                    (188.0, 562.0, 186.0, 579.0),
                    (188.0, 603.0, 212.0, 610.0),
                    (228.0, 595.0),
                    (234.0, 584.0, 218.0, 582.0),
                    (224.0, 571.0),
                    (223.0, 565.0, 208.0, 569.0),
                ),
                (
                    (399.0, 565.0),
                    (421.0, 561.0, 421.0, 580.0),
                    (418.0, 601.0, 397.0, 607.0),
                    (382.0, 594.0),
                    (375.0, 582.0, 391.0, 579.0),
                    (386.0, 569.0),
                    (387.0, 560.0, 399.0, 565.0),
                ),
            ),
            held=True,
        ),
    )
}


def _tablet() -> list[Layer]:
    """The tablet he reads from, its screen blank but for the ruled lines."""
    place = _moved(201.0, 530.0, -3.0)
    out: list[Layer] = [
        (_shape(_rounded(0.0, 0.0, 200.0, 148.0, 12.0), place), "#101B35"),
        (_shape(_rounded(10.0, 10.0, 180.0, 124.0, 6.0), place), "#EBF2FF"),
        (_shape(_rounded(10.0, 10.0, 180.0, 31.0, 5.0), place), "#214FDB"),
    ]
    for y, end in ((59.0, 174.0), (77.0, 158.0), (95.0, 165.0)):
        out.append(_line(((24.0, y), (end, y)), "#7994C6", 4.0, place))
    out.append(_oval(100.0, 140.0, 3.0, 3.0, "#7182A4", place))
    return out


def _gesture_layers(gesture: Gesture, number: int = 1) -> tuple[list[Layer], list[Layer]]:
    """``(under, over)`` the head (:func:`srstudio.toon_cast._arms`) in version ``number``. Ready keeps its sleeves
    behind the blazer; every other gesture lies over him, head included, the way his drawing stacks it."""
    sleeves = [layer for path in gesture.sleeves for layer in _sleeve(path)]
    paws = [layer for path in gesture.paws for layer in _furred(path, PAW_LINE)]
    hands = [layer for paw in gesture.hands for layer in _paw_layers(paw, number)]
    if gesture.name == "ready":
        cuffs = [
            _line(((123.0, 647.0), (166.0, 654.0)), "#456AC4", 3.0),
            _line(((435.0, 651.0), (477.0, 645.0)), "#456AC4", 3.0),
        ]
        creases = [
            _line(((x, y), (x + 1.0, y + 10.0)), PAW_LINE, 3.0)
            for x, y in ((122.0, 712.0), (135.0, 718.0), (453.0, 716.0), (468.0, 716.0))
        ]
        return [*sleeves, *cuffs, *_blazer_layers()], [*paws, *creases]
    held = _tablet() if gesture.held else []
    return [], [*sleeves, *held, *hands, *paws]


# -- the mouths --------------------------------------------------------------------------------------------------------
_BIG_MOUTHS: dict[str, Path] = {
    "smile": ((257.0, 397.0), (291.0, 420.0, 327.0, 395.0), (317.0, 430.0, 286.0, 426.0), (265.0, 423.0, 257.0, 397.0)),
    "grin": ((250.0, 394.0), (290.0, 416.0, 333.0, 393.0), (323.0, 435.0, 287.0, 431.0), (260.0, 428.0, 250.0, 394.0)),
    "beam": ((248.0, 387.0), (288.0, 408.0, 335.0, 385.0), (330.0, 436.0, 291.0, 437.0), (257.0, 436.0, 248.0, 387.0)),
    "laugh": ((246.0, 384.0), (288.0, 397.0, 338.0, 382.0), (330.0, 440.0, 290.0, 441.0), (254.0, 438.0, 246.0, 384.0)),
    "cry": ((260.0, 423.0), (290.0, 387.0, 325.0, 422.0), (295.0, 408.0, 260.0, 423.0)),
    "shout": ((251.0, 397.0), (291.0, 377.0, 330.0, 397.0), (325.0, 426.0), (288.0, 443.0, 253.0, 424.0)),
    "fear": ((258.0, 418.0), (268.0, 388.0, 291.0, 396.0), (314.0, 389.0, 324.0, 420.0), (291.0, 430.0, 258.0, 418.0)),
    "scream": (
        (262.0, 397.0),
        (290.0, 380.0, 321.0, 398.0),
        (328.0, 438.0, 292.0, 442.0),
        (259.0, 441.0, 262.0, 397.0),
    ),
    "awkward": (
        (259.0, 405.0),
        (290.0, 393.0, 325.0, 410.0),
        (312.0, 426.0, 289.0, 420.0),
        (274.0, 418.0, 259.0, 405.0),
    ),
    "sneer": (
        (252.0, 405.0),
        (263.0, 381.0, 286.0, 397.0),
        (311.0, 410.0, 328.0, 403.0),
        (301.0, 430.0, 280.0, 409.0),
        (265.0, 403.0, 252.0, 405.0),
    ),
}
_ROUND_MOUTHS: dict[str, tuple[float, float]] = {
    "small-o": (9.0, 8.0),
    "o": (15.0, 18.0),
    "gasp": (22.0, 29.0),
    "yawn": (18.0, 21.0),
}
_LINE_MOUTHS: dict[str, tuple[Path, ...]] = {
    "neutral": (((265.0, 407.0), (291.0, 407.0, 320.0, 407.0)),),
    "soft-flat": (((269.0, 407.0), (291.0, 405.0, 316.0, 408.0)),),
    "softsmile": (((264.0, 401.0), (292.0, 420.0, 322.0, 401.0)),),
    "smallsmile": (((271.0, 403.0), (292.0, 415.0, 315.0, 401.0)),),
    "proud": (((262.0, 402.0), (292.0, 421.0, 327.0, 396.0)),),
    "asym-smile": (((263.0, 411.0), (291.0, 414.0, 326.0, 392.0)), ((326.0, 389.0), (327.0, 398.0))),
    "pursed": (((283.0, 406.0), (295.0, 399.0, 308.0, 405.0)), ((285.0, 412.0), (296.0, 414.0, 307.0, 410.0))),
    "crooked": (((262.0, 410.0), (279.0, 397.0, 291.0, 408.0), (306.0, 419.0, 323.0, 409.0)),),
    "side-flat": (((269.0, 409.0), (325.0, 405.0)),),
    "frown": (((263.0, 418.0), (291.0, 394.0, 322.0, 418.0)),),
    "flat-frown": (((259.0, 416.0), (289.0, 406.0, 323.0, 416.0)),),
    "tight": (((259.0, 405.0), (322.0, 405.0)), ((268.0, 411.0), (314.0, 411.0))),
    "scowl": (((254.0, 419.0), (289.0, 391.0, 328.0, 419.0)),),
    "sneer-small": (((258.0, 400.0), (271.0, 389.0, 284.0, 400.0), (318.0, 409.0)),),
    "wavy": (
        ((259.0, 413.0), (268.0, 402.0, 278.0, 413.0), (288.0, 424.0, 298.0, 413.0), (309.0, 402.0, 321.0, 414.0)),
    ),
}
MOUTH_KINDS: tuple[str, ...] = (*_LINE_MOUTHS, *_BIG_MOUTHS, *_ROUND_MOUTHS)
_DIMPLED = frozenset({"softsmile", "proud", "smallsmile"})
_TWO_TEETH = frozenset({"smile", "grin", "beam", "laugh", "sneer"})
_TOOTH_ROW = frozenset({"shout", "fear", "awkward"})
_TONGUED = frozenset({"beam", "laugh", "scream", "shout"})
_TOOTH_LINE = "#CABAA5"
_TEETH: tuple[Path, Path] = (
    ((275.0, 396.0), (291.0, 401.0), (291.0, 419.0), (277.0, 417.0)),
    ((294.0, 401.0), (309.0, 398.0), (307.0, 418.0), (294.0, 420.0)),
)
_UPPER_ROW: Path = ((249.0, 392.0), (291.0, 399.0, 335.0, 392.0), (334.0, 407.0), (288.0, 415.0, 251.0, 403.0))
_LOWER_ROW: Path = ((249.0, 430.0), (289.0, 420.0, 333.0, 429.0), (333.0, 442.0), (249.0, 442.0))
SHARED_MOUTHS: dict[str, str] = {
    "flat": "neutral",
    "open": "beam",
    "round": "o",
    "drop": "gasp",
    "wave": "wavy",
    "smirk": "asym-smile",
    "grimace": "fear",
    "tongue": "laugh",
    "kiss": "pursed",
    "puff": "tight",
}


def _inside(mouth: Sequence[Point], path: Path, colour: str) -> list[Layer]:
    return _patch(_meet(mouth, _samples(path)), colour)


def _tooth_line(mouth: Sequence[Point], x: float) -> Layer:
    """The line between two teeth at ``x``, cut to the mouth: a lip lower than the row would leave it standing above."""
    span = _span(mouth, x)
    if span is None:
        raise ToonDataError(f"a tooth line at {x} misses the mouth")
    return _line(((x, max(span[0], 394.0)), (x, min(span[1], 408.0))), _TOOTH_LINE, 1.4)


def _mouth_layers(kind: str) -> list[Layer]:
    if kind in _BIG_MOUTHS:
        path = _BIG_MOUTHS[kind]
        mouth = _samples(path)
        out: list[Layer] = _patch(mouth, THROAT)
        if kind in _TOOTH_ROW:
            out += _inside(mouth, _UPPER_ROW, TOOTH)
            if kind == "shout":
                out += _inside(mouth, _LOWER_ROW, TOOTH)
            out += [_tooth_line(mouth, x) for x in (274.0, 293.0, 312.0)]
        elif kind in _TWO_TEETH:
            out += [layer for tooth in _TEETH for layer in _inside(mouth, tooth, TOOTH)]
        if kind in _TONGUED:
            out += _patch(_meet(mouth, _ring(294.0, 435.0, 22.0, 10.0)), TONGUE)
        return out
    if kind in _ROUND_MOUTHS:
        rx, ry = _ROUND_MOUTHS[kind]
        out = [_oval(294.0, 408.0, rx, ry, THROAT)]
        return out + ([_oval(294.0, 416.0, rx * 0.6, ry * 0.3, TONGUE)] if ry > 10.0 else [])
    if kind in _LINE_MOUTHS:
        out = [_line(path, THROAT, 4.5) for path in _LINE_MOUTHS[kind]]
        if kind in _DIMPLED:
            out += [_oval(259.0, 399.0, 2.0, 2.0, THROAT), _oval(326.0, 399.0, 2.0, 2.0, THROAT)]
        return out
    raise ToonDataError(f"Bento has no mouth {kind!r}: his are {MOUTH_KINDS}, and the shared kinds")


_OPEN_MOUTH: Path = (
    (254.0, 392.0),
    (290.0, 402.0, 330.0, 391.0),
    (328.0, 432.0, 291.0, 433.0),
    (258.0, 433.0, 254.0, 392.0),
)
_BITE: Path = ((256.0, 400.0), (291.0, 412.0, 328.0, 399.0), (318.0, 417.0, 291.0, 417.0), (266.0, 417.0, 256.0, 400.0))


def _viseme_layers(kind: str) -> list[Layer]:
    """A speaking mouth, the two front teeth showing on ``open`` and on the bite of ``teeth``."""
    if kind == "open":
        mouth = _samples(_OPEN_MOUTH)
        teeth = [layer for tooth in _TEETH for layer in _inside(mouth, tooth, TOOTH)]
        return [*_patch(mouth, THROAT), *_patch(_meet(mouth, _ring(292.0, 432.0, 20.0, 9.0)), TONGUE), *teeth]
    if kind == "round":
        return _mouth_layers("o")
    if kind == "teeth":
        mouth = _samples(_BITE)
        return [*_patch(mouth, THROAT), *[layer for tooth in _TEETH for layer in _inside(mouth, tooth, TOOTH)]]
    return _mouth_layers("neutral")  # closed: what a track holds where no pose's own mouth is drawn


# -- the moods ---------------------------------------------------------------------------------------------------------
Pair = tuple[float, float]


@dataclass(frozen=True)
class Mood:
    """One of his expressions. ``gaze`` runs -1 to 1 each way; ``lids`` is how much of each eye its upper lid covers
    and ``bottom`` how much the lower lids rise; ``brows`` moves each brow down (his drawing's pixels) and ``angles``
    turns it (degrees clockwise); ``tilt`` turns the head; ``pupil`` scales the pupil. ``shut`` closes the eyes,
    ``happy`` arched and ``soft`` hanging; ``wide`` opens them taller. ``marks`` come from :data:`MARKS`. ``gesture`` is
    the arms that go with it."""

    name: str
    use: str
    mouth: str
    gesture: str
    gaze: Pair = (0.0, 0.0)
    lids: Pair = (0.0, 0.0)
    bottom: float = 0.0
    brows: Pair = (0.0, 0.0)
    angles: Pair = (0.0, 0.0)
    tilt: float = 0.0
    pupil: float = 1.0
    shut: str = ""
    wide: bool = False
    marks: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.mouth not in MOUTH_KINDS:
            raise ToonDataError(f"mood {self.name}: no mouth {self.mouth!r}")
        if self.gesture not in GESTURES:
            raise ToonDataError(f"mood {self.name}: no gesture {self.gesture!r}")
        if any(abs(v) > 1.0 for v in self.gaze):
            raise ToonDataError(f"mood {self.name}: a gaze runs -1 to 1, got {self.gaze!r}")
        if any(not 0.0 <= v <= 1.0 for v in self.lids):
            raise ToonDataError(f"mood {self.name}: lids cover 0 to 1 of the eye, got {self.lids!r}")
        if not 0.0 <= self.bottom <= 1.0:
            raise ToonDataError(f"mood {self.name}: a bottom lid covers 0 to 1 of the eye, got {self.bottom!r}")
        if not 0.0 < self.pupil <= 1.5:
            raise ToonDataError(f"mood {self.name}: a pupil scales between 0 and 1.5, got {self.pupil!r}")
        if abs(self.tilt) > TILT_REACH:
            raise ToonDataError(f"mood {self.name}: a tilt is at most {TILT_REACH} degrees, got {self.tilt!r}")
        if self.shut not in SHUT_KINDS:
            raise ToonDataError(f"mood {self.name}: shut is one of {SHUT_KINDS}, got {self.shut!r}")
        if self.marks - MARKS:
            raise ToonDataError(f"mood {self.name}: no mark {sorted(self.marks - MARKS)}")


def _marks(*names: str) -> frozenset[str]:
    return frozenset(names)


MOODS: dict[str, Mood] = {
    mood.name: mood
    for mood in (
        Mood("neutral", "Fact delivery without emotional colouring.", "neutral", "tablet", lids=(0.12, 0.12)),
        Mood("welcoming", "Opening the programme and greeting viewers.", "smile", "present", brows=(-4, -8), tilt=-2),
        Mood("happy", "A positive outcome or a pleasant update.", "grin", "present", bottom=0.13, brows=(-6, -6)),
        Mood("delighted", "An unexpectedly excellent result.", "beam", "shrug", bottom=0.27, brows=(-13, -13), tilt=-3),
        Mood(
            "laughing",
            "A full comic release after the punchline.",
            "laugh",
            "present",
            shut="happy",
            brows=(-9, -9),
            tilt=-6,
            marks=_marks("cheeks"),
        ),
        Mood(
            "proud", "Celebrating someone's achievement.", "proud", "folded", lids=(0.20, 0.20), brows=(-7, -7), tilt=-3
        ),
        Mood(
            "relieved",
            "Tension releases after a problem is resolved.",
            "softsmile",
            "empathy",
            shut="soft",
            brows=(-3, -3),
            tilt=3,
        ),
        Mood(
            "grateful",
            "Thanking a guest, colleague or audience.",
            "softsmile",
            "empathy",
            bottom=0.18,
            brows=(-5, -5),
            angles=(-9, 9),
            tilt=5,
        ),
        Mood(
            "affectionate",
            "A tender human-interest beat.",
            "smile",
            "empathy",
            lids=(0.12, 0.12),
            bottom=0.18,
            brows=(-10, -10),
            angles=(-10, 10),
            tilt=-6,
            pupil=1.17,
            marks=_marks("cheeks"),
        ),
        Mood(
            "hopeful",
            "Looking toward a possible positive outcome.",
            "smallsmile",
            "ready",
            gaze=(0.15, -0.8),
            brows=(-13, -13),
            angles=(-6, 6),
            pupil=1.12,
        ),
        Mood("excited", "An energetic announcement.", "beam", "panic", brows=(-21, -21), tilt=4, wide=True, pupil=1.10),
        Mood(
            "confident",
            "Explaining a verified finding with assurance.",
            "asym-smile",
            "present",
            lids=(0.23, 0.13),
            brows=(-1, -8),
            tilt=-3,
        ),
        Mood(
            "curious",
            "Introducing a question worth investigating.",
            "small-o",
            "present",
            gaze=(0.65, -0.25),
            brows=(-3, -20),
            tilt=-7,
        ),
        Mood(
            "thinking",
            "Considering a cause or connecting clues.",
            "pursed",
            "ready",
            gaze=(-0.65, -0.75),
            lids=(0.18, 0.13),
            brows=(-13, -1),
            tilt=5,
        ),
        Mood(
            "confused",
            "Something does not fit the explanation.",
            "crooked",
            "shrug",
            brows=(-19, 3),
            angles=(0, -8),
            lids=(0.0, 0.25),
            tilt=7,
        ),
        Mood(
            "skeptical",
            "A claim needs stronger evidence.",
            "side-flat",
            "folded",
            gaze=(0.8, 0.0),
            lids=(0.42, 0.08),
            brows=(7, -21),
            angles=(8, 0),
            tilt=-4,
        ),
        Mood("surprised", "A sudden unexpected update.", "o", "shrug", brows=(-22, -22), wide=True, pupil=0.88),
        Mood(
            "astonished",
            "A revelation exceeds every expectation.",
            "gasp",
            "panic",
            brows=(-29, -29),
            wide=True,
            pupil=0.67,
            tilt=-5,
        ),
        Mood(
            "concerned",
            "A developing situation needs attention.",
            "frown",
            "empathy",
            brows=(-1, -1),
            angles=(-15, 15),
            lids=(0.05, 0.05),
        ),
        Mood(
            "empathetic",
            "Acknowledging another person's difficulty.",
            "soft-flat",
            "empathy",
            brows=(-4, -4),
            angles=(-16, 16),
            lids=(0.18, 0.18),
            tilt=5,
        ),
        Mood(
            "sad",
            "Quiet disappointment or loss.",
            "frown",
            "ready",
            gaze=(0.0, 0.7),
            brows=(2, 2),
            angles=(-19, 19),
            lids=(0.20, 0.20),
            tilt=3,
        ),
        Mood(
            "grieving",
            "An explicitly sorrowful emotional beat.",
            "cry",
            "empathy",
            gaze=(0.0, 0.45),
            angles=(-24, 24),
            lids=(0.43, 0.43),
            tilt=6,
            marks=_marks("tears"),
        ),
        Mood(
            "disappointed",
            "An expected result fails to materialise.",
            "flat-frown",
            "ready",
            gaze=(-0.2, 0.4),
            brows=(7, 7),
            angles=(-6, 6),
            lids=(0.52, 0.52),
            tilt=-4,
        ),
        Mood(
            "embarrassed",
            "A harmless on-air slip is noticed.",
            "awkward",
            "facepalm",
            gaze=(0.7, 0.4),
            brows=(-9, 3),
            lids=(0.08, 0.26),
            tilt=-7,
            marks=_marks("cheeks"),
        ),
        Mood(
            "irritated",
            "A small recurring annoyance.",
            "tight",
            "folded",
            gaze=(-0.6, 0.0),
            brows=(6, 6),
            angles=(12, -12),
            lids=(0.35, 0.35),
            tilt=3,
        ),
        Mood(
            "angry",
            "A firm objection or an unfair situation.",
            "scowl",
            "firm",
            brows=(7, 7),
            angles=(24, -24),
            lids=(0.17, 0.17),
        ),
        Mood(
            "furious",
            "The comic breaking point.",
            "shout",
            "firm",
            brows=(7, 7),
            angles=(31, -31),
            lids=(0.10, 0.10),
            pupil=0.82,
            tilt=-4,
            marks=_marks("flush"),
        ),
        Mood(
            "disgusted",
            "An unpleasant discovery.",
            "sneer",
            "present",
            brows=(4, 4),
            angles=(12, -12),
            lids=(0.40, 0.24),
            tilt=6,
            marks=_marks("wrinkle"),
        ),
        Mood(
            "contemptuous",
            "A character dismisses an absurd excuse.",
            "sneer-small",
            "folded",
            gaze=(-0.55, 0.0),
            brows=(-15, 4),
            lids=(0.20, 0.57),
            tilt=-5,
        ),
        Mood(
            "sarcastic",
            "Dry irony about an everyday absurdity.",
            "asym-smile",
            "folded",
            gaze=(0.7, -0.1),
            brows=(3, -13),
            lids=(0.48, 0.24),
            tilt=6,
        ),
        Mood(
            "deadpan",
            "Delivering an absurd line with a straight face.",
            "neutral",
            "tablet",
            brows=(3, 3),
            lids=(0.50, 0.50),
        ),
        Mood(
            "bored",
            "Waiting through a needlessly long briefing.",
            "side-flat",
            "ready",
            gaze=(0.55, 0.35),
            brows=(8, 8),
            lids=(0.65, 0.65),
            tilt=7,
        ),
        Mood(
            "tired",
            "The late shift catches up with the anchor.",
            "yawn",
            "ready",
            gaze=(0.0, 0.35),
            brows=(6, 6),
            lids=(0.72, 0.64),
            tilt=-5,
            marks=_marks("bags"),
        ),
        Mood(
            "anxious",
            "Waiting for a difficult live update.",
            "wavy",
            "ready",
            gaze=(-0.65, 0.05),
            brows=(-6, -6),
            angles=(-14, 14),
            marks=_marks("sweat"),
        ),
        Mood(
            "frightened",
            "A threatening surprise.",
            "fear",
            "shrug",
            brows=(-17, -17),
            angles=(-12, 12),
            pupil=0.65,
            wide=True,
            tilt=4,
        ),
        Mood(
            "panicked",
            "Comic on-air catastrophe.",
            "scream",
            "panic",
            brows=(-23, -23),
            angles=(-16, 16),
            pupil=0.48,
            wide=True,
            tilt=-6,
            marks=_marks("sweat"),
        ),
    )
}


def mood(name: str) -> Mood:
    """The mood ``name``, or a :class:`srstudio.toon.ToonDataError` naming what was asked for."""
    try:
        return MOODS[name]
    except KeyError:
        raise ToonDataError(f"Bento has no mood {name!r}: his are {tuple(MOODS)}") from None


@dataclass(frozen=True)
class EyeState:
    """Where the eyes are, over any mood: ``gaze`` in its place (``None`` keeps the mood's), ``blink`` how much each
    eye is shut (``None`` keeps the mood's lids), ``near`` turned in toward his nose."""

    name: str
    gaze: Pair | None = (0.0, 0.0)
    blink: Pair | None = None
    near: bool = False


EYE_STATES: dict[str, EyeState] = {
    state.name: state
    for state in (
        EyeState("camera"),
        EyeState("left", (-1.0, 0.0)),
        EyeState("right", (1.0, 0.0)),
        EyeState("up", (0.0, -1.0)),
        EyeState("down", (0.0, 1.0)),
        EyeState("up-left", (-0.75, -0.75)),
        EyeState("up-right", (0.75, -0.75)),
        EyeState("near", near=True),
        EyeState("half-blink", blink=(0.5, 0.5)),
        EyeState("closed", blink=(1.0, 1.0)),
        EyeState("left-wink", blink=(1.0, 0.0)),
        EyeState("right-wink", blink=(0.0, 1.0)),
    )
}
SHARED_EYES: dict[str, str] = {
    "wide": "welcoming/camera",
    "half": "deadpan",
    "side": "sarcastic",
    "narrow": "angry",
    "shock": "astonished",
    "roll": "skeptical/up-right",
    "teary": "grieving",
    "wince": "concerned/closed",
    "sleepy": "tired",
}


def _reading(kind: str) -> tuple[Mood, EyeState | None]:
    """What a pose's ``eyes`` names: a mood, a state, ``mood/state`` or a shared kind."""
    kind = SHARED_EYES.get(kind, kind)
    name, _, state = kind.partition("/")
    if not state:
        if name in EYE_STATES:
            return MOODS["neutral"], EYE_STATES[name]
        return mood(name), None
    if state not in EYE_STATES:
        raise ToonDataError(f"Bento has no eye state {state!r}: his are {tuple(EYE_STATES)}")
    return mood(name), EYE_STATES[state]


def pose_of(
    start: float, name: str, gesture: str | None = None, eyes: str | None = None, wear: tuple[str, ...] = ()
) -> Pose:
    """The pose of the mood ``name`` from ``start``: its eyes, its mouth and its gesture, or the ``gesture`` given (one
    of his own or a shared arm kind), with ``eyes`` one of :data:`EYE_STATES` over it."""
    held = mood(name)
    arms = held.gesture if gesture is None else gesture
    if arms not in GESTURES and arms not in ARMS:
        raise ToonDataError(f"Bento has no gesture {arms!r}: his are {tuple(GESTURES)}, and the shared {ARMS}")
    return Pose(start, name if eyes is None else _state_of(name, eyes), held.mouth, arms, wear)


def _state_of(name: str, eyes: str) -> str:
    kind = f"{name}/{eyes}"
    _reading(kind)
    return kind


def _tilt_of(eyes: str) -> float:
    """How far a pose with these eyes tilts his head."""
    return 0.0 if eyes == "hearts" else _reading(eyes)[0].tilt


# -- the eyes ----------------------------------------------------------------------------------------------------------
_GLANCE = 0.42  # a glance's eye radii that take a pupil the whole way across
_EYE_X = (206.0, 368.0)
_EYE_Y = 280.0
_EYE_RX = 34.0
_BROW: Path = ((-29.0, 2.0), (0.0, -11.0, 29.0, 1.0))
_FLAT_BROW: Path = ((-29.0, 0.0), (0.0, -2.0, 29.0, 0.0))
_CHEEK_X = (172.0, 386.0)
_TEARS = ((213.0, 324.0), (374.0, 327.0))
_SWEAT: Path = (
    (427.0, 241.0),
    (412.0, 263.0, 419.0, 275.0),
    (427.0, 284.0, 436.0, 275.0),
    (443.0, 265.0, 427.0, 241.0),
)


def _eye_marks(held: Mood, side: int) -> list[Layer]:
    cx = _EYE_X[side]
    out: list[Layer] = []
    if "bags" in held.marks:
        out.append(_line(((cx - 24.0, 317.0), (cx, 330.0, cx + 23.0, 316.0)), "#9E6D54", 3.0))
        out.append(_line(((cx - 18.0, 323.0), (cx, 332.0, cx + 16.0, 322.0)), "#BC865B", 2.0))
    out.append(_line(_GLASSES[side], RIM, 2.2))
    if held.marks & {"cheeks", "flush"}:
        x = _CHEEK_X[side]
        out.append(_oval(x, 380.0, 17.0, 10.0, "#DD604A7A" if "flush" in held.marks else "#DD604A52"))
        if "cheeks" in held.marks:
            out += [_line(((k, 377.0), (k - 2.0, 384.0)), "#C7644E", 1.8) for k in (x - 8.0, x, x + 8.0)]
    if "wrinkle" in held.marks and side == 0:
        out.append(_line(((215.0, 343.0), (235.0, 333.0, 255.0, 343.0)), "#A26D4A", 2.5))
        out.append(_line(((223.0, 337.0), (236.0, 331.0, 249.0, 336.0)), "#A26D4A", 2.5))
    if "tears" in held.marks:
        x, y = _TEARS[side]
        drop: Path = (
            (x, y),
            (x - 3.0, y + 15.0, x - 13.0, y + 25.0, x - 8.0, y + 34.0),
            (x, y + 44.0, x + 9.0, y + 34.0),
            (x + 14.0, y + 24.0, x + 3.0, y + 14.0, x, y),
        )
        out.append((_shape(drop), "#6CC6F2"))
        out.append(_line(((x - 3.0, y + 22.0), (x - 5.0, y + 30.0)), "#D8F7FF", 2.0))
    if "sweat" in held.marks and side == 1:
        out.append((_shape(_SWEAT), "#5EBDEB"))
        out.append(_line(((424.0, 260.0), (422.0, 268.0)), "#E5F9FF", 2.0))
    return out


def _brow(held: Mood, side: int) -> Layer:
    place = _moved(_EYE_X[side], 239.0 + held.brows[side], held.angles[side])
    return _line(_FLAT_BROW if held.name in LEVEL_BROWS else _BROW, DARK_FUR, 8.5, place)


def _iris(held: Mood, aperture: Sequence[Point], x: float, y: float) -> list[Layer]:
    return [
        *_patch(_meet(aperture, _ring(x, y, 15.0, 19.0)), IRIS),
        *_patch(_meet(aperture, _ring(x + 0.6, y + 1.0, 10.0 * held.pupil, 14.0 * held.pupil)), PUPIL),
        *_patch(_meet(aperture, _ring(x - 4.0, y - 6.0, 4.0, 5.0, 16), 16), "#FFFFFF"),
        *_patch(_meet(aperture, _ring(x + 4.0, y + 7.0, 1.6, 2.0, 12), 8), "#E3F1FB"),
    ]


def _lid_line(path: Path, ring: Sequence[Point]) -> list[Layer]:
    """A lid's edge, as far as the eye it crosses."""
    inside = []
    for x, y in _samples(path, per_piece=24):
        span = _span(ring, x)
        if span is not None and span[0] <= y <= span[1]:
            inside.append((x, y))
    return [_trace(inside, DARK_FUR, 2.2)] if len(inside) >= 2 else []


def _eye_layers(held: Mood, state: EyeState | None, side: int, glance: Point) -> list[Layer]:
    """One eye, side 0 the one on screen left: the white, the iris and its lids, the brow, then the marks."""
    cx, cy, rx = _EYE_X[side], _EYE_Y, _EYE_RX
    ry = 36.0 if held.wide else 31.0
    top = held.lids[side] if state is None or state.blink is None else state.blink[side]
    shut = top >= 0.99 or (bool(held.shut) and (state is None or state.blink is None))
    out: list[Layer] = []
    if shut:
        curve = -15.0 if held.shut == "happy" else 11.0
        out.append(_line(((cx - 29.0, cy + 3.0), (cx, cy + curve, cx + 29.0, cy + 3.0)), DARK_FUR, 4.0))
    else:
        ty = cy - ry + 2.0 * ry * top if top > 0.015 else cy - ry - 8.0
        by = cy + ry - held.bottom * 2.0 * ry if held.bottom else cy + ry + 10.0
        opening: Path = (
            (cx - rx - 4.0, ty),
            (cx, ty + 5.0, cx + rx + 4.0, ty),
            (cx + rx + 4.0, by),
            (cx, by - 8.0, cx - rx - 4.0, by),
        )
        ring = _ring(cx, cy, rx, ry)
        aperture = _meet(ring, _samples(opening))
        gx, gy = held.gaze if state is None or state.gaze is None else state.gaze
        if state is not None and state.near:
            gx = 0.8 if side == 0 else -0.8
        gx, gy = gx + glance[0] / _GLANCE, gy + glance[1] / _GLANCE
        mag = max(1.0, math.hypot(gx, gy))
        out += _patch(aperture, SCLERA)
        out += _iris(held, aperture, cx + gx / mag * 14.0, cy + gy / mag * 12.0)
        if top > 0.015:
            out += _lid_line(((cx - rx - 3.0, ty), (cx, ty + 5.0, cx + rx + 3.0, ty)), ring)
        if held.bottom:
            out += _lid_line(((cx - rx - 3.0, by), (cx, by - 8.0, cx + rx + 3.0, by)), ring)
    return [*out, _brow(held, side), *_eye_marks(held, side)]


def _hearts(side: int) -> list[Layer]:
    x, y = _at(_EYE_X[side], _EYE_Y)
    heart = _heart(x, y, _EYE_RX * SIZE)
    return [(brush.outline(heart), HEART), *_eye_marks(MOODS["affectionate"], side)]


def _lid_layers() -> list[Layer]:
    """Both eyes shut for a blink: his fur and muzzle laid back over the eye, then the closed line."""
    out: list[Layer] = []
    muzzle = _samples(MUZZLE)
    for side, cx in enumerate(_EYE_X):
        ring = _ring(cx, _EYE_Y, _EYE_RX + 1.5, 37.5)
        out += _patch(ring, _head_ramp())
        out += _patch(_meet(muzzle, ring), _snout_ramp())
        reach = [(x, y) for x, y in _samples(_MUZZLE_TOP, per_piece=48) if abs(x - cx) <= _EYE_RX + 4.0]
        out.append(_trace(reach, MUZZLE_LINE, 2.0))
        out.append(_line(((cx - 29.0, _EYE_Y + 3.0), (cx, _EYE_Y + 11.0, cx + 29.0, _EYE_Y + 3.0)), DARK_FUR, 4.0))
        out.append(_line(_GLASSES[side], RIM, 2.2))
    out.append(_line(_BRIDGE, RIM, 2.2))
    return out


# -- the drawing -------------------------------------------------------------------------------------------------------
_SLEEVE_WEIGHT = 54.0  # an arm of a shared pose, his drawing's pixels
# Where a shared arm leaves him: the cast's shoulders stand clear of his blazer, and a sleeve from there is a hump
_HIS_SHOULDERS: dict[Point, Point] = dict(zip(SHOULDERS, ((92.0, 726.0), (281.4, 726.0)), strict=True))
_PAW_REACH = 16.0  # how far past the cuff a shared pose's paw sits, reference pixels
_CUFF = "#456AC4"
_SHARED_ARMS = frozenset(ARMS)


def _arm_from(shoulder: Point) -> Arm:
    """The arm a shared pose's limb leaves ``shoulder`` on."""
    if shoulder not in SHOULDERS:
        raise ToonDataError(f"a shared arm leaves a shoulder in {SHOULDERS}, not {shoulder}")
    return Arm.LEFT if shoulder == SHOULDERS[0] else Arm.RIGHT


@dataclass(frozen=True)
class Bento:
    """His drawing (:class:`srstudio.toon_cast.Drawing`, :class:`srstudio.toon_cast.Posing`,
    :class:`srstudio.toon_head.Glancing`). ``glance`` is how far his pupils are off, in eye radii, and ``number`` the
    version he is drawn as."""

    tilt: float = 0.0
    glance: Point = (0.0, 0.0)
    number: int = 1

    def __post_init__(self) -> None:
        if self.number not in (1, 2):
            raise ToonDataError(f"Bento has versions 1 and 2, not version {self.number}")

    def foundation(self, look: Look) -> list[Layer]:
        return [*trunk_layers(), *skull_layers(), *_muzzle_layers()]

    def eye(self, look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
        side = 0 if inner > 0 else 1
        if kind == "hearts":
            return _hearts(side)
        held, state = _reading(kind)
        return _eye_layers(held, state, side, self.glance)

    def lids(self, look: Look) -> list[Layer]:
        return _lid_layers()

    def mouth(self, look: Look, kind: str) -> list[Layer]:
        if kind == "none":
            return []
        return _mouth_layers(SHARED_MOUTHS.get(kind, kind))

    def viseme(self, look: Look, kind: str) -> list[Layer]:
        return _viseme_layers(kind)

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]:
        """An arm of a shared pose: a sleeve along ``points`` and on to ``paw``, a cuff and a tiny paw past its end."""
        line = [_HIS_SHOULDERS.get(points[0], points[0]), *points[1:], paw]
        (x0, y0), (x1, y1) = line[-2], line[-1]
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        half = _SLEEVE_WEIGHT * SIZE / 2.0
        sleeve = brush.stroke(line, half * 2.0, brush.EVEN)
        cuff = [(x1 - uy * half, y1 + ux * half), (x1 + uy * half, y1 - ux * half)]
        wrist = _off((x1 + ux * _PAW_REACH, y1 + uy * _PAW_REACH))
        angle = math.degrees(math.atan2(ux, -uy))
        if self.number < 2:
            hand = _hand(wrist[0], wrist[1], angle, False, 0.72)
        else:  # on a desk, on a keyboard, across him, over his mouth or hanging: never shown palm first
            hand = _paw_layers(Paw(_arm_from(points[0]), wrist[0], wrist[1], angle, scale=0.72, facing=Facing.BACK), 2)
        return [
            (brush.stroke(line, (half + 3.0 * SIZE) * 2.0, brush.EVEN), SLEEVE_LINE),
            (sleeve, _ramp("sleeve", JACKET, JACKET_FLAT, sleeve)),
            (brush.stroke(cuff, 3.0 * SIZE, brush.EVEN), _CUFF),
            *hand,
        ]

    def looking(self, dx: float, dy: float) -> Bento:
        return replace(self, glance=(dx, dy))

    def gesture(self, arms: str) -> tuple[list[Layer], list[Layer]] | None:
        if arms in GESTURES:
            return _gesture_layers(GESTURES[arms], self.number)
        if arms in _SHARED_ARMS:
            return None
        raise ToonDataError(f"Bento has no gesture {arms!r}: his are {tuple(GESTURES)}, and the shared kinds")

    def shut(self, eyes: str) -> bool:
        if eyes == "hearts":
            return True
        held, state = _reading(eyes)
        if state is not None and state.blink is not None:
            return min(state.blink) >= 0.99
        return bool(held.shut)


_head = _outline(HEAD)
BENTO = Look(
    name="bento",
    coat=FUR_FLAT,
    dark=DARK_FUR,
    light=SNOUT_FLAT,
    silhouette=_head,
    eyes=(_at(_EYE_X[0], _EYE_Y), _at(_EYE_X[1], _EYE_Y)),
    eye_r=_EYE_RX * SIZE,
    mouth=_at(291.0, 405.0),
    mouth_w=62.0 * SIZE,
    limb=_SLEEVE_WEIGHT * SIZE / 2.0,
    blink=3.7,
    drawing=Bento(),
)
BENTO_2 = replace(BENTO, drawing=Bento(number=2))
BENTO_MOTION = HeadStyle(  # a calm anchor: a measured nod that settles, a level head, the eyes doing the glancing
    seed=6062,
    signature="^",
    nod_px=6.0,
    nod_roll=1.0,
    head=Spring(2.6, 0.82),
    settle=Spring(1.6, 0.9),
    body=Spring(1.4, 1.0),
    min_gap=0.6,
    loud_range=8.0,
    lean=0.6,
    idle_roll=0.9,
    idle_px=0.7,
    idle_hz=0.16,
    breath_period=4.6,
    glance_every=4.2,
    glance_hold=1.1,
    glance_turn=2.0,
    glance_face=0.8,
)
_TILTS = tuple(mood.tilt for mood in MOODS.values())
BENTO_RIG = HeadRig(
    look=BENTO,
    neck=_at(PIVOT_X, 424.0),
    tilt=0.0,
    head=_head,
    cover=_BLAZER_TOP,
    skull=skull_layers,
    face=_muzzle_layers,
    trunk=trunk_layers,
    style=BENTO_MOTION,
    head_over=True,
    pose_tilt=_tilt_of,
    tilt_reach=(min(_TILTS), max(_TILTS)),
    face_slide=FACE_SLIDE,
)
BENTO_RIG_2 = replace(BENTO_RIG, look=BENTO_2)
_CONTRACT = PartContract(
    parameters=(
        (
            'poses',
            ParameterContract(
                items=ParameterContract(
                    fields=(('start', ParameterContract(unit='seconds', timebase='relative:enter', minimum=0)),)
                )
            ),
        ),
        ('enter', ParameterContract(unit='seconds', timebase='project', role='start', minimum=0)),
        (
            'duration',
            ParameterContract(
                unit='seconds', timebase='project', role='end', description='Exit time; must be greater than enter.'
            ),
        ),
        ('taps', ParameterContract(items=ParameterContract(unit='seconds', timebase='project'))),
    ),
    capabilities=(('limbs', False), ('head_motion', False), ('expressions', True), ('mouths', True)),
    constraints=(
        'Pose starts are ordered relative to enter and begin at zero.',
        'duration is the project exit time, strictly after enter.',
        'For procedural head motion use toon_head.figure with BENTO_RIG and a HeadPlan.',
    ),
    operations=(
        Operation(
            'pose_of',
            pose_of,
            PartContract(
                parameters=(
                    ('start', ParameterContract(unit='seconds', timebase='relative:enter', minimum=0)),
                    ('name', ParameterContract(enum=tuple(MOODS))),
                    ('gesture', ParameterContract(enum=(None, *dict.fromkeys((*GESTURES, *ARMS))))),
                    ('eyes', ParameterContract(enum=(None, *EYE_STATES))),
                )
            ),
        ),
    ),
)


@register(
    "character",
    "toon-bento",
    summary="Bento, a caramel capybara in a blue blazer and red tie: a broad muzzle, two front teeth, small round ears "
    "and tiny paws, with 36 moods, 12 eye states, 9 gestures and his own visemes",
    examples=(
        'from srstudio import get\n'
        'from srstudio.toon_bento import pose_of\n'
        'poses = [pose_of(0, "skeptical", "folded", "left"), pose_of(1, "happy")]\n'
        'groups = get("character", "toon-bento")(ep.cv, ep.comp, poses, duration=2)',
    ),
    contract=_CONTRACT,
)
def bento(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    """Draw Bento's mood poses with each mood's head tilt held and no procedural head motion.

    Use srstudio.toon_bento.pose_of(start, name, gesture=None, eyes=None). MOODS, EYE_STATES and GESTURES in
    that module expose the accepted names; gesture also accepts srstudio.toon.ARMS. Pose starts are seconds
    relative to enter, starting at zero. Enter, duration (the exit time), taps and mouths use project seconds.
    Returns a list containing the outer group. Nonempty limbs are unsupported: use Bento's named gestures.
    For moving heads, pass the poses and a HeadPlan to srstudio.toon_head.figure with BENTO_RIG.
    """
    if limbs:
        raise ToonDataError("Bento's arms are gestures: a limb track cannot draw over them")
    return [figure(cv, parent, BENTO_RIG, poses, duration, HeadPlan.still(), taps, enter, stickers, mouths)]


@register(
    "character",
    "toon-bento@2",
    summary="Bento with a pair of hands, the right the mirror of the left and each thumb on its own side",
    contract=_CONTRACT,
)
def bento_2(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    """Draw Bento as :func:`bento` does, with his pair of hands: version 2.

    For moving heads, pass the poses and a HeadPlan to srstudio.toon_head.figure with BENTO_RIG_2.
    """
    if limbs:
        raise ToonDataError("Bento's arms are gestures: a limb track cannot draw over them")
    return [figure(cv, parent, BENTO_RIG_2, poses, duration, HeadPlan.still(), taps, enter, stickers, mouths)]
