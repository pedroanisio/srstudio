"""Soft closets: plain doors in the office's back wall, a mop, and the dark behind them with its one line of light.

:func:`doors` lays doors flat on the back wall in the room's own 3/4 view. Whoever stands in a doorway is drawn through
``between``, in front of the dark and behind the door, so a shut door really does hide them. :func:`closet` is the same
dark from inside: the frame nearly black, what stands in it drawn through ``behind``, and one bright slit of door crack
down it. Nothing here draws a face. Every refusal is a :class:`SoftClosetError`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import NamedTuple

from . import blob, checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["Door", "SoftClosetError", "closet", "doors", "mop"]

DARK = "#171A22"
LEAF, LEAF_INSET, TRIM = "#F2E4CC", "#E6D3B4", "#FBF4E6"
LINE = "#4A4636"
KNOB = "#C9A24E"
SWING = 74.0  # how far an open leaf stands off the wall, along it
SWING_DROP = 84.0  # and toward the viewer, in frame pixels
LEAN_LIMIT = 80.0
POLE, STRANDS = "#B98A5E", "#E8E0CE"


class SoftClosetError(SrstudioError, ValueError):
    """A door, a mop or a closet asked for with arguments it cannot be drawn from."""


class Door(NamedTuple):
    """A door on the back wall from ``a0`` to ``a1`` along it, ``up`` tall, shut through the ``shut`` spans."""

    a0: float
    a1: float
    up: float
    shut: Sequence[tuple[float, float]]
    hinge: str = "left"


def _check_door(door: Door) -> None:
    if not all(checks.number(v) for v in (door.a0, door.a1, door.up)) or door.a0 >= door.a1 or door.up <= 0:
        raise SoftClosetError(f"a door runs from a0 to a later a1 and has a height, got {door!r}")
    if door.hinge not in ("left", "right"):
        raise SoftClosetError(f"a door hinges on the left or the right, got {door.hinge!r}")
    for span in door.shut:
        if not (len(span) == 2 and all(checks.number(v) for v in span) and 0 <= span[0] < span[1]):
            raise SoftClosetError(f"a door's shut span needs 0 <= start < end, got {span!r}")


def _open_spans(door: Door, end: float) -> list[tuple[float, float]]:
    out, at = [], 0.0
    for a, b in sorted(door.shut):
        if a > at:
            out.append((at, a))
        at = b
    if at < end:
        out.append((at, end))
    return out


def _leaf(cv: Canvas, g, door: Door) -> None:
    blob._quad(cv, g, blob.wall_quad("back", door.a0, door.a1, 0, door.up), LEAF, LINE, 4)
    width = door.a1 - door.a0
    for u0, u1 in ((0.1, 0.46), (0.54, 0.9)):
        quad = blob.wall_quad("back", door.a0 + width * 0.16, door.a1 - width * 0.16, door.up * u0, door.up * u1)
        blob._quad(cv, g, quad, LEAF_INSET, LINE, 2)
    knob_at = door.a1 - 26 if door.hinge == "left" else door.a0 + 26
    x, y = blob.room_point(knob_at, 0, door.up * 0.47)
    cv.ellipse(g, x - 11, y - 11, 22, 22, KNOB, LINE, 3)


def _swung(cv: Canvas, g, door: Door) -> None:
    pin = door.a0 if door.hinge == "left" else door.a1
    sign = -1.0 if door.hinge == "left" else 1.0
    foot, head = blob.room_point(pin, 0, 0), blob.room_point(pin, 0, door.up)
    far = (foot[0] + sign * SWING, foot[1] + SWING_DROP), (head[0] + sign * SWING, head[1] + SWING_DROP * 0.55)
    blob._quad(cv, g, [foot, far[0], far[1], head], LEAF, LINE, 4)
    cv.ellipse(g, far[0][0] - sign * 18 - 9, (far[0][1] + far[1][1]) / 2 - 9, 18, 18, KNOB, LINE, 3)


@register(
    "prop",
    "soft-door",
    style="soft",
    summary="Plain paneled doors on the office's back wall, opening on a dark closet that can hide someone",
)
def doors(
    cv: Canvas,
    parent,
    rows: Sequence[Door] = (Door(150.0, 340.0, 640.0, ()),),
    *,
    end: float = 8.0,
    between: Callable[[object], object] | None = None,
    id: str = "soft-door",
):
    """Each door in ``rows``, open from the first frame to ``end`` except through its ``shut`` spans. ``between`` draws
    in front of the dark and behind the doors."""
    if not rows:
        raise SoftClosetError("doors need at least one door")
    if between is not None and not callable(between):
        raise SoftClosetError(f"between draws who stands in a doorway and must be callable, got {between!r}")
    for door in rows:
        _check_door(door)
    for a, b in zip(sorted(rows), sorted(rows)[1:], strict=False):
        if b.a0 < a.a1:
            raise SoftClosetError(f"two doors cannot share a stretch of wall, got {a!r} and {b!r}")
    g = cv.group(parent, id)
    for k, door in enumerate(rows):
        frame = blob.wall_quad("back", door.a0 - 14, door.a1 + 14, 0, door.up + 14)
        blob._quad(cv, g, frame, TRIM, LINE, 4)
        dark = cv.group(g, f"{id}-dark-{k}")
        blob._quad(cv, dark, blob.wall_quad("back", door.a0, door.a1, 0, door.up), DARK, LINE, 3)
    if between is not None:
        between(cv.group(g, f"{id}-between"))
    else:
        cv.group(g, f"{id}-between")
    for k, door in enumerate(rows):
        shut = cv.group(g, f"{id}-shut-{k}")
        if door.shut:
            cv.gate(shut, list(door.shut))
        else:
            cv.gate(shut, [(0.0, end)])
        _leaf(cv, shut, door)
        opened = _open_spans(door, end) if door.shut else []
        if opened:
            swung = cv.group(g, f"{id}-open-{k}")
            cv.gate(swung, opened)
            _swung(cv, swung, door)
    return g


@register("prop", "soft-mop", style="soft", summary="A string mop standing on its head, that can tip over, slowly")
def mop(
    cv: Canvas,
    parent,
    x: float = 540,
    y: float = 1500,
    *,
    scale: float = 1.0,
    lean: float = 6.0,
    tips: tuple[float, float] | None = None,
    to: float = 58.0,
    id: str = "soft-mop",
):
    """Its head on the floor at (``x``, ``y``), ``lean`` degrees off upright, 620 tall at scale 1. ``tips`` (start, end)
    takes it over, pivoting on its head, to ``to`` degrees."""
    if not (checks.number(scale) and scale > 0):
        raise SoftClosetError(f"a mop's scale must be a positive number, got {scale!r}")
    if not (checks.number(lean) and abs(lean) <= LEAN_LIMIT):
        raise SoftClosetError(f"a mop leans up to {LEAN_LIMIT} degrees, got {lean!r}")
    if tips is not None and not (all(checks.number(v) for v in tips) and 0 <= tips[0] < tips[1]):
        raise SoftClosetError(f"a mop tips from a start to a later end, got {tips!r}")
    if not (checks.number(to) and abs(to) <= 180):
        raise SoftClosetError(f"a mop tips to at most 180 degrees, got {to!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=lean)
    if tips is not None:
        cv.keys(g, "rotation", [(0.0, lean), (tips[0], lean), (tips[1], to)], kind="sine-in")
    cv.path(g, "M -7 -620 L 7 -620 L 7 -60 L -7 -60 Z", POLE, ink, 4)
    cv.rect(g, -40, -74, 80, 26, "#5D8FD0", ink, 4, radius=8)
    for k in range(-3, 4):
        cv.path(g, f"M {k * 11} -50 Q {k * 22} -22 {k * 26} 0", stroke=ink, sw=17)
    for k in range(-3, 4):
        cv.path(g, f"M {k * 11} -50 Q {k * 22} -22 {k * 26} 0", stroke=STRANDS, sw=10)
    return g


@register(
    "prop",
    "soft-closet",
    style="soft",
    summary="The inside of a shut closet: the frame nearly black, with one line of light down the crack of the door",
)
def closet(
    cv: Canvas,
    parent,
    start: float = 0.0,
    end: float = 8.0,
    *,
    slit: tuple[float, float] = (620.0, 668.0),
    veil: float = 0.94,
    behind: Callable[[object], object] | None = None,
    id: str = "soft-closet",
):
    """The whole frame from ``start`` to ``end``. ``behind`` draws what stands in the closet; the dark goes on over it
    on both sides of ``slit`` (left, right), so only what crosses the line of light shows plainly."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise SoftClosetError(f"a closet needs 0 <= start < end, got {start!r} to {end!r}")
    if not (all(checks.number(v) for v in slit) and 0 < slit[0] < slit[1] < cv.width):
        raise SoftClosetError(f"a slit lies inside the frame, left of its right edge, got {slit!r}")
    if not (checks.number(veil) and 0 < veil <= 1):
        raise SoftClosetError(f"a veil's opacity is 0..1, got {veil!r}")
    if behind is not None and not callable(behind):
        raise SoftClosetError(f"behind draws what stands in the closet and must be callable, got {behind!r}")
    g = cv.group(parent, id)
    cv.gate(g, [(start, end)])
    over = 200.0  # past the frame, so a slow push stays dark to the edge
    cv.rect(g, -over, -over, cv.width + 2 * over, cv.height + 2 * over, "#3A3D47")
    if behind is not None:
        behind(g)
    left, right = slit
    cv.rect(g, -over, -over, left + over, cv.height + 2 * over, DARK, opacity=veil)
    cv.rect(g, right, -over, cv.width - right + over, cv.height + 2 * over, DARK, opacity=veil)
    light = cv.group(g, f"{id}-light")
    cv.rect(light, left, -over, right - left, cv.height + 2 * over, "#FFE9BE", opacity=0.14)
    cv.line(light, left, -over, left, cv.height + over, "#FFF3D2", 3)
    cv.line(light, right, -over, right, cv.height + over, "#FFF3D2", 3)
    return g
