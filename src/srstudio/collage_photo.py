"""The Collage family photo's props (ADR 0036): a phone on a stack of books counting its self-timer down, the
same countdown in the phone's viewfinder over the group shot, the front of the sofa that the seated busts sink
into, the camera's flash, and the printed photo.

The group shot itself is a :class:`srstudio.collage_group.Lineup`; the props here sit in a shot's ``front``. The
countdown shows one digit per ``tick`` from ``start`` (project seconds), from ``seconds`` down to 1, the full count
waiting on screen before ``start``; a scene longer or shorter than the count stretches the tick, so the count
visibly drops from the press and reaches zero on the shutter. The print is a still of the lineup in its room: each
character in one pose (no breath, no blink), the ones in ``blur`` out of focus, the room cropped to the camera's
framing inside a paper border.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING

from . import collage, collage_sets
from .canvas import Canvas
from .collage import INK, _cut, _paper, draw_shapes, figure_shapes
from .errors import SrstudioError
from .native import NativeError
from .registry import register

if TYPE_CHECKING:  # the group shot's module imports the sketch build, which imports the package
    from .collage_group import Place

__all__ = ["PhotoError", "SOFA_TOP", "PHOTO_CROP", "flash", "print_photo", "sofa", "timer", "viewfinder"]

MAX_SECONDS = 10  # the self-timer's longest countdown
SOFA_TOP = 1690.0  # the sofa's seat front: what is below it is hidden
PHOTO_BLUR = 9.0  # the blur radius of a subject who moved
BORDER, CHIN = 0.045, 0.16  # the print's paper border and its deeper bottom margin, as fractions of its width
BOOKS = ((-150, -64, 300, 64, "#bc4749"), (-130, -120, 262, 56, "#386641"), (-142, -168, 280, 48, "#f2e8cf"))
PHONE_W, PHONE_H = 150.0, 262.0
COUNT_AT, COUNT_R = (540.0, 660.0), 92.0  # the viewfinder's countdown disc: below the caption pill, above the heads
# the viewfinder's frame lines, x0, y0, x1, y1: below the living room's cactus shelf, around the seated group
CORNERS = (60.0, 790.0, 1020.0, 1780.0)
BRACKET = 90.0
# x, y, w, h of the frame the print shows: the one the viewfinder showed
PHOTO_CROP = (CORNERS[0], CORNERS[1], CORNERS[2] - CORNERS[0], CORNERS[3] - CORNERS[1])


class PhotoError(SrstudioError, ValueError):
    """A countdown, a flash or a print the props cannot show."""


def _check_count(start: float, seconds: int, tick: float) -> None:
    if not (isinstance(start, int | float) and math.isfinite(start) and start >= 0):
        raise PhotoError(f"a countdown starts at a project second, got start={start!r}")
    if not (isinstance(tick, int | float) and math.isfinite(tick) and tick > 0):
        raise PhotoError(f"a countdown ticks forward, got tick={tick!r}")
    if not (isinstance(seconds, int) and not isinstance(seconds, bool) and 1 <= seconds <= MAX_SECONDS):
        raise PhotoError(f"the self-timer counts whole seconds from 1 to {MAX_SECONDS}, got seconds={seconds!r}")


def _tick(start: float, tick: float, i: int) -> float:
    return round(start + i * tick, 6)


def _digits(cv: Canvas, parent, start: float, seconds: int, tick: float, box: tuple[float, float, float, float]):
    """The digits ``seconds`` down to 1, each shown for its ``tick`` from ``start``; the first also waits on screen
    from 0, as a self-timer shows its full count before it starts."""
    x, y, w, h = box
    for i in range(seconds):
        digit = cv.group(parent, cv.uid("count"))
        cv.text(digit, cv.uid("count-digit"), str(seconds - i), x, y, round(w), round(h), 120, color=INK)
        cv.gate(digit, [(0.0 if i == 0 else _tick(start, tick, i), _tick(start, tick, i + 1))])


@register("prop", "collage-phone-timer", summary="A phone propped on three paper books, its self-timer counting")
def timer(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    start: float,
    seconds: int = MAX_SECONDS,
    tick: float = 1.0,
    scale: float = 1.0,
):
    """The books' bottom centre at ``x, y``, the phone standing on them facing the room, its screen counting
    ``seconds`` down from ``start``, one digit per ``tick``."""
    _check_count(start, seconds, tick)
    g = cv.group(parent, cv.uid("timer"), x=x, y=y, scaleX=scale, scaleY=scale)
    for i, (bx, by, bw, bh, fill) in enumerate(BOOKS):
        draw_shapes(cv, g, _paper(_cut(f"timer-book-{i}", [(bx, by), (bx + bw, by), (bx + bw, by + bh),
                                                            (bx, by + bh)], 3), fill))  # fmt: skip
    top = BOOKS[-1][1]
    px, py = -PHONE_W / 2, top - PHONE_H
    draw_shapes(cv, g, _paper(_cut("timer-phone", [(px, py), (px + PHONE_W, py), (px + PHONE_W, top), (px, top)], 2),
                              "#2b2d42"))  # fmt: skip
    cv.rect(g, px + 12, py + 16, PHONE_W - 24, PHONE_H - 32, "#fffaf0", radius=14)
    _digits(cv, g, start, seconds, tick, (px + 12, py + 40, PHONE_W - 24, PHONE_H - 80))
    return g


@register("prop", "collage-viewfinder", summary="The phone camera's frame lines and its countdown over a shot")
def viewfinder(cv: Canvas, parent, *, start: float, seconds: int = MAX_SECONDS, tick: float = 1.0):
    """The shot seen through the phone on the books: white corner brackets and a paper disc counting ``seconds``
    down from ``start``, one digit per ``tick``, under the caption pill and over the heads; the disc goes with the
    last digit."""
    _check_count(start, seconds, tick)
    g = cv.group(parent, cv.uid("viewfinder"))
    x0, y0, x1, y1 = CORNERS
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d = f"M {cx} {cy + sy * BRACKET} L {cx} {cy} L {cx + sx * BRACKET} {cy}"
        cv.path(g, d, fill=cv.clear, stroke=INK, sw=14, opacity=0.35)
        cv.path(g, d, fill=cv.clear, stroke="#ffffff", sw=8)
    (ax, ay), r = COUNT_AT, COUNT_R
    disc = cv.group(g, cv.uid("count-disc"))
    cv.gate(disc, [(0.0, _tick(start, tick, seconds))])
    cv.ellipse(disc, ax - r, ay - r, 2 * r, 2 * r, "#fffaf0", stroke=INK, sw=6)
    _digits(cv, disc, start, seconds, tick, (ax - r, ay - r * 0.8, 2 * r, 1.7 * r))
    return g


@register("prop", "collage-sofa", summary="The front of the living room's sofa: seat and arms, paper cut")
def sofa(cv: Canvas, parent):
    """The sofa's seat front from :data:`SOFA_TOP` down, its seams and its two arms: in front of a lineup seated on
    it, it hides the busts' cut-off bottoms."""
    g = cv.group(parent, cv.uid("sofa"))
    w = cv.width
    seat = [(-20, SOFA_TOP), (w + 20, SOFA_TOP), (w + 20, cv.height + 20), (-20, cv.height + 20)]
    draw_shapes(cv, g, _paper(_cut("sofa-seat", seat, 3), "#3a5a40"))
    for sx in (w / 3, 2 * w / 3):
        cv.path(g, f"M {sx} {SOFA_TOP + 24} L {sx} {cv.height}", fill=cv.clear, stroke="#2d4632", sw=6)
    for key, arm in (("sofa-left", [(-30, SOFA_TOP - 110), (96, SOFA_TOP - 96), (112, cv.height + 20),
                                    (-30, cv.height + 20)]),
                     ("sofa-right", [(w - 96, SOFA_TOP - 96), (w + 30, SOFA_TOP - 110), (w + 30, cv.height + 20),
                                     (w - 112, cv.height + 20)])):  # fmt: skip
        draw_shapes(cv, g, _paper(_cut(key, arm, 3), "#588157"))
    return g


@register("prop", "collage-flash", summary="The camera's flash: the frame white, held, then fading")
def flash(cv: Canvas, parent, at: float, *, hold: float = 1.2, fade: float = 0.5):
    """White over the whole frame from ``at`` (project seconds), held ``hold`` seconds, fading over ``fade``."""
    numbers = (at, hold, fade)
    if not (all(math.isfinite(v) for v in numbers) and at >= 0 and hold >= 0 and fade > 0):
        raise PhotoError(f"a flash fires at a project second, holds and fades, got at={at}, hold={hold}, fade={fade}")
    g = cv.group(parent, cv.uid("flash"))
    cv.gate(g, [(at, at + hold + fade)])
    white = cv.rect(g, 0, 0, cv.width, cv.height, "#ffffff")
    cv.keys(white, "opacity", [(at, 1.0), (at + hold, 1.0), (at + hold + fade, 0.0)], hold=False)
    return g


def _check_print(places, poses, width, blur, room, crop) -> None:
    unknown = sorted(set(places) - set(collage.LOOKS))
    if unknown:
        raise PhotoError(f"{unknown} are not in the Collage cast")
    if set(poses) != set(places):
        raise PhotoError(f"a pose for each placed character: placed {sorted(places)}, posed {sorted(poses)}")
    for name, (eyes, mouth, arms) in poses.items():
        for what, value, allowed in (("eyes", eyes, collage.EYES), ("mouth", mouth, collage.MOUTHS),
                                     ("arms", arms, collage.ARMS)):  # fmt: skip
            if value not in allowed:
                raise PhotoError(f"{name}: {what} {value!r} is not one of {allowed}")
    stray = sorted(set(blur) - set(places))
    if stray:
        raise PhotoError(f"blur names {stray}, who are not in the photo")
    if not (math.isfinite(width) and width > 0):
        raise PhotoError(f"a print has a positive width, got {width!r}")
    if room not in collage_sets.SETS:
        raise PhotoError(f"room {room!r} is not one of {sorted(collage_sets.SETS)}")
    x, y, w, h = crop
    if not (all(math.isfinite(v) for v in crop) and x >= 0 and y >= 0 and w > 0 and h > 0
            and x + w <= 1080 and y + h <= 1920):  # fmt: skip
        raise PhotoError(f"the crop {crop} is not inside the 1080 × 1920 frame")


def _blur(cv: Canvas, radius: float) -> str:
    """The print's blur of ``radius`` px: the first radius on a canvas keeps the name a single-scale print has
    always had; another radius (a subject at another scale) gets its own effect, named by the radius."""
    try:
        return cv.effect("collage-photo-blur", "blur", radius=radius)
    except NativeError:
        return cv.effect(f"collage-photo-blur-{radius:.6g}", "blur", radius=radius)


@register("prop", "collage-photo-print", summary="A printed photo: a still of the lineup in its room, paper border")
def print_photo(
    cv: Canvas,
    parent,
    places: Mapping[str, Place],
    poses: Mapping[str, tuple[str, str, str]],
    *,
    x: float,
    y: float,
    width: float,
    tilt: float = 0.0,
    blur: Collection[str] = (),
    room: str = "living-room",
    crop: tuple[float, float, float, float] = PHOTO_CROP,
):
    """The print with its top-left at ``x, y``, ``width`` across its image, turned ``tilt`` degrees: ``room`` with
    each character of ``places`` in its place, in its ``poses`` entry (eyes, mouth, arms), the ``blur`` ones out of
    focus, the frame cropped to ``crop``, then the sofa; a white border with a deeper bottom margin, a faint
    gloss."""
    _check_print(places, poses, width, blur, room, crop)
    cx, cy, cw, ch = crop
    k = width / cw
    border, chin = width * BORDER, width * CHIN
    pw, ph = width + 2 * border, ch * k + border + chin
    g = cv.group(parent, cv.uid("photo"), x=x, y=y, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("photo-print", [(0, 0), (pw, 0), (pw, ph), (0, ph)], 3), "#fffdf7"))
    image = cv.group(g, cv.uid("photo-image"), x=border - cx * k, y=border - cy * k, scaleX=k, scaleY=k)
    image.add_mask(type="rect", x=cx, y=cy, width=cw, height=ch)
    collage_sets.SETS[room](cv, image)
    for name, place in places.items():
        px, py = place.transform()
        who = cv.group(image, cv.uid(f"photo-{name}"), x=px, y=py, scaleX=place.scale, scaleY=place.scale)
        if name in blur:
            cv.apply(who, _blur(cv, PHOTO_BLUR / place.scale))
        under, mouth, over = figure_shapes(collage.LOOKS[name], *poses[name])
        for shapes in (under, mouth, over):
            draw_shapes(cv, who, shapes)
    sofa(cv, image)
    gloss = cv.grad("collage-photo-gloss", [(0, "#ffffff59"), (0.45, "#ffffff00"), (1, "#ffffff00")], (0, 0, 1, 1))
    cv.rect(g, border, border, width, ch * k, gloss)
    return g
