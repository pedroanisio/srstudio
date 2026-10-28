"""The parts of the **Soft** style (:data:`srstudio.styles.SOFT`).

A blob character is one rig of fixed topology: five tapered brush :class:`Stroke` s (two legs, torso,
two arms) and a head. A :class:`Pose` places them; because every pose has the same limbs, any two
poses interpolate. A performance is a list of :class:`Cue` s on a beat; a cue with ``ease`` arrives
through in-between drawings (smoothstep, ``fps`` drawings a second), so moves are animated, not cut.

The rig is drawn once: every limb is a filled outline path in two passes (every outline in ink, then
every fill in white) so head, body and limbs merge under one outline, and each limb's ``path`` is
hold-keyed on every drawing. Arms switch between the merged back pass and a front pass with their own
outline (hands clasped over the chest, arms on the desk). Eyes and mouth are gated groups that follow
the head; a ``sing`` mouth follows the soundtrack's mouth states.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from . import signature
from .canvas import Canvas
from .registry import register
from .soundtrack import MOUTHS as MOUTH_STATES

__all__ = [
    "OUTLINE",
    "HEAD",
    "LIMBS",
    "ARMS",
    "EYES",
    "MOUTHS",
    "POSES",
    "SEAT",
    "FLOOR",
    "SCALE",
    "BlobError",
    "Stroke",
    "Pose",
    "Cue",
    "Drawing",
    "FEET",
    "FRONTABLE",
    "SEATED_FLOOR",
    "LAPTOP",
    "keyboard",
    "silhouette",
    "drawings",
    "mouth_track",
    "pip",
    "office",
]

Point = tuple[float, float]

OUTLINE = 4.0  # outline thickness of the silhouette, in output pixels
HEAD = 100.0  # head radius of the blob in pose units
LIMBS = ("leg_l", "leg_r", "torso", "arm_l", "arm_r")  # back-to-front order of the merged pass
ARMS = ("arm_l", "arm_r")
FEET = ("leg_l", "leg_r")
FRONTABLE = (*FEET, *ARMS)  # limbs a pose may outline over the body, drawn in this order
BLUSH = "#F4B4A4"
LEAF = "#8CC47A"
TONGUE = "#E8837A"
WOOD_LINE = "#3A2615"
WOOD_TOP = "#C68A4E"
WOOD_FRONT = "#A86F38"
WOOD_SIDE = "#8E5A2B"
METAL = "#959FA6"
METAL_LIGHT = "#B9C1C7"
METAL_DARK = "#6E777D"

SCALE = 1.48  # the soft office is drawn for Pip at this scale
FLOOR = 1600.0  # standing poses put their origin (between the feet) on this line, in front of the chair
SEAT = (790.0, 1340.0)  # a sitting pose's origin (the hip) on the soft office chair
SEATED_FLOOR = 1476.0  # where a seated pose's soles meet the floor, beside the chair's front legs
LAPTOP = (277.5, 416.0, 0.75)  # the laptop's x, y and scale on the desk, within reach of a seated pose's hands


class BlobError(ValueError):
    """A stroke, pose, cue or mouth track the blob cannot draw."""


def _finite(*values: float) -> bool:
    return all(math.isfinite(v) for v in values)


def _lerp(a: float, b: float, u: float) -> float:
    if u == 1:  # exact on the key, so a landed pose equals its sheet pose
        return b
    return a + (b - a) * u


def _lerp_pt(a: Point, b: Point, u: float) -> Point:
    return (_lerp(a[0], b[0], u), _lerp(a[1], b[1], u))


# -- strokes -----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Stroke:
    """A cubic centreline ``p0..p3`` drawn ``w0`` wide at the start and ``w1`` at the end, with round caps."""

    p0: Point
    p1: Point
    p2: Point
    p3: Point
    w0: float
    w1: float

    def __post_init__(self) -> None:
        if not _finite(*self.p0, *self.p1, *self.p2, *self.p3, self.w0, self.w1):
            raise BlobError(f"stroke {self} has a value that is not finite")
        if self.w0 <= 0 or self.w1 <= 0:
            raise BlobError(f"stroke widths {self.w0}, {self.w1} must be positive")

    def point(self, t: float) -> Point:
        s = 1 - t
        a, b, c, d = s * s * s, 3 * s * s * t, 3 * s * t * t, t * t * t
        return (
            a * self.p0[0] + b * self.p1[0] + c * self.p2[0] + d * self.p3[0],
            a * self.p0[1] + b * self.p1[1] + c * self.p2[1] + d * self.p3[1],
        )

    def tangent(self, t: float) -> Point:
        s = 1 - t
        dx = (
            3 * s * s * (self.p1[0] - self.p0[0])
            + 6 * s * t * (self.p2[0] - self.p1[0])
            + 3 * t * t * (self.p3[0] - self.p2[0])
        )
        dy = (
            3 * s * s * (self.p1[1] - self.p0[1])
            + 6 * s * t * (self.p2[1] - self.p1[1])
            + 3 * t * t * (self.p3[1] - self.p2[1])
        )
        n = math.hypot(dx, dy)
        if n < 1e-9:  # a control point on its end point: fall back to the chord
            dx, dy = self.p3[0] - self.p0[0], self.p3[1] - self.p0[1]
            n = math.hypot(dx, dy) or 1.0
        return (dx / n, dy / n)

    def _rim(self, samples: int, cap: int) -> tuple[list[Point], list[Point]]:
        """The rim without and with the start cap: left side, end cap, right side back; then the start cap
        (``cap`` is even, so each cap has a point on its tip)."""
        left, right = [], []
        for i in range(samples + 1):
            t = i / samples
            (cx, cy), (tx, ty) = self.point(t), self.tangent(t)
            h = _lerp(self.w0, self.w1, t) / 2
            left.append((cx - ty * h, cy + tx * h))
            right.append((cx + ty * h, cy - tx * h))

        def arc(t: float, h: float, sign: float) -> list[Point]:
            (cx, cy), (tx, ty) = self.point(t), self.tangent(t)
            out = []
            for k in range(1, cap):
                a = math.pi * k / cap
                nx, ny = -ty * math.cos(a), tx * math.cos(a)  # from the left normal...
                fx, fy = sign * tx * math.sin(a), sign * ty * math.sin(a)  # ...around the tip
                out.append((cx + (nx + fx) * h, cy + (ny + fy) * h))
            return out

        rim = left + arc(1, self.w1 / 2, 1) + list(reversed(right))
        return rim, list(reversed(arc(0, self.w0 / 2, -1)))

    def outline(self, samples: int = 14, cap: int = 8) -> str:
        """The closed outline: the left side, the end cap, the right side back, the start cap."""
        rim, start = self._rim(samples, cap)
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in rim + start) + " Z"

    def contour(self, samples: int = 14, cap: int = 8) -> str:
        """The open contour: the outline without its start cap, so a limb traced with it grows out of the body."""
        rim, _ = self._rim(samples, cap)
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in rim)

    def widened(self, by: float) -> Stroke:
        return Stroke(self.p0, self.p1, self.p2, self.p3, self.w0 + by, self.w1 + by)

    def lerp(self, other: Stroke, u: float) -> Stroke:
        return Stroke(
            _lerp_pt(self.p0, other.p0, u),
            _lerp_pt(self.p1, other.p1, u),
            _lerp_pt(self.p2, other.p2, u),
            _lerp_pt(self.p3, other.p3, u),
            _lerp(self.w0, other.w0, u),
            _lerp(self.w1, other.w1, u),
        )

    def mapped(self, f: Callable[[Point], Point]) -> Stroke:
        return Stroke(f(self.p0), f(self.p1), f(self.p2), f(self.p3), self.w0, self.w1)


def seg(a: Point, b: Point, w0: float, w1: float | None = None, bend: float = 0.0) -> Stroke:
    """A stroke from ``a`` to ``b``, bowed sideways by ``bend`` × its length (positive: to the left of travel)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    nx, ny = dy * bend, -dx * bend
    return Stroke(
        a,
        (a[0] + dx / 3 + nx, a[1] + dy / 3 + ny),
        (a[0] + 2 * dx / 3 + nx, a[1] + 2 * dy / 3 + ny),
        b,
        w0,
        w0 if w1 is None else w1,
    )


# -- poses --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Pose:
    """Head centre and the five limbs; ``front`` arms are outlined over the body; ``face`` offsets the features."""

    name: str
    head: Point
    limbs: Mapping[str, Stroke]
    front: frozenset[str] = field(default_factory=frozenset)
    face: Point = (0.0, 0.0)

    def __post_init__(self) -> None:
        if set(self.limbs) != set(LIMBS):
            raise BlobError(f"pose {self.name!r} has limbs {sorted(self.limbs)}, not {sorted(LIMBS)}")
        if not self.front <= set(FRONTABLE):
            raise BlobError(
                f"pose {self.name!r} puts {sorted(self.front - set(FRONTABLE))} in front; only arms and legs can be"
            )
        if not _finite(*self.head, *self.face):
            raise BlobError(f"pose {self.name!r} has a value that is not finite")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pose):
            return NotImplemented
        return (self.name, self.head, dict(self.limbs), self.front, self.face) == (
            other.name,
            other.head,
            dict(other.limbs),
            other.front,
            other.face,
        )

    def __hash__(self) -> int:
        return hash((self.name, self.head, self.front, self.face))

    def lerp(self, other: Pose, u: float) -> Pose:
        """Part way (``u``) from this pose to ``other``. In between, only arms in front in both poses stay in
        front, so an arm on its way to or from the front passes behind the body, never across the face."""
        return Pose(
            self.name if u < 0.5 else other.name,
            _lerp_pt(self.head, other.head, u),
            {k: self.limbs[k].lerp(other.limbs[k], u) for k in LIMBS},
            self.front if u <= 0 else other.front if u >= 1 else self.front & other.front,
            _lerp_pt(self.face, other.face, u),
        )

    def placed(self, x: float, y: float, turn: float = 0.0, flip: bool = False) -> Pose:
        """Mirrored (``flip``), turned ``turn`` degrees about the origin, then moved to ``x, y``."""
        c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))

        def vec(p: Point) -> Point:
            px = -p[0] if flip else p[0]
            return (px * c - p[1] * s, px * s + p[1] * c)

        def pt(p: Point) -> Point:
            vx, vy = vec(p)
            return (vx + x, vy + y)

        return Pose(
            self.name, pt(self.head), {k: v.mapped(pt) for k, v in self.limbs.items()}, self.front, vec(self.face)
        )


TORSO = (150.0, 195.0)
LEG = (76.0, 58.0)
ARM = (36.0, 32.0)
SHADOW = (250.0, 34.0)  # contact shadow under the feet, in pose units


def _pose(name, head, front=(), face=(0.0, 0.0), **limbs: Stroke) -> Pose:
    return Pose(name, head, limbs, frozenset(front), face)


def _standing_legs(dx_l=0.0, dx_r=0.0) -> dict[str, Stroke]:
    return {
        "leg_l": seg((-45, -200), (-50 + dx_l, -42), *LEG, bend=0.04),
        "leg_r": seg((45, -200), (50 + dx_r, -42), *LEG, bend=-0.04),
    }


_TORSO_STAND = seg((0, -330), (0, -215), *TORSO)


def _forearm(shoulder: Point, hand: Point) -> Stroke:
    """An arm that drops from the shoulder to the elbow and reaches forward to the hand."""
    return Stroke(shoulder, (shoulder[0] - 16, shoulder[1] + 62), (hand[0] + 58, hand[1] + 10), hand, *ARM)


def _sitting(hand_l: Point, hand_r: Point, head: Point = (-40, -322), face: Point = (-26, 6)) -> Pose:
    """Seated facing left: the hip on the origin, thighs level along the seat, knees bent, shins down to the floor,
    forearms forward onto the keyboard. The near leg is outlined over the far one."""
    return _pose(
        "sit",
        head,
        front=("arm_l", "leg_l"),  # 3/4 view: the near arm and leg in front, the far arm behind the body
        face=face,
        torso=seg((5, -92), (-22, -212), 190, 150),
        leg_l=Stroke((-10, -40), (-75, -48), (-108, -22), (-102, 62), *LEG),
        leg_r=Stroke((22, -32), (-40, -38), (-72, -14), (-64, 64), *LEG),
        arm_l=_forearm((-62, -205), hand_l),
        arm_r=_forearm((-42, -198), hand_r),
    )


def _named(pose: Pose, name: str) -> Pose:
    return Pose(name, pose.head, pose.limbs, pose.front, pose.face)


def _raised(shoulder: Point, hand: Point, out: float) -> Stroke:
    """An arm raised from the shoulder, its elbow bowed ``out`` (negative bows to the left)."""
    return Stroke(shoulder, (shoulder[0] + out, shoulder[1] - 40), (hand[0] + out * 0.6, hand[1] + 50), hand, *ARM)


_HANDS_BEHIND_HEAD = {
    "arm_l": Stroke((-62, -312), (-122, -330), (-120, -405), (-66, -428), *ARM),
    "arm_r": Stroke((62, -312), (122, -330), (120, -405), (66, -428), *ARM),
}

# Standing poses: origin on the floor between the feet. Sitting poses: origin at the hip on the seat.
POSES: dict[str, Pose] = {
    p.name: p
    for p in (
        _pose(
            "stand",
            (0, -430),
            front=ARMS,
            torso=_TORSO_STAND,
            **_standing_legs(),
            arm_l=seg((-58, -312), (-112, -192), *ARM, bend=-0.10),
            arm_r=seg((58, -312), (112, -192), *ARM, bend=0.10),
        ),
        _pose(
            "step",
            (10, -428),
            front=ARMS,
            face=(16, 0),
            torso=seg((0, -330), (5, -215), *TORSO),
            leg_l=seg((-40, -200), (-98, -46), *LEG, bend=0.05),
            leg_r=Stroke((45, -200), (105, -165), (115, -100), (88, -62), *LEG),
            arm_l=seg((-64, -312), (-140, -225), *ARM, bend=-0.1),
            arm_r=seg((64, -312), (160, -398), *ARM, bend=0.1),
        ),
        _named(_sitting((-170, -112), (-150, -108)), "sit"),
        _named(_sitting((-178, -118), (-150, -106), head=(-44, -318)), "type-a"),
        _named(_sitting((-166, -106), (-158, -118), head=(-36, -326)), "type-b"),
        _named(_sitting((-170, -112), (-150, -108), head=(-46, -308), face=(-28, 10)), "nod"),
        _pose(
            "clasp",
            (0, -432),
            front=ARMS,
            face=(0, 4),
            torso=_TORSO_STAND,
            **_standing_legs(14, -14),
            arm_l=Stroke((-62, -306), (-100, -232), (-46, -212), (-10, -246), *ARM),
            arm_r=Stroke((62, -306), (100, -232), (46, -212), (10, -246), *ARM),
        ),
        _pose(
            "lean",
            (78, -425),
            face=(22, 2),
            torso=seg((-15, -205), (38, -322), 195, 150),
            leg_l=seg((-42, -192), (-104, -45), *LEG, bend=0.05),
            leg_r=Stroke((5, -196), (60, -140), (48, -80), (12, -45), *LEG),
            arm_l=seg((10, -305), (-72, -205), *ARM, bend=-0.12),  # hangs behind the body
            arm_r=seg((52, -300), (182, -262), *ARM, bend=0.18),  # elbow out on the chair's back rail
        ),
        _pose(
            "walk-a",  # weight on the left foot, the right foot up and swinging out to the right
            (-8, -432),
            front=ARMS,
            face=(6, 0),
            torso=seg((0, -330), (-6, -215), *TORSO),
            leg_l=seg((-40, -200), (-25, -42), *LEG, bend=0.03),
            leg_r=Stroke((45, -200), (112, -178), (142, -118), (132, -88), *LEG),
            arm_l=seg((-64, -312), (-130, -215), *ARM, bend=-0.1),
            arm_r=seg((64, -312), (140, -220), *ARM, bend=0.1),
        ),
        _pose(
            "stride",  # both feet down, wide apart
            (0, -420),
            front=ARMS,
            face=(8, 2),
            torso=seg((0, -320), (0, -207), *TORSO),
            leg_l=seg((-45, -195), (-140, -42), *LEG, bend=0.05),
            leg_r=seg((45, -195), (140, -42), *LEG, bend=-0.05),
            arm_l=seg((-64, -302), (-118, -192), *ARM, bend=-0.12),
            arm_r=seg((64, -302), (118, -192), *ARM, bend=0.12),
        ),
        _pose(
            "walk-b",  # weight on the right foot, the left foot up and closing in
            (8, -432),
            front=ARMS,
            face=(10, 0),
            torso=seg((0, -330), (6, -215), *TORSO),
            leg_l=Stroke((-45, -200), (-92, -160), (-80, -110), (-48, -92), *LEG),
            leg_r=seg((40, -200), (25, -42), *LEG, bend=-0.03),
            arm_l=seg((-64, -312), (-140, -220), *ARM, bend=-0.1),
            arm_r=seg((64, -312), (130, -215), *ARM, bend=0.1),
        ),
        _pose(
            "cheer-a",  # both arms up in a V beside the head, stretched tall
            (0, -445),
            face=(0, -4),
            torso=seg((0, -340), (0, -215), *TORSO),
            **_standing_legs(),
            arm_l=_raised((-64, -322), (-138, -462), -30),
            arm_r=_raised((64, -322), (138, -462), 30),
        ),
        _pose(
            "cheer-b",  # the bounce between cheers: knees bent, hands still up
            (0, -418),
            face=(0, -2),
            torso=seg((0, -318), (0, -205), *TORSO),
            leg_l=Stroke((-45, -195), (-100, -140), (-92, -82), (-56, -42), *LEG),
            leg_r=Stroke((45, -195), (100, -140), (92, -82), (56, -42), *LEG),
            arm_l=_raised((-64, -300), (-150, -430), -26),
            arm_r=_raised((64, -300), (150, -430), 26),
        ),
        _pose(
            "wave-a",  # the right hand up and waving, the left hanging in front
            (4, -432),
            front=("arm_l",),
            face=(4, 0),
            torso=_TORSO_STAND,
            **_standing_legs(),
            arm_l=seg((-58, -312), (-112, -192), *ARM, bend=-0.10),
            arm_r=_raised((62, -314), (128, -452), 28),
        ),
        _pose(
            "wave-b",
            (8, -430),
            front=("arm_l",),
            face=(6, 0),
            torso=_TORSO_STAND,
            **_standing_legs(),
            arm_l=seg((-58, -312), (-112, -192), *ARM, bend=-0.10),
            arm_r=_raised((62, -314), (162, -438), 14),
        ),
        _pose(
            "groove-a",
            (0, -430),
            torso=_TORSO_STAND,
            leg_l=seg((-45, -200), (-96, -46), *LEG, bend=0.05),
            leg_r=seg((45, -200), (50, -42), *LEG, bend=-0.04),
            **_HANDS_BEHIND_HEAD,
        ),
        _pose(
            "groove-b",
            (0, -430),
            torso=_TORSO_STAND,
            leg_l=seg((-45, -200), (-50, -42), *LEG, bend=0.04),
            leg_r=seg((45, -200), (96, -46), *LEG, bend=-0.05),
            **_HANDS_BEHIND_HEAD,
        ),
        _pose(
            "groove-c",
            (0, -415),
            torso=seg((0, -315), (0, -205), *TORSO),
            leg_l=Stroke((-45, -195), (-115, -135), (-100, -80), (-58, -42), *LEG),
            leg_r=Stroke((45, -195), (115, -135), (100, -80), (58, -42), *LEG),
            arm_l=Stroke((-62, -298), (-122, -316), (-120, -391), (-66, -414), *ARM),
            arm_r=Stroke((62, -298), (122, -316), (120, -391), (66, -414), *ARM),
        ),
    )
}


# -- faces ------------------------------------------------------------------------------------------------
def _stroke(cv: Canvas, g, d: str, sw: float = 6) -> None:
    cv.path(g, d, stroke=cv.ink, sw=sw)


def _eye(cv: Canvas, g, x: float, y: float, w: float, h: float, pupil: float, dx: float = 0.0) -> None:
    cv.ellipse(g, x - w / 2, y - h / 2, w, h, cv.white, cv.ink, 4.5)
    cv.ellipse(g, x - pupil / 2 + dx, y - pupil * 0.55 + h * 0.12, pupil, pupil * 1.1, cv.ink)


def _eyes(cv: Canvas, g, kind: str, x: float, y: float) -> None:
    for side in (-1, 1):
        ex = x + side * 30
        if kind == "open":
            _eye(cv, g, ex, y, 40, 46, 17)
        elif kind == "look":
            _eye(cv, g, ex, y, 40, 46, 17, dx=-8)
        elif kind == "wide":
            _eye(cv, g, ex, y - 3, 48, 56, 13)
        elif kind == "happy":
            _stroke(cv, g, f"M {ex - 15:g} {y + 6:g} Q {ex:g} {y - 14:g} {ex + 15:g} {y + 6:g}")
        elif kind == "squint":
            tip, back = ex - 11 * side, ex + 13 * side  # pointing inward: ">" on the left, "<" on the right
            _stroke(cv, g, f"M {back:g} {y - 12:g} L {tip:g} {y:g} L {back:g} {y + 12:g}")
        else:  # closed
            _stroke(cv, g, f"M {ex - 15:g} {y - 2:g} Q {ex:g} {y + 11:g} {ex + 15:g} {y - 2:g}")


def _mouth(cv: Canvas, g, kind: str, x: float, y: float) -> None:
    if kind == "smile":
        _stroke(cv, g, f"M {x - 18:g} {y:g} Q {x:g} {y + 15:g} {x + 18:g} {y:g}", 5.5)
    elif kind == "grin":
        cv.path(
            g,
            f"M {x - 30:g} {y - 5:g} L {x + 30:g} {y - 5:g} Q {x + 27:g} {y + 32:g} {x:g} {y + 34:g} "
            f"Q {x - 27:g} {y + 32:g} {x - 30:g} {y - 5:g} Z",
            cv.ink,
            cv.ink,
            2,
        )
        cv.path(
            g,
            f"M {x - 15:g} {y + 25:g} Q {x:g} {y + 15:g} {x + 15:g} {y + 25:g} Q {x + 8:g} {y + 32:g} "
            f"{x:g} {y + 32:g} Q {x - 8:g} {y + 32:g} {x - 15:g} {y + 25:g} Z",
            TONGUE,
            sw=0,
        )
    elif kind == "o":
        cv.ellipse(g, x - 11, y - 4, 22, 27, cv.ink)
    elif kind == "small":
        cv.ellipse(g, x - 14, y, 28, 14, cv.ink)
    else:  # flat
        _stroke(cv, g, f"M {x - 14:g} {y + 4:g} L {x + 14:g} {y + 4:g}", 5.5)


EYES: dict[str, Callable[..., None]] = {
    k: (lambda cv, g, x, y, k=k: _eyes(cv, g, k, x, y)) for k in ("open", "look", "wide", "happy", "squint", "closed")
}
# "sing" follows the soundtrack: the amplitude mouth states map onto drawn mouths.
SING = {"rest": "smile", "smile": "smile", "small": "small", "open": "grin", "round": "o"}
MOUTHS: tuple[str, ...] = ("smile", "grin", "o", "small", "flat", "sing")


def _sprout(cv: Canvas, g, x: float, y: float, r: float) -> None:
    """Pip's sprout: a stem planted in the head (its base hidden by the head's fill) and two leaves."""
    top = y - r
    _stroke(cv, g, f"M {x:g} {top + 10:g} Q {x + 6:g} {top - 22:g} {x - 2:g} {top - 44:g}", 6)
    for d in (
        f"M {x - 2:g} {top - 42:g} Q {x - 36:g} {top - 72:g} {x - 52:g} {top - 38:g} Q {x - 24:g} {top - 27:g} "
        f"{x - 2:g} {top - 42:g} Z",
        f"M {x - 2:g} {top - 42:g} Q {x + 27:g} {top - 82:g} {x + 52:g} {top - 55:g} Q {x + 27:g} {top - 32:g} "
        f"{x - 2:g} {top - 42:g} Z",
    ):
        cv.path(g, d, LEAF, cv.ink, 4)


# -- the static silhouette ------------------------------------------------------------------------------------
def silhouette(
    cv: Canvas,
    parent,
    strokes: Sequence[Stroke],
    head: tuple[float, float, float] | None = None,
    *,
    outline: float = OUTLINE,
    between: Callable[[object], object] | None = None,
):
    """Every stroke (and the head disc) outlined, then ``between(group)``, then every fill: one merged shape."""
    g = parent.add_group(id=cv.uid("silhouette"))
    for s in strokes:
        cv.path(g, s.outline(), cv.ink, cv.ink, 2 * outline)
    if head:
        x, y, r = head
        cv.ellipse(g, x - r - outline, y - r - outline, 2 * (r + outline), 2 * (r + outline), cv.ink)
    if between is not None:
        between(g)
    for s in strokes:
        cv.path(g, s.outline(), cv.white, cv.clear, 0)
    if head:
        x, y, r = head
        cv.ellipse(g, x - r, y - r, 2 * r, 2 * r, cv.white)
    return g


# -- cues and drawings -----------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cue:
    """From ``time`` until the next cue: ``pose`` with ``eyes`` and ``mouth`` at ``x, y`` (added to the
    character's position), turned ``turn`` degrees and mirrored when ``flip``.

    ``ease`` seconds before ``time`` the character leaves the previous pose through in-between drawings and
    lands on the beat; ``lift`` raises the middle of that move on an arc. ``pin`` names a leg whose foot stays
    planted through the move: the position is then solved from that foot, not given. ``overshoot`` lands that
    fraction past the pose and settles back one drawing later. The expression changes when the pose lands."""

    time: float
    pose: str
    eyes: str = "open"
    mouth: str = "smile"
    x: float = 0.0
    y: float = 0.0
    turn: float = 0.0
    flip: bool = False
    ease: float = 0.0
    lift: float = 0.0
    pin: str | None = None
    overshoot: float = 0.0


@dataclass(frozen=True)
class Drawing:
    """One drawing of the performance: shown from ``time`` until the next. ``u`` < 1 marks an in-between,
    ``u`` > 1 an overshoot; ``face`` is the cue whose eyes and mouth it shows."""

    time: float
    cue: Cue
    pose: Pose
    u: float
    face: Cue


MAX_OVERSHOOT = 0.5


def _smooth(x: float) -> float:
    return x * x * (3 - 2 * x)


def _check(cues: Sequence[Cue], end: float) -> None:
    if not cues:
        raise BlobError("a performance needs at least one cue")
    if cues[0].time != 0:
        raise BlobError(f"the first cue must be at 0, not {cues[0].time}")
    for cue in cues:
        if not _finite(cue.time, cue.x, cue.y, cue.turn, cue.ease, cue.lift, cue.overshoot):
            raise BlobError(f"cue {cue} has a value that is not finite")
        if cue.pose not in POSES:
            raise BlobError(f"unknown pose {cue.pose!r}; one of {sorted(POSES)}")
        if cue.eyes not in EYES:
            raise BlobError(f"unknown eyes {cue.eyes!r}; one of {sorted(EYES)}")
        if cue.mouth not in MOUTHS:
            raise BlobError(f"unknown mouth {cue.mouth!r}; one of {MOUTHS}")
        if cue.pin is not None:
            if cue.pin not in FEET:
                raise BlobError(f"unknown pin {cue.pin!r}; one of {FEET}")
            if cue.x or cue.y or cue.lift:
                raise BlobError(
                    f"the cue at {cue.time} takes its position from the planted foot; leave x, y, lift at 0"
                )
        if not 0 <= cue.overshoot <= MAX_OVERSHOOT:
            raise BlobError(f"overshoot {cue.overshoot} of the cue at {cue.time} must lie in 0..{MAX_OVERSHOOT}")
    for a, b in zip(cues, cues[1:], strict=False):
        if b.time <= a.time:
            raise BlobError(f"cue times must be increasing: {a.time} then {b.time}")
        if not 0 <= b.ease <= b.time - a.time:
            raise BlobError(f"ease {b.ease} of the cue at {b.time} must lie in 0..{b.time - a.time:g}")
    if cues[0].ease:
        raise BlobError("the first cue has nothing to ease from")
    if cues[0].pin is not None:
        raise BlobError("the first cue cannot be pinned: no foot is planted before it")
    if cues[-1].time >= end:
        raise BlobError(f"the last cue at {cues[-1].time} is not before the end {end}")


def drawings(cues: Sequence[Cue], *, end: float, fps: float = 15) -> list[Drawing]:
    """The drawings of a performance: each cue's eased in-betweens, its key drawing and, after an overshoot,
    its settle. Poses blend in pose space and positions and turns blend apart, so a turn is a rotation."""
    _check(cues, end)
    out: list[Drawing] = []
    before: tuple[Pose, float, float, float, bool, Cue] | None = None  # the previous cue at rest
    for k, cue in enumerate(cues):
        target = POSES[cue.pose]
        anchor = out[-1].pose.limbs[cue.pin].p3 if cue.pin else None
        x0, y0, turn0, flip0, start = (cue.x, cue.y, cue.turn, cue.flip, target)
        if before is not None:
            start, x0, y0, turn0, flip0, _ = before

        def at(u: float, cue=cue, target=target, start=start, x0=x0, y0=y0, turn0=turn0, flip0=flip0, anchor=anchor):
            pose = start.lerp(target, u)
            turn, flip = _lerp(turn0, cue.turn, u), (flip0 if u < 0.5 else cue.flip)
            if anchor is not None and cue.pin is not None:
                foot = pose.placed(0, 0, turn, flip).limbs[cue.pin].p3
                return pose.placed(anchor[0] - foot[0], anchor[1] - foot[1], turn, flip)
            lift = cue.lift * math.sin(math.pi * u) if u < 1 else 0.0
            return pose.placed(_lerp(x0, cue.x, u), _lerp(y0, cue.y, u) - lift, turn, flip)

        if before is not None and cue.ease > 0:
            n = max(1, round(cue.ease * fps))
            for j in range(n):
                u = _smooth((j + 1) / (n + 1))
                out.append(Drawing(cue.time - cue.ease + j * cue.ease / n, cue, at(u), u, before[5]))
        rest = at(1.0)
        if cue.overshoot:
            settle = cue.time + 1 / fps
            nxt = cues[k + 1].time - cues[k + 1].ease if k + 1 < len(cues) else end
            if settle >= nxt:
                raise BlobError(f"the overshoot at {cue.time} needs one drawing (1/{fps:g} s) to settle before {nxt:g}")
            out.append(Drawing(float(cue.time), cue, at(1 + cue.overshoot), 1 + cue.overshoot, cue))
            out.append(Drawing(settle, cue, rest, 1.0, cue))
        else:
            out.append(Drawing(float(cue.time), cue, rest, 1.0, cue))
        if cue.pin:  # where the solved pose stands, so the next move starts from it
            ox = rest.head[0] - target.placed(0, 0, cue.turn, cue.flip).head[0]
            oy = rest.head[1] - target.placed(0, 0, cue.turn, cue.flip).head[1]
        else:
            ox, oy = cue.x, cue.y
        before = (target, ox, oy, cue.turn, cue.flip, cue)
    return out


def mouth_track(frames: Sequence[Drawing], states: Sequence[tuple[float, str]] = ()) -> list[tuple[float, str]]:
    """The drawn mouth at every drawing and every mouth-state time: the shown cue's own mouth, or the song's while
    it sings."""
    times = sorted({d.time for d in frames} | {float(t) for t, _ in states})
    out, i, j, state = [], 0, 0, "rest"
    for t in times:
        while i + 1 < len(frames) and frames[i + 1].time <= t:
            i += 1
        while j < len(states) and states[j][0] <= t:
            state = states[j][1]
            j += 1
        mouth = frames[i].face.mouth
        out.append((t, SING[state] if mouth == "sing" else mouth))
    return out


def _changes(track: Sequence[tuple[float, object]], value: object) -> list[tuple[float, int]]:
    keys: list[tuple[float, int]] = []
    for t, v in track:
        on = int(v == value)
        if not keys or keys[-1][1] != on:
            keys.append((t, on))
    return keys


def _show(cv: Canvas, node, keys: list[tuple[float, int]]) -> None:
    if len(keys) == 1:
        node.opacity = keys[0][1]
    else:
        cv.keys(node, "opacity", keys)


@register(
    "character",
    "pip",
    summary="Pip, the sprout-headed white blob: one interpolating rig (stand, step, walk, sit, type, nod, clasp, "
    "lean, groove, cheer, wave), eased in-betweens on a beat, six eyes, five mouths and a sung mouth that follows "
    "the soundtrack",
    episodes=("focus-mode", "camera-off"),
)
def pip(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str = "pip",
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
):
    """Pip performing ``cues`` until ``end``; ``mouth_states`` (``Episode.mouth``) drive every ``sing`` mouth;
    ``shadow`` puts a contact shadow under the feet on every drawing."""
    frames = drawings(cues, end=end, fps=fps)
    if any(c.mouth == "sing" for c in cues):
        if not mouth_states:
            raise BlobError("a sung cue needs mouth states (Episode.mouth) to move the mouth")
        unknown = sorted({s for _, s in mouth_states} - set(MOUTH_STATES))
        if unknown:
            raise BlobError(f"unknown mouth state {unknown[0]!r}; one of {MOUTH_STATES}")
    o = OUTLINE / scale
    root = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    times = [d.time for d in frames]
    if shadow:
        feet = [[d.pose.limbs[leg].p3 for leg in FEET] for d in frames]
        g = cv.group(root, f"{id}-shadow")
        cv.keys(g, "x", [(t, round((a[0] + b[0]) / 2, 3)) for t, (a, b) in zip(times, feet, strict=True)])
        cv.keys(g, "y", [(t, round(max(a[1], b[1]) + LEG[1] / 2, 3)) for t, (a, b) in zip(times, feet, strict=True)])
        cv.ellipse(g, -SHADOW[0] / 2, -SHADOW[1] / 2, *SHADOW, cv.ink, opacity=0.13)

    def limb_shape(g, limb: str, fill: str, stroke: str, sw: float):
        paths = [d.pose.limbs[limb].outline() for d in frames]
        shape = cv.path(g, paths[0], fill, stroke, sw)
        cv.keys(shape, "path", list(zip(times, paths, strict=True)))
        return shape

    def head_at(g, dx: float = 0.0, dy: float = 0.0):
        cv.keys(g, "x", [(d.time, round(d.pose.head[0] + dx, 3)) for d in frames])
        cv.keys(g, "y", [(d.time, round(d.pose.head[1] + dy, 3)) for d in frames])
        return g

    fronts = {limb: [(d.time, limb in d.pose.front) for d in frames] for limb in FRONTABLE}
    for pass_name, fill, stroke, sw in (("outline", cv.ink, cv.ink, 2 * o), ("fill", cv.white, cv.clear, 0)):
        g = cv.group(root, f"{id}-{pass_name}")
        for limb in LIMBS:
            shape = limb_shape(g, limb, fill, stroke, sw)
            if limb in fronts and any(v for _, v in fronts[limb]):
                _show(cv, shape, _changes(fronts[limb], False))
        head = head_at(cv.group(g, f"{id}-head-{pass_name}"))
        r = radius + (o if pass_name == "outline" else 0)
        cv.ellipse(head, -r, -r, 2 * r, 2 * r, fill)
        if pass_name == "outline":
            _sprout(cv, head_at(cv.group(root, f"{id}-sprout")), 0, 0, radius)
    # A front limb is filled, then traced along its sides and tip only: the root stays open inside the body, so
    # the limb grows out of it instead of sitting on it. Widened by the outline so it matches the silhouette's edge.
    for limb in FRONTABLE:
        if any(v for _, v in fronts[limb]):
            g = cv.group(root, f"{id}-front-{limb}")
            _show(cv, g, _changes(fronts[limb], True))
            fills = [d.pose.limbs[limb].widened(o).outline() for d in frames]
            traces = [d.pose.limbs[limb].widened(o).contour() for d in frames]
            fill = cv.path(g, fills[0], cv.white, cv.clear, 0)
            cv.keys(fill, "path", list(zip(times, fills, strict=True)))
            trace = cv.path(g, traces[0], cv.clear, cv.ink, o)
            cv.keys(trace, "path", list(zip(times, traces, strict=True)))
    face = cv.group(root, f"{id}-face")
    cv.keys(face, "x", [(d.time, round(d.pose.head[0] + d.pose.face[0], 3)) for d in frames])
    cv.keys(face, "y", [(d.time, round(d.pose.head[1] + d.pose.face[1], 3)) for d in frames])
    for side in (-1, 1):
        cv.ellipse(face, side * 58 - 15, 16, 30, 17, BLUSH, opacity=0.85)
    eyes_track = [(d.time, d.face.eyes) for d in frames]
    for kind in dict.fromkeys(e for _, e in eyes_track):
        g = cv.group(face, f"{id}-eyes-{kind}")
        _show(cv, g, _changes(eyes_track, kind))
        EYES[kind](cv, g, 0, -8)
    mouths = mouth_track(frames, mouth_states or ())
    for shape in dict.fromkeys(m for _, m in mouths):
        g = cv.group(face, f"{id}-mouth-{shape}")
        _show(cv, g, _changes(mouths, shape))
        _mouth(cv, g, shape, 0, 32)
    return root


# -- props and the stage: a 3/4 view from above and to the right ---------------------------------------------
def _poly(cv: Canvas, g, pts: Sequence[Point], fill: str, line: str = WOOD_LINE, sw: float = 4) -> None:
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts) + " Z"
    cv.path(g, d, fill, line, sw)


def _leg(cv: Canvas, g, x: float, top: float, bottom: float, w: float = 34, side: float = 14) -> None:
    """A square wooden leg: the face toward the viewer and its darker side face."""
    _poly(cv, g, [(x + w, top), (x + w + side, top - 10), (x + w + side, bottom - 10), (x + w, bottom)], WOOD_SIDE)
    _poly(cv, g, [(x, top), (x + w, top), (x + w, bottom), (x, bottom)], WOOD_FRONT)


@register("prop", "soft-desk", summary="A wooden desk in a 3/4 view from above: top, front and side faces, square legs")
def desk(cv: Canvas, parent, id: str = "soft-desk"):
    g = cv.group(parent, id)
    _leg(cv, g, 296, 1010, 1268, w=30, side=12)  # back right, behind the top
    _poly(cv, g, [(600, 1190), (330, 955), (330, 1005), (600, 1240)], WOOD_SIDE)  # right edge
    _poly(cv, g, [(-60, 1295), (600, 1190), (600, 1240), (-60, 1347)], WOOD_FRONT)  # front edge
    _poly(cv, g, [(-60, 1020), (330, 955), (600, 1190), (-60, 1295)], WOOD_TOP)  # top
    for a, b in (((-60, 1115), (380, 1040)), ((-60, 1200), (470, 1115))):  # grain
        cv.path(g, f"M {a[0]:g} {a[1]:g} L {b[0]:g} {b[1]:g}", stroke=WOOD_LINE, sw=2.5, opacity=0.3)
    _leg(cv, g, 560, 1240, 1500, w=40)
    _leg(cv, g, -10, 1347, 1620, w=42)
    return g


@register("prop", "soft-chair", summary="A low wooden chair in a 3/4 view, facing left, slatted backrest on the right")
def chair(cv: Canvas, parent, id: str = "soft-chair"):
    g = cv.group(parent, id)
    _leg(cv, g, 842, 1285, 1420, w=20, side=8)  # back left
    _leg(cv, g, 927, 1345, 1488, w=24, side=10)  # back right
    _poly(cv, g, [(640, 1315), (735, 1385), (735, 1412), (640, 1342)], WOOD_SIDE)  # seat, left edge
    _poly(cv, g, [(735, 1385), (950, 1340), (950, 1367), (735, 1412)], WOOD_FRONT)  # seat, front edge
    _poly(cv, g, [(640, 1315), (860, 1275), (950, 1340), (735, 1385)], WOOD_TOP)  # seat top
    _leg(cv, g, 640, 1342, 1470, w=24, side=10)
    _leg(cv, g, 735, 1412, 1545, w=26, side=10)
    # Backrest along the seat's right edge: two posts, a top rail and two slats.
    for x0, y0 in ((852, 1280), (938, 1342)):
        _poly(cv, g, [(x0, y0), (x0, y0 - 330), (x0 + 16, y0 - 336), (x0 + 16, y0 - 6)], WOOD_FRONT)
    for k in (1 / 3, 2 / 3):
        sx, sy = 860 + 86 * k, 1280 + 62 * k
        _poly(cv, g, [(sx - 7, sy - 250), (sx + 7, sy - 248), (sx + 7, sy), (sx - 7, sy - 2)], WOOD_SIDE)
    _poly(cv, g, [(846, 946), (958, 1006), (958, 1072), (846, 1012)], WOOD_TOP)  # top rail
    return g


_DECK = ((170.0, 1070.0), (410.0, 1032.0), (296.0, 933.0), (56.0, 971.0))  # the keyboard deck, in laptop units


def keyboard() -> list[Point]:
    """The laptop's keyboard deck in output pixels, where a seated pose's hands land."""
    x, y, k = LAPTOP
    return [(x + px * k, y + py * k) for px, py in _DECK]


@register("prop", "soft-laptop", summary="An open laptop on the soft desk: keyboard deck and the back of the lid")
def laptop(cv: Canvas, parent, id: str = "soft-laptop"):
    x, y, k = LAPTOP
    g = cv.group(parent, id, x=x, y=y, scaleX=k, scaleY=k)
    _poly(cv, g, [(170, 1070), (410, 1032), (410, 1044), (170, 1083)], METAL_DARK, cv.ink, 3.5)
    _poly(cv, g, list(_DECK), METAL_LIGHT, cv.ink, 3.5)
    for i in range(1, 5):  # rows of keys across the deck
        f = i / 5.6
        a = (170 + (56 - 170) * f + 30, 1070 + (971 - 1070) * f - 8)
        b = (410 + (296 - 410) * f - 60, 1032 + (933 - 1032) * f + 2)
        cv.path(g, f"M {a[0]:.1f} {a[1]:.1f} L {b[0]:.1f} {b[1]:.1f}", stroke=METAL_DARK, sw=3)
    _poly(cv, g, [(214, 1052), (270, 1043), (262, 1034), (206, 1043)], METAL, cv.ink, 2)  # trackpad
    # The lid, hinged on the deck's left edge, leaning back: the viewer sees its back.
    _poly(cv, g, [(170, 1070), (56, 971), (30, 745), (148, 838)], METAL, cv.ink, 4)
    cv.ellipse(g, 86, 880, 30, 34, METAL_LIGHT)
    return g


@register(
    "location",
    "soft-office",
    summary="The warm office in a 3/4 view: desk with laptop on the left, chair on the right, the signature cactus",
    episodes=("focus-mode", "camera-off"),
)
def office(cv: Canvas, parent, *, shots: Sequence[tuple[float, float]] | None = None, id: str = "soft-office"):
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    chair(cv, g)
    desk(cv, g)
    signature.cactus(cv, g, 170, 1040, 0.62)
    laptop(cv, g)
    signature.code(cv, g, 40, 1327, 14, color=WOOD_LINE, angle=-9)
    return g
