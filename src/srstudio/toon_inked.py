"""The inked fox: the Toon fox drawn again the way the traced cat is drawn, beside the brush-drawn fox.

The traced cat reads as hand-made where the brush characters read as clean vector art. What it has, and what this
module draws in code (:class:`Inked`, a :class:`srstudio.toon_cast.Drawing`):

* **uneven, asymmetric contours with many points**: the outlines are placed by hand, unmirrored, and drift like a
  hand following them (:func:`srstudio.brush.wobble`);
* **a pressed, broken line**: every ink band is heavier where the form turns from the light (the bottom and the
  back), thins at the tips, carries a dry brush's grit, and breaks in three to five seeded places with a nick
  between, where a hand lifts the brush (:func:`srstudio.brush.broken`); limbs and inner lines taper into their
  joins;
* **one body, arms inside it**: the contour runs from the ruff into the shoulders and flanks in one gentle curve;
  an arm leaves the body inside the shoulder, slim there and widest at the forearm and paw, and is inked only where
  it overlaps the body or leaves it (:meth:`Inked.limb`), never along the flank;
* **few inner lines, left open**: the cheeks, the tail tip, a fluff in each ear, the philtrum and the
  paw creases are tapered strokes, not closed shapes (:meth:`Inked.details`), each a little lumpy;
* **a slight head tilt and an off-centre face**: the head turns about the neck, fading to nothing at the shoulders,
  and the face sits toward the far side, the far eye smaller;
* **eyes and mouths drawn for the face**: almond eyes with an iris that slant to the outer corner, a fox's mouth
  under the nose; every kind of :data:`srstudio.toon.EYES` and :data:`srstudio.toon.MOUTHS` and every viseme is its
  own drawing here, none the shared brush template (``sleepy``, ``yawn``, ``scream`` and ``puff`` too, ahead of
  the vocabulary the sloth, goat and hamster bring), and every eye a one-off: its almond, iris, pupil and shine are
  seeded lumps per kind and side (:func:`srstudio.brush.lump`), never a perfect ellipse;
* **a shade tone**: one darker coat (:data:`SHADE`) where the forms turn away, the head's a crescent that starts and
  ends on the outline and swells into the cheek, and a cream shade under the chin.

:data:`FOX_INKED` is a :class:`srstudio.toon_cast.Look` with this drawing, so it keeps the brush characters'
contract (every expression and arms, typing frames, blinks, lip sync, wear, :func:`srstudio.toon_cast.figure_shapes`
as data). It is the fox's version 2 (ADR 0047), the default for new reels; the fox of
:data:`srstudio.toon_cast.FOX` is version 1 and stays as it is.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import TYPE_CHECKING

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .head_motion import HeadStyle, Spring
from .registry import register
from .toon import LIPS, Pose, ToonDataError
from .toon_cast import CENTRE, FINE, FOX, HEART, INK, TEAR, TONGUE, VISEMES, Layer, Look, Mouths, figure
from .toon_head import HeadRig
from .toon_torso import arm_lines, depth_in

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "SHADE",
    "CREAM_SHADE",
    "IRIS",
    "INSIDE",
    "TILT",
    "Inked",
    "FOX_INK",
    "FOX_INKED",
    "FOX_MOTION",
    "FOX_RIG",
    "fox_inked",
]

SHADE = "#c2501f"  # the coat where the forms turn away from the light
CREAM_SHADE = "#ead2bd"  # the white under the chin
IRIS = "#e8a23a"
INSIDE = "#6b2230"  # an open mouth
TILT = -3.5  # degrees the head turns about the neck, anticlockwise
NECK: Point = (CENTRE, 700.0)
FADE = 90.0  # the tilt fades to nothing over this many px above the neck
SHIFT = 13.0  # the face sits this far toward the far (right) side

BODY_HAND = brush.Hand(light=0.62, heavy=1.5, toward=(0.45, 0.89), tips=0.7, grain=0.22, ragged=0.16)
EYE_HAND = brush.Hand(light=0.35, heavy=1.55, toward=(0.0, -1.0), tips=0.6, grain=0.12)  # a heavy upper lid
MOUTH_HAND = brush.Hand(light=0.5, heavy=1.3, toward=(0.0, 1.0), tips=0.5, grain=0.12)
ARM_TAPER = brush.Pressure(0.45, 1.1, 0.12, 0.04, 2.0)  # slim where it leaves the body, widest at forearm and paw
TUCK = (0.5, 10.0)  # an arm leaves the body this far inside the shoulder: limb widths in, px down
FUR = brush.Pressure(1.0, 0.2, 0.14, 0.16, 1.7)  # pressed at the root, lifted at the tip, unevenly
LINE = brush.Pressure(0.95, 0.35, 0.15, 0.14, 2.3)
GAP = 1.5  # a break in a body contour, in line weights
GLANCE_ROOM = 0.42  # eye radii an iris may be moved by a glance before it leaves the almond


def _tilt(points: Sequence[Point]) -> tuple[Point, ...]:
    """Head points turned :data:`TILT` about the neck, the turn fading out toward the shoulders."""
    out = []
    for x, y in points:
        a = math.radians(TILT * min(1.0, max(0.0, (NECK[1] - y) / FADE)))
        dx, dy = x - NECK[0], y - NECK[1]
        out.append(
            (
                round(NECK[0] + dx * math.cos(a) - dy * math.sin(a), 2),
                round(NECK[1] + dx * math.sin(a) + dy * math.cos(a), 2),
            )
        )
    return tuple(out)


def _face(points: Sequence[Point]) -> tuple[Point, ...]:
    """Face points moved toward the far side, then tilted with the head."""
    return _tilt([(x + SHIFT, y) for x, y in points])


def _hand(points: Sequence[Point], amount: float, seed: int, steps: int = 3) -> list[Point]:
    return brush.wobble(points, amount, steps=steps, seed=seed)


def _seed(*parts: str) -> int:
    """A seed that names what it draws, the same in every build (not :func:`hash`, which changes per run)."""
    return zlib.crc32("-".join(parts).encode())


def _inked_fill(
    points: Sequence[Point], colour: str, weight: float, seed: int, amount: float = 1.4, breaks: int = 3
) -> list[Layer]:
    """A pressed ink band broken in ``breaks`` places and the fill over it, both on the same hand-drifted contour."""
    contour = _hand(points, amount, seed)
    band = brush.broken(contour, weight, BODY_HAND, steps=1, breaks=breaks, gap=GAP * weight, seed=seed)
    return [(piece, "ink") for piece in band] + [(brush.outline(contour, steps=1), colour)]


def _fill(points: Sequence[Point], colour: str, seed: int, amount: float = 1.0) -> Layer:
    return (brush.outline(_hand(points, amount, seed), steps=1), colour)


def _line(points: Sequence[Point], weight: float, seed: int, pressure: brush.Pressure = FUR) -> Layer:
    """An inner line, drifting a little off the points it was placed on."""
    return (brush.stroke(brush.wobble(points, 0.9, closed=False, steps=3, seed=seed), weight, pressure, steps=2), "ink")


# -- the fox's body, at rest, before the tilt ------------------------------------------------------------------------
_SILHOUETTE = (
    (96.0, 520.0), (108.0, 503.0), (126.0, 492.0), (148.0, 485.0), (170.0, 482.0), (190.0, 481.0), (210.0, 483.0),
    (232.0, 488.0), (252.0, 497.0), (268.0, 510.0), (279.0, 527.0), (287.0, 548.0), (293.0, 570.0), (300.0, 590.0),
    (312.0, 598.0), (334.0, 606.0), (316.0, 616.0), (330.0, 632.0), (309.0, 636.0), (316.0, 652.0), (306.0, 664.0),
    (304.0, 680.0), (306.0, 689.0), (309.0, 697.0), (312.0, 706.0), (315.0, 714.0), (320.0, 734.0), (325.0, 758.0),
    (329.0, 792.0), (331.0, 830.0), (262.0, 833.0), (110.0, 832.0), (40.0, 830.0), (42.0, 792.0), (47.0, 756.0),
    (52.0, 734.0), (57.0, 715.0), (59.0, 706.0), (62.0, 698.0), (65.0, 682.0), (67.0, 674.0), (70.0, 666.0),
    (46.0, 651.0), (64.0, 637.0), (33.0, 624.0), (58.0, 613.0), (41.0, 598.0), (66.0, 592.0),
    (74.0, 572.0), (80.0, 551.0), (87.0, 534.0),
)  # the ruff runs into the shoulders and the flanks in one gentle curve, with no notch for the arms  # fmt: skip
_EARS = (
    (  # the near ear, standing
        (100.0, 542.0), (88.0, 508.0), (74.0, 474.0), (61.0, 441.0), (51.0, 412.0), (46.0, 393.0), (59.0, 396.0),
        (81.0, 408.0), (105.0, 428.0), (128.0, 452.0), (149.0, 474.0), (163.0, 494.0),
    ),
    (  # the far ear, a little turned
        (212.0, 490.0), (229.0, 467.0), (250.0, 443.0), (274.0, 421.0), (297.0, 405.0), (314.0, 397.0),
        (317.0, 414.0), (311.0, 441.0), (301.0, 471.0), (289.0, 501.0), (277.0, 528.0),
    ),
)  # fmt: skip
_EAR_INNER = (
    ((102.0, 520.0), (88.0, 488.0), (73.0, 452.0), (61.0, 424.0), (68.0, 422.0), (88.0, 438.0), (110.0, 458.0),
     (130.0, 478.0), (142.0, 496.0)),
    ((232.0, 494.0), (250.0, 466.0), (272.0, 444.0), (296.0, 424.0), (302.0, 428.0), (296.0, 454.0), (285.0, 484.0),
     (274.0, 512.0)),
)  # fmt: skip
_EAR_TIPS = (
    ((52.0, 420.0), (48.0, 402.0), (47.0, 394.0), (58.0, 397.0), (73.0, 405.0), (66.0, 412.0), (60.0, 424.0)),
    ((300.0, 406.0), (313.0, 398.0), (316.0, 410.0), (314.0, 424.0), (306.0, 420.0), (296.0, 418.0)),
)  # fmt: skip
_EAR_FLUFF = (((112.0, 506.0), (100.0, 484.0), (93.0, 462.0)), ((252.0, 500.0), (262.0, 476.0), (270.0, 460.0)))
_TAIL = (
    (300.0, 806.0), (318.0, 782.0), (337.0, 752.0), (352.0, 716.0), (360.0, 684.0), (361.0, 656.0), (356.0, 633.0),
    (347.0, 613.0), (369.0, 619.0), (383.0, 641.0), (389.0, 674.0), (384.0, 714.0), (370.0, 754.0), (348.0, 790.0),
    (322.0, 815.0),
)  # fmt: skip
_TAIL_TIP = (
    (351.0, 617.0), (368.0, 622.0), (380.0, 641.0), (385.0, 661.0), (376.0, 657.0), (370.0, 667.0), (364.0, 655.0),
    (360.0, 662.0), (358.0, 642.0),
)  # fmt: skip
_MASK = (
    (45.0, 626.0), (62.0, 617.0), (82.0, 609.0), (104.0, 603.0), (126.0, 600.0), (148.0, 602.0), (166.0, 609.0),
    (180.0, 619.0), (187.0, 629.0), (196.0, 620.0), (212.0, 610.0), (232.0, 603.0), (254.0, 601.0), (276.0, 605.0),
    (296.0, 611.0), (316.0, 619.0), (305.0, 631.0), (312.0, 645.0), (294.0, 648.0), (288.0, 661.0), (270.0, 668.0),
    (250.0, 676.0), (226.0, 684.0), (200.0, 688.0), (176.0, 688.0), (150.0, 684.0), (126.0, 676.0), (110.0, 668.0),
    (93.0, 661.0), (73.0, 663.0), (82.0, 649.0), (58.0, 645.0), (70.0, 635.0),
)  # fmt: skip
_BIB = (
    (128.0, 694.0), (156.0, 684.0), (185.0, 682.0), (216.0, 685.0), (242.0, 695.0), (256.0, 724.0), (264.0, 762.0),
    (262.0, 800.0), (240.0, 822.0), (185.0, 832.0), (130.0, 822.0), (108.0, 800.0), (106.0, 762.0), (114.0, 724.0),
)  # fmt: skip
_CHIN = (
    (146.0, 690.0), (170.0, 697.0), (196.0, 698.0), (222.0, 693.0), (238.0, 688.0), (228.0, 701.0), (208.0, 710.0),
    (184.0, 712.0), (162.0, 707.0),
)  # fmt: skip
_HEAD_SHADE = brush.crescent(_SILHOUETTE[7:14], 24.0, (185.0, 580.0))  # the crown's far side down into the cheek
_FLANK_SHADE = (
    (296.0, 714.0), (309.0, 728.0), (317.0, 756.0), (322.0, 790.0), (324.0, 826.0), (302.0, 826.0), (300.0, 792.0),
    (295.0, 758.0), (288.0, 732.0),
)  # fmt: skip
_TAIL_SHADE = (
    (372.0, 690.0), (382.0, 676.0), (384.0, 712.0), (371.0, 752.0), (350.0, 786.0), (330.0, 804.0), (346.0, 776.0),
    (362.0, 742.0),
)  # fmt: skip
_HEAD_STROKES = (
    ((72.0, 640.0), (88.0, 650.0), (98.0, 663.0)),  # the cheek line under the ruff
    ((300.0, 640.0), (287.0, 652.0)),
)
_BODY_STROKES = (
    ((382.0, 662.0), (372.0, 657.0), (367.0, 666.0), (360.0, 655.0)),  # where the tail turns white
)
_NOSE = ((-11.0, -6.0), (-4.0, -8.5), (5.0, -8.0), (11.5, -5.0), (8.0, 1.5), (2.0, 7.0), (-3.0, 6.0), (-9.0, 1.0))
NOSE_AT: Point = (185.0, 622.0)
EYES_AT: tuple[Point, Point] = ((150.0, 566.0), (222.0, 564.0))
MOUTH_AT: Point = (185.0, 648.0)


def _muzzle() -> list[Point]:
    """The white of the face: the muzzle follows the face; the ruff stays inside the outline it runs along."""
    return [
        (x + SHIFT, y) if 140.0 < x < 236.0 else (185.0 + (x - 185.0) * 0.92 + SHIFT / 2, 640.0 + (y - 640.0) * 0.96)
        for x, y in _MASK
    ]


def _fox_base() -> tuple[tuple[Layer, ...], tuple[Layer, ...]]:
    """The fox at rest without arms or face (tail, ears, body, shade, white, inner lines) and its inner lines."""
    light, dark = FOX.light, FOX.paw
    layers: list[Layer] = []
    layers += _inked_fill(_TAIL, FOX.coat, INK, seed=1)
    layers.append(_fill(_TAIL_SHADE, SHADE, seed=2, amount=0.6))
    layers.append(_fill(_TAIL_TIP, light, seed=3, amount=0.5))
    for k, ear in enumerate(_EARS):
        layers += _inked_fill(_tilt(ear), FOX.coat, INK, seed=4 + k)
        layers.append(_fill(_tilt(_EAR_INNER[k]), light, seed=6 + k, amount=0.8))
        layers.append(_fill(_tilt(_EAR_TIPS[k]), dark, seed=8 + k, amount=0.4))
    layers += _inked_fill(_tilt(_SILHOUETTE), FOX.coat, INK * 1.05, seed=10, amount=1.6, breaks=4)
    layers.append(_fill(_tilt(_HEAD_SHADE), SHADE, seed=11, amount=0.8))
    layers.append(_fill(_FLANK_SHADE, SHADE, seed=12, amount=0.8))
    layers.append(_fill(_BIB, light, seed=13))
    layers.append(_fill(_tilt(_muzzle()), light, seed=14, amount=1.2))
    layers.append(_fill(_tilt(_CHIN), CREAM_SHADE, seed=15, amount=0.8))
    nose_x, nose_y = _face([NOSE_AT])[0]
    strokes: list[Layer] = [_line(_tilt(s), FINE * 1.1, 20 + k) for k, s in enumerate(_EAR_FLUFF)]
    strokes += [_line(_tilt(s), FINE * 1.25, 30 + k) for k, s in enumerate(_HEAD_STROKES)]
    strokes += [_line(s, FINE * 1.15, 40 + k) for k, s in enumerate(_BODY_STROKES)]
    philtrum = [(nose_x, nose_y + 8.0), (nose_x + 0.8, nose_y + 18.0)]
    strokes.append(_line(philtrum, FINE * 1.2, 50, LINE))
    return tuple(layers + strokes), tuple(strokes)


# -- the face ------------------------------------------------------------------------------------------------------
# the open eye as an almond in units of the eye radius: u toward the nose, v down; the outer corner rides high
ALMOND = (
    (1.08, 0.2), (0.78, -0.42), (0.36, -0.86), (-0.12, -1.0), (-0.58, -0.86), (-0.92, -0.5), (-1.1, -0.12),
    (-0.98, 0.32), (-0.62, 0.7), (-0.12, 0.88), (0.38, 0.8), (0.82, 0.52),
)  # fmt: skip
_LOOK = {  # where the iris looks: (across the frame, +1 to the right; down), eye radii
    "wide": (0.0, 0.02),
    "half": (0.0, 0.18),
    "left": (-0.38, 0.05),
    "up": (0.0, -0.28),
    "down": (0.0, 0.3),
    "side": (0.38, 0.1),
    "narrow": (0.0, 0.12),
    "shock": (0.0, 0.0),
    "roll": (0.28, -0.3),
    "teary": (0.0, 0.06),
    "sleepy": (0.04, 0.36),
}
_LID = {  # a lid over the top of the eye, its edge (outer, inner) this far down
    "half": (-0.14, -0.02),
    "down": (0.22, 0.32),
    "side": (-0.32, -0.2),
    "narrow": (-0.6, 0.06),
    "sleepy": (0.34, 0.14),  # hung past the middle, drooping to the outer corner
}
_BROW = {  # (lift over the eye in px, the inner end's rise, the middle's rise, the outer end's rise) in eye radii
    "wide": (10.0, 0.0, 0.16, 0.0),
    "half": (4.0, 0.0, 0.06, 0.04),
    "left": (8.0, 0.0, 0.12, 0.08),
    "up": (16.0, 0.0, 0.3, 0.02),
    "down": (2.0, -0.04, 0.04, 0.0),
    "side": (6.0, -0.08, 0.08, 0.14),
    "closed": (4.0, 0.0, 0.1, 0.0),
    "narrow": (0.0, -0.5, -0.04, 0.22),
    "shock": (20.0, 0.06, 0.36, 0.0),
    "roll": (12.0, 0.18, 0.22, -0.08),
    "teary": (8.0, 0.45, 0.12, -0.2),
    "wince": (2.0, 0.5, 0.1, -0.24),
    "hearts": (10.0, 0.04, 0.34, 0.04),
    "sleepy": (3.0, 0.0, 0.02, -0.1),
}
BROW = brush.Pressure(1.0, 0.25, 0.12, 0.1, 1.5)  # pressed at the inner end


def _heart(cx: float, cy: float, size: float) -> tuple[Point, ...]:
    """A heart drawn by hand: the near lobe fuller than the far one, the point a little off the axis."""
    out = []
    for k in range(24):
        t = 2 * math.pi * k / 24
        x = 16.0 * math.sin(t) ** 3
        y = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        x *= 1.08 if x < 0 else 0.94
        out.append((round(cx + (x + 0.06 * (y + 17.0)) * size / 16.0, 2), round(cy + (y - 2.5) * size / 16.0, 2)))
    return tuple(out)


def _drop(x: float, y: float, scale: float) -> tuple[Point, ...]:
    drop = ((0.0, 0.0), (4.0, 7.0), (6.5, 14.0), (4.5, 19.0), (-0.5, 21.0), (-5.5, 17.0), (-6.0, 11.0), (-3.5, 5.0))
    return tuple((round(x + dx * scale, 2), round(y + dy * scale, 2)) for dx, dy in drop)


@dataclass(frozen=True)
class Inked:
    """A :class:`srstudio.toon_cast.Drawing` for a look drawn like the traced cat: ``base`` is the body at rest
    (with its inner lines, ``strokes``), the head turned ``tilt`` degrees; the near (left) eye is ``sizes[0]`` and
    the far one ``sizes[1]`` of the look's eye radius; ``iris`` and ``inside`` colour the eyes and an open
    mouth."""

    base: tuple[Layer, ...]
    strokes: tuple[Layer, ...]
    tilt: float
    sizes: tuple[float, float]
    iris: str
    inside: str
    glance: Point = (0.0, 0.0)  # the iris this many eye radii off where the kind of eye puts it

    def looking(self, dx: float, dy: float) -> Inked:
        """This drawing with its irises ``dx`` and ``dy`` eye radii off (:class:`srstudio.toon_head.Glancing`)."""
        return replace(self, glance=(dx, dy))

    def _iris(self, kind: str) -> Point:
        """Where the iris of ``kind`` looks, a glance moving it no further than the almond has room for."""
        dx, dv = _LOOK[kind]
        if self.glance == (0.0, 0.0):
            return dx, dv
        room = GLANCE_ROOM
        return max(-room, min(room, dx + self.glance[0])), max(-room, min(room, dv + self.glance[1]))

    def foundation(self, look: Look) -> list[Layer]:
        return list(self.base)

    def details(self, look: Look) -> list[Layer]:
        """The inner lines: open tapered strokes, every one also in :meth:`foundation`."""
        return list(self.strokes)

    def _turn(self, layers: list[Layer], centre: Point) -> list[Layer]:
        return [(brush.rotate(s, centre[0], centre[1], self.tilt), c) for s, c in layers]

    def eye(self, look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
        """One eye of ``kind``, drawn for this face: ``inner`` is +1 for the near eye (the nose to its right)."""
        if kind not in _BROW:
            raise ToonDataError(f"{look.name}: no eyes {kind!r} drawn for this face")
        ex, ey = centre
        r = look.eye_r * (self.sizes[0] if inner > 0 else self.sizes[1])
        lid = look.lid or look.coat

        def at(u: float, v: float, scale: float = 1.0) -> Point:
            return (ex + inner * u * r * scale, ey + v * r * scale)

        side = "near" if inner > 0 else "far"

        def lump(x: float, y: float, rx: float, ry: float, part: str, amount: float, tilt: float = 0.0) -> Shape:
            return brush.lump(x, y, rx, ry, amount, seed=_seed(part, kind, side), tilt=tilt, points=6)

        lift, rise_in, rise_mid, rise_out = _BROW[kind]
        v0 = -1.0 - (INK + lift) / r
        brow = [at(0.9, v0 - rise_in), at(0.05, v0 - rise_mid), at(-1.0, v0 - rise_out)]
        out: list[Layer] = [(brush.stroke(brow, INK * 1.05, BROW, steps=6), "ink")]
        if kind == "closed":
            arc = [at(1.05, 0.16), at(0.25, 0.48), at(-0.5, 0.42), at(-1.1, 0.04)]
            out += [(brush.stroke(arc, INK * 1.1, LINE, steps=6), "ink")]
            out += [(brush.stroke([at(-1.05, 0.06), at(-1.36, -0.14)], FINE, FUR, steps=4), "ink")]  # a lash
            return self._turn(out, centre)
        if kind == "wince":  # squeezed shut toward the nose, a crease under it
            out += [
                (brush.stroke([at(-1.05, -0.55), at(-0.2, -0.24), at(0.85, 0.06)], INK, LINE, steps=6), "ink"),
                (brush.stroke([at(-1.0, 0.62), at(-0.2, 0.36), at(0.85, 0.1)], INK * 0.9, LINE, steps=6), "ink"),
                (brush.stroke([at(-0.75, 1.0), at(-0.2, 1.12), at(0.2, 1.08)], FINE * 0.9, FUR, steps=4), "ink"),
            ]
            return self._turn(out, centre)
        if kind == "hearts":
            heart = _heart(ex, ey + 1.0, r * 1.22)
            out += [(brush.inked(heart, INK, EYE_HAND), "ink"), (brush.outline(heart), HEART)]
            out.append((lump(ex - 0.42 * r, ey - 0.42 * r, 0.2 * r, 0.14 * r, "shine", 0.2, -30.0), "white"))
            return self._turn(out, centre)
        scale = 1.22 if kind == "shock" else 1.0
        stretch = 1.1 if kind == "shock" else 1.0  # a shocked eye opens round
        rng = random.Random(_seed("almond", kind, side))  # no two eyes drawn alike
        almond = [at(u + rng.uniform(-0.07, 0.07), v * stretch + rng.uniform(-0.07, 0.07), scale) for u, v in ALMOND]
        out += [(brush.inked(almond, INK, EYE_HAND), "ink"), (brush.outline(almond), "white")]
        dx, dv = self._iris(kind)
        ix, iy = ex + dx * r, ey + dv * r
        if kind == "shock":  # a pinpoint: no iris to see
            out.append((lump(ix, iy, 0.17 * r, 0.2 * r, "pupil", 0.14), "ink"))
            out.append((lump(ix - 0.06 * r, iy - 0.08 * r, 0.07 * r, 0.06 * r, "shine", 0.2), "white"))
        else:
            ri, rp = (0.64, 0.42) if kind == "teary" else (0.56, 0.3)
            out.append((lump(ix, iy, ri * r, ri * r * 1.06, "iris", 0.08), self.iris))
            out.append((lump(ix + inner * 0.03 * r, iy + 0.02 * r, rp * r * 0.86, rp * r * 1.08, "pupil", 0.12), "ink"))
            out.append((lump(ix - 0.22 * r, iy - 0.24 * r, 0.13 * r, 0.11 * r, "shine", 0.22, -20.0), "white"))
        if kind in _LID:
            v_out, v_in = _LID[kind]
            out.append(
                (brush.outline([at(-1.5, -1.45), at(1.4, -1.45), at(1.4, v_in), at(0.1, (v_in + v_out) / 2 + 0.06),
                                at(-1.5, v_out)], steps=3), lid)
            )  # fmt: skip
            edge = [at(1.12, v_in + 0.04), at(0.1, (v_in + v_out) / 2 + 0.07), at(-1.14, v_out)]
            out.append((brush.stroke(edge, INK * 1.15, LINE, steps=6), "ink"))
        elif kind == "roll":  # the lower lid risen: the bored half of an eye roll
            out.append(
                (brush.outline([at(-1.5, 0.34), at(0.0, 0.26), at(1.4, 0.4), at(1.4, 1.4), at(-1.5, 1.4)], steps=3),
                 lid)
            )  # fmt: skip
            out.append((brush.stroke([at(-1.12, 0.36), at(0.0, 0.27), at(1.1, 0.42)], INK, LINE, steps=6), "ink"))
        elif kind == "teary":  # glistening, a welling line and a tear at the outer corner
            out.append((lump(ix + 0.24 * r, iy + 0.26 * r, 0.08 * r, 0.08 * r, "glint", 0.22), "white"))
            well = [at(-0.8, 0.6), at(-0.2, 0.74), at(0.5, 0.66)]
            out.append((brush.stroke(well, FINE * 1.2, brush.EVEN, steps=6), TEAR))
            tear = _drop(at(-0.95, 0.5)[0], ey + 0.7 * r, r / 17.0)
            out += [(brush.inked(tear, FINE, MOUTH_HAND), "ink"), (brush.outline(tear), TEAR)]
        if kind == "sleepy":  # a tired line under the eye
            out.append(
                (brush.stroke([at(-0.62, 1.22), at(0.0, 1.36), at(0.55, 1.24)], FINE * 0.85, FUR, steps=4), "ink")
            )
        return self._turn(out, centre)

    def lids(self, look: Look) -> list[Layer]:
        """Both eyes shut for a blink: a lid over each (big enough for a shocked eye) and the closed line."""
        lid = look.lid or look.coat
        out: list[Layer] = []
        for (ex, ey), inner, size in zip(look.eyes, (1.0, -1.0), self.sizes, strict=True):
            r = look.eye_r * size

            def at(u: float, v: float, ex: float = ex, ey: float = ey, inner: float = inner, r: float = r) -> Point:
                return (ex + inner * u * r, ey + v * r)

            cover = [at(u * 1.5, v * 1.52) for u, v in ALMOND]
            arc = [at(1.05, 0.16), at(0.25, 0.48), at(-0.5, 0.42), at(-1.1, 0.04)]
            layers: list[Layer] = [
                (brush.outline(cover), lid),
                (brush.stroke(arc, INK * 1.1, LINE, steps=6), "ink"),
                (brush.stroke([at(-1.05, 0.06), at(-1.36, -0.14)], FINE, FUR, steps=4), "ink"),
            ]
            out += self._turn(layers, (ex, ey))
        return out

    def mouth(self, look: Look, kind: str) -> list[Layer]:
        """A mouth of ``kind`` under the nose, drawn for a fox's muzzle."""
        mx, my = look.mouth
        w = look.mouth_w

        def at(x: float, y: float) -> Point:
            return (mx + x * w, my + y)

        def half(points: Sequence[Point], weight: float = INK * 0.95) -> Layer:
            return (brush.stroke([at(x, y) for x, y in points], weight, LINE, steps=6), "ink")

        def opening(points: Sequence[Point], fill: str, weight: float = INK * 0.85) -> list[Layer]:
            pts = [at(x, y) for x, y in points]
            return [(brush.inked(pts, weight, MOUTH_HAND), "ink"), (brush.outline(pts), fill)]

        def tongue(points: Sequence[Point]) -> Layer:
            return (brush.outline([at(x, y) for x, y in points]), TONGUE)

        out: list[Layer]
        if kind == "none":
            return []
        if kind == "flat":
            out = [half([(0.0, 0.0), (-0.18, 3.5), (-0.38, 3.0), (-0.52, -1.5)]),
                   half([(0.0, 0.0), (0.16, 3.0), (0.34, 2.5), (0.46, -0.5)])]  # fmt: skip
        elif kind == "smirk":
            out = [half([(0.0, 0.0), (-0.16, 2.5), (-0.34, 2.0)]),
                   half([(0.0, 0.0), (0.2, 2.0), (0.4, -3.0), (0.56, -9.0)]),
                   half([(0.5, -14.0), (0.6, -9.5), (0.57, -4.0)], FINE)]  # fmt: skip
        elif kind == "wave":
            out = [half([(-0.5, 0.0), (-0.25, -4.0), (0.0, 1.0), (0.22, 5.0), (0.48, -1.0)])]
        elif kind == "frown":
            out = [half([(-0.5, 7.0), (-0.2, -2.0), (0.1, -3.0), (0.46, 5.0)]),
                   half([(-0.12, 14.0), (0.0, 15.5), (0.12, 15.0)], FINE)]  # fmt: skip
        elif kind == "open":
            out = opening([(-0.46, -1.0), (-0.22, 2.0), (0.0, 0.0), (0.22, 2.0), (0.44, -1.0), (0.4, 9.0),
                           (0.2, 16.0), (0.0, 18.0), (-0.22, 16.0), (-0.42, 9.0)], self.inside)  # fmt: skip
            out.append(tongue([(-0.26, 14.0), (-0.1, 9.0), (0.08, 9.5), (0.26, 13.0), (0.12, 16.5), (-0.12, 16.5)]))
        elif kind == "round":
            out = opening([(0.0, -1.0), (0.24, 3.0), (0.3, 10.0), (0.2, 17.0), (0.0, 19.0), (-0.2, 17.0),
                           (-0.28, 10.0), (-0.22, 3.0)], self.inside)  # fmt: skip
            out.append(tongue([(-0.16, 15.0), (0.0, 12.0), (0.16, 14.5), (0.08, 17.5), (-0.1, 17.5)]))
        elif kind == "o":
            out = opening([(0.0, -1.0), (0.17, 2.0), (0.22, 8.0), (0.14, 14.0), (-0.02, 16.0), (-0.18, 13.0),
                           (-0.21, 7.0), (-0.14, 1.5)], self.inside)  # fmt: skip
        elif kind == "drop":
            out = opening([(0.0, -2.0), (0.26, 4.0), (0.32, 16.0), (0.22, 26.0), (0.0, 30.0), (-0.22, 26.0),
                           (-0.32, 16.0), (-0.26, 4.0)], self.inside)  # fmt: skip
            out.append(tongue([(-0.22, 25.0), (0.0, 20.0), (0.2, 24.0), (0.1, 28.5), (-0.12, 28.5)]))
        elif kind == "grin":
            out = opening([(-0.5, -3.0), (0.0, 1.0), (0.5, -4.0), (0.38, 6.0), (0.0, 14.0), (-0.36, 6.0)], "white")
            out += [half([(-0.42, 1.0), (0.0, 4.5), (0.42, 0.0)], FINE * 0.8),
                    half([(-0.6, -7.0), (-0.56, -2.0)], FINE), half([(0.6, -8.0), (0.57, -3.0)], FINE)]  # fmt: skip
        elif kind == "grimace":  # clenched teeth, wider than the mouth, strain at the corners
            out = opening([(-0.62, -8.0), (-0.2, -9.0), (0.2, -8.5), (0.62, -7.0), (0.66, 0.0), (0.6, 8.0),
                           (0.2, 9.0), (-0.2, 8.5), (-0.62, 8.0), (-0.66, 0.0)], "white")  # fmt: skip
            out.append(half([(-0.6, 0.0), (-0.2, 1.0), (0.2, -0.5), (0.6, 0.5)], FINE * 0.8))
            for x, lean in ((-0.4, 0.5), (-0.13, -0.3), (0.15, 0.4), (0.4, -0.4)):
                out.append(half([(x - 0.01 * lean, -7.0), (x + 0.01 * lean, 7.0)], FINE * 0.7))
            out += [half([(-0.72, -11.0), (-0.79, -2.0)], FINE), half([(0.73, -10.0), (0.8, -1.0)], FINE)]
        elif kind == "tongue":
            out = [half([(-0.5, -2.0), (-0.2, 4.0), (0.15, 4.5), (0.5, -3.0)])]
            pts = [at(x, y) for x, y in ((0.0, 3.5), (0.32, 2.5), (0.34, 13.0), (0.18, 20.0), (0.02, 14.0))]
            out += [(brush.inked(pts, FINE, MOUTH_HAND), "ink"), (brush.outline(pts), TONGUE)]
            out.append(half([(0.17, 6.0), (0.18, 13.0)], FINE * 0.6))
            out.append(out.pop(0))  # the lips over the tongue's root
        elif kind == "yawn":  # the jaw dropped, tall and narrow, the tongue lying low
            out = opening([(0.0, -4.0), (0.2, -2.0), (0.34, 6.0), (0.36, 18.0), (0.28, 28.0), (0.0, 33.0),
                           (-0.28, 28.0), (-0.36, 18.0), (-0.32, 6.0), (-0.18, -2.0)], self.inside)  # fmt: skip
            out.append(tongue([(-0.24, 27.0), (-0.08, 21.0), (0.1, 22.0), (0.25, 27.0), (0.1, 31.0), (-0.12, 31.0)]))
            out.append(half([(0.0, 23.0), (0.01, 28.5)], FINE * 0.6))
        elif kind == "scream":  # wide open, the top row of teeth bared and the tongue showing
            out = opening([(-0.6, -6.0), (-0.2, -8.0), (0.2, -7.5), (0.62, -5.0), (0.56, 10.0), (0.42, 24.0),
                           (0.02, 31.0), (-0.4, 24.0), (-0.58, 10.0)], self.inside)  # fmt: skip
            out.append(tongue([(-0.34, 25.0), (-0.1, 17.0), (0.16, 18.0), (0.36, 24.0), (0.12, 29.0), (-0.16, 29.0)]))
            out.append((brush.outline([at(x, y) for x, y in ((-0.46, -4.5), (0.0, -5.5), (0.48, -3.5), (0.44, 2.5),
                                                              (0.0, 1.5), (-0.44, 2.5))]), "white"))  # fmt: skip
            for x, lean in ((-0.22, 0.4), (0.02, -0.3), (0.25, 0.3)):
                out.append(half([(x - 0.01 * lean, -5.0), (x + 0.01 * lean, 2.0)], FINE * 0.6))
            out += [half([(-0.7, -10.0), (-0.78, -1.0)], FINE), half([(0.72, -9.0), (0.8, 0.0)], FINE)]
        elif kind == "puff":  # the cheeks blown out round a small closed smile
            out = [half([(side * 0.62, -18.0), (side * 0.86, -7.0), (side * 0.86, 5.0), (side * 0.66, 14.0)])
                   for side in (-1.0, 1.0)]  # fmt: skip
            out += [half([(-0.18, -1.0), (0.0, 3.0), (0.2, -1.5)], INK * 0.85),
                    half([(0.2, -1.5), (0.27, -4.5)], FINE), half([(-0.18, -1.0), (-0.25, -3.5)], FINE)]  # fmt: skip
        elif kind == "kiss":
            pts = [(mx + x, my + y) for x, y in ((-2.0, -8.0), (5.0, -6.0), (8.0, -2.0), (4.0, 0.0), (8.0, 3.0),
                                                  (5.0, 7.5), (-2.0, 8.5), (-4.5, 0.0))]  # fmt: skip
            out = [(brush.inked(pts, FINE * 1.2, MOUTH_HAND), "ink"), (brush.outline(pts), LIPS)]
            out += [half([(-0.2, -5.0), (-0.25, 0.0), (-0.2, 5.0)], FINE * 0.8), half([(0.02, 0.0), (0.1, 0.0)], FINE)]
        else:
            raise ToonDataError(f"{look.name}: no mouth {kind!r} drawn for this face")
        return self._turn(out, look.mouth)

    def viseme(self, look: Look, kind: str) -> list[Layer]:
        """A speaking mouth, drawn for the muzzle: ``open`` with the tongue showing, ``round``, ``teeth`` a bite."""
        mx, my = look.mouth
        w = look.mouth_w

        def opening(points: Sequence[Point], fill: str) -> list[Layer]:
            pts = [(mx + x * w, my + y) for x, y in points]
            return [(brush.inked(pts, INK * 0.85, MOUTH_HAND), "ink"), (brush.outline(pts), fill)]

        if kind == "open":
            out = opening([(-0.4, 0.0), (0.0, 1.5), (0.4, -0.5), (0.36, 10.0), (0.02, 19.0), (-0.36, 10.0)],
                          self.inside)  # fmt: skip
            tip = [(mx + x * w, my + y) for x, y in ((-0.2, 14.0), (0.0, 11.0), (0.2, 13.5), (0.02, 17.5))]
            out.append((brush.outline(tip), TONGUE))
        elif kind == "round":
            out = opening([(0.0, 0.0), (0.18, 3.5), (0.21, 10.0), (0.14, 17.0), (0.0, 19.0), (-0.15, 16.5),
                           (-0.2, 9.5), (-0.15, 3.0)], self.inside)  # fmt: skip
        elif kind == "teeth":
            out = opening([(-0.46, -2.0), (0.0, -1.0), (0.46, -3.0), (0.44, 5.0), (0.0, 8.5), (-0.44, 5.0)], "white")
            bite = [(mx + x * w, my + y) for x, y in ((-0.36, 2.5), (0.0, 3.5), (0.36, 2.0))]
            out.append((brush.stroke(bite, FINE * 0.7, brush.EVEN, steps=6), "ink"))
        else:
            raise ToonDataError(f"{look.name}: no viseme {kind!r}; the visemes are {VISEMES}")
        return self._turn(out, look.mouth)

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]:
        """An arm the way the cat's are drawn: it leaves the body inside the shoulder (:data:`TUCK`), slim there and
        widest at the forearm and paw, one form with the body where it lies along the flank and inked only where it
        overlaps the body or leaves it (:func:`srstudio.toon_torso.arm_lines`); and a mitten of a paw, its line
        broken, with curved creases."""
        w = look.limb
        (sx, sy), *rest = points
        inward = 1.0 if sx < CENTRE else -1.0
        start = (sx + inward * TUCK[0] * w, sy + TUCK[1])
        path = [start, *rest]
        if depth_in(look.silhouette, rest[0])[0] < 0.0:  # reaching out: the upper arm hangs inside, the forearm leaves
            path.insert(1, (start[0] + (rest[0][0] - start[0]) * 0.25, rest[0][1]))
        out: list[Layer] = [(brush.stroke(path, w, ARM_TAPER), look.coat)]
        out += [(line, "ink") for line in arm_lines(path, w, look.silhouette, ARM_TAPER, INK * 1.1)]
        px, py = paw
        rx, ry = w * 0.74, w * 0.52
        mitten = [
            (
                px + rx * math.cos(t) * (1.06 if math.cos(t) > 0 else 0.96),
                py + ry * math.sin(t) * (1.1 if t > 0 else 1.0),
            )
            for t in (2 * math.pi * k / 10 - math.pi / 2 for k in range(10))
        ]
        seed = int(px + py) % 7
        contour = brush.wobble(mitten, 0.7, steps=3, seed=seed)
        band = brush.broken(contour, INK * 0.95, BODY_HAND, steps=1, breaks=3, gap=GAP * INK * 0.95, seed=seed)
        out += [(piece, "ink") for piece in band] + [(brush.outline(contour, steps=1), look.paw or look.coat)]
        if toes:
            for dx in (-w * 0.22, w * 0.2):
                x = px + dx
                crease = [(x - 1.0, py - w * 0.44), (x + 1.0, py - w * 0.28), (x + 0.2, py - w * 0.12)]
                out.append((brush.stroke(crease, FINE, FUR, steps=4), "ink"))
        return out


_BASE, _STROKES = _fox_base()
FOX_INK = Inked(_BASE, _STROKES, TILT, (1.05, 0.93), IRIS, INSIDE)
FOX_INKED = Look(
    name="fox-inked",
    coat=FOX.coat,
    dark=FOX.dark,
    light=FOX.light,
    silhouette=_tilt(_SILHOUETTE),
    eyes=(_face([EYES_AT[0]])[0], _face([EYES_AT[1]])[0]),
    eye_r=17.0,
    mouth=_face([MOUTH_AT])[0],
    mouth_w=38.0,
    limb=FOX.limb,
    ears=tuple(_tilt(ear) for ear in _EARS),
    nose=(
        brush.outline(_face([(NOSE_AT[0] + x, NOSE_AT[1] + y) for x, y in _NOSE])),
        brush.rotate(
            brush.lump(
                NOSE_AT[0] + SHIFT - 4.0, NOSE_AT[1] - 4.0, 3.6, 2.0, 0.2, seed=_seed("nose"), tilt=-12.0, points=6
            ),
            *NECK,
            TILT,
        ),
    ),
    ear=FOX.coat,
    ear_inner=FOX.light,
    brows=True,
    shine=True,
    blink=FOX.blink,
    paw=FOX.paw,
    drawing=FOX_INK,
)


FOX_MOTION = HeadStyle(  # sly: more cock of the head than nod, and the eyes go long before the head does
    seed=4048,
    signature="~",
    nod_px=6.0,
    nod_roll=2.6,
    head=Spring(2.2, 0.6, 0.1),
    settle=Spring(1.1, 0.7),
    body=Spring(1.2, 0.9),
    min_gap=0.5,
    lean=1.0,
    idle_roll=1.6,
    idle_px=0.9,
    idle_hz=0.18,
    breath_period=4.6,
    glance_every=3.0,
    glance_hold=1.6,
    glance_turn=1.8,
    glance_face=3.0,
    avert=0.7,
)
_HEAD = (*_SILHOUETTE[41:], *_SILHOUETTE[:21])  # from the left of the neck over the crown to the right, ruff and all
_JAW = ((286.0, 678.0), (262.0, 688.0), (232.0, 698.0), (200.0, 704.0), (170.0, 704.0), (138.0, 698.0),
        (108.0, 688.0), (84.0, 676.0))  # fmt: skip
_BODY_TOP = ((86.0, 655.0), (130.0, 632.0), (185.0, 624.0), (232.0, 640.0), (250.0, 664.0))


def _shifted(points: Sequence[Point]) -> list[Point]:
    return [(x + SHIFT, y) for x, y in points]


@lru_cache(maxsize=1)
def _fox_skull() -> tuple[Layer, ...]:
    """The head alone, ruff and ears, closed under the chin, untilted: the rig turns it."""
    layers: list[Layer] = []
    for k, ear in enumerate(_EARS):
        layers += _inked_fill(ear, FOX.coat, INK, seed=4 + k)
        layers.append(_fill(_EAR_INNER[k], FOX.light, seed=6 + k, amount=0.8))
        layers.append(_fill(_EAR_TIPS[k], FOX.paw, seed=8 + k, amount=0.4))
    layers += _inked_fill((*_HEAD, *_JAW), FOX.coat, INK * 1.05, seed=10, amount=1.6, breaks=4)
    layers.append(_fill(_HEAD_SHADE, SHADE, seed=11, amount=0.8))
    layers += [_line(s, FINE * 1.1, 20 + k) for k, s in enumerate(_EAR_FLUFF)]
    layers += [_line(s, FINE * 1.25, 30 + k) for k, s in enumerate(_HEAD_STROKES)]
    return tuple(layers)


@lru_cache(maxsize=1)
def _fox_face() -> tuple[Layer, ...]:
    """What slides across the head: the white of the face and the philtrum."""
    nose_x, nose_y = _shifted([NOSE_AT])[0]
    philtrum = [(nose_x, nose_y + 8.0), (nose_x + 0.8, nose_y + 18.0)]
    return (_fill(_muzzle(), FOX.light, seed=14, amount=1.2), _line(philtrum, FINE * 1.2, 50, LINE))


@lru_cache(maxsize=1)
def _fox_trunk() -> tuple[Layer, ...]:
    """The tail and the body, its top run up behind the head, the bib and the shadow under the chin."""
    layers = _inked_fill(_TAIL, FOX.coat, INK, seed=1)
    layers.append(_fill(_TAIL_SHADE, SHADE, seed=2, amount=0.6))
    layers.append(_fill(_TAIL_TIP, FOX.light, seed=3, amount=0.5))
    layers += _inked_fill((*_SILHOUETTE[21:41], *_BODY_TOP), FOX.coat, INK * 1.05, seed=10, amount=1.6, breaks=4)
    layers.append(_fill(_FLANK_SHADE, SHADE, seed=12, amount=0.8))
    layers.append(_fill(_BIB, FOX.light, seed=13))
    layers.append(_fill(_CHIN, CREAM_SHADE, seed=15, amount=0.8))
    layers += [_line(s, FINE * 1.15, 40 + k) for k, s in enumerate(_BODY_STROKES)]
    return tuple(layers)


FOX_RIG = HeadRig(
    look=replace(
        FOX_INKED,
        eyes=(_shifted([EYES_AT[0]])[0], _shifted([EYES_AT[1]])[0]),
        mouth=_shifted([MOUTH_AT])[0],
        nose=(
            brush.outline(_shifted([(NOSE_AT[0] + x, NOSE_AT[1] + y) for x, y in _NOSE])),
            brush.lump(
                NOSE_AT[0] + SHIFT - 4.0, NOSE_AT[1] - 4.0, 3.6, 2.0, 0.2, seed=_seed("nose"), tilt=-12.0, points=6
            ),
        ),
        drawing=Inked((), (), 0.0, FOX_INK.sizes, IRIS, INSIDE),
    ),
    neck=NECK,
    tilt=TILT,
    head=(*_HEAD, *_JAW),
    cover=(_SILHOUETTE[40], *_BODY_TOP, _SILHOUETTE[21]),
    skull=_fox_skull,
    face=_fox_face,
    trunk=_fox_trunk,
    style=FOX_MOTION,
    head_over=True,
    free=45.0,
)


@register(
    "character",
    "toon-fox@2",
    summary="The fox drawn like the traced cat: pressed uneven ink, open fur lines, a shade tone, a tilted head, "
    "its own almond eyes and muzzle mouths; the whole brush contract",
)
def fox_inked(
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
    return figure(cv, parent, FOX_INKED, poses, duration, taps, enter, stickers, mouths, limbs=limbs)
