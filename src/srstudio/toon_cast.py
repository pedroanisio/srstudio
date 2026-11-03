"""More Toon characters, drawn with the brush: a dog, a frog, a bear, a rabbit, a fox, a raccoon and a hedgehog at
the cat's desk.

The Toon cat is traced from its reference; these four are drawn in code with :mod:`srstudio.brush`, in the same
reference pixels (:func:`srstudio.toon.fx`/``fy``), with the same vocabulary of expressions (:data:`EYES`,
:data:`MOUTHS`, :data:`ARMS` of :mod:`srstudio.toon`) and the same contract: one group per pose run, a typing pose
that swaps two frames on the keystrokes it contains. A pose file written for the cat poses any of them.

Every line is a filled brush shape, never a stroke: the ink band under the body fill (:func:`brush.rim`), the limbs
as tapered strokes in ink under strokes in the coat colour, lids as coat-coloured shapes with an inked edge. What
differs per character is a :class:`Look`: the silhouette, the coat colours, where the eyes and the mouth sit, the
parts only it has (the dog's floppy ears, snout and nose; the frog's eye bumps, belly, nostrils and spots; the
bear's round ears and muzzle; the rabbit's tall ears, whiskers and front teeth; the fox's tall ears and white cheek
tufts; the raccoon's mask, white-rimmed ears and dark gloves; the hedgehog's spines) and its polish: eyebrows that
follow the eyes, a highlight on each pupil, blushing cheeks and blinks at its own pace.

**Lip sync.** A character speaks through :data:`VISEMES`: ``closed`` is the pose's own mouth (a smirk stays a
smirk between syllables), ``open``, ``round`` and ``teeth`` replace it while a sound is heard. :func:`figure` takes
the viseme track as ``(project second, viseme)`` states (:func:`srstudio.sketch.visemes` derives them from the
voice's character timestamps) and draws the mouth as one layer per viseme with hold keys, inside each pose run, so
the lips move while the expression holds.

:func:`figure_shapes` is the whole drawing as data (shape, colour) in reference pixels, so a test can measure it
without a canvas; :func:`dog`, :func:`frog`, :func:`bear`, :func:`rabbit`, :func:`fox`, :func:`raccoon` and
:func:`hedgehog` put it on one.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from . import _character_contracts as cc
from . import _toon_contracts as tc
from . import anatomy_ledger, brush, checks
from .anatomy import Side
from .brush import Point, Shape
from .canvas import Canvas
from .registry import register
from .toon import (
    ARMS,
    EPSILON,
    EYES,
    LIPS,
    MOUTHS,
    REF_TOP,
    SCALE,
    WEAR,
    Pose,
    ToonDataError,
    flat,
    fx,
    fy,
    runs,
    swap_frames,
)

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "Look",
    "Drawing",
    "DOG",
    "FROG",
    "BEAR",
    "RABBIT",
    "FOX",
    "RACCOON",
    "HEDGEHOG",
    "LOOKS",
    "INK",
    "VISEMES",
    "BLINK_HOLD",
    "SLEEPY_PACE",
    "SLEEPY_HOLD",
    "SHUT",
    "Posing",
    "Ramp",
    "TEAR",
    "HEART",
    "TONGUE",
    "figure_layers",
    "figure_shapes",
    "viseme_keys",
    "blink_times",
    "figure",
    "dog",
    "frog",
    "bear",
    "rabbit",
    "fox",
    "raccoon",
    "hedgehog",
]

INK = 5.5  # the brush's weight: the reference's line, reference pixels
FINE = 3.0
CENTRE = 185.0  # the character's axis
PIVOT = (CENTRE, 812.0)  # where a lean turns about: the seat, under the desk's edge
LEAN_DEGREES = 7.0
SIGH_DROP = 10.0
SHOULDERS: tuple[Point, Point] = ((62.0, 712.0), (308.0, 712.0))
# The desk arms past the shoulders, screen-left then screen-right: the elbow, the wrist and the paw on the desk's edge.
DESK: tuple[tuple[Point, Point, Point], tuple[Point, Point, Point]] = (
    ((82.0, 760.0), (124.0, 792.0), (132.0, 794.0)),
    ((288.0, 760.0), (246.0, 792.0), (238.0, 794.0)),
)
VISEMES = ("closed", "open", "round", "teeth")  # the lip-sync mouths; closed is the pose's own mouth
BLINK_HOLD = 0.12  # seconds the lids stay down in a blink
BLINK_PHASE = 0.55  # the first blink of a pose comes this fraction of the period after it starts
SLEEPY_PACE = 1.8  # sleepy eyes blink this many times slower than the look's own pace
SLEEPY_HOLD = 0.34  # and keep their lids down this long, seconds
SHUT = ("closed", "wince", "hearts")  # eyes with nothing to blink: no lids come down over them
TEAR = "#8fd0f5"
HEART = "#e2364b"
TONGUE = "#e8798c"
Layer = tuple[Shape, str]  # a shape and its colour: "ink" and "white" are the palette's, the rest literal
Mouths = Sequence[tuple[float, str]]  # (project second, viseme) states, in time order


class Drawing(Protocol):
    """A look's own drawing in place of the shared brush parts: its body and ears at rest (with the marks, shading
    and inner lines), one eye of each kind, the blink lids, the mouths, the visemes and an arm, every one as layers
    in reference pixels. :func:`figure_layers` and :func:`figure` call it wherever the shared parts would draw, so
    a look with a drawing keeps the whole contract (:mod:`srstudio.toon_inked`). ``tilt`` is how many degrees
    clockwise the drawing turns the head, so what the look wears turns with it (:mod:`srstudio.toon_wear`)."""

    @property
    def tilt(self) -> float: ...

    def foundation(self, look: Look) -> list[Layer]: ...

    def eye(self, look: Look, centre: Point, kind: str, inner: float) -> list[Layer]: ...

    def lids(self, look: Look) -> list[Layer]: ...

    def mouth(self, look: Look, kind: str) -> list[Layer]: ...

    def viseme(self, look: Look, kind: str) -> list[Layer]: ...

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]: ...


@runtime_checkable
class Posing(Protocol):
    """A drawing with poses of its own beyond the shared kinds. ``gesture`` is the arms of a kind it draws itself, as
    :func:`_arms` returns them, or ``None`` for a shared kind; it refuses a kind it does not know. ``shut`` says eyes
    of that kind have nothing to blink."""

    def gesture(self, arms: str) -> tuple[list[Layer], list[Layer]] | None: ...

    def shut(self, eyes: str) -> bool: ...


class Ramp(str):
    """A layer's colour that is a gradient: the string is the flat colour it averages to, for anything that reads a
    colour, and :func:`_draw` paints the ramp itself. ``box`` is ``(x0, y0, x1, y1)`` in reference pixels, the line
    the ``stops`` run along, the same whatever the shape, so two shapes of one ramp meet with no edge."""

    name: str
    stops: tuple[tuple[float, str], ...]
    box: tuple[float, float, float, float]

    def __new__(
        cls, colour: str, name: str, stops: Sequence[tuple[float, str]], box: tuple[float, float, float, float]
    ) -> Ramp:
        ramp = super().__new__(cls, colour)
        ramp.name, ramp.stops, ramp.box = name, tuple(stops), box
        return ramp

    def paint(self, cv: Canvas) -> str:
        """The ``url(#name)`` of this ramp, declared the first time it is asked for."""
        x0, y0, x1, y1 = self.box
        return cv.grad(self.name, self.stops, (fx(x0), fy(y0), fx(x1), fy(y1)), units="user")


@dataclass(frozen=True)
class Look:
    """One character: its silhouette (head running into the body, closed, at rest), coat colours, where its face
    is, and its polish. ``ears`` are drawn behind the body, ``marks`` (light patches, spots) over it, both at rest;
    ``ear`` and ``ear_inner`` colour the ears (the dark coat and nothing by default). ``brows`` adds eyebrows that
    follow the eyes, ``shine`` a highlight on each pupil, ``blush`` cheeks in that colour, ``teeth`` two front
    teeth under the mouth, ``whiskers`` three a side; ``blink`` is the seconds between blinks (0: never).
    ``mantle`` is an outline drawn behind the ears and the body in the dark coat (the hedgehog's spines), ``paw``
    the paws' colour when not the coat (the raccoon's gloves). ``drawing`` replaces the shared brush parts with the
    look's own (:class:`Drawing`); without one the look is drawn from its fields."""

    name: str
    coat: str
    dark: str
    light: str
    silhouette: tuple[Point, ...]
    eyes: tuple[Point, Point]
    eye_r: float
    mouth: Point
    mouth_w: float
    limb: float
    ears: tuple[tuple[Point, ...], ...] = ()
    marks: tuple[tuple[Shape, str], ...] = ()
    nose: tuple[Shape, ...] = ()
    lid: str = ""  # the lids' colour when not the coat (the frog's bumps)
    ear: str = ""
    ear_inner: str = ""
    brows: bool = False
    shine: bool = False
    blush: str = ""
    teeth: bool = False
    whiskers: bool = False
    blink: float = 0.0
    mantle: tuple[Point, ...] = ()
    paw: str = ""
    drawing: Drawing | None = None


def _mirror(points: Sequence[Point]) -> tuple[Point, ...]:
    return tuple((round(2 * CENTRE - x, 2), y) for x, y in points)


def _ring(cx: float, cy: float, r: float, n: int = 12) -> tuple[Point, ...]:
    """A circle as control points for the brush (an ear)."""
    return tuple(
        (round(cx + r * math.cos(2 * math.pi * k / n), 2), round(cy + r * math.sin(2 * math.pi * k / n), 2))
        for k in range(n)
    )


def _shrink(points: Sequence[Point], factor: float) -> tuple[Point, ...]:
    """The outline pulled toward its centroid (an inner ear)."""
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    return tuple((round(cx + (x - cx) * factor, 2), round(cy + (y - cy) * factor, 2)) for x, y in points)


_DOG_EAR = (
    (72.0, 478.0),
    (40.0, 516.0),
    (22.0, 588.0),
    (30.0, 652.0),
    (62.0, 676.0),
    (90.0, 652.0),
    (94.0, 580.0),
    (92.0, 508.0),
)
DOG = Look(
    name="dog",
    coat="#f0a35c",
    dark="#c97a3a",
    light="#fbe0b8",
    silhouette=(
        (82.0, 470.0),
        (130.0, 456.0),
        (185.0, 452.0),
        (240.0, 456.0),
        (288.0, 470.0),
        (312.0, 520.0),
        (314.0, 590.0),
        (302.0, 642.0),
        (278.0, 672.0),
        (316.0, 700.0),
        (336.0, 760.0),
        (340.0, 830.0),
        (30.0, 830.0),
        (34.0, 760.0),
        (54.0, 700.0),
        (92.0, 672.0),
        (68.0, 642.0),
        (56.0, 590.0),
        (58.0, 520.0),
    ),
    eyes=((150.0, 574.0), (222.0, 574.0)),
    eye_r=20.0,
    mouth=(185.0, 652.0),
    mouth_w=52.0,
    limb=34.0,
    ears=(_DOG_EAR, _mirror(_DOG_EAR)),
    marks=((brush.ellipse(185.0, 630.0, 58.0, 40.0), "#fbe0b8"),),
    nose=(brush.ellipse(185.0, 606.0, 17.0, 12.0), brush.ellipse(179.0, 602.0, 4.0, 2.5)),
)

FROG = Look(
    name="frog",
    coat="#7fcf6b",
    dark="#4f9a46",
    light="#dcf3b0",
    silhouette=(
        (60.0, 560.0),
        (70.0, 520.0),
        (98.0, 488.0),
        (124.0, 468.0),
        (152.0, 476.0),
        (170.0, 504.0),
        (185.0, 512.0),
        (200.0, 504.0),
        (218.0, 476.0),
        (246.0, 468.0),
        (272.0, 488.0),
        (300.0, 520.0),
        (312.0, 560.0),
        (318.0, 612.0),
        (306.0, 662.0),
        (302.0, 700.0),
        (330.0, 760.0),
        (338.0, 830.0),
        (32.0, 830.0),
        (40.0, 760.0),
        (68.0, 700.0),
        (64.0, 662.0),
        (52.0, 612.0),
    ),
    eyes=((136.0, 500.0), (234.0, 500.0)),
    eye_r=24.0,
    mouth=(185.0, 600.0),
    mouth_w=110.0,
    limb=30.0,
    marks=(
        (brush.ellipse(185.0, 748.0, 96.0, 82.0), "#dcf3b0"),
        (brush.ellipse(92.0, 604.0, 9.0, 7.0, 20.0), "#4f9a46"),
        (brush.ellipse(282.0, 596.0, 7.0, 6.0, -15.0), "#4f9a46"),
        (brush.ellipse(262.0, 650.0, 5.0, 4.0), "#4f9a46"),
        (brush.ellipse(172.0, 562.0, 3.5, 3.5), "ink"),
        (brush.ellipse(198.0, 562.0, 3.5, 3.5), "ink"),
    ),
)

_BEAR_EAR = _ring(98.0, 464.0, 29.0)
BEAR = Look(
    name="bear",
    coat="#a9744f",
    dark="#7a4f32",
    light="#eccfae",
    silhouette=(
        (78.0, 482.0),
        (110.0, 452.0),
        (150.0, 440.0),
        (185.0, 437.0),
        (220.0, 440.0),
        (260.0, 452.0),
        (292.0, 482.0),
        (312.0, 532.0),
        (314.0, 594.0),
        (300.0, 646.0),
        (278.0, 674.0),
        (316.0, 702.0),
        (336.0, 760.0),
        (340.0, 830.0),
        (30.0, 830.0),
        (34.0, 760.0),
        (54.0, 702.0),
        (92.0, 674.0),
        (70.0, 646.0),
        (56.0, 594.0),
        (58.0, 532.0),
    ),
    eyes=((152.0, 572.0), (218.0, 572.0)),
    eye_r=15.0,
    mouth=(185.0, 656.0),
    mouth_w=44.0,
    limb=36.0,
    ears=(_BEAR_EAR, _mirror(_BEAR_EAR)),
    marks=((brush.ellipse(185.0, 638.0, 54.0, 40.0), "#eccfae"), (brush.ellipse(185.0, 756.0, 88.0, 70.0), "#bf8a62")),
    nose=(brush.ellipse(185.0, 620.0, 16.0, 11.0), brush.ellipse(179.0, 616.0, 4.0, 2.5)),
    ear="#a9744f",
    ear_inner="#eccfae",
    brows=True,
    shine=True,
    blush="#c67b5b",
    blink=3.4,
)

_RABBIT_EAR = (
    (112.0, 494.0),
    (104.0, 442.0),
    (100.0, 400.0),
    (112.0, 376.0),
    (130.0, 380.0),
    (146.0, 410.0),
    (156.0, 452.0),
    (158.0, 488.0),
)
RABBIT = Look(
    name="rabbit",
    coat="#efe8ee",
    dark="#cdbfca",
    light="#f9c9d8",
    silhouette=(
        (96.0, 488.0),
        (120.0, 462.0),
        (152.0, 450.0),
        (185.0, 447.0),
        (218.0, 450.0),
        (250.0, 462.0),
        (274.0, 488.0),
        (296.0, 536.0),
        (302.0, 598.0),
        (292.0, 648.0),
        (272.0, 674.0),
        (312.0, 702.0),
        (334.0, 760.0),
        (338.0, 830.0),
        (32.0, 830.0),
        (36.0, 760.0),
        (58.0, 702.0),
        (98.0, 674.0),
        (78.0, 648.0),
        (68.0, 598.0),
        (74.0, 536.0),
    ),
    eyes=((150.0, 556.0), (220.0, 556.0)),
    eye_r=19.0,
    mouth=(185.0, 618.0),
    mouth_w=36.0,
    limb=30.0,
    ears=(_RABBIT_EAR, _mirror(_RABBIT_EAR)),
    marks=((brush.ellipse(185.0, 756.0, 86.0, 70.0), "#faf5f8"), (brush.ellipse(185.0, 600.0, 8.0, 5.5), "#f28fae")),
    ear="#efe8ee",
    ear_inner="#f9c9d8",
    brows=True,
    shine=True,
    blush="#f4b3c4",
    teeth=True,
    whiskers=True,
    blink=2.6,
)
_FOX_EAR = ((96.0, 546.0), (76.0, 496.0), (56.0, 440.0), (44.0, 402.0), (80.0, 410.0), (128.0, 446.0), (166.0, 488.0))
FOX = Look(
    name="fox",
    coat="#e2672c",
    dark="#a8461b",
    light="#fff4e8",
    silhouette=(
        (104.0, 504.0),
        (142.0, 488.0),
        (185.0, 484.0),
        (228.0, 488.0),
        (266.0, 504.0),
        (290.0, 544.0),
        (306.0, 588.0),
        (338.0, 622.0),
        (300.0, 634.0),
        (322.0, 652.0),
        (276.0, 662.0),
        (256.0, 680.0),
        (306.0, 704.0),
        (326.0, 760.0),
        (330.0, 830.0),
        (40.0, 830.0),
        (44.0, 760.0),
        (64.0, 704.0),
        (114.0, 680.0),
        (94.0, 662.0),
        (48.0, 652.0),
        (70.0, 634.0),
        (32.0, 622.0),
        (64.0, 588.0),
        (80.0, 544.0),
    ),
    eyes=((150.0, 566.0), (220.0, 566.0)),
    eye_r=17.0,
    mouth=(185.0, 646.0),
    mouth_w=40.0,
    limb=30.0,
    ears=(_FOX_EAR, _mirror(_FOX_EAR)),
    marks=(
        (  # the white cheeks and chin, tufted at the sides, the mouth on them
            brush.outline(
                [
                    (62.0, 624.0),
                    (100.0, 608.0),
                    (142.0, 604.0),
                    (185.0, 620.0),
                    (228.0, 604.0),
                    (270.0, 608.0),
                    (308.0, 624.0),
                    (286.0, 646.0),
                    (250.0, 670.0),
                    (185.0, 684.0),
                    (120.0, 670.0),
                    (84.0, 646.0),
                ]
            ),
            "#fff4e8",
        ),
        (brush.ellipse(185.0, 764.0, 66.0, 60.0), "#fff4e8"),
    ),
    nose=(brush.ellipse(185.0, 622.0, 12.0, 8.5), brush.ellipse(180.0, 619.0, 3.5, 2.2)),
    ear="#e2672c",
    ear_inner="#fff4e8",
    brows=True,
    shine=True,
    blink=3.8,
    paw="#5a2e1e",
)

_RACCOON_EAR = ((122.0, 500.0), (116.0, 462.0), (126.0, 432.0), (148.0, 428.0), (166.0, 450.0), (170.0, 486.0))
RACCOON_MASK = "#33373c"
RACCOON = Look(
    name="raccoon",
    coat="#8f969e",
    dark="#5b6168",
    light="#eceae4",
    silhouette=(
        (118.0, 502.0),
        (150.0, 486.0),
        (185.0, 482.0),
        (220.0, 486.0),
        (252.0, 502.0),
        (280.0, 534.0),
        (302.0, 568.0),
        (330.0, 596.0),
        (316.0, 606.0),
        (352.0, 622.0),
        (328.0, 634.0),
        (360.0, 652.0),
        (318.0, 660.0),
        (300.0, 670.0),
        (328.0, 700.0),
        (348.0, 760.0),
        (352.0, 830.0),
        (18.0, 830.0),
        (22.0, 760.0),
        (42.0, 700.0),
        (70.0, 670.0),
        (52.0, 660.0),
        (10.0, 652.0),
        (42.0, 634.0),
        (18.0, 622.0),
        (54.0, 606.0),
        (40.0, 596.0),
        (68.0, 568.0),
        (90.0, 534.0),
    ),
    eyes=((146.0, 572.0), (224.0, 572.0)),
    eye_r=18.0,
    mouth=(185.0, 652.0),
    mouth_w=46.0,
    limb=38.0,
    ears=(_RACCOON_EAR, _mirror(_RACCOON_EAR)),
    marks=(
        (  # the pale muzzle and cheeks under the mask
            brush.outline(
                [
                    (68.0, 610.0),
                    (108.0, 598.0),
                    (185.0, 606.0),
                    (262.0, 598.0),
                    (302.0, 610.0),
                    (304.0, 640.0),
                    (270.0, 668.0),
                    (185.0, 680.0),
                    (100.0, 668.0),
                    (66.0, 640.0),
                ]
            ),
            "#eceae4",
        ),
        (  # the bandit's mask across both eyes, dipping at the nose
            brush.outline(
                [
                    (78.0, 566.0),
                    (104.0, 546.0),
                    (148.0, 548.0),
                    (185.0, 566.0),
                    (222.0, 548.0),
                    (266.0, 546.0),
                    (292.0, 566.0),
                    (292.0, 600.0),
                    (258.0, 608.0),
                    (214.0, 596.0),
                    (185.0, 602.0),
                    (156.0, 596.0),
                    (112.0, 608.0),
                    (78.0, 600.0),
                ]
            ),
            RACCOON_MASK,
        ),
        (brush.ellipse(185.0, 762.0, 92.0, 68.0), "#b9bec4"),
    ),
    nose=(brush.ellipse(185.0, 618.0, 15.0, 10.0), brush.ellipse(179.0, 614.0, 4.0, 2.5)),
    lid=RACCOON_MASK,
    ear="#eceae4",
    ear_inner="#4b5158",
    shine=True,
    blink=3.0,
    paw="#25282c",
)


def _spines(cx: float, cy: float, n: int) -> tuple[Point, ...]:
    """A crest of ``n`` spines round the head from lower left to lower right, longest over the crown and short at the
    sides, closed behind the shoulders."""
    out: list[Point] = []
    for k in range(2 * n + 1):
        angle = math.radians(200.0 - 220.0 * k / (2 * n))
        up = math.sin(angle)  # 1 over the crown, below 0 under the sides
        r = 118.0 + 72.0 * max(up, 0.0) ** 1.5 if k % 2 else 100.0 + 8.0 * up
        out.append((round(cx + r * math.cos(angle), 2), round(cy - r * math.sin(angle), 2)))
    return (*out, (300.0, 700.0), (70.0, 700.0))


HEDGEHOG = Look(
    name="hedgehog",
    coat="#e8c79c",
    dark="#6a4a3c",
    light="#f7e6cc",
    silhouette=(
        (98.0, 546.0),
        (132.0, 520.0),
        (185.0, 512.0),
        (238.0, 520.0),
        (272.0, 546.0),
        (290.0, 588.0),
        (292.0, 628.0),
        (280.0, 658.0),
        (262.0, 680.0),
        (304.0, 706.0),
        (326.0, 764.0),
        (330.0, 830.0),
        (40.0, 830.0),
        (44.0, 764.0),
        (66.0, 706.0),
        (108.0, 680.0),
        (90.0, 658.0),
        (78.0, 628.0),
        (80.0, 588.0),
    ),
    eyes=((154.0, 592.0), (216.0, 592.0)),
    eye_r=13.0,
    mouth=(185.0, 652.0),
    mouth_w=34.0,
    limb=28.0,
    ears=(_ring(104.0, 548.0, 16.0), _mirror(_ring(104.0, 548.0, 16.0))),
    marks=((brush.ellipse(185.0, 636.0, 44.0, 30.0), "#f7e6cc"), (brush.ellipse(185.0, 764.0, 82.0, 64.0), "#f7e6cc")),
    nose=(brush.ellipse(185.0, 624.0, 12.0, 10.0), brush.ellipse(181.0, 620.0, 3.5, 2.5)),
    ear="#e8c79c",
    ear_inner="#d99a86",
    brows=True,
    shine=True,
    blush="#f2a0a0",
    blink=2.2,
    mantle=_spines(185.0, 612.0, 11),
)
LOOKS = {"dog": DOG, "frog": FROG, "bear": BEAR, "rabbit": RABBIT, "fox": FOX, "raccoon": RACCOON, "hedgehog": HEDGEHOG}
BEAR_BROW = (
    24  # the index of the bear's left brow in figure_shapes(BEAR, ..., "desk"): after ears, body, marks, blush, arms
)


# -- pieces ---------------------------------------------------------------------------------------------------------
def _limb(points: Sequence[Point], look: Look, paw: Point, toes: bool = True) -> list[Layer]:
    """An arm from the shoulder to the paw: an ink stroke under a coat stroke, the paw a rimmed oval with toes."""
    if look.drawing is not None:
        return look.drawing.limb(points, look, paw, toes)
    out: list[Layer] = [
        (brush.stroke(points, look.limb + 2 * INK, brush.EVEN), "ink"),
        (brush.stroke(points, look.limb, brush.EVEN), look.coat),
        (brush.ellipse(paw[0], paw[1], look.limb * 0.72 + INK, look.limb * 0.5 + INK), "ink"),
        (brush.ellipse(paw[0], paw[1], look.limb * 0.72, look.limb * 0.5), look.paw or look.coat),
    ]
    if toes:
        for dx in (-look.limb * 0.22, look.limb * 0.22):
            x = paw[0] + dx
            out.append((brush.stroke([(x, paw[1] - look.limb * 0.46), (x, paw[1] - look.limb * 0.12)], FINE), "ink"))
    return out


def _arms(
    look: Look, arms: str, frame: int, omit_arms: frozenset[str] = frozenset()
) -> tuple[list[Layer], list[Layer]]:
    """The arms of a pose at rest: those drawn before the face and those drawn over it (paws on the mouth)."""
    if not omit_arms <= {"left", "right"}:
        raise ToonDataError("omitted arms must be left or right")
    if isinstance(look.drawing, Posing):
        own = look.drawing.gesture(arms)
        if own is not None:
            return own

    def limb(side: str, *args, **kwargs) -> list[Layer]:
        return [] if side in omit_arms else _limb(*args, **kwargs)

    (lx, ly), (rx, ry) = SHOULDERS
    mx, my = look.mouth
    under: list[Layer] = []
    over: list[Layer] = []
    if arms == "desk" or arms == "lean":
        (le, lw, lp), (re, rw, rp) = DESK
        under += limb("left", [(lx, ly), le, lw], look, lp)
        if arms == "desk":
            under += limb("right", [(rx, ry), re, rw], look, rp)
        else:
            under += limb("right", [(rx, ry), (330.0, 750.0), (344.0, 788.0)], look, (348.0, 792.0))
    elif arms == "type":
        lift = 0.0 if frame == 0 else 9.0  # the far arm lies along the desk's edge, the near one reaches over it
        under += limb(
            "left", [(lx, ly), (110.0, 776.0), (250.0, 792.0), (366.0, 788.0 - lift)], look, (376.0, 789.0 - lift)
        )
        under += limb("right", [(rx, ry), (352.0, 742.0), (398.0, 762.0 + lift)], look, (404.0, 764.0 + lift))
    elif arms == "crossed":
        under += limb("left", [(lx, ly), (120.0, 748.0), (230.0, 752.0), (282.0, 738.0)], look, (290.0, 732.0))
        under += limb("right", [(rx, ry), (262.0, 760.0), (150.0, 772.0), (96.0, 758.0)], look, (86.0, 752.0))
    elif arms == "sigh":
        under += limb("left", [(lx, ly), (58.0, 760.0), (70.0, 800.0)], look, (72.0, 806.0), toes=False)
        under += limb("right", [(rx, ry), (312.0, 760.0), (300.0, 800.0)], look, (298.0, 806.0), toes=False)
    else:  # face, face2: both paws over the mouth
        spread = 26.0 if arms == "face" else 36.0
        drop = 0.0 if arms == "face" else -8.0
        over += limb(
            "left", [(lx, ly), (76.0, 700.0), (mx - spread - 18.0, my + 12.0 + drop)], look, (mx - spread, my + drop)
        )
        over += limb(
            "right", [(rx, ry), (294.0, 700.0), (mx + spread + 18.0, my + 12.0 + drop)], look, (mx + spread, my + drop)
        )
    return under, over


def pose_hands(
    cv: Canvas, look: Look, node: str, arms: str, omit_arms: frozenset[str] = frozenset(), tracks: Sequence[str] = ()
) -> None:
    """Record the hands the body drawing ``node`` draws in the pose ``arms``: one per arm :func:`_arms` draws, and one
    per limb track drawn into it (``tracks``, their sides), so the count of a character's hands sees each (ADR 0174).
    A look's own gesture draws both its arms whatever is omitted, as :func:`_arms` does."""
    gesture = isinstance(look.drawing, Posing) and look.drawing.gesture(arms) is not None
    drawn = [side for side in ("left", "right") if gesture or side not in omit_arms]
    sides = {"left": Side.LEFT, "right": Side.RIGHT}
    anatomy_ledger.pose_hands(cv, look.name, node, [sides[side] for side in [*drawn, *tracks]])


def _brow(look: Look, centre: Point, kind: str, inner: float) -> Layer:
    """An eyebrow over one eye: raised for surprise, flat and low when tired, angled down toward the nose in anger,
    up toward it in pain."""
    ex, ey = centre
    r = look.eye_r
    lift = {
        "wide": 12.0,
        "shock": 22.0,
        "up": 18.0,
        "half": 6.0,
        "down": 4.0,
        "side": 8.0,
        "left": 10.0,
        "teary": 10.0,
        "wince": 4.0,
        "hearts": 12.0,
    }
    y = ey - r - INK - lift.get(kind, 7.0)
    outer, inside = ex - inner * r * 1.05, ex + inner * r * 0.9
    if kind == "narrow":  # the inner end comes down: a frown
        points = [(outer, y - 5.0), (inside, y + 9.0)]
    elif kind in ("teary", "wince"):  # the inner end goes up: hurt
        points = [(outer, y + 4.0), (inside, y - 8.0)]
    elif kind in ("shock", "up", "wide", "hearts"):  # an arch
        points = [(outer, y + 2.0), (ex, y - 4.0), (inside, y + 2.0)]
    else:
        points = [(outer, y), (inside, y + (2.0 if kind == "down" else 0.0))]
    return (brush.stroke(points, INK * 0.95), "ink")


def _eye(look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
    """One eye: ``inner`` is +1 when the nose is to the right of it, −1 when to the left."""
    if look.drawing is not None:
        return look.drawing.eye(look, centre, kind, inner)
    if kind == "sleepy":  # drawn for every look by toon_critters (ADR 0045); here, not at import: it draws with this
        from .toon_critters import shared_eye

        return shared_eye(look, centre, inner)
    ex, ey = centre
    r = look.eye_r * (1.3 if kind == "shock" else 1.0)
    lid = look.lid or look.coat
    out: list[Layer] = [_brow(look, centre, kind, inner)] if look.brows else []
    if kind == "closed":
        return out + [(brush.stroke([(ex - r, ey + 1.0), (ex, ey + 7.0), (ex + r, ey + 1.0)], INK), "ink")]
    if kind == "wince":  # squeezed shut: a chevron pointing at the nose
        tip, back = ex + inner * 0.75 * r, ex - inner * 0.9 * r
        return out + [(brush.stroke([(back, ey - 0.65 * r), (tip, ey), (back, ey + 0.65 * r)], INK), "ink")]
    if kind == "hearts":
        heart = _heart(ex, ey, r * 1.25)
        return out + [(brush.rim(heart, INK), "ink"), (brush.outline(heart), HEART)]
    out.append((brush.ellipse(ex, ey, r + INK, r + INK), "ink"))
    out.append((brush.ellipse(ex, ey, r, r), "white"))
    pupil = {
        "wide": (0.0, 0.0),
        "half": (0.0, 0.15),
        "left": (-0.45, 0.05),
        "up": (0.0, -0.5),
        "down": (0.0, 0.5),
        "side": (0.5, 0.12),
        "narrow": (0.0, 0.15),
        "shock": (0.0, 0.0),
        "roll": (0.42, -0.5),  # up and the same way for both eyes
        "teary": (0.0, 0.05),
    }[kind]
    size = r * {"shock": 0.14, "teary": 0.38}.get(kind, 0.28)
    lids = {"half": 0.5, "down": 0.3, "side": 0.45}  # a straight lid, this far down the eye
    if kind in lids:
        y = ey - r + 2 * r * lids[kind]
        out.append(
            (
                brush.outline(
                    [
                        (ex - r - INK - 1, ey - r - INK - 1),
                        (ex + r + INK + 1, ey - r - INK - 1),
                        (ex + r + INK + 1, y),
                        (ex - r - INK - 1, y),
                    ]
                ),
                lid,
            )
        )
        out.append((brush.stroke([(ex - r - 2.0, y), (ex, y + 1.5), (ex + r + 2.0, y)], INK), "ink"))
    elif kind == "narrow":  # an angled lid, lower on the inner side
        outer, inside = ex - inner * (r + INK + 1), ex + inner * (r + INK + 1)
        y_out, y_in = ey - 0.6 * r, ey - 0.05 * r
        out.append(
            (
                brush.outline([(outer, ey - r - INK - 1), (inside, ey - r - INK - 1), (inside, y_in), (outer, y_out)]),
                lid,
            )
        )
        out.append((brush.stroke([(outer, y_out), (inside, y_in)], INK), "ink"))
    elif kind == "roll":  # a lower lid risen to the middle: the bored half of an eye roll
        y = ey + 0.3 * r
        out.append(
            (brush.outline([(ex - r - INK - 1, y), (ex + r + INK + 1, y), (ex + r + INK + 1, ey + r + INK + 1),
                            (ex - r - INK - 1, ey + r + INK + 1)]), lid)
        )  # fmt: skip
        out.append((brush.stroke([(ex - r - 2.0, y), (ex, y - 1.5), (ex + r + 2.0, y)], INK), "ink"))
    px, py = ex + pupil[0] * r, ey + pupil[1] * r
    out.append((brush.ellipse(px, py, size, size * 1.15), "ink"))
    if kind == "teary":  # glistening whatever the look's polish, and a tear at the outer corner
        out.append((brush.ellipse(px - size * 0.35, py - size * 0.4, size * 0.36, size * 0.36), "white"))
        out.append((brush.ellipse(px + size * 0.4, py + size * 0.4, size * 0.18, size * 0.18), "white"))
        tear = _tear(ex - inner * 0.75 * r, ey + r + INK + 4.0, r / 17.0)
        return out + [(brush.rim(tear, FINE), "ink"), (brush.outline(tear), TEAR)]
    if look.shine:
        out.append((brush.ellipse(px - size * 0.35, py - size * 0.45, size * 0.3, size * 0.3), "white"))
    return out


def _heart(cx: float, cy: float, size: float) -> tuple[Point, ...]:
    """A heart about ``2 * size`` across, centred on (``cx``, ``cy``): the classic curve, notched at the top."""
    s = size / 16.0
    out = []
    for k in range(20):
        t = 2 * math.pi * k / 20
        x = 16.0 * math.sin(t) ** 3
        y = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        out.append((round(cx + x * s, 2), round(cy + (y - 2.5) * s, 2)))
    return tuple(out)


def _tear(x: float, y: float, scale: float) -> tuple[Point, ...]:
    """A drop hanging from (``x``, ``y``), pointed at the top."""
    drop = ((0.0, 0.0), (5.0, 9.0), (6.5, 15.0), (0.0, 20.0), (-6.5, 15.0), (-5.0, 9.0))
    return tuple((round(x + dx * scale, 2), round(y + dy * scale, 2)) for dx, dy in drop)


def _lids(look: Look) -> list[Layer]:
    """Both eyes shut for a blink: a lid over each eye and the closed line, drawn over the open eyes."""
    if look.drawing is not None:
        return look.drawing.lids(look)
    lid = look.lid or look.coat
    out: list[Layer] = []
    for ex, ey in look.eyes:
        r = look.eye_r
        out.append((brush.ellipse(ex, ey, r + INK + 1.0, r + INK + 1.0), lid))
        out.append((brush.stroke([(ex - r, ey + 1.0), (ex, ey + 7.0), (ex + r, ey + 1.0)], INK), "ink"))
    return out


def _mouth(look: Look, kind: str) -> list[Layer]:
    if look.drawing is not None:
        return look.drawing.mouth(look, kind)
    if kind in ("yawn", "scream", "puff"):  # drawn for every look by toon_critters (ADR 0045)
        from .toon_critters import shared_mouth

        return shared_mouth(look, kind)
    mx, my = look.mouth
    w = look.mouth_w
    if kind == "none":
        return []
    if kind == "flat":
        return [(brush.stroke([(mx - w / 2, my), (mx, my + 2.0), (mx + w / 2, my)], INK * 0.9), "ink")]
    if kind in ("open", "round", "o"):
        rx, ry = {"open": (w * 0.42, 11.0), "round": (w * 0.36, 16.0), "o": (9.0, 11.0)}[kind]
        return [(brush.ellipse(mx, my + 6.0, rx + INK, ry + INK), "ink"), (brush.ellipse(mx, my + 6.0, rx, ry), LIPS)]
    if kind == "drop":
        pts = [
            (mx, my - 2.0),
            (mx + 7.0, my + 8.0),
            (mx + 8.0, my + 16.0),
            (mx, my + 23.0),
            (mx - 8.0, my + 16.0),
            (mx - 7.0, my + 8.0),
        ]
        return [(brush.outline(pts), "ink")]
    if kind == "grin":
        teeth = [(mx - w / 2 + 4.0, my - 2.0), (mx, my + 9.0), (mx + w / 2 - 4.0, my - 2.0)]
        return [
            (brush.outline(teeth), "white"),
            (brush.stroke([(mx - w / 2, my - 4.0), (mx, my + 13.0), (mx + w / 2, my - 4.0)], INK), "ink"),
            (brush.stroke([(mx - w / 2, my - 4.0), (mx + w / 2, my - 4.0)], FINE), "ink"),
        ]
    if kind == "wave":
        pts = [(mx - w / 2, my), (mx - w / 4, my - 5.0), (mx, my), (mx + w / 4, my + 5.0), (mx + w / 2, my)]
        return [(brush.stroke(pts, INK * 0.8), "ink")]
    if kind == "grimace":  # clenched teeth, wider than the mouth
        hw = w * 0.58
        box = [(mx - hw, my - 9.0), (mx + hw, my - 9.0), (mx + hw, my + 9.0), (mx - hw, my + 9.0)]
        out: list[Layer] = [
            (brush.rim(box, INK * 0.8, brush.EVEN, steps=3), "ink"),
            (brush.outline(box, steps=3), "white"),
        ]
        out.append((brush.stroke([(mx - hw + 2.0, my), (mx + hw - 2.0, my)], FINE * 0.7, brush.EVEN, steps=3), "ink"))
        for k in (-1.0, 0.0, 1.0):
            x = mx + k * hw / 2
            out.append((brush.stroke([(x, my - 8.0), (x, my + 8.0)], FINE * 0.7, brush.EVEN, steps=3), "ink"))
        return out
    if kind == "frown":
        return [(brush.stroke([(mx - w / 2, my + 6.0), (mx, my - 6.0), (mx + w / 2, my + 6.0)], INK * 0.9), "ink")]
    if kind == "tongue":  # a smile with the tongue out under one side
        tw = w * 0.36
        tongue = [
            (mx - 2.0, my + 2.0),
            (mx + tw, my + 2.0),
            (mx + tw, my + 15.0),
            (mx + tw / 2 + 1.0, my + 22.0),
            (mx - 2.0, my + 15.0),
        ]
        return [
            (brush.rim(tongue, FINE), "ink"),
            (brush.outline(tongue), TONGUE),
            (brush.stroke([(mx + tw / 2 + 1.0, my + 6.0), (mx + tw / 2 + 1.0, my + 13.0)], FINE * 0.6), "ink"),
            (brush.stroke([(mx - w / 2, my - 3.0), (mx, my + 5.0), (mx + w / 2, my - 3.0)], INK), "ink"),
        ]
    if kind == "kiss":  # a pucker
        pts = [(mx - 3.0, my - 9.0), (mx + 5.0, my - 5.0), (mx, my), (mx + 5.0, my + 5.0), (mx - 3.0, my + 9.0)]
        return [(brush.stroke(pts, INK * 0.85), "ink")]
    # smirk
    return [(brush.stroke([(mx - w / 4, my + 2.0), (mx + w / 6, my), (mx + w / 2, my - 8.0)], INK), "ink")]


def _viseme(look: Look, kind: str) -> list[Layer]:
    """A speaking mouth: ``open`` and ``round`` show the lips, ``teeth`` a shallow bite with a parting line."""
    if look.drawing is not None:
        return look.drawing.viseme(look, kind)
    mx, my = look.mouth
    w = look.mouth_w
    if kind == "open":
        return [
            (brush.ellipse(mx, my + 7.0, w * 0.40 + INK, 14.0 + INK), "ink"),
            (brush.ellipse(mx, my + 7.0, w * 0.40, 14.0), LIPS),
        ]
    if kind == "round":
        return [
            (brush.ellipse(mx, my + 8.0, w * 0.24 + INK, 15.0 + INK), "ink"),
            (brush.ellipse(mx, my + 8.0, w * 0.24, 15.0), LIPS),
        ]
    if kind == "teeth":
        return [
            (brush.ellipse(mx, my + 3.0, w * 0.46 + INK * 0.8, 7.0 + INK * 0.8), "ink"),
            (brush.ellipse(mx, my + 3.0, w * 0.46, 7.0), "white"),
            (brush.stroke([(mx - w * 0.36, my + 3.0), (mx + w * 0.36, my + 3.0)], FINE * 0.6, brush.EVEN), "ink"),
        ]
    raise ToonDataError(f"{look.name}: no viseme {kind!r}; the visemes are {VISEMES}")


def _teeth(look: Look) -> list[Layer]:
    """Two front teeth hanging from the middle of the mouth."""
    mx, my = look.mouth
    out: list[Layer] = []
    for dx in (-5.5, 0.5):
        tooth = [(mx + dx, my + 2.0), (mx + dx + 5.0, my + 2.0), (mx + dx + 5.0, my + 15.0), (mx + dx, my + 15.0)]
        out += [(brush.rim(tooth, FINE * 0.8, brush.EVEN, steps=3), "ink"), (brush.outline(tooth, steps=3), "white")]
    return out


def _whiskers(look: Look) -> list[Layer]:
    mx, my = look.mouth
    out: list[Layer] = []
    for side in (-1.0, 1.0):
        for dy0, dy1 in ((-14.0, -22.0), (-8.0, -8.0), (-2.0, 6.0)):
            line = [(mx + side * 24.0, my + dy0), (mx + side * 58.0, my + dy1)]
            out.append((brush.stroke(line, FINE * 0.7, brush.EVEN, steps=3), "ink"))
    return out


def _blush(look: Look) -> list[Layer]:
    (lx, _), (rx, _) = look.eyes
    y = look.mouth[1] - 14.0
    return [(brush.ellipse(lx - 10.0, y, 15.0, 8.0), look.blush), (brush.ellipse(rx + 10.0, y, 15.0, 8.0), look.blush)]


def _place(layers: list[Layer], arms: str) -> list[Layer]:
    """The whole figure moved for its arms: a sigh drops, a lean turns toward the laptop."""
    if arms == "sigh":
        return [(brush.shift(s, 0.0, SIGH_DROP), c) for s, c in layers]
    if arms == "lean":
        return [(brush.rotate(s, PIVOT[0], PIVOT[1], LEAN_DEGREES), c) for s, c in layers]
    return layers


NOTE_PAPER = "#fff3a3"
HEADSET = "#2f3442"
HEADSET_LIGHT = "#6b7385"


@register(
    "prop",
    "toon-headset",
    contract=tc.contract('toon-headset'),
    summary="A call-centre headset for any brush-drawn character: a band over the crown, a cup and a mic boom",
    style="toon",
)
def headset(look: Look, mic: bool = True) -> list[Layer]:
    """A headset fitted to ``look``: a band arching just over the crown from cup to cup, ear cups at eye height on
    the head's sides and, with ``mic``, a boom from the left cup to a mic beside the mouth. Reference pixels; stick
    it on the figure with ``stickers=`` so it leans and sighs with it."""
    top = min(y for _, y in look.silhouette)
    head = [x for x, y in look.silhouette if y < look.mouth[1]]
    left, right = min(head), max(head)
    ear_y = (look.eyes[0][1] + look.eyes[1][1]) / 2
    crown = top - 6.0
    arc = []
    for k in range(13):
        s = k / 12
        arc.append((left + (right - left) * s, crown + (ear_y - 20.0 - crown) * (2 * s - 1) ** 2))
    layers: list[Layer] = [
        (brush.stroke(arc, 10.0, brush.EVEN, steps=4), "ink"),
        (brush.stroke(arc, 5.0, brush.EVEN, steps=4), HEADSET),
    ]
    for cx in (left + 2.0, right - 2.0):
        layers.append((brush.ellipse(cx, ear_y, 17.0, 25.0), "ink"))
        layers.append((brush.ellipse(cx, ear_y, 13.0, 21.0), HEADSET))
        layers.append((brush.ellipse(cx - 3.0, ear_y - 8.0, 4.0, 7.0), HEADSET_LIGHT))
    if mic:
        end = (look.mouth[0] - look.mouth_w * 0.75, look.mouth[1] + 4.0)
        boom = [(left + 6.0, ear_y + 18.0), ((left + end[0]) / 2, end[1] + 6.0), end]
        layers.append((brush.stroke(boom, 6.0, brush.EVEN, steps=4), "ink"))
        layers.append((brush.stroke(boom, 2.5, brush.EVEN, steps=4), HEADSET_LIGHT))
        layers.append((brush.ellipse(end[0], end[1], 11.0, 9.0), "ink"))
        layers.append((brush.ellipse(end[0], end[1], 8.0, 6.0), HEADSET_LIGHT))
    return layers


def sticky_note(cx: float, cy: float, size: float = 44.0, tilt: float = -8.0, paper: str = NOTE_PAPER) -> list[Layer]:
    """A square note with three lines of scribble, centred on ``cx, cy`` and turned ``tilt`` degrees: ink rim, paper,
    scribbles. Reference pixels; stick it on a figure with ``stickers=``."""
    if not (checks.number(size) and size > 8):
        raise ToonDataError(f"a note needs a size over 8 px, got {size!r}")
    h = size / 2
    square = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    layers: list[Layer] = [
        (brush.rim(square, FINE, brush.EVEN, steps=3), "ink"),
        (brush.outline(square, steps=3), paper),
    ]
    for k, width in enumerate((0.62, 0.5, 0.34)):
        y = cy - h * 0.45 + k * h * 0.45
        line = brush.stroke([(cx - h * width, y), (cx + h * width, y)], FINE * 0.7, brush.EVEN, steps=3)
        layers.append((line, "ink"))
    return [(brush.rotate(s, cx, cy, tilt), c) for s, c in layers]


def _foundation(look: Look) -> list[Layer]:
    if look.drawing is not None:
        return look.drawing.foundation(look)
    layers: list[Layer] = []
    if look.mantle:
        layers += [(brush.rim(look.mantle, INK), "ink"), (brush.outline(look.mantle), look.dark)]
    for ear in look.ears:
        layers += [(brush.rim(ear, INK), "ink"), (brush.outline(ear), look.ear or look.dark)]
        if look.ear_inner:
            layers.append((brush.outline(_shrink(ear, 0.55)), look.ear_inner))
    layers += [(brush.rim(look.silhouette, INK), "ink"), (brush.outline(look.silhouette), look.coat)]
    layers += list(look.marks)
    if look.blush:
        layers += _blush(look)
    return layers


def figure_layers(
    look: Look,
    eyes: str,
    mouth: str,
    arms: str,
    frame: int = 0,
    stickers: Sequence[Layer] = (),
    *,
    omit_arms: frozenset[str] = frozenset(),
    wear: Sequence[str] = (),
) -> tuple[list[Layer], list[Layer], list[Layer]]:
    """The character in one expression as three runs of (shape, colour) layers in draw order, reference pixels:
    everything under the mouth (ears, body, marks, blush, arms, eyes, nose, whiskers), the mouth, and everything
    over it (the front teeth, paws on the face, ``stickers`` such as a note on the forehead). ``frame`` is the
    typing frame (0 or 1) for ``arms == "type"``. What is ``wear``-ing (:mod:`srstudio.toon_wear`) goes on the
    cheeks under the nose, or over the face under the paws. The runs are already moved for the arms
    (:func:`_place`)."""
    if eyes not in EYES or mouth not in MOUTHS or arms not in ARMS:
        raise ToonDataError(f"{look.name}: no expression {eyes!r}/{mouth!r}/{arms!r}")
    if frame not in (0, 1):
        raise ToonDataError(f"{look.name}: a typing frame is 0 or 1, got {frame!r}")
    under_mouth = _foundation(look)
    under, over = _arms(look, arms, frame, omit_arms)
    under_mouth += under
    under_mouth += _eye(look, look.eyes[0], eyes, 1.0) + _eye(look, look.eyes[1], eyes, -1.0)
    cheeks: list[Layer] = []
    worn: list[Layer] = []
    if wear:
        from .toon_wear import face_of, wear_layers  # here, not at import: toon_wear draws with this module

        cheeks, worn = wear_layers(face_of(look), wear)
    under_mouth += cheeks
    under_mouth += [(shape, "ink" if i == 0 else "white") for i, shape in enumerate(look.nose)]
    if look.whiskers:
        under_mouth += _whiskers(look)
    bare = look.teeth and mouth not in ("none", "grimace", "kiss", "scream")  # none over clenched, puckered or
    # screaming lips (a scream shows its own row)
    over_mouth: list[Layer] = (_teeth(look) if bare else []) + worn + over + list(stickers)
    return _place(under_mouth, arms), _place(_mouth(look, mouth), arms), _place(over_mouth, arms)


def figure_shapes(
    look: Look,
    eyes: str,
    mouth: str,
    arms: str,
    frame: int = 0,
    stickers: Sequence[Layer] = (),
    *,
    omit_arms: frozenset[str] = frozenset(),
    wear: Sequence[str] = (),
) -> list[Layer]:
    """The whole drawing of :func:`figure_layers` as one run of layers."""
    under, mouth_layers, over = figure_layers(look, eyes, mouth, arms, frame, stickers, omit_arms=omit_arms, wear=wear)
    return under + mouth_layers + over


# -- lip sync and blinks ----------------------------------------------------------------------------------------------
def viseme_keys(mouths: Mouths, start: float, end: float) -> dict[str, list[tuple[float, int]]]:
    """Opacity hold keys per viseme over the run ``[start, end)`` from the ``(second, viseme)`` states: the state in
    force at ``start`` (closed when none precedes it), then every change inside the run. Empty when the mouth is
    closed throughout, so the pose's own mouth is drawn plainly."""
    if any(not (checks.number(t) and t >= 0) or v not in VISEMES for t, v in mouths):
        raise ToonDataError(f"mouths are (non-negative seconds, viseme among {VISEMES}) states")
    if any(b <= a for (a, _), (b, _) in zip(mouths, mouths[1:], strict=False)):
        raise ToonDataError("mouths must be in time order, one state a second")
    current = "closed"
    for t, v in mouths:
        if t <= start + EPSILON:
            current = v
    states = [(round(start, 6), current)]
    for t, v in mouths:
        if start + EPSILON < t < end - EPSILON and v != states[-1][1]:
            states.append((round(t, 6), v))
    used = {v for _, v in states}
    if used == {"closed"}:
        return {}
    return {v: [(t, int(s == v)) for t, s in states] for v in VISEMES if v in used}


def blink_times(start: float, end: float, period: float, hold: float = BLINK_HOLD) -> list[float]:
    """When a character blinks through a run: every ``period`` seconds from :data:`BLINK_PHASE` of one into it,
    never within a ``hold`` of the end; none when ``period`` is 0."""
    if not (checks.number(period) and period >= 0):
        raise ToonDataError(f"a blink period is a non-negative number of seconds, got {period!r}")
    if not (checks.number(hold) and hold > 0):
        raise ToonDataError(f"a blink hold is a positive number of seconds, got {hold!r}")
    if period == 0:
        return []
    out = []
    t = start + BLINK_PHASE * period
    while t + hold < end - EPSILON:
        out.append(round(t, 6))
        t += period
    return out


# -- on a canvas ----------------------------------------------------------------------------------------------------
def _draw(cv: Canvas, parent, layers: Sequence[Layer]) -> None:
    for shape, colour in layers:
        paint = colour.paint(cv) if isinstance(colour, Ramp) else {"ink": cv.ink, "white": cv.white}.get(colour, colour)
        flat(cv, parent, shape, paint)


def _limb_layer(cv: Canvas, parent, arms: str):
    ref = cv.group(parent, cv.uid("g"), y=-REF_TOP * SCALE, scaleX=SCALE, scaleY=SCALE)
    if arms == "lean":
        return cv.group(
            ref, cv.uid("g"), x=PIVOT[0], y=PIVOT[1], anchorX=PIVOT[0], anchorY=PIVOT[1], rotation=LEAN_DEGREES
        )
    if arms == "sigh":
        return cv.group(ref, cv.uid("g"), y=SIGH_DROP)
    return ref


def _draw_mouth(
    cv: Canvas, g, look: Look, pose: Pose, closed: Sequence[Layer], mouths: Mouths, start: float, end: float
) -> None:
    """The pose's mouth ``closed`` in ``g``, or one layer per viseme with hold keys where a sound is heard."""
    keys = viseme_keys(mouths, start, end)
    if keys:
        lips = cv.group(g, cv.uid("g"))
        for viseme, states in keys.items():
            layer = cv.group(lips, cv.uid("g"))
            _draw(cv, layer, closed if viseme == "closed" else _place(_viseme(look, viseme), pose.arms))
            cv.keys(layer, "opacity", states, local=False)
    else:
        _draw(cv, g, closed)


def _draw_blinks(cv: Canvas, g, look: Look, pose: Pose, start: float, end: float) -> None:
    """The lids shut at the look's blinks over the run, slower on sleepy eyes."""
    sleepy = pose.eyes == "sleepy"
    pace, hold = (SLEEPY_PACE, SLEEPY_HOLD) if sleepy else (1.0, BLINK_HOLD)
    shut = pose.eyes in SHUT or (isinstance(look.drawing, Posing) and look.drawing.shut(pose.eyes))
    blinks = blink_times(start, end, look.blink * pace, hold) if not shut else []
    if blinks:
        lids = cv.group(g, cv.uid("g"))
        _draw(cv, lids, _place(_lids(look), pose.arms))
        states = [(start, 0)]
        for t in blinks:
            states += [(t, 1), (round(t + hold, 6), 0)]
        cv.keys(lids, "opacity", states, local=False)


def figure(
    cv: Canvas,
    parent,
    look: Look,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    """One group per pose run (:func:`srstudio.toon.runs`), the typing frames swapped on ``taps`` (project
    seconds). ``enter`` puts the character on from that project second: its poses count from it, and it leaves at
    ``duration``. ``mouths`` is the lip-sync track, ``(project second, viseme)`` states: inside every run where a
    sound is heard the mouth becomes one layer per viseme with hold keys (:func:`viseme_keys`), the pose's own mouth
    showing while closed. A look with a blink period shuts its eyes for :data:`BLINK_HOLD` at :func:`blink_times`;
    sleepy eyes blink :data:`SLEEPY_PACE` times slower and stay shut for :data:`SLEEPY_HOLD`."""
    if not (checks.number(enter) and 0 <= enter < duration):
        raise ToonDataError(f"{look.name}: enter must be a project second before the end, got {enter!r}")
    sides: frozenset[str] = frozenset()
    if limbs:
        from .limbs.compile import LayerTargets
        from .limbs.integration import Facing, draw_tracks, prepare_tracks

        limbs = prepare_tracks(cv, limbs, duration)
        facing = Facing(front=True)  # faces the viewer and never flips
        sides = facing.slots(limbs)
    groups = []
    for pose, start, end in runs(poses, duration - enter):
        start, end = round(start + enter, 6), round(end + enter, 6)
        g = cv.group(parent, cv.uid("g"), start=start, end=end)
        pose_hands(cv, look, g.id, pose.arms, sides, [facing.slot(t.motion.arm.side) for t in limbs] if limbs else ())

        behind = _limb_layer(cv, g, pose.arms) if limbs else None
        under, mouth_layers, over = figure_layers(
            look, pose.eyes, pose.mouth, pose.arms, 0, stickers, omit_arms=sides, wear=pose.wear
        )
        base_count = len(_foundation(look)) if limbs else 0
        if limbs:
            _draw(cv, g, under[:base_count])
        limb_body = _limb_layer(cv, g, pose.arms) if limbs else None
        if pose.arms == "type":

            def frame_of(
                parent,
                frame: int,
                eyes: str = pose.eyes,
                mouth: str = pose.mouth,
                skip: int = base_count,
                wear: tuple[str, ...] = pose.wear,
            ) -> None:
                layers = figure_layers(look, eyes, mouth, "type", frame, omit_arms=sides, wear=wear)[0]
                _draw(cv, parent, layers[skip:])

            swap_frames(cv, g, start, end, taps, frame_of)
        else:
            _draw(cv, g, under[base_count:])
        _draw_mouth(cv, g, look, pose, mouth_layers, mouths, start, end)
        _draw_blinks(cv, g, look, pose, start, end)
        _draw(cv, g, over)
        if limbs:
            front = _limb_layer(cv, g, pose.arms)
            draw_tracks(cv, LayerTargets(behind, limb_body, front), limbs, id=cv.uid("limbs"), facing=facing)
        groups.append(g)
    return groups


_CHARACTER_CONTRACT = cc.toon(Pose, EYES, MOUTHS, ARMS, visemes=VISEMES, wear=WEAR, limbs=True)


@register(
    "character",
    "toon-dog",
    summary="A floppy-eared dog at the desk, brush-drawn: the cat's expressions and arms, its own snout and ears",
    contract=_CHARACTER_CONTRACT,
)
def dog(
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
    return figure(cv, parent, DOG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-frog",
    summary="A wide-mouthed frog at the desk, brush-drawn: eyes on bumps, a pale belly, the cat's vocabulary",
    contract=_CHARACTER_CONTRACT,
)
def frog(
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
    return figure(cv, parent, FROG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-bear",
    summary="A brown bear at the desk: round ears, a pale muzzle, eyebrows, blushing cheeks, blinks and lip sync",
    contract=_CHARACTER_CONTRACT,
)
def bear(
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
    return figure(cv, parent, BEAR, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-rabbit",
    summary="A pale rabbit at the desk: tall pink-lined ears, whiskers, front teeth, eyebrows, blinks and lip sync",
    contract=_CHARACTER_CONTRACT,
)
def rabbit(
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
    return figure(cv, parent, RABBIT, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-fox",
    summary="A slender red fox at the desk: tall ears, white cheek tufts and chin, dark paws, blinks and lip sync",
    contract=_CHARACTER_CONTRACT,
)
def fox(
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
    return figure(cv, parent, FOX, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-raccoon",
    summary="A stout grey raccoon at the desk: a bandit's mask, white-rimmed ears, dark gloves, blinks and lip sync",
    contract=_CHARACTER_CONTRACT,
)
def raccoon(
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
    return figure(cv, parent, RACCOON, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-hedgehog",
    summary="A small hedgehog at the desk: a crown of dark spines, beady eyes, a button nose, blinks and lip sync",
    contract=_CHARACTER_CONTRACT,
)
def hedgehog(
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
    return figure(cv, parent, HEDGEHOG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)
