"""The anchors' arms from version 5: two bones of fixed length on a shoulder that stays put (ADR 0071).

A pose names where a wrist goes, and the elbow follows from the lengths, so no pose can stretch an arm or bend it
sharper than :data:`ELBOW_LEAST`. A change of pose eases both joints over :data:`EASE` either side of its beat, so an
arm travels between holds and never jumps. A sleeve is two tubes with no ink around its root: the shoulder is the
jacket's, and the sleeve grows out of it. This module holds the geometry; :mod:`srstudio.news_inked` draws it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .brush import Point
from .news_kit import ARMS, NewsKitError, Pose

ELBOW_LEAST = 65.0  # the sharpest elbow a pose may hold, inside the bend, in degrees
EASE = 0.14  # seconds either side of a beat that a change of pose takes
TAPER, OUTER_TAPER = 40.0, 22.0  # how far along the upper arm a sleeve's ink takes to reach its weight: chest, outside
JOINTS = ("upper", "bend", "palm")


@dataclass(frozen=True)
class Build:
    """An anchor's arm, the same in every pose: a shoulder joint for the arm on the frame's right, mirrored for the
    other, its two lengths, the sleeve's half width at the shoulder, elbow and wrist, and the size of the hand."""

    shoulder: Point
    upper: float
    fore: float
    root: float
    elbow: float
    wrist: float
    hand: float


@dataclass(frozen=True)
class Reach:
    """Where a pose puts a wrist, on the anchor's own axes. ``hand`` is the shape held and ``turn`` its fingers in
    degrees clockwise of up. ``tucked`` keeps the elbow out and low, with the forearm coming back across the body;
    otherwise the forearm goes away from it, with the elbow on the far side of the line from shoulder to wrist."""

    wrist: Point
    hand: str
    turn: float
    tucked: bool = True


@dataclass(frozen=True)
class Hold:
    """One arm in one pose. ``upper`` and ``bend`` are the keyed joints, in degrees: the upper arm clockwise of up and
    the forearm clockwise of the upper arm, in 0 to 360 on the frame's left arm so that an elbow closes through 180 and
    never straightens through 0 on its way between the two kinds of pose. ``palm`` is the hand on the forearm."""

    upper: float
    bend: float
    palm: float
    hand: str


# The arm on the side of the frame each shape is drawn for: a palm to the camera has its thumb inward, so ``open`` is
# the hand on the frame's right, and the other three are the frame's left with the thumb on top.
DRAWN_FOR: Mapping[str, float] = MappingProxyType({"open": 1.0, "fist": -1.0, "rest": -1.0, "point": -1.0})


@dataclass(frozen=True)
class Hand:
    """One of a pair of hands, from version 6: a shape and the arm it hangs on. The hand on the other arm is the same
    drawing mirrored, so a thumb follows its side and the two can never be the same hand."""

    kind: str
    side: float

    def __post_init__(self) -> None:
        if self.kind not in DRAWN_FOR:
            raise NewsKitError(f"no hand drawn as {self.kind!r}")
        if self.side not in (-1.0, 1.0):
            raise NewsKitError(f"a hand is on the frame's left (-1) or right (1), not {self.side}")

    @property
    def mirrored(self) -> bool:
        return self.side != DRAWN_FOR[self.kind]

    def on(self, side: float) -> Hand:
        """This hand once it is placed on the arm on ``side``. Only its own arm takes it."""
        if side != self.side:
            raise NewsKitError(f"the {self.kind} hand of the arm on side {self.side} was placed on side {side}")
        return self


Keys = tuple[tuple[float, float], ...]
BUILDS: Mapping[str, Build] = MappingProxyType(
    {
        "vera": Build((164.0, -96.0), 108.0, 126.0, 32.0, 28.0, 23.0, 0.92),
        "gus": Build((166.0, -96.0), 112.0, 128.0, 32.0, 29.0, 23.0, 1.0),
    }
)
_DESK = Reach((-96.0, 14.0), "rest", 98.0)
_DESK_RIGHT = Reach((96.0, 14.0), "rest", -98.0)
REACHES: Mapping[str, Mapping[str, tuple[Reach, Reach]]] = MappingProxyType(
    {
        "vera": MappingProxyType(  # her hands stay where they are: it is the news that moves
            dict.fromkeys(ARMS, (Reach((-92.0, 14.0), "rest", 98.0), Reach((92.0, 14.0), "rest", -98.0)))
        ),
        "gus": MappingProxyType(
            {
                "rest": (_DESK, _DESK_RIGHT),
                "up": (Reach((-258.0, -196.0), "open", -8.0, False), Reach((258.0, -196.0), "open", 8.0, False)),
                "chest": (_DESK, Reach((54.0, -30.0), "fist", -52.0)),
                "point": (Reach((-296.0, -56.0), "point", -80.0, False), _DESK_RIGHT),
                "phone": (Reach((-68.0, -2.0), "fist", 84.0), Reach((68.0, -2.0), "fist", -84.0)),
            }
        ),
    }
)
# The jackets from version 5: the same width at the shoulder, a slope from the neck, and sides that come in to the desk.
TORSOS: Mapping[str, tuple[Point, ...]] = MappingProxyType(
    {
        "vera": (
            (-192, 60),
            (-200, -20),
            (-209, -78),
            (-200, -110),
            (-172, -134),
            (-136, -143),
            (-94, -150),
            (-62, -158),
            (-44, -166),
            (0, -120),
            (44, -166),
            (62, -158),
            (94, -150),
            (136, -143),
            (172, -134),
            (200, -110),
            (209, -78),
            (200, -20),
            (192, 60),
        ),
        "gus": (
            (-188, 60),
            (-197, -20),
            (-203, -78),
            (-197, -110),
            (-176, -132),
            (-138, -143),
            (-96, -150),
            (-66, -158),
            (-48, -168),
            (-4, -110),
            (52, -166),
            (68, -156),
            (96, -150),
            (138, -143),
            (176, -132),
            (197, -110),
            (203, -78),
            (197, -20),
            (188, 60),
        ),
    }
)


def _heading(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[0] - a[0], a[1] - b[1]))


def _wrap(angle: float) -> float:
    """``angle`` in -180 to 180."""
    return (angle + 180.0) % 360.0 - 180.0


def elbow_of(build: Build, side: float, reach: Reach) -> Point:
    """Where the lengths of ``build`` put the elbow of the arm on ``side`` (-1 the frame's left) for ``reach``."""
    sx, sy = build.shoulder[0] * side, build.shoulder[1]
    dx, dy = reach.wrist[0] - sx, reach.wrist[1] - sy
    span = math.hypot(dx, dy)
    if not abs(build.upper - build.fore) < span < build.upper + build.fore:
        raise NewsKitError(f"an arm of {build.upper} and {build.fore} cannot reach {reach.wrist}")
    along = (build.upper**2 - build.fore**2 + span**2) / (2 * span)
    off = math.sqrt(build.upper**2 - along**2)
    way = -side if reach.tucked else side  # looking from the shoulder to the wrist, the side the elbow is on
    ux, uy = dx / span, dy / span
    return sx + ux * along + way * uy * off * -1, sy + uy * along + way * ux * off


def hold_of(build: Build, side: float, reach: Reach) -> Hold:
    """The joints of ``reach`` on the arm on ``side``. The arm on the frame's right is the mirror of the left."""
    shoulder = (build.shoulder[0] * side, build.shoulder[1])
    elbow = elbow_of(build, side, reach)
    fore = _heading(elbow, reach.wrist)
    upper = _heading(shoulder, elbow)
    bend = (-side * (fore - upper)) % 360.0
    down = (-side * upper - 90.0) % 360.0 - 270.0  # on the frame's left arm: -270 to 90, so that no key crosses a wrap
    return Hold(-side * down, -side * bend, _wrap(reach.turn - fore), reach.hand)


def holds(who: str, side: float) -> dict[str, Hold]:
    """Every pose of the arm of ``who`` on ``side``."""
    index = 0 if side < 0 else 1
    return {state: hold_of(BUILDS[who], side, pair[index]) for state, pair in REACHES[who].items()}


def keys_of(who: str, side: float, acts: Sequence[tuple[float, Pose]]) -> dict[str, Keys]:
    """The keys of each of :data:`JOINTS` through ``acts``: a hold to a change's beat, less :data:`EASE`, and the next
    pose by the beat plus it. Two changes closer than that share the time between them."""
    poses = holds(who, side)
    rows = [(at, poses[pose.arms]) for at, pose in acts]
    frames: list[tuple[float, Hold]] = [rows[0]]
    for at, hold in rows[1:]:
        if hold == frames[-1][1]:
            continue
        lead = min(EASE, (at - frames[-1][0]) / 2)
        frames += [(at - lead, frames[-1][1]), (at + lead, hold)]
    return {
        "upper": tuple((t, h.upper) for t, h in frames),
        "bend": tuple((t, h.bend) for t, h in frames),
        "palm": tuple((t, h.palm) for t, h in frames),
    }


def value_at(keys: Keys, t: float) -> float:
    """``keys`` at ``t``, eased as the scene eases them (``sine-in-out``)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, v), (b, w) in zip(keys, keys[1:], strict=False):
        if t <= b:
            part = (t - a) / (b - a) if b > a else 1.0
            return v + (w - v) * (1 - math.cos(math.pi * part)) / 2
    return keys[-1][1]


def joints_at(who: str, side: float, keys: Mapping[str, Keys], t: float) -> tuple[Point, Point, Point]:
    """Shoulder, elbow and wrist at ``t``: what the keys of :func:`keys_of` draw on the rig."""
    build = BUILDS[who]
    s = (build.shoulder[0] * side, build.shoulder[1])
    upper = value_at(keys["upper"], t)
    fore = math.radians(upper + value_at(keys["bend"], t))
    up = math.radians(upper)
    e = (s[0] + build.upper * math.sin(up), s[1] - build.upper * math.cos(up))
    return s, e, (e[0] + build.fore * math.sin(fore), e[1] - build.fore * math.cos(fore))


def _round(r: float, y: float, sweep: Sequence[int]) -> list[Point]:
    return [(r * math.sin(math.radians(a)), y - r * math.cos(math.radians(a))) for a in sweep]


def sleeve(build: Build, grow: float = 0.0, outer: float = 1.0) -> tuple[Point, ...]:
    """The upper arm up its bone from the shoulder at the origin: round at the elbow, ``grow`` wider for the ink under
    the fill. The ink starts under the fill and comes out of it, soon on the ``outer`` side (-1 the bone's left), where
    it carries on the jacket's own line, and over :data:`TAPER` on the side toward the chest. So it shows as two lines
    that begin on the jacket, the root stays open with no line across it, and the fill's root is a bare circle."""
    width = _taper(build.root, build.elbow, build.upper)
    tip = _round(build.elbow + grow, -build.upper, (-90, -60, -30, 0, 30, 60, 90))
    if not grow:
        down = [(width(k * build.upper), -k * build.upper) for k in (0.75, 0.5, 0.25)]
        return (*tip, *down, *_round(build.root, 0.0, (120, 150, 180, 210, 240)), *[(-x, y) for x, y in reversed(down)])

    def edge(taper: float) -> list[Point]:
        return [
            (build.root - 8.0, 6.0),
            (width(taper * 0.5) - 1.0, -taper * 0.5),
            (width(taper) + grow * 0.6, -taper),
            (width(taper + 24.0) + grow, -taper - 24.0),
            (width(build.upper * 0.75) + grow, -build.upper * 0.75),
        ]

    left, right = (edge(TAPER), edge(OUTER_TAPER)) if outer > 0 else (edge(OUTER_TAPER), edge(TAPER))
    return (*[(-x, y) for x, y in left], *tip, *reversed(right))


def forearm(build: Build, grow: float = 0.0) -> tuple[Point, ...]:
    """The forearm up its bone from the elbow at the origin: round there, cut square at the cuff."""
    width = _taper(build.elbow + grow, build.wrist + grow, build.fore)
    down = [(width(k * build.fore), -k * build.fore) for k in (1.0, 0.75, 0.5, 0.25, 0.08)]
    arc = _round(build.elbow + grow, 0.0, (105, 120, 150, 180, 210, 240, 255))
    cuff = -build.fore - grow
    return ((-down[0][0], cuff), (down[0][0], cuff), *down[1:], *arc, *[(-x, y) for x, y in reversed(down[1:])])


def _taper(near: float, far: float, length: float) -> Callable[[float], float]:
    return lambda y: near + (far - near) * y / length


def shade_strip(near: float, far: float, length: float, deep: float = 11.0) -> tuple[Point, ...]:
    """The shade along the right edge of a length of sleeve, ``near`` to ``far`` wide along ``length``: on the edge
    itself, deepest in the middle, and coming to nothing short of either joint."""
    width = _taper(near, far, length)
    rows = [0.16, 0.3, 0.5, 0.7, 0.86]
    out = [(width(k * length), -k * length) for k in rows]
    back = [
        (width(k * length) - deep * math.sin(math.pi * (k - 0.16) / 0.7), -k * length) for k in reversed(rows[1:-1])
    ]
    return (*out, *back)


def sheds(heading: float, edge: float, light: Point) -> bool:
    """Whether the ``edge`` of a bone (-1 its left, looking up it) at ``heading`` faces away from ``light``."""
    a = math.radians(heading)
    return (edge * math.cos(a)) * light[0] + (edge * math.sin(a)) * light[1] < -0.2
