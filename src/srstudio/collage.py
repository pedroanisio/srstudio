"""Collage: paper cut-out people and a glossy porcelain toilet with a paper head, on painted sets (ADR 0026).

The look mixes media the way a surreal cartoon does: the people are flat construction paper with hand-cut edges, an
ink outline and a drop shadow that lifts them off the set, while *Flush*, the singing toilet of the invented kids'
show *BOWLHEADS*, is the one glossy "CGI" object in the frame: porcelain in gradients with a paper head poking out
of the bowl. The joke is the clash; nothing here copies a real show's characters, songs or drawings.

Every character is a :class:`Look` (skin, hair, top, build, accents, blink) drawn waist-up at the bottom centre of a
1080x1920 frame, inside :data:`FIGURE_BOX`, below the Toon caption pill that :mod:`srstudio.toon` draws at the
top. The vocabulary is the style's own (:data:`EYES`, :data:`MOUTHS`, :data:`ARMS`): :data:`CAST` hands it to
:mod:`srstudio.sketch` so a Collage sketch is checked against it. Every character is lip-synced on the
:data:`srstudio.toon_cast.VISEMES` and blinks at its own pace.

:func:`figure_shapes` is the drawing as data (``(d, fill, stroke, width, opacity)``, frame pixels, only coordinate
pairs in ``d``), so a test can measure it; :func:`figure` puts it on a canvas, one group per pose run, and the
registered drawers in :data:`DRAWERS` follow the :func:`srstudio.sketch.drawer` contract.
"""

from __future__ import annotations

import math
import random
import re
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .sketch import Cast
from .styles import PAPER
from .toon import EPSILON, Line, Pose, runs
from .toon_cast import BLINK_HOLD, VISEMES, Mouths, blink_times, viseme_keys

__all__ = [
    "CollageError",
    "PAPER",
    "INK",
    "EYES",
    "MOUTHS",
    "ARMS",
    "VISEMES",
    "HAIRS",
    "BUILDS",
    "ACCENTS",
    "FIGURE_BOX",
    "Look",
    "LOOKS",
    "CAST",
    "DRAWERS",
    "PAINTS",
    "jitter",
    "face",
    "parse_poses",
    "figure_shapes",
    "viseme_shapes",
    "lid_shapes",
    "draw_shapes",
    "figure",
    "CAPTION_TOP",
    "CAPTION_BOTTOM",
    "CAPTION_SIZE",
    "CAPTION_PAD",
    "CAPTION_MARGIN",
    "caption_lines",
    "captions",
]

INK = PAPER.ink
EYES = ("open", "side", "up", "half", "closed", "wide", "angry", "sad")
MOUTHS = ("flat", "smile", "frown", "o", "grin", "smug")
ARMS = ("down", "point", "shrug", "hold", "face", "fist", "free", "free-right")
HAIRS = ("bald", "balding", "short", "long", "bun", "ponytail", "beanie", "curly")
BUILDS = ("slim", "broad", "round", "kid")
ACCENTS = ("tie", "glasses", "cane", "headset", "moustache", "pearls", "hoodie", "blazer")
FIGURE_BOX = (100.0, 760.0, 980.0, 1960.0)  # x0, y0, x1, y1: inside, below the captions; it bleeds off the bottom
CX = 540.0
HEAD_Y, HEAD_RX, HEAD_RY = 1090.0, 220.0, 205.0
TOILET_HEAD_Y = 1240.0
CAPTION_TOP = 334.0  # the pill's top, where the Toon pill sits: clear of the reel's top bar
CAPTION_SIZE = 54  # font pixels
CAPTION_LEADING = 62  # frame pixels from one caption line to the next
CAPTION_PAD = 64  # frame pixels added to the widest line's width
CAPTION_PAD_Y = 22  # above and below the text
CAPTION_MARGIN = 40  # kept free at each side of the frame
CAPTION_RADIUS = 26
CAPTION_SHADOW = {"radius": 10, "offsetX": 6, "offsetY": 9, "color": "#2b183873"}  # lifts the pill off the set
CAPTION_BOTTOM = CAPTION_TOP + 2 * CAPTION_LEADING + 2 * CAPTION_PAD_Y  # the lowest a two-line pill reaches
SHOULDER_Y = {"slim": 1340.0, "broad": 1330.0, "round": 1340.0, "kid": 1390.0}
HALF_WIDTH = {"slim": 250.0, "broad": 330.0, "round": 300.0, "kid": 210.0}
EDGE = 5.0  # the ink outline of a cut-out
SHADOW = (9.0, 12.0)  # the drop shadow's offset
SHADOW_OPACITY = 0.22
# the soft shadow a figure casts on its set: the engine's drop-shadow on every pose group
FIGURE_SHADOW = {"radius": 22, "offsetX": 14, "offsetY": 18, "color": "#2b18385c"}
BLINK = 3.4
BREATH = 6.0  # pixels a figure rises when it breathes in
BREATH_PERIOD = 2.4  # seconds for one breath
LIPS = "#3a1418"
TONGUE = "#d9606b"
HEX = re.compile(r"#[0-9a-fA-F]{6}")
# gradients a shape may name as ``url(#name)``; draw_shapes defines them on the canvas when first used
PAINTS: dict[str, tuple[str, tuple[tuple[float, str], ...], tuple[float, ...]]] = {
    "collage-porcelain": ("linear", ((0, "#ffffff"), (0.55, "#e9eef3"), (1, "#a9b6c3")), (0, 0, 0, 1)),
    "collage-porcelain-side": ("linear", ((0, "#b7c3cf"), (0.35, "#ffffff"), (1, "#9eabb8")), (0, 0, 1, 0)),
    "collage-water": ("radial", ((0, "#bfe9ff"), (1, "#3d8fc4")), (0.5, 0.4, 0.6)),
    "collage-gloss": ("radial", ((0, "#ffffff"), (1, "#ffffff00")), (0.5, 0.5, 0.5)),
    "collage-chrome": ("linear", ((0, "#f8fbff"), (0.5, "#9aa7b4"), (1, "#e3e9ef")), (0, 0, 0, 1)),
}

Shape = tuple[str, str, str | None, float, float]  # d, fill, stroke (None: none), stroke width, opacity
Point = tuple[float, float]


class CollageError(SrstudioError, ValueError):
    """A Collage look, pose or drawing request is malformed."""


@dataclass(frozen=True)
class Look:
    """One character: who it is (``summary``), its paper colours, hair, build, the accents it wears and how often
    it blinks (seconds; 0 never). ``toilet`` draws the porcelain body instead of a torso."""

    name: str
    summary: str
    skin: str
    hair: str
    hair_color: str
    top: str
    build: str = "slim"
    accents: tuple[str, ...] = ()
    blink: float = BLINK
    toilet: bool = False

    def __post_init__(self) -> None:
        for key in ("skin", "hair_color", "top"):
            if not HEX.fullmatch(getattr(self, key)):
                raise CollageError(f"{self.name}: {key} {getattr(self, key)!r} is not a #rrggbb colour")
        if self.hair not in HAIRS:
            raise CollageError(f"{self.name}: hair {self.hair!r} is not one of {HAIRS}")
        if self.build not in BUILDS:
            raise CollageError(f"{self.name}: build {self.build!r} is not one of {BUILDS}")
        unknown = [a for a in self.accents if a not in ACCENTS]
        if unknown:
            raise CollageError(f"{self.name}: accent {unknown} is not one of {ACCENTS}")
        if not (checks.number(self.blink) and self.blink >= 0):
            raise CollageError(f"{self.name}: blink {self.blink!r} must be a non-negative number of seconds")


LOOKS: dict[str, Look] = {
    look.name: look
    for look in (
        Look(
            "brent",
            "Brent, a fifties chief marketing officer in a blazer and tie who rebrands everything",
            "#f1c7a8",
            "short",
            "#b8b2a6",
            "#2f3d5c",
            "broad",
            ("tie", "blazer"),
        ),
        Look(
            "rosa",
            "Rosa, a seventies board chair with a cane, pearls and no patience",
            "#c98f63",
            "bun",
            "#e8e4de",
            "#7a2f4a",
            "slim",
            ("cane", "pearls"),
            blink=4.6,
        ),
        Look(
            "gary",
            "Gary, a balding forties dad who learned every episode of his kid's show",
            "#f4d0b5",
            "balding",
            "#7a5a3c",
            "#5b8c4e",
            "round",
        ),
        Look(
            "kai",
            "Kai, a kid in a hoodie whose headset beeps whenever a new episode drops",
            "#8d5a3b",
            "curly",
            "#1f1612",
            "#e94f37",
            "kid",
            ("hoodie", "headset"),
            blink=2.6,
        ),
        Look(
            "priya",
            "Priya, a thirties teacher in glasses with a ponytail and a red pen",
            "#a8714f",
            "ponytail",
            "#15110f",
            "#3c7a89",
            "slim",
            ("glasses",),
        ),
        Look(
            "deb",
            "Deb, a forties mom on a first date she is starting to regret",
            "#5c3a24",
            "long",
            "#20150f",
            "#f2a541",
            "round",
        ),
        Look(
            "jun",
            "Jun, a thirties showrunner in a beanie who makes the toilet show and wants to be taken seriously",
            "#e6b98f",
            "beanie",
            "#4a4e69",
            "#22223b",
            "slim",
        ),
        Look(
            "feld",
            "Dr. Feld, a sixties therapist with a bun and glasses who has heard everything until now",
            "#f3d6c4",
            "bun",
            "#9a8f87",
            "#8a6f9e",
            "slim",
            ("glasses",),
            blink=5.0,
        ),
        Look(
            "omar",
            "Omar, a fifties news anchor with a moustache and a tie, sliding from panic to engagement",
            "#b07a52",
            "short",
            "#2a201a",
            "#1d3557",
            "broad",
            ("moustache", "tie", "blazer"),
        ),
        Look(
            "flush",
            "Flush, the singing toilet of the invented kids' show BOWLHEADS: glossy porcelain, a paper head",
            "#f6dcc6",
            "bald",
            "#000000",
            "#ffffff",
            "slim",
            blink=2.2,
            toilet=True,
        ),
    )
}
CAST = Cast("Collage", tuple(LOOKS), tuple(LOOKS), EYES, MOUTHS, ARMS)


# -- paper geometry ---------------------------------------------------------------------------------------------------
def _r(v: float) -> float:
    return round(v, 1)


def _poly(points: Sequence[Point], closed: bool = True) -> str:
    head, *rest = points
    d = f"M{_r(head[0]):g} {_r(head[1]):g}" + "".join(f" L{_r(x):g} {_r(y):g}" for x, y in rest)
    return d + (" Z" if closed else "")


def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode()))


def _ring(key: str, cx: float, cy: float, rx: float, ry: float, n: int = 32, amount: float = 0.025) -> list[Point]:
    if n < 3:
        raise CollageError(f"a jittered ring needs at least 3 points, got {n}")
    rng = _rng(key)
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + rng.uniform(-amount, amount)
        out.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return out


def jitter(key: str, cx: float, cy: float, rx: float, ry: float, n: int = 32, amount: float = 0.025) -> str:
    """A hand-cut ellipse: ``n`` points on it, each radius off by up to ``amount``, the same for the same ``key``."""
    return _poly(_ring(key, cx, cy, rx, ry, n, amount))


def _cut(key: str, points: Sequence[Point], amount: float = 4.0) -> list[Point]:
    """A polygon as if cut with scissors: every corner moved a little, the same for the same ``key``."""
    rng = _rng(key)
    return [(x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount)) for x, y in points]


def _shift(points: Sequence[Point], dx: float, dy: float) -> list[Point]:
    return [(x + dx, y + dy) for x, y in points]


def _paper(points: Sequence[Point], fill: str, shadow: bool = True) -> list[Shape]:
    """A cut-out: its drop shadow, then the paper with its ink edge."""
    out: list[Shape] = []
    if shadow:
        out.append((_poly(_shift(points, *SHADOW)), "#000000", None, 0.0, SHADOW_OPACITY))
    out.append((_poly(points), fill, INK, EDGE, 1.0))
    return out


def _arc(points: Sequence[Point], width: float, colour: str = INK) -> Shape:
    """An open stroke through ``points`` (a smile, a lash line)."""
    return (_poly(points, closed=False), "#00000000", colour, width, 1.0)


def _curve(x0: float, x1: float, y: float, sag: float, n: int = 9) -> list[Point]:
    """``n`` points from ``x0`` to ``x1`` along a parabola sagging ``sag`` at the middle (negative: a hump)."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append((x0 + (x1 - x0) * t, y + sag * (1 - (2 * t - 1) ** 2)))
    return out


def _arc_points(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, n: int = 16) -> list[Point]:
    return [
        (
            cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
            cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1))),
        )
        for i in range(n)
    ]


def face(look: Look) -> Point:
    """The centre of a character's head, frame pixels: the pivot of a zoom onto it."""
    return CX, TOILET_HEAD_Y if look.toilet else HEAD_Y


# -- poses ------------------------------------------------------------------------------------------------------------
def parse_poses(data: Any, where: str = "poses") -> list[Pose]:
    """Poses in order from 0 s, each naming an expression the Collage cast has."""
    if not isinstance(data, list):
        raise CollageError(f"{where}: a list of poses, got {type(data).__name__}")
    out: list[Pose] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise CollageError(f"{where}[{i}]: a pose is an object")
        for key, allowed in (("eyes", EYES), ("mouth", MOUTHS), ("arms", ARMS)):
            if item.get(key) not in allowed:
                raise CollageError(f"{where}[{i}]: {key} {item.get(key)!r} is not one of {allowed}")
        start = item.get("start")
        if not checks.number(start):
            raise CollageError(f"{where}[{i}]: start {start!r} is not a number")
        if i == 0 and start != 0:
            raise CollageError(f"{where}[0]: the first pose starts at {start}, not 0")
        if out and start <= out[-1].start + EPSILON:
            raise CollageError(f"{where}[{i}]: start {start} is not after the pose before ({out[-1].start})")
        out.append(Pose(float(start), item["eyes"], item["mouth"], item["arms"]))
    return out


# -- the figure as data -----------------------------------------------------------------------------------------------
def _smooth(points: Sequence[Point], closed: bool = True) -> str:
    """A curve through ``points`` (Catmull-Rom as cubic Béziers): the scissors follow a line, not a polygon."""
    pts = list(points)
    n = len(pts)
    if n < 3:
        raise CollageError("a smooth cut needs at least 3 points")
    d = f"M{_r(pts[0][0]):g} {_r(pts[0][1]):g}"
    last = n if closed else n - 1
    for i in range(last):
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{_r(c1[0]):g} {_r(c1[1]):g} {_r(c2[0]):g} {_r(c2[1]):g} {_r(p2[0]):g} {_r(p2[1]):g}"
    return d + (" Z" if closed else "")


def _mix(colour: str, other: str, t: float) -> str:
    a = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b, strict=True))


def _shade(colour: str) -> str:
    return _mix(colour, "#2b1838", 0.24)


def _light(colour: str) -> str:
    return _mix(colour, "#ffffff", 0.28)


def _blob(
    key: str,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    fill: str,
    n: int = 14,
    amount: float = 0.025,
    edge: float = EDGE,
    opacity: float = 1.0,
) -> Shape:
    """A hand-cut oval with a smooth edge."""
    return (_smooth(_ring(key, cx, cy, rx, ry, n, amount)), fill, INK if edge else None, edge, opacity)


def _sheet(points: Sequence[Point]) -> str:
    """A curve through ``points`` closed by a straight edge from the last back to the first: a shape cut off by the
    frame's bottom, whose straight edge must not bulge past it."""
    return _smooth(points, closed=False) + " Z"


def _cutout(
    key: str, points: Sequence[Point], fill: str, amount: float = 3.0, edge: float = EDGE, flat: bool = False
) -> Shape:
    cut = _cut(key, points, amount)
    return (_sheet(cut) if flat else _smooth(cut), fill, INK if edge else None, edge, 1.0)


def _crescent(cx: float, cy: float, rx: float, ry: float, dx: float, dy: float, a0: float, a1: float) -> list[Point]:
    """The part of an ellipse's rim from angle ``a0`` to ``a1`` closed by the same ellipse moved by ``dx, dy``: a
    shaded or lit edge inside the shape."""
    outer = _arc_points(cx, cy, rx, ry, a0, a1, n=12)
    inner = _arc_points(cx + dx, cy + dy, rx * 0.97, ry * 0.97, a1, a0, n=12)
    return outer + inner[1:-1]


def _capsule(a: Point, b: Point, width: float) -> list[Point]:
    """A sleeve or a finger: a band from ``a`` to ``b`` with round ends."""
    (x0, y0), (x1, y1) = a, b
    angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
    r = width / 2
    end = _arc_points(x1, y1, r, r, angle - 90, angle + 90, n=7)
    start = _arc_points(x0, y0, r, r, angle + 90, angle + 270, n=7)

    # points along the straight sides keep the curve through them from bulging past the band
    def side(p: Point, q: Point) -> list[Point]:
        return [(p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k) for k in (0.25, 0.5, 0.75)]

    return end + side(end[-1], start[0]) + start + side(start[-1], end[0])


BEANIE_BAND_BOTTOM = -4  # the band's lower edge, from the face's centre


def _eye_centres(look: Look) -> tuple[Point, Point]:
    cx, cy = face(look)
    return (cx - 62, cy - 18), (cx + 62, cy - 18)


PUPIL = {"side": (24, 4, 15), "up": (0, -26, 15), "wide": (0, 0, 9), "angry": (0, 12, 15), "sad": (0, 12, 15)}
# eyebrows: (raise of the inner end, raise of the outer end) in pixels; positive is up
BROWS = {
    "open": (4, 10),
    "side": (0, 14),
    "up": (22, 26),
    "half": (-6, -2),
    "closed": (0, 2),
    "wide": (34, 30),
    "angry": (-24, 14),
    "sad": (22, -12),
}


def _eyes(look: Look, kind: str) -> list[Shape]:
    out: list[Shape] = []
    brow = look.hair_color if look.hair not in ("bald",) else _shade(look.skin)
    for side, (ex, ey) in zip((-1, 1), _eye_centres(look), strict=True):
        inner_up, outer_up = BROWS[kind]
        inner, outer = ex - side * 46, ex + side * 50
        top = ey - 80
        band = [
            (inner, top - inner_up),
            ((inner + outer) / 2, top - (inner_up + outer_up) / 2 - 8),
            (outer, top - outer_up),
        ]
        out.append(
            _cutout(
                f"{look.name}-brow{side}",
                _capsule(band[0], band[2], 22)[:7] + _capsule(band[0], band[2], 22)[7:],
                brow,
                1.0,
                0,
            )
        )
        if kind == "closed":
            out.append(_arc(_curve(ex - 44, ex + 44, ey + 4, 14), 7))
            continue
        ry = 70.0 if kind == "wide" else 60.0
        out.append(_blob(f"{look.name}-eye{side}", ex, ey, 52, ry, "#ffffff", n=16, amount=0.01, edge=4.5))
        out.append((_smooth(_crescent(ex, ey, 52, ry, 0, -14, 20, 160)), "#dfe3ee", None, 0.0, 1.0))
        dx, dy, r = PUPIL.get(kind, (0, 6, 15))
        out.append(_blob(f"{look.name}-pupil{side}", ex + dx, ey + dy, r, r, INK, n=10, amount=0.02, edge=0))
        out.append(
            _blob(
                f"{look.name}-glint{side}",
                ex + dx + r * 0.35,
                ey + dy - r * 0.4,
                r * 0.32,
                r * 0.32,
                "#ffffff",
                n=8,
                amount=0.0,
                edge=0,
            )
        )
        if kind == "half":
            lid = [(ex - 58, ey - 70), (ex + 58, ey - 70), (ex + 58, ey - 2), (ex - 58, ey - 2)]
            out.append((_poly(lid), look.skin, None, 0.0, 1.0))
            out.append(_arc(_curve(ex - 52, ex + 52, ey - 2, 4), 7))
        elif kind in ("angry", "sad"):
            near, far = ex - side * 58, ex + side * 58
            inner_y, outer_y = (ey - 14, ey - 44) if kind == "angry" else (ey - 44, ey - 14)
            lid = [(far, ey - 80), (near, ey - 80), (near, inner_y), (far, outer_y)]
            out.append((_poly(lid), look.skin, None, 0.0, 1.0))
            out.append(_arc([(near, inner_y), (far, outer_y)], 7))
    return out


def lid_shapes(look: Look, under_band: bool = False) -> list[Shape]:
    """Both eyes shut: paper lids over the whites and a lash line, for a blink. The lids are drawn after the hair, so
    a hat's band ends up under them; ``under_band`` starts them at its lower edge and drops the lash line below it,
    for new reels, and delivered ones keep the lid they were drawn with."""
    out: list[Shape] = []
    cy = face(look)[1]
    for side, (ex, ey) in zip((-1, 1), _eye_centres(look), strict=True):
        if under_band and look.hair == "beanie":
            top, bottom = cy + BEANIE_BAND_BOTTOM, ey + 75
            lid = [(ex - 57, top), (ex + 57, top), (ex + 57, bottom - 24), (ex + 30, bottom), (ex - 30, bottom)]
            out.append((_poly([*lid, (ex - 57, bottom - 24)]), look.skin, None, 0.0, 1.0))
            out.append(_arc(_curve(ex - 44, ex + 44, top + 22, 14), 7))
            continue
        out.append(_blob(f"{look.name}-lid{side}", ex, ey, 57, 75, look.skin, n=14, amount=0.01, edge=0))
        out.append(_arc(_curve(ex - 44, ex + 44, ey + 4, 14), 7))
    return out


def _mouth_centre(look: Look) -> Point:
    cx, cy = face(look)
    return cx, cy + 116


def _mouth(look: Look, kind: str) -> list[Shape]:
    mx, my = _mouth_centre(look)
    if kind == "flat":
        return [_arc([(mx - 44, my), (mx, my + 2), (mx + 44, my)], 8)]
    if kind == "smile":
        return [
            _arc(_curve(mx - 62, mx + 62, my - 10, 30), 8),
            _arc([(mx - 70, my - 18), (mx - 58, my - 6)], 6),
            _arc([(mx + 70, my - 18), (mx + 58, my - 6)], 6),
        ]
    if kind == "frown":
        return [_arc(_curve(mx - 52, mx + 52, my + 14, -24), 8)]
    if kind == "o":
        return [
            _blob(f"{look.name}-o", mx, my + 6, 24, 30, LIPS, n=12, edge=5),
            _blob(f"{look.name}-o-tongue", mx, my + 22, 13, 8, TONGUE, n=8, edge=0),
        ]
    if kind == "grin":
        top = [(mx - 76, my - 16), (mx - 30, my - 20), (mx + 30, my - 20), (mx + 76, my - 16)]
        bowl = _curve(mx + 70, mx - 70, my - 12, 58, n=9)
        teeth = [(mx - 64, my - 14), (mx + 64, my - 14), (mx + 58, my + 4), (mx - 58, my + 4)]
        return [
            (_smooth(top + bowl), LIPS, INK, 6.0, 1.0),
            (_smooth(teeth), "#ffffff", None, 0.0, 1.0),
            _blob(f"{look.name}-grin-tongue", mx, my + 30, 34, 13, TONGUE, n=10, edge=0),
            (_smooth(top + bowl), "#00000000", INK, 6.0, 1.0),
        ]
    if kind == "smug":
        return [
            _arc([(mx - 52, my + 6), (mx - 10, my + 10), (mx + 34, my - 4), (mx + 60, my - 22)], 8),
            _arc([(mx + 62, my - 28), (mx + 66, my - 12)], 6),
        ]
    raise CollageError(f"mouth {kind!r} is not one of {MOUTHS}")


def viseme_shapes(look: Look, kind: str) -> list[Shape]:
    """The mouth shape for a sound: ``open``, ``round`` or ``teeth`` (``closed`` is the pose's own mouth)."""
    mx, my = _mouth_centre(look)
    if kind == "open":
        return [
            _blob(f"{look.name}-open", mx, my + 8, 44, 34, LIPS, n=14, edge=5),
            (
                _smooth([(mx - 34, my - 14), (mx + 34, my - 14), (mx + 30, my - 4), (mx - 30, my - 4)]),
                "#ffffff",
                None,
                0.0,
                1.0,
            ),
            _blob(f"{look.name}-tongue", mx, my + 26, 24, 10, TONGUE, n=10, edge=0),
        ]
    if kind == "round":
        return [
            _blob(f"{look.name}-round", mx, my + 8, 21, 27, LIPS, n=12, edge=5),
            _blob(f"{look.name}-round-tongue", mx, my + 22, 10, 6, TONGUE, n=8, edge=0),
        ]
    if kind == "teeth":
        box = [(mx - 48, my - 14), (mx + 48, my - 14), (mx + 42, my + 22), (mx - 42, my + 22)]
        return [(_smooth(box), "#ffffff", INK, 5.0, 1.0), _arc([(mx - 44, my + 4), (mx + 44, my + 4)], 3)]
    raise CollageError(f"viseme {kind!r} is not one of {VISEMES[1:]}")


def _torso_points(look: Look) -> list[Point]:
    hw, sy = HALF_WIDTH[look.build], SHOULDER_Y[look.build]
    left = [
        (CX - hw + 6, 1950),
        (CX - hw - 4, sy + 200),
        (CX - hw + 14, sy + 70),
        (CX - hw + 70, sy + 14),
        (CX - 120, sy - 8),
    ]
    if look.build == "round":
        left.insert(1, (CX - hw - 30, 1720))
    right = [(2 * CX - x, y) for x, y in reversed(left)]
    return _cut(f"{look.name}-torso", left + right, 3.0)


def _torso(look: Look) -> list[Shape]:
    """The body: the top's cut-out, its shaded side, a lit shoulder, the neckline."""
    hw, sy = HALF_WIDTH[look.build], SHOULDER_Y[look.build]
    top = look.top
    out: list[Shape] = [(_sheet(_torso_points(look)), top, INK, EDGE, 1.0)]
    shade = [
        (CX - hw + 8, 1950),
        (CX - hw - 2, sy + 200),
        (CX - hw + 16, sy + 76),
        (CX - hw + 64, sy + 26),
        (CX - hw + 70, sy + 120),
        (CX - hw + 60, sy + 300),
        (CX - hw + 90, 1950),
    ]
    out.append((_sheet(shade), _shade(top), None, 0.0, 0.9))
    out.append(
        (
            _smooth(
                [(CX + hw - 130, sy + 4), (CX + hw - 60, sy + 18), (CX + hw - 26, sy + 60), (CX + hw - 70, sy + 44)]
            ),
            _light(top),
            None,
            0.0,
            0.9,
        )
    )
    if "tie" in look.accents or "blazer" in look.accents:
        shirt = [(CX - 92, sy - 6), (CX + 92, sy - 6), (CX + 40, sy + 150), (CX, sy + 230), (CX - 40, sy + 150)]
        out.append(_cutout(f"{look.name}-shirt", shirt, "#f8f9fa", 2.0))
        for side in (-1, 1):
            collar = [(CX + side * 8, sy + 6), (CX + side * 96, sy - 10), (CX + side * 70, sy + 60)]
            out.append((_poly(_cut(f"{look.name}-collar{side}", collar, 2)), "#ffffff", INK, 4.0, 1.0))
    elif "hoodie" in look.accents:
        out.append((_smooth(_curve(CX - 110, CX + 110, sy + 2, 40, n=7)), "#00000000", _shade(top), 18.0, 1.0))
        pocket = [(CX - 150, 1950), (CX - 120, 1800), (CX + 120, 1800), (CX + 150, 1950)]
        out.append(_cutout(f"{look.name}-pocket", pocket, _shade(top), 2.0, 4.0, flat=True))
        for side in (-1, 1):
            out.append(
                _arc([(CX + side * 50, sy + 30), (CX + side * 58, sy + 120), (CX + side * 54, sy + 190)], 7, "#f2e9e4")
            )
            out.append(_blob(f"{look.name}-tip{side}", CX + side * 54, sy + 196, 8, 11, "#f2e9e4", n=8, edge=2.5))
    else:
        out.append(
            (_smooth(_curve(CX - 100, CX + 100, sy - 2, 46, n=7), closed=False), "#00000000", _shade(top), 16.0, 1.0)
        )
    return out


def _neck(look: Look) -> list[Shape]:
    sy = SHOULDER_Y[look.build]
    neck = [(CX - 66, HEAD_Y + 130), (CX + 66, HEAD_Y + 130), (CX + 74, sy + 30), (CX - 74, sy + 30)]
    return [
        _cutout(f"{look.name}-neck", neck, look.skin, 2.0),
        (
            _smooth(
                [(CX - 66, HEAD_Y + 140), (CX + 66, HEAD_Y + 140), (CX + 60, HEAD_Y + 200), (CX - 60, HEAD_Y + 200)]
            ),
            _shade(look.skin),
            None,
            0.0,
            1.0,
        ),
    ]


def _hand(look: Look, key: str, x: float, y: float, r: float = 40, side: int = 1) -> list[Shape]:
    """A mitten hand with its thumb, the skin shaded on one side."""
    return [
        _blob(f"{look.name}-{key}-thumb", x - side * r * 0.85, y - r * 0.2, r * 0.38, r * 0.5, look.skin, n=10),
        _blob(f"{look.name}-{key}", x, y, r, r * 0.92, look.skin, n=12, amount=0.04),
        (_smooth(_crescent(x, y, r, r * 0.92, side * 8, -6, 40, 200)), _shade(look.skin), None, 0.0, 0.8),
    ]


def _sleeve(look: Look, key: str, a: Point, b: Point, width: float = 74) -> list[Shape]:
    """An arm in the character's top, shaded along one side, a cuff at the wrist."""
    (x0, y0), (x1, y1) = a, b
    length = math.hypot(x1 - x0, y1 - y0) or 1.0
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    cuff = (x1 - ux * 18, y1 - uy * 18)
    nx, ny = -uy * width * 0.22, ux * width * 0.22
    return [
        _cutout(f"{look.name}-{key}", _capsule(a, b, width), look.top, 2.0),
        (_smooth(_capsule((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), width * 0.42)), _shade(look.top), None, 0.0, 0.7),
        (_smooth(_capsule(cuff, b, width * 0.98)), _shade(look.top), INK, 4.0, 1.0),
    ]


def _arms(look: Look, arms: str) -> tuple[list[Shape], list[Shape]]:
    """The arms under the head and those over the face (a facepalm)."""
    if look.toilet:
        return [], []  # a toilet has no arms; its poses are all in the face
    hw, sy = HALF_WIDTH[look.build], SHOULDER_Y[look.build]
    ls, rs = (CX - hw + 46, sy + 50), (CX + hw - 46, sy + 50)
    under: list[Shape] = []
    over: list[Shape] = []
    low_l, low_r = (CX - hw - 6, 1790), (CX + hw + 6, 1790)

    def down(side: int, shoulder: Point, low: Point, key: str) -> list[Shape]:
        # a relaxed arm: the elbow out from the body, the forearm back in towards the hip
        elbow = (low[0] + side * 14, (shoulder[1] + low[1]) / 2 + 30)
        wrist = (low[0] - side * 12, low[1])
        return (
            _sleeve(look, f"{key}u", shoulder, elbow)
            + _sleeve(look, f"{key}a", elbow, wrist, 70)
            + _hand(look, f"{key}h", wrist[0], wrist[1] + 50, 40, side)
        )

    if arms == "down":
        under += down(-1, ls, low_l, "l") + down(1, rs, low_r, "r")
    elif arms == "point":
        under += down(-1, ls, low_l, "l")
        elbow, hand = (CX + hw + 40, sy + 160), (CX + hw + 30, sy - 120)
        under += _sleeve(look, "ru", rs, elbow) + _sleeve(look, "rf", elbow, hand, 68)
        finger = _capsule((hand[0] + 6, hand[1] - 18), (hand[0] + 44, hand[1] - 84), 26)
        under += [_cutout(f"{look.name}-finger", finger, look.skin, 1.0)] + _hand(look, "rh", *hand, r=38)
    elif arms == "shrug":
        for side, shoulder, key in ((-1, ls, "l"), (1, rs, "r")):
            elbow = (CX + side * (hw + 24), sy + 220)
            hand = (CX + side * (hw + 34), sy + 70)
            under += _sleeve(look, f"{key}u", shoulder, elbow) + _sleeve(look, f"{key}f", elbow, hand, 66)
            under += _hand(look, f"{key}h", *hand, r=36, side=side)
    elif arms == "hold":
        for side, shoulder, key in ((-1, ls, "l"), (1, rs, "r")):
            elbow = (CX + side * (hw + 4), sy + 300)
            hand = (CX + side * 96, sy + 250)
            under += _sleeve(look, f"{key}u", shoulder, elbow) + _sleeve(look, f"{key}f", elbow, hand, 66)
            under += _hand(look, f"{key}h", *hand, r=36, side=-side)
    elif arms == "face":
        under += down(-1, ls, low_l, "l")
        ex, ey = _eye_centres(look)[1]
        elbow = (CX + hw + 10, sy + 230)
        over += _sleeve(look, "ru", rs, elbow) + _sleeve(look, "rf", elbow, (ex + 40, ey + 110), 66)
        over += _hand(look, "rh", ex - 4, ey + 6, r=74, side=-1)
    elif arms == "free":
        under += down(1, rs, low_r, "r")  # the screen-left arm is the scene's to draw, with what it holds
    elif arms == "free-right":
        under += down(-1, ls, low_l, "l")  # the same, for a figure whose scene is on its screen-right
    elif arms == "fist":
        under += down(-1, ls, low_l, "l")
        elbow, hand = (CX + hw + 50, sy + 120), (CX + hw + 30, HEAD_Y - 140)
        under += _sleeve(look, "ru", rs, elbow) + _sleeve(look, "rf", elbow, hand, 68)
        under += [_blob(f"{look.name}-fist", hand[0], hand[1], 46, 42, look.skin, n=12, amount=0.05)]
        under += [
            _arc([(hand[0] - 30, hand[1] - 8), (hand[0] + 28, hand[1] - 8)], 4),
            _arc([(hand[0] - 26, hand[1] + 12), (hand[0] + 24, hand[1] + 12)], 4),
        ]
    else:
        raise CollageError(f"arms {arms!r} is not one of {ARMS}")
    return under, over


def _head(look: Look) -> list[Shape]:
    """Ears, the head with its shaded jaw and a lit brow, a nose and cheeks."""
    cx, cy = face(look)
    skin = look.skin
    out: list[Shape] = []
    for side in (-1, 1):
        ex = cx + side * (HEAD_RX - 6)
        out.append(_blob(f"{look.name}-ear{side}", ex, cy + 14, 36, 48, skin, n=10))
        out.append(_blob(f"{look.name}-ear-in{side}", ex + side * 6, cy + 16, 16, 26, _shade(skin), n=8, edge=0))
    head = _ring(f"{look.name}-head", cx, cy, HEAD_RX, HEAD_RY, n=20, amount=0.014)
    out.append((_smooth(head), skin, INK, EDGE, 1.0))
    out.append((_smooth(_crescent(cx, cy, HEAD_RX, HEAD_RY, 18, -16, 70, 190)), _shade(skin), None, 0.0, 0.55))
    out.append(_blob(f"{look.name}-sheen", cx + 92, cy - 96, 40, 18, _light(skin), n=10, edge=0, opacity=0.7))
    out.append(_blob(f"{look.name}-nose", cx + 8, cy + 52, 22, 16, _shade(skin), n=10, edge=0, opacity=0.9))
    out.append(_blob(f"{look.name}-nose-lit", cx + 14, cy + 46, 8, 5, _light(skin), n=8, edge=0))
    for side in (-1, 1):
        out.append(
            _blob(f"{look.name}-cheek{side}", cx + side * 128, cy + 66, 36, 20, "#ff7f96", n=10, edge=0, opacity=0.35)
        )
    return out


def _hair_back(look: Look) -> list[Shape]:
    cx, cy = face(look)
    hair = look.hair_color
    if look.hair == "long":
        mane = [
            (cx - 250, cy + 360),
            (cx - 268, cy + 80),
            (cx - 220, cy - 160),
            (cx, cy - 236),
            (cx + 220, cy - 160),
            (cx + 268, cy + 80),
            (cx + 250, cy + 360),
            (cx + 120, cy + 380),
            (cx - 120, cy + 380),
        ]
        return [
            _cutout(f"{look.name}-mane", mane, hair, 5.0),
            (
                _smooth([(cx - 250, cy + 360), (cx - 266, cy + 80), (cx - 200, cy + 60), (cx - 190, cy + 360)]),
                _shade(hair),
                None,
                0.0,
                0.8,
            ),
        ]
    if look.hair == "bun":
        return [
            _blob(f"{look.name}-bun", cx + 10, cy - HEAD_RY - 26, 64, 56, hair, n=12, amount=0.04),
            (_smooth(_crescent(cx + 10, cy - HEAD_RY - 26, 64, 56, 14, -12, 100, 220)), _shade(hair), None, 0.0, 0.8),
        ]
    if look.hair == "ponytail":
        tail = [
            (cx + 150, cy - 150),
            (cx + 262, cy - 60),
            (cx + 290, cy + 120),
            (cx + 236, cy + 250),
            (cx + 210, cy + 90),
            (cx + 196, cy - 40),
        ]
        return [
            _cutout(f"{look.name}-tail", tail, hair, 3.0),
            _blob(f"{look.name}-tie", cx + 222, cy - 96, 22, 16, "#e94f37", n=8),
        ]
    if look.hair == "curly":
        out: list[Shape] = []
        for i, (x, y) in enumerate(_arc_points(cx, cy - 6, HEAD_RX + 6, HEAD_RY + 4, 160, 380, n=13)):
            out.append(_blob(f"{look.name}-curl{i}", x, y, 50, 46, hair, n=10, amount=0.06))
        return out
    return []


def _cap(look: Look, depth: float, key: str, fill: str, part: float = 0.3) -> list[Shape]:
    """Hair (or a hat) over the top of the head, ``depth`` of it down, a side part, strands in shade."""
    cx, cy = face(look)
    top = _arc_points(cx, cy, HEAD_RX + 12, HEAD_RY + 14, 188, 352, n=11)
    rng = _rng(f"{look.name}-{key}-fringe")
    fringe_y = cy - HEAD_RY + depth
    fringe = [
        (cx + HEAD_RX - 10 - i * 46, fringe_y + rng.uniform(-10, 10) + (24 if i % 3 == 1 else 0)) for i in range(10)
    ]
    out: list[Shape] = [(_smooth(top + fringe), fill, INK, EDGE, 1.0)]
    px = cx - HEAD_RX * part
    top_y = cy - HEAD_RY * math.sqrt(1 - ((px - cx) / HEAD_RX) ** 2) + 14
    out.append(_arc([(px, top_y), (px + 16, fringe_y - 10)], 6, _shade(fill)))
    for i in range(3):
        x = cx + 30 + i * 52
        y = cy - HEAD_RY * math.sqrt(1 - ((x - cx) / HEAD_RX) ** 2) + 18
        out.append(_arc([(x, y), (x + 20, fringe_y - 24)], 5, _shade(fill)))
    out.append(_arc(_arc_points(cx, cy + 6, HEAD_RX - 26, HEAD_RY - 18, 285, 320, n=5), 9, _light(fill)))
    return out


def _hair_front(look: Look) -> list[Shape]:
    cx, cy = face(look)
    hair = look.hair_color
    if look.hair == "bald":
        return [_blob(f"{look.name}-shine", cx + 70, cy - 140, 52, 22, "#ffffff", n=10, edge=0, opacity=0.4)]
    if look.hair == "balding":
        out: list[Shape] = [
            _blob(f"{look.name}-shine", cx + 60, cy - 150, 56, 24, "#ffffff", n=10, edge=0, opacity=0.4)
        ]
        for side in (-1, 1):
            tuft = [
                (cx + side * 226, cy + 30),
                (cx + side * 236, cy - 70),
                (cx + side * 196, cy - 130),
                (cx + side * 174, cy - 60),
                (cx + side * 196, cy + 10),
            ]
            out.append(_cutout(f"{look.name}-tuft{side}", tuft, hair, 4.0))
        out.append(_arc(_curve(cx - 40, cx + 30, cy - HEAD_RY + 6, -14, n=5), 5, hair))  # the comb-over
        return out
    if look.hair == "beanie":
        dome = _arc_points(cx, cy - 10, HEAD_RX + 16, HEAD_RY + 26, 180, 360, n=13)
        out = [(_smooth(dome), hair, INK, EDGE, 1.0)]
        out.append(
            (
                _smooth(_crescent(cx, cy - 10, HEAD_RX + 16, HEAD_RY + 26, 30, 20, 190, 250)),
                _shade(hair),
                None,
                0.0,
                0.8,
            )
        )
        band = [
            (cx - HEAD_RX - 22, cy - 60),
            (cx + HEAD_RX + 22, cy - 60),
            (cx + HEAD_RX + 18, cy + BEANIE_BAND_BOTTOM),
            (cx - HEAD_RX - 18, cy + BEANIE_BAND_BOTTOM),
        ]
        out.append(_cutout(f"{look.name}-band", band, _shade(hair), 2.0))
        for i in range(12):
            x = cx - HEAD_RX - 4 + i * 38
            out.append(_arc([(x, cy - 52), (x, cy - 12)], 4, _mix(hair, INK, 0.45)))
        out.append(_blob(f"{look.name}-pom", cx, cy - HEAD_RY - 50, 38, 34, "#f2e9e4", n=12, amount=0.12))
        return out
    if look.hair == "curly":
        out = []
        for i, (x, y) in enumerate(_arc_points(cx, cy - 60, HEAD_RX - 40, HEAD_RY - 70, 190, 350, n=6)):
            out.append(_blob(f"{look.name}-top{i}", x, y, 44, 38, hair, n=10, amount=0.06))
            out.append(_arc(_arc_points(x, y + 4, 22, 16, 200, 340, n=5), 4, _light(hair)))
        return out
    depth = {"short": 70.0, "bun": 76.0, "ponytail": 86.0, "long": 96.0}[look.hair]
    return _cap(look, depth, "cap", hair, part=-0.35 if look.hair == "long" else 0.3)


def _accents_under(look: Look) -> list[Shape]:
    hw, sy = HALF_WIDTH[look.build], SHOULDER_Y[look.build]
    out: list[Shape] = []
    if "blazer" in look.accents:
        for side in (-1, 1):
            lapel = [
                (CX + side * 20, 1950),
                (CX + side * 30, sy - 4),
                (CX + side * (hw - 70), sy + 14),
                (CX + side * 104, sy + 210),
                (CX + side * 124, sy + 300),
                (CX + side * 56, 1950),
            ]
            out.append(_cutout(f"{look.name}-lapel{side}", lapel, _shade(look.top), 2.0, flat=True))
        out.append(
            _cutout(
                f"{look.name}-square",
                [
                    (CX + hw - 150, sy + 170),
                    (CX + hw - 90, sy + 160),
                    (CX + hw - 96, sy + 196),
                    (CX + hw - 146, sy + 200),
                ],
                "#e9c46a",
                2.0,
                3.0,
            )
        )
    if "tie" in look.accents:
        knot = [(CX - 22, sy + 16), (CX + 22, sy + 16), (CX + 16, sy + 54), (CX - 16, sy + 54)]
        tie = [(CX - 16, sy + 52), (CX + 16, sy + 52), (CX + 46, 1700), (CX, 1756), (CX - 46, 1700)]
        out.append((_poly(_cut(f"{look.name}-tie", tie, 2)), "#c1121f", INK, 4.5, 1.0))
        out.append(
            (
                _poly([(CX + 4, sy + 60), (CX + 16, sy + 60), (CX + 42, 1700), (CX + 10, 1730)]),
                "#8d0b16",
                None,
                0.0,
                0.8,
            )
        )
        out.append((_poly(_cut(f"{look.name}-knot", knot, 1.5)), "#9d0f1b", INK, 4.5, 1.0))
    if "pearls" in look.accents:
        for i, (x, y) in enumerate(_curve(CX - 124, CX + 124, sy + 8, 78, n=11)):
            out.append(_blob(f"{look.name}-pearl{i}", x, y, 14, 14, "#fbf6ec", n=8, amount=0.0, edge=3))
            out.append(_blob(f"{look.name}-pearl-lit{i}", x + 4, y - 5, 4, 4, "#ffffff", n=6, amount=0.0, edge=0))
    if "cane" in look.accents:
        x = CX - hw - 86
        out.append(_cutout(f"{look.name}-cane", _capsule((x, 1930), (x, 1560), 24), "#7f5539", 1.0))
        out.append((_smooth(_capsule((x - 4, 1920), (x - 4, 1580), 7)), "#b08968", None, 0.0, 1.0))
        out.append(_arc(_arc_points(x + 40, 1560, 40, 40, 180, 360, n=9), 24, INK))
        out.append(_arc(_arc_points(x + 40, 1560, 40, 40, 180, 360, n=9), 16, "#7f5539"))
    return out


def _accents_head(look: Look) -> list[Shape]:
    """What sits on the face, drawn over the mouth and the blinks: glasses, a moustache, a headset."""
    cx, cy = face(look)
    out: list[Shape] = []
    if "headset" in look.accents:
        out.append(_arc(_arc_points(cx, cy - 20, HEAD_RX + 30, HEAD_RY + 40, 190, 350, n=11), 22, INK))
        out.append(_arc(_arc_points(cx, cy - 20, HEAD_RX + 30, HEAD_RY + 40, 190, 350, n=11), 13, "#3d405b"))
        for side in (-1, 1):
            out.append(_blob(f"{look.name}-cup{side}", cx + side * (HEAD_RX + 14), cy + 8, 40, 60, "#3d405b", n=12))
            out.append(
                _blob(f"{look.name}-cup-lit{side}", cx + side * (HEAD_RX + 6), cy - 18, 12, 18, "#6d7196", n=8, edge=0)
            )
        out.append(_arc([(cx + HEAD_RX + 10, cy + 56), (cx + 170, cy + 140), (cx + 84, cy + 146)], 9, "#3d405b"))
        out.append(_blob(f"{look.name}-mic", cx + 78, cy + 146, 16, 12, INK, n=8, edge=0))
        out.append(
            _blob(f"{look.name}-led-glow", cx + HEAD_RX + 14, cy - 10, 24, 24, "#3ddc97", n=10, edge=0, opacity=0.35)
        )
        out.append(_blob(f"{look.name}-led", cx + HEAD_RX + 14, cy - 10, 9, 9, "#b7f7d8", n=8, edge=2))
    if "glasses" in look.accents:
        for side, (ex, ey) in zip((-1, 1), _eye_centres(look), strict=True):
            out.append(
                _blob(f"{look.name}-lens{side}", ex, ey, 66, 58, "#cde7ff", n=14, amount=0.0, edge=0, opacity=0.3)
            )
            out.append(_arc(_arc_points(ex + 16, ey - 14, 40, 34, 200, 250, n=4), 6, "#ffffff"))
            out.append(_arc(_arc_points(ex, ey, 66, 58, 0, 360, n=16), 8))
        out.append(_arc(_curve(cx - 2, cx + 2, cy - 26, -6, n=3), 8))
    if "moustache" in look.accents:
        mx, my = _mouth_centre(look)
        stache = [
            (mx - 92, my + 4),
            (mx - 60, my - 44),
            (mx - 14, my - 40),
            (mx, my - 30),
            (mx + 14, my - 40),
            (mx + 60, my - 44),
            (mx + 92, my + 4),
            (mx + 40, my - 14),
            (mx, my - 18),
            (mx - 40, my - 14),
        ]
        out.append(_cutout(f"{look.name}-stache", stache, look.hair_color, 1.5))
        out.append(_arc([(mx - 50, my - 32), (mx - 20, my - 34)], 4, _light(look.hair_color)))
    return out


def _rounded(x0: float, y0: float, x1: float, y1: float, r: float) -> list[Point]:
    """A rectangle with round corners as points, clockwise from the top left."""
    return (
        _arc_points(x0 + r, y0 + r, r, r, 180, 270, n=5)
        + _arc_points(x1 - r, y0 + r, r, r, 270, 360, n=5)
        + _arc_points(x1 - r, y1 - r, r, r, 0, 90, n=5)
        + _arc_points(x0 + r, y1 - r, r, r, 90, 180, n=5)
    )


RIM_Y = 1392.0  # the toilet rim's centre: Flush's chin is under its water line
PORCELAIN_EDGE = "#6b7785"


def _toilet_back(look: Look) -> list[Shape]:
    """The tank and the back of the bowl behind Flush's head: glossy porcelain, water in the bowl."""
    e = PORCELAIN_EDGE
    return [
        (_poly(_rounded(292, 960, 788, 1370, 34)), "url(#collage-porcelain-side)", e, 5.0, 1.0),
        (_poly(_rounded(270, 916, 810, 980, 26)), "url(#collage-porcelain)", e, 5.0, 1.0),
        (_poly(_rounded(320, 1000, 360, 1330, 18)), "#ffffff", None, 0.0, 0.55),
        (_smooth(_capsule((300, 1010), (234, 1022), 24)), "url(#collage-chrome)", e, 3.0, 1.0),
        (
            _smooth(_ring(f"{look.name}-rim", CX, RIM_Y, 360, 104, n=24, amount=0.0)),
            "url(#collage-porcelain)",
            e,
            5.0,
            1.0,
        ),
        (
            _smooth(_ring(f"{look.name}-water", CX, RIM_Y, 300, 72, n=20, amount=0.0)),
            "url(#collage-water)",
            None,
            0.0,
            1.0,
        ),
    ]


def _toilet_front(look: Look) -> list[Shape]:
    """The water's near half over Flush's chin, the front of the rim and the bowl, with its gloss."""
    e = PORCELAIN_EDGE
    water = _arc_points(CX, RIM_Y, 300, 72, 0, 180, n=12)
    front_rim = _arc_points(CX, RIM_Y, 360, 104, 0, 180, n=14)
    inner = _arc_points(CX, RIM_Y, 300, 72, 180, 0, n=12)
    bowl = [
        (CX - 170, 1950),
        (CX - 200, 1860),
        (CX - 310, 1640),
        (CX - 352, RIM_Y + 20),
        (CX - 200, RIM_Y + 10),
        (CX + 200, RIM_Y + 10),
        (CX + 352, RIM_Y + 20),
        (CX + 310, 1640),
        (CX + 200, 1860),
        (CX + 170, 1950),
    ]
    return [
        (_poly(water), "#5aaedc", None, 0.0, 0.8),
        (
            _smooth(_ring(f"{look.name}-ripple", CX, RIM_Y + 4, 236, 44, n=16, amount=0.02)),
            "#00000000",
            "#e6f7ff",
            5.0,
            0.8,
        ),
        (_sheet(bowl), "url(#collage-porcelain)", e, 5.0, 1.0),
        (_poly(front_rim + inner), "url(#collage-porcelain)", e, 5.0, 1.0),
        (
            _smooth(_ring(f"{look.name}-bowl-gloss", CX - 190, 1620, 30, 110, n=10, amount=0.0)),
            "url(#collage-gloss)",
            None,
            0.0,
            0.95,
        ),
        (
            _smooth(_ring(f"{look.name}-rim-gloss", CX - 150, RIM_Y + 76, 80, 12, n=10, amount=0.0)),
            "url(#collage-gloss)",
            None,
            0.0,
            0.9,
        ),
    ]


def figure_shapes(look: Look, eyes: str, mouth: str, arms: str) -> tuple[list[Shape], list[Shape], list[Shape]]:
    """The whole character in one pose as data: the layers under the mouth, the mouth, the layers over it."""
    if eyes not in EYES:
        raise CollageError(f"eyes {eyes!r} is not one of {EYES}")
    if arms not in ARMS:
        raise CollageError(f"arms {arms!r} is not one of {ARMS}")
    cx, cy = face(look)
    arms_under, arms_over = _arms(look, arms)
    under: list[Shape] = []
    if look.toilet:
        under += _toilet_back(look)
    if "hoodie" in look.accents:
        hood = [
            (cx - 270, cy + 260),
            (cx - 280, cy - 20),
            (cx - 190, cy - 210),
            (cx, cy - 250),
            (cx + 190, cy - 210),
            (cx + 280, cy - 20),
            (cx + 270, cy + 260),
        ]
        under.append(_cutout(f"{look.name}-hood", hood, _shade(look.top), 4.0))
    under += _hair_back(look)
    if not look.toilet:
        under += _neck(look) + _torso(look) + _accents_under(look) + arms_under
    under += _head(look)
    under += _eyes(look, eyes)
    under += _hair_front(look)
    over = _accents_head(look) + arms_over
    if look.toilet:
        over += _toilet_front(look)
    return under, _mouth(look, mouth), over


# -- on a canvas ------------------------------------------------------------------------------------------------------
def _paint(cv: Canvas, fill: str) -> str:
    if fill.startswith("url(#"):
        name = fill[5:-1]
        if name not in PAINTS:
            raise CollageError(f"no paint {name!r}; one of {sorted(PAINTS)}")
        kind, stops, geometry = PAINTS[name]
        if kind == "radial":
            return cv.rgrad(name, list(stops), geometry)
        return cv.grad(name, list(stops), geometry)
    return fill


def draw_shapes(cv: Canvas, parent, shapes: Sequence[Shape]) -> None:
    """Put shapes from :func:`figure_shapes` (or any ``(d, fill, stroke, width, opacity)``) on the canvas."""
    for d, fill, stroke, width, opacity in shapes:
        kw = {} if opacity == 1 else {"opacity": opacity}
        cv.path(parent, d, fill=_paint(cv, fill), stroke=cv.clear if stroke is None else stroke, sw=width, **kw)


def _breathe(cv: Canvas, g, start: float, end: float) -> None:
    """A slow rise and fall over a pose run, so a held pose is never a still."""
    half = BREATH_PERIOD / 2
    n = int((end - start) / half)
    states = [(round(start + i * half, 6), 0.0 if i % 2 == 0 else -BREATH) for i in range(n + 1)]
    cv.keys(g, "y", states, kind="sine-in-out", local=False)


def figure(
    cv: Canvas,
    parent,
    look: Look,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Any] = (),
    mouths: Mouths = (),
    still: bool = False,
    lids_under_band: bool = False,
) -> list:
    """One group per pose run, on from project second ``enter`` until ``duration``. ``mouths`` is the lip-sync
    track (``(project second, viseme)``): the mouth becomes one layer per viseme with hold keys inside each run, the
    pose's own mouth showing while closed. The eyes shut for :data:`srstudio.toon_cast.BLINK_HOLD` at the look's
    pace. A ``still`` figure keys nothing: no breath, no blink and the pose's own mouth, for an opening whose
    picture must not change (ADR 0036). ``lids_under_band`` is :func:`lid_shapes`' ``under_band``. ``taps`` and
    ``stickers`` are part of the drawer contract; the Collage cast types on no keyboard."""
    if not (checks.number(enter) and 0 <= enter < duration):
        raise CollageError(f"{look.name}: enter must be a project second before the end, got {enter!r}")
    groups = []
    for pose, start, end in runs(poses, duration - enter):
        start, end = round(start + enter, 6), round(end + enter, 6)
        g = cv.group(parent, cv.uid("g"), start=start, end=end)
        cv.apply(g, cv.effect("collage-figure-shadow", "drop-shadow", **FIGURE_SHADOW))
        if not still:
            _breathe(cv, g, start, end)
        under, mouth_shapes, over = figure_shapes(look, pose.eyes, pose.mouth, pose.arms)
        draw_shapes(cv, g, under)
        keys = {} if still else viseme_keys(mouths, start, end)
        if keys:
            lips = cv.group(g, cv.uid("g"))
            for viseme, states in keys.items():
                layer = cv.group(lips, cv.uid("g"))
                draw_shapes(cv, layer, mouth_shapes if viseme == "closed" else viseme_shapes(look, viseme))
                cv.keys(layer, "opacity", states, local=False)
        else:
            draw_shapes(cv, g, mouth_shapes)
        blinks = blink_times(start, end, look.blink) if pose.eyes != "closed" and not still else []
        if blinks:
            shut = cv.group(g, cv.uid("g"))
            draw_shapes(cv, shut, lid_shapes(look, lids_under_band))
            states = [(start, 0)]
            for t in blinks:
                states += [(t, 1), (round(t + BLINK_HOLD, 6), 0)]
            cv.keys(shut, "opacity", states, local=False)
        draw_shapes(cv, g, over)
        groups.append(g)
    return groups


Drawer = Callable[..., list]


def _drawer(look: Look) -> Drawer:
    def draw(
        cv: Canvas,
        parent,
        poses: Sequence[Pose],
        duration: float,
        taps: Sequence[float] = (),
        enter: float = 0.0,
        stickers: Sequence[Any] = (),
        mouths: Mouths = (),
        still: bool = False,
        lids_under_band: bool = False,
    ) -> list:
        return figure(cv, parent, look, poses, duration, taps, enter, stickers, mouths, still, lids_under_band)

    draw.__name__ = draw.__qualname__ = look.name
    draw.__doc__ = look.summary
    return register("character", f"collage-{look.name}", summary=look.summary)(draw)


DRAWERS: dict[str, Drawer] = {name: _drawer(look) for name, look in LOOKS.items()}


# -- captions ---------------------------------------------------------------------------------------------------------
def caption_lines(measure: Callable[[str], float], text: str, width: float, *, sentences: bool = False) -> list[str]:
    """``text`` as one caption line, or as the two most even lines, every one fitting a pill inside the frame's
    margins; :class:`CollageError` when a word alone is too wide or two lines are not enough. With ``sentences`` the
    break falls at a sentence end whenever one fits, so a row never starts a sentence it cannot finish."""
    room = width - 2 * CAPTION_MARGIN - CAPTION_PAD
    words = text.split()
    too_wide = [w for w in words if measure(w) > room]
    if too_wide:
        raise CollageError(f"caption word {too_wide[0]!r} is wider than the frame allows")
    if measure(text) <= room:
        return [text]
    splits: list[tuple[float, str, str]] = []
    for i in range(1, len(words)):
        first, second = " ".join(words[:i]), " ".join(words[i:])
        widest = max(measure(first), measure(second))
        if widest <= room:
            splits.append((widest, first, second))
    if not splits:
        raise CollageError(f"caption {text!r} does not fit in two lines: split the beat")
    ends = [split for split in splits if split[1].endswith((".", "?", "!"))] if sentences else []
    _, first, second = min(ends or splits, key=lambda split: split[0])
    return [first, second]


def captions(
    cv: Canvas,
    parent,
    lines: Sequence[Line],
    measure: Callable[[str], float],
    tints: Mapping[str, str] | None = None,
    *,
    sentences: bool = False,
    tops: Mapping[str, float] | None = None,
) -> None:
    """One pill per cue, centred under :data:`CAPTION_TOP`, one or two lines (:func:`caption_lines`), sized by
    ``measure(text)`` (the advance width at :data:`CAPTION_SIZE`), tinted by speaker (paper white otherwise).
    ``tops`` moves the pill of a cue, by its text, for a shot whose picture the usual place would cover."""
    cv.require_font("the Collage style letters its captions in its font", CollageError)
    for line in lines:
        rows = caption_lines(measure, line.text, cv.width, sentences=sentences)
        g = cv.group(parent, cv.uid("g"), start=line.start, end=line.end)
        cv.apply(g, cv.effect("collage-caption-shadow", "drop-shadow", **CAPTION_SHADOW))
        width = round(max(measure(r) for r in rows) + CAPTION_PAD, 2)
        height = len(rows) * CAPTION_LEADING + 2 * CAPTION_PAD_Y
        fill = (tints or {}).get(line.speaker, cv.white)
        x = round(cv.width / 2 - width / 2, 2)
        pill = (tops or {}).get(line.text, CAPTION_TOP)
        cv.rect(g, x, pill, width, height, fill, INK, EDGE, radius=CAPTION_RADIUS)
        for i, row in enumerate(rows):
            top = pill + CAPTION_PAD_Y + i * CAPTION_LEADING
            cv.text(g, cv.uid("caption"), row, 0, top, cv.width, CAPTION_LEADING, CAPTION_SIZE, color=INK, wrap="none")
