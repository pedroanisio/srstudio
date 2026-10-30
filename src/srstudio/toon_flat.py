"""Toon in a shared flat that has been cleaned the way a roommate cleans: everything moved out of sight. A pale wall,
and behind the character the place it went: :func:`closet`, :func:`oven`, :func:`shower`, :func:`front_door`, each
opening at a given second. :func:`pile` is what comes out, rising over whoever is in shot and drawn before a
:func:`srstudio.toon_world.ledge` so the signature (ADR 0001) stays on top; :func:`tiny_drawer` sits on that ledge.
:func:`whirl` spins a character into a shot and :func:`sparkles` says the room is spotless.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), every key is on the composition clock.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_sets import _inked, _line

__all__ = [
    "BURST",
    "PLATE_RUN",
    "closet",
    "flat",
    "front_door",
    "oven",
    "pile",
    "plates",
    "shower",
    "sparkles",
    "tiny_drawer",
    "whirl",
]

Point = tuple[float, float]
WALL, WALL_LOW, SKIRT = "#fbf3d9", "#f4e6bd", "#ffffff"
DOOR, DOOR_LINE, DOOR_DARK, KNOB = "#e9dcc3", "#c9b896", "#2e2a3a", "#c9a23c"
STEEL, STEEL_DARK, GLASS, RING = "#cfd5dc", "#9aa3ad", "#2d3340", "#e2483d"
TILE, TILE_LINE, CURTAIN, CURTAIN_FOLD, RAIL = "#d4edf0", "#b1d7dc", "#f28e7a", "#d76e5c", "#8c919a"
BIN, BIN_LID, BIN_DARK, BAG = "#4a7a58", "#3a6146", "#2c4a36", "#2f3038"
HALL, BOX, BOX_DARK = "#3a3247", "#b98a55", "#94683a"
PLATE, PLATE_RIM = "#f1f4f8", "#7fa6c9"
GARMENTS = ("#e2483d", "#2f6bb0", "#f0b429", "#4f9a5b", "#b06ab3", "#f28e7a", "#6d7f92", "#fafafa")
WHIRL_A, WHIRL_B = "#7f8ea0", "#a3b0be"  # close in value: a fast spin must not flash
SPARKLE = "#ffffff"
CABINET, CABINET_DARK, SOCK, SOCK_STRIPE = "#b98a55", "#94683a", "#fafafa", "#e2483d"
BURST = 0.18  # seconds a door takes to fly open
PLATE_RUN = 0.42  # seconds a plate takes to leave the frame
RISE = 0.55  # seconds the pile takes to rise
# (x, y from the pile's top, size, colour index): the garments on a pile
LOAD: tuple[tuple[float, float, float, int], ...] = (
    (-10, 60, 150, 0), (120, 30, 130, 1), (240, 70, 150, 2), (360, 34, 140, 3), (480, 66, 150, 4), (590, 40, 120, 5),
    (60, 170, 170, 6), (200, 150, 160, 7), (340, 170, 170, 0), (470, 150, 170, 1), (580, 180, 130, 2),
    (0, 300, 190, 3), (150, 290, 190, 4), (300, 300, 190, 5), (450, 290, 190, 6), (590, 300, 170, 7),
)  # fmt: skip


def _opening(at: float, what: str) -> None:
    if not (checks.number(at) and at >= 0):
        raise ToonDataError(f"{what} opens at a second, got {at!r}")


def _door(cv: Canvas, parent, x: float, y: float, w: float, h: float, at: float | None, hinge: float, leaf: str):
    """A leaf from ``(x, y)`` hung on ``hinge``, flying open at ``at`` (None: it stays shut)."""
    g = cv.group(parent, cv.uid("g"), x=fx(hinge), y=fy(y), anchorX=fx(hinge), anchorY=fy(y))
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), leaf, cv.ink, INK_W, radius=0)
    if at is not None:
        cv.keys(g, "scaleX", [(0.0, 1.0), (at, 1.0), (at + BURST, 0.14)], hold=False)
    return g


@register("location", "toon-flat", summary="A shared flat's pale wall, spotless")
def flat(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    paint = cv.grad("toon-flat-wall", [(0.0, WALL), (1.0, WALL_LOW)], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, paint)
    cv.rect(g, fx(-10), fy(780), fh(612), fh(34), SKIRT, cv.ink, FINE_W / 2, radius=0)


@register("prop", "toon-closet", summary="A closet door that bursts open on a dark inside")
def closet(cv: Canvas, parent, at: float = 1.0) -> None:
    _opening(at, "a closet")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(340), fy(300), fh(262), fh(490), DOOR_DARK, cv.ink, INK_W, radius=0)
    leaf = _door(cv, g, 348, 306, 250, 478, at, 598, DOOR)
    for y in range(330, 770, 32):
        _line(cv, leaf, [(366, y), (582, y)], 5.0, DOOR_LINE)
    cv.ellipse(leaf, fx(362), fy(530), fh(20), fh(20), KNOB, cv.ink, FINE_W / 2)


@register("prop", "toon-oven", summary="An oven whose door drops open")
def oven(cv: Canvas, parent, at: float = 1.0) -> None:
    _opening(at, "an oven")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(340), fy(470), fh(262), fh(320), STEEL, cv.ink, INK_W, radius=0)
    for x in (380, 440, 500, 560):
        cv.ellipse(g, fx(x - 15), fy(490), fh(30), fh(30), STEEL_DARK, cv.ink, FINE_W / 2)
    cv.rect(g, fx(360), fy(548), fh(224), fh(226), GLASS, cv.ink, FINE_W, radius=0)
    leaf = cv.group(g, cv.uid("g"), x=fx(360), y=fy(774), anchorX=fx(360), anchorY=fy(774))
    cv.rect(leaf, fx(360), fy(548), fh(224), fh(226), STEEL, cv.ink, FINE_W, radius=0)
    cv.rect(leaf, fx(384), fy(584), fh(176), fh(150), GLASS, cv.ink, FINE_W / 2, radius=fh(6))
    cv.rect(leaf, fx(384), fy(558), fh(176), fh(14), STEEL_DARK, cv.ink, FINE_W / 2, radius=fh(6))
    cv.keys(leaf, "scaleY", [(0.0, 1.0), (at, 1.0), (at + BURST, 0.08)], hold=False)


@register("prop", "toon-plates", summary="Plates sliding out of an oven across the frame, one after the other")
def plates(cv: Canvas, parent, start: float = 0.0, count: int = 9, step: float = 0.1, end: float = 4.0) -> None:
    """``count`` plates run from the oven's mouth out of the frame's left, ``step`` seconds apart from ``start``."""
    if not (isinstance(count, int) and count > 0 and checks.number(start) and checks.number(step) and step > 0):
        raise ToonDataError(f"plates need a count, a start and a step, got {count!r}, {start!r}, {step!r}")
    if start + (count - 1) * step + PLATE_RUN > end:
        raise ToonDataError(f"{count} plates from {start} s do not finish by {end} s")
    for i in range(count):
        t = round(start + i * step, 3)
        g = cv.group(parent, cv.uid("g"), start=t, end=t + PLATE_RUN)
        wobble = 26 * math.sin(i * 1.7)
        cv.keys(g, "x", [(t, 0.0), (t + PLATE_RUN, -fh(760))], hold=False)
        cv.keys(g, "y", [(t, 0.0), (t + PLATE_RUN, fh(90 + wobble))], hold=False)
        cv.ellipse(g, fx(430), fy(660), fh(150), fh(70), PLATE, cv.ink, FINE_W)
        cv.ellipse(g, fx(460), fy(676), fh(90), fh(38), PLATE, PLATE_RIM, FINE_W / 2)


@register("prop", "toon-shower", summary="A shower curtain pulled back on what is behind it")
def shower(cv: Canvas, parent, at: float = 1.0) -> None:
    _opening(at, "a shower curtain")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(340), fy(300), fh(262), fh(490), TILE, cv.ink, INK_W, radius=0)
    for y in range(340, 790, 46):
        _line(cv, g, [(344, y), (598, y)], 3.0, TILE_LINE)
    for x, y in ((372, 600), (480, 590), (424, 440)):
        cv.rect(g, fx(x), fy(y + 26), fh(108), fh(150), BIN, cv.ink, FINE_W, radius=fh(8))
        cv.rect(g, fx(x - 8), fy(y), fh(124), fh(30), BIN_LID, cv.ink, FINE_W, radius=fh(6))
        for dx in (26, 54, 82):
            _line(cv, g, [(x + dx, y + 50), (x + dx, y + 156)], 5.0, BIN_DARK)
    cv.rect(g, fx(334), fy(308), fh(274), fh(12), RAIL, cv.ink, FINE_W / 2, radius=fh(5))
    drape = cv.group(g, cv.uid("g"), x=fx(600), y=fy(320), anchorX=fx(600), anchorY=fy(320))
    cv.rect(drape, fx(340), fy(320), fh(260), fh(470), CURTAIN, cv.ink, FINE_W, radius=0)
    for x in range(370, 590, 44):
        _line(cv, drape, [(x, 326), (x + 6, 560), (x - 4, 786)], 8.0, CURTAIN_FOLD)
    cv.keys(drape, "scaleX", [(0.0, 1.0), (at, 1.0), (at + 0.25, 0.12)], hold=False)


@register("prop", "toon-front-door", summary="A flat's front door that opens on a hall stacked to the ceiling")
def front_door(cv: Canvas, parent, at: float = 1.0) -> None:
    _opening(at, "a front door")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(340), fy(270), fh(262), fh(520), HALL, cv.ink, INK_W, radius=0)
    for x, y, w, h in ((348, 610, 130, 170), (470, 590, 124, 190), (360, 450, 150, 150), (500, 430, 96, 160)):
        cv.rect(g, fx(x), fy(y), fh(w), fh(h), BOX, BOX_DARK, FINE_W, radius=0)
        _line(cv, g, [(x + w / 2, y + 2), (x + w / 2, y + 44)], 7.0, BOX_DARK)
    leaf = _door(cv, g, 348, 276, 250, 508, at, 598, DOOR)
    cv.rect(leaf, fx(376), fy(310), fh(194), fh(190), DOOR, DOOR_LINE, FINE_W, radius=0)
    cv.rect(leaf, fx(376), fy(530), fh(194), fh(220), DOOR, DOOR_LINE, FINE_W, radius=0)
    cv.ellipse(leaf, fx(360), fy(510), fh(22), fh(22), KNOB, cv.ink, FINE_W / 2)


def _garment(cv: Canvas, g, x: float, y: float, size: float, colour: str, tilt: float) -> None:
    """A dropped shirt: a body and two sleeves, turned ``tilt`` radians about ``(x, y)``."""
    s = size / 2
    shirt = ((-0.9, -0.3), (-0.45, -0.75), (-0.15, -0.6), (0.15, -0.6), (0.45, -0.75), (0.9, -0.3), (0.62, 0.0),
             (0.45, -0.1), (0.5, 0.8), (-0.5, 0.8), (-0.45, -0.1), (-0.62, 0.0))  # fmt: skip
    c, n = math.cos(tilt), math.sin(tilt)
    _inked(cv, g, [(x + s * (u * c - v * n), y + s * (u * n + v * c)) for u, v in shirt], colour, FINE_W, 2)


@register("prop", "toon-laundry-pile", summary="A heap of clothes that rises over whoever is in shot")
def pile(cv: Canvas, parent, top: float = 640.0, start: float | None = 0.5, end: float = 4.0) -> None:
    """The heap's top edge at reference ``top``: rising there over :data:`RISE` from ``start``, or there already
    (``start`` None) until ``end``."""
    if not (checks.number(top) and 200 <= top <= 900):
        raise ToonDataError(f"a pile's top stands between 200 and 900, got {top!r}")
    if start is not None and not (checks.number(start) and 0 <= start and start + RISE <= end):
        raise ToonDataError(f"a pile rises in {RISE} s from {start!r} before {end!r}")
    g = cv.group(parent, cv.uid("g"), start=start)
    if start is not None:
        cv.keys(g, "y", [(start, fh(1200 - top)), (start + RISE * 0.8, -fh(14)), (start + RISE, 0.0)], hold=False)
    cv.rect(g, fx(-20), fy(top + 90), fh(640), fh(1200 - top), GARMENTS[6], cv.clear, 0, radius=0)
    for i, (x, y, size, colour) in enumerate(LOAD):
        _garment(cv, g, x, top + y, size * 1.2, GARMENTS[colour], 0.9 * math.sin(i * 2.3))


@register("prop", "toon-tiny-drawer", summary="A tiny chest on the counter whose top drawer slides out on one sock")
def tiny_drawer(cv: Canvas, parent, at: float = 1.0, end: float = 4.0, x: float = 396.0, y: float = 801.0) -> None:
    """The chest stands on ``(x, y)`` (its bottom middle); the drawer opens at ``at`` and the sock rises from it."""
    _opening(at, "a tiny drawer")
    if not at + 0.3 <= end:
        raise ToonDataError(f"a tiny drawer needs 0.3 s from {at!r} to {end!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 74), fy(y - 130), fh(148), fh(130), CABINET, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, fx(x - 62), fy(y - 122), fh(124), fh(50), DOOR_DARK, cv.ink, FINE_W, radius=fh(4))
    sock = cv.group(g, cv.uid("g"), start=at)
    cv.keys(sock, "y", [(at, fh(90)), (at + 0.3, 0.0)], hold=False)
    cv.rect(sock, fx(x - 12), fy(y - 214), fh(34), fh(84), SOCK, cv.ink, FINE_W, radius=fh(6))
    cv.rect(sock, fx(x - 34), fy(y - 156), fh(56), fh(30), SOCK, cv.ink, FINE_W, radius=fh(14))
    cv.rect(sock, fx(x - 12), fy(y - 202), fh(34), fh(10), SOCK_STRIPE, cv.clear, 0, radius=0)
    cv.rect(g, fx(x - 62), fy(y - 62), fh(124), fh(50), CABINET_DARK, cv.ink, FINE_W, radius=fh(4))
    cv.ellipse(g, fx(x - 7), fy(y - 44), fh(14), fh(14), KNOB, cv.ink, FINE_W / 2)
    cx, cy = fx(x), fy(y - 97)
    drawer = cv.group(g, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    for prop in ("scaleX", "scaleY"):
        cv.keys(drawer, prop, [(0.0, 1.0), (at, 1.0), (at + 0.2, 1.3)], hold=False)
    cv.keys(drawer, "y", [(0.0, cy), (at, cy), (at + 0.2, cy + fh(26))], hold=False)
    cv.rect(drawer, fx(x - 62), fy(y - 122), fh(124), fh(50), CABINET_DARK, cv.ink, FINE_W, radius=fh(4))
    cv.ellipse(drawer, fx(x - 7), fy(y - 104), fh(14), fh(14), KNOB, cv.ink, FINE_W / 2)


@register("prop", "toon-whirl", summary="A spinning blur that a character whirls in on, gone at a given second")
def whirl(cv: Canvas, parent, start: float = 0.0, end: float = 0.7, at: Point = (185.0, 640.0)) -> None:
    """A blur crossing the frame from the right to ``at`` over the span, spinning, wide enough to hide who is in it."""
    if not (checks.number(start) and checks.number(end) and 0 <= start and start + 0.2 <= end):
        raise ToonDataError(f"a whirl spins from {start!r} to {end!r}, 0.2 s at least")
    cx, cy = fx(at[0]), fy(at[1])
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.keys(g, "x", [(start, fh(300)), (start + (end - start) * 0.7, 0.0)], hold=False)
    spin = cv.group(g, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    cv.keys(spin, "rotation", [(start, 0.0), (end, 540.0)], hold=False)
    w, h = fh(330), fh(460)
    cv.ellipse(spin, cx - w / 2, cy - h / 2, w, h, WHIRL_A, cv.ink, INK_W)
    cv.ellipse(spin, cx - w * 0.36, cy - h * 0.46, w * 0.42, h * 0.92, WHIRL_B, cv.ink, FINE_W)
    cv.ellipse(spin, cx + w * 0.02, cy - h * 0.3, w * 0.2, h * 0.6, WHIRL_B, cv.ink, FINE_W / 2)


@register("prop", "toon-sparkles", summary="Four-pointed glints that twinkle on a clean room")
def sparkles(
    cv: Canvas, parent, start: float = 0.0, end: float = 2.0, at: Sequence[Point] = ((420, 400), (520, 560))
) -> None:
    """A glint at each of ``at``, one after the other, between ``start`` and ``end``."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"sparkles run from {start!r} to {end!r}")
    step = (end - start) / max(len(at), 1)
    for i, (x, y) in enumerate(at):
        t = start + i * step
        cx, cy = fx(x), fy(y)
        g = cv.group(parent, cv.uid("g"), start=t, end=min(t + 0.5, end), x=cx, y=cy, anchorX=cx, anchorY=cy)
        cv.keys(g, "scaleX", [(t, 0.0), (t + 0.22, 1.0), (min(t + 0.5, end), 0.0)], hold=False)
        cv.keys(g, "scaleY", [(t, 0.0), (t + 0.22, 1.0), (min(t + 0.5, end), 0.0)], hold=False)
        r, w = fh(44), fh(9)
        mid = f"Q {cx:.1f} {cy:.1f}"
        d = (f"M {cx:.1f} {cy - r:.1f} {mid} {cx + r:.1f} {cy:.1f} {mid} {cx:.1f} {cy + r:.1f} "
             f"{mid} {cx - r:.1f} {cy:.1f} {mid} {cx:.1f} {cy - r:.1f} Z")  # fmt: skip
        cv.path(g, d, fill=SPARKLE, stroke=cv.ink, sw=w / 3)
