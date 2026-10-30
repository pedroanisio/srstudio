"""Camera moves on a setup group: the group's anchor becomes the point the lens pushes toward."""

from __future__ import annotations

import math

from . import checks
from .canvas import Canvas, Keys
from .errors import SrstudioError


class CameraError(SrstudioError, ValueError):
    """A camera move that cannot play: a time, scale or duration out of range, a snap too slow to be one."""


def anchor(group, x: float, y: float, *, place: bool = False):
    """Set the pivot of a setup; with ``place`` also sets x/y so the group does not move."""
    group.anchorX = x
    group.anchorY = y
    if place:
        group.x = x
        group.y = y


def push_in(cv: Canvas, group, *, x: Keys = (), y: Keys = (), scale: Keys = (), hold_scale: bool = False):
    """Keys for a push-in: position keys hold (a cut), scale keys ease unless ``hold_scale``."""
    if x:
        cv.keys(group, "x", x)
    if y:
        cv.keys(group, "y", y)
    if scale:
        cv.keys(group, "scaleX", scale, hold=hold_scale)
        cv.keys(group, "scaleY", scale, hold=hold_scale)


SNAP = 0.25  # seconds: a scale change at least this fast is a crash zoom; slower is a push (srstudio.craft agrees)


def crash_zoom(
    cv: Canvas,
    group,
    at: float,
    scale: float,
    *,
    duration: float = 0.15,
    start_scale: float = 1.0,
    back: float | None = None,
) -> float:
    """A crash (snap) zoom: ``group`` holds ``start_scale``, then snaps to ``scale`` over ``duration`` from ``at``;
    with ``back`` it snaps out again at that time. Set the pivot first with :func:`anchor`. Returns ``at``, the cue
    for the whoosh or sting that sells the move (:func:`srstudio.foley.whoosh`). A move slower than :data:`SNAP` is
    a push: use :func:`push_in`."""
    if not (checks.number(at) and at >= 0):
        raise CameraError(f"crash zoom: at {at} must be a time >= 0")
    if not (checks.number(scale) and scale > 0 and checks.number(start_scale) and start_scale > 0):
        raise CameraError(f"crash zoom: scale {scale} and start_scale {start_scale} must be > 0")
    if not (checks.number(duration) and duration > 0):
        raise CameraError(f"crash zoom: duration {duration} must be > 0")
    if duration > SNAP:
        raise CameraError(f"crash zoom: {duration} s is slower than a snap ({SNAP} s); use push_in for a push")
    if back is not None and not (checks.number(back) and back >= at + duration):
        raise CameraError(f"crash zoom: back {back} must come after the zoom lands at {at + duration}")
    keys: list[tuple[float, float]] = [(0, start_scale), (at, start_scale), (at + duration, scale)]
    if back is not None:
        keys += [(back, scale), (back + duration, start_scale)]
    keys = [k for i, k in enumerate(keys) if i == 0 or k[0] > keys[i - 1][0]]  # at == 0 needs no lead-in key
    cv.keys(group, "scaleX", keys, hold=False)
    cv.keys(group, "scaleY", keys, hold=False)
    return at


def zoom_holds(cv: Canvas, group, scale: Keys):
    """Per-shot zoom levels that change on the cut (hold keys)."""
    cv.keys(group, "scaleX", scale)
    cv.keys(group, "scaleY", scale)


def reframe(cv: Canvas, group, moves: list[tuple[float, float, float, float]]):
    """``(time, scale, x, y)`` rows applied as hold keys: the café's cut-to-cut reframing."""
    for prop, column in [("scaleX", 1), ("scaleY", 1), ("x", 2), ("y", 3)]:
        cv.keys(group, prop, [(row[0], row[column]) for row in moves])


EDGE_ON = 0.03  # narrowest scaleX of a turn: a sliver, never a zero-width (singular) transform


def spin(cv: Canvas, group, start: float, turns: int = 2, period: float = 0.9, fps: int = 30):
    """Turn ``group`` about its vertical axis: scaleX follows |cos| of the angle, one key per frame.

    The flat group cannot show its far side, so the turn reports when the near side changes:
    ``[(time, "back"|"front"), ...]`` at each edge-on moment. Pass it to :func:`show_facing`."""
    if turns < 1 or period <= 0 or fps <= 0:
        raise CameraError(f"spin needs turns >= 1, period > 0 and fps > 0 (got {turns}, {period}, {fps})")
    total = turns * period
    frames = math.ceil(total * fps - 1e-9)
    values: list[tuple[float, float]] = [(0, 1), (start, 1)]
    for f in range(1, frames):
        t = f / fps
        values.append((start + t, round(max(abs(math.cos(2 * math.pi * t / period)), EDGE_ON), 6)))
    values.append((start + total, 1))
    cv.keys(group, "scaleX", values, hold=False)
    facing = []
    for k in range(2 * turns):
        facing.append((start + period / 4 + k * period / 2, "back" if k % 2 == 0 else "front"))
    return facing


def show_facing(cv: Canvas, front, back, facing):
    """Hold-key visibility for the two sides of a spinning group, from :func:`spin`'s report."""
    front_keys, back_keys = [(0, 1)], [(0, 0)]
    for t, side in facing:
        front_keys.append((t, int(side == "front")))
        back_keys.append((t, int(side == "back")))
    cv.keys(front, "opacity", front_keys)
    cv.keys(back, "opacity", back_keys)
