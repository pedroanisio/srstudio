"""More Toon characters, drawn with the brush: a dog, a frog, a bear and a rabbit at the cat's desk.

The Toon cat is traced from its reference; these four are drawn in code with :mod:`srstudio.brush`, in the same
reference pixels (:func:`srstudio.toon.fx`/``fy``), with the same vocabulary of expressions (:data:`EYES`,
:data:`MOUTHS`, :data:`ARMS` of :mod:`srstudio.toon`) and the same contract: one group per pose run, a typing pose
that swaps two frames on the keystrokes it contains. A pose file written for the cat poses any of them.

Every line is a filled brush shape, never a stroke: the ink band under the body fill (:func:`brush.rim`), the limbs
as tapered strokes in ink under strokes in the coat colour, lids as coat-coloured shapes with an inked edge. What
differs per character is a :class:`Look`: the silhouette, the coat colours, where the eyes and the mouth sit, the
parts only it has (the dog's floppy ears, snout and nose; the frog's eye bumps, belly, nostrils and spots; the
bear's round ears and muzzle; the rabbit's tall ears, whiskers and front teeth) and its polish: eyebrows that follow
the eyes, a highlight on each pupil, blushing cheeks and blinks at its own pace.

**Lip sync.** A character speaks through :data:`VISEMES`: ``closed`` is the pose's own mouth (a smirk stays a
smirk between syllables), ``open``, ``round`` and ``teeth`` replace it while a sound is heard. :func:`figure` takes
the viseme track as ``(project second, viseme)`` states (:func:`srstudio.sketch.visemes` derives them from the
voice's character timestamps) and draws the mouth as one layer per viseme with hold keys, inside each pose run, so
the lips move while the expression holds.

:func:`figure_shapes` is the whole drawing as data (shape, colour) in reference pixels, so a test can measure it
without a canvas; :func:`dog`, :func:`frog`, :func:`bear` and :func:`rabbit` put it on one.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Number

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .registry import register
from .toon import ARMS, EPSILON, EYES, LIPS, MOUTHS, Pose, ToonDataError, flat, runs, swap_frames

__all__ = [
    "Look",
    "DOG",
    "FROG",
    "BEAR",
    "RABBIT",
    "LOOKS",
    "INK",
    "VISEMES",
    "BLINK_HOLD",
    "figure_layers",
    "figure_shapes",
    "viseme_keys",
    "blink_times",
    "figure",
    "dog",
    "frog",
    "bear",
    "rabbit",
]

INK = 5.5  # the brush's weight: the reference's line, reference pixels
FINE = 3.0
CENTRE = 185.0  # the character's axis
PIVOT = (CENTRE, 812.0)  # where a lean turns about: the seat, under the desk's edge
LEAN_DEGREES = 7.0
SIGH_DROP = 10.0
SHOULDERS: tuple[Point, Point] = ((62.0, 712.0), (308.0, 712.0))
VISEMES = ("closed", "open", "round", "teeth")  # the lip-sync mouths; closed is the pose's own mouth
BLINK_HOLD = 0.12  # seconds the lids stay down in a blink
BLINK_PHASE = 0.55  # the first blink of a pose comes this fraction of the period after it starts
Layer = tuple[Shape, str]  # a shape and its colour: "ink" and "white" are the palette's, the rest literal
Mouths = Sequence[tuple[float, str]]  # (project second, viseme) states, in time order


@dataclass(frozen=True)
class Look:
    """One character: its silhouette (head running into the body, closed, at rest), coat colours, where its face
    is, and its polish. ``ears`` are drawn behind the body, ``marks`` (light patches, spots) over it, both at rest;
    ``ear`` and ``ear_inner`` colour the ears (the dark coat and nothing by default). ``brows`` adds eyebrows that
    follow the eyes, ``shine`` a highlight on each pupil, ``blush`` cheeks in that colour, ``teeth`` two front
    teeth under the mouth, ``whiskers`` three a side; ``blink`` is the seconds between blinks (0: never)."""

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
LOOKS = {"dog": DOG, "frog": FROG, "bear": BEAR, "rabbit": RABBIT}
BEAR_BROW = (
    24  # the index of the bear's left brow in figure_shapes(BEAR, ..., "desk"): after ears, body, marks, blush, arms
)


# -- pieces ---------------------------------------------------------------------------------------------------------
def _limb(points: Sequence[Point], look: Look, paw: Point, toes: bool = True) -> list[Layer]:
    """An arm from the shoulder to the paw: an ink stroke under a coat stroke, the paw a rimmed oval with toes."""
    out: list[Layer] = [
        (brush.stroke(points, look.limb + 2 * INK, brush.EVEN), "ink"),
        (brush.stroke(points, look.limb, brush.EVEN), look.coat),
        (brush.ellipse(paw[0], paw[1], look.limb * 0.72 + INK, look.limb * 0.5 + INK), "ink"),
        (brush.ellipse(paw[0], paw[1], look.limb * 0.72, look.limb * 0.5), look.coat),
    ]
    if toes:
        for dx in (-look.limb * 0.22, look.limb * 0.22):
            x = paw[0] + dx
            out.append((brush.stroke([(x, paw[1] - look.limb * 0.46), (x, paw[1] - look.limb * 0.12)], FINE), "ink"))
    return out


def _arms(look: Look, arms: str, frame: int) -> tuple[list[Layer], list[Layer]]:
    """The arms of a pose at rest: those drawn before the face and those drawn over it (paws on the mouth)."""
    (lx, ly), (rx, ry) = SHOULDERS
    mx, my = look.mouth
    under: list[Layer] = []
    over: list[Layer] = []
    if arms == "desk" or arms == "lean":
        under += _limb([(lx, ly), (82.0, 760.0), (124.0, 792.0)], look, (132.0, 794.0))
        if arms == "desk":
            under += _limb([(rx, ry), (288.0, 760.0), (246.0, 792.0)], look, (238.0, 794.0))
        else:
            under += _limb([(rx, ry), (330.0, 750.0), (344.0, 788.0)], look, (348.0, 792.0))
    elif arms == "type":
        lift = 0.0 if frame == 0 else 9.0  # the far arm lies along the desk's edge, the near one reaches over it
        under += _limb([(lx, ly), (110.0, 776.0), (250.0, 792.0), (366.0, 788.0 - lift)], look, (376.0, 789.0 - lift))
        under += _limb([(rx, ry), (352.0, 742.0), (398.0, 762.0 + lift)], look, (404.0, 764.0 + lift))
    elif arms == "crossed":
        under += _limb([(lx, ly), (120.0, 748.0), (230.0, 752.0), (282.0, 738.0)], look, (290.0, 732.0))
        under += _limb([(rx, ry), (262.0, 760.0), (150.0, 772.0), (96.0, 758.0)], look, (86.0, 752.0))
    elif arms == "sigh":
        under += _limb([(lx, ly), (58.0, 760.0), (70.0, 800.0)], look, (72.0, 806.0), toes=False)
        under += _limb([(rx, ry), (312.0, 760.0), (300.0, 800.0)], look, (298.0, 806.0), toes=False)
    else:  # face, face2: both paws over the mouth
        spread = 26.0 if arms == "face" else 36.0
        drop = 0.0 if arms == "face" else -8.0
        over += _limb([(lx, ly), (76.0, 700.0), (mx - spread - 18.0, my + 12.0 + drop)], look, (mx - spread, my + drop))
        over += _limb(
            [(rx, ry), (294.0, 700.0), (mx + spread + 18.0, my + 12.0 + drop)], look, (mx + spread, my + drop)
        )
    return under, over


def _brow(look: Look, centre: Point, kind: str, inner: float) -> Layer:
    """An eyebrow over one eye: raised for surprise, flat and low when tired, angled down toward the nose in anger."""
    ex, ey = centre
    r = look.eye_r
    lift = {"wide": 12.0, "shock": 22.0, "up": 18.0, "half": 6.0, "down": 4.0, "side": 8.0, "left": 10.0}
    y = ey - r - INK - lift.get(kind, 7.0)
    outer, inside = ex - inner * r * 1.05, ex + inner * r * 0.9
    if kind == "narrow":  # the inner end comes down: a frown
        points = [(outer, y - 5.0), (inside, y + 9.0)]
    elif kind in ("shock", "up", "wide"):  # an arch
        points = [(outer, y + 2.0), (ex, y - 4.0), (inside, y + 2.0)]
    else:
        points = [(outer, y), (inside, y + (2.0 if kind == "down" else 0.0))]
    return (brush.stroke(points, INK * 0.95), "ink")


def _eye(look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
    """One eye: ``inner`` is +1 when the nose is to the right of it, −1 when to the left."""
    ex, ey = centre
    r = look.eye_r * (1.3 if kind == "shock" else 1.0)
    lid = look.lid or look.coat
    out: list[Layer] = [_brow(look, centre, kind, inner)] if look.brows else []
    if kind == "closed":
        return out + [(brush.stroke([(ex - r, ey + 1.0), (ex, ey + 7.0), (ex + r, ey + 1.0)], INK), "ink")]
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
    }[kind]
    size = r * (0.14 if kind == "shock" else 0.28)
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
    px, py = ex + pupil[0] * r, ey + pupil[1] * r
    out.append((brush.ellipse(px, py, size, size * 1.15), "ink"))
    if look.shine:
        out.append((brush.ellipse(px - size * 0.35, py - size * 0.45, size * 0.3, size * 0.3), "white"))
    return out


def _lids(look: Look) -> list[Layer]:
    """Both eyes shut for a blink: a lid over each eye and the closed line, drawn over the open eyes."""
    lid = look.lid or look.coat
    out: list[Layer] = []
    for ex, ey in look.eyes:
        r = look.eye_r
        out.append((brush.ellipse(ex, ey, r + INK + 1.0, r + INK + 1.0), lid))
        out.append((brush.stroke([(ex - r, ey + 1.0), (ex, ey + 7.0), (ex + r, ey + 1.0)], INK), "ink"))
    return out


def _mouth(look: Look, kind: str) -> list[Layer]:
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
    # smirk
    return [(brush.stroke([(mx - w / 4, my + 2.0), (mx + w / 6, my), (mx + w / 2, my - 8.0)], INK), "ink")]


def _viseme(look: Look, kind: str) -> list[Layer]:
    """A speaking mouth: ``open`` and ``round`` show the lips, ``teeth`` a shallow bite with a parting line."""
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


def sticky_note(cx: float, cy: float, size: float = 44.0, tilt: float = -8.0, paper: str = NOTE_PAPER) -> list[Layer]:
    """A square note with three lines of scribble, centred on ``cx, cy`` and turned ``tilt`` degrees: ink rim, paper,
    scribbles. Reference pixels; stick it on a figure with ``stickers=``."""
    if not (math.isfinite(size) and size > 8):
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


def figure_layers(
    look: Look, eyes: str, mouth: str, arms: str, frame: int = 0, stickers: Sequence[Layer] = ()
) -> tuple[list[Layer], list[Layer], list[Layer]]:
    """The character in one expression as three runs of (shape, colour) layers in draw order, reference pixels:
    everything under the mouth (ears, body, marks, blush, arms, eyes, nose, whiskers), the mouth, and everything
    over it (the front teeth, paws on the face, ``stickers`` such as a note on the forehead). ``frame`` is the
    typing frame (0 or 1) for ``arms == "type"``. The runs are already moved for the arms (:func:`_place`)."""
    if eyes not in EYES or mouth not in MOUTHS or arms not in ARMS:
        raise ToonDataError(f"{look.name}: no expression {eyes!r}/{mouth!r}/{arms!r}")
    if frame not in (0, 1):
        raise ToonDataError(f"{look.name}: a typing frame is 0 or 1, got {frame!r}")
    under_mouth: list[Layer] = []
    for ear in look.ears:
        under_mouth += [(brush.rim(ear, INK), "ink"), (brush.outline(ear), look.ear or look.dark)]
        if look.ear_inner:
            under_mouth.append((brush.outline(_shrink(ear, 0.55)), look.ear_inner))
    under_mouth += [(brush.rim(look.silhouette, INK), "ink"), (brush.outline(look.silhouette), look.coat)]
    under_mouth += list(look.marks)
    if look.blush:
        under_mouth += _blush(look)
    under, over = _arms(look, arms, frame)
    under_mouth += under
    under_mouth += _eye(look, look.eyes[0], eyes, 1.0) + _eye(look, look.eyes[1], eyes, -1.0)
    under_mouth += [(shape, "ink" if i == 0 else "white") for i, shape in enumerate(look.nose)]
    if look.whiskers:
        under_mouth += _whiskers(look)
    over_mouth: list[Layer] = (_teeth(look) if look.teeth and mouth != "none" else []) + over + list(stickers)
    return _place(under_mouth, arms), _place(_mouth(look, mouth), arms), _place(over_mouth, arms)


def figure_shapes(
    look: Look, eyes: str, mouth: str, arms: str, frame: int = 0, stickers: Sequence[Layer] = ()
) -> list[Layer]:
    """The whole drawing of :func:`figure_layers` as one run of layers."""
    under, mouth_layers, over = figure_layers(look, eyes, mouth, arms, frame, stickers)
    return under + mouth_layers + over


# -- lip sync and blinks ----------------------------------------------------------------------------------------------
def viseme_keys(mouths: Mouths, start: float, end: float) -> dict[str, list[tuple[float, int]]]:
    """Opacity hold keys per viseme over the run ``[start, end)`` from the ``(second, viseme)`` states: the state in
    force at ``start`` (closed when none precedes it), then every change inside the run. Empty when the mouth is
    closed throughout, so the pose's own mouth is drawn plainly."""
    if any(
        not (isinstance(t, Number) and not isinstance(t, bool) and math.isfinite(t) and t >= 0) or v not in VISEMES
        for t, v in mouths
    ):
        raise ToonDataError(f"mouths are (non-negative seconds, viseme among {VISEMES}) states")
    if any(b < a for (a, _), (b, _) in zip(mouths, mouths[1:], strict=False)):
        raise ToonDataError("mouths must be in time order")
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


def blink_times(start: float, end: float, period: float) -> list[float]:
    """When a character blinks through a run: every ``period`` seconds from :data:`BLINK_PHASE` of one into it,
    never within a hold of the end; none when ``period`` is 0."""
    if not (isinstance(period, Number) and not isinstance(period, bool) and math.isfinite(period) and period >= 0):
        raise ToonDataError(f"a blink period is a non-negative number of seconds, got {period!r}")
    if period == 0:
        return []
    out = []
    t = start + BLINK_PHASE * period
    while t + BLINK_HOLD < end - EPSILON:
        out.append(round(t, 6))
        t += period
    return out


# -- on a canvas ----------------------------------------------------------------------------------------------------
def _draw(cv: Canvas, parent, layers: Sequence[Layer]) -> None:
    for shape, colour in layers:
        flat(cv, parent, shape, {"ink": cv.ink, "white": cv.white}.get(colour, colour))


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
) -> list:
    """One group per pose run (:func:`srstudio.toon.runs`), the typing frames swapped on ``taps`` (project
    seconds). ``enter`` puts the character on from that project second: its poses count from it, and it leaves at
    ``duration``. ``mouths`` is the lip-sync track, ``(project second, viseme)`` states: inside every run where a
    sound is heard the mouth becomes one layer per viseme with hold keys (:func:`viseme_keys`), the pose's own mouth
    showing while closed. A look with a blink period shuts its eyes for :data:`BLINK_HOLD` at :func:`blink_times`."""
    if not (isinstance(enter, int | float) and math.isfinite(enter) and 0 <= enter < duration):
        raise ToonDataError(f"{look.name}: enter must be a project second before the end, got {enter!r}")
    groups = []
    for pose, start, end in runs(poses, duration - enter):
        start, end = round(start + enter, 6), round(end + enter, 6)
        g = cv.group(parent, cv.uid("g"), start=start, end=end)
        under, mouth_layers, over = figure_layers(look, pose.eyes, pose.mouth, pose.arms, 0, stickers)
        if pose.arms == "type":

            def frame_of(parent, frame: int, eyes: str = pose.eyes, mouth: str = pose.mouth) -> None:
                _draw(cv, parent, figure_layers(look, eyes, mouth, "type", frame)[0])

            swap_frames(cv, g, start, end, taps, frame_of)
        else:
            _draw(cv, g, under)
        keys = viseme_keys(mouths, start, end)
        if keys:
            lips = cv.group(g, cv.uid("g"))
            for viseme, states in keys.items():
                layer = cv.group(lips, cv.uid("g"))
                _draw(cv, layer, mouth_layers if viseme == "closed" else _place(_viseme(look, viseme), pose.arms))
                cv.keys(layer, "opacity", states, local=False)
        else:
            _draw(cv, g, mouth_layers)
        blinks = blink_times(start, end, look.blink) if pose.eyes != "closed" else []
        if blinks:
            shut = cv.group(g, cv.uid("g"))
            _draw(cv, shut, _place(_lids(look), pose.arms))
            states = [(start, 0)]
            for t in blinks:
                states += [(t, 1), (round(t + BLINK_HOLD, 6), 0)]
            cv.keys(shut, "opacity", states, local=False)
        _draw(cv, g, over)
        groups.append(g)
    return groups


@register(
    "character",
    "toon-dog",
    summary="A floppy-eared dog at the desk, brush-drawn: the cat's expressions and arms, its own snout and ears",
    episodes=("the-report", "logo-bigger"),
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
) -> list:
    return figure(cv, parent, DOG, poses, duration, taps, enter, stickers, mouths)


@register(
    "character",
    "toon-frog",
    summary="A wide-mouthed frog at the desk, brush-drawn: eyes on bumps, a pale belly, the cat's vocabulary",
    episodes=("the-report", "logo-bigger"),
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
) -> list:
    return figure(cv, parent, FROG, poses, duration, taps, enter, stickers, mouths)


@register(
    "character",
    "toon-bear",
    summary="A brown bear at the desk: round ears, a pale muzzle, eyebrows, blushing cheeks, blinks and lip sync",
    episodes=("quick-question",),
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
) -> list:
    return figure(cv, parent, BEAR, poses, duration, taps, enter, stickers, mouths)


@register(
    "character",
    "toon-rabbit",
    summary="A pale rabbit at the desk: tall pink-lined ears, whiskers, front teeth, eyebrows, blinks and lip sync",
    episodes=("quick-question",),
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
) -> list:
    return figure(cv, parent, RABBIT, poses, duration, taps, enter, stickers, mouths)
