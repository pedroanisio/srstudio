"""The Ink video doorbell: a talking doorbell by a front door and what its camera sees, drawn in the style's pen
stroke (:mod:`srstudio.ink`).

The doorbell is a tall rounded box on the wall: the camera lens at the top, the speaker slits and the button with
its ring of lights. While it speaks the ring chases and voice marks flicker, as the router's LEDs and the vacuum's
ring do, and at a moment of the take its button can show a verdict, a cross (deny) or a tick (allow). The doorstep
is the wall, the numbered front door and the mat, with the doorbell beside the door. The camera view is the
doorbell's feed: the human close up through a round lens, REC blinking, a clock strip and a face box whose tag
changes over the take. Every time is seconds into the take. The doorbell carries the signature code (ADR 0001).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import signature
from .canvas import Canvas
from .errors import SrstudioError
from .ink import ellipse, group, human, path
from .registry import register
from .timeline import Take

__all__ = ["DoorbellError", "LENS", "RING_LIGHTS", "TAG_MAX", "doorbell", "doorstep", "doorbell_view"]

MARKS = ("deny", "allow")
RING_LIGHTS = 8
TAG_MAX = 10  # characters on the face box's tag
NUMBER_MAX = 4  # characters on the house number
CLOCK_MAX = 12  # characters of the clock strip after FRONT DOOR
LENS = (540, 620, 400)  # the camera view's round lens: centre and radius, frame pixels
FACE = (240, 400, 1.25)  # the human in the camera view: position and scale
BOX = (230, 390, 520, 520)  # the face box: left, top, width, height


class DoorbellError(SrstudioError, ValueError):
    """A verdict, a house number, a tag or a clock the doorbell or its camera cannot show."""


def _text(cv: Canvas, parent, value: str, x, y, w, h, size, color: str) -> None:
    aid = cv.uid("txt")
    cv.assets.add_text(
        id=aid,
        text=value,
        width=round(w),
        height=round(h),
        size=size,
        fontAsset=cv.font_asset,
        color=color,
        align="center",
        verticalAlign="middle",
        wrap="none",
    )
    parent.add_layer(id=cv.uid("label"), asset=aid, x=x, y=y)


def _box(x: float, y: float, w: float, h: float, r: float) -> str:
    return (
        f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} L {x + w} {y + h - r} "
        f"Q {x + w} {y + h} {x + w - r} {y + h} L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} "
        f"L {x} {y + r} Q {x} {y} {x + r} {y} Z"
    )


def _ring_keys(i: int, duration: float) -> list[tuple[float, float]]:
    """Light ``i`` of the ring while the doorbell speaks: on, then a chase around the ring until the take ends."""
    period, step = 0.48, 0.06
    keys, t, lit = [(0.0, 1.0)], step * i + 0.08, False
    while t < duration:
        keys.append((round(t, 3), 1.0 if lit else 0.15))
        lit, t = not lit, t + period / 2
    return keys


def _check_mark(mark: tuple[str, float] | None, take: Take) -> None:
    if mark is None:
        return
    kind, at = mark
    if kind not in MARKS:
        raise DoorbellError(f"the mark is one of {MARKS}, got {kind!r}")
    if not (math.isfinite(at) and 0 <= at <= take.duration):
        raise DoorbellError(f"the mark falls within the take (0..{take.duration}), got {at}")


@register(
    "character",
    "talking-doorbell",
    summary="A video doorbell that talks: its ring of lights chases and voice marks flicker when it speaks, and its "
    "button shows a verdict (deny or allow) from a moment of the take",
    style="ink",
)
def doorbell(
    cv: Canvas, parent, take: Take, x, y, scale=1, *, speaker: str = "doorbell", mark: tuple[str, float] | None = None
):
    """The doorbell centred on ``x, y``; ``mark=(verdict, at)`` shows a cross (``deny``) or a tick (``allow``) on
    its button from ``at``."""
    _check_mark(mark, take)
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    path(cv, g, _box(-66, -168, 150, 360, 60), cv.shade, sw=0)  # its shadow on the wall
    path(cv, g, _box(-75, -180, 150, 360, 60), cv.white, sw=3)
    path(cv, g, _box(-58, -162, 116, 324, 46), stroke=cv.shade, sw=1.4)
    ellipse(cv, g, -46, -146, 92, 92, cv.ink, sw=2.5)  # the lens
    ellipse(cv, g, -24, -124, 48, 48, cv.shade, sw=0)
    ellipse(cv, g, -14, -120, 16, 16, cv.white, sw=0)
    path(cv, g, "M -30 -30 L 30 -30 M -30 -12 L 30 -12 M -30 6 L 30 6", sw=2.2)  # the speaker
    ellipse(cv, g, -44, 46, 88, 88, cv.white, sw=2.6)  # the button
    talking = take.actor == speaker
    for i in range(RING_LIGHTS):
        a = 2 * math.pi * i / RING_LIGHTS - math.pi / 2
        light = ellipse(cv, g, 56 * math.cos(a) - 6, 90 + 56 * math.sin(a) - 6, 12, 12, cv.ink, sw=0)
        if talking:
            cv.keys(light, "opacity", _ring_keys(i, take.duration))
    if mark is not None:
        kind, at = mark
        verdict = group(cv, g)
        d = "M -18 72 L 18 108 M 18 72 L -18 108" if kind == "deny" else "M -20 92 L -6 106 L 22 72"
        path(cv, verdict, d, sw=6)
        cv.keys(verdict, "opacity", [(0.0, 0.0), (at, 1.0)])
    signature.code(cv, g, -30, 150, 9)
    if talking:
        marks = group(cv, g, x=96, y=-196)
        path(cv, marks, "M 0 0 L 8 -24 M 19 8 L 40 -9 M 27 25 L 55 21", sw=2.6)
        fade = [(0, 0), (0.06, 0.9), (0.24, 0.3), (0.4, 0.8), (0.58, 0.25), (0.72, 0.65), (0.85, 0)]
        cv.keys(marks, "opacity", fade, hold=False)
    return g


@register(
    "location",
    "ink-doorstep",
    summary="The front door from outside: siding, the numbered door with its knob, the mat, and the doorbell "
    "beside it, normal or close",
    style="ink",
)
def doorstep(cv: Canvas, parent, take: Take, *, close: bool = False, number: str = "14", **bell_kw):
    """The wall, the door and its number, the doorbell on the wall beside it; ``bell_kw`` (``mark``, ``speaker``)
    go to :func:`doorbell`."""
    if not (number.strip() and len(number) <= NUMBER_MAX):
        raise DoorbellError(f"the house number is 1 to {NUMBER_MAX} characters, got {number!r}")
    door = 860 if close else 620  # the door frame's left edge
    floor = 1010
    for k in range(10):  # the siding's boards
        y0 = 250 + k * 76
        path(cv, parent, f"M 0 {y0} L {door - 24} {y0}", stroke=cv.shade, sw=1.4)
    path(cv, parent, f"M 0 {floor} L 1080 {floor}", sw=2.4)
    path(
        cv,
        parent,
        f"M {door - 24} 190 L {door + 400} 190 L {door + 400} {floor} L {door - 24} {floor} Z",
        cv.white,
        sw=2.8,
    )  # fmt: skip  the frame
    path(cv, parent, f"M {door} 214 L {door + 380} 214 L {door + 380} {floor} L {door} {floor} Z", cv.white, sw=2.6)
    for py in (260, 600):  # the door's panels
        path(cv, parent, _box(door + 50, py, 140, 280, 10), stroke=cv.shade, sw=2)
        path(cv, parent, _box(door + 230, py, 110, 280, 10), stroke=cv.shade, sw=2)
    ellipse(cv, parent, door + 26, 600, 34, 34, cv.white, sw=2.4)  # the knob
    path(cv, parent, f"M {door + 34} 650 l 18 0 l 0 34 l -18 0 Z", cv.ink, sw=0)  # the deadbolt
    mat = (door - 140, floor + 18, 520, 52) if not close else (door - 200, floor + 18, 420, 52)
    path(cv, parent, _box(*mat, 12), cv.shade, sw=2.2)
    plaque = (380, 250, 130, 84) if not close else (150, 300, 150, 96)
    path(cv, parent, _box(*plaque, 12), cv.white, sw=2.4)
    _text(cv, parent, number, *plaque, 60 if close else 54, cv.ink)
    signature.cactus(cv, parent, 150 if not close else 140, floor, 0.45)
    bx, by, sc = (445, 620, 1.15) if not close else (540, 610, 1.85)
    return doorbell(cv, parent, take, bx, by, sc, **bell_kw)


def _check_tags(tags: Sequence[tuple[float, str]], take: Take) -> None:
    if not tags:
        raise DoorbellError("the face box needs at least one tag")
    for at, text in tags:
        if not (text.strip() and len(text) <= TAG_MAX):
            raise DoorbellError(f"a tag is 1 to {TAG_MAX} characters, got {text!r}")
        if not (math.isfinite(at) and 0 <= at <= take.duration):
            raise DoorbellError(f"a tag changes within the take (0..{take.duration}), got {at}")
    if tags[0][0] != 0:
        raise DoorbellError(f"the first tag shows from 0, got {tags[0][0]}")
    times = [at for at, _ in tags]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise DoorbellError(f"tags change at rising seconds, got {times}")


@register(
    "graphic",
    "ink-doorbell-view",
    summary="What the doorbell's camera sees: the human close up through a round lens, REC blinking, a clock strip "
    "and a face box whose tag changes over the take",
    style="ink",
)
def doorbell_view(
    cv: Canvas, parent, take: Take, *, tags: Sequence[tuple[float, str]], clock: str = "", shades: bool = False
):
    """The camera feed: the human (``shades`` puts sunglasses on his forehead) behind the lens, each
    ``(at, text)`` of ``tags`` on the face box from ``at`` until the next, the first from 0, and the strip reading
    FRONT DOOR and ``clock``."""
    _check_tags(tags, take)
    if len(clock) > CLOCK_MAX:
        raise DoorbellError(f"the clock strip holds {CLOCK_MAX} characters, got {clock!r}")
    fx, fy, fs = FACE
    human(cv, parent, take, fx, fy, fs, shades=shades)
    g = group(cv, parent)
    cx, cy, r = LENS
    outer = 900  # past the frame's farthest corner from the lens centre
    mid = (r + outer) / 2
    ellipse(cv, g, cx - mid, cy - mid, 2 * mid, 2 * mid, cv.clear, stroke=cv.shade, sw=outer - r)
    ellipse(cv, g, cx - r, cy - r, 2 * r, 2 * r, cv.clear, sw=5)
    bx, by, bw, bh = BOX
    arm = 70
    for x0, y0, dx, dy in ((bx, by, 1, 1), (bx + bw, by, -1, 1), (bx, by + bh, 1, -1), (bx + bw, by + bh, -1, -1)):
        path(cv, g, f"M {x0} {y0 + dy * arm} L {x0} {y0} L {x0 + dx * arm} {y0}", sw=6)
    for k, (at, text) in enumerate(tags):
        tag = group(cv, g)
        path(cv, tag, _box(bx - 4, by - 66, 250, 58, 10), cv.ink, sw=0)
        _text(cv, tag, text, bx - 4, by - 66, 250, 58, 40, cv.white)
        if len(tags) > 1:
            keys = [(0.0, 1.0)] if k == 0 else [(0.0, 0.0), (at, 1.0)]
            if k + 1 < len(tags):
                keys.append((tags[k + 1][0], 0.0))
            cv.keys(tag, "opacity", keys)
    rec = ellipse(cv, g, 300, 330, 24, 24, cv.ink, sw=0)
    blink = [(round(t * 0.5, 3), 1.0 if t % 2 == 0 else 0.0) for t in range(int(take.duration / 0.5) + 1)]
    cv.keys(rec, "opacity", blink)
    _text(cv, g, "REC", 332, 318, 90, 48, 38, cv.ink)
    strip = f"FRONT DOOR  {clock}".strip()
    _text(cv, g, strip, cx - 210, cy + r - 92, 420, 50, 36, cv.ink)
    return g
