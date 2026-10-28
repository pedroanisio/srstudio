"""Camera moves on a setup group: the group's anchor becomes the point the lens pushes toward."""

from __future__ import annotations

import math

from .canvas import Canvas, Keys


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
        raise ValueError(f"spin needs turns >= 1, period > 0 and fps > 0 (got {turns}, {period}, {fps})")
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
