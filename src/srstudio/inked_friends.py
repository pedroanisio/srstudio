"""Leo and Sam, two friends of about twenty on a couch, drawn the way the News anchors are (ADR 0231).

The ink is :mod:`srstudio.news_inked`'s: a pressed contour, a shade tone away from the light, open inner strokes. The
arms are its two bones of fixed length on a shoulder that stays put (:mod:`srstudio.news_arms`, ADR 0071), and every
hand is one drawing whose other is its mirror, so a thumb follows its arm (ADR 0103). What is their own:

* **Faces built to act.** An eye state (:class:`Look`) sets the top and lower lids, where the pupils go and how each
  brow's inner and outer ends sit, so a worried brow (inner end up) and a cross one (inner end down) are different
  states, and the lower lid rises for a smile that reaches the eyes. Mouths are named shapes (:data:`MOUTHS`), each one
  drawn to read at phone size: a lopsided sheepish smile, pressed lips, a gape, a soft genuine smile.
* **A face that stays alive.** Breath, blinks and a slow drift of the head run under every beat, and a performance
  adds what the scene asks: a nod (the head dips and comes back), a shrug (the shoulders rise and fall), a swallow
  (lips pressed, the chin tucks and the throat moves).
* **A controller in both hands.** Seen from the screen, each hand wraps its grip with its thumb over the top edge,
  pointing in at its stick; the other hand is the same drawing reflected (:data:`GRIP`). The thumbs press a button, the
  menu button, lie off the sticks in the lap, and one hand can let go to hold a phone up while the other keeps the
  controller in the lap.
* **Light from the screen.** :func:`screen_light` lights only the people, through a track matte on their group: the
  screen's colour, its level and a fall-off from the faces to the edges, so the room behind stays dim.

Both are version 1, proposed (ADR 0047): no reel draws either until the operator approves it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from . import _character_contracts as cc
from . import anatomy, news_arms, toon_rooms
from .anatomy import Facing, Side
from .brush import Point
from .canvas import Canvas
from .errors import SrstudioError
from .news_inked import CUFF, SLEEVE_INK, _form, _hand, _inked_oval, _line, _oval, flat
from .news_kit import PLUM_DEEP, Spans, _spans
from .registry import register
from .toon_critters import FUR, LIGHT_FROM

__all__ = [
    "FRIENDS",
    "GRIP",
    "HANDS",
    "HOLDS",
    "MOUTHS",
    "THUMBS",
    "VISEMES",
    "Beat",
    "Friend",
    "FriendsError",
    "Hold",
    "Look",
    "Moves",
    "leo",
    "perform",
    "sam",
    "screen_light",
]

NECK_Y, CHIN_Y = -170.0, -40.0  # the neck in the body's frame, and the point of the head that sits on it
FACE_SLIDE = 12.0  # pixels the face slides toward the side a head turns to
BLINK = 0.13  # seconds an eye stays shut in a blink
BREATH = 3.4  # seconds a breath takes
BREATH_PX = 2.4  # how far the chest rises
DRIFT = 1.9  # seconds between keys of the head's slow drift
EASE = 0.16  # seconds either side of a beat a change of tilt, turn or hold takes
VISEMES = ("closed", "open", "round", "teeth")
MOUTHS = ("rest", "flat", "set", "sheepish", "pressed", "gape", "smile", "smirk", "concern", *VISEMES)
HANDS = ("pad", "pad-press", "pad-pause", "pad-lap", "pad-up", "phone")
THUMBS = ("stick", "button", "menu", "rest")
GRIP: Final = anatomy.Drawing("pad-grip", Side.LEFT, Facing.BACK)  # the frame's left hand, its thumb toward the right


class FriendsError(SrstudioError, ValueError):
    """A beat, a move or a light cue the two friends cannot play as asked."""


@dataclass(frozen=True)
class Look:
    """One state of the eyes and brows. ``lid`` is how far the top lid has come down over the eye (0 open, 1 shut) and
    ``under`` how far the lower lid has risen (a smile's cheek). ``gaze`` is where the pupils go in eye radii: +x toward
    the other friend, +y down. ``brow`` lifts both brows, ``inner`` and ``outer`` lift each brow's ends on top of that
    (an inner end up is worry, down is anger), ``near`` lifts the brow on the other friend's side alone. ``wide``
    scales the eye. ``blinks`` is False for a stare that must hold."""

    lid: float
    under: float = 0.0
    gaze: Point = (0.0, 0.0)
    brow: float = 0.0
    inner: float = 0.0
    outer: float = 0.0
    near: float = 0.0
    wide: float = 1.0
    blinks: bool = True

    def __post_init__(self) -> None:
        if not (0.0 <= self.lid <= 0.75 and 0.0 <= self.under <= 0.5):
            raise FriendsError(f"a look's lid is 0..0.75 and its lower lid 0..0.5, got {self.lid}, {self.under}")
        if not all(abs(v) <= 0.45 for v in self.gaze):
            raise FriendsError(f"a look's pupils stay inside the eye, at most 0.45 radii off, got {self.gaze}")
        if not 0.8 <= self.wide <= 1.3:
            raise FriendsError(f"a look's eye scale is 0.8..1.3, got {self.wide}")


SHUT: Final = Look(lid=0.0)  # a placeholder in the tables: "shut" is drawn as a closed lid, not from these numbers


@dataclass(frozen=True)
class Face:
    """Where a friend's features sit on his head, his colours, and the side of the frame the other friend is on."""

    skin: str
    tone: str
    deep: str
    lip: str
    iris: str
    brow: str
    eye_x: float
    eye_y: float
    eye_r: float
    brow_w: float
    mouth_y: float
    mouth_w: float
    toward: float


@dataclass(frozen=True)
class Hold:
    """Where the controller is in one hold, in the body's frame, and where each thumb lies (frame left, frame right).
    A thumb of ``None`` is a hand off the controller: in ``phone`` the frame's right hand holds the phone up."""

    pad: Point
    thumbs: tuple[str | None, str | None]

    def __post_init__(self) -> None:
        if len(self.thumbs) != 2 or any(t is not None and t not in THUMBS for t in self.thumbs):
            raise FriendsError(f"a hold puts each thumb on one of {THUMBS} or off the pad, got {self.thumbs!r}")
        if self.thumbs[0] is None:
            raise FriendsError("the frame's left hand always holds the controller")


HOLDS: Final = MappingProxyType(
    {
        "pad": Hold((0.0, 34.0), ("stick", "stick")),
        "pad-press": Hold((0.0, 34.0), ("button", "stick")),  # a thumb on a face button: playing hard
        "pad-pause": Hold((0.0, 34.0), ("menu", "stick")),  # the thumb on the middle button: pause and unpause
        "pad-lap": Hold((0.0, 92.0), ("rest", "rest")),  # sunk toward the lap, thumbs off the sticks
        "pad-up": Hold((0.0, 8.0), ("stick", "stick")),  # lifted, back in the game
        "phone": Hold((-36.0, 92.0), ("rest", None)),  # one hand keeps the controller in the lap
    }
)
_GRIP_X, _GRIP_Y = 54.0, 12.0  # each grip's middle from the controller's, the frame's right one; the left mirrors it
_STICK_X, _CAP_Y = 26.0, -22.0
_TIPS: Mapping[str, Point] = MappingProxyType(  # the frame's left thumb's tip in the controller's frame
    {"stick": (-26.0, -26.0), "button": (-40.0, -26.0), "menu": (-9.0, -24.0), "rest": (-52.0, -20.0)}
)
_PHONE = news_arms.Reach((104.0, -78.0), "fist", 16.0)  # the right wrist: the phone held up toward the other


@dataclass(frozen=True)
class Beat:
    """A friend from ``at`` on: eyes (a :class:`Look` of his), a mouth (:data:`MOUTHS`, or ``"talk"`` for the viseme
    track), hands (:data:`HANDS`), the head's ``tilt`` in degrees (clockwise), its ``turn`` (-1..1, +1 toward the
    other friend) and ``lift`` (pixels the face rises: the chin up)."""

    at: float
    eyes: str
    mouth: str = "rest"
    hands: str = "pad"
    tilt: float = 0.0
    turn: float = 0.0
    lift: float = 0.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.at) and self.at >= 0):
            raise FriendsError(f"a beat starts at a second >= 0, got {self.at!r}")
        if self.mouth != "talk" and self.mouth not in MOUTHS:
            raise FriendsError(f"a mouth is 'talk' or one of {MOUTHS}, got {self.mouth!r}")
        if self.hands not in HANDS:
            raise FriendsError(f"hands are one of {HANDS}, got {self.hands!r}")
        if abs(self.tilt) > 8 or abs(self.turn) > 1 or abs(self.lift) > 10:
            raise FriendsError(f"a beat tilts at most 8 degrees, turns -1..1, lifts at most 10 px: {self!r}")


@dataclass(frozen=True)
class Moves:
    """What a performance adds over its beats: ``nods`` (second, depth in pixels: the head dips and comes back),
    ``shrugs`` (second: the shoulders rise and fall), ``swallows`` (second: the chin tucks, the throat moves) and
    ``flush`` (spans of a blush)."""

    nods: tuple[tuple[float, float], ...] = ()
    shrugs: tuple[float, ...] = ()
    swallows: tuple[float, ...] = ()
    flush: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        for at, depth in self.nods:
            if not (at >= 0 and 2.0 <= depth <= 16.0):
                raise FriendsError(f"a nod starts at a second >= 0 and dips 2..16 px, got {(at, depth)!r}")
        if any(t < 0 for t in (*self.shrugs, *self.swallows)):
            raise FriendsError("a shrug or a swallow starts at a second >= 0")
        if any(not 0 <= a < b for a, b in self.flush):
            raise FriendsError(f"a blush is a span 0 <= start < end, got {self.flush!r}")


STILL: Final = Moves()  # a performance with nothing added over its beats


@dataclass(frozen=True)
class Friend:
    """One of the two: his name, face, the looks he can give, his arm, his clothes and what is drawn of his head."""

    name: str
    face: Face
    looks: Mapping[str, Look]
    build: news_arms.Build
    sleeve: str
    sleeve_tone: str
    cuff: str
    seed: float
    head: tuple[Point, ...]
    back: tuple[Point, ...]
    hair: str
    hair_tone: str
    hair_shine: str
    ears: tuple[float, float, float]  # x, top, bottom of the frame's right ear
    neck: float
    blink_every: tuple[float, float] = field(default=(2.9, 4.4))


# -- the drawing of a face ---------------------------------------------------------------------------------------------
def _eye(cv: Canvas, parent, face: Face, side: float, look: Look, shut: bool) -> None:
    x, y = side * face.eye_x, face.eye_y
    r = face.eye_r * look.wide
    ry = r * 1.08
    if shut:
        _line(cv, parent, ((x - r - 2, y + 1), (x, y + 9), (x + r + 2, y + 1)), PLUM_DEEP, 7.0)
        return
    _inked_oval(cv, parent, x, y, r, ry, "#ffffff", 3.4)
    _oval(cv, parent, x, y + ry * 0.78, r * 0.7, r * 0.12, "#e6e3f0")
    gx, gy = look.gaze[0] * face.toward * r, look.gaze[1] * r
    size = r * (0.46 if look.wide > 1.1 else 0.58)
    _oval(cv, parent, x + gx, y + gy, size, size, face.iris)
    _oval(cv, parent, x + gx, y + gy, size * 0.55, size * 0.55, PLUM_DEEP)
    _oval(cv, parent, x + gx - size * 0.32, y + gy - size * 0.36, size * 0.3, size * 0.3, "#ffffff")
    _oval(cv, parent, x + gx + size * 0.3, y + gy + size * 0.3, size * 0.12, size * 0.12, "#ffffff")
    if look.under > 0.01:  # the lower lid rising into a crescent: the cheek of a smile that reaches the eyes
        low = y + ry - 2 * ry * look.under
        cv.path(
            parent,
            f"M {x - r - 6} {y + ry * 1.4} L {x - r - 6} {low + 6} Q {x} {low - r * 0.3} {x + r + 6} {low + 6} "
            f"L {x + r + 6} {y + ry * 1.4} Z",
            face.skin,
            cv.clear,
            0,
        )
        _line(cv, parent, ((x - r - 2, low + 5), (x, low - r * 0.22), (x + r + 2, low + 5)), face.deep, 4.0)
    if look.lid > 0.01:
        lid = y - ry + 2 * ry * look.lid
        top = y - ry * 1.4
        cv.path(
            parent,
            f"M {x - r - 6} {top} L {x + r + 6} {top} L {x + r + 6} {lid + 3} Q {x} {lid - 7} {x - r - 6} {lid + 3} Z",
            face.skin,
            cv.clear,
            0,
        )
        _line(cv, parent, ((x - r - 7, lid + 4), (x, lid - 4), (x + r + 7, lid + 4)), PLUM_DEEP, 8.0)
    else:
        _line(
            cv,
            parent,
            ((x - r * 1.15, y - ry * 0.95), (x, y - ry * 1.5), (x + r * 1.15, y - ry * 0.95)),
            PLUM_DEEP,
            5.5,
        )


def _brow(cv: Canvas, parent, face: Face, side: float, look: Look) -> None:
    x, y, r = side * face.eye_x, face.eye_y, face.eye_r
    base = y - r * 1.6 - look.brow - (r * (look.wide - 1.0) * 1.2)
    near = look.near if side == face.toward else 0.0
    inner = (x - side * r * 1.05, base + 4 - look.inner - near * 0.4)
    mid = (x + side * r * 0.1, base - 5 - (look.inner + look.outer) * 0.25 - near)
    outer = (x + side * r * 1.3, base + 6 - look.outer - near)
    _line(cv, parent, (inner, mid, outer), face.brow, face.brow_w * 1.5)


def _mouth(cv: Canvas, g, face: Face, state: str) -> None:
    y, w, t = face.mouth_y, face.mouth_w, face.toward
    lip = face.lip
    if state in ("rest", "closed"):
        _line(cv, g, ((-w * 0.42, y), (0, y + 2), (w * 0.42, y - 1)), lip, 11.0)
    elif state == "flat":  # proud and flat: a wide, firm line with the corners tucked
        _line(cv, g, ((-w * 0.56, y - 1), (0, y + 1), (w * 0.56, y - 1)), lip, 9.5)
        for s in (-1.0, 1.0):
            _line(cv, g, ((s * w * 0.6, y - 7), (s * w * 0.66, y + 1)), face.deep, 3.6)
    elif state == "set":  # a jaw held shut: a short hard line, the muscle at each hinge, the chin pushed up
        _line(cv, g, ((-w * 0.38, y), (0, y), (w * 0.38, y)), lip, 10.0)
        for s in (-1.0, 1.0):
            _line(cv, g, ((s * 90, y - 6), (s * 86, y + 14), (s * 74, y + 30)), face.deep, 5.6)
        _line(cv, g, ((-w * 0.18, y + 20), (w * 0.18, y + 20)), face.deep, 4.0)
    elif state == "sheepish":  # a lopsided closed smile, the up corner away from the other, a dimple on it
        s = -t
        _line(cv, g, ((-s * w * 0.46, y + 3), (s * w * 0.02, y + 4), (s * w * 0.44, y - 10)), lip, 9.0)
        _line(cv, g, ((s * w * 0.5, y - 18), (s * w * 0.56, y - 6)), face.deep, 4.0)
        _line(cv, g, ((-w * 0.1, y + 16), (w * 0.1, y + 16)), face.deep, 3.4)
    elif state == "pressed":  # lips pressed in: a thick short line, corners down, the chin's knot under it
        _line(cv, g, ((-w * 0.36, y + 4), (0, y - 1), (w * 0.36, y + 4)), lip, 11.0)
        _line(cv, g, ((-w * 0.18, y + 16), (0, y + 21), (w * 0.18, y + 16)), face.deep, 4.2)
    elif state == "gape":  # horror: a tall open mouth, the top teeth, the tongue
        h, half = 50.0, w * 0.38
        cv.path(
            g,
            f"M {-half} {y - 10} Q 0 {y - 20} {half} {y - 10} Q {half * 1.1} {y + h * 0.7} 0 {y + h} "
            f"Q {-half * 1.1} {y + h * 0.7} {-half} {y - 10} Z",
            "#4a1420",
            PLUM_DEEP,
            6.0,
        )
        cv.path(
            g,
            f"M {-half * 0.8} {y - 11} Q 0 {y - 18} {half * 0.8} {y - 11} L {half * 0.72} {y - 1} "
            f"Q 0 {y - 5} {-half * 0.72} {y - 1} Z",
            "#ffffff",
            cv.clear,
            0,
        )
        _oval(cv, g, 0, y + h * 0.74, half * 0.6, h * 0.17, "#d9586e")
    elif state == "smile":  # a soft genuine smile: the corners up, closed, the cheeks round under the eyes
        _line(cv, g, ((-w * 0.5, y - 9), (-w * 0.2, y + 5), (w * 0.2, y + 5), (w * 0.5, y - 9)), lip, 9.0)
        for s in (-1.0, 1.0):
            _line(cv, g, ((s * w * 0.6, y - 26), (s * w * 0.66, y - 12), (s * w * 0.6, y - 2)), face.deep, 4.0)
        _line(cv, g, ((-w * 0.14, y + 18), (w * 0.14, y + 18)), face.deep, 3.4)
    elif state == "smirk":  # dry: one corner up, toward the other
        _line(cv, g, ((-t * w * 0.44, y + 2), (t * w * 0.08, y + 3), (t * w * 0.48, y - 9)), lip, 9.0)
        _line(cv, g, ((t * w * 0.54, y - 16), (t * w * 0.58, y - 5)), face.deep, 3.6)
    elif state == "concern":  # gentle: a soft line with the corners a little down, the lips just apart
        _line(cv, g, ((-w * 0.38, y + 5), (0, y - 1), (w * 0.38, y + 5)), lip, 8.0)
        _oval(cv, g, 0, y + 4, w * 0.1, 2.6, "#4a1420")
    elif state == "open":
        _inked_oval(cv, g, 0, y + 8, w * 0.3, 15.0, "#4a1420", 5.0)
        _oval(cv, g, 0, y + 15, w * 0.18, 5.0, "#d9586e")
    elif state == "round":
        _inked_oval(cv, g, 0, y + 6, w * 0.16, 15.0, "#4a1420", 5.0)
    elif state == "teeth":
        cv.path(
            g,
            f"M {-w * 0.4} {y - 6} Q 0 {y - 11} {w * 0.4} {y - 6} Q {w * 0.42} {y + 14} 0 {y + 18} "
            f"Q {-w * 0.42} {y + 14} {-w * 0.4} {y - 6} Z",
            "#4a1420",
            PLUM_DEEP,
            5.0,
        )
        cv.path(
            g,
            f"M {-w * 0.32} {y - 6} Q 0 {y - 10} {w * 0.32} {y - 6} L {w * 0.27} {y + 3} L {-w * 0.27} {y + 3} Z",
            "#ffffff",
            cv.clear,
            0,
        )
    else:  # pragma: no cover - MOUTHS is closed and Beat checks it
        raise FriendsError(f"no mouth {state!r}")


# -- the timeline ------------------------------------------------------------------------------------------------------
def _check(friend: Friend, beats: Sequence[Beat], end: float) -> None:
    if not (math.isfinite(end) and end > 0):
        raise FriendsError(f"a performance ends after 0 s, got {end!r}")
    if not beats or beats[0].at != 0.0:
        raise FriendsError(f"{friend.name}'s first beat is at 0 s, got {beats[:1]!r}")
    if any(b.at <= a.at for a, b in zip(beats, beats[1:], strict=False)):
        raise FriendsError(f"{friend.name}'s beats go forward in time")
    if beats[-1].at >= end:
        raise FriendsError(f"{friend.name}'s last beat starts before the end, {end}")
    for beat in beats:
        if beat.eyes not in friend.looks:
            raise FriendsError(f"{friend.name} has no look {beat.eyes!r}: his looks are {tuple(friend.looks)}")
        if beat.hands == "phone" and friend.face.toward < 0:
            raise FriendsError(f"{friend.name} is on the frame's right: the phone is held by the friend on the left")


def _blinks(friend: Friend, beats: Sequence[Beat], end: float) -> list[tuple[float, str]]:
    """The eye track: each beat's look and a blink every few seconds on a fixed rhythm seeded by the friend, except
    inside a look that holds its stare and where a blink would run past the beat's end."""
    looks = [(b.at, b.eyes) for b in beats]
    rows = list(looks)
    low, high = friend.blink_every
    t, k = 0.7 + (friend.seed % 7) * 0.13, 0
    while t < end - BLINK:
        state = next(e for at, e in reversed(looks) if at <= t)
        until = next((at for at, _ in looks if at > t), end)
        if friend.looks[state].blinks and t + BLINK < until:
            rows += [(t, "shut"), (t + BLINK, state)]
        k += 1
        t += low + (high - low) * ((math.sin(friend.seed * 3.1 + k * 2.3) + 1) / 2)
    return sorted(rows)


def _mouth_track(beats: Sequence[Beat], mouths: Sequence[tuple[float, str]], end: float) -> list[tuple[float, str]]:
    rows: list[tuple[float, str]] = []
    for beat, nxt in zip(beats, [*beats[1:], None], strict=True):
        stop = nxt.at if nxt else end
        if beat.mouth != "talk":
            rows.append((beat.at, beat.mouth))
            continue
        inside = [(t, v) for t, v in mouths if beat.at <= t < stop]
        before = [v for t, v in mouths if t < beat.at]
        rows.append((beat.at, before[-1] if before else "closed"))
        rows += inside
    for _, v in mouths:
        if v not in VISEMES:
            raise FriendsError(f"a viseme is one of {VISEMES}, got {v!r}")
    return rows


def _eased(beats: Sequence[Beat], value) -> list[tuple[float, float]]:
    """Keys of ``value(beat)`` that hold through each beat and ease into the next over :data:`EASE` either side."""
    keys = [(0.0, value(beats[0]))]
    for prev, beat in zip(beats, beats[1:], strict=False):
        if value(beat) == value(prev):
            continue
        lead = min(EASE, (beat.at - prev.at) / 2)
        keys += [(beat.at - lead, value(prev)), (beat.at + lead, value(beat))]
    return keys


def _breath(end: float, seed: float) -> list[tuple[float, float]]:
    phase = (seed % 5) * 0.4
    return [(round(t, 3), round(-BREATH_PX * (1 - math.cos(2 * math.pi * (t + phase) / BREATH)) / 2, 3))
            for t in [i * 0.3 for i in range(int(end / 0.3) + 2)]]  # fmt: skip


def _drift(end: float, seed: float, size: float) -> list[tuple[float, float]]:
    return [(round(i * DRIFT, 3), round(size * math.sin(seed * 1.7 + i * 2.1) * math.cos(seed + i * 0.9), 3))
            for i in range(int(end / DRIFT) + 2)]  # fmt: skip


def _pulse(times: Sequence[float], rise: float, hold: float, fall: float, amount: float, start: float = 0.0):
    keys = [(0.0, start)]
    for t in sorted(times):
        keys += [
            (t, start),
            (t + rise, start + amount),
            (t + rise + hold, start + amount),
            (t + rise + hold + fall, start),
        ]
    return keys


def _nods(nods: Sequence[tuple[float, float]], swallows: Sequence[float]) -> list[tuple[float, float]]:
    """The head's dip: each nod goes down in 0.22 s and comes back in 0.34 s; a swallow tucks the chin 6 px."""
    events = sorted([(t, d, 0.22, 0.06, 0.34) for t, d in nods] + [(t, 6.0, 0.16, 0.18, 0.3) for t in swallows])
    keys = [(0.0, 0.0)]
    for t, depth, down, hold, up in events:
        if t < keys[-1][0]:
            raise FriendsError(f"a nod or swallow at {t} s starts before the one before it is over")
        keys += [(t, 0.0), (t + down, depth), (t + down + hold, depth), (t + down + hold + up, 0.0)]
    return keys


def _key(cv: Canvas, node, prop: str, keys: Sequence[tuple[float, float]], end: float, rest: float = 0.0) -> None:
    """Key ``prop`` of ``node`` through ``keys`` up to ``end``; a value that never leaves ``rest`` (where the node was
    created) adds nothing, and one that holds elsewhere is held there from 0 to the end."""
    inside = [(t, v) for t, v in keys if t <= end]
    if {v for _, v in inside} == {rest}:
        return
    if len(inside) == 1:
        inside = [inside[0], (end, inside[0][1])]
    cv.keys(node, prop, inside, hold=False, kind="sine-in-out", local=False)


# -- the body, the arms, the controller --------------------------------------------------------------------------------
def _holds(friend: Friend, side: float) -> dict[str, news_arms.Hold]:
    out = {}
    for name, hold in HOLDS.items():
        if name == "phone" and side > 0:
            reach = _PHONE
        else:
            px, py = hold.pad
            reach = news_arms.Reach((px + side * (_GRIP_X + 14.0), py + _GRIP_Y + 16.0), "fist", side * -40.0)
        out[name] = news_arms.hold_of(friend.build, side, reach)
    return out


def _arm_keys(friend: Friend, side: float, beats: Sequence[Beat]) -> dict[str, list[tuple[float, float]]]:
    holds = _holds(friend, side)
    return {joint: _eased(beats, lambda b, j=joint: getattr(holds[b.hands], j)) for joint in ("upper", "bend", "palm")}


def _bones(cv: Canvas, parent, build: news_arms.Build, side: float, keys, end: float):
    upper = cv.group(parent, cv.uid("arm"), x=build.shoulder[0] * side, y=build.shoulder[1], anchorX=0.0, anchorY=0.0)
    _key(cv, upper, "rotation", keys["upper"], end)
    fore = cv.group(upper, cv.uid("forearm"), x=0.0, y=-build.upper, anchorX=0.0, anchorY=0.0)
    _key(cv, fore, "rotation", keys["bend"], end)
    return upper, fore


def _arm(cv: Canvas, parent, friend: Friend, side: float, beats, spans: Mapping[str, Spans], end: float) -> None:
    """One arm: the phone and its hand under the sleeve when this arm holds it, then the sleeve's ink, then its fill,
    so one line runs round the whole arm (news_inked's order)."""
    build = friend.build
    keys = _arm_keys(friend, side, beats)
    _, fore = _bones(cv, parent, build, side, keys, end)
    if side > 0 and "phone" in spans:
        wrist = cv.group(fore, cv.uid("wrist"), x=0.0, y=-build.fore - CUFF, anchorX=0.0, anchorY=0.0)
        _key(cv, wrist, "rotation", keys["palm"], end)
        g = cv.group(wrist, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans["phone"])
        _phone(cv, g)
        mirrored = news_arms.Hand("fist", side).on(side).mirrored
        _hand(cv, g, "fist", (0.0, 0.0), 0.0, friend.face.skin, friend.face.tone, build.hand, friend.seed + 3, mirrored)
    tip = -build.fore
    _form(cv, fore, ((-25, tip - CUFF), (25, tip - CUFF), (26, tip + 8), (-26, tip + 8)), friend.cuff, None,
          friend.seed + 2, 5.0, amount=0.2)  # fmt: skip
    upper, fore = _bones(cv, parent, build, side, keys, end)
    flat(cv, upper, _outline(news_arms.sleeve(build, SLEEVE_INK, -side)), PLUM_DEEP)
    flat(cv, fore, _outline(news_arms.forearm(build, SLEEVE_INK)), PLUM_DEEP)
    upper, _ = _bones(cv, parent, build, side, keys, end)
    _, fore = _bones(cv, parent, build, side, keys, end)
    holds = _holds(friend, side)
    for bone, drawn, near, far, length, turn in (
        (upper, news_arms.sleeve(build), build.root, build.elbow, build.upper, lambda h: h.upper),
        (fore, news_arms.forearm(build), build.elbow, build.wrist, build.fore, lambda h: h.upper + h.bend),
    ):
        flat(cv, bone, _outline(drawn), friend.sleeve)
        for edge in (-1.0, 1.0):
            when = [s for st, h in holds.items() if st in spans and news_arms.sheds(turn(h), edge, LIGHT_FROM)
                    for s in spans[st]]  # fmt: skip
            if when:
                g = cv.group(bone, cv.uid("g"), opacity=0.0, scaleX=edge)
                cv.gate(g, when)
                flat(cv, g, _outline(news_arms.shade_strip(near, far, length)), friend.sleeve_tone)


def _outline(points):
    from . import brush

    return brush.outline(points, steps=3)


def _phone(cv: Canvas, g) -> None:
    """A plain phone in the fist, turned toward the other friend: its back to us, no maker's mark."""
    p = cv.group(g, cv.uid("g"), rotation=-6.0)
    _form(cv, p, ((-38, -196), (38, -196), (44, -188), (44, -40), (36, -32), (-36, -32), (-44, -40), (-44, -188)),
          "#3a3352", "#241e38", 241.0, 6.5, depth=12.0, amount=0.2)  # fmt: skip
    _inked_oval(cv, p, -20, -172, 9, 9, "#5a5274", 3.4)
    _inked_oval(cv, p, -20, -146, 9, 9, "#5a5274", 3.4)
    _line(cv, p, ((46, -186), (46, -44)), "#9fd0ff", 6.0)  # the lit edge of its screen, turned toward the other


_PAD_BODY: tuple[Point, ...] = (
    (-50.0, -18.0), (-25.0, -20.0), (0.0, -20.0), (25.0, -20.0), (50.0, -18.0), (62.0, -10.0), (68.0, 4.0),
    (66.0, 20.0), (58.0, 34.0), (46.0, 38.0), (36.0, 30.0), (30.0, 18.0), (16.0, 11.0), (0.0, 10.0), (-16.0, 11.0),
    (-30.0, 18.0), (-36.0, 30.0), (-46.0, 38.0), (-58.0, 34.0), (-66.0, 20.0), (-68.0, 4.0), (-62.0, -10.0),
)  # fmt: skip
PAD, PAD_TONE, PAD_BUMPER, PAD_CAP = "#3a3f4a", "#262a32", "#5d6472", "#1c1f25"


def _pad(cv: Canvas, g) -> None:
    """A generic controller seen from the screen: two grips, a pale bumper along the top, two stick caps and a small
    middle button showing over the top edge. No maker's shape, button or colour."""
    for s in (-1.0, 1.0):
        _inked_oval(cv, g, s * _STICK_X, _CAP_Y, 11.0, 6.5, PAD_CAP, 4.0)
    _inked_oval(cv, g, 0.0, _CAP_Y + 3, 6.0, 3.6, "#7d8494", 3.0)
    _form(cv, g, _PAD_BODY, PAD, PAD_TONE, 228.0, 6.5, depth=12.0, amount=0.2)
    _line(cv, g, ((-50, -13), (-25, -15), (25, -15), (50, -13)), PAD_BUMPER, 5.0)


_GRIP_HAND: tuple[Point, ...] = (  # the frame's left hand round its grip, the back of it to us, in the pad's frame
    (-84.0, -2.0), (-80.0, -18.0), (-66.0, -27.0), (-50.0, -25.0), (-38.0, -14.0), (-34.0, 4.0), (-36.0, 24.0),
    (-46.0, 40.0), (-62.0, 46.0), (-78.0, 38.0), (-86.0, 18.0),
)  # fmt: skip


def _grip(cv: Canvas, g, face: Face, thumb: str, seed: float) -> None:
    """The frame's left hand on its grip with its thumb on ``thumb``: wrapped round the grip, the knuckles along its
    front, the thumb over the top edge pointing in."""
    _form(cv, g, _GRIP_HAND, face.skin, face.tone, seed, 6.0, depth=12.0, amount=0.3)
    for k, y in enumerate((8.0, 20.0, 31.0)):
        _line(cv, g, ((-78.0 + k * 2, y - 2), (-62.0, y + 4), (-46.0 - k * 3, y + 1)), face.deep, 3.4)
    tx, ty = _TIPS[thumb]
    root = (-50.0, -16.0)
    thumb_line = (root, ((root[0] + tx) / 2, min(root[1], ty) - 5.0), (tx, ty))
    flat(cv, g, _stroke(thumb_line, 21.0), PLUM_DEEP)
    flat(cv, g, _stroke(thumb_line, 13.0), face.skin)
    _oval(cv, g, tx, ty - 1, 4.0, 3.0, "#ffffff40")


def _stroke(points, weight: float):
    from . import brush

    return brush.stroke(points, weight, brush.EVEN, steps=4)


def _controller(cv: Canvas, parent, friend: Friend, beats: Sequence[Beat], end: float) -> None:
    """The controller and the hands on it, moving between holds with the arms."""
    spans = _spans([(b.at, b.hands) for b in beats], 0.0, end)
    g = cv.group(parent, cv.uid("pad"))
    _key(cv, g, "x", _eased(beats, lambda b: HOLDS[b.hands].pad[0]), end)
    _key(cv, g, "y", _eased(beats, lambda b: HOLDS[b.hands].pad[1]), end)
    _pad(cv, g)
    for index, side in ((0, -1.0), (1, 1.0)):
        hand = anatomy.Arm(Side.of(side)).hand(Facing.BACK)
        mirror = cv.group(g, cv.uid("g"), scaleX=-1.0 if GRIP.mirrored(hand) else 1.0)
        for thumb in THUMBS:
            when = [s for name, sp in spans.items() if HOLDS[name].thumbs[index] == thumb for s in sp]
            if not when:
                continue
            h = cv.group(mirror, cv.uid("g"), opacity=0.0)
            cv.gate(h, when)
            _grip(cv, h, friend.face, thumb, friend.seed + 5 + index)


# -- the two of them ---------------------------------------------------------------------------------------------------
LEO_SKIN, LEO_TONE, LEO_DEEP = "#e3ae86", "#c78d66", "#9a6444"
SAM_SKIN, SAM_TONE, SAM_DEEP = "#8a573a", "#683f26", "#462614"
HOODIE, HOODIE_TONE, HOODIE_LINE = "#5d8f6c", "#426f51", "#2f5a3e"
DENIM, DENIM_TONE, TEE, TEE_TONE = "#4d6c97", "#36527a", "#ece6dc", "#cfc6b8"

LEO_FACE = Face(
    LEO_SKIN, LEO_TONE, LEO_DEEP, "#8e3a48", "#5a3a22", "#2b1d18", 46.0, -166.0, 20.5, 10.0, -78.0, 78.0, 1.0
)
SAM_FACE = Face(
    SAM_SKIN, SAM_TONE, SAM_DEEP, "#24100a", "#2a160c", "#120c0c", 44.0, -170.0, 21.0, 13.0, -76.0, 80.0, -1.0
)

LEO_LOOKS: Mapping[str, Look] = MappingProxyType(
    {
        "level": Look(0.36, 0.12),  # at ease: the lids part way down, nothing startled
        "side": Look(0.36, 0.12, (0.38, 0.0)),
        "proud": Look(0.5, 0.04, (0.0, -0.08), brow=8.0, inner=-1.0, outer=5.0),  # chin up, lids lowered: discipline
        "set": Look(0.3, 0.3, (0.0, -0.05), brow=-3.0, inner=-2.0, blinks=False),  # a stare that will not blink
        "stare": Look(0.12, 0.0, brow=10.0, inner=2.0),  # at the screen as the game ends
        "away": Look(0.38, 0.2, (-0.4, 0.28), brow=8.0, inner=10.0),  # sheepish: eyes off, brows up in the middle
        "hurt": Look(0.5, 0.08, (-0.08, 0.42), brow=8.0, inner=24.0, outer=-8.0),  # worried brows, eyes down
        "horror": Look(0.0, 0.0, brow=24.0, inner=8.0, outer=2.0, wide=1.24, blinks=False),
        "soft": Look(0.34, 0.36, (0.22, 0.04), brow=5.0, inner=4.0),  # a smile that reaches the eyes
        "shut": SHUT,
    }
)
SAM_LOOKS: Mapping[str, Look] = MappingProxyType(
    {
        "easy": Look(0.3, 0.12),  # relaxed: lids at rest, nothing to prove
        "side": Look(0.3, 0.12, (0.38, 0.0)),
        "dry": Look(0.54, 0.12, (0.4, 0.0), near=12.0),  # a side-eye with one brow up
        "phone": Look(0.46, 0.1, (0.44, 0.12), near=6.0),  # down at the phone held out to him
        "concern": Look(0.3, 0.06, (0.38, 0.06), brow=6.0, inner=10.0, outer=-2.0),
        "deadpan": Look(0.64, 0.0, brow=-5.0, inner=-1.0, blinks=False),
        "shut": SHUT,
    }
)

LEO_HEAD: tuple[Point, ...] = (  # round and soft, full cheeks, a short chin
    (-114, -180), (-114, -132), (-104, -92), (-80, -60), (-44, -40), (0, -34), (44, -40), (80, -60), (104, -92),
    (114, -132), (114, -180), (104, -236), (64, -272), (0, -282), (-64, -272), (-104, -236),
)  # fmt: skip
LEO_BACK: tuple[Point, ...] = (  # the hair behind the head: the crown and the short sides over the ears
    (-124, -150), (-130, -214), (-112, -270), (-70, -308), (0, -320), (70, -308), (112, -270), (130, -214),
    (124, -150), (110, -176), (0, -200), (-110, -176),
)  # fmt: skip
LEO_FRINGE: tuple[Point, ...] = (  # a soft fringe swept toward the frame's right, its locks clear of the brows
    (-114, -226), (-110, -266), (-72, -304), (-10, -318), (58, -308), (106, -280), (122, -240), (116, -214),
    (100, -246), (82, -254), (66, -240), (50, -262), (22, -252), (0, -268), (-28, -250), (-50, -264), (-76, -242),
    (-96, -254),
)  # fmt: skip
SAM_HEAD: tuple[Point, ...] = (  # longer than Leo's, a squared jaw and a chin
    (-100, -190), (-100, -124), (-92, -80), (-78, -50), (-40, -24), (0, -18), (40, -24), (78, -50), (92, -80),
    (100, -124), (100, -190), (94, -244), (56, -280), (0, -290), (-56, -280), (-94, -244),
)  # fmt: skip
SAM_CROP: tuple[Point, ...] = (  # a short crop, squared on top, with a clean line at the brow and the temples
    (-108, -176), (-110, -236), (-100, -282), (-60, -308), (0, -314), (60, -308), (100, -282), (110, -236),
    (108, -176), (99, -188), (94, -226), (70, -238), (36, -242), (0, -243), (-36, -242), (-70, -238), (-94, -226),
    (-99, -188),
)  # fmt: skip

LEO_BUILD = news_arms.Build((150.0, -110.0), 130.0, 142.0, 33.0, 30.0, 25.0, 0.96)
SAM_BUILD = news_arms.Build((152.0, -112.0), 132.0, 144.0, 31.0, 28.0, 24.0, 0.96)

LEO_FRIEND = Friend(
    "leo", LEO_FACE, LEO_LOOKS, LEO_BUILD, HOODIE, HOODIE_TONE, HOODIE_LINE, 401.0, LEO_HEAD, LEO_BACK,
    "#2b1d18", "#1a110e", "#5b4032", (114.0, -176.0, -112.0), 38.0,
)  # fmt: skip
SAM_FRIEND = Friend(
    "sam", SAM_FACE, SAM_LOOKS, SAM_BUILD, DENIM, DENIM_TONE, "#2c4568", 433.0, SAM_HEAD, SAM_CROP,
    "#151012", "#0b0809", "#3a2f33", (106.0, -170.0, -116.0), 40.0, (3.4, 5.2),
)  # fmt: skip
FRIENDS: Mapping[str, Friend] = MappingProxyType({"leo": LEO_FRIEND, "sam": SAM_FRIEND})


def _ears(cv: Canvas, g, friend: Friend) -> None:
    x, top, bottom = friend.ears
    f = friend.face
    for side in (-1.0, 1.0):
        ex = side * x
        _form(cv, g, ((ex + side * 16, top), (ex + side * 28, top + 26), (ex + side * 20, bottom + 8), (ex, bottom),
                      (ex - side * 8, top + 30)), f.skin, f.tone, friend.seed + 7 + side, 6.0, 8.0)  # fmt: skip
        _line(cv, g, ((ex + side * 16, top + 18), (ex + side * 8, top + 40), (ex + side * 12, bottom - 4)), f.deep, 3.6)


def _leo_hair(cv: Canvas, g) -> None:
    _form(cv, g, LEO_FRINGE, "#2b1d18", "#1a110e", 409.0, depth=22.0, amount=0.8)
    for x, y, k in ((-70, -290, 1), (-20, -304, 1), (36, -300, -1), (80, -282, -1)):
        _line(cv, g, ((x, y), (x + k * 18, y + 14), (x + k * 22, y + 30)), "#5b4032", 4.6, FUR)


def _sam_hair(cv: Canvas, g) -> None:
    _form(cv, g, SAM_CROP, "#151012", "#0b0809", 437.0, depth=16.0, amount=0.3)
    for x, y in ((-70, -284), (-40, -298), (-6, -302), (30, -298), (64, -286), (-56, -262), (-22, -270), (14, -272),
                 (48, -264), (80, -256), (-84, -246), (-36, -252), (2, -254), (40, -250)):  # fmt: skip
        _line(cv, g, ((x - 6, y + 3), (x, y - 3), (x + 6, y + 3)), "#3a2f33", 3.4)


def _features(cv: Canvas, g, friend: Friend) -> None:
    """What does not change with the beat: the nose and the cheeks."""
    f = friend.face
    if friend.name == "leo":
        for s in (-1.0, 1.0):
            _oval(cv, g, s * 70, -116, 24, 13, "#e0806035")
        _line(cv, g, ((-4, -152), (-12, -122), (-4, -108), (12, -112)), f.deep, 5.5)
    else:
        for s in (-1.0, 1.0):  # a broad nose: the two wings, no line under them that could read as a mouth
            _line(cv, g, ((s * 14, -136), (s * 26, -124), (s * 24, -112), (s * 12, -110)), "#24100a", 5.5)
        _line(cv, g, ((-2, -158), (-5, -136)), "#24100a", 4.0)
        for s in (-1.0, 1.0):  # the cheekbones under the light
            _line(cv, g, ((s * 64, -128), (s * 76, -112)), "#a0684a", 4.0)


def _flush(cv: Canvas, g, face: Face) -> None:
    for s in (-1.0, 1.0):
        _oval(cv, g, s * 70, -114, 30, 16, "#ff5f6a55")
        for k in (-10.0, 0.0, 10.0):
            _line(cv, g, ((s * 70 + k - 4, -108), (s * 70 + k + 4, -122)), "#e2485a90", 3.0)


def _leo_body(cv: Canvas, g) -> None:
    hood = ((-126, -120), (-118, -176), (-84, -200), (0, -206), (84, -200), (118, -176), (126, -120))
    _form(cv, g, hood, HOODIE_TONE, HOODIE_LINE, 411.0, depth=14.0, amount=0.3)
    _neck(cv, g, LEO_FRIEND)
    torso = ((-192, 360), (-196, 140), (-200, -20), (-196, -88), (-176, -124), (-136, -144), (-92, -152),
             (-58, -156), (-30, -136), (0, -130), (30, -136), (58, -156), (92, -152), (136, -144), (176, -124),
             (196, -88), (200, -20), (196, 140), (192, 360))  # fmt: skip
    _form(cv, g, torso, HOODIE, HOODIE_TONE, 412.0, depth=30.0, amount=0.3)
    collar = ((-80, -150), (-44, -144), (0, -128), (44, -144), (80, -150), (84, -128), (44, -112), (0, -100),
              (-44, -112), (-84, -128))  # fmt: skip
    _form(cv, g, collar, HOODIE_TONE, HOODIE_LINE, 413.0, 6.0, depth=8.0, amount=0.2)
    for s in (-1.0, 1.0):
        _line(cv, g, ((s * 22, -104), (s * 26, -60), (s * 24, -20)), "#efe6d2", 6.0)
        _inked_oval(cv, g, s * 24, -14, 4.5, 8.0, "#d8d0c0", 3.0)
    _line(cv, g, ((-118, 250), (-96, 96), (96, 96), (118, 250)), HOODIE_LINE, 5.0)


def _sam_body(cv: Canvas, g) -> None:
    _neck(cv, g, SAM_FRIEND)
    torso = ((-194, 360), (-198, 140), (-204, -20), (-200, -90), (-180, -126), (-140, -146), (-94, -154),
             (-62, -160), (62, -160), (94, -154), (140, -146), (180, -126), (200, -90), (204, -20), (198, 140),
             (194, 360))  # fmt: skip
    _form(cv, g, torso, DENIM, DENIM_TONE, 441.0, depth=30.0, amount=0.3)
    tee = ((-58, 360), (-60, -150), (-36, -134), (0, -126), (36, -134), (60, -150), (58, 360))
    _form(cv, g, tee, TEE, TEE_TONE, 442.0, 6.0, depth=10.0, amount=0.2)
    _line(cv, g, ((-40, -140), (0, -118), (40, -140)), TEE_TONE, 4.5)
    for s in (-1.0, 1.0):
        lapel = ((s * 58, -162), (s * 92, -150), (s * 100, -110), (s * 72, -96), (s * 62, 20), (s * 54, -120))
        _form(cv, g, lapel, "#5b7ca8", DENIM_TONE, 443.0 + s, 6.0, depth=10.0, amount=0.2)
    _form(cv, g, ((-150, -70), (-96, -70), (-96, -22), (-150, -22)), DENIM, DENIM_TONE, 445.0, 5.0, depth=8.0)
    _line(cv, g, ((-150, -56), (-96, -56)), DENIM_TONE, 4.0)


def _neck(cv: Canvas, g, friend: Friend) -> None:
    f, w = friend.face, friend.neck
    _form(cv, g, ((-w, -262), (-w, -196), (-w - 8, -120), (w + 8, -120), (w, -196), (w, -262)), f.skin, f.tone,
          friend.seed + 9, 6.4, depth=14.0, amount=0.3)  # fmt: skip
    cv.path(g, f"M {-w + 4} -214 Q 0 -160 {w - 4} -214 L {w - 4} -190 Q 0 -140 {-w + 4} -190 Z", f.deep + "80",
            cv.clear, 0)  # fmt: skip


def perform(
    cv: Canvas,
    parent,
    who: str,
    beats: Sequence[Beat],
    end: float,
    x: float = 540.0,
    y: float = 1120.0,
    scale: float = 1.0,
    moves: Moves = STILL,
    mouths: Sequence[tuple[float, str]] = (),
):
    """``who`` (``"leo"`` or ``"sam"``) seated with the top of his collar's middle at frame ``x``, ``y``, at ``scale``,
    from 0 to ``end``: a :class:`Beat` from each second on, ``moves`` over them and ``mouths`` the take's visemes for
    any beat whose mouth is ``"talk"``. Draws through the registered part. Returns the friend's group."""
    if who not in FRIENDS:
        raise FriendsError(f"the couch seats {tuple(FRIENDS)}, not {who!r}")
    return (leo if who == "leo" else sam)(cv, parent, beats, end, x=x, y=y, scale=scale, moves=moves, mouths=mouths)


def _perform(cv: Canvas, parent, friend: Friend, x, y, scale, beats, end, moves: Moves, mouths):
    f = friend.face
    g = cv.group(parent, cv.uid(friend.name), x=x, y=y, scaleX=scale, scaleY=scale)
    breath = cv.group(g, cv.uid("breath"))
    _key(cv, breath, "y", _breath(end, friend.seed), end)
    shoulders = cv.group(breath, cv.uid("shoulders"))
    _key(cv, shoulders, "y", _pulse(moves.shrugs, 0.2, 0.28, 0.36, -13.0), end)
    (_leo_body if friend.name == "leo" else _sam_body)(cv, shoulders)
    throat = cv.group(shoulders, cv.uid("throat"))
    _key(cv, throat, "y", _pulse(moves.swallows, 0.16, 0.12, 0.3, -12.0), end)
    _line(cv, throat, ((-9, -150), (0, -143), (9, -150)), f.deep, 4.4)
    # the head: the beat's tilt, then the slow drift, then the dip of a nod, all on the chin
    pivot = dict(anchorX=0.0, anchorY=CHIN_Y)
    tilt = cv.group(breath, cv.uid("head-tilt"), x=0.0, y=NECK_Y, **pivot)
    _key(cv, tilt, "rotation", _eased(beats, lambda b: b.tilt), end)
    up = cv.group(tilt, cv.uid("head-shrug"), x=0.0, y=CHIN_Y, **pivot)
    _key(cv, up, "y", _pulse(moves.shrugs, 0.2, 0.28, 0.36, -6.0, CHIN_Y), end, CHIN_Y)
    drift = cv.group(up, cv.uid("head-drift"), x=0.0, y=CHIN_Y, **pivot)
    _key(cv, drift, "rotation", _drift(end, friend.seed, 1.1), end)
    _key(cv, drift, "x", [(t, v * 2.2) for t, v in _drift(end, friend.seed + 1, 1.0)], end)
    nod = cv.group(drift, cv.uid("head-nod"), x=0.0, y=CHIN_Y, **pivot)
    dips = _nods(moves.nods, moves.swallows)
    _key(cv, nod, "y", [(t, CHIN_Y + d * 0.5) for t, d in dips], end, CHIN_Y)
    _form(cv, nod, friend.back, friend.hair, friend.hair_tone, friend.seed + 11, depth=22.0, amount=0.8)
    _ears(cv, nod, friend)
    _form(cv, nod, friend.head, f.skin, f.tone, friend.seed + 13, depth=24.0, amount=0.5)
    (_leo_hair if friend.name == "leo" else _sam_hair)(cv, nod)
    face = cv.group(nod, cv.uid("head-face"))
    _key(cv, face, "x", _eased(beats, lambda b: b.turn * f.toward * FACE_SLIDE), end)
    _key(cv, face, "y", [(t, v) for t, v in _merge_y(beats, dips)], end)
    _features(cv, face, friend)
    if moves.flush:
        blush = cv.group(face, cv.uid("g"), opacity=0.0)
        cv.gate(blush, list(moves.flush))
        _flush(cv, blush, f)
    for state, spans in _spans(_blinks(friend, beats, end), 0.0, end).items():
        e = cv.group(face, cv.uid("g"), opacity=0.0)
        cv.gate(e, spans)
        look = friend.looks.get(state, SHUT)
        for side in (-1.0, 1.0):
            _eye(cv, e, f, side, look, state == "shut")
            _brow(cv, e, f, side, look if state != "shut" else Look(0.0, brow=-2.0))
    for state, spans in _spans(_mouth_track(beats, mouths, end), 0.0, end).items():
        m = cv.group(face, cv.uid("g"), opacity=0.0)
        cv.gate(m, spans)
        _mouth(cv, m, f, state)
    arms = cv.group(breath, cv.uid("arms"))  # over the head, so a hand held up is in front of the chin
    _key(cv, arms, "y", _pulse(moves.shrugs, 0.2, 0.28, 0.36, -13.0), end)
    hand_spans = _spans([(b.at, b.hands) for b in beats], 0.0, end)
    for side in (-1.0, 1.0):
        _arm(cv, arms, friend, side, beats, hand_spans, end)
    _controller(cv, arms, friend, beats, end)
    return g


def _merge_y(beats: Sequence[Beat], dips: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """The face's slide up and down: the beat's lift (chin up) and half of each nod's dip, which the skull carries the
    other half of."""
    lifts = _eased(beats, lambda b: -b.lift)
    times = sorted({t for t, _ in lifts} | {t for t, _ in dips})

    def at(keys, t):
        return news_arms.value_at(tuple(keys), t)

    return [(t, round(at(lifts, t) + at(dips, t) * 0.5, 3)) for t in times]


# -- the light of the screen -------------------------------------------------------------------------------------------
NIGHT = "#2c2238"  # how far the people go down when the screen does
FALL_OFF = "#4a3b56"  # the edges of the frame, away from the screen's light on the faces


def screen_light(cv: Canvas, parent, people: str, cues: Any, end: float, faces: Sequence[Point]) -> list:
    """The screen's light on the people only: a group gated by the alpha of the group ``people`` (its id), multiplied
    over them so the ink stays ink. The screen's colour (``cues`` as :func:`srstudio.toon_rooms.front_screen` reads
    them), a fall-off from the ``faces`` to the frame's edges, and a darker sheet as the screen's level falls. A glow of
    the colour on each face goes over that, screened. Returns the parsed cues."""
    if not faces:
        raise FriendsError("the screen lights at least one face")
    parsed = toon_rooms._cues("screen", cues, True, end)
    levels = toon_rooms.level_keys(parsed, end)
    lit = cv.group(parent, cv.uid("lit"), matte=people, matteVisible="true", blend="multiply")
    toon_rooms._coloured(
        cv, lit, parsed, end,
        lambda c, name, colour: cv.rect(c, 0, 0, cv.width, cv.height,
                                        toon_rooms.front_tint(colour, 0.5 if name == "red" else 0.34), cv.clear, 0),
    )  # fmt: skip
    cx = sum(p[0] for p in faces) / len(faces) / cv.width
    cy = sum(p[1] for p in faces) / len(faces) / cv.height
    fall = cv.rgrad("friends-fall-off", ((0, "#ffffff"), (0.42, "#f1ebf4"), (1, FALL_OFF)), (cx, cy, 0.62))
    cv.rect(lit, 0, 0, cv.width, cv.height, fall, cv.clear, 0)
    night = toon_rooms._level(cv, lit, levels, -0.6, 0.6)
    cv.rect(night, 0, 0, cv.width, cv.height, NIGHT, cv.clear, 0)
    glow = cv.group(parent, cv.uid("glow"), matte=people, matteVisible="true", blend="screen")
    shine = toon_rooms._level(cv, glow, levels, 0.55)

    def spot(c, name: str, colour: str) -> None:
        paint = cv.rgrad(f"friends-glow-{name}", ((0, colour + "aa"), (0.5, colour + "44"), (1, colour + "00")))
        for fx_, fy_ in faces:
            cv.ellipse(c, fx_ - 230, fy_ - 250, 460, 500, paint)

    toon_rooms._coloured(cv, shine, parsed, end, spot)
    return parsed


# -- the registered drawings -------------------------------------------------------------------------------------------
_CONTRACT = cc.character(
    limbs=False,
    expressions=True,
    parameters=(
        ("beats", cc.P(items=cc.P(fields=(("mouth", cc.P(enum=(*MOUTHS, "talk"))), ("hands", cc.P(enum=HANDS)))))),
        ("end", cc.seconds("project", "end")),
        ("mouths", cc.track("project", VISEMES)),
    ),
)


@register(
    "character",
    "friends-leo",
    summary="Leo, about twenty, inked the News way: a soft fringe, a green hoodie, a controller in both hands",
    contract=_CONTRACT,
)
def leo(cv: Canvas, parent, beats: Sequence[Beat], end: float, x: float = 540.0, y: float = 1120.0,
        scale: float = 1.0, moves: Moves = STILL, mouths: Sequence[tuple[float, str]] = ()):  # fmt: skip
    """Leo on the couch: likeable, a little soft round the edges, confident until he isn't."""
    return _perform(cv, parent, LEO_FRIEND, x, y, scale, _checked(LEO_FRIEND, beats, end), end, moves, mouths)


@register(
    "character",
    "friends-sam",
    summary="Sam, about twenty, inked the News way: a short crop, an open denim shirt, a controller in both hands",
    contract=_CONTRACT,
)
def sam(cv: Canvas, parent, beats: Sequence[Beat], end: float, x: float = 540.0, y: float = 1120.0,
        scale: float = 1.0, moves: Moves = STILL, mouths: Sequence[tuple[float, str]] = ()):  # fmt: skip
    """Sam on the couch: relaxed, secure, the cool one."""
    return _perform(cv, parent, SAM_FRIEND, x, y, scale, _checked(SAM_FRIEND, beats, end), end, moves, mouths)


def _checked(friend: Friend, beats: Sequence[Beat], end: float) -> list[Beat]:
    out = list(beats)
    _check(friend, out, end)
    return out


def specimen_beats(who: str, seconds: float) -> tuple[Beat, ...]:
    """Every look, mouth and hold of ``who`` in turn over ``seconds``: what a specimen of the drawing shows."""
    friend = FRIENDS[who]
    looks = [k for k in friend.looks if k != "shut"]
    hands = [h for h in HANDS if not (h == "phone" and friend.face.toward < 0)]
    count = max(len(looks), len(MOUTHS), len(hands))
    return tuple(
        Beat(round(seconds * n / count, 4), looks[n % len(looks)], MOUTHS[n % len(MOUTHS)], hands[n % len(hands)])
        for n in range(count)
    )


SPECIMEN_MOVES: Final = Moves(nods=((1.0, 8.0),), shrugs=(2.0,), swallows=(3.0,), flush=((0.5, 1.5),))
