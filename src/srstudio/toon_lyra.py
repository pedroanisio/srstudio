"""Lyra, the owl who presents astronomy: a character from the Retro Orbit pack supplied by the operator (ADR 0063),
drawn on flat print plates (:mod:`srstudio.toon_plate`) and kept in her own mid-century palette, not the older cast's
ink line.

She keeps her swept feather tufts and elongated mask, the almond eyes with their boomerang brows, the tapered uniform
and the comet scarf. Her beak is always drawn, an inked gape opening under it to speak.

Her expressions are typed data: :data:`MOODS` (:class:`Mood`, eyes, a :class:`Beak` and how the head sits) and
:data:`EYE_POSES` (:class:`EyePose`). A :class:`srstudio.toon.Pose` may name a mood as its eyes and its mouth, or an eye
pose as its eyes, and the shared vocabulary (:data:`srstudio.toon.EYES`, :data:`srstudio.toon.MOUTHS`) is mapped onto
the same states, so she keeps the contract of the brush characters; anything else is refused by name
(:func:`mood`, :func:`eye_pose`).

:data:`LYRA_RIG` is her head rig (ADR 0050), with :data:`LYRA_MOTION`: an owl's head, quick to snap round and slow to
leave. The whole head lies over the scarf, chin first, and the top of the uniform runs up behind it. :func:`mood_plan`
turns her head from mood to mood; :func:`pose` writes a pose in a mood or an eye pose. Lip sync (ADR 0020) opens the
beak: ``open`` is the talking gape, ``round`` the round one, ``teeth`` the small one.

Everything is in Toon reference pixels; :data:`PLACE` maps the drawing's own units to them. Bad input is a
:class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from . import brush, checks
from .brush import Point
from .canvas import Canvas
from .contracts import ParameterContract, PartContract
from .head_motion import Channel, HeadPlan, HeadStyle, Spring
from .registry import register
from .toon import ARMS, Pose, ToonDataError
from .toon_cast import CENTRE, Layer, Look, Mouths
from .toon_head import HeadRig
from .toon_head import figure as rig_figure
from .toon_orbit import clicker_art
from .toon_plate import (
    CORAL,
    CREAM,
    GOLD,
    MINT,
    NAVY,
    PALE,
    PAPER,
    TEAL,
    Frame,
    Plate,
    atom,
    clip,
    ell,
    inside,
    points,
    polygon,
    rule,
    shape,
)

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "BEAKS",
    "EYE_POSES",
    "LYRA",
    "LYRA_MOTION",
    "LYRA_RIG",
    "MOODS",
    "PALETTE",
    "PLACE",
    "SCARF_TOP",
    "TURN_SECONDS",
    "Beak",
    "EyePose",
    "Eyes",
    "Lyra",
    "Mood",
    "eye_pose",
    "iris_of",
    "lyra",
    "mood",
    "mood_plan",
    "pose",
]

PALETTE = (PAPER, NAVY, TEAL, MINT, CORAL, GOLD, CREAM, PALE)
BOB = 0.66  # reference pixels to a unit of the drawing
PLACE = Frame(CENTRE - 300.0 * BOB, 700.0 - 470.0 * BOB, BOB)  # her axis on the character's, her neck on the neck
EYE_CENTRES = (219.0, 380.0)
EYE_Y = 290.0
EYE_W = 67.0
GAZE_REACH = 27.0  # units an iris may leave the centre of its eye
NEAR = 0.85  # how far each iris crosses inward for the near-focus pose
TILT_MOST = 12.0  # the most a mood turns her head, degrees
TURN_SECONDS = 0.28  # the time :func:`mood_plan` gives a head to turn to a new mood
SCARF_TOP = PLACE.point(300.0, 460.0)[1]  # the scarf's knot: the chin must never rise above it
GAPE_AT = (299.0, 397.0)


def _unit(value: float, what: str) -> float:
    if not (checks.number(value) and 0.0 <= value <= 1.0):
        raise ToonDataError(f"{what} is 0 to 1, got {value!r}")
    return value


@dataclass(frozen=True)
class Eyes:
    """How her eyes sit: ``gaze`` across and down (-1 to 1), ``lids`` over the left and right eye and ``bottom`` under
    both (shares of the eye), ``pupil`` a scale, ``brows`` their rise (units, up is negative) and ``angles`` their turn
    (degrees), ``tall`` the almond's half height, ``near`` both irises crossed inward, ``blink`` a lid as a share of
    the eye that overrides ``lids`` (1 is shut), and ``mark`` one of ``tear``, ``heart``, ``wince`` for the shared
    expressions that draw one."""

    gaze: tuple[float, float] = (0.0, 0.0)
    lids: tuple[float, float] = (0.04, 0.04)
    bottom: float = 0.0
    pupil: float = 1.0
    brows: tuple[float, float] = (-5.0, -5.0)
    angles: tuple[float, float] = (0.0, 0.0)
    tall: float = 76.0
    near: bool = False
    blink: float | None = None
    mark: str = ""

    def __post_init__(self) -> None:
        if not all(checks.number(v) and -1.0 <= v <= 1.0 for v in self.gaze):
            raise ToonDataError(f"a gaze is -1 to 1 each way, got {self.gaze!r}")
        for v in self.lids:
            _unit(v, "a lid")
        _unit(self.bottom, "the lower lid")
        if self.blink is not None:
            _unit(self.blink, "a blink")
        if not (checks.number(self.pupil) and 0.2 <= self.pupil <= 1.5):
            raise ToonDataError(f"a pupil's scale is 0.2 to 1.5, got {self.pupil!r}")
        if not (checks.number(self.tall) and 60.0 <= self.tall <= 90.0):
            raise ToonDataError(f"an almond's half height is 60 to 90, got {self.tall!r}")
        if not all(checks.number(v) for v in (*self.brows, *self.angles)):
            raise ToonDataError(f"brows are finite, got {self.brows!r} and {self.angles!r}")
        if self.mark not in ("", "tear", "heart", "wince"):
            raise ToonDataError(f"no eye mark {self.mark!r}")


@dataclass(frozen=True)
class Beak:
    """A beak: ``gape`` the half width and half height of the opening under it (none: shut), ``tongue`` shown in it."""

    name: str
    gape: tuple[float, float] | None = None
    tongue: bool = False

    def __post_init__(self) -> None:
        if self.gape is not None and not all(checks.number(v) and 0.0 < v <= 60.0 for v in self.gape):
            raise ToonDataError(f"{self.name}: a gape is 0 to 60 each way, got {self.gape!r}")


BEAKS: Mapping[str, Beak] = {
    "closed": Beak("closed"),
    "talk": Beak("talk", (22.0, 24.0), True),
    "small": Beak("small", (18.0, 10.0)),
    "round": Beak("round", (17.0, 35.0)),
    "smile": Beak("smile", (28.0, 29.0), True),
    "wide": Beak("wide", (26.0, 46.0), True),  # past what the plates show: a yawn or a scream of the shared vocabulary
}


@dataclass(frozen=True)
class Mood:
    """An expression: her ``eyes``, a beak by name, and ``tilt``, how many degrees clockwise her head sits."""

    name: str
    eyes: Eyes
    beak: str
    tilt: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ToonDataError("a mood has a name")
        if self.beak not in BEAKS:
            raise ToonDataError(f"{self.name}: no beak {self.beak!r}; the beaks are {tuple(BEAKS)}")
        if not (checks.number(self.tilt) and abs(self.tilt) <= TILT_MOST):
            raise ToonDataError(f"{self.name}: a mood's tilt is within {TILT_MOST} degrees, got {self.tilt!r}")


@dataclass(frozen=True)
class EyePose:
    """A gaze or a lid held in the welcome mood's face: ``eyes``, the head level."""

    name: str
    eyes: Eyes


MOODS: Mapping[str, Mood] = {
    "welcome": Mood("welcome", Eyes(), "talk", -2.0),
    "curiosity": Mood(
        "curiosity", Eyes((0.55, -0.2), (0.08, 0.0), brows=(-2.0, -24.0), angles=(-7.0, 5.0)), "small", -6.0
    ),
    "doubt": Mood("doubt", Eyes((0.9, 0.0), (0.47, 0.12), brows=(12.0, -22.0), angles=(-7.0, 9.0)), "closed", 5.0),
    "delight": Mood("delight", Eyes(lids=(0.0, 0.0), bottom=0.44, brows=(-15.0, -15.0)), "smile", -4.0),
    "focus": Mood("focus", Eyes((0.0, 0.55), (0.29, 0.29), brows=(8.0, 8.0), angles=(16.0, -16.0)), "closed", 2.0),
    "wonder": Mood(
        "wonder", Eyes((0.15, -0.65), (0.0, 0.0), pupil=1.15, brows=(-30.0, -30.0), tall=84.0), "round", -3.0
    ),
}
EYE_POSES: Mapping[str, EyePose] = {
    "camera": EyePose("camera", Eyes()),
    "left": EyePose("left", Eyes((-1.0, 0.0))),
    "right": EyePose("right", Eyes((1.0, 0.0))),
    "up": EyePose("up", Eyes((0.0, -1.0))),
    "down": EyePose("down", Eyes((0.0, 1.0))),
    "near": EyePose("near", Eyes(near=True)),
    "half": EyePose("half", Eyes(blink=0.5)),
    "closed": EyePose("closed", Eyes(blink=1.0)),
}
_SHARED_EYES = {"side": "right", "wide": "camera"}
_SHARED_MOODS = {"narrow": "focus", "shock": "wonder"}
_SHARED_STATES = {
    "roll": Eyes((0.65, -0.75), (0.12, 0.12), brows=(-14.0, -8.0)),
    "teary": Eyes(lids=(0.1, 0.1), brows=(-16.0, -16.0), angles=(9.0, -9.0), mark="tear"),
    "wince": Eyes(brows=(10.0, 10.0), angles=(14.0, -14.0), mark="wince"),
    "hearts": Eyes(lids=(0.0, 0.0), brows=(-15.0, -15.0), mark="heart"),
    "sleepy": Eyes((0.0, 0.2), (0.62, 0.62), brows=(4.0, 4.0)),
}
_SHARED_BEAKS = {
    "flat": "closed",
    "open": "talk",
    "o": "small",
    "drop": "talk",
    "grin": "smile",
    "wave": "small",
    "smirk": "small",
    "none": "closed",
    "grimace": "small",
    "frown": "closed",
    "tongue": "talk",
    "kiss": "closed",
    "yawn": "wide",
    "scream": "wide",
    "puff": "closed",
}
_VISEMES = {"open": "talk", "round": "round", "teeth": "small"}


def mood(name: str) -> Mood:
    """A mood by name, or a refusal naming them."""
    try:
        return MOODS[name]
    except KeyError:
        raise ToonDataError(f"Lyra has no mood {name!r}; her moods are {tuple(MOODS)}") from None


def eye_pose(name: str) -> EyePose:
    """An eye pose by name, or a refusal naming them."""
    try:
        return EYE_POSES[name]
    except KeyError:
        raise ToonDataError(f"Lyra has no eye pose {name!r}; her eye poses are {tuple(EYE_POSES)}") from None


def _eyes_of(kind: str) -> Eyes:
    """The state of a pose's ``eyes``: a mood, an eye pose or a word of the shared vocabulary."""
    if kind in MOODS:
        return MOODS[kind].eyes
    if kind in EYE_POSES:
        return EYE_POSES[kind].eyes
    if kind in _SHARED_EYES:
        return EYE_POSES[_SHARED_EYES[kind]].eyes
    if kind in _SHARED_MOODS:
        return MOODS[_SHARED_MOODS[kind]].eyes
    if kind in _SHARED_STATES:
        return _SHARED_STATES[kind]
    raise ToonDataError(
        f"Lyra has no eyes {kind!r}: a mood {tuple(MOODS)}, an eye pose {tuple(EYE_POSES)} or a Toon word"
    )


def _beak_of(kind: str) -> Beak:
    """The beak of a pose's ``mouth``: a mood, a beak or a word of the shared vocabulary."""
    if kind in MOODS:
        return BEAKS[MOODS[kind].beak]
    if kind in BEAKS:
        return BEAKS[kind]
    if kind in _SHARED_BEAKS:
        return BEAKS[_SHARED_BEAKS[kind]]
    raise ToonDataError(f"Lyra has no beak {kind!r}: a mood {tuple(MOODS)}, a beak {tuple(BEAKS)} or a Toon word")


def iris_of(eyes: Eyes, side: int, glance: tuple[float, float]) -> Point:
    """Where the iris of eye ``side`` (0 left, 1 right) sits, in the drawing's units, gaze and glance together."""
    cx = EYE_CENTRES[side]
    gx = (NEAR if side == 0 else -NEAR) if eyes.near else eyes.gaze[0] + glance[0]
    gy = eyes.gaze[1] + glance[1]
    far = max(1.0, math.hypot(gx, gy))
    return (cx + gx / far * GAZE_REACH, EYE_Y + gy / far * GAZE_REACH)


def _almond(cx: float, tall: float) -> str:
    return (
        f"M {cx - EYE_W} {EYE_Y} C {cx - 52} {EYE_Y - tall} {cx + 43} {EYE_Y - tall - 10} {cx + EYE_W} {EYE_Y - 5} "
        f"C {cx + 53} {EYE_Y + tall} {cx - 43} {EYE_Y + tall + 3} {cx - EYE_W} {EYE_Y} Z"
    )


def _brow(cx: float, rise: float, angle: float) -> Layer:
    f = PLACE.then(Frame(cx, 207.0 + rise, 1.0, angle))
    return (shape("M -64 9 Q -15 -28 63 -2 L 43 8 Q -9 -6 -64 17 Z", f), NAVY)


def _lidded(d: str, outline: Sequence[Point], colour: str) -> Layer | None:
    kept = clip(points(d, PLACE, 12), outline)
    return (polygon(kept), colour) if len(kept) >= 3 else None


def _line_in(d: str, weight: float, outline: Sequence[Point], colour: str = NAVY) -> Layer | None:
    line = inside(points(d, PLACE, 24), outline)
    if len(line) < 2:
        return None
    return (brush.stroke(line, weight * BOB, brush.Pressure(1.0, 1.0, 0.0, 0.0, 2.0), steps=1), colour)


def _heart(x: float, y: float, size: float) -> str:
    return (
        f"M {x} {y + size} C {x - size * 1.5} {y - size * 0.1} {x - size * 0.8} {y - size * 1.1} {x} {y - size * 0.35} "
        f"C {x + size * 0.8} {y - size * 1.1} {x + size * 1.5} {y - size * 0.1} {x} {y + size} Z"
    )


def _eye(eyes: Eyes, side: int, glance: tuple[float, float]) -> list[Layer]:
    """One eye in layers: the almond, the iris clipped to it, the lids, the brow."""
    cx = EYE_CENTRES[side]
    tall = eyes.tall
    d = _almond(cx, tall)
    outline = points(d, PLACE, 16)
    out: list[Layer] = [(shape(d, PLACE), CREAM)]
    rim = f"M {cx - EYE_W} {EYE_Y} C {cx - 52} {EYE_Y - tall} {cx + 43} {EYE_Y - tall - 10} {cx + EYE_W} {EYE_Y - 5}"
    out.append((rule(rim, 3.5, PLACE), NAVY))
    blink = eyes.blink
    if eyes.mark == "wince":
        out.append((shape(d, PLACE), PAPER))
        out.append(
            (rule(f"M {cx - 40} {EYE_Y - 24} L {cx + 34} {EYE_Y + 2} L {cx - 40} {EYE_Y + 28}", 4.0, PLACE), NAVY)
        )
    elif blink is not None and blink >= 0.99:
        out.append((shape(d, PLACE), PAPER))
        out.append(
            (rule(f"M {cx - EYE_W + 8} {EYE_Y + 1} Q {cx} {EYE_Y + 27} {cx + EYE_W - 5} {EYE_Y + 1}", 4.0, PLACE), NAVY)
        )
    elif eyes.mark == "heart":
        x, y = iris_of(eyes, side, glance)
        out.append((shape(_heart(x, y, 34.0), PLACE), CORAL))
    else:
        out += _iris(eyes, side, glance, outline)
        out += _lids(eyes, side, outline)
    if eyes.mark == "tear":
        x = cx + (-30.0 if side == 0 else 30.0)
        out.append((shape(_heart(x, EYE_Y + 66.0, 11.0), PLACE), MINT))
    out.append(_brow(cx, eyes.brows[side], eyes.angles[side]))
    return out


def _iris(eyes: Eyes, side: int, glance: tuple[float, float], outline: Sequence[Point]) -> list[Layer]:
    x, y = iris_of(eyes, side, glance)
    parts = (
        (x, y, 28.0, 38.0, GOLD),
        (x + 1.0, y + 1.0, 17.0 * eyes.pupil, 28.0 * eyes.pupil, NAVY),
        (x - 8.0, y - 16.0, 7.0, 10.0, CREAM),
        (x + 10.0, y + 16.0, 3.0, 4.0, CREAM),
    )
    out: list[Layer] = []
    for ex, ey, rx, ry, colour in parts:
        ring = tuple(
            PLACE.point(ex + rx * math.cos(2 * math.pi * k / 28), ey + ry * math.sin(2 * math.pi * k / 28))
            for k in range(28)
        )
        kept = clip(ring, outline)
        if len(kept) >= 3:
            out.append((polygon(kept), colour))
    return out


def _lids(eyes: Eyes, side: int, outline: Sequence[Point]) -> list[Layer]:
    cx = EYE_CENTRES[side]
    tall = eyes.tall
    top = eyes.lids[side] if eyes.blink is None else eyes.blink
    bottom = eyes.bottom if eyes.blink is None else eyes.blink * 0.04
    ty = EYE_Y - tall + top * tall * 2.0
    by = EYE_Y + tall - bottom * tall * 2.0
    left, right = cx - EYE_W - 4.0, cx + EYE_W + 4.0
    roof = EYE_Y - tall - 18.0
    upper = f"M {left} {roof} L {right} {roof} L {right} {ty} Q {cx} {ty + 9.0} {left} {ty} Z"
    candidates = [_lidded(upper, outline, PAPER)]
    if top > 0.03:
        candidates.append(_line_in(f"M {left} {ty} Q {cx} {ty + 9.0} {right} {ty}", 3.0, outline))
    if bottom:
        sill = EYE_Y + tall + 10.0
        lower = f"M {left} {by} Q {cx} {by - 26.0} {right} {by} L {right} {sill} L {left} {sill} Z"
        candidates.append(_lidded(lower, outline, PAPER))
        candidates.append(_line_in(f"M {left} {by} Q {cx} {by - 26.0} {right} {by}", 3.3, outline))
    return [c for c in candidates if c is not None]


def _beak(beak: Beak) -> list[Layer]:
    out: list[Layer] = []
    x, y = GAPE_AT
    if beak.gape is not None:
        out.append((ell(x, y, *beak.gape, PLACE), NAVY))
        if beak.tongue:
            out.append((ell(300.0, 409.0, 14.0, 6.0, PLACE), CORAL))
    return out + [
        (shape("M 274 361 L 299 344 L 327 360 L 299 397 Z", PLACE), GOLD),
        (shape("M 299 344 L 327 360 L 299 397 Z", PLACE), CORAL),
    ]


_HEAD_D = (
    "M 138 208 L 103 97 L 233 163 Q 302 130 374 162 L 502 83 L 465 216 C 522 310 463 418 358 465 L 301 505 L 241 466 "
    "C 128 424 82 312 138 208 Z"
)
_SILHOUETTE_D = (
    "M 138 208 L 103 97 L 233 163 Q 302 130 374 162 L 502 83 L 465 216 C 522 310 463 418 372 452 Q 430 497 425 566 "
    "L 397 705 L 426 800 L 320 852 L 179 806 L 202 678 L 176 558 Q 173 497 231 455 C 128 424 82 312 138 208 Z"
)
_MASK_D = (
    "M 299 221 C 263 158 182 161 158 231 C 127 310 162 370 222 405 L 299 465 L 379 405 C 444 366 478 304 442 229 "
    "C 413 162 338 161 299 221 Z"
)


def _skull() -> Plate:
    """The swept head: the two tufts' inner feathers, the teal collar of the face and the gold crest."""
    return [
        (shape(_HEAD_D, PLACE), NAVY),
        (shape("M 113 108 L 185 190 L 148 207 Z", PLACE), CORAL),
        (shape("M 491 96 L 423 191 L 459 209 Z", PLACE), TEAL),
        (
            shape(
                "M 126 333 Q 152 419 247 451 L 301 494 L 359 451 Q 452 417 475 331 "
                "Q 415 393 301 408 Q 188 393 126 333 Z",
                PLACE,
            ),
            TEAL,
        ),
        (shape("M 258 153 L 299 207 L 344 153 L 319 159 L 300 181 L 281 157 Z", PLACE), GOLD),
    ]


def _face() -> Plate:
    """The elongated mask, its pale brow and the coral darts on the cheeks: what slides over the head on a glance."""
    return [
        (shape(_MASK_D, PLACE), PAPER),
        (
            shape(
                "M 299 229 C 255 185 203 200 180 250 C 217 225 251 225 275 253 L 300 281 "
                "L 328 253 C 350 225 387 224 421 248 C 396 201 343 184 299 229 Z",
                PLACE,
            ),
            CREAM,
        ),
        (shape("M 165 347 L 197 365 L 164 371 Z", PLACE), CORAL),
        (shape("M 433 347 L 401 365 L 434 371 Z", PLACE), CORAL),
    ]


def _feet() -> Plate:
    return [
        (shape("M 224 801 L 239 886 L 255 883 L 251 805 Z", PLACE), GOLD),
        (shape("M 347 800 L 362 866 L 378 858 L 370 800 Z", PLACE), GOLD),
        (shape("M 245 880 Q 219 875 203 903 L 229 900 L 245 891 L 257 908 L 273 905 L 263 886 Z", PLACE), NAVY),
        (shape("M 368 852 Q 383 844 401 859 L 414 878 L 390 874 L 379 863 L 363 878 L 346 872 Z", PLACE), NAVY),
    ]


def _uniform(neck: str = "M 231 455 L 372 452", start: str = "231 455") -> Plate:
    """The tapered uniform; ``neck`` is its top, from ``start`` at the left shoulder to the right one."""
    out: Plate = [
        (
            shape(
                f"{neck} Q 430 497 425 566 L 397 705 L 426 800 L 320 852 "
                f"L 179 806 L 202 678 L 176 558 Q 173 497 {start} Z",
                PLACE,
            ),
            TEAL,
        ),
        (shape("M 218 474 L 268 481 L 247 692 L 270 815 L 179 806 L 202 678 L 176 558 Z", PLACE), NAVY),
        (shape("M 268 483 L 335 481 L 362 718 L 306 765 L 248 721 Z", PLACE), PAPER),
    ]
    for x, y, s in ((293.0, 556.0, 1.0), (307.0, 603.0, 1.0), (298.0, 650.0, 0.8)):
        out.append((shape("M -9 -5 L 0 5 L 9 -5 L 0 17 Z", PLACE.then(Frame(x, y, s))), GOLD))
    out.append((shape("M 210 738 L 262 759 L 252 783 L 205 766 Z", PLACE), CORAL))
    out.append((rule("M 356 742 L 395 729", 3.0, PLACE), MINT))
    return out + atom(381.0, 560.0, 0.42, PAPER, PLACE)


def _scarf() -> Plate:
    return [
        (shape("M 232 460 L 299 493 L 371 454 L 358 491 L 299 512 L 243 490 Z", PLACE), CORAL),
        (shape("M 349 486 L 388 501 L 438 601 L 397 584 L 389 611 L 333 511 Z", PLACE), CORAL),
        (shape("M 357 508 L 399 575 L 374 511 Z", PLACE), GOLD),
    ]


_SHOULDER = {"left": PLACE.point(181.0, 513.0), "right": PLACE.point(411.0, 511.0)}
_REST_PAW = {"left": (132.0, 794.0), "right": (238.0, 794.0)}  # the shared "desk" arms: she stands and presents
WING_W = 44.0
_WING = brush.Pressure(0.8, 0.55, 0.3, 0.0, 2.0)


def _left_wing(holding: bool) -> Plate:
    """The wing at her side, with the clicker in its feathers."""
    out: Plate = [
        (
            shape(
                "M 181 513 C 135 539 119 604 130 663 Q 142 712 191 724 L 211 701 Q 183 681 177 652 L 207 565 Z", PLACE
            ),
            TEAL,
        ),
        (shape("M 142 580 Q 138 636 165 668 L 179 671 Q 158 626 171 577 Z", PLACE), MINT),
        (
            shape(
                "M 182 676 Q 205 672 218 683 Q 224 696 209 702 Q 217 710 205 717 L 188 724 Q 172 707 171 687 Z", PLACE
            ),
            NAVY,
        ),
    ]
    if holding:
        out += clicker_art(PLACE.then(Frame(142.0, 619.0, 0.15)))
        out.append((shape("M 185 683 Q 197 677 211 687 L 209 696 L 189 694 Z", PLACE), TEAL))
    return out


def _right_wing() -> Plate:
    """The wing raised with its feathers spread, the way she presents."""
    return [
        (
            shape(
                "M 411 511 C 452 524 451 560 464 588 L 522 551 L 550 503 Q 560 486 567 500 L 566 527 "
                "L 595 500 Q 608 495 605 510 L 588 532 L 614 524 Q 631 529 609 541 L 588 553 "
                "L 609 551 Q 621 562 589 574 L 558 572 L 482 649 Q 459 664 438 641 L 397 571 Z",
                PLACE,
            ),
            TEAL,
        ),
        (shape("M 421 540 L 461 621 L 548 559 L 533 555 L 467 596 L 438 539 Z", PLACE), MINT),
    ]


def _feathers(paw: Point) -> Plate:
    """Three primary feathers at a wing's end, in ink, in the shape of the plate's wingtip."""
    x, y = paw
    return [
        (brush.ellipse(x + dx, y + dy, 16.0, 6.5, tilt), NAVY)
        for dx, dy, tilt in ((-10.0, 2.0, -28.0), (0.0, 7.0, 0.0), (10.0, 2.0, 28.0))
    ]


@dataclass(frozen=True)
class Lyra:
    """Her drawing of the :class:`srstudio.toon_cast.Drawing` contract. ``glance`` moves her irises as a share of a
    gaze (:class:`srstudio.toon_head.Glancing`), ``holding`` puts the clicker in her wing at rest. The tilt stays at
    naught: a head is turned by the rig, and a mood's turn by :func:`mood_plan`."""

    glance: tuple[float, float] = (0.0, 0.0)
    holding: bool = True

    @property
    def tilt(self) -> float:
        return 0.0

    def looking(self, dx: float, dy: float) -> Lyra:
        return replace(self, glance=(dx, dy))

    def foundation(self, look: Look) -> list[Layer]:
        return [*_feet(), *_uniform(), *_scarf(), *_skull(), *_face()]

    def eye(self, look: Look, centre: Point, kind: str, inner: float) -> list[Layer]:
        return _eye(_eyes_of(kind), 0 if inner > 0 else 1, self.glance)

    def lids(self, look: Look) -> list[Layer]:
        """The blink, tall enough for the wonder almond too: a band of paper a few frames long."""
        shut = replace(EYE_POSES["closed"].eyes, tall=84.0)
        return [layer for side in (0, 1) for layer in _eye(shut, side, (0.0, 0.0))[2:-1]]

    def mouth(self, look: Look, kind: str) -> list[Layer]:
        return _beak(_beak_of(kind))

    def viseme(self, look: Look, kind: str) -> list[Layer]:
        if kind not in _VISEMES:
            raise ToonDataError(f"{look.name}: no viseme {kind!r}; the speaking beaks are {tuple(_VISEMES)}")
        return _beak(BEAKS[_VISEMES[kind]])

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]:
        """A wing: at rest (the shared ``desk`` arms) the two the plates draw, her left at her side and her right
        raised; any other arm pose a tapered wing along the pose's line, from her own shoulder."""
        side = "left" if points[0][0] < CENTRE else "right"
        if tuple(paw) == _REST_PAW[side]:
            return _left_wing(self.holding) if side == "left" else _right_wing()
        path = [_SHOULDER[side], *points[1:]]
        return [
            (brush.stroke(path, WING_W, _WING), TEAL),
            (brush.stroke(path[1:] if len(path) > 2 else path, WING_W * 0.3, _WING), MINT),
            *_feathers(paw),
        ]


_MOUTH = PLACE.point(*GAPE_AT)
LYRA = Look(
    name="lyra",
    coat=TEAL,
    dark=NAVY,
    light=PAPER,
    silhouette=tuple(points(_SILHOUETTE_D, PLACE, 6)),
    eyes=(PLACE.point(EYE_CENTRES[0], EYE_Y), PLACE.point(EYE_CENTRES[1], EYE_Y)),
    eye_r=EYE_W * BOB,
    mouth=_MOUTH,
    mouth_w=44.0 * BOB,
    limb=WING_W,
    brows=True,
    shine=True,
    blink=3.4,
    drawing=Lyra(),
)
LYRA_MOTION = HeadStyle(  # an owl: the head snaps round, then stays; small quick nods, eyes that follow the head
    seed=6301,
    signature="^",
    nod_px=5.0,
    nod_roll=1.8,
    head=Spring(3.2, 0.55, 0.1),
    settle=Spring(1.4, 0.72),
    body=Spring(1.1, 0.95),
    min_gap=0.6,
    lean=0.5,
    follow=0.8,
    idle_roll=0.7,
    idle_px=0.6,
    idle_hz=0.13,
    breath_period=5.2,
    glance_every=2.6,
    glance_hold=1.9,
    glance_turn=6.0,
    glance_face=4.0,
    avert=0.6,
)
_NECKLINE = "M 232 432 Q 300 390 372 432"  # the uniform's top run up behind the head: no turn shows daylight beside the
# chin (the plain drawing's line, from 231 455 to 372 452, opens seven points of the seam at the rig's bounds)


def _trunk() -> Plate:
    return [*_feet(), *_uniform(_NECKLINE, "232 432"), *_scarf()]


LYRA_RIG = HeadRig(
    look=LYRA,
    neck=PLACE.point(300.0, 462.0),
    tilt=MOODS["welcome"].tilt,
    head=tuple(points(_HEAD_D, PLACE, 12)),
    cover=tuple(points(_NECKLINE, PLACE, 10)),
    skull=_skull,
    face=_face,
    trunk=_trunk,
    style=LYRA_MOTION,
    head_over=True,
)


def pose(start: float, name: str, arms: str = "desk") -> Pose:
    """A :class:`srstudio.toon.Pose` in a mood (its beak with it) or an eye pose (the welcome face's beak)."""
    if arms not in ARMS:
        raise ToonDataError(f"Lyra has no arms {arms!r}; the arms are {ARMS}")
    if name in MOODS:
        return Pose(start, name, name, arms)
    if name in EYE_POSES:
        return Pose(start, name, MOODS["welcome"].beak, arms)
    raise ToonDataError(f"Lyra has no mood or eye pose {name!r}; {tuple(MOODS)}, {tuple(EYE_POSES)}")


def mood_plan(poses: Sequence[Pose], duration: float, rig: HeadRig = LYRA_RIG) -> HeadPlan:
    """A still body whose head turns to each pose's mood over :data:`TURN_SECONDS` from the pose's start; an eye pose
    holds it level, and a word of the shared vocabulary leaves it where it was; a pose too short for the turn ends
    its turn before the next begins."""
    if not poses:
        raise ToonDataError("a mood plan needs poses")
    if not (checks.number(duration) and duration > poses[-1].start):
        raise ToonDataError(f"a mood plan ends after its last pose, got {duration!r}")

    def turn(p: Pose, held: float) -> float:
        if p.eyes in MOODS:
            return MOODS[p.eyes].tilt - rig.tilt
        return -rig.tilt if p.eyes in EYE_POSES else held

    held = turn(poses[0], 0.0)
    keys: list[tuple[float, float]] = [(poses[0].start, held)]
    ends = [p.start for p in poses[2:]] + [duration]
    for p, end in zip(poses[1:], ends, strict=True):
        target = turn(p, held)
        keys += [(p.start, held), (round(p.start + min(TURN_SECONDS, (end - p.start) * 0.8), 6), target)]
        held = target
    return HeadPlan(turn=Channel(tuple(keys), curve="cubic-in-out"))


_CONTRACT = PartContract(
    parameters=(
        (
            "poses",
            ParameterContract(
                items=ParameterContract(
                    fields=(("start", ParameterContract(unit="seconds", timebase="relative:enter", minimum=0)),)
                )
            ),
        ),
        ("enter", ParameterContract(unit="seconds", timebase="project", role="start", minimum=0)),
        (
            "duration",
            ParameterContract(
                unit="seconds", timebase="project", role="end", description="Exit time; must be greater than enter."
            ),
        ),
        ("taps", ParameterContract(items=ParameterContract(unit="seconds", timebase="project"))),
    ),
    capabilities=(("limbs", False), ("head_motion", False), ("expressions", True), ("mouths", True)),
    constraints=(
        "Pose starts are ordered relative to enter and begin at zero.",
        "duration is the project exit time, strictly after enter.",
        "Her wings are drawn with her, so limb tracks are refused.",
        "For procedural head motion use toon_head.figure with LYRA_RIG and a HeadPlan.",
    ),
)


@register(
    "character",
    "toon-lyra",
    summary="Lyra, the owl astronomy presenter: swept tufts, almond eyes, boomerang brows, a tapered uniform and a "
    "comet scarf, in flat print colour, with six moods, eight eye poses and a beak that speaks",
    contract=_CONTRACT,
)
def lyra(
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
    """Lyra through her rig with the head at rest, so a pose may name a mood or an eye pose; what moves her head is
    :func:`srstudio.toon_head.figure` with a plan. Her wings are drawn, so she takes no limb tracks."""
    if limbs:
        raise ToonDataError("Lyra's wings are drawn with her: she takes no limb tracks")
    return [rig_figure(cv, parent, LYRA_RIG, poses, duration, HeadPlan.still(), taps, enter, stickers, mouths)]
