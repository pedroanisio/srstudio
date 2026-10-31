"""A Cutout arm that follows a hand: reach across a frame without a limb rig.

An actor's drawn arms end where they end. A reel that needs a hand on someone's wrist, on a cup, or on a thing it picks
up draws this arm above both actors, with the actor's own left out (``free_arms`` on the café cast). The hand goes
through the (time, x, y) points of ``track``, easing between them, and the arm stays straight from the fixed shoulder
to the hand: its angle and length are sampled from the same curve, so the two cannot part. Every refusal is a
:class:`ReachError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError

__all__ = ["ReachError", "carried", "hand_at", "reach"]

RATE = 30  # samples a second: the frame rate of a reel, so the arm never lags the hand by a frame
UNIT = 100.0  # the length of the drawn arm before its scale


class ReachError(SrstudioError, ValueError):
    """A reach asked for with a track or a shoulder it cannot be drawn from."""


def _ease(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * u)


def hand_at(track: Sequence[tuple[float, float, float]], t: float) -> tuple[float, float]:
    """Where the hand is at ``t``: held at each end of the track, eased between its points."""
    if t <= track[0][0]:
        return track[0][1], track[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(track, track[1:], strict=False):
        if t <= t1:
            u = _ease((t - t0) / (t1 - t0))
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
    return track[-1][1], track[-1][2]


def _check(shoulder, track) -> None:
    if len(track) < 1:
        raise ReachError("a reach needs at least one (time, x, y) point")
    if any(
        len(point) != 3 or not all(isinstance(v, int | float) and math.isfinite(v) for v in point) for point in track
    ):
        raise ReachError(f"a reach's track is (time, x, y) points of finite numbers, got {track!r}")
    if any(b[0] <= a[0] for a, b in zip(track, track[1:], strict=False)):
        raise ReachError(f"a reach's track runs in rising time, got {[p[0] for p in track]!r}")
    near = min(math.hypot(x - shoulder[0], y - shoulder[1]) for _, x, y in track)
    if near < 1:
        raise ReachError(f"a hand on the shoulder {shoulder!r} has no arm to draw")


def reach(
    cv: Canvas,
    parent,
    id: str,
    shoulder: tuple[float, float],
    track: Sequence[tuple[float, float, float]],
    *,
    skin: str = "#F1D0AA",
    width: float = 7.5,
    hand: float = 34.0,
    sleeve: str | None = None,
):
    """Draw the arm from ``shoulder`` to the hand at ``track``'s (time, x, y) points, in ``parent``'s pixels. ``sleeve``
    is a colour for a cloth arm, wider than the ink line. Returns (arm group, hand group): gate them both, or the
    parent, to show it, and hang what the hand carries from the hand group."""
    _check(shoulder, track)
    start, end = track[0][0], track[-1][0]
    points = sorted({round(start + k / RATE, 4) for k in range(int((end - start) * RATE) + 1)} | {p[0] for p in track})
    sx, sy = shoulder
    at = [(t, *hand_at(track, t)) for t in points]
    x0, y0 = at[0][1], at[0][2]
    arm = cv.group(parent, id, x=sx, y=sy, rotation=math.degrees(math.atan2(y0 - sy, x0 - sx)),
                   scaleX=math.hypot(x0 - sx, y0 - sy) / UNIT)  # fmt: skip
    angles: list[float] = []
    for _, x, y in at:  # unwrapped, so an arm crossing straight left does not spin the long way round
        a = math.degrees(math.atan2(y - sy, x - sx))
        if angles:
            a += 360 * round((angles[-1] - a) / 360)
        angles.append(a)
    cv.keys(arm, "rotation", list(zip(points, angles, strict=True)), hold=False)
    cv.keys(arm, "scaleX", [(t, math.hypot(x - sx, y - sy) / UNIT) for t, x, y in at], hold=False)
    if sleeve is not None:
        cv.line(arm, 0, 0, UNIT, 0, cv.ink, width * 3.4)
        cv.line(arm, 0, 0, UNIT, 0, sleeve, width * 2.6)
    else:
        cv.line(arm, 0, 0, UNIT, 0, cv.ink, width)
    grip = cv.group(parent, f"{id}-hand", x=x0, y=y0)
    cv.keys(grip, "x", [(t, x) for t, x, _ in at], hold=False)
    cv.keys(grip, "y", [(t, y) for t, _, y in at], hold=False)
    cv.ellipse(grip, -hand / 2, -hand * 0.56, hand, hand * 1.12, skin, cv.ink, 3.5)
    return arm, grip


def carried(
    cv: Canvas,
    node,
    track: Sequence[tuple[float, float, float]],
    take: float,
    put: float,
    *,
    rest: tuple[float, float],
    lands: tuple[float, float] | None = None,
) -> None:
    """Key ``node``'s x and y: at ``rest`` until the hand takes it at ``take``, in the hand along ``track`` until
    ``put``, then at ``lands``, or where the hand let go. For a thing a hand picks up off one actor and sets down."""
    if len(track) < 1 or not checks.number(take) or not checks.number(put) or not take < put:
        raise ReachError(f"a hand takes a thing and puts it down later, got {take!r} and {put!r}")
    if take < track[0][0] or put > track[-1][0]:
        raise ReachError(f"the hand is on its track from {track[0][0]} to {track[-1][0]}, got {take} to {put}")
    if not all(checks.number(v) for v in (*rest, *(lands or ()))):
        raise ReachError(f"a carried thing rests at finite places, got {rest!r} and {lands!r}")
    samples = sorted({round(take + k / RATE, 4) for k in range(int((put - take) * RATE) + 1) if k} | {put})
    path = [(t, hand_at(track, t)) for t in samples if t < put]
    last = lands if lands is not None else hand_at(track, put)
    for axis, prop in enumerate(("x", "y")):
        keys = [(0.0, rest[axis]), (take, rest[axis]), *((t, at[axis]) for t, at in path), (put, last[axis])]
        cv.keys(node, prop, keys, hold=False)
