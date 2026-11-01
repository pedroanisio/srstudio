"""A Cutout arm that bends: a hand on a timed track, an elbow, and two strokes of a fixed length.

The office and café rigs draw two-stroke arms that hang at their sides. A hand that reaches for a hat, passes a lanyard
or picks up a phone is drawn here instead, in the actor's own units when ``parent`` is ``who.group``, with the actor's
own arm hidden for those seconds. The hand goes through the (time, x, y) points of ``track`` and the elbow is solved for
every frame, so the arm keeps its length and the hand keeps its time. A point the arm cannot reach is refused by its
time rather than stretched. Every refusal is a :class:`CutoutArmError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import checks
from .canvas import Canvas
from .errors import SrstudioError

__all__ = ["Arm", "CutoutArmError", "angles", "arm", "hand_at"]

RATE = 30  # samples a second: a reel's frame rate, so the elbow never lags the hand
UPPER = 130.0  # shoulder to elbow, in the rig's units
FORE = 130.0  # elbow to wrist

Track = Sequence[tuple[float, float, float]]


class CutoutArmError(SrstudioError, ValueError):
    """An arm asked for with a track or a length it cannot be drawn from."""


@dataclass(frozen=True)
class Arm:
    """``group`` is the shoulder, gate it to show the arm; ``grip`` follows the hand without turning, for what it
    carries; ``rotations`` are the shoulder's (time, degrees) keys."""

    group: Any
    grip: Any
    rotations: list[tuple[float, float]]


def _ease(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * u)


def hand_at(track: Track, t: float) -> tuple[float, float]:
    """Where the hand is at ``t``: held at each end of the track, eased between its points."""
    if t <= track[0][0]:
        return track[0][1], track[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(track, track[1:], strict=False):
        if t <= t1:
            u = _ease((t - t0) / (t1 - t0))
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
    return track[-1][1], track[-1][2]


def angles(
    shoulder: tuple[float, float], upper: float, fore: float, hand: tuple[float, float], bend: int
) -> tuple[float, float]:
    """The shoulder's rotation and the elbow's, in degrees, that end the forearm on ``hand``. ``bend`` is +1 or -1, the
    side the elbow goes. A hand out of the arm's reach raises :class:`CutoutArmError`."""
    dx, dy = hand[0] - shoulder[0], hand[1] - shoulder[1]
    span = math.hypot(dx, dy)
    if not abs(upper - fore) < span < upper + fore:
        raise CutoutArmError(f"a hand {span:.1f} from the shoulder is out of an arm of {upper:g} and {fore:g}")
    elbow = math.acos((span**2 - upper**2 - fore**2) / (2 * upper * fore)) * bend
    aim = math.atan2(dy, dx) - math.atan2(fore * math.sin(elbow), upper + fore * math.cos(elbow))
    return math.degrees(aim), math.degrees(elbow)


def _check(track: Track, upper: float, fore: float, bend: int, width: float, hand: float) -> None:
    if not track:
        raise CutoutArmError("an arm needs at least one (time, x, y) point")
    if any(len(point) != 3 or not all(checks.number(v) for v in point) for point in track):
        raise CutoutArmError(f"an arm's track is (time, x, y) points of finite numbers, got {track!r}")
    if any(b[0] <= a[0] for a, b in zip(track, track[1:], strict=False)):
        raise CutoutArmError(f"an arm's track runs in rising time, got {[p[0] for p in track]!r}")
    for value, name in ((upper, "upper"), (fore, "fore"), (width, "width"), (hand, "hand")):
        checks.positive(value, CutoutArmError, f"{name} must be a positive number, got {value!r}")
    if bend not in (1, -1):
        raise CutoutArmError(f"an elbow bends +1 or -1, got {bend!r}")


def _samples(track: Track) -> list[float]:
    start, end = track[0][0], track[-1][0]
    frames = {round(start + k / RATE, 4) for k in range(int((end - start) * RATE) + 1)}
    return sorted(frames | {p[0] for p in track})


def _unwrapped(values: list[float]) -> list[float]:
    out: list[float] = []
    for value in values:
        out.append(value + 360 * round((out[-1] - value) / 360) if out else value)
    return out


def arm(
    cv: Canvas,
    parent,
    id: str,
    shoulder: tuple[float, float],
    track: Track,
    *,
    upper: float = UPPER,
    fore: float = FORE,
    bend: int = 1,
    width: float = 5.0,
    hand: float = 44.0,
    finger: bool = False,
    skin: str | None = None,
) -> Arm:
    """Draw the arm from ``shoulder`` to the hand at ``track``'s (time, x, y) points, in ``parent``'s units. ``finger``
    gives the hand one finger out, to poke with. ``skin`` colours the hand (default: white, as the office rig's)."""
    _check(track, upper, fore, bend, width, hand)
    if skin is not None and (not isinstance(skin, str) or not skin):
        raise CutoutArmError(f"skin is a nonempty colour string, got {skin!r}")
    colour = cv.white if skin is None else skin
    times = _samples(track)
    poses = []
    for t in times:
        try:
            poses.append(angles(shoulder, upper, fore, hand_at(track, t), bend))
        except CutoutArmError as error:
            raise CutoutArmError(f"at {t:g} s: {error}") from None
    turns = _unwrapped([a for a, _ in poses])
    bends = _unwrapped([b for _, b in poses])
    shoulder_group = cv.group(parent, id, x=shoulder[0], y=shoulder[1], rotation=turns[0])
    rotations = list(zip(times, turns, strict=True))
    cv.keys(shoulder_group, "rotation", rotations, hold=False)
    cv.line(shoulder_group, 0, 0, upper, 0, cv.ink, width)
    forearm = cv.group(shoulder_group, f"{id}-forearm", x=upper, rotation=bends[0])
    cv.keys(forearm, "rotation", list(zip(times, bends, strict=True)), hold=False)
    cv.line(forearm, 0, 0, fore, 0, cv.ink, width)
    if finger:
        cv.path(forearm, f"M{fore + hand * 0.3:g} -5 L{fore + hand * 1.1:g} -4 Q{fore + hand * 1.26:g} 0 "
                         f"{fore + hand * 1.1:g} 5 L{fore + hand * 0.3:g} 6Z", colour, cv.ink, 3)  # fmt: skip
    cv.ellipse(forearm, fore - hand / 2, -hand * 0.46, hand, hand * 0.92, colour, cv.ink, 3.5)
    x0, y0 = hand_at(track, times[0])
    grip = cv.group(parent, f"{id}-grip", x=x0, y=y0)
    cv.keys(grip, "x", [(t, hand_at(track, t)[0]) for t in times], hold=False)
    cv.keys(grip, "y", [(t, hand_at(track, t)[1]) for t in times], hold=False)
    return Arm(shoulder_group, grip, rotations)
