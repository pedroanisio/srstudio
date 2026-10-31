"""Three more Toon characters with drawings of their own: a sloth, a goat and a hamster, and the expressions they
bring to every brush character (ADR 0045).

The older brush cast (:mod:`srstudio.toon_cast`) is drawn from a :class:`~srstudio.toon_cast.Look`'s fields with one
shared face: symmetric, few points, an even line. These three carry a :class:`Critter`, a
:class:`srstudio.toon_cast.Drawing` of their own, drawn the way the traced cat reads:

* **dense, asymmetric contours**: every outline is placed by hand, unmirrored, and drifts a little like a hand
  following it (:func:`drifted`);
* **a pressed line** (:func:`pressed`): the ink band under a fill is heavier where the form turns from the light (the
  bottom and the back) and thins where the outline turns sharply, where a brush lifts; arms are inked heavier
  underneath and taper into the shoulder;
* **open, tapered inner strokes** (:meth:`Critter.details`): fur on the crown and chest, the cheek line, ear and paw
  creases, pressed at the root and lifted at the tip;
* **a slight head tilt**: the head turns about the neck, fading to nothing at the shoulders;
* **one shade tone** (:attr:`Critter.shade`) laid along every edge that faces away from the light (:func:`shade`);
* **faces drawn for their anatomy**: the sloth's eyes sit in dark stripes running down and out and its yawn is its
  own; the goat has bar pupils, a long muzzle and its own scream; the hamster has beady glossy eyes, cheek pouches
  and its own puffed cheeks.

Every kind of :data:`srstudio.toon.EYES` and :data:`srstudio.toon.MOUTHS` and every viseme draws on them: the face
parts they do not draw themselves come from the shared brush parts, placed on the untilted face and turned with the
head. :func:`shared_eye` and :func:`shared_mouth` are the new kinds for every other brush character: ``sleepy`` eyes
(heavy lids over low pupils; :func:`srstudio.toon_cast.figure` blinks them slower), a ``yawn``, a ``scream`` (wider
than a shock, teeth and tongue showing) and a ``puff`` (a closed smile between puffed cheeks). The traced cat was
not traced with them and refuses them by name (:func:`srstudio.toon.cat`).

The designs are original: generic animals drawn from their anatomy, not any photograph, meme, mascot or emoji set.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import cached_property, lru_cache
from typing import TYPE_CHECKING

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .head_motion import HeadStyle, Spring
from .registry import register
from .toon import Pose
from .toon_cast import CENTRE, FINE, INK, TONGUE, Layer, Look, Mouths, _brow, _eye, _mouth, _viseme, figure
from .toon_head import HeadRig
from .toon_torso import Torso

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "THROAT",
    "PRESS",
    "pressed",
    "drifted",
    "shade",
    "shared_eye",
    "shared_mouth",
    "Critter",
    "Split",
    "torso_rig",
    "SLOTH",
    "GOAT",
    "HAMSTER",
    "CRITTERS",
    "SLOTH_RIG",
    "GOAT_RIG",
    "HAMSTER_RIG",
    "SLOTH_STRIPE",
    "GOAT_HORN",
    "sloth",
    "goat",
    "hamster",
]

THROAT = "#5b1f2c"  # inside a wide-open mouth
LIGHT_FROM: Point = (-0.7, -0.71)  # the light comes from the upper left: edges facing away from it are shaded
FUR = brush.Pressure(1.0, 0.18, 0.12, 0.06, 1.0)  # an inner stroke: pressed at the root, lifted at the tip
LINE = brush.Pressure(0.35, 0.3, 0.75, 0.06, 1.2)  # a line pressed in the middle, tapered at both ends
CALM = 0.15  # the share of a hand's drift the shoulders and flanks take: the head's edge wobbles, the torso runs smooth
CLAW = brush.Pressure(1.0, 0.16, 0.0, 0.0, 1.0)


# -- the hand ----------------------------------------------------------------------------------------------------------
WAVE = brush.Wave(((5, 1.0, 0.4, 1.0), (11, 0.55, 2.1, 1.7), (23, 0.3, 4.3, 2.9)), 1.85)  # slower than the fox's hand
PRESS = brush.Hand(light=0.45, heavy=1.45, toward=(0.45, 0.89), tips=0.6, grain=0.12, wave=WAVE)
EYE_PRESS = replace(PRESS, light=0.6, heavy=1.35, toward=(0.0, -1.0), tips=0.3, grain=0.08)  # a heavy upper lid


def pressed(points: Sequence[Point], weight: float, press: brush.Hand = PRESS, seed: float = 0.0) -> Shape:
    """The ink band under an :func:`srstudio.brush.outline` of the same points, by a critter's hand."""
    return brush.inked(points, weight, press, steps=4, seed=seed)


def drifted(
    points: Sequence[Point], amount: float, seed: float, weights: Sequence[float] | None = None
) -> tuple[Point, ...]:
    """The control points of a contour wobbled by a critter's hand, as :data:`WAVE` draws them for a ``seed``."""
    moved = brush.wobble(points, amount, steps=1, seed=seed / brush.SEED_RATE, weights=weights, wave=WAVE)
    return tuple((round(x, 2), round(y, 2)) for x, y in moved)


def shade(
    points: Sequence[Point],
    depth: float,
    colour: str,
    least: float = 0.2,
    steps: int = 4,
    above: Callable[[float], float] | None = None,
) -> list[Layer]:
    """The shade tone along every run of a closed contour that faces away from the light: a band from the edge
    inward, ``depth`` deep where the edge faces straight away and nothing where it stops facing away. ``above`` gives
    the lowest a band reaches at an ``x``, for a band cut along a chin: what lies under it goes, what crosses it ends
    on it."""
    ring = brush.facing(points, steps)
    n = len(ring)
    lx, ly = LIGHT_FROM
    depths = [depth * max(0.0, (-(nx * lx + ny * ly) - least) / (1 - least)) ** 0.8 for _, (nx, ny) in ring]
    start = next((i for i in range(n) if depths[i] == 0), None)
    if start is None:
        raise brush.BrushError("a shade needs part of the contour to face the light")
    layers: list[Layer] = []
    run: list[int] = []
    for k in range(1, n + 1):
        i = (start + k) % n
        if depths[i] > 0:
            run.append(i)
            continue
        if len(run) >= 6:
            edge = [ring[j][0] for j in run]
            inner = [
                (ring[j][0][0] - ring[j][1][0] * depths[j], ring[j][0][1] - ring[j][1][1] * depths[j]) for j in run
            ]
            if above is not None:
                pairs = [(e, i) for e, i in zip(edge, inner, strict=True) if e[1] < above(e[0]) or i[1] < above(i[0])]
                edge = [(x, min(y, above(x))) for (x, y), _ in pairs]
                inner = [(x, min(y, above(x))) for _, (x, y) in pairs]
            if edge:
                layers.append((brush.outline([*edge, *inner[::-1]], steps=1), colour))
        run = []
    return layers


def _along(line: Sequence[Point]) -> Callable[[float], float]:
    """The height of a line at any ``x``, the height of its nearer end past its ends."""
    ordered = sorted(line)
    xs = [x for x, _ in ordered]

    def at(x: float) -> float:
        k = bisect_left(xs, x)
        if k == 0 or k == len(ordered):
            return ordered[min(k, len(ordered) - 1)][1]
        (ax, ay), (bx, by) = ordered[k - 1], ordered[k]
        return ay + (by - ay) * (x - ax) / (bx - ax)

    return at


def _fur(points: Sequence[Point], weight: float = FINE * 1.15, pressure: brush.Pressure = FUR) -> Layer:
    return (brush.stroke(points, weight, pressure, steps=6), "ink")


def _inked(points: Sequence[Point], colour: str, seed: float, weight: float = INK, amount: float = 1.2) -> list[Layer]:
    """A pressed ink band and the fill over it, on the same drifted contour."""
    contour = drifted(points, amount, seed)
    return [(pressed(contour, weight, seed=seed), "ink"), (brush.outline(contour, steps=3), colour)]


def _fill(points: Sequence[Point], colour: str, seed: float, amount: float = 0.8) -> Layer:
    return (brush.outline(drifted(points, amount, seed), steps=3), colour)


def _oval(cx: float, cy: float, rx: float, ry: float, n: int = 12, flat: float = 0.0) -> list[Point]:
    """An oval as control points, its top flattened by ``flat`` (0..1)."""
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        y = math.sin(t)
        out.append((cx + rx * math.cos(t), cy + ry * (y if y > 0 else y * (1 - flat))))
    return out


# -- the new kinds for every brush character ---------------------------------------------------------------------------
Pupil = Callable[[Look, float, float, float], list[Layer]]


def _round_pupil(look: Look, px: float, py: float, size: float) -> list[Layer]:
    out: list[Layer] = [(brush.ellipse(px, py, size, size * 1.15), "ink")]
    if look.shine:
        out.append((brush.ellipse(px - size * 0.35, py - size * 0.45, size * 0.3, size * 0.3), "white"))
    return out


def _sleepy(
    look: Look, centre: Point, inner: float, pupil: Pupil, cover: Callable[[Sequence[Point]], Shape] | None = None
) -> list[Layer]:
    """Sleepy eyes: a lid hung past the middle of the eye, drooping to the outer corner over a low pupil, a relaxed
    brow and a tired line under the eye. ``cover`` draws the lid from its outline, the plain outline by default."""
    ex, ey = centre
    r = look.eye_r
    lid = look.lid or look.coat
    out: list[Layer] = []
    if look.brows:
        y = ey - r - INK - 3.0
        outer, inside = ex - inner * r * 1.05, ex + inner * r * 0.9
        out.append((brush.stroke([(outer, y + 5.0), (ex, y + 1.0), (inside, y)], INK * 0.95), "ink"))
    out.append((brush.ellipse(ex, ey, r + INK, r + INK), "ink"))
    out.append((brush.ellipse(ex, ey, r, r), "white"))
    out += pupil(look, ex, ey + 0.4 * r, r * 0.28)
    top = ey - r - INK - 1.0
    outer_x, inside_x = ex - inner * (r + INK + 1.0), ex + inner * (r + INK + 1.0)
    y_out, y_in = ey + 0.32 * r, ey + 0.18 * r
    lid_shape = [(outer_x, top), (inside_x, top), (inside_x, y_in), (ex, y_in + 0.1 * r), (outer_x, y_out)]
    out.append((cover(lid_shape) if cover else brush.outline(lid_shape, steps=3), lid))
    out.append((brush.stroke([(outer_x + inner * 2.0, y_out), (ex, y_in + 0.12 * r), (inside_x - inner * 2.0, y_in)],
                             INK * 1.1, LINE), "ink"))  # fmt: skip
    bag = ey + r + INK + 3.0
    out.append((brush.stroke([(ex - 0.6 * r, bag), (ex, bag + 2.5), (ex + 0.6 * r, bag)], FINE * 0.8, LINE), "ink"))
    return out


def shared_eye(look: Look, centre: Point, inner: float) -> list[Layer]:
    """A ``sleepy`` eye for any brush look drawn from its fields (``inner`` is +1 when the nose is to its right)."""
    return _sleepy(look, centre, inner, _round_pupil)


def _yawn(look: Look, cx: float, top: float, rx: float, ry: float) -> list[Layer]:
    cy = top + ry
    oval = _oval(cx, cy, rx, ry, 14, flat=0.25)
    return [
        (pressed(oval, INK, replace(PRESS, light=0.55, heavy=1.3, toward=(0.0, 1.0), tips=0.2)), "ink"),
        (brush.outline(oval, steps=3), THROAT),
        (brush.ellipse(cx, cy + ry * 0.5, rx * 0.62, ry * 0.34), TONGUE),
        (brush.stroke([(cx, cy + ry * 0.32), (cx, cy + ry * 0.6)], FINE * 0.6, LINE), "ink"),
    ]


def _scream(look: Look, mx: float, top: float, bottom: float, hw_top: float, hw_bottom: float) -> list[Layer]:
    mid = (top + bottom) / 2
    opening = [
        (mx - hw_top, top),
        (mx - hw_top * 0.5, top - 3.0),
        (mx + hw_top * 0.5, top - 3.0),
        (mx + hw_top, top),
        (mx + hw_bottom + 3.0, mid),
        (mx + hw_bottom, bottom - 4.0),
        (mx, bottom + 2.0),
        (mx - hw_bottom, bottom - 4.0),
        (mx - hw_bottom - 3.0, mid),
    ]
    teeth = [(mx - hw_top + 5.0, top + 0.5), (mx + hw_top - 5.0, top + 0.5), (mx + hw_top - 7.5, top + 9.0),
             (mx - hw_top + 7.5, top + 9.0)]  # fmt: skip
    tongue = [
        (mx - hw_bottom * 0.78, bottom - 5.0),
        (mx - hw_bottom * 0.3, bottom - 14.0),
        (mx + hw_bottom * 0.35, bottom - 15.0),
        (mx + hw_bottom * 0.8, bottom - 6.0),
        (mx + hw_bottom * 0.45, bottom - 0.5),
        (mx - hw_bottom * 0.45, bottom - 0.5),
    ]
    out: list[Layer] = [
        (pressed(opening, INK, replace(PRESS, light=0.55, heavy=1.35, toward=(0.0, 1.0), tips=0.35)), "ink"),
        (brush.outline(opening, steps=3), THROAT),
        (brush.outline(tongue, steps=3), TONGUE),
        (brush.stroke([(mx, bottom - 12.0), (mx + 0.5, bottom - 4.0)], FINE * 0.6, LINE), "ink"),
        (brush.outline(teeth, steps=3), "white"),
    ]
    for k in (-0.5, 0.0, 0.5):
        x = mx + k * (hw_top - 7.0)
        out.append((brush.stroke([(x, top + 1.0), (x, top + 8.5)], FINE * 0.6, brush.EVEN, steps=3), "ink"))
    return out


def _puff(look: Look, mx: float, my: float, w: float) -> list[Layer]:
    """Puffed cheeks: a bulge drawn out each side of the mouth and a small closed smile between them."""
    out: list[Layer] = []
    reach = w * 0.5 + 14.0
    for side in (-1.0, 1.0):
        cx = mx + side * reach
        if look.blush:
            out.append((brush.ellipse(cx - side * 9.0, my - 2.0, 10.0, 6.5), look.blush))
        arc = [(cx - side * 3.0, my - 20.0), (cx + side * 7.0, my - 8.0), (cx + side * 7.0, my + 5.0),
               (cx - side * 2.0, my + 15.0)]  # fmt: skip
        out.append((brush.stroke(arc, INK * 0.95, LINE), "ink"))
    smile = [(mx - w * 0.2, my - 1.0), (mx, my + 4.0), (mx + w * 0.2, my - 1.0)]
    out.append((brush.stroke(smile, INK * 0.9, LINE), "ink"))
    for side in (-1.0, 1.0):
        corner = mx + side * w * 0.2
        out.append((brush.stroke([(corner, my - 1.0), (corner + side * 4.0, my - 5.0)], FINE, FUR), "ink"))
    return out


def shared_mouth(look: Look, kind: str) -> list[Layer]:
    """A ``yawn``, a ``scream`` or a ``puff`` for any brush look drawn from its fields."""
    mx, my = look.mouth
    w = look.mouth_w
    if kind == "yawn":  # tall, the jaw dropped: clear of the nose above it
        return _yawn(look, mx, my - 6.0, max(w * 0.36, 13.0), 27.0)
    if kind == "scream":  # wider than a shocked mouth, a row of teeth and the tongue showing
        return _scream(look, mx, my - 6.0, my + 30.0, max(w * 0.66, 20.0), max(w * 0.48, 15.0))
    if kind == "puff":
        return _puff(look, mx, my, w)
    raise ValueError(f"{look.name}: shared_mouth draws yawn, scream and puff, not {kind!r}")


# -- the critters' own drawing -----------------------------------------------------------------------------------------
@dataclass(frozen=True, eq=False)
class Critter:
    """A critter's own drawing (:class:`srstudio.toon_cast.Drawing`). ``face`` is the look untilted and without a
    drawing: where the shared brush parts draw a kind the critter does not draw itself. ``parts`` gives the body at
    rest, untilted, as layers flagged when they are inner strokes; ``tilt`` turns the head about ``neck`` (degrees
    clockwise, fading to nothing over ``fade`` px toward the shoulders). ``pupil`` draws a pupil, ``mouths`` the
    mouths it draws for its own face, ``paw`` the end of an arm. ``torso`` is the body under the head (ADR 0049):
    the face's silhouette is its contour, and the arms are drawn inside it (:meth:`Torso.limb`)."""

    name: str
    face: Look
    shade: str
    tilt: float
    neck: Point
    fade: float
    parts: Callable[[], list[tuple[Layer, bool]]]
    pupil: Pupil
    mouths: Callable[[Look, str], list[Layer] | None]
    paw: Callable[[Look, Point, Point, bool], list[Layer]]
    torso: Torso
    lid_press: brush.Hand = EYE_PRESS

    def _turn(self, x: float, y: float) -> Point:
        nx, ny = self.neck
        a = math.radians(self.tilt * min(1.0, max(0.0, (ny - y) / self.fade)))
        dx, dy = x - nx, y - ny
        return round(nx + dx * math.cos(a) - dy * math.sin(a), 2), round(ny + dx * math.sin(a) + dy * math.cos(a), 2)

    def turn(self, layers: Sequence[Layer]) -> list[Layer]:
        """Layers drawn on the untilted face, turned with the head."""
        out = []
        for shape, colour in layers:
            flat: list[float] = []
            for i in range(0, len(shape), 2):
                flat += self._turn(shape[i], shape[i + 1])
            out.append((tuple(flat), colour))
        return out

    def look(self) -> Look:
        """The critter as a :class:`Look`: its contour, eyes and mouth where the tilted head puts them, this
        drawing, and the face's other fields."""
        return replace(
            self.face,
            silhouette=tuple(self._turn(x, y) for x, y in self.face.silhouette),
            eyes=(self._turn(*self.face.eyes[0]), self._turn(*self.face.eyes[1])),
            mouth=self._turn(*self.face.mouth),
            drawing=self,
        )

    @cached_property
    def _base(self) -> tuple[tuple[Layer, bool], ...]:
        flagged = self.parts()
        turned = self.turn([layer for layer, _ in flagged])
        return tuple((layer, detail) for layer, (_, detail) in zip(turned, flagged, strict=True))

    def foundation(self, look: Look) -> list[Layer]:
        return [layer for layer, _ in self._base]

    def details(self) -> list[Layer]:
        """The open inner strokes of the body at rest: fur, creases, the cheek line."""
        return [layer for layer, detail in self._base if detail]

    def _local(self, inner: float) -> Point:
        return self.face.eyes[0 if inner > 0 else 1]

    def eye(self, look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
        local = self._local(inner)
        if kind in ("closed", "wince", "hearts"):  # no pupil: the shared drawing
            return self.turn(_eye(self.face, local, kind, inner))
        if kind == "sleepy":
            reach = self.face.eye_r + INK + 1.0
            return self.turn(_sleepy(self.face, local, inner, self.pupil, lambda box: self._lid(box, local, reach)))
        return self.turn(self._open_eye(local, kind, inner))

    def _open_eye(self, centre: Point, kind: str, inner: float) -> list[Layer]:
        """An open eye of every kind with a pupil: a pressed ring heavier along the upper lid, the critter's pupil,
        and the kind's lids as tapered lines."""
        face = self.face
        ex, ey = centre
        r = face.eye_r * (1.3 if kind == "shock" else 1.0)
        lid = face.lid or face.coat
        out: list[Layer] = [_brow(face, centre, kind, inner)] if face.brows else []
        out.append((pressed(_oval(ex, ey, r, r, 10), INK, self.lid_press), "ink"))
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
            "roll": (0.42, -0.5),
            "teary": (0.0, 0.05),
        }[kind]
        size = r * {"shock": 0.14, "teary": 0.38}.get(kind, 0.28)
        px, py = ex + pupil[0] * r, ey + pupil[1] * r
        out += self.pupil(face, px, py, size)
        edge = r + INK + 1.0
        lids = {"half": 0.5, "down": 0.3, "side": 0.45}
        if kind in lids:
            y = ey - r + 2 * r * lids[kind]
            box = [(ex - edge, ey - edge), (ex + edge, ey - edge), (ex + edge, y), (ex - edge, y)]
            out.append((self._lid(box, centre, edge), lid))
            out.append((brush.stroke([(ex - r - 2.0, y), (ex, y + 1.5), (ex + r + 2.0, y)], INK * 1.05, LINE), "ink"))
        elif kind == "narrow":
            outer, inside = ex - inner * edge, ex + inner * edge
            y_out, y_in = ey - 0.6 * r, ey - 0.05 * r
            box = [(outer, ey - edge), (inside, ey - edge), (inside, y_in), (outer, y_out)]
            out.append((self._lid(box, centre, edge), lid))
            out.append((brush.stroke([(outer, y_out), (inside, y_in)], INK * 1.05, LINE), "ink"))
        elif kind == "roll":
            y = ey + 0.3 * r
            box = [(ex - edge, y), (ex + edge, y), (ex + edge, ey + edge), (ex - edge, ey + edge)]
            out.append((self._lid(box, centre, edge), lid))
            out.append((brush.stroke([(ex - r - 2.0, y), (ex, y - 1.5), (ex + r + 2.0, y)], INK, LINE), "ink"))
        elif kind == "teary":
            out.append((brush.ellipse(px + size * 0.4, py + size * 0.4, size * 0.18, size * 0.18), "white"))
            from .toon_cast import TEAR, _tear

            tear = _tear(ex - inner * 0.75 * r, ey + r + INK + 4.0, r / 17.0)
            out += [(brush.rim(tear, FINE), "ink"), (brush.outline(tear), TEAR)]
        return out

    def _lid(self, box: Sequence[Point], centre: Point, reach: float) -> Shape:
        """What a lid covers: ``box`` over an eye at ``centre``, ``reach`` from its middle to outside its rim."""
        return brush.outline(box, steps=3)

    def lids(self, look: Look) -> list[Layer]:
        face = self.face
        lid = face.lid or face.coat
        out: list[Layer] = []
        for ex, ey in face.eyes:
            r = face.eye_r
            out.append((brush.ellipse(ex, ey, r + INK + 1.0, r + INK + 1.0), lid))
            out.append((brush.stroke([(ex - r, ey + 1.0), (ex, ey + 7.0), (ex + r, ey + 1.0)], INK * 1.1, LINE), "ink"))
        return self.turn(out)

    def mouth(self, look: Look, kind: str) -> list[Layer]:
        own = self.mouths(self.face, kind)
        return self.turn(own if own is not None else _mouth(self.face, kind))

    def viseme(self, look: Look, kind: str) -> list[Layer]:
        return self.turn(_viseme(self.face, kind))

    def looking(self, dx: float, dy: float) -> Critter:
        """This drawing with its pupils ``dx`` and ``dy`` eye radii off (:class:`srstudio.toon_head.Glancing`)."""
        r = self.face.eye_r
        base = self.pupil

        def pupil(face: Look, x: float, y: float, size: float) -> list[Layer]:
            return base(face, x + dx * r, y + dy * r, size)

        return replace(self, pupil=pupil)

    def rig(self, split: Split, style: HeadStyle, free: float = 0.0) -> HeadRig:
        """This critter split at its neck (:func:`torso_rig`): its look untilted, the tilt carried by the head."""
        look = replace(self, tilt=0.0).look()
        return torso_rig(look, self.torso, self.neck, self.tilt, (self.face.coat, self.shade), split, style, free)

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]:
        """An arm inside the body (:meth:`srstudio.toon_torso.Torso.limb`): a thin crease out of the body widening
        to the forearm, inked heavier underneath, the shade along its underside, then the critter's paw."""
        layers, at, way = self.torso.limb(points, paw, look.coat, self.shade)
        return layers + self.paw(look, at, way, toes)


CHIN_ROOM = 30.0  # how far inside the head an open chin's ink closes, reference pixels
CHIN_PEEL = (7.0, 4.0, 1.5)  # how far inside the head an open chin's ink lies at the points above each join
CHIN_LAP = 2.0  # how far a head's shade laps past its chin onto the body's, so no line of coat shows between them
CHIN_TAIL = brush.Pressure(0.04, 1.0, 0.2, 0.0, 1.0)  # the line that carries the ink on to the join, tapering out


@dataclass(frozen=True)
class Split:
    """What a :class:`~srstudio.toon_torso.Torso` character supplies beyond its torso to move its head (ADR 0050).
    ``chin`` closes the torso's head from its right neck join round to its left, ``top`` is the body's top from its
    left neck join to its right; ``hand`` is the amount and the seed of the drift on both outlines. ``back`` draws what
    is behind the head's outline (ears, horns), ``skull`` what stays on the head, ``face`` what slides over it,
    ``trunk`` what sits on the body. With ``head_over`` the body goes under the head and ``top`` runs up behind the
    head; without it, the body goes over the head and ``top`` is a ruff. With ``open_chin`` a head runs on into its body
    with no chin line, as its drawing does: the head's ink tapers out at the joins, where ``top`` runs up the same edge
    behind it and carries the contour on, and its shade is the drawing's, cut along the chin."""

    chin: tuple[Point, ...]
    top: tuple[Point, ...]
    hand: tuple[float, float]
    skull: Callable[[], Sequence[Layer]]
    face: Callable[[], Sequence[Layer]]
    trunk: Callable[[], Sequence[Layer]]
    back: Callable[[], Sequence[Layer]] = tuple
    head_over: bool = False
    open_chin: bool = False


def torso_rig(
    look: Look,
    torso: Torso,
    neck: Point,
    tilt: float,
    colours: tuple[str, str],
    split: Split,
    style: HeadStyle,
    free: float = 0.0,
) -> HeadRig:
    """A :class:`HeadRig` for any drawing with a torso: the outlines drawn the critters' way, in ``colours`` (coat,
    shade). ``look`` is the look with an untilted head."""
    coat, shading = colours
    amount, seed = split.hand
    head = (*torso.head, *split.chin)

    def outlined(contour: tuple[Point, ...], weights: tuple[float, ...] | None = None) -> list[Layer]:
        drawn = drifted(contour, amount, seed, weights)
        fill: list[Layer] = [(pressed(drawn, INK * 1.05, seed=seed), "ink"), (brush.outline(drawn, steps=3), coat)]
        return fill + shade(drawn, 22.0, shading)

    def seamless() -> list[Layer]:
        drawn = drifted(head, amount, seed)
        count = len(torso.head)

        def peeled(index: int, inset: float) -> Point:
            x, y = drawn[index]
            return (x + inset if x < torso.centre else x - inset, y)

        left = [peeled(k + 1, inset) for k, inset in enumerate(CHIN_PEEL)]
        right = [peeled(count - 2 - k, inset) for k, inset in enumerate(CHIN_PEEL)][::-1]
        closing = [(x, y - CHIN_ROOM) for x, y in drawn[count + 1 : -1]]
        crown = (*left, *drawn[len(CHIN_PEEL) + 1 : count - len(CHIN_PEEL) - 1], *right, *closing)
        ends = len(CHIN_PEEL) + 2
        ink = [
            pressed(crown, INK * 1.05, seed=seed),
            brush.stroke(drawn[1:ends], INK * 1.05, CHIN_TAIL, steps=6),
            brush.stroke(drawn[count - 2 : count - ends - 1 : -1], INK * 1.05, CHIN_TAIL, steps=6),
        ]
        fill: list[Layer] = [*((line, "ink") for line in ink), (brush.outline(drawn, steps=3), coat)]
        ring = [point for point, _ in brush.facing(drawn, 3)]
        chin = _along((*ring[(count - 1) * 3 :], ring[0]))
        return fill + shade(torso.under(drawn[:count]), 22.0, shading, above=lambda x: chin(x) + CHIN_LAP)

    @lru_cache(maxsize=1)
    def skull() -> tuple[Layer, ...]:
        return (*split.back(), *(seamless() if split.open_chin else outlined(head)), *split.skull())

    @lru_cache(maxsize=1)
    def face() -> tuple[Layer, ...]:
        return tuple(split.face())

    @lru_cache(maxsize=1)
    def trunk() -> tuple[Layer, ...]:
        return (*outlined(torso.under(split.top), torso.weights(CALM, len(split.top))), *split.trunk())

    return HeadRig(
        look=look,
        neck=neck,
        tilt=tilt,
        head=head,
        cover=split.top,
        skull=skull,
        face=face,
        trunk=trunk,
        style=style,
        head_over=split.head_over,
        free=free,
    )


def _pressed_paw(look: Look, paw: Point, rx: float, ry: float, colour: str, seed: float) -> list[Layer]:
    oval = _oval(paw[0], paw[1], rx, ry, 10)
    return [(pressed(oval, INK * 0.9, seed=seed), "ink"), (brush.outline(oval, steps=3), colour)]


# -- the sloth ---------------------------------------------------------------------------------------------------------
SLOTH_STRIPE = "#4a3826"
SLOTH_SHADE = "#6b6e3c"
SLOTH_BELLY = "#a3a46d"
SLOTH_NOSE = "#3a2a20"
SLOTH_CLAW = "#efe4c6"
_SLOTH_HEAD = (  # the sloth's head from the left of its neck over the crown to the right, the fur tufts and all
    (75.0, 690.0), (77.0, 672.0), (68.0, 664.0), (81.0, 652.0), (82.0, 636.0), (79.0, 624.0), (88.0, 612.0),
    (90.0, 588.0), (87.0, 574.0), (95.0, 566.0), (98.0, 546.0), (93.0, 534.0), (106.0, 528.0), (111.0, 512.0),
    (111.0, 497.0), (123.0, 503.0), (128.0, 487.0), (138.0, 490.0), (147.0, 470.0), (159.0, 482.0), (167.0, 466.0),
    (176.0, 474.0), (188.0, 457.0), (191.0, 432.0), (199.0, 414.0), (208.0, 408.0), (207.0, 424.0), (216.0, 432.0),
    (213.0, 448.0), (197.0, 472.0), (210.0, 463.0), (219.0, 478.0), (234.0, 471.0), (239.0, 486.0), (251.0, 486.0),
    (253.0, 501.0), (264.0, 510.0), (267.0, 525.0), (275.0, 534.0), (274.0, 547.0), (279.0, 566.0), (282.0, 590.0),
    (288.0, 604.0), (284.0, 616.0), (288.0, 638.0), (300.0, 650.0), (291.0, 659.0), (298.0, 676.0), (300.0, 690.0),
)  # fmt: skip
_SLOTH_TORSO = Torso(_SLOTH_HEAD, shoulder=150.0, slope=35.0, flank=156.0, arm=30.0)
_SLOTH_BODY = _SLOTH_TORSO.contour
_SLOTH_DISC = (
    (111.0, 600.0), (115.0, 572.0), (128.0, 550.0), (149.0, 538.0), (170.0, 544.0), (185.0, 553.0), (202.0, 542.0),
    (223.0, 536.0), (243.0, 548.0), (256.0, 570.0), (262.0, 600.0), (260.0, 631.0), (247.0, 655.0), (220.0, 670.0),
    (185.0, 677.0), (152.0, 671.0), (126.0, 655.0), (113.0, 631.0),
)  # fmt: skip
_SLOTH_STRIPES = (
    ((168.0, 572.0), (163.0, 565.0), (154.0, 565.0), (144.0, 571.0), (138.0, 584.0), (131.0, 602.0), (121.0, 624.0),
     (110.0, 642.0), (112.0, 651.0), (122.0, 645.0), (137.0, 626.0), (151.0, 608.0), (162.0, 596.0), (170.0, 586.0)),
    ((202.0, 569.0), (207.0, 563.0), (216.0, 563.0), (226.0, 569.0), (232.0, 582.0), (239.0, 600.0), (249.0, 622.0),
     (260.0, 641.0), (258.0, 649.0), (248.0, 643.0), (233.0, 625.0), (219.0, 607.0), (208.0, 595.0), (200.0, 584.0)),
)  # fmt: skip
_SLOTH_NOSE = ((175.0, 607.0), (179.0, 600.0), (187.0, 599.0), (195.0, 603.0), (197.0, 611.0), (191.0, 618.0),
               (184.0, 620.0), (177.0, 616.0))  # fmt: skip
_SLOTH_BELLY = ((128.0, 724.0), (160.0, 712.0), (196.0, 711.0), (232.0, 718.0), (254.0, 744.0), (262.0, 782.0),
                (258.0, 830.0), (116.0, 830.0), (110.0, 784.0), (114.0, 748.0))  # fmt: skip
_SLOTH_CHIN_SHADE = ((136.0, 688.0), (160.0, 697.0), (186.0, 700.0), (214.0, 696.0), (239.0, 686.0), (232.0, 702.0),
                     (206.0, 712.0), (182.0, 714.0), (156.0, 708.0))  # fmt: skip
_SLOTH_FUR = (
    ((157.0, 499.0), (160.0, 511.0), (159.0, 520.0)),  # the crown, combed every way
    ((179.0, 491.0), (182.0, 505.0)),
    ((208.0, 492.0), (204.0, 506.0), (203.0, 514.0)),
    ((231.0, 500.0), (226.0, 513.0)),
    ((136.0, 512.0), (142.0, 524.0)),
    ((94.0, 630.0), (100.0, 640.0), (101.0, 652.0)),  # the cheeks, outside the face
    ((274.0, 624.0), (269.0, 636.0)),
    ((158.0, 683.0), (185.0, 690.0), (213.0, 683.0)),  # the chin line under the face
    ((148.0, 730.0), (153.0, 744.0)),  # the chest
    ((210.0, 733.0), (206.0, 747.0)),
    ((180.0, 758.0), (183.0, 772.0)),
    ((185.0, 620.0), (185.0, 629.0)),  # the philtrum
)


def _sloth_parts() -> list[tuple[Layer, bool]]:
    body = drifted(_SLOTH_BODY, 1.3, 1.0, _SLOTH_TORSO.weights(CALM))
    out: list[tuple[Layer, bool]] = [
        ((pressed(body, INK * 1.05, seed=1.0), "ink"), False),
        ((brush.outline(body, steps=3), _SLOTH_COAT), False),
    ]
    layers: list[Layer] = shade(body, 22.0, SLOTH_SHADE)
    layers.append(_fill(_SLOTH_BELLY, SLOTH_BELLY, 2.0))
    layers.append(_fill(_SLOTH_CHIN_SHADE, SLOTH_SHADE, 3.0))
    layers.append(_fill(_SLOTH_DISC, _SLOTH_LIGHT, 4.0, amount=1.0))
    layers += [_fill(stripe, SLOTH_STRIPE, 5.0 + k, amount=0.6) for k, stripe in enumerate(_SLOTH_STRIPES)]
    out += [(layer, False) for layer in layers]
    out += [(_fur(points), True) for points in _SLOTH_FUR]
    out += [
        ((pressed(_SLOTH_NOSE, FINE, seed=7.0), "ink"), False),
        ((brush.outline(_SLOTH_NOSE, steps=3), SLOTH_NOSE), False),
    ]
    out.append(((brush.ellipse(181.0, 604.0, 3.6, 2.2, -10.0), "white"), False))
    return out


_SLOTH_CHIN = ((286.0, 716.0), (240.0, 738.0), (185.0, 744.0), (130.0, 738.0), (88.0, 716.0))  # behind the ruff
_SLOTH_RUFF = (  # the body's top: a shaggy ruff from neck join to neck join, over the seam under the head
    (75.0, 692.0), (66.0, 682.0), (84.0, 684.0), (92.0, 672.0), (104.0, 685.0), (118.0, 681.0), (130.0, 693.0),
    (152.0, 698.0), (185.0, 702.0), (218.0, 698.0), (240.0, 693.0), (252.0, 681.0), (266.0, 685.0), (278.0, 672.0),
    (286.0, 684.0), (304.0, 682.0), (300.0, 692.0),
)  # fmt: skip
_SLOTH_RUFF_SHADE = tuple((x, y + 13.0) for x, y in _SLOTH_CHIN_SHADE)
_SLOTH_RUFF_FUR = (((112.0, 690.0), (116.0, 702.0)), ((262.0, 690.0), (258.0, 702.0)))


def _sloth_cover() -> list[Layer]:
    """What sits on the sloth's body: the belly, the ruff's shade and the chest fur."""
    layers = [_fill(_SLOTH_BELLY, SLOTH_BELLY, 2.0), _fill(_SLOTH_RUFF_SHADE, SLOTH_SHADE, 3.0)]
    return layers + [_fur(points) for points in (*_SLOTH_FUR[8:11], *_SLOTH_RUFF_FUR)]


def _sloth_features() -> list[Layer]:
    """What slides across the sloth's head when it turns: the pale face, its stripes, the chin line and the nose."""
    layers: list[Layer] = [_fill(_SLOTH_DISC, _SLOTH_LIGHT, 4.0, amount=1.0)]
    layers += [_fill(stripe, SLOTH_STRIPE, 5.0 + k, amount=0.6) for k, stripe in enumerate(_SLOTH_STRIPES)]
    layers += [_fur(_SLOTH_FUR[7]), _fur(_SLOTH_FUR[11])]
    layers += [(pressed(_SLOTH_NOSE, FINE, seed=7.0), "ink"), (brush.outline(_SLOTH_NOSE, steps=3), SLOTH_NOSE)]
    layers.append((brush.ellipse(181.0, 604.0, 3.6, 2.2, -10.0), "white"))
    return layers


def _sloth_mouths(face: Look, kind: str) -> list[Layer] | None:
    if kind != "yawn":
        return None
    mx, my = face.mouth
    out = _yawn(face, mx, my - 16.0, 25.0, 33.0)
    for side in (-1.0, 1.0):  # two little peg teeth and the stretch at the corners
        x = mx + side * 11.0
        tooth = [(x - 3.0, my - 13.0), (x + 3.0, my - 13.0), (x + 1.5, my - 6.0), (x - 1.5, my - 6.0)]
        out.append((brush.outline(tooth, steps=2), "white"))
        corner = mx + side * 28.0
        out.append((brush.stroke([(corner, my + 2.0), (corner + side * 7.0, my + 10.0)], FINE, FUR), "ink"))
    return out


def _sloth_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A long-clawed paw: three ivory hooks laid forward along the desk, curling down at the tips."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.62, w * 0.46, SLOTH_SHADE, 8.0)
    ahead = 1.0 if way[0] >= 0 else -1.0
    for dy, length in ((-8.0, 19.0), (-1.0, 23.0), (6.0, 18.0)):
        x0, y0 = paw[0] + ahead * w * 0.28, paw[1] + dy
        hook = [(x0, y0), (x0 + ahead * length * 0.6, y0 - 3.0), (x0 + ahead * length, y0 + 6.0)]
        out.append((brush.stroke(hook, 8.0 + 2 * FINE, CLAW, steps=4), "ink"))
        out.append((brush.stroke(hook, 8.0, CLAW, steps=4), SLOTH_CLAW))
    out.append(_fur([(paw[0] - ahead * w * 0.2, paw[1] - w * 0.3), (paw[0] - ahead * w * 0.05, paw[1] - w * 0.05)]))
    return out


_SLOTH_COAT = "#878a52"
_SLOTH_LIGHT = "#e9dcbb"
SLOTH_CRITTER = Critter(
    name="sloth",
    face=Look(
        name="sloth",
        coat=_SLOTH_COAT,
        dark=SLOTH_SHADE,
        light=_SLOTH_LIGHT,
        silhouette=_SLOTH_BODY,
        eyes=((155.0, 584.0), (215.0, 582.0)),
        eye_r=13.0,
        mouth=(185.0, 640.0),
        mouth_w=42.0,
        limb=30.0,
        lid=SLOTH_STRIPE,
        brows=True,
        shine=True,
        blink=4.6,
    ),
    shade=SLOTH_SHADE,
    tilt=7.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _sloth_parts(),
    pupil=_round_pupil,
    mouths=_sloth_mouths,
    paw=_sloth_paw,
    torso=_SLOTH_TORSO,
)
SLOTH = SLOTH_CRITTER.look()
SLOTH_MOTION = HeadStyle(  # slow, heavy, late: a low spring, a slow shift for its one nod, a long breath
    seed=1045,
    signature="/",
    nod_px=11.0,
    nod_roll=2.0,
    head=Spring(1.5, 0.7, 0.12),
    settle=Spring(0.8, 0.85),
    body=Spring(1.0, 1.0),
    min_gap=0.55,
    loud_range=8.0,
    lean=1.2,
    idle_roll=2.4,
    idle_px=1.5,
    idle_hz=0.2,
    breath_period=5.4,
    glance_every=4.5,
    glance_hold=1.3,
)
SLOTH_RIG = SLOTH_CRITTER.rig(
    Split(
        chin=_SLOTH_CHIN,
        top=_SLOTH_RUFF,
        hand=(1.3, 1.0),
        skull=lambda: [_fur(points) for points in _SLOTH_FUR[:7]],
        face=_sloth_features,
        trunk=_sloth_cover,
    ),
    SLOTH_MOTION,
    free=25.0,
)


# -- the goat ----------------------------------------------------------------------------------------------------------
GOAT_HORN = "#eadfc4"
GOAT_SHADE = "#8a73b5"
GOAT_EAR = "#d8b6d2"
GOAT_HOOF = "#4b3f5f"
GOAT_IRIS = "#e8b84a"
_GOAT_COAT = "#a48ccc"
_GOAT_LIGHT = "#f2ebdc"
_GOAT_HEAD = (  # the goat's head from under the left jaw over the horns' roots to under the right jaw
    (140.0, 676.0), (143.0, 666.0), (136.0, 648.0), (130.0, 626.0), (124.0, 604.0), (117.0, 582.0), (112.0, 562.0),
    (109.0, 542.0), (112.0, 522.0), (118.0, 504.0), (130.0, 488.0), (146.0, 477.0), (163.0, 470.0), (174.0, 468.0),
    (181.0, 455.0), (190.0, 466.0), (204.0, 469.0), (222.0, 476.0), (238.0, 487.0), (250.0, 502.0), (257.0, 520.0),
    (261.0, 540.0), (259.0, 562.0), (253.0, 584.0), (248.0, 600.0), (256.0, 611.0), (244.0, 618.0), (239.0, 634.0),
    (233.0, 652.0), (232.0, 670.0),
)  # fmt: skip
_GOAT_TORSO = Torso(_GOAT_HEAD, shoulder=150.0, slope=22.0, flank=146.0, arm=26.0)
_GOAT_BODY = _GOAT_TORSO.contour
_GOAT_EARS = (
    ((118.0, 548.0), (101.0, 551.0), (83.0, 560.0), (66.0, 572.0), (56.0, 582.0), (65.0, 587.0), (84.0, 584.0),
     (104.0, 577.0), (118.0, 568.0)),
    ((252.0, 540.0), (270.0, 541.0), (289.0, 548.0), (305.0, 558.0), (316.0, 568.0), (308.0, 573.0), (290.0, 572.0),
     (271.0, 567.0), (255.0, 561.0)),
)  # fmt: skip
_GOAT_EAR_INNER = (
    ((108.0, 557.0), (90.0, 563.0), (72.0, 575.0), (82.0, 579.0), (100.0, 573.0), (111.0, 565.0)),
    ((262.0, 549.0), (281.0, 551.0), (300.0, 561.0), (292.0, 566.0), (274.0, 562.0), (261.0, 556.0)),
)  # fmt: skip
_GOAT_HORNS = (
    ((146.0, 494.0), (136.0, 472.0), (124.0, 450.0), (111.0, 430.0), (100.0, 413.0), (94.0, 400.0), (101.0, 397.0),
     (114.0, 409.0), (130.0, 427.0), (147.0, 447.0), (163.0, 465.0), (178.0, 482.0)),
    ((196.0, 480.0), (209.0, 461.0), (225.0, 442.0), (243.0, 425.0), (262.0, 410.0), (279.0, 399.0), (285.0, 403.0),
     (276.0, 415.0), (262.0, 431.0), (248.0, 449.0), (236.0, 469.0), (226.0, 490.0)),
)  # fmt: skip
_GOAT_RIDGES = (
    ((126.0, 456.0), (143.0, 446.0)),
    ((115.0, 437.0), (129.0, 428.0)),
    ((106.0, 420.0), (116.0, 413.0)),
    ((224.0, 452.0), (240.0, 462.0)),
    ((238.0, 433.0), (252.0, 442.0)),
    ((253.0, 418.0), (264.0, 425.0)),
)
_GOAT_MUZZLE = (
    (146.0, 614.0), (166.0, 606.0), (185.0, 604.0), (204.0, 606.0), (226.0, 613.0), (232.0, 636.0), (228.0, 658.0),
    (221.0, 676.0), (204.0, 686.0), (185.0, 689.0), (166.0, 686.0), (150.0, 676.0), (141.0, 658.0), (139.0, 636.0),
)  # fmt: skip
_GOAT_BEARD = ((164.0, 682.0), (185.0, 689.0), (206.0, 682.0), (203.0, 700.0), (196.0, 720.0), (189.0, 744.0),
               (182.0, 728.0), (174.0, 708.0))  # fmt: skip
_GOAT_CHIN_SHADE = ((146.0, 690.0), (185.0, 700.0), (228.0, 690.0), (222.0, 706.0), (185.0, 714.0), (152.0, 706.0))
_GOAT_FUR = (
    ((178.0, 476.0), (183.0, 488.0), (182.0, 497.0)),  # the forelock
    ((193.0, 476.0), (191.0, 488.0)),
    ((140.0, 590.0), (147.0, 604.0)),  # the cheekbones, down the long face
    ((233.0, 588.0), (227.0, 602.0)),
    ((175.0, 614.0), (170.0, 620.0), (173.0, 626.0)),  # the nostrils
    ((196.0, 614.0), (200.0, 620.0), (197.0, 626.0)),
    ((181.0, 700.0), (184.0, 716.0)),  # the beard
    ((192.0, 700.0), (190.0, 713.0)),
    ((104.0, 568.0), (80.0, 574.0)),  # the ear creases
    ((266.0, 560.0), (292.0, 562.0)),
    ((150.0, 742.0), (156.0, 756.0)),  # the chest
    ((218.0, 748.0), (214.0, 762.0)),
)


def _goat_parts() -> list[tuple[Layer, bool]]:
    out: list[tuple[Layer, bool]] = []
    for k, horn in enumerate(_GOAT_HORNS):
        out += [(layer, False) for layer in _inked(horn, GOAT_HORN, 10.0 + k, weight=INK * 0.95, amount=0.6)]
    for k, ear in enumerate(_GOAT_EARS):
        out += [(layer, False) for layer in _inked(ear, _GOAT_COAT, 12.0 + k, amount=0.6)]
        out.append((_fill(_GOAT_EAR_INNER[k], GOAT_EAR, 14.0 + k, amount=0.4), False))
    body = drifted(_GOAT_BODY, 1.2, 16.0, _GOAT_TORSO.weights(CALM))
    out += [((pressed(body, INK * 1.05, seed=16.0), "ink"), False), ((brush.outline(body, steps=3), _GOAT_COAT), False)]
    layers: list[Layer] = shade(body, 22.0, GOAT_SHADE)
    layers.append(_fill(_GOAT_CHIN_SHADE, GOAT_SHADE, 17.0))
    layers.append(_fill(_GOAT_MUZZLE, _GOAT_LIGHT, 18.0, amount=0.8))
    layers += _inked(_GOAT_BEARD, _GOAT_LIGHT, 19.0, weight=INK * 0.85, amount=0.5)
    out += [(layer, False) for layer in layers]
    out += [(_fur(points, FINE * 0.95, LINE), True) for points in _GOAT_RIDGES]
    out += [(_fur(points), True) for points in _GOAT_FUR]
    return out


def _goat_pupil(look: Look, px: float, py: float, size: float) -> list[Layer]:
    """A goat's eye, stylised: an amber iris and a bar pupil wider than tall, rounded at the ends."""
    hw, hh = size * 1.6, size * 0.78
    iris = size / 0.28 * 0.62  # the iris keeps to the eye whatever the pupil's size
    bar = [
        (px - hw, py - hh * 0.7),
        (px - hw * 0.6, py - hh),
        (px + hw * 0.6, py - hh),
        (px + hw, py - hh * 0.7),
        (px + hw, py + hh * 0.7),
        (px + hw * 0.6, py + hh),
        (px - hw * 0.6, py + hh),
        (px - hw, py + hh * 0.7),
    ]
    out: list[Layer] = [(brush.ellipse(px, py, min(iris, size * 2.6), min(iris, size * 2.6) * 0.92), GOAT_IRIS)]
    out.append((brush.outline(bar, steps=2), "ink"))
    if look.shine:
        out.append((brush.ellipse(px - hw * 0.5, py - hh * 1.1, size * 0.34, size * 0.28), "white"))
    return out


def _goat_mouths(face: Look, kind: str) -> list[Layer] | None:
    if kind != "scream":
        return None
    mx, my = face.mouth
    out = _scream(face, mx, my - 12.0, my + 36.0, 27.0, 17.0)
    for side in (-1.0, 1.0):  # the bleat carries: three short lines off each side of the muzzle
        for k, (dy, reach) in enumerate(((-14.0, 9.0), (0.0, 12.0), (14.0, 9.0))):
            x = mx + side * (58.0 + 2.0 * k % 2)
            line = [(x, my + dy - side * 0.0), (x + side * reach, my + dy + dy * 0.35)]
            out.append((brush.stroke(line, FINE * 1.2, LINE, steps=3), "ink"))
    return out


def _goat_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A hoof: a dark pressed mitt split at the front."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.66, w * 0.5, GOAT_HOOF, 20.0)
    out.append((brush.ellipse(paw[0] - w * 0.18, paw[1] - w * 0.2, w * 0.16, w * 0.08, -15.0), GOAT_SHADE))
    ahead = 1.0 if way[0] >= 0 else -1.0
    split = paw[0] + ahead * w * 0.22
    out.append(_fur([(split, paw[1] - w * 0.46), (split - ahead * 1.5, paw[1] + w * 0.05)], FINE * 1.2))
    return out


GOAT_CRITTER = Critter(
    name="goat",
    face=Look(
        name="goat",
        coat=_GOAT_COAT,
        dark=GOAT_SHADE,
        light=_GOAT_LIGHT,
        silhouette=_GOAT_BODY,
        eyes=((150.0, 544.0), (220.0, 542.0)),
        eye_r=15.0,
        mouth=(185.0, 652.0),
        mouth_w=34.0,
        limb=26.0,
        brows=True,
        shine=True,
        blink=3.1,
        paw=GOAT_HOOF,
    ),
    shade=GOAT_SHADE,
    tilt=-6.0,
    neck=(CENTRE, 700.0),
    fade=120.0,
    parts=lambda: _goat_parts(),
    pupil=_goat_pupil,
    mouths=_goat_mouths,
    paw=_goat_paw,
    torso=_GOAT_TORSO,
)
GOAT = GOAT_CRITTER.look()
GOAT_MOTION = HeadStyle(  # abrupt: a stiff spring that stops dead, long stares between sudden moves
    seed=2046,
    signature="^",
    nod_px=9.0,
    nod_roll=1.2,
    head=Spring(4.5, 0.95),
    settle=Spring(3.0, 0.95),
    body=Spring(2.0, 1.0),
    min_gap=0.7,
    loud_range=8.0,
    lean=0.8,
    idle_roll=0.9,
    idle_px=0.5,
    idle_hz=0.12,
    breath_period=4.2,
    glance_every=3.2,
    glance_hold=0.7,
    glance_turn=3.0,
    glance_face=7.0,
)
_GOAT_CHIN = ((227.0, 684.0), (212.0, 699.0), (185.0, 705.0), (158.0, 699.0), (145.0, 688.0))
_GOAT_NECK_TOP = ((140.0, 676.0), (152.0, 656.0), (168.0, 642.0), (204.0, 640.0), (218.0, 652.0), (232.0, 670.0))


def _goat_back() -> list[Layer]:
    """The goat's horns and ears, behind its head."""
    out: list[Layer] = []
    for k, horn in enumerate(_GOAT_HORNS):
        out += _inked(horn, GOAT_HORN, 10.0 + k, weight=INK * 0.95, amount=0.6)
    for k, ear in enumerate(_GOAT_EARS):
        out += [
            *_inked(ear, _GOAT_COAT, 12.0 + k, amount=0.6),
            _fill(_GOAT_EAR_INNER[k], GOAT_EAR, 14.0 + k, amount=0.4),
        ]
    return out


def _goat_skull() -> list[Layer]:
    """The horns' ridges and the fur on the goat's head."""
    return [_fur(points, FINE * 0.95, LINE) for points in _GOAT_RIDGES] + [
        _fur(points) for points in (*_GOAT_FUR[:4], *_GOAT_FUR[8:10])
    ]


def _goat_face() -> list[Layer]:
    """What slides across the goat's head: the muzzle, the nostrils and the beard over the chest."""
    layers = [_fill(_GOAT_MUZZLE, _GOAT_LIGHT, 18.0, amount=0.8)]
    layers += _inked(_GOAT_BEARD, _GOAT_LIGHT, 19.0, weight=INK * 0.85, amount=0.5)
    return layers + [_fur(points) for points in _GOAT_FUR[4:8]]


def _goat_chest() -> list[Layer]:
    """What sits on the goat's body: the shadow under the chin and the chest fur."""
    return [_fill(_GOAT_CHIN_SHADE, GOAT_SHADE, 17.0), *(_fur(points) for points in _GOAT_FUR[10:])]


GOAT_RIG = GOAT_CRITTER.rig(
    Split(
        chin=_GOAT_CHIN,
        top=_GOAT_NECK_TOP,
        hand=(1.2, 16.0),
        back=_goat_back,
        skull=_goat_skull,
        face=_goat_face,
        trunk=_goat_chest,
        head_over=True,
    ),
    GOAT_MOTION,
    free=18.0,
)


# -- the hamster -------------------------------------------------------------------------------------------------------
HAMSTER_SHADE = "#e07f7a"
HAMSTER_EAR = "#f6bfc4"
HAMSTER_NOSE = "#e2667f"
HAMSTER_BLUSH = "#f58f9b"
_HAMSTER_COAT = "#f4a09c"
_HAMSTER_LIGHT = "#fff3e2"
_HAMSTER_HEAD = (  # the hamster's head from the left of its neck over the pouches and the crown to the right
    (54.0, 694.0), (52.0, 679.0), (43.0, 672.0), (49.0, 666.0), (47.0, 654.0), (50.0, 644.0), (56.0, 630.0),
    (63.0, 617.0), (74.0, 600.0), (88.0, 584.0), (104.0, 572.0), (124.0, 561.0), (146.0, 553.0), (166.0, 548.0),
    (179.0, 548.0), (184.0, 540.0), (192.0, 548.0), (206.0, 548.0), (226.0, 552.0), (248.0, 559.0), (268.0, 570.0),
    (284.0, 584.0), (296.0, 600.0), (305.0, 617.0), (312.0, 633.0), (316.0, 650.0), (322.0, 658.0), (316.0, 667.0),
    (312.0, 686.0),
)  # fmt: skip
_HAMSTER_TORSO = Torso(_HAMSTER_HEAD, shoulder=136.0, slope=60.0, flank=141.0, arm=22.0)
_HAMSTER_BODY = _HAMSTER_TORSO.contour
_HAMSTER_EARS = (
    ((90.0, 558.0), (94.0, 545.0), (106.0, 539.0), (122.0, 541.0), (132.0, 550.0), (130.0, 562.0), (116.0, 572.0),
     (98.0, 570.0)),
    ((240.0, 548.0), (248.0, 539.0), (264.0, 537.0), (277.0, 544.0), (280.0, 556.0), (272.0, 567.0), (256.0, 569.0),
     (243.0, 561.0)),
)  # fmt: skip
_HAMSTER_EAR_INNER = (
    ((100.0, 558.0), (104.0, 548.0), (115.0, 545.0), (123.0, 552.0), (121.0, 561.0), (110.0, 565.0)),
    ((250.0, 550.0), (256.0, 543.0), (267.0, 543.0), (272.0, 551.0), (268.0, 559.0), (257.0, 560.0)),
)  # fmt: skip
_HAMSTER_POUCHES = (
    ((63.0, 637.0), (88.0, 627.0), (118.0, 630.0), (134.0, 648.0), (128.0, 669.0), (104.0, 679.0), (77.0, 677.0),
     (60.0, 660.0)),
    ((245.0, 629.0), (276.0, 625.0), (302.0, 632.0), (310.0, 651.0), (305.0, 671.0), (281.0, 680.0), (255.0, 676.0),
     (239.0, 658.0)),
)  # fmt: skip
_HAMSTER_MUZZLE = ((150.0, 631.0), (170.0, 625.0), (185.0, 626.0), (200.0, 624.0), (220.0, 630.0), (227.0, 645.0),
                   (215.0, 660.0), (185.0, 666.0), (156.0, 660.0), (144.0, 645.0))  # fmt: skip
_HAMSTER_BELLY = ((112.0, 717.0), (146.0, 704.0), (185.0, 701.0), (226.0, 705.0), (258.0, 718.0), (274.0, 754.0),
                  (276.0, 800.0), (270.0, 832.0), (100.0, 832.0), (94.0, 798.0), (96.0, 752.0))  # fmt: skip
_HAMSTER_NOSE = ((178.0, 631.0), (185.0, 630.0), (193.0, 631.0), (190.0, 636.0), (185.0, 638.0), (180.0, 636.0))
_HAMSTER_FUR = (
    ((170.0, 558.0), (174.0, 566.0)),  # the crown
    ((199.0, 556.0), (196.0, 565.0)),
    ((184.0, 552.0), (186.0, 561.0), (184.0, 566.0)),
    ((80.0, 679.0), (100.0, 683.0), (120.0, 676.0)),  # under the pouches
    ((256.0, 679.0), (281.0, 683.0)),
    ((106.0, 559.0), (113.0, 569.0)),  # the ear creases
    ((262.0, 556.0), (258.0, 565.0)),
    ((166.0, 742.0), (170.0, 755.0)),  # the belly
    ((204.0, 746.0), (200.0, 759.0)),
    ((184.0, 770.0), (186.0, 782.0)),
    ((146.0, 640.0), (118.0, 635.0)),  # whiskers
    ((146.0, 647.0), (116.0, 649.0)),
    ((224.0, 640.0), (253.0, 633.0)),
    ((224.0, 646.0), (255.0, 648.0)),
)


def _hamster_parts() -> list[tuple[Layer, bool]]:
    out: list[tuple[Layer, bool]] = []
    for k, ear in enumerate(_HAMSTER_EARS):
        out += [(layer, False) for layer in _inked(ear, _HAMSTER_COAT, 30.0 + k, amount=0.5)]
        out.append((_fill(_HAMSTER_EAR_INNER[k], HAMSTER_EAR, 32.0 + k, amount=0.3), False))
    body = drifted(_HAMSTER_BODY, 1.1, 34.0, _HAMSTER_TORSO.weights(CALM))
    out += [
        ((pressed(body, INK * 1.05, seed=34.0), "ink"), False),
        ((brush.outline(body, steps=3), _HAMSTER_COAT), False),
    ]
    layers: list[Layer] = shade(body, 22.0, HAMSTER_SHADE)
    layers.append(_fill(_HAMSTER_BELLY, _HAMSTER_LIGHT, 35.0))
    layers += [_fill(pouch, _HAMSTER_LIGHT, 36.0 + k) for k, pouch in enumerate(_HAMSTER_POUCHES)]
    layers.append(_fill(_HAMSTER_MUZZLE, _HAMSTER_LIGHT, 38.0))
    layers += [
        (brush.ellipse(98.0, 658.0, 13.0, 7.5, -8.0), HAMSTER_BLUSH),
        (brush.ellipse(274.0, 656.0, 13.0, 7.5, 8.0), HAMSTER_BLUSH),
    ]
    out += [(layer, False) for layer in layers]
    out += [(_fur(points), True) for points in _HAMSTER_FUR]
    out += [
        ((pressed(_HAMSTER_NOSE, FINE, seed=39.0), "ink"), False),
        ((brush.outline(_HAMSTER_NOSE, steps=2), HAMSTER_NOSE), False),
    ]
    out.append(((brush.ellipse(183.0, 632.0, 2.4, 1.5), "white"), False))
    return out


def _bead_pupil(look: Look, px: float, py: float, size: float) -> list[Layer]:
    """A beady, glossy pupil filling most of the eye: two highlights."""
    rx, ry = size * 1.75, size * 1.9
    return [
        (brush.ellipse(px, py, rx, ry), "ink"),
        (brush.ellipse(px - rx * 0.38, py - ry * 0.4, rx * 0.34, ry * 0.3), "white"),
        (brush.ellipse(px + rx * 0.35, py + ry * 0.38, rx * 0.15, ry * 0.13), "white"),
    ]


def _hamster_mouths(face: Look, kind: str) -> list[Layer] | None:
    if kind != "puff":
        return None
    mx, my = face.mouth
    out: list[Layer] = []
    for side, tilt in ((-1.0, -8.0), (1.0, 6.0)):  # the pouches blown up round, past the head
        cx, cy = mx + side * 92.0, my + 6.0
        cheek = _oval(cx, cy, 47.0, 33.0, 12)
        out += [(pressed(cheek, INK, seed=40.0 + side), "ink"), (brush.outline(cheek, steps=3), _HAMSTER_LIGHT)]
        out.append((brush.ellipse(cx + side * 4.0, cy + 6.0, 17.0, 9.0, tilt), HAMSTER_BLUSH))
        glint = [(cx - side * 26.0, cy - 14.0), (cx - side * 14.0, cy - 24.0)]
        out.append((brush.stroke(glint, FINE * 1.3, LINE, steps=3), "white"))
        out.append(_fur([(cx + side * 30.0, cy + 18.0), (cx + side * 18.0, cy + 27.0)]))
    out += _puff(face, mx, my, face.mouth_w * 0.8)[-3:]  # the closed smile and its corners
    return out


def _hamster_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A tiny paw held up: a pale mitt with its fingers pointing up."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.58, w * 0.5, HAMSTER_EAR, 41.0)
    out.append((brush.ellipse(paw[0], paw[1] + w * 0.12, w * 0.24, w * 0.16), HAMSTER_NOSE))
    for dx in (-0.25, 0.0, 0.25):
        x = paw[0] + dx * w
        out.append(_fur([(x, paw[1] - w * 0.48), (x + dx * 2.0, paw[1] - w * 0.2)], FINE * 0.9))
    return out


HAMSTER_CRITTER = Critter(
    name="hamster",
    face=Look(
        name="hamster",
        coat=_HAMSTER_COAT,
        dark=HAMSTER_SHADE,
        light=_HAMSTER_LIGHT,
        silhouette=_HAMSTER_BODY,
        eyes=((150.0, 615.0), (220.0, 615.0)),
        eye_r=15.0,
        mouth=(185.0, 650.0),
        mouth_w=30.0,
        limb=22.0,
        brows=True,
        shine=True,
        blush=HAMSTER_BLUSH,
        blink=2.4,
        paw=HAMSTER_EAR,
    ),
    shade=HAMSTER_SHADE,
    tilt=5.0,
    neck=(CENTRE, 720.0),
    fade=160.0,
    parts=lambda: _hamster_parts(),
    pupil=_bead_pupil,
    mouths=_hamster_mouths,
    paw=_hamster_paw,
    torso=_HAMSTER_TORSO,
)
HAMSTER = HAMSTER_CRITTER.look()
HAMSTER_MOTION = HeadStyle(  # quick and small: a fast light spring that bobs past rest, little breaths, darting eyes
    seed=3047,
    signature="~",
    nod_px=4.5,
    nod_roll=1.0,
    head=Spring(4.0, 0.6, 0.08),
    settle=Spring(3.0, 0.7),
    body=Spring(2.5, 0.9),
    min_gap=0.3,
    lean=0.5,
    idle_roll=0.9,
    idle_px=0.8,
    idle_hz=0.5,
    breath_period=1.8,
    breath_px=1.5,
    glance_every=2.0,
    glance_hold=0.45,
    glance_turn=1.2,
    glance_face=4.0,
)
_HAMSTER_CHIN = ((306.0, 688.0), (268.0, 692.0), (226.0, 694.0), (185.0, 695.0), (144.0, 694.0), (102.0, 692.0),
                 (62.0, 690.0))  # fmt: skip
_HAMSTER_CHIN_SOFT = ((296.0, 672.0), (250.0, 676.0), (185.0, 678.0), (120.0, 676.0), (72.0, 672.0), (78.0, 706.0),
                      (120.0, 704.0), (185.0, 703.0), (250.0, 704.0), (290.0, 706.0))  # fmt: skip
_HAMSTER_NECK_TOP = ((54.0, 694.0), (82.0, 668.0), (120.0, 652.0), (185.0, 648.0), (250.0, 652.0), (298.0, 664.0),
                     (312.0, 686.0))  # fmt: skip


def _hamster_back() -> list[Layer]:
    """The hamster's ears, behind its head."""
    out: list[Layer] = []
    for k, ear in enumerate(_HAMSTER_EARS):
        out += [
            *_inked(ear, _HAMSTER_COAT, 30.0 + k, amount=0.5),
            _fill(_HAMSTER_EAR_INNER[k], HAMSTER_EAR, 32.0 + k, amount=0.3),
        ]
    return out


def _hamster_skull() -> list[Layer]:
    """The chin's line coated over, head and body one mass as in the flat drawing, and the fur on the crown and ears."""
    layers = [(brush.outline(_HAMSTER_CHIN_SOFT, steps=3), _HAMSTER_COAT)]
    return layers + [_fur(points) for points in (*_HAMSTER_FUR[:3], *_HAMSTER_FUR[5:7])]


def _hamster_face() -> list[Layer]:
    """What slides across the hamster's head: the pouches, muzzle, blush, whiskers and nose."""
    layers = [_fill(pouch, _HAMSTER_LIGHT, 36.0 + k) for k, pouch in enumerate(_HAMSTER_POUCHES)]
    layers.append(_fill(_HAMSTER_MUZZLE, _HAMSTER_LIGHT, 38.0))
    layers += [
        (brush.ellipse(98.0, 658.0, 13.0, 7.5, -8.0), HAMSTER_BLUSH),
        (brush.ellipse(274.0, 656.0, 13.0, 7.5, 8.0), HAMSTER_BLUSH),
    ]
    layers += [_fur(points) for points in (*_HAMSTER_FUR[3:5], *_HAMSTER_FUR[10:])]
    layers += [(pressed(_HAMSTER_NOSE, FINE, seed=39.0), "ink"), (brush.outline(_HAMSTER_NOSE, steps=2), HAMSTER_NOSE)]
    layers.append((brush.ellipse(183.0, 632.0, 2.4, 1.5), "white"))
    return layers


def _hamster_belly() -> list[Layer]:
    """What sits on the hamster's body: the belly and its fur."""
    return [_fill(_HAMSTER_BELLY, _HAMSTER_LIGHT, 35.0), *(_fur(points) for points in _HAMSTER_FUR[7:10])]


HAMSTER_RIG = HAMSTER_CRITTER.rig(
    Split(
        chin=_HAMSTER_CHIN,
        top=_HAMSTER_NECK_TOP,
        hand=(1.1, 34.0),
        back=_hamster_back,
        skull=_hamster_skull,
        face=_hamster_face,
        trunk=_hamster_belly,
        head_over=True,
    ),
    HAMSTER_MOTION,
    free=34.0,
)
CRITTERS = {"sloth": SLOTH, "goat": GOAT, "hamster": HAMSTER}


# -- on a canvas -------------------------------------------------------------------------------------------------------
@register(
    "character",
    "toon-sloth",
    summary="A droopy olive sloth at the desk: a pale face with dark stripes down from the eyes, shaggy crown, long "
    "clawed arms, its own yawn; pressed ink, a tilted head, blinks and lip sync",
    examples=(
        'from srstudio import get\nfrom srstudio.toon import Pose\n'
        'poses = [Pose(0, "sleepy", "flat", "desk"), Pose(1, "wide", "yawn", "sigh")]\n'
        'groups = get("character", "toon-sloth")(ep.cv, ep.comp, poses, duration=2)',
    ),
)
def sloth(
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
    """Draw srstudio.toon.Pose(start, eyes, mouth, arms) states using srstudio.toon.EYES, MOUTHS and ARMS names.

    Pose starts are seconds relative to enter; the first is zero. Enter, duration (the exit time), taps and
    mouths use project seconds. Optional limbs are typed LimbTracks on the project clock. Returns pose groups.
    """
    return figure(cv, parent, SLOTH, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-goat",
    summary="A wiry lilac goat at the desk: back-swept horns, sideways ears, a long pale muzzle and beard, bar pupils, "
    "its own scream; pressed ink, a tilted head, blinks and lip sync",
    examples=(
        'from srstudio import get\nfrom srstudio.toon import Pose\n'
        'poses = [Pose(0, "half", "flat", "desk"), Pose(1, "shock", "scream", "sigh")]\n'
        'groups = get("character", "toon-goat")(ep.cv, ep.comp, poses, duration=2)',
    ),
)
def goat(
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
    """Draw srstudio.toon.Pose(start, eyes, mouth, arms) states using srstudio.toon.EYES, MOUTHS and ARMS names.

    Pose starts are seconds relative to enter; the first is zero. Enter, duration (the exit time), taps and
    mouths use project seconds. Optional limbs are typed LimbTracks on the project clock. Returns pose groups.
    """
    return figure(cv, parent, GOAT, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-hamster",
    summary="A small round apricot hamster at the desk: cream cheek pouches and belly, round ears, beady eyes, tiny "
    "paws, its own puffed cheeks; pressed ink, a tilted head, blinks and lip sync",
    examples=(
        'from srstudio import get\nfrom srstudio.toon import Pose\n'
        'poses = [Pose(0, "wide", "flat", "desk"), Pose(1, "narrow", "puff", "crossed")]\n'
        'groups = get("character", "toon-hamster")(ep.cv, ep.comp, poses, duration=2)',
    ),
)
def hamster(
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
    """Draw srstudio.toon.Pose(start, eyes, mouth, arms) states using srstudio.toon.EYES, MOUTHS and ARMS names.

    Pose starts are seconds relative to enter; the first is zero. Enter, duration (the exit time), taps and
    mouths use project seconds. Optional limbs are typed LimbTracks on the project clock. Returns pose groups.
    """
    return figure(cv, parent, HAMSTER, poses, duration, taps, enter, stickers, mouths, limbs=limbs)
