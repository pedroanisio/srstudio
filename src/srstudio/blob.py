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

A :class:`Look` is what makes the rig a particular character: body fill, blush, what grows from the head
(Pip's sprout), what sits on it (Bo's hair) and what the face wears (Bo's glasses), and optional polish: a
shaded head, a gloss, catch-lights and lashes. :func:`pip`, :func:`bo`, :func:`juno` and :func:`remy` are the
same rig in four looks, so every pose and cue works for all of them.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from . import _blob_drawing_contracts as bdc
from . import _character_contracts as cc
from . import checks, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soundtrack import MOUTHS as MOUTH_STATES

__all__ = [
    "OUTLINE",
    "HEAD",
    "LIMBS",
    "ARMS",
    "EYES",
    "GAZES",
    "held",
    "worn",
    "speaking",
    "MOUTHS",
    "POSES",
    "POSES_SINCE_APPROVAL",
    "SEAT",
    "FLOOR",
    "SCALE",
    "BlobError",
    "Stroke",
    "Pose",
    "Cue",
    "Drawing",
    "Look",
    "Outfit",
    "PIP",
    "BO",
    "JUNO",
    "JUNO_HOME",
    "JUNO_V2",
    "REMY",
    "MIN_CLOTH_DISTANCE",
    "COLLAR",
    "delta_e",
    "clothed",
    "collar",
    "cut",
    "inside",
    "juno_v2",
    "FEET",
    "FRONTABLE",
    "SEATED_FLOOR",
    "LAPTOP",
    "SOFA_SEAT",
    "SOFA_FLOOR",
    "keyboard",
    "sofa_seat",
    "silhouette",
    "drawings",
    "mouth_track",
    "blob",
    "pip",
    "bo",
    "juno",
    "remy",
    "office",
    "sofa",
    "home",
    "ROOM",
    "CORNER",
    "CAPTION_FLOOR",
    "BREAK_STAND",
    "WALL_DECOR",
    "STOOL_TOP",
    "STOOL_FLOOR",
    "RoomPalette",
    "room_point",
    "wall_base",
    "wall_quad",
    "floor_quad",
    "meeting_table_top",
    "swivel_seat",
    "swivel_chair",
    "coffee_machine",
    "fridge",
    "stool",
    "meeting_room",
    "break_room",
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
SOFA_SEAT = (600.0, 1340.0)  # a sitting pose's origin (the hip) on the soft home's sofa
SOFA_FLOOR = SOFA_SEAT[1] + SEATED_FLOOR - SEAT[1]  # the sofa's seat stands as high over the floor as the chair's
FABRIC_LINE = "#2E4A41"
FABRIC_TOP = "#8FB3A5"
FABRIC_FRONT = "#769C8E"
FABRIC_SIDE = "#5F8577"
RUG = "#E9C9A8"
RUG_LINE = "#C99D74"


class BlobError(SrstudioError, ValueError):
    """A stroke, pose, cue or mouth track the blob cannot draw."""


def _finite(*values: float) -> bool:
    return all(checks.number(v) for v in values)


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
    forearms forward onto the keyboard. The near leg is outlined over the far one, its shin a sole's width ahead
    of the far shin so the two legs read apart."""
    return _pose(
        "sit",
        head,
        front=("arm_l", "leg_l"),  # 3/4 view: the near arm and leg in front, the far arm behind the body
        face=face,
        torso=seg((5, -92), (-22, -212), 190, 150),
        leg_l=Stroke((-10, -40), (-82, -50), (-122, -24), (-114, 62), *LEG),
        leg_r=Stroke((22, -32), (-28, -40), (-50, -16), (-42, 60), *LEG),
        arm_l=_forearm((-62, -205), hand_l),
        arm_r=_forearm((-42, -198), hand_r),
    )


def _lounging() -> Pose:
    """Seated back against a sofa: the sit pose with the head tipped back and both hands resting on the near thigh."""
    sit = _sitting((-170, -112), (-150, -108), head=(-30, -322), face=(-20, 2))
    arms = {
        "arm_l": Stroke((-62, -205), (-72, -160), (-72, -112), (-84, -70), *ARM),
        "arm_r": Stroke((-42, -198), (-52, -152), (-50, -110), (-60, -74), *ARM),
    }
    return Pose("lounge", sit.head, {**sit.limbs, **arms}, sit.front, sit.face)


def _on_the_floor() -> Pose:
    """Sat on the floor facing left, with nothing under her: the sit pose with the hip on the ground and both legs out
    along it, the far knee a little up."""
    sit = _sitting((-170, -112), (-150, -108))
    legs = {
        "leg_l": Stroke((-10, -40), (-76, -48), (-140, -36), (-196, -14), *LEG),
        "leg_r": Stroke((22, -32), (-40, -84), (-96, -78), (-136, -36), *LEG),
    }
    return Pose("floor", sit.head, {**sit.limbs, **legs}, sit.front, sit.face)


def _phone_up(name: str, hand_l: Point, hand_r: Point, head: Point = (-40, -322)) -> Pose:
    """The sit pose with a phone up at the chest, its screen to the camera: each elbow drops and comes back up, so the
    arm keeps its length with the hands that near the body."""
    sit = _sitting((-170, -112), (-150, -108), head=head)
    arms = {
        "arm_l": Stroke((-62, -205), (-32, -116), (hand_l[0] + 8, hand_l[1] + 70), hand_l, *ARM),
        "arm_r": Stroke((-42, -198), (-12, -112), (hand_r[0] + 8, hand_r[1] + 66), hand_r, *ARM),
    }
    return Pose(name, sit.head, {**sit.limbs, **arms}, sit.front, sit.face)


def _named(pose: Pose, name: str) -> Pose:
    return Pose(name, pose.head, pose.limbs, pose.front, pose.face)


def _showing() -> Pose:
    """Seated, both hands up in front of the chest with something small between them, held out to be looked at."""
    sit = _sitting((-170, -112), (-150, -108))
    arms = {
        "arm_l": Stroke((-62, -205), (-92, -180), (-140, -200), (-160, -262), *ARM),
        "arm_r": Stroke((-42, -198), (-72, -172), (-112, -192), (-132, -252), *ARM),
    }
    return Pose("sit-show", sit.head, {**sit.limbs, **arms}, sit.front, sit.face)


def _glancing() -> Pose:
    """Seated with the head turned back over the far shoulder, away from what the sit pose is facing."""
    sit = _sitting((-170, -112), (-150, -108), head=(-8, -326), face=(30, 2))
    return _named(sit, "sit-back")


def _hugging() -> Pose:
    """Standing, leaning in to the right with both arms across someone there; flip for the other one."""
    return _pose(
        "hug",
        (30, -428),
        front=ARMS,
        face=(10, 2),
        torso=seg((6, -326), (0, -215), *TORSO),
        **_standing_legs(),
        arm_l=Stroke((-58, -306), (-30, -270), (30, -270), (84, -292), *ARM),
        arm_r=Stroke((58, -308), (100, -296), (150, -300), (190, -332), *ARM),
    )


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
        _lounging(),
        _on_the_floor(),
        _phone_up("phone-a", (-112, -176), (-82, -168)),
        _phone_up("phone-b", (-106, -172), (-88, -176), head=(-36, -326)),  # a thumb working on it
        _showing(),
        _glancing(),
        _hugging(),
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
# Poses added after the cast was approved. An approved drawing walks only the others, so a new pose moves no digest.
POSES_SINCE_APPROVAL = frozenset({"floor", "phone-a", "phone-b", "sit-show", "sit-back", "hug"})


# -- faces ------------------------------------------------------------------------------------------------
def _stroke(cv: Canvas, g, d: str, sw: float = 6) -> None:
    cv.path(g, d, stroke=cv.ink, sw=sw)


def _eye(
    cv: Canvas, g, x: float, y: float, w: float, h: float, pupil: float, dx: float = 0.0, shine: bool = False
) -> None:
    cv.ellipse(g, x - w / 2, y - h / 2, w, h, cv.white, cv.ink, 4.5)
    cv.ellipse(g, x - pupil / 2 + dx, y - pupil * 0.55 + h * 0.12, pupil, pupil * 1.1, cv.ink)
    if shine:  # a catch-light up and left on the pupil, from the same light as the head's gloss, and a fleck below
        px, py = x + dx, y + h * 0.12
        big, small = pupil * 0.46, pupil * 0.2
        cv.ellipse(g, px - pupil * 0.3 - big / 2, py - pupil * 0.28 - big / 2, big, big, cv.white)
        cv.ellipse(g, px + pupil * 0.22 - small / 2, py + pupil * 0.24 - small / 2, small, small, cv.white)


def _lash(cv: Canvas, g, x: float, y: float, side: int, rise: float) -> None:
    """Two flicks from the outer corner at ``x, y``, swept outward and up by ``rise``."""
    for k, (dx, dy) in enumerate(((11, -rise), (14, -rise * 0.35))):
        x0, y0 = x - side * 3 * k, y + 5 * k
        cv.path(
            g, f"M {x0:g} {y0:g} Q {x0 + side * dx * 0.5:g} {y0:g} {x0 + side * dx:g} {y0 + dy:g}", stroke=cv.ink, sw=4
        )


def _eyes(
    cv: Canvas, g, kind: str, x: float, y: float, shine: bool = False, lashes: bool = False, gaze: str = "left"
) -> None:
    dx = (-LOOK_REACH if gaze == "left" else LOOK_REACH) if kind == "look" else 0.0
    for side in (-1, 1):
        ex = x + side * 30
        if kind in ("open", "look", "wide"):
            w, h, cy = (48, 56, y - 3) if kind == "wide" else (40, 46, y)
            _eye(cv, g, ex, cy, w, h, 13 if kind == "wide" else 17, dx=dx, shine=shine)
            if lashes:  # where the lid's outer curve turns down
                _lash(cv, g, ex + side * w * 0.36, cy - h * 0.34, side, 10)
        elif kind == "happy":
            _stroke(cv, g, f"M {ex - 15:g} {y + 6:g} Q {ex:g} {y - 14:g} {ex + 15:g} {y + 6:g}")
            if lashes:
                _lash(cv, g, ex + side * 13, y + 2, side, 8)
        elif kind == "squint":
            tip, back = ex - 11 * side, ex + 13 * side  # pointing inward: ">" on the left, "<" on the right
            _stroke(cv, g, f"M {back:g} {y - 12:g} L {tip:g} {y:g} L {back:g} {y + 12:g}")
            if lashes:
                _lash(cv, g, back, y - 11, side, 8)
        else:  # closed
            _stroke(cv, g, f"M {ex - 15:g} {y - 2:g} Q {ex:g} {y + 11:g} {ex + 15:g} {y - 2:g}")
            if lashes:
                _lash(cv, g, ex + side * 14, y, side, 6)


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


LOOK_REACH = 8  # how far the "look" pupils sit from the middle of the eye, toward the gaze
# Which way the "look" eyes point on the screen. "left" is what the rig always drew, so a cue that names no gaze draws
# as before; "right" lets a figure look at someone on its right, flipped or not (ADR 0235).
GAZES: tuple[str, ...] = ("left", "right")
EYES: dict[str, Callable[..., None]] = {
    k: (lambda cv, g, x, y, k=k, **polish: _eyes(cv, g, k, x, y, **polish))
    for k in ("open", "look", "wide", "happy", "squint", "closed")
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


Drawer = Callable[[Canvas, object, float], None]  # (canvas, a group centred on the head, head radius)
_COLOUR = re.compile(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?")
_NAME = re.compile(r"[a-z][a-z0-9-]*")


# -- clothes (ADR 0240) -------------------------------------------------------------------------------------------
MIN_CLOTH_DISTANCE = 40.0  # CIE76 ΔE*ab a garment keeps from the skin it covers: it reads as cloth, never as skin
COLLAR = 14.0  # how far the collar stands out from the head's rim, in pose units
COLLAR_SPAN = 62.0  # degrees either side of the line from the head to the body the collar may run
COLLAR_MARGIN = 6.0  # pose units the collar keeps inside the body's edge, so it never changes the silhouette
COLLAR_STEPS = 16  # points along each arc of the collar, the same on every drawing


def _lab(colour: str) -> tuple[float, float, float]:
    """``#RRGGBB`` in CIE L*a*b* (sRGB, D65)."""

    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(int(colour[i : i + 2], 16) / 255) for i in (1, 3, 5))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    """How far apart two ``#RRGGBB`` colours look: CIE76 ΔE*ab, the straight distance in L*a*b*. About 2.3 is the
    least an eye notices; :data:`MIN_CLOTH_DISTANCE` is far past "a slightly different peach"."""
    for colour in (a, b):
        if not (isinstance(colour, str) and _COLOUR.fullmatch(colour)):
            raise BlobError(f"a colour distance takes #RRGGBB colours, got {colour!r}")
    return math.dist(_lab(a), _lab(b))


@dataclass(frozen=True)
class Outfit:
    """Clothes the rig draws on the body as part of a :class:`Look`, so they follow every pose and in-between.

    ``top`` dresses the torso and sleeves the arms, ``trousers`` dress the legs. A sleeve stops ``hand`` pose units
    (measured along the arm) short of its tip and a trouser leg ``foot`` short of its, so every hand and foot is the
    same size in every pose and in-between, and stays the look's skin. Each sleeve and trouser leg ends in a cuff
    ``cuff`` long in ``trim``, with an ink line where it meets the skin, and a ``trim`` collar sits under the chin."""

    top: str
    trousers: str
    trim: str
    hand: float = 26.0
    foot: float = 22.0
    cuff: float = 12.0

    def __post_init__(self) -> None:
        for label in ("top", "trousers", "trim"):
            colour = getattr(self, label)
            if not (isinstance(colour, str) and _COLOUR.fullmatch(colour)):
                raise BlobError(f"an outfit's {label} must be a #RRGGBB colour, got {colour!r}")
        for label in ("hand", "foot"):
            bare = getattr(self, label)
            if not (checks.number(bare) and 0 < bare <= 80):
                raise BlobError(f"an outfit leaves a {label} of 0 < {label} <= 80 pose units bare, got {bare!r}")
        if not (checks.number(self.cuff) and 0 < self.cuff <= 20):
            raise BlobError(f"an outfit's cuff is a short band, 0 < cuff <= 20 pose units, got {self.cuff!r}")

    def reach(self, limb: str, s: Stroke) -> float:
        """How far along ``limb``, drawn as ``s``, the cloth runs (0..1): all of the torso, an arm to :attr:`hand` from
        its tip, a leg to :attr:`foot` from its tip; an in-between that folds a limb shorter than two of those
        keeps half of its length clothed and half bare."""
        if limb not in LIMBS:
            raise BlobError(f"unknown limb {limb!r}; one of {LIMBS}")
        if limb == "torso":
            return 1.0
        return _from_tip(s, min(self.hand if limb in ARMS else self.foot, _length(s) / 2))


_ARC = 96  # chords along a stroke when measuring its length


def _length(s: Stroke) -> float:
    """How long ``s``'s centreline is, measured along it."""
    pts = [s.point(k / _ARC) for k in range(_ARC + 1)]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False))


def _from_tip(s: Stroke, length: float) -> float:
    """Where along ``s`` (0..1) the curve is ``length`` short of its tip, measured along it; 0 if it is shorter."""
    pts = [s.point(k / _ARC) for k in range(_ARC + 1)]
    left = length
    for k in range(_ARC, 0, -1):
        step = math.dist(pts[k], pts[k - 1])
        if step >= left:
            return (k - left / step) / _ARC if step else k / _ARC
        left -= step
    return 0.0


def _span(s: Stroke, a: float, b: float) -> Stroke:
    """The part of ``s`` from ``a`` to ``b`` along it (0 <= a < b <= 1), as a stroke of its own: the cubic's blossom
    gives its control points, and the widths run on as they did."""

    def blossom(t1: float, t2: float, t3: float) -> Point:
        pts = [s.p0, s.p1, s.p2, s.p3]
        for t in (t1, t2, t3):
            pts = [_lerp_pt(p, q, t) for p, q in zip(pts, pts[1:], strict=False)]
        return pts[0]

    if a == 0 and b == 1:
        return s
    return Stroke(
        blossom(a, a, a),
        blossom(a, a, b),
        blossom(a, b, b),
        blossom(b, b, b),
        _lerp(s.w0, s.w1, a),
        _lerp(s.w0, s.w1, b),
    )


def clothed(s: Stroke, outfit: Outfit, limb: str) -> Stroke:
    """The part of ``limb`` (drawn as ``s``) that ``outfit`` covers, from the body out to its cuff."""
    return _span(s, 0.0, outfit.reach(limb, s))


def _cuff(s: Stroke, outfit: Outfit, limb: str) -> Stroke:
    """The cuff at the end of ``limb``'s cloth: the last :attr:`Outfit.cuff` of it, measured along the limb."""
    end = outfit.reach(limb, s)
    start = max(0.0, _from_tip(_span(s, 0.0, end), outfit.cuff) * end)
    return _span(s, start, end)


def cut(s: Stroke, *, start: bool = True, samples: int = 14, cap: int = 8) -> str:
    """The closed outline of ``s`` cut square at its end, as cloth is where it stops on a limb (and at its start too
    unless ``start``, which keeps the round cap that sits inside the body)."""
    left, right = [], []
    for i in range(samples + 1):
        t = i / samples
        (cx, cy), (tx, ty) = s.point(t), s.tangent(t)
        h = _lerp(s.w0, s.w1, t) / 2
        left.append((cx - ty * h, cy + tx * h))
        right.append((cx + ty * h, cy - tx * h))
    ring = left + list(reversed(right))
    if start:
        ring += s._rim(samples, cap)[1]
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in ring) + " Z"


def _across(s: Stroke, t: float, wider: float) -> str:
    """A line across ``s`` at ``t`` along it, edge to edge of the stroke drawn ``wider``: where a cuff meets."""
    (x, y), (tx, ty) = s.point(t), s.tangent(t)
    half = (_lerp(s.w0, s.w1, t) + wider) / 2
    return f"M {x - ty * half:.1f} {y + tx * half:.1f} L {x + ty * half:.1f} {y - tx * half:.1f}"


def inside(s: Stroke, p: Point, margin: float = 0.0, samples: int = 64) -> bool:
    """Is ``p`` at least ``margin`` inside the round-capped stroke ``s``?"""
    for i in range(samples + 1):
        t = i / samples
        if math.dist(p, s.point(t)) + margin <= _lerp(s.w0, s.w1, t) / 2:
            return True
    return False


def collar(pose: Pose) -> list[Point]:
    """The collar of ``pose``: a band :data:`COLLAR` wide round the bottom of the head, centred on the line from the
    head to the body and running as far either way as it stays :data:`COLLAR_MARGIN` inside the torso (at most
    :data:`COLLAR_SPAN` degrees), so the silhouette never changes. Its outer arc, then its inner arc back just inside
    the head's rim, which the head's fill covers; :data:`COLLAR_STEPS` points each, on every drawing."""
    torso = pose.limbs["torso"]
    (hx, hy), r = pose.head, HEAD
    top = torso.p0 if math.dist(torso.p0, pose.head) <= math.dist(torso.p3, pose.head) else torso.p3
    centre = math.degrees(math.atan2(top[1] - hy, top[0] - hx))

    def at(angle: float, radius: float) -> Point:
        a = math.radians(angle)
        return (hx + radius * math.cos(a), hy + radius * math.sin(a))

    def fits(angle: float) -> bool:
        return inside(torso, at(angle, r + COLLAR), COLLAR_MARGIN) and inside(torso, at(angle, r - 2), 0.5)

    lo = hi = centre
    if fits(centre):
        while lo - 1 >= centre - COLLAR_SPAN and fits(lo - 1):
            lo -= 1
        while hi + 1 <= centre + COLLAR_SPAN and fits(hi + 1):
            hi += 1
    angles = [lo + (hi - lo) * k / (COLLAR_STEPS - 1) for k in range(COLLAR_STEPS)]
    return [at(a, r + COLLAR) for a in angles] + [at(a, r - 2) for a in reversed(angles)]


@dataclass(frozen=True)
class Look:
    """What makes the blob rig a particular character.

    ``fill`` colours the body and head (``None``: the palette's white); ``blush`` the cheeks (``None``: none).
    ``topper`` draws what grows from the head, between the outline and fill passes so the fill hides its base;
    ``hair`` draws on top of the head after the fill; ``features`` draws on the face after the mouth. Each
    drawer gets a group that follows the head (``features``: the face) and the head radius; its group is
    ``<id>-<topper_id>``, ``<id>-hair`` and ``<id>-<features_id>``.

    The polish is off by default, so a look without it draws exactly as before: ``shade`` colours a crescent
    on the head away from the light (upper left), ``gloss`` puts a highlight on the lit side, ``catchlights``
    puts the same light in the pupils and ``lashes`` adds two flicks at the outer corner of every eye.

    ``outfit`` (ADR 0240) dresses the body and limbs (:class:`Outfit`); a look without one draws exactly as before.
    Its top and trousers keep :data:`MIN_CLOTH_DISTANCE` from the fill, so a dressed look never reads as skin."""

    name: str
    fill: str | None = None
    blush: str | None = BLUSH
    topper: Drawer | None = None
    topper_id: str = "topper"
    hair: Drawer | None = None
    features: Drawer | None = None
    features_id: str = "features"
    shade: str | None = None
    gloss: bool = False
    catchlights: bool = False
    lashes: bool = False
    outfit: Outfit | None = None

    def __post_init__(self) -> None:
        if not _NAME.fullmatch(self.name):
            raise BlobError(f"a look's name is a lower-case id, got {self.name!r}")
        for label, colour in (("fill", self.fill), ("blush", self.blush), ("shade", self.shade)):
            if colour is not None and not _COLOUR.fullmatch(colour):
                raise BlobError(f"look {self.name!r}: {label} must be a #RRGGBB colour, got {colour!r}")
        if self.outfit is not None:
            if not isinstance(self.outfit, Outfit):
                raise BlobError(f"look {self.name!r}: an outfit is an Outfit, got {self.outfit!r}")
            skin = (self.fill or "#FFFFFF")[:7]
            for label in ("top", "trousers"):
                colour = getattr(self.outfit, label)
                gap = delta_e(colour, skin)
                if gap < MIN_CLOTH_DISTANCE:
                    raise BlobError(
                        f"look {self.name!r}: the outfit's {label} {colour} is too close to its fill {skin} "
                        f"(ΔE {gap:.1f} < {MIN_CLOTH_DISTANCE:g}); it would read as skin"
                    )


def _sprout_look(cv: Canvas, g, r: float) -> None:
    _sprout(cv, g, 0, 0, r)


BO_FILL = "#DCE8F4"
BO_HAIR = "#3B3F4A"


def _side_part(cv: Canvas, g, r: float) -> None:
    """Bo's hair: a cap over the crown, parted on his right, the fringe swept to his left."""
    # the rim stops above the ear on the parted side, so the hairline climbs from it instead of dropping down the cheek
    rim = [(r * math.cos(math.radians(a)), -r * math.sin(math.radians(a))) for a in range(196, 7, -8)]
    fringe = [
        (0.80 * r, -0.36 * r),
        (0.42 * r, -0.50 * r),
        (0.30 * r, -0.62 * r),  # the parting
        (0.10 * r, -0.50 * r),
        (-0.45 * r, -0.42 * r),
        (-0.86 * r, -0.12 * r),
    ]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in [*rim, *fringe]) + " Z"
    cv.path(g, d, BO_HAIR, cv.ink, 4)


def _glasses(cv: Canvas, g, r: float) -> None:
    """Square-rimmed glasses over the eyes (which sit 30 either side of the face centre, 8 above it)."""
    for side in (-1, 1):
        cv.rect(g, side * 30 - 26, -34, 52, 50, cv.clear, cv.ink, 5, radius=12)
    cv.path(g, "M -4 -14 Q 0 -19 4 -14", stroke=cv.ink, sw=5)
    for side in (-1, 1):
        cv.path(g, f"M {side * 56:g} -16 L {side * 0.9 * r:g} -20", stroke=cv.ink, sw=5)


PIP = Look("pip", topper=_sprout_look, topper_id="sprout")
BO = Look("bo", fill=BO_FILL, blush=None, hair=_side_part, features=_glasses, features_id="glasses")


# -- polish: light from the upper left ----------------------------------------------------------------------
LIGHT = (-0.16, -0.2)  # where the lit disc sits, as a fraction of the head radius; the shade is what it misses
GLOSS = "#FFFFFF"


def _arc(cx: float, cy: float, r: float, a0: float, a1: float, steps: int) -> list[Point]:
    return [
        (cx + r * math.cos(a0 + (a1 - a0) * i / steps), cy + r * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]


def _crescent(r: float, dx: float, dy: float, steps: int = 24) -> str:
    """The part of a disc of radius ``r`` at the origin that the same disc moved by ``dx, dy`` leaves uncovered:
    an outer arc on the side away from the move, closed by an arc of the moved disc."""
    gap = math.hypot(dx, dy)
    if not (checks.number(gap) and 0 < gap < 2 * r):
        raise BlobError(f"a crescent needs the lit disc moved by more than 0 and less than {2 * r:g}, got {gap!r}")
    toward, half = math.atan2(dy, dx), math.acos(gap / (2 * r))
    outer = _arc(0, 0, r, toward + half, toward + 2 * math.pi - half, steps)
    # the moved circle from where the outer arc ends back to where it starts, through its side inside the head
    (ex, ey), (sx, sy) = outer[-1], outer[0]
    a_end, a_start = math.atan2(ey - dy, ex - dx), math.atan2(sy - dy, sx - dx)
    if a_start > a_end:
        a_start -= 2 * math.pi
    inner = _arc(dx, dy, r, a_end, a_start, steps)[1:-1]
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in [*outer, *inner]) + " Z"


def _polish(cv: Canvas, g, r: float, look: Look) -> None:
    """The head's shade and gloss, drawn over its fill in a group that follows the head."""
    if look.shade is not None:
        cv.path(g, _crescent(r, LIGHT[0] * r, LIGHT[1] * r), look.shade, cv.clear, 0)
    if look.gloss:  # a highlight following the head's curve on the lit side, and a dot after it
        band = _arc(0, 0, 0.74 * r, math.radians(196), math.radians(236), 8)
        cv.path(g, "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in band), stroke=GLOSS, sw=0.11 * r, opacity=0.85)
        (dot_x, dot_y), size = _arc(0, 0, 0.74 * r, math.radians(252), math.radians(252), 1)[0], 0.1 * r
        cv.ellipse(g, dot_x - size / 2, dot_y - size / 2, size, size, GLOSS, opacity=0.85)


def _points(points: Sequence[Point]) -> str:
    return " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)


JUNO_FILL = "#FAD5BE"
JUNO_SHADE = "#EFBA9D"
JUNO_HAIR = "#6E3A2C"
JUNO_STRAND = "#4F271D"
JUNO_SHEEN = "#A0604C"
JUNO_TIE = "#E8695A"
JUNO_FRECKLE = "#C7876A"
BUN = (0.04, -1.2, 0.36)  # the bun's centre and radius, in head radii: a third of it hidden by the head


def _bun(cv: Canvas, g, r: float) -> None:
    """Juno's bun, planted on the crown (the head's fill hides its base), wound in two strands with a sheen."""
    bx, by, br = (v * r for v in BUN)
    cv.ellipse(g, bx - br, by - br, 2 * br, 2 * br, JUNO_HAIR, cv.ink, 4)
    for d in (
        f"M {bx - 0.7 * br:.1f} {by + 0.1 * br:.1f} Q {bx - 0.2 * br:.1f} {by - 0.75 * br:.1f} "
        f"{bx + 0.65 * br:.1f} {by - 0.35 * br:.1f}",
        f"M {bx - 0.35 * br:.1f} {by + 0.55 * br:.1f} Q {bx + 0.45 * br:.1f} {by + 0.35 * br:.1f} "
        f"{bx + 0.7 * br:.1f} {by - 0.15 * br:.1f}",
    ):
        cv.path(g, d, stroke=JUNO_STRAND, sw=3.5)
    sheen = _arc(bx, by, 0.72 * br, math.radians(200), math.radians(245), 6)
    cv.path(g, "M " + _points(sheen), stroke=JUNO_SHEEN, sw=5)


def _bangs(cv: Canvas, g, r: float) -> None:
    """Juno's hair: a cap from ear to ear with three scalloped bangs, a parting sheen and the scrunchie that
    ties the bun on, drawn over the cap."""
    rim = _arc(0, 0, r, math.radians(170), math.radians(370), 40)  # y down: 170° is the left cheek, 370° the right
    lx, ly = rim[0]
    hairline = (
        f"Q {0.9 * r:.1f} {-0.2 * r:.1f} {0.72 * r:.1f} {-0.38 * r:.1f} "
        f"Q {0.5 * r:.1f} {-0.26 * r:.1f} {0.26 * r:.1f} {-0.46 * r:.1f} "
        f"Q {0.0:.1f} {-0.3 * r:.1f} {-0.26 * r:.1f} {-0.48 * r:.1f} "
        f"Q {-0.52 * r:.1f} {-0.28 * r:.1f} {-0.74 * r:.1f} {-0.38 * r:.1f} "
        f"Q {-0.92 * r:.1f} {-0.2 * r:.1f} {lx:.1f} {ly:.1f}"
    )
    cv.path(g, f"M {_points(rim)} {hairline} Z", JUNO_HAIR, cv.ink, 4)
    for d in (
        f"M {0.02 * r:.1f} {-0.96 * r:.1f} Q {-0.28 * r:.1f} {-0.72 * r:.1f} {-0.5 * r:.1f} {-0.5 * r:.1f}",
        f"M {0.02 * r:.1f} {-0.96 * r:.1f} Q {0.3 * r:.1f} {-0.74 * r:.1f} {0.46 * r:.1f} {-0.52 * r:.1f}",
    ):
        cv.path(g, d, stroke=JUNO_STRAND, sw=3.5)
    sheen = _arc(0, 0, 0.8 * r, math.radians(205), math.radians(240), 6)
    cv.path(g, "M " + _points(sheen), stroke=JUNO_SHEEN, sw=7, opacity=0.9)
    bx, by, br = (v * r for v in BUN)
    tie = -0.98 * r  # round the bun where it meets the crown
    half = math.sqrt(br * br - (by - tie) ** 2) + 0.05 * r
    cv.rect(g, bx - half, tie - 0.08 * r, 2 * half, 0.16 * r, JUNO_TIE, cv.ink, 4, radius=0.08 * r)
    for k in (-1, 0, 1):
        x = bx + k * 0.45 * half
        cv.path(g, f"M {x:.1f} {tie - 0.04 * r:.1f} L {x:.1f} {tie + 0.04 * r:.1f}", stroke=cv.ink, sw=2.5)


def _freckles(cv: Canvas, g, r: float) -> None:
    """Three freckles over each cheek, over the blush."""
    for side in (-1, 1):
        for fx, fy, size in ((50, 18, 5.5), (61, 26, 5), (68, 16, 4.5)):
            cv.ellipse(g, side * fx - size / 2, fy - size / 2, size, size, JUNO_FRECKLE)


REMY_FILL = "#DDD5F4"
REMY_SHADE = "#C4B7E9"
REMY_HAIR = "#4A4372"
REMY_SHEEN = "#7C74A8"
REMY_GEAR = "#3D4250"
REMY_CUSHION = "#272A33"
REMY_TRIM = "#6D7488"
REMY_LED = "#F2A93B"
REMY_BLUSH = "#EFB3C4"


def _tuft(cv: Canvas, g, r: float) -> None:
    """Remy's tuft: three locks sprung from the crown (the head's fill hides their roots), swept up and curling
    over at the tip by ``curl``, the middle one tallest, each with a sheen along its lit edge."""
    root_y = -0.82
    locks = ((-0.5, -0.12, -0.36, -1.5, 0.22), (-0.2, 0.2, 0.12, -1.68, 0.26), (0.12, 0.48, 0.58, -1.46, 0.2))
    for left, right, tip_x, tip_y, curl in locks:
        d = (
            f"M {left * r:.1f} {root_y * r:.1f} "
            f"C {(left - 0.06) * r:.1f} {(tip_y + 0.3) * r:.1f} {(tip_x - curl) * r:.1f} {tip_y * r:.1f} "
            f"{tip_x * r:.1f} {tip_y * r:.1f} "
            f"C {(tip_x - 0.02) * r:.1f} {(tip_y + 0.22) * r:.1f} {(right + 0.04) * r:.1f} {(root_y - 0.3) * r:.1f} "
            f"{right * r:.1f} {root_y * r:.1f} Z"
        )
        cv.path(g, d, REMY_HAIR, cv.ink, 4)
        sheen = (
            f"M {(left + 0.1) * r:.1f} {(root_y - 0.12) * r:.1f} Q {(left + 0.04) * r:.1f} {(tip_y + 0.36) * r:.1f} "
            f"{(tip_x - 0.06) * r:.1f} {(tip_y + 0.12) * r:.1f}"
        )
        cv.path(g, sheen, stroke=REMY_SHEEN, sw=4)


def _headset(cv: Canvas, g, r: float) -> None:
    """Remy's headset: a padded band over the crown, an ear cup each side with a status light, and a mic boom
    from the left cup to beside the mouth."""
    outer = _arc(0, 0, 1.12 * r, math.radians(194), math.radians(346), 24)
    inner = _arc(0, 0, 1.0 * r, math.radians(346), math.radians(194), 24)
    cv.path(g, f"M {_points([*outer, *inner])} Z", REMY_GEAR, cv.ink, 4)
    trim = _arc(0, 0, 1.06 * r, math.radians(214), math.radians(326), 16)
    cv.path(g, "M " + _points(trim), stroke=REMY_TRIM, sw=3)
    boom = f"M {-0.98 * r:.1f} {0.12 * r:.1f} Q {-0.9 * r:.1f} {0.46 * r:.1f} {-0.44 * r:.1f} {0.44 * r:.1f}"
    cv.path(g, boom, stroke=cv.ink, sw=11)
    cv.path(g, boom, stroke=REMY_GEAR, sw=5)
    cv.rect(g, -0.5 * r, 0.36 * r, 0.2 * r, 0.16 * r, REMY_CUSHION, cv.ink, 4, radius=0.08 * r)
    for side in (-1, 1):
        x = side * 1.02 * r
        cv.rect(g, x - 0.17 * r, -0.3 * r, 0.34 * r, 0.56 * r, REMY_GEAR, cv.ink, 4, radius=0.15 * r)
        cv.rect(
            g, x - 0.17 * r + (0.2 * r if side < 0 else 0), -0.22 * r, 0.14 * r, 0.4 * r, REMY_CUSHION, radius=0.07 * r
        )
        cv.ellipse(g, x - 0.04 * r, -0.2 * r, 0.08 * r, 0.08 * r, REMY_LED)


JUNO = Look(
    "juno",
    fill=JUNO_FILL,
    topper=_bun,
    topper_id="bun",
    hair=_bangs,
    features=_freckles,
    features_id="freckles",
    shade=JUNO_SHADE,
    catchlights=True,
    lashes=True,
)
# Juno's home outfit (ADR 0240): a teal top and mustard trousers, the kitchen's own two accents, with a cream collar
# and cuffs. Version 2 of Juno is version 1 dressed in it; her head, hair and face are version 1's.
JUNO_TOP = "#3F8F8A"
JUNO_TROUSERS = "#D29B2A"
JUNO_TRIM = "#F6EAD3"
JUNO_HOME = Outfit(top=JUNO_TOP, trousers=JUNO_TROUSERS, trim=JUNO_TRIM)
JUNO_V2 = replace(JUNO, outfit=JUNO_HOME)
REMY = Look(
    "remy",
    fill=REMY_FILL,
    blush=REMY_BLUSH,
    topper=_tuft,
    topper_id="tuft",
    hair=_headset,
    shade=REMY_SHADE,
    gloss=True,
    catchlights=True,
)


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
    fraction past the pose and settles back one drawing later. The expression changes when the pose lands.
    ``gaze`` is the screen side the ``"look"`` eyes point to, one of :data:`GAZES`; ``flip`` does not turn it."""

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
    published_full_gap_ease: bool = False  # set by settle(); see there
    gaze: str = "left"


def cue(
    time: float, pose: str, spot: tuple[float, float] | None = None, *, scale: float = 1.0, ease: float = 0.0, **kw
) -> Cue:
    """A :class:`Cue` at ``spot`` in output pixels, for a character drawn at ``scale`` (the rig's units are
    pixels / scale); without a spot the character stays where it is. A cue at 0 has nothing to ease from."""
    if not (checks.number(scale) and scale > 0):
        raise BlobError(f"scale {scale} must be a positive number to map pixels to rig units")
    x, y = (0.0, 0.0) if spot is None else (spot[0] / scale, spot[1] / scale)
    return Cue(time, pose, x=x, y=y, ease=ease if time else 0.0, **kw)


def settle(cues: Sequence[Cue], fps: float, *, published_full_gap_ease: bool = False) -> list[Cue]:
    """``cues`` in time order, each ease capped so the move starts only after the previous pose has landed (and,
    after an overshoot, settled one drawing at ``fps`` later).

    ``published_full_gap_ease`` reproduces a defect kept only for frozen published episodes (L8); never use in new
    work. It makes :func:`drawings` draw an ease that fills the whole gap as those episodes shipped: its first
    in-between at the time of the drawing before it, which hides that drawing."""
    if not (checks.number(fps) and fps > 0):
        raise BlobError(f"fps {fps} must be a positive number")
    ordered = sorted(cues, key=lambda c: c.time)
    for a, b in zip(ordered, ordered[1:], strict=False):
        if b.time <= a.time:
            raise BlobError(f"cue times must be increasing: {a.time} then {b.time}")
    landed = [0.0, *(c.time + (1 / fps + 1e-3 if c.overshoot else 0.0) for c in ordered)]
    return [
        replace(c, ease=max(0.0, min(c.ease, c.time - s)), published_full_gap_ease=published_full_gap_ease)
        for s, c in zip(landed, ordered, strict=False)
    ]


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
        if cue.gaze not in GAZES:
            raise BlobError(f"unknown gaze {cue.gaze!r}; one of {GAZES}")
        if cue.gaze != "left" and cue.eyes != "look":
            raise BlobError(f"the cue at {cue.time} sets gaze {cue.gaze!r}, which only the \"look\" eyes have")
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
    checks.positive(end, BlobError, f"a performance's end must be a positive number of seconds, got {end!r}")
    checks.positive(fps, BlobError, f"a performance's fps must be a positive number, got {fps!r}")
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
                u, t = _smooth((j + 1) / (n + 1)), cue.time - cue.ease + j * cue.ease / n
                if t <= out[-1].time + 1e-9 and not cue.published_full_gap_ease:
                    continue  # an ease filling the whole gap: the pose it leaves keeps its drawing
                out.append(Drawing(t, cue, at(u), u, before[5]))
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


def held(cv: Canvas, parent, cues: Sequence[Cue], *, end: float, scale: float = 1, fps: float = 15, id: str):
    """A group that rides between the hands through ``cues``, drawing by drawing, for a prop the character holds.

    It uses the same cues, ``end``, ``scale`` and ``fps`` as the character it rides with, and is placed in the same
    parent, so a phone stays in the hands through every in-between."""
    checks.positive(scale, BlobError, f"a held prop's scale must be a positive number, got {scale!r}")
    frames = drawings(cues, end=end, fps=fps)
    g = cv.group(parent, id)
    tips = [(d.pose.limbs["arm_l"].p3, d.pose.limbs["arm_r"].p3) for d in frames]
    cv.keys(g, "x", [(d.time, round(scale * (a[0] + b[0]) / 2, 3)) for d, (a, b) in zip(frames, tips, strict=True)])
    cv.keys(g, "y", [(d.time, round(scale * (a[1] + b[1]) / 2, 3)) for d, (a, b) in zip(frames, tips, strict=True)])
    return g


def worn(cv: Canvas, parent, cues: Sequence[Cue], *, end: float, scale: float = 1, fps: float = 15, id: str):
    """A group on the head through ``cues``, drawing by drawing, for what a character wears: a scarf, a blanket.

    Like :func:`held`, it uses the same cues, ``end``, ``scale`` and ``fps`` as the character it rides with and is
    placed in the same parent. What it holds is drawn with its origin on the head's centre."""
    checks.positive(scale, BlobError, f"what a blob wears needs a positive scale, got {scale!r}")
    frames = drawings(cues, end=end, fps=fps)
    g = cv.group(parent, id)
    cv.keys(g, "x", [(d.time, round(scale * d.pose.head[0], 3)) for d in frames])
    cv.keys(g, "y", [(d.time, round(scale * d.pose.head[1], 3)) for d in frames])
    return g


def speaking(cues: Sequence[Cue], spans: Sequence[tuple[float, float]], end: float, fps: float = 15) -> list[Cue]:
    """``cues`` in time order, the later of two at one time winning, with the ``sing`` mouth on every hold that
    overlaps one of ``spans`` (a character's lines), the eases :func:`settle`d: a character talks while they talk."""
    unique = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
    holds = zip(unique, [c.time for c in unique[1:]] + [end], strict=True)
    voiced = [replace(c, mouth="sing") if any(a < until and c.time < b for a, b in spans) else c for c, until in holds]
    return settle(voiced, fps)


def quieted(cues: Sequence[Cue], spans: Sequence[tuple[float, float]], end: float, fps: float = 15) -> list[Cue]:
    """:func:`speaking`, with every hold split where a line starts and stops, so a figure on one long hold talks for
    its line and is back on its own mouth the moment the line ends. Splitting moves nothing: a split cue only holds."""
    later = []
    for start, stop in spans:
        if stop < start:
            raise BlobError(f"a line ends before it starts: {start} to {stop}")
        for at in (start, stop):
            before = [c for c in cues if c.time <= at]
            if not before:
                raise BlobError(f"no cue stands at or before {at}, where a line starts or stops")
            held = max(before, key=lambda c: c.time)
            if held.time != at:
                later.append(replace(held, time=at, ease=0.0, lift=0.0))
    return speaking([*cues, *later], spans, end, fps)


def walking(
    points: Sequence[tuple[float, float]],
    start: float,
    stop: float,
    *,
    step: float = 0.22,
    scale: float = 1.0,
    flip: bool = False,
    **kw,
) -> list[Cue]:
    """Cues that walk ``points`` (output pixels) from ``start``, landing on the last at ``stop``, a stride every
    ``step`` seconds or the nearest that divides the time, each leg taking its share of the strides. ``kw`` goes to
    every stride, as a face does. The figure stands where the first point is at ``start``: its own cue puts it there."""
    if len(points) < 2:
        raise BlobError(f"a walk takes at least two points, got {len(points)}")
    if stop <= start:
        raise BlobError(f"a walk stops after it starts, got {start} to {stop}")
    if step <= 0:
        raise BlobError(f"a stride takes a positive time, got {step}")
    count = max(2, int((stop - start) / step + 1e-9))
    legs = len(points) - 1
    out = []
    for k in range(1, count + 1):
        along = k / count * legs
        leg = min(int(along), legs - 1)
        (ax, ay), (bx, by), part = points[leg], points[leg + 1], along - leg
        spot = (ax + (bx - ax) * part, ay + (by - ay) * part)
        pose = "walk-a" if k % 2 else "walk-b"
        out.append(cue(start + (stop - start) * k / count, pose, spot, scale=scale, ease=step, flip=flip, **kw))
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


def blob(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str,
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
    look: Look,
):
    """The blob rig in ``look`` performing ``cues`` until ``end``; ``mouth_states`` (``Episode.mouth``) drive every
    ``sing`` mouth; ``shadow`` puts a contact shadow under the feet on every drawing."""
    body_fill = look.fill or cv.white
    checks.positive(scale, BlobError, f"a blob's scale must be a positive number, got {scale!r}")
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
    outfit = look.outfit

    def keyed(g, paths: list[str], fill: str, stroke: str, sw: float):
        shape = cv.path(g, paths[0], fill, stroke, sw)
        cv.keys(shape, "path", list(zip(times, paths, strict=True)))
        return shape

    def dress(g, limb: str, wider: float) -> None:
        """``limb``'s cloth on every drawing, ``wider`` than the limb (a front limb is widened by its outline): the
        garment, then its cuff in the trim and the ink line where the cuff meets the skin."""
        assert outfit is not None
        strokes = [d.pose.limbs[limb] for d in frames]
        colour = outfit.top if limb in ("torso", *ARMS) else outfit.trousers
        if limb == "torso":
            keyed(g, [s.widened(wider).outline() for s in strokes], colour, cv.clear, 0)
            hems = []
            for s in strokes:
                rim, start = s._rim(14, 8)
                # The hip is the lower end, regardless of the torso's direction.
                hem = rim[14:23] if s.p3[1] > s.p0[1] else [rim[-1], *start, rim[0]]
                hems.append("M " + _points(hem))
            keyed(g, hems, cv.clear, cv.ink, o)
            return
        keyed(g, [cut(clothed(s, outfit, limb).widened(wider)) for s in strokes], colour, cv.clear, 0)
        cuffs = [_cuff(s, outfit, limb) for s in strokes]
        keyed(g, [cut(c.widened(wider), start=False) for c in cuffs], outfit.trim, cv.clear, 0)
        keyed(g, [_across(c, 1.0, wider) for c in cuffs], cv.clear, cv.ink, o)  # the cuff line, at the skin
        keyed(g, [_across(c, 0.0, wider) for c in cuffs], cv.clear, cv.ink, 0.6 * o)  # the cuff's seam, finer

    def front_limb(parent, limb):
        g = cv.group(parent, f"{id}-front-{limb}")
        _show(cv, g, _changes(fronts[limb], True))
        fills = [d.pose.limbs[limb].widened(o).outline() for d in frames]
        traces = [d.pose.limbs[limb].widened(o).contour() for d in frames]
        fill = cv.path(g, fills[0], body_fill, cv.clear, 0)
        cv.keys(fill, "path", list(zip(times, fills, strict=True)))
        if outfit is not None:
            dress(g, limb, o)
        trace = cv.path(g, traces[0], cv.clear, cv.ink, o)
        cv.keys(trace, "path", list(zip(times, traces, strict=True)))

    # Dressed, an arm held behind the body is drawn behind it: one colour never showed a hand over the body, a top does.
    order = LIMBS if outfit is None else (*ARMS, *FEET, "torso")
    for pass_name, fill, stroke, sw in (("outline", cv.ink, cv.ink, 2 * o), ("fill", body_fill, cv.clear, 0)):
        g = cv.group(root, f"{id}-{pass_name}")
        for limb in order:
            if pass_name == "fill" and outfit is not None and limb == "torso":
                for leg in FEET:
                    if any(v for _, v in fronts[leg]):
                        front_limb(g, leg)
            shape = limb_shape(g, limb, fill, stroke, sw)
            front = limb in fronts and any(v for _, v in fronts[limb])
            if front:
                _show(cv, shape, _changes(fronts[limb], False))
            if pass_name == "fill" and outfit is not None:
                cloth = cv.group(g, f"{id}-fill-{limb}-cloth")
                if front:
                    _show(cv, cloth, _changes(fronts[limb], False))
                dress(cloth, limb, 0.0)
        if pass_name == "fill" and outfit is not None:
            band = cv.group(g, f"{id}-collar")
            rims = [collar(d.pose) for d in frames]
            keyed(band, ["M " + _points(rim) + " Z" for rim in rims], outfit.trim, cv.clear, 0)
            keyed(band, ["M " + _points(rim[:COLLAR_STEPS]) for rim in rims], cv.clear, cv.ink, o)
        head = head_at(cv.group(g, f"{id}-head-{pass_name}"))
        r = radius + (o if pass_name == "outline" else 0)
        cv.ellipse(head, -r, -r, 2 * r, 2 * r, fill)
        if pass_name == "fill":
            _polish(cv, head, radius, look)
        if pass_name == "outline" and look.topper is not None:
            look.topper(cv, head_at(cv.group(root, f"{id}-{look.topper_id}")), radius)
    if look.hair is not None:
        look.hair(cv, head_at(cv.group(root, f"{id}-hair")), radius)
    # Dressed front legs are already under the top; arms still sit over it.
    for limb in FRONTABLE:
        if any(v for _, v in fronts[limb]) and (outfit is None or limb in ARMS):
            front_limb(root, limb)
    face = cv.group(root, f"{id}-face")
    cv.keys(face, "x", [(d.time, round(d.pose.head[0] + d.pose.face[0], 3)) for d in frames])
    cv.keys(face, "y", [(d.time, round(d.pose.head[1] + d.pose.face[1], 3)) for d in frames])
    if look.blush is not None:
        for side in (-1, 1):
            cv.ellipse(face, side * 58 - 15, 16, 30, 17, look.blush, opacity=0.85)
    # One group a drawn pair of eyes: "look" left keeps its old id, "look" right is a group of its own.
    eyes_track = [(d.time, (d.face.eyes, d.face.gaze)) for d in frames]
    for kind, gaze in dict.fromkeys(e for _, e in eyes_track):
        g = cv.group(face, f"{id}-eyes-{kind}" if gaze == "left" else f"{id}-eyes-{kind}-{gaze}")
        _show(cv, g, _changes(eyes_track, (kind, gaze)))
        EYES[kind](cv, g, 0, -8, shine=look.catchlights, lashes=look.lashes, gaze=gaze)
    mouths = mouth_track(frames, mouth_states or ())
    for shape in dict.fromkeys(m for _, m in mouths):
        g = cv.group(face, f"{id}-mouth-{shape}")
        _show(cv, g, _changes(mouths, shape))
        _mouth(cv, g, shape, 0, 32)
    if look.features is not None:
        look.features(cv, cv.group(face, f"{id}-{look.features_id}"), radius)
    return root


@register(
    "character",
    "pip",
    summary="Pip, the sprout-headed white blob: one interpolating rig (stand, step, walk, sit, type, nod, clasp, "
    "lean, groove, cheer, wave), eased in-betweens on a beat, six eyes, five mouths and a sung mouth that follows "
    "the soundtrack",
    contract=cc.soft(Cue, tuple(POSES), tuple(EYES), MOUTHS, tuple(FEET), tuple(MOUTH_STATES), gazes=GAZES),
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
    return blob(
        cv,
        parent,
        cues,
        end=end,
        x=x,
        y=y,
        scale=scale,
        mouth_states=mouth_states,
        id=id,
        fps=fps,
        radius=radius,
        shadow=shadow,
        look=PIP,
    )


@register(
    "character",
    "bo",
    summary="Bo, the boss: Pip's rig and pose sheet in a pale blue body with side-parted hair and square glasses, "
    "no blush; any cue Pip can perform, Bo can",
    contract=cc.soft(Cue, tuple(POSES), tuple(EYES), MOUTHS, tuple(FEET), tuple(MOUTH_STATES), gazes=GAZES),
)
def bo(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str = "bo",
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
):
    """Bo performing ``cues``: the same rig, poses and options as :func:`pip`, in :data:`BO`."""
    return blob(
        cv,
        parent,
        cues,
        end=end,
        x=x,
        y=y,
        scale=scale,
        mouth_states=mouth_states,
        id=id,
        fps=fps,
        radius=radius,
        shadow=shadow,
        look=BO,
    )


@register(
    "character",
    "juno",
    summary="Juno, the colleague who already did the reading: Pip's rig and pose sheet in an apricot body with "
    "an auburn bun, scalloped bangs, a coral scrunchie and freckles; shaded, with catch-lights and lashes on every "
    "eye",
    contract=cc.soft(Cue, tuple(POSES), tuple(EYES), MOUTHS, tuple(FEET), tuple(MOUTH_STATES), gazes=GAZES),
)
def juno(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str = "juno",
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
):
    """Juno performing ``cues``: the same rig, poses and options as :func:`pip`, in :data:`JUNO`."""
    return blob(
        cv,
        parent,
        cues,
        end=end,
        x=x,
        y=y,
        scale=scale,
        mouth_states=mouth_states,
        id=id,
        fps=fps,
        radius=radius,
        shadow=shadow,
        look=JUNO,
    )


@register(
    "character",
    "juno@2",
    summary="Juno version 2 (ADR 0240): version 1's head, hair and face, dressed at home in a teal top and mustard "
    "trousers with a cream collar and cuffs, drawn by the rig on every pose and in-between; hands and feet bare",
    contract=cc.soft(Cue, tuple(POSES), tuple(EYES), MOUTHS, tuple(FEET), tuple(MOUTH_STATES), gazes=GAZES),
)
def juno_v2(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str = "juno",
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
):
    """Juno version 2 performing ``cues``: :func:`juno` in :data:`JUNO_V2`, her home outfit on. A reel calls it by
    name; version 1 (:func:`juno`) stays as published reels drew it."""
    return blob(
        cv,
        parent,
        cues,
        end=end,
        x=x,
        y=y,
        scale=scale,
        mouth_states=mouth_states,
        id=id,
        fps=fps,
        radius=radius,
        shadow=shadow,
        look=JUNO_V2,
    )


@register(
    "character",
    "remy",
    summary="Remy from IT support: Pip's rig and pose sheet in a lavender body with a spiky tuft and a headset "
    "(padded band, ear cups with a status light, mic boom); shaded, with a gloss on the head and catch-lights",
    contract=cc.soft(Cue, tuple(POSES), tuple(EYES), MOUTHS, tuple(FEET), tuple(MOUTH_STATES), gazes=GAZES),
)
def remy(
    cv: Canvas,
    parent,
    cues: Sequence[Cue],
    *,
    end: float,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    mouth_states: Sequence[tuple[float, str]] | None = None,
    id: str = "remy",
    fps: float = 15,
    radius: float = HEAD,
    shadow: bool = False,
):
    """Remy performing ``cues``: the same rig, poses and options as :func:`pip`, in :data:`REMY`."""
    return blob(
        cv,
        parent,
        cues,
        end=end,
        x=x,
        y=y,
        scale=scale,
        mouth_states=mouth_states,
        id=id,
        fps=fps,
        radius=radius,
        shadow=shadow,
        look=REMY,
    )


# -- props and the stage: a 3/4 view from above and to the right ---------------------------------------------
def _part(id: str, default: str, part: str, name: str) -> str:
    """The id of a location's ``part``: the default instance keeps the part's own ``name``; a location drawn under
    another ``id`` namespaces it, so a room drawn twice never repeats an id."""
    return name if id == default else f"{id}-{part}"


def _poly(cv: Canvas, g, pts: Sequence[Point], fill: str, line: str = WOOD_LINE, sw: float = 4) -> None:
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts) + " Z"
    cv.path(g, d, fill, line, sw)


def _leg(cv: Canvas, g, x: float, top: float, bottom: float, w: float = 34, side: float = 14) -> None:
    """A square wooden leg: the face toward the viewer and its darker side face."""
    _poly(cv, g, [(x + w, top), (x + w + side, top - 10), (x + w + side, bottom - 10), (x + w, bottom)], WOOD_SIDE)
    _poly(cv, g, [(x, top), (x + w, top), (x + w, bottom), (x, bottom)], WOOD_FRONT)


@register(
    "prop",
    "soft-desk",
    summary="A wooden desk in a 3/4 view from above: top, front and side faces, square legs",
    contract=bdc.contract('soft-desk'),
)
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


@register(
    "prop",
    "soft-chair",
    summary="A low wooden chair in a 3/4 view, facing left, slatted backrest on the right",
    contract=bdc.contract('soft-chair'),
)
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


@register(
    "prop",
    "soft-laptop",
    summary="An open laptop on the soft desk: keyboard deck and the back of the lid",
    contract=bdc.contract('soft-laptop', keyboard=keyboard),
)
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
    contract=bdc.contract('soft-office', keyboard=keyboard),
)
def office(cv: Canvas, parent, *, shots: Sequence[tuple[float, float]] | None = None, id: str = "soft-office"):
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    chair(cv, g, _part(id, "soft-office", "chair", "soft-chair"))
    desk(cv, g, _part(id, "soft-office", "desk", "soft-desk"))
    signature.cactus(cv, g, 170, 1040, 0.62)
    laptop(cv, g, _part(id, "soft-office", "laptop", "soft-laptop"))
    signature.code(cv, g, 40, 1327, 14, color=WOOD_LINE, angle=-9)
    return g


# -- the soft home: a sofa in the same 3/4 view, facing left -------------------------------------------------
# A point on the sofa is ``a`` along the seat's depth (positive toward the backrest, on the right) and ``c`` along
# its length (positive toward the viewer), ``up`` above the seat, from the hip at SOFA_SEAT; the axes are the
# office chair's, so a seated pose fits both.
_BACK = -45 / 215  # rise per pixel toward the backrest
_NEAR = 70 / 95  # drop per pixel toward the viewer
_DROP = SOFA_FLOOR - SOFA_SEAT[1] + 115 * _BACK  # seat top to floor where the soles land, 115 ahead of the hip
_FEET = 18.0
_SEAT_A, _SEAT_C = (-110.0, 120.0), (-300.0, 170.0)
_ARM_W, _ARM_UP, _BACK_A, _BACK_UP = 60.0, 70.0, 200.0, 240.0


def _sofa_pt(a: float, c: float, up: float = 0.0) -> Point:
    return (SOFA_SEAT[0] + a + c, SOFA_SEAT[1] + a * _BACK + c * _NEAR - up)


def _box(cv: Canvas, g, a: tuple[float, float], c: tuple[float, float], up: tuple[float, float], faces=None) -> None:
    """A fabric block over ``a`` x ``c`` from ``up[0]`` to ``up[1]`` above the seat: its left, near and top faces."""
    (a0, a1), (c0, c1), (lo, hi) = a, c, up
    left = [_sofa_pt(a0, c0, hi), _sofa_pt(a0, c1, hi), _sofa_pt(a0, c1, lo), _sofa_pt(a0, c0, lo)]
    near = [_sofa_pt(a0, c1, hi), _sofa_pt(a1, c1, hi), _sofa_pt(a1, c1, lo), _sofa_pt(a0, c1, lo)]
    top = [_sofa_pt(a0, c0, hi), _sofa_pt(a1, c0, hi), _sofa_pt(a1, c1, hi), _sofa_pt(a0, c1, hi)]
    for name, pts, fill in (("near", near, FABRIC_FRONT), ("left", left, FABRIC_SIDE), ("top", top, FABRIC_TOP)):
        if faces is None or name in faces:
            _poly(cv, g, pts, fill, FABRIC_LINE)


def _foot(cv: Canvas, g, a: float, c: float) -> None:
    x, y = _sofa_pt(a, c, -_DROP + _FEET)
    _leg(cv, g, x, y, y + _FEET, w=22, side=8)


def sofa_seat() -> list[Point]:
    """The sofa's seat cushion top in output pixels, where a seated pose's hip lands."""
    (a0, a1), (c0, c1) = _SEAT_A, _SEAT_C
    return [_sofa_pt(a0, c0), _sofa_pt(a1, c0), _sofa_pt(a1, c1), _sofa_pt(a0, c1)]


@register(
    "prop",
    "soft-sofa",
    summary="A two-seat fabric sofa in a 3/4 view, facing left: backrest on the right, an arm at each end; "
    "on_sofa draws who sits on it before the near arm",
    contract=bdc.contract('soft-sofa', sofa_seat=sofa_seat),
)
def sofa(cv: Canvas, parent, *, on_sofa: Callable[[object], object] | None = None, id: str = "soft-sofa"):
    g = cv.group(parent, id)
    (a0, a1), (c0, c1) = _SEAT_A, _SEAT_C
    far, near = (c0 - _ARM_W, c0), (c1, c1 + _ARM_W)
    for a, c in ((a0, far[0]), (_BACK_A, far[0])):
        _foot(cv, g, a, c)
    _box(cv, g, (a1, _BACK_A), (far[0], near[1]), (-_DROP + _FEET, _BACK_UP))  # backrest
    _box(cv, g, (a0 - 10, a1), far, (-_DROP + _FEET, _ARM_UP))  # far arm
    seat = cv.group(g, f"{id}-seat")
    _box(cv, seat, (a0, a1), (c0, c1), (-_DROP + _FEET, 0), faces=("left", "top"))
    mid = (c0 + c1) / 2  # the seam between the two seat cushions, and the two back cushions above it
    cv.path(
        seat, "M {:.1f} {:.1f} L {:.1f} {:.1f}".format(*_sofa_pt(a0, mid), *_sofa_pt(a1, mid)), stroke=FABRIC_LINE, sw=3
    )
    cv.path(
        seat,
        "M {:.1f} {:.1f} L {:.1f} {:.1f}".format(*_sofa_pt(a1, mid), *_sofa_pt(a1, mid, _BACK_UP - 30)),
        stroke=FABRIC_LINE,
        sw=3,
        opacity=0.6,
    )
    if on_sofa is not None:
        on_sofa(g)
    arm = cv.group(g, f"{id}-arm-near")
    _foot(cv, arm, a0 - 10, near[1])
    _foot(cv, arm, _BACK_A, near[1])
    _box(cv, arm, (a0 - 10, _BACK_A), near, (-_DROP + _FEET, _ARM_UP))
    return g


def _floor_at(a: float, c: float) -> Point:
    """The floor under the sofa point ``a, c``."""
    return _sofa_pt(a, c, -_DROP)


LAMP_AT = _floor_at(260, -400)  # where the soft home's floor lamp stands
LAMP_SHADE = (LAMP_AT[0], LAMP_AT[1] - 555)  # the middle of its shade, for a camera to frame


def _lamp_glow(cv: Canvas, g, talk: Sequence[tuple[float, float]], id: str) -> None:
    """The shade lit up, with a halo, in each ``talk`` span: a smart lamp speaking."""
    x, floor = LAMP_AT
    glow = cv.group(g, id, opacity=0)
    cv.ellipse(glow, x - 170, floor - 725, 340, 340, "#FFE9A0", opacity=0.45)
    _poly(
        cv,
        glow,
        [(x - 62, floor - 500), (x + 62, floor - 500), (x + 44, floor - 610), (x - 44, floor - 610)],
        "#FFF6CF",
        WOOD_LINE,
        4,
    )
    cv.path(glow, f"M {x - 58:g} {floor - 512:g} L {x + 58:g} {floor - 512:g}", stroke="#F2A93B", sw=6)
    cv.keys(glow, "opacity", [(0, 0)] + [k for start, end in talk for k in ((start, 1), (end, 0))])


def _lamp(cv: Canvas, g, x: float, floor: float) -> None:
    """A floor lamp: a round base, a thin pole and a drum shade."""
    cv.ellipse(g, x, floor, 90, 22, WOOD_FRONT, WOOD_LINE, 4)
    cv.path(g, f"M {x:g} {floor:g} L {x:g} {floor - 520:g}", stroke=WOOD_LINE, sw=8)
    _poly(
        cv, g, [(x - 62, floor - 500), (x + 62, floor - 500), (x + 44, floor - 610), (x - 44, floor - 610)], "#F6E3B4"
    )


def _side_table(cv: Canvas, g, x: float, floor: float) -> Point:
    """A small wooden side table; returns the middle of its top, where the cactus stands."""
    h, w, d = 150.0, 120.0, 40.0
    _leg(cv, g, x + 6, floor - h + 26, floor, w=18, side=8)
    _leg(cv, g, x + w - 24, floor - h + 26, floor, w=18, side=8)
    _poly(
        cv,
        g,
        [(x + w, floor - h), (x + w + d, floor - h - 22), (x + w + d, floor - h - 4), (x + w, floor - h + 18)],
        WOOD_SIDE,
    )
    _poly(cv, g, [(x, floor - h), (x + w, floor - h), (x + w, floor - h + 18), (x, floor - h + 18)], WOOD_FRONT)
    _poly(cv, g, [(x, floor - h), (x + d, floor - h - 22), (x + w + d, floor - h - 22), (x + w, floor - h)], WOOD_TOP)
    return (x + w / 2 + d / 2, floor - h - 8)


@register(
    "location",
    "soft-home",
    summary="The warm living room in the office's 3/4 view: a fabric sofa facing left on a rug, a floor lamp "
    "behind it, a side table with the signature cactus; on_sofa seats a character between the seat and the near arm",
    contract=bdc.contract('soft-home', sofa_seat=sofa_seat),
)
def home(
    cv: Canvas,
    parent,
    *,
    shots: Sequence[tuple[float, float]] | None = None,
    on_sofa: Callable[[object], object] | None = None,
    id: str = "soft-home",
    lamp_talk: Sequence[tuple[float, float]] = (),
):
    """``lamp_talk``: (start, end) spans, in order and apart, in which the floor lamp speaks and its shade glows."""
    last = 0.0
    for start, end in lamp_talk:
        if not (checks.number(start) and checks.number(end) and last <= start < end):
            raise BlobError(f"lamp_talk spans are (start, end) in order from 0, apart; got {list(lamp_talk)}")
        last = end
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    _poly(
        cv,
        g,
        [_floor_at(-380, -180), _floor_at(-60, -180), _floor_at(-60, 260), _floor_at(-380, 260)],
        RUG,
        RUG_LINE,
        4,
    )
    lx, ly = LAMP_AT
    _lamp(cv, g, lx, ly)
    if lamp_talk:
        _lamp_glow(cv, g, lamp_talk, f"{id}-lamp-talk")
    sofa(cv, g, on_sofa=on_sofa, id=_part(id, "soft-home", "sofa", "soft-sofa"))
    top = _side_table(cv, g, 24, _floor_at(-330, -250)[1])
    signature.cactus(cv, g, top[0], top[1], 0.55)
    signature.code(cv, g, *_floor_at(-330, 120), 14, color=RUG_LINE, angle=36)
    return g


# -- polished rooms: walls, floor and light in the same 3/4 view ----------------------------------------------
# A room point is ``a`` along the back wall (positive to the right, toward the corner), ``c`` out from it toward
# the viewer and ``up`` above the floor, from ROOM, where the back wall meets the floor. The axes are the sofa's,
# so a seated pose fits a room's seats as it fits the chair. The side wall stands at ``a = CORNER``.
ROOM = (330.0, 1180.0)
CORNER = 530.0
CAPTION_FLOOR = 440.0  # wall decor stays below this line, under the Soft captions (y 250-430)
BASEBOARD = 22.0
BREAK_STAND = (400.0, FLOOR)  # where a standing character waits in front of the break-room counter
LIGHT_GLAZE = "#FFF8E8"


def room_point(a: float, c: float = 0.0, up: float = 0.0) -> Point:
    """A room point in output pixels."""
    return (ROOM[0] + a + c, ROOM[1] + a * _BACK + c * _NEAR - up)


def wall_base(x: float) -> float:
    """The y at output ``x`` where the back wall (left of the corner) or the side wall (right of it) meets the
    floor."""
    corner_x, corner_y = room_point(CORNER)
    if x <= corner_x:
        return ROOM[1] + (x - ROOM[0]) * _BACK
    return corner_y + (x - corner_x) * _NEAR


def wall_quad(wall: str, a0: float, a1: float, u0: float, u1: float) -> list[Point]:
    """A rectangle on a wall from ``a0`` to ``a1`` along it (on the side wall: ``c``) and ``u0`` to ``u1`` up."""
    if wall == "back":
        return [room_point(a0, 0, u0), room_point(a1, 0, u0), room_point(a1, 0, u1), room_point(a0, 0, u1)]
    if wall == "side":
        return [
            room_point(CORNER, a0, u0),
            room_point(CORNER, a1, u0),
            room_point(CORNER, a1, u1),
            room_point(CORNER, a0, u1),
        ]
    raise BlobError(f"a wall is 'back' or 'side', got {wall!r}")


def floor_quad(a0: float, a1: float, c0: float, c1: float, up: float = 0.0) -> list[Point]:
    """A rectangle parallel to the floor, ``up`` above it."""
    return [room_point(a0, c0, up), room_point(a1, c0, up), room_point(a1, c1, up), room_point(a0, c1, up)]


def _quad(cv: Canvas, g, pts: Sequence[Point], fill: str, line: str | None = None, sw: float = 4, **kw):
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    return cv.path(g, d, fill, line if line is not None else cv.clear, sw if line is not None else 0, **kw)


def _line(cv: Canvas, g, a: Point, b: Point, colour: str, sw: float = 3, **kw):
    return cv.path(g, f"M {a[0]:.1f} {a[1]:.1f} L {b[0]:.1f} {b[1]:.1f}", stroke=colour, sw=sw, **kw)


def _block(
    cv: Canvas,
    g,
    a: tuple[float, float],
    c: tuple[float, float],
    up: tuple[float, float],
    faces: tuple[str, str, str],
    line: str,
    *,
    end: str = "right",
    sw: float = 4,
) -> None:
    """A box standing in the room: its near face (toward the viewer), one end and its top, in ``faces`` colours
    (top, near, end). ``end`` is the end the viewer sees: ``right`` (``a1``) or ``left`` (``a0``)."""
    (a0, a1), (c0, c1), (lo, hi) = a, c, up
    top, near, side = faces
    ax = a1 if end == "right" else a0
    _quad(
        cv,
        g,
        [room_point(ax, c0, hi), room_point(ax, c1, hi), room_point(ax, c1, lo), room_point(ax, c0, lo)],
        side,
        line,
        sw,
    )
    _quad(
        cv,
        g,
        [room_point(a0, c1, hi), room_point(a1, c1, hi), room_point(a1, c1, lo), room_point(a0, c1, lo)],
        near,
        line,
        sw,
    )
    _quad(cv, g, floor_quad(a0, a1, c0, c1, hi), top, line, sw)


@dataclass(frozen=True)
class RoomPalette:
    """The shell of a polished room: back and side wall, floor and its lines, baseboard, and the outline."""

    wall: str
    side: str
    floor: str
    grain: str
    baseboard: str
    line: str


def _shell(cv: Canvas, g, id: str, p: RoomPalette, *, tiles: bool) -> None:
    """Walls to the top of the frame, the floor to the bottom, planks (or tiles) on it, the baseboard and the
    soft shadow where the floor meets the walls."""
    w, h = cv.width, cv.height
    cx, cy = room_point(CORNER)
    left, right = (0.0, wall_base(0)), (float(w), wall_base(w))
    walls = cv.group(g, f"{id}-walls")
    _quad(cv, walls, [(0, 0), (cx, 0), (cx, cy), left], p.wall)
    _quad(cv, walls, [(cx, 0), (w, 0), right, (cx, cy)], p.side)
    _line(cv, walls, (cx, 0), (cx, cy), p.line, 3, opacity=0.35)
    floor = cv.group(g, f"{id}-floor")
    _quad(cv, floor, [left, (cx, cy), right, (w, h), (0, h)], p.floor)
    far_c = (h - ROOM[1]) / _NEAR + 400  # far enough toward the viewer to leave the frame
    if tiles:  # a grid on both axes
        for a in range(-1800, int(CORNER), 90):
            _line(cv, floor, room_point(a), room_point(a, far_c), p.grain, 3, opacity=0.55)
    for k, c in enumerate(range(45 if tiles else 38, int(far_c), 90 if tiles else 76)):
        _line(cv, floor, room_point(-1800, c), room_point(CORNER, c), p.grain, 3, opacity=0.55)
        if not tiles:  # plank joints, staggered row by row
            for a in range(-1800 + (k % 3) * 120, int(CORNER) - 40, 360):
                _line(cv, floor, room_point(a, c), room_point(a, c - 76), p.grain, 2.5, opacity=0.45)
    # the floor darkens toward the walls, then the baseboards
    _quad(
        cv,
        floor,
        [left, (cx, cy), right, (right[0], right[1] + 34), (cx, cy + 34), (left[0], left[1] + 34)],
        cv.ink,
        opacity=0.06,
    )
    _quad(cv, floor, wall_quad("back", -ROOM[0], CORNER, 0, BASEBOARD), p.baseboard, p.line, 3)
    _quad(cv, floor, wall_quad("side", 0, w - cx, 0, BASEBOARD), p.baseboard, p.line, 3)


def _shadow(cv: Canvas, g, cx: float, cy: float, rx: float, ry: float, opacity: float = 0.12) -> None:
    cv.ellipse(g, cx - rx, cy - ry, 2 * rx, 2 * ry, cv.ink, opacity=opacity)


def _window(cv: Canvas, g, wall: str, a0: float, a1: float, u0: float, u1: float, sky: str, frame: str, line: str):
    """A window with a sky, a cloud, a cross of glazing bars and a sill; returns the glass corners."""
    _quad(cv, g, wall_quad(wall, a0 - 12, a1 + 12, u0 - 12, u1 + 12), frame, line, 4)
    glass = wall_quad(wall, a0, a1, u0, u1)
    _quad(cv, g, glass, sky, line, 3)
    (x0, y0), (x1, y1) = glass[3], glass[2]
    for dx, dy, rw, rh in ((0.3, 0.32, 0.22, 0.09), (0.42, 0.27, 0.2, 0.11), (0.52, 0.33, 0.18, 0.08)):
        cx, cy = x0 + (x1 - x0) * dx, y0 + (y1 - y0) * dx + (glass[0][1] - y0) * dy
        cv.ellipse(g, cx - rw * (x1 - x0) / 2, cy - rh * 60, rw * (x1 - x0), rh * 120, "#FFFFFF", opacity=0.9)
    mid_a, mid_u = (a0 + a1) / 2, (u0 + u1) / 2
    for p, q in (wall_quad(wall, mid_a, mid_a, u0, u1)[1:3], wall_quad(wall, a0, a1, mid_u, mid_u)[0:2]):
        _line(cv, g, p, q, frame, 9)
    _quad(cv, g, wall_quad(wall, a0 - 26, a1 + 26, u0 - 26, u0 - 10), frame, line, 3)  # the sill
    return glass


# -- the meeting room --------------------------------------------------------------------------------------------
MEETING = RoomPalette(
    wall="#E3E6D6", side="#D0D6C2", floor="#DDBB98", grain="#C39C78", baseboard="#F7F1E6", line="#4A4636"
)
WALNUT_TOP, WALNUT_FRONT, WALNUT_SIDE, WALNUT_LINE, WALNUT_SHINE = "#8E5D3E", "#73492F", "#5E3A25", "#2E1B10", "#B9875F"
UPHOLSTERY, UPHOLSTERY_SIDE, UPHOLSTERY_LINE = "#E07A5F", "#C4644B", "#5A2A1E"
CHROME, CHROME_DARK = "#C9CFD4", "#7D858C"
SCREEN_BEZEL, SCREEN_LIGHT, SCREEN_DEEP = "#2B2E36", "#5D8FD0", "#2F5490"
TABLE_TOP = 300.0  # the table's top, above the floor: the desk's height, so a seated pose types on it
_TABLE_A, _TABLE_C = (-1100.0, -110.0), (180.0, 440.0)
WALL_DECOR: dict[str, tuple[str, float, float, float, float]] = {
    "meeting-screen": ("back", -300.0, 120.0, 440.0, 700.0),
    "meeting-clock": ("back", 250.0, 350.0, 520.0, 620.0),
    "meeting-window": ("side", 60.0, 200.0, 320.0, 668.0),
    "break-cabinets": ("back", -330.0, -60.0, 540.0, 745.0),
    "break-window": ("back", 30.0, 250.0, 450.0, 680.0),
}


def meeting_table_top() -> list[Point]:
    """The meeting table's top in output pixels, where the laptop stands."""
    return floor_quad(*_TABLE_A, *_TABLE_C, TABLE_TOP)


def swivel_seat() -> list[Point]:
    """The swivel chair's seat in output pixels: the office chair's, so the seated hip lands on it."""
    return [(640.0, 1315.0), (860.0, 1275.0), (950.0, 1340.0), (735.0, 1385.0)]


def _meeting_table(cv: Canvas, g) -> None:
    (a0, a1), (c0, c1) = _TABLE_A, _TABLE_C
    for c in (c0 + 40, c1 - 40):  # a panel leg at the near end, each side
        _block(
            cv,
            g,
            (a1 - 70, a1 - 40),
            (c - 20, c + 20),
            (0, TABLE_TOP - 26),
            (WALNUT_TOP, WALNUT_FRONT, WALNUT_SIDE),
            WALNUT_LINE,
        )
    _block(cv, g, (a0, a1), (c0, c1), (TABLE_TOP - 26, TABLE_TOP), (WALNUT_TOP, WALNUT_FRONT, WALNUT_SIDE), WALNUT_LINE)
    _line(cv, g, room_point(a0, c1 - 6, TABLE_TOP), room_point(a1 - 6, c1 - 6, TABLE_TOP), WALNUT_SHINE, 4)
    _line(cv, g, room_point(a1 - 6, c0 + 6, TABLE_TOP), room_point(a1 - 6, c1 - 6, TABLE_TOP), WALNUT_SHINE, 4)
    for a, c in ((-600, 320),):  # a notepad with its lines
        _quad(cv, g, floor_quad(a, a + 110, c, c + 80, TABLE_TOP), "#FBF8F1", WALNUT_LINE, 3)
        for k in (1, 2, 3):
            _line(
                cv,
                g,
                room_point(a + 14, c + 20 * k, TABLE_TOP),
                room_point(a + 96, c + 20 * k, TABLE_TOP),
                "#9DB8D8",
                2.5,
            )
    gx, gy = room_point(-380, 380, TABLE_TOP)  # a glass of water by the laptop
    cv.rect(g, gx - 18, gy - 62, 36, 62, "#DDEFF5", WALNUT_LINE, 3, radius=6, opacity=0.85)
    cv.rect(g, gx - 15, gy - 34, 30, 31, "#A9D3E6", radius=4)
    _line(cv, g, (gx - 9, gy - 54), (gx - 9, gy - 10), "#FFFFFF", 3, opacity=0.9)


@register(
    "prop",
    "soft-swivel-chair",
    summary="An upholstered swivel chair facing left on a five-spoke chrome base; seated poses fit it like the "
    "office chair",
    contract=bdc.contract('soft-swivel-chair', swivel_seat=swivel_seat),
)
def swivel_chair(cv: Canvas, parent, id: str = "soft-swivel-chair"):
    g = cv.group(parent, id)
    hub_a, hub_c = 45.0, 415.0  # under the seated hip
    spokes = [
        (hub_a + 120 * math.cos(t), hub_c + 120 * math.sin(t)) for t in (math.radians(18 + 72 * k) for k in range(5))
    ]
    hub = room_point(hub_a, hub_c, 16)
    _shadow(cv, g, *room_point(hub_a, hub_c), 150, 34)
    back = [s for s in spokes if s[1] < hub_c]
    for spokes_now in (back, [s for s in spokes if s[1] >= hub_c]):
        for a, c in spokes_now:
            tip = room_point(a, c, 16)
            _line(cv, g, hub, tip, cv.ink, 18)
            _line(cv, g, hub, tip, CHROME, 10)
            cv.ellipse(g, tip[0] - 15, tip[1] - 2, 30, 20, "#2A2D33", cv.ink, 3)
        if spokes_now is back:
            cv.rect(g, hub[0] - 14, 1360, 28, hub[1] - 1355, CHROME, cv.ink, 4, radius=6)  # the gas lift
            _line(cv, g, (hub[0] - 5, 1372), (hub[0] - 5, hub[1] - 8), "#FFFFFF", 3, opacity=0.8)
    # the backrest: a padded panel up the seat's right edge, its thickness on the right, a stitched seam
    _quad(cv, g, [(958, 1046), (978, 1036), (978, 1318), (958, 1330)], UPHOLSTERY_SIDE, UPHOLSTERY_LINE)
    panel = "M 846 1262 L 846 1000 Q 846 966 878 980 L 932 1008 Q 958 1022 958 1052 L 958 1330 Z"
    cv.path(g, panel, UPHOLSTERY, UPHOLSTERY_LINE, 4)
    cv.path(g, "M 864 1240 L 864 1006 L 940 1046 L 940 1290", stroke=UPHOLSTERY_LINE, sw=2.5, opacity=0.45)
    # the seat cushion, thick and rounded at the front
    seat = swivel_seat()
    _quad(cv, g, [seat[0], seat[3], (735, 1420), (640, 1350)], UPHOLSTERY_SIDE, UPHOLSTERY_LINE)
    _quad(cv, g, [seat[3], seat[2], (950, 1375), (735, 1420)], UPHOLSTERY_SIDE, UPHOLSTERY_LINE)
    cv.path(
        g,
        "M 652 1313 Q 640 1317 652 1326 L 727 1381 Q 735 1388 748 1382 L 940 1342 Q 952 1338 942 1330 "
        "L 868 1278 Q 860 1273 850 1276 Z",
        UPHOLSTERY,
        UPHOLSTERY_LINE,
        4,
    )
    _line(cv, g, (668, 1318), (740, 1371), "#F0A08A", 4, opacity=0.9)
    return g


def meeting_screen() -> tuple[Point, float, float, float]:
    """The meeting room screen's picture as a flat frame: its top-left corner in output pixels, its width and
    height, and the ``skewY`` (degrees) that lays a flat drawing along the back wall."""
    _, a0, a1, u0, u1 = WALL_DECOR["meeting-screen"]
    i0, i1, v0, v1 = a0 + 16, a1 - 16, u0 + 16, u1 - 16
    return room_point(i0, 0, v1), i1 - i0, v1 - v0, math.degrees(math.atan(_BACK))


def _screen(cv: Canvas, g, call: Callable[[object], object] | None = None, call_id: str = "") -> None:
    """The wall screen showing a slide: a title, a bar chart and a page dot row; a webcam on top. ``call`` draws
    over the slide in the flat frame of :func:`meeting_screen`, masked to the picture."""
    _, a0, a1, u0, u1 = WALL_DECOR["meeting-screen"]
    _quad(cv, g, wall_quad("back", a0 + 14, a1 + 14, u0 - 14, u1 - 14), cv.ink, opacity=0.12)  # cast on the wall
    _quad(cv, g, wall_quad("back", a0, a1, u0, u1), SCREEN_BEZEL, cv.ink, 4)
    glow = cv.grad("soft-screen-glow", [(0, SCREEN_LIGHT), (1, SCREEN_DEEP)])
    i0, i1, v0, v1 = a0 + 16, a1 - 16, u0 + 16, u1 - 16
    _quad(cv, g, wall_quad("back", i0, i1, v0, v1), glow)
    _quad(cv, g, wall_quad("back", i0 + 24, i0 + 210, v1 - 46, v1 - 26), "#FFFFFF")  # the slide's title
    _quad(cv, g, wall_quad("back", i0 + 24, i0 + 140, v1 - 66, v1 - 56), "#FFFFFF", opacity=0.6)
    base = v0 + 34
    for k, (height, colour) in enumerate(((70, LEAF), (104, "#F2A93B"), (140, "#E8695A"), (176, "#FFFFFF"))):
        a = i0 + 40 + k * 64
        _quad(cv, g, wall_quad("back", a, a + 40, base, base + height), colour)
    _line(cv, g, room_point(i0 + 28, 0, base), room_point(i0 + 300, 0, base), "#FFFFFF", 3, opacity=0.8)
    for k in range(6):  # page dots: the first of many
        x, y = room_point(i1 - 120 + k * 18, 0, v0 + 18)
        cv.ellipse(g, x - 4, y - 4, 8, 8, "#FFFFFF", opacity=1.0 if k == 0 else 0.35)
    gloss = [
        room_point(i0 + 200, 0, v1),
        room_point(i0 + 270, 0, v1),
        room_point(i0 + 110, 0, v0),
        room_point(i0 + 40, 0, v0),
    ]
    _quad(cv, g, gloss, "#FFFFFF", opacity=0.07)
    if call is not None:
        (x, y), w, h, skew = meeting_screen()
        frame = cv.group(g, call_id, x=x, y=y, skewY=skew)
        frame.add_mask(type="rect", x=0, y=0, width=w, height=h)
        call(frame)
    cx, cy = room_point((a0 + a1) / 2, 0, u1)
    cv.rect(g, cx - 34, cy - 20, 68, 22, SCREEN_BEZEL, cv.ink, 3, radius=8)  # the webcam
    cv.ellipse(g, cx - 8, cy - 17, 16, 16, "#1B1D22", "#5D8FD0", 2.5)


def _clock(cv: Canvas, g) -> None:
    _, a0, a1, u0, u1 = WALL_DECOR["meeting-clock"]
    x, y = room_point((a0 + a1) / 2, 0, (u0 + u1) / 2)
    r = 46.0
    cv.ellipse(g, x - r + 5, y - r + 6, 2 * r, 2 * r, cv.ink, opacity=0.1)
    cv.ellipse(g, x - r, y - r, 2 * r, 2 * r, "#FBF8F1", cv.ink, 5)
    for k in range(12):
        t = math.radians(30 * k)
        inner = r - (12 if k % 3 == 0 else 8)
        _line(
            cv,
            g,
            (x + inner * math.sin(t), y - inner * math.cos(t)),
            (x + (r - 5) * math.sin(t), y - (r - 5) * math.cos(t)),
            cv.ink,
            3,
        )
    _line(cv, g, (x, y), (x + 18, y - 14), cv.ink, 5)  # ten to two
    _line(cv, g, (x, y), (x - 24, y - 16), cv.ink, 4)
    cv.ellipse(g, x - 5, y - 5, 10, 10, "#E8695A")


@register(
    "location",
    "soft-meeting-room",
    summary="A polished meeting room in the office's 3/4 view: sage walls, a plank floor and baseboards, a walnut "
    "table that takes the laptop, an upholstered swivel chair at the office chair's seat, a wall screen with a slide "
    "and a webcam, a wall clock, a side window whose light falls on the floor, and the signature cactus",
    contract=bdc.contract(
        'soft-meeting-room',
        meeting_screen=meeting_screen,
        meeting_table_top=meeting_table_top,
        swivel_seat=swivel_seat,
        keyboard=keyboard,
        room_point=room_point,
        wall_quad=wall_quad,
    ),
)
def meeting_room(
    cv: Canvas,
    parent,
    *,
    shots: Sequence[tuple[float, float]] | None = None,
    id: str = "soft-meeting-room",
    on_screen: Callable[[object], object] | None = None,
    chair: bool = True,
):
    """``on_screen`` (opt-in) draws a call over the screen's slide, in the flat frame of :func:`meeting_screen`.
    ``chair=False`` clears the swivel chair, for a scene that walks across the room's right side."""
    if not isinstance(chair, bool):
        raise BlobError(f"a meeting room has a chair or it does not, got {chair!r}")
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    _shell(cv, g, id, MEETING, tiles=False)
    decor = cv.group(g, f"{id}-decor")
    _, w0, w1, u0, u1 = WALL_DECOR["meeting-window"]
    _window(
        cv,
        decor,
        "side",
        w0,
        w1,
        u0,
        u1,
        cv.grad("soft-sky", [(0, "#BFE0F2"), (1, "#EAF6FB")]),
        "#FBF7F0",
        MEETING.line,
    )
    _screen(cv, decor, on_screen, f"{id}-screen-call")
    _clock(cv, decor)
    light = cv.group(g, f"{id}-light")
    # The sun comes in low through the side window, across the room and toward the viewer, so the window's two
    # panes fall on the open floor in front of the table: a window point (c, up) lands at (CORNER - up, c + 0.6 up).
    half = (w0 + w1) / 2
    for c0, c1 in ((w0, half - 5), (half + 5, w1)):
        patch = [
            room_point(CORNER - u0, c0 + 0.6 * u0),
            room_point(CORNER - u0, c1 + 0.6 * u0),
            room_point(CORNER - u1, c1 + 0.6 * u1),
            room_point(CORNER - u1, c0 + 0.6 * u1),
        ]
        _quad(cv, light, patch, LIGHT_GLAZE, opacity=0.32)
    furniture = cv.group(g, f"{id}-furniture")
    _shadow(cv, furniture, *room_point(-400, 310), 360, 70, 0.1)
    if chair:
        swivel_chair(cv, furniture, _part(id, "soft-meeting-room", "swivel-chair", "soft-swivel-chair"))
    _meeting_table(cv, furniture)
    laptop(cv, furniture, id=f"{id}-laptop")
    top = room_point(-330, 200, TABLE_TOP)
    signature.cactus(cv, furniture, top[0], top[1], 0.55)
    x, y = room_point(-620, _TABLE_C[1], TABLE_TOP - 18)
    signature.code(cv, furniture, x, y, 14, color=WALNUT_SHINE, angle=-12)
    return g


# -- the break room --------------------------------------------------------------------------------------------
BREAK = RoomPalette(
    wall="#F6E5C3", side="#EAD2A7", floor="#E9C2A3", grain="#D29F7C", baseboard="#FBF4E6", line="#4D3B26"
)
CABINET, CABINET_SIDE, CABINET_LINE = "#A9D3C3", "#8DBBA9", "#2E4A41"
STONE, STONE_EDGE = "#F4EFE7", "#DCD3C5"
FRIDGE, FRIDGE_SIDE = "#F6B8A0", "#E29C83"
MACHINE, MACHINE_SIDE = "#3B3F4A", "#2B2E36"
COFFEE = "#5A3420"
COUNTER_TOP = 352.0
_COUNTER_A = (-1100.0, 250.0)
STOOL_TOP = (800.0, 1335.0, 118.0, 46.0)  # the stool cushion's centre and radii in output pixels
STOOL_FLOOR = 1490.0


def _counter(cv: Canvas, g) -> None:
    """Base cabinets with doors and drawers under a stone top, the tiled splashback and wall cabinets above."""
    a0, a1 = _COUNTER_A
    tiles = wall_quad("back", a0, a1, COUNTER_TOP, 470)
    _quad(cv, g, tiles, "#FFFFFF", BREAK.line, 3)
    for a in range(int(a0), int(a1), 40):
        _line(cv, g, room_point(a, 0, COUNTER_TOP), room_point(a, 0, 470), STONE_EDGE, 2)
    for u in range(int(COUNTER_TOP) + 39, 470, 39):
        _line(cv, g, room_point(a0, 0, u), room_point(a1, 0, u), STONE_EDGE, 2)
    _, ca0, ca1, cu0, cu1 = WALL_DECOR["break-cabinets"]
    _block(cv, g, (a0, ca1), (0, 90), (cu0, cu1), (CABINET, CABINET, CABINET_SIDE), CABINET_LINE)
    for a in range(int(ca1) - 130, int(a0), -130):
        _quad(
            cv,
            g,
            [
                room_point(a + 10, 90, cu0 + 12),
                room_point(a + 120, 90, cu0 + 12),
                room_point(a + 120, 90, cu1 - 12),
                room_point(a + 10, 90, cu1 - 12),
            ],
            CABINET,
            CABINET_LINE,
            2.5,
        )
        hx, hy = room_point(a + 108, 90, cu0 + 40)
        cv.rect(g, hx - 4, hy - 26, 8, 28, CHROME, cv.ink, 2.5, radius=4)
    _block(cv, g, (a0, a1), (0, 150), (0, 18), ("#2E3A35",) * 3, CABINET_LINE)  # the toe kick
    _block(cv, g, (a0, a1), (0, 150), (18, COUNTER_TOP - 22), (CABINET, CABINET, CABINET_SIDE), CABINET_LINE)
    for a in range(int(a1) - 160, int(a0), -160):
        for u_lo, u_hi in ((30, COUNTER_TOP - 92), (COUNTER_TOP - 82, COUNTER_TOP - 34)):  # a door, a drawer
            _quad(
                cv,
                g,
                [
                    room_point(a + 10, 150, u_lo),
                    room_point(a + 150, 150, u_lo),
                    room_point(a + 150, 150, u_hi),
                    room_point(a + 10, 150, u_hi),
                ],
                CABINET,
                CABINET_LINE,
                2.5,
            )
        hx, hy = room_point(a + 80, 150, COUNTER_TOP - 58)
        cv.rect(g, hx - 22, hy - 4, 44, 8, CHROME, cv.ink, 2.5, radius=4)
    _block(
        cv, g, (a0, a1 + 12), (0, 166), (COUNTER_TOP - 22, COUNTER_TOP), (STONE, STONE_EDGE, STONE_EDGE), CABINET_LINE
    )
    _line(cv, g, room_point(a0, 160, COUNTER_TOP), room_point(a1 + 6, 160, COUNTER_TOP), "#FFFFFF", 4)


@register(
    "prop",
    "soft-coffee-machine",
    summary="A drip coffee machine on the break-room counter: tower, hood with a lit button, a glass carafe half "
    "full, and a mug steaming beside it",
    examples=('from srstudio import get\nmachine = get("prop", "soft-coffee-machine")(ep.cv, ep.comp)',),
    contract=bdc.contract('soft-coffee-machine'),
)
def coffee_machine(cv: Canvas, parent, id: str = "soft-coffee-machine"):
    g = cv.group(parent, id)
    a0, a1, c0, c1, base = -290.0, -160.0, 26.0, 116.0, COUNTER_TOP
    _shadow(cv, g, *room_point((a0 + a1) / 2, (c0 + c1) / 2, base), 90, 22, 0.14)
    _block(cv, g, (a0, a1), (c0, c0 + 44), (base, base + 220), (MACHINE, MACHINE, MACHINE_SIDE), cv.ink)  # tower
    _block(cv, g, (a0, a1), (c0 + 44, c1), (base, base + 16), (MACHINE, MACHINE, MACHINE_SIDE), cv.ink)  # plate
    _block(cv, g, (a0, a1), (c0 + 44, c1), (base + 170, base + 220), (MACHINE, MACHINE, MACHINE_SIDE), cv.ink)  # hood
    bx, by = room_point(a1 - 26, c1, base + 195)
    cv.ellipse(g, bx - 7, by - 7, 14, 14, "#7ED957", cv.ink, 2)
    gx, gy = room_point((a0 + a1) / 2 - 8, c0 + 80, base + 16)
    cv.path(
        g,
        f"M {gx - 38:.1f} {gy - 112:.1f} L {gx + 38:.1f} {gy - 112:.1f} Q {gx + 50:.1f} {gy - 40:.1f} "
        f"{gx + 34:.1f} {gy:.1f} L {gx - 34:.1f} {gy:.1f} Q {gx - 50:.1f} {gy - 40:.1f} {gx - 38:.1f} {gy - 112:.1f} Z",
        "#D9ECF2",
        cv.ink,
        3.5,
        opacity=0.9,
    )
    cv.path(
        g,
        f"M {gx - 45:.1f} {gy - 52:.1f} L {gx + 45:.1f} {gy - 52:.1f} Q {gx + 44:.1f} {gy - 24:.1f} "
        f"{gx + 34:.1f} {gy - 2:.1f} L {gx - 34:.1f} {gy - 2:.1f} "
        f"Q {gx - 44:.1f} {gy - 24:.1f} {gx - 45:.1f} {gy - 52:.1f} Z",
        COFFEE,
    )
    cv.path(
        g,
        f"M {gx + 40:.1f} {gy - 96:.1f} Q {gx + 74:.1f} {gy - 90:.1f} {gx + 66:.1f} {gy - 54:.1f} "
        f"Q {gx + 60:.1f} {gy - 32:.1f} {gx + 42:.1f} {gy - 30:.1f}",
        stroke=cv.ink,
        sw=6,
    )
    _line(cv, g, (gx - 24, gy - 100), (gx - 30, gy - 62), "#FFFFFF", 5, opacity=0.85)
    mx, my = room_point(-370, 96, base)
    cv.rect(g, mx - 26, my - 52, 52, 52, "#E8695A", cv.ink, 3.5, radius=8)
    cv.path(
        g,
        f"M {mx + 24:.1f} {my - 40:.1f} Q {mx + 46:.1f} {my - 36:.1f} {mx + 24:.1f} {my - 14:.1f}",
        stroke=cv.ink,
        sw=5,
    )
    cv.ellipse(g, mx - 26, my - 60, 52, 16, COFFEE, cv.ink, 3)
    for k, dx in enumerate((-10, 10)):  # steam
        cv.path(
            g,
            f"M {mx + dx:.1f} {my - 70:.1f} Q {mx + dx - 14:.1f} {my - 92:.1f} {mx + dx:.1f} {my - 112:.1f} "
            f"Q {mx + dx + 14:.1f} {my - 132:.1f} {mx + dx:.1f} {my - 152 + 10 * k:.1f}",
            stroke="#FFFFFF",
            sw=5,
            opacity=0.75,
        )
    return g


FRIDGE_BOX = (330.0, 500.0, 6.0, 150.0, 620.0)  # along, out, up: its top clears the captions


@register(
    "prop",
    "soft-fridge",
    summary="A rounded pastel fridge against the break-room wall: freezer and fridge doors, chrome handles, magnets "
    "and a sticky note",
    contract=bdc.contract('soft-fridge'),
)
def fridge(cv: Canvas, parent, id: str = "soft-fridge"):
    g = cv.group(parent, id)
    a0, a1, c0, c1, height = FRIDGE_BOX
    _quad(cv, g, floor_quad(a0 - 10, a1 + 10, c0, c1 + 26), cv.ink, opacity=0.12)
    _block(cv, g, (a0, a1), (c0, c1), (12, height), (FRIDGE, FRIDGE, FRIDGE_SIDE), cv.ink)
    _block(cv, g, (a0 + 14, a1 - 14), (c0, c1), (0, 12), ("#2B2E36",) * 3, cv.ink, sw=3)
    split = 420.0
    _line(cv, g, room_point(a0, c1, split), room_point(a1, c1, split), cv.ink, 4)
    for u0, u1 in ((split - 200, split - 30), (split + 40, split + 160)):
        p, q = room_point(a0 + 24, c1, u0), room_point(a0 + 24, c1, u1)
        cv.rect(g, p[0] - 7, q[1], 14, p[1] - q[1], CHROME, cv.ink, 3, radius=7)
    _line(cv, g, room_point(a1 - 18, c1, height - 40), room_point(a1 - 18, c1, 60), "#FFFFFF", 5, opacity=0.5)
    for (a, u), colour in (((420, 540), "#5D8FD0"), ((455, 575), LEAF), ((395, 470), "#F2C94C")):
        x, y = room_point(a, c1, u)
        cv.ellipse(g, x - 10, y - 10, 20, 20, colour, cv.ink, 2.5)
    _quad(
        cv,
        g,
        [room_point(430, c1, 370), room_point(490, c1, 370), room_point(490, c1, 300), room_point(430, c1, 300)],
        "#FFE58A",
        cv.ink,
        2.5,
    )  # a sticky note, scribbled
    for k in (1, 2, 3):
        _line(
            cv, g, room_point(438, c1, 370 - 16 * k), room_point(480 - 8 * k, c1, 370 - 16 * k), cv.ink, 2, opacity=0.6
        )
    return g


@register(
    "prop",
    "soft-stool",
    summary="A cushioned stool on a chrome stem with a foot ring, its seat at the office chair's height, so "
    "seated poses (lounge) fit it",
    contract=bdc.contract('soft-stool'),
)
def stool(cv: Canvas, parent, id: str = "soft-stool"):
    g = cv.group(parent, id)
    cx, cy, rx, ry = STOOL_TOP
    _shadow(cv, g, cx, STOOL_FLOOR, 110, 26)
    cv.ellipse(g, cx - 80, STOOL_FLOOR - 24, 160, 40, CHROME_DARK, cv.ink, 4)
    cv.ellipse(g, cx - 80, STOOL_FLOOR - 30, 160, 40, CHROME, cv.ink, 4)
    cv.rect(g, cx - 12, cy + 20, 24, STOOL_FLOOR - cy - 30, CHROME, cv.ink, 4, radius=6)
    _line(cv, g, (cx - 4, cy + 30), (cx - 4, STOOL_FLOOR - 30), "#FFFFFF", 3, opacity=0.8)
    cv.ellipse(g, cx - 66, STOOL_FLOOR - 112, 132, 40, cv.clear, cv.ink, 12)  # the foot ring
    cv.ellipse(g, cx - 66, STOOL_FLOOR - 112, 132, 40, cv.clear, CHROME, 6)
    cv.ellipse(g, cx - rx, cy - ry + 26, 2 * rx, 2 * ry, UPHOLSTERY_SIDE, UPHOLSTERY_LINE, 4)
    cv.rect(g, cx - rx, cy, 2 * rx, 26, UPHOLSTERY_SIDE)
    _line(cv, g, (cx - rx, cy), (cx - rx, cy + 26), UPHOLSTERY_LINE, 4)
    _line(cv, g, (cx + rx, cy), (cx + rx, cy + 26), UPHOLSTERY_LINE, 4)
    cv.ellipse(g, cx - rx, cy - ry, 2 * rx, 2 * ry, UPHOLSTERY, UPHOLSTERY_LINE, 4)
    cv.path(
        g,
        f"M {cx - rx * 0.7:.1f} {cy - ry * 0.25:.1f} Q {cx - rx * 0.3:.1f} {cy - ry * 0.85:.1f} "
        f"{cx + rx * 0.2:.1f} {cy - ry * 0.75:.1f}",
        stroke="#F0A08A",
        sw=5,
        opacity=0.9,
    )
    return g


def _pendant(cv: Canvas, g, light, x: float, y: float, floor_y: float) -> None:
    """A pendant lamp hung from above the frame, and the cone of its light down to ``floor_y``."""
    _line(cv, g, (x, 0), (x, y - 46), cv.ink, 4)
    cv.path(
        g,
        f"M {x - 70:.1f} {y:.1f} Q {x - 66:.1f} {y - 52:.1f} {x:.1f} {y - 56:.1f} Q {x + 66:.1f} {y - 52:.1f} "
        f"{x + 70:.1f} {y:.1f} Z",
        "#E8695A",
        cv.ink,
        4,
    )
    cv.ellipse(g, x - 26, y - 12, 52, 24, "#FFF3C4", cv.ink, 3)
    cone = cv.grad("soft-lamp-cone", [(0, LIGHT_GLAZE), (1, LIGHT_GLAZE + "00")], (0, 0, 0, 1))  # fades as it falls
    _quad(cv, light, [(x - 56, y + 4), (x + 56, y + 4), (x + 200, floor_y), (x - 200, floor_y)], cone, opacity=0.4)


@register(
    "location",
    "soft-break-room",
    summary="A polished break room in the office's 3/4 view: butter walls, a tiled floor, mint cabinets under a "
    "stone counter with a tiled splashback, a coffee machine and a steaming mug, wall cabinets, a window with a herb "
    "pot, a pastel fridge, a pendant lamp and its light, a stool at the office chair's seat height, and the "
    "signature cactus",
    contract=bdc.contract('soft-break-room', room_point=room_point, wall_quad=wall_quad, floor_quad=floor_quad),
)
def break_room(cv: Canvas, parent, *, shots: Sequence[tuple[float, float]] | None = None, id: str = "soft-break-room"):
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    _shell(cv, g, id, BREAK, tiles=True)
    decor = cv.group(g, f"{id}-decor")
    _, w0, w1, u0, u1 = WALL_DECOR["break-window"]
    _window(
        cv,
        decor,
        "back",
        w0,
        w1,
        u0,
        u1,
        cv.grad("soft-sky-warm", [(0, "#BFE0F2"), (1, "#F6EBD5")]),
        "#FBF7F0",
        BREAK.line,
    )
    px, py = room_point(w0 + 50, 0, u0 - 10)  # a herb pot on the sill
    cv.path(
        g,
        f"M {px - 22:.1f} {py - 40:.1f} L {px + 22:.1f} {py - 40:.1f} L {px + 16:.1f} {py:.1f} L {px - 16:.1f} "
        f"{py:.1f} Z",
        "#D9825B",
        cv.ink,
        3,
    )
    for dx, tip in ((-14, -92), (0, -110), (14, -88)):
        cv.path(
            g,
            f"M {px + dx * 0.4:.1f} {py - 40:.1f} Q {px + dx * 2.2:.1f} {py + tip * 0.6:.1f} {px + dx:.1f} "
            f"{py + tip:.1f} Q {px + dx * 0.2:.1f} {py + tip * 0.6:.1f} {px + dx * 0.4:.1f} {py - 40:.1f} Z",
            LEAF,
            cv.ink,
            3,
        )
    light = cv.group(g, f"{id}-light")
    # The window's light clears the counter and falls on the floor in front of it: a window point (a, up) lands
    # at (a - 0.3 up, 0.8 up).
    patch = [room_point(a - 0.3 * u, 0.8 * u) for a, u in ((w0, u0), (w1, u0), (w1, u1), (w0, u1))]
    _quad(cv, light, patch, LIGHT_GLAZE, opacity=0.26)
    signature.cactus(cv, decor, *room_point(w1 - 40, 0, u0 - 10), 0.5)  # on the sill, beside the herbs
    furniture = cv.group(g, f"{id}-furniture")
    _counter(cv, furniture)
    coffee_machine(cv, furniture, _part(id, "soft-break-room", "coffee-machine", "soft-coffee-machine"))
    fridge(cv, furniture, _part(id, "soft-break-room", "fridge", "soft-fridge"))
    stool(cv, furniture, _part(id, "soft-break-room", "stool", "soft-stool"))
    lamp_light = cv.group(g, f"{id}-lamp-light")  # the lamp's glaze lies over the counter it lights
    _pendant(cv, furniture, lamp_light, *room_point(-100, 90, 740), wall_base(room_point(-100, 90)[0]) + 60)
    signature.code(cv, g, *room_point(-760, 620), 14, color=BREAK.grain, angle=-12)
    return g
