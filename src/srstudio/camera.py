"""Camera moves on a setup group: the group's anchor becomes the point the lens pushes toward."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from . import checks
from ._transaction import scene_transaction
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


def push_in(
    cv: Canvas,
    group,
    *,
    x: Keys = (),
    y: Keys = (),
    scale: Keys = (),
    hold_scale: bool = False,
    curve: str = 'sine-in-out',
):
    """Position keys hold (a cut); scale keys use ``curve``, defaulting to sine-in-out easing.

    ``curve='linear'`` retains the previous constant-speed behavior. ``hold_scale`` overrides the curve with
    held scale keys. All keys follow the canvas clock; invalid input leaves the scene unchanged.
    """
    held_count = len(cv._held)
    try:
        with scene_transaction(cv.scene, cv):
            if x:
                cv.keys(group, "x", x)
            if y:
                cv.keys(group, "y", y)
            if scale:
                for prop in ('scaleX', 'scaleY'):
                    cv.keys(group, prop, scale, kind='hold' if hold_scale else curve)
    except Exception:
        del cv._held[held_count:]
        raise


WHIP = 0.14  # seconds a whip pan takes to leave a shot, and to land in the next
WHIP_BANDS = 14  # the paper streaks that cover the cut
WHIP_RUN = 700.0  # px each streak travels while it shows


def whip(cv: Canvas, group, at: float, *, leaving: bool, direction: int = -1, width: float = 1080.0) -> float:
    """One side of a whip pan cut at project second ``at``, for shots drawn as groups (a ``<sequence>`` has the native
    ``whip-pan`` transition, :func:`srstudio.native.transition`): a ``leaving`` shot runs off the frame towards
    ``direction`` (-1 left, 1 right) over the last :data:`WHIP` seconds, the next shot arrives from the other side over
    the first. ``group`` must hold no other ``x`` keys. Returns ``at``, the cue for a whoosh."""
    if not (checks.number(at) and at >= WHIP):
        raise CameraError(f"whip: at {at} must leave {WHIP} s before the cut")
    if direction not in (-1, 1):
        raise CameraError(f"whip: direction is -1 or 1, got {direction!r}")
    if leaving:
        cv.keys(group, "x", [(round(at - WHIP, 6), 0.0), (at, direction * width)], kind="cubic-in")
    else:
        cv.keys(group, "x", [(at, -direction * width), (round(at + WHIP, 6), 0.0)], kind="cubic-out")
    return at


def whip_streaks(
    cv: Canvas, parent, at: float, colours: Sequence[str], *, direction: int = -1, seed: int = 0
) -> object:
    """Horizontal streaks over the frame, fading up to the cut at ``at`` and away after it, in ``colours``, moving
    towards ``direction``: what the eye gets instead of the empty frame between two shots of a :func:`whip`. Draw them
    over the shots. Returns the group."""
    if not colours:
        raise CameraError("whip: the streaks need at least one colour")
    rng = random.Random(seed)
    g = cv.group(parent, cv.uid("whip-streaks"))
    a, b = round(at - WHIP, 6), round(at + WHIP, 6)
    cv.keys(g, "opacity", [(a, 0.0), (at, 1.0), (b, 0.0)], hold=False)
    tall = cv.height / WHIP_BANDS
    for i in range(WHIP_BANDS):
        band = cv.rect(g, -WHIP_RUN, i * tall, cv.width + 2 * WHIP_RUN, tall + 1, rng.choice(list(colours)))
        run = direction * WHIP_RUN * rng.uniform(0.5, 1.0)
        cv.keys(band, "x", [(a, -run), (b, run)], hold=False)
    return g


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
    """``(time, scale, x, y)`` rows applied as hold keys: the café's cut-to-cut reframing.

    Keys follow the canvas clock. Invalid input leaves the scene and held-frame bookkeeping unchanged,
    so callers can correct the moves and retry on the same group.
    """
    columns = [
        (prop, [(row[0], row[column]) for row in moves])
        for prop, column in [("scaleX", 1), ("scaleY", 1), ("x", 2), ("y", 3)]
    ]
    held_count, held_rate = len(cv._held), cv._held_rate
    try:
        with scene_transaction(cv.scene, cv):
            for prop, keys in columns:
                cv.keys(group, prop, keys)
    except Exception:
        del cv._held[held_count:]
        cv._held_rate = held_rate
        raise


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
