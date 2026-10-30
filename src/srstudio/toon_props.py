"""Toon props and sets beyond the survey's room: the meeting room with its whiteboard, a mug on the desk, a wall
clock whose hands jump, sticky notes on the laptop lid, phone notifications that buzz in, a logo that grows on the
whiteboard, and a call badge. Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``); every
animation is keyed on the composition clock, like the rest of the style."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from . import brush, checks
from .canvas import Canvas
from .registry import register
from .toon import CHAIR_D, FINE_W, INK_W, REF_W, ToonDataError, _d, _path, fh, flat, fx, fy

__all__ = [
    "Toast",
    "meeting",
    "mug",
    "clock",
    "notes",
    "toasts",
    "board_text",
    "logo",
    "badge",
    "clock_angles",
    "scale_keys",
]

MEET_WALL = (("0", "#eef6f1"), ("0.5", "#d8e9df"), ("1", "#c9ddd2"))
BOARD_FRAME = "#c9cdd3"
BOARD = "#fbfbfd"
TRAY = "#9aa0a8"
MARKER = "#1e40af"
MUG = "#f05a7a"
MUG_BAND = "#fbd1dc"
CLOCK_FACE = "#fffaf0"
NOTE_COLOURS = ("#fff3a3", "#ffc1d9", "#c9f0ff")
TOAST_BG = "#ffffff"
TOAST_DOT = "#34c759"
LOGO_SUN = "#ffd23f"
LOGO_RAY = "#ff9f1c"
LOGO_SHADOW = "#1b1b2a"
BADGE_BG = "#1b1b2a"
BADGE_DOT = "#ff3b30"
TOAST_W, TOAST_H, TOAST_X, TOAST_Y = 240, 88, 340, 372  # the card, reference pixels: in the sky, under the badge
TOAST_SLIDE = 0.25  # seconds it slides in
TOAST_READ = 0.875  # a gated toast's lettering shows at least the engine's minDisplayTime (0.8333 s) and a frame
BUZZ_SHAKE = ((0.0, 0), (0.04, -6), (0.08, 6), (0.12, -5), (0.16, 5), (0.2, -3), (0.24, 0))  # x, relative
BOARD_BOX = (352, 290, 292, 400)  # the writable white inside the frame
BOARD_SEEN = REF_W - 14  # the board's writable part ends here on screen (reference px), a margin before the edge
BADGE_TOP = 316  # under the caption pill
LOGO_CENTRE = (498, 470)
LOGO_R = 42
GROW = 0.3  # seconds a logo change takes


@dataclass(frozen=True)
class Toast:
    """A phone notification: ``sender`` and ``text`` on a card from ``start`` to ``end`` (project seconds)."""

    start: float
    end: float
    sender: str
    text: str


# -- sets -------------------------------------------------------------------------------------------------------------
@register("location", "toon-meeting", summary="A mint meeting room: a whiteboard where the window was, and the chair")
def meeting(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    cv.rect(
        g, 0, 0, cv.width, cv.height, cv.grad("toon-meet-wall", [(float(o), c) for o, c in MEET_WALL], (0, 0, 0, 1))
    )
    cv.rect(g, fx(333), fy(262), fh(330), fh(471), BOARD_FRAME, cv.ink, INK_W, radius=0)
    cv.rect(g, fx(BOARD_BOX[0]), fy(BOARD_BOX[1]), fh(BOARD_BOX[2]), fh(BOARD_BOX[3]), BOARD, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(346), fy(700), fh(304), fh(14), TRAY, cv.ink, FINE_W, radius=4)  # the marker tray
    cv.rect(g, fx(380), fy(692), fh(46), fh(10), MARKER, cv.ink, 3, radius=4)  # a marker on it
    _path(cv, g, CHAIR_D, "#60a7fb")


# -- props ------------------------------------------------------------------------------------------------------------
@register("prop", "toon-mug", summary="A coffee mug on the desk, steaming while asked")
def mug(cv: Canvas, parent, x: float = 350, steam: Sequence[tuple[float, float]] = ()) -> None:
    """The mug stands on the desk top with its handle to the right; ``steam`` lists the spans its wisps show."""
    if any(not (checks.number(a) and checks.number(b) and 0 <= a < b) for a, b in steam):
        raise ToonDataError("steam spans need 0 <= start < end")
    g = cv.group(parent, cv.uid("g"))
    base = 838
    _path(
        cv,
        g,
        _d("M", (x + 50, base - 50), "C", (x + 80, base - 52), (x + 80, base - 14), (x + 50, base - 16)),
        None,
        INK_W,
    )
    cv.rect(g, fx(x), fy(base - 64), fh(56), fh(64), MUG, cv.ink, INK_W, radius=8)
    cv.rect(g, fx(x + 4), fy(base - 44), fh(48), fh(12), MUG_BAND, cv.clear, 0, radius=4)
    if steam:
        s = cv.group(g, cv.uid("g"))
        for dx in (10, 26, 42):
            top = base - 74
            d = _d("M", (x + dx, top), "C", (x + dx - 8, top - 10), (x + dx + 8, top - 20), (x + dx, top - 32))
            _path(cv, s, d, None, 4.0)
        cv.gate(s, [(a, b) for a, b in steam])


def clock_angles(time: str) -> tuple[float, float]:
    """Hour and minute hand angles (degrees clockwise from twelve) for ``"HH:MM"``."""
    try:
        hh, mm = (int(part) for part in time.split(":"))
    except ValueError:
        raise ToonDataError(f"a clock time is HH:MM, got {time!r}") from None
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise ToonDataError(f"a clock time is HH:MM, got {time!r}")
    return ((hh % 12) * 30 + mm * 0.5) % 360, mm * 6.0


@register("prop", "toon-clock", summary="A wall clock whose hands jump to each listed time")
def clock(
    cv: Canvas, parent, times: Sequence[tuple[float, str]], at: tuple[float, float] = (105, 385), r: float = 45
) -> None:
    """A clock on the wall at ``at``; ``times`` are ``(project second, "HH:MM")`` in order, the first held from 0."""
    if not times or any(b[0] <= a[0] for a, b in zip(times, times[1:], strict=False)) or times[0][0] < 0:
        raise ToonDataError("clock times need rising project seconds")
    angles = [(t, clock_angles(time)) for t, time in times]
    cx, cy = at
    g = cv.group(parent, cv.uid("g"))
    cv.ellipse(g, fx(cx - r), fy(cy - r), fh(2 * r), fh(2 * r), CLOCK_FACE, cv.ink, INK_W)
    for k in range(12):
        a = math.radians(k * 30)
        inner = r - (12 if k % 3 == 0 else 7)
        d = _d(
            "M",
            (cx + inner * math.sin(a), cy - inner * math.cos(a)),
            "L",
            (cx + (r - 3) * math.sin(a), cy - (r - 3) * math.cos(a)),
        )
        _path(cv, g, d, None, FINE_W if k % 3 == 0 else FINE_W * 0.6)
    for hand, length, width in (("hour", r * 0.52, INK_W), ("minute", r * 0.78, FINE_W)):
        h = cv.group(g, cv.uid("g"), anchorX=fx(cx), anchorY=fy(cy), x=fx(cx), y=fy(cy))
        _path(cv, h, _d("M", (cx, cy + 6), "L", (cx, cy - length)), None, width)
        keys = [(t, (a if hand == "hour" else m)) for t, (a, m) in angles]
        if keys[0][0] > 0:
            keys.insert(0, (0.0, keys[0][1]))
        cv.keys(h, "rotation", keys, local=False)
    cv.ellipse(g, fx(cx - 5), fy(cy - 5), fh(10), fh(10), cv.ink)


@register("prop", "toon-notes", summary="Sticky notes on the back of the laptop lid, lettered in the style's font")
def notes(cv: Canvas, parent, texts: Sequence[str], size: int = 26) -> None:
    """Up to four notes on the lid, each turned a little the other way; ``texts`` are short (one or two words)."""
    if not texts or len(texts) > 4 or any(not t.strip() or len(t) > 10 for t in texts):
        raise ToonDataError("notes are one to four short texts (at most 10 characters each)")
    spots = ((425, 552, -7), (505, 566, 6), (430, 640, 5), (508, 648, -6))  # two columns on the visible lid
    g = cv.group(parent, cv.uid("g"))
    for i, text in enumerate(texts):
        x, y, tilt = spots[i]
        side = 66
        n = cv.group(
            g,
            cv.uid("g"),
            anchorX=fx(x + side / 2),
            anchorY=fy(y + side / 2),
            x=fx(x + side / 2),
            y=fy(y + side / 2),
            rotation=tilt,
        )
        cv.rect(n, fx(x), fy(y), fh(side), fh(side), NOTE_COLOURS[i % 3], cv.ink, FINE_W, radius=2)
        cv.text(n, cv.uid("note"), text, fx(x), fy(y), int(fh(side)), int(fh(side)), size, color=cv.ink, wrap="word")


@register("graphic", "toon-toast", summary="A phone notification that buzzes in over the window")
def toasts(cv: Canvas, parent, items: Sequence[Toast], size: int = 28, gated: bool = False) -> None:
    """Each toast slides in from the right, shakes with the buzz and holds until its end. ``gated`` letters the card
    only once it has landed wholly on frame: lettering drawn off frame measures 1:1 in the engine's contrast check,
    which fails a strict encode. Off by default, so the toasts of published episodes stay as they were."""
    for i, t in enumerate(items):
        if not (checks.number(t.start) and checks.number(t.end) and 0 <= t.start < t.end):
            raise ToonDataError(f"toast {i}: needs 0 <= start < end")
        if not t.sender.strip() or not t.text.strip() or len(t.text) > 24 or len(t.sender) > 12:
            raise ToonDataError(f"toast {i}: a sender (at most 12 characters) and a text (at most 24)")
        if gated and t.end - t.start < TOAST_SLIDE + TOAST_READ:
            raise ToonDataError(
                f"toast {i}: gated, it lasts at least {TOAST_SLIDE + TOAST_READ} s, got {t.start}-{t.end}"
            )
    for t in items:
        g = cv.group(parent, cv.uid("g"), start=t.start, end=t.end)
        card = cv.group(g, cv.uid("g"))
        cv.rect(card, fx(TOAST_X), fy(TOAST_Y), fh(TOAST_W), fh(TOAST_H), TOAST_BG, cv.ink, FINE_W, radius=18)
        cv.ellipse(card, fx(TOAST_X + 14), fy(TOAST_Y + 14), fh(12), fh(12), TOAST_DOT)
        letters = cv.group(card, cv.uid("g"), start=t.start + TOAST_SLIDE, end=t.end) if gated else card
        cv.text(
            letters,
            cv.uid("toast"),
            t.sender.upper(),
            fx(TOAST_X + 34),
            fy(TOAST_Y + 6),
            int(fh(TOAST_W - 44)),
            int(fh(30)),
            size - 6,
            color=cv.ink,
            align="start",
            wrap="none",
        )
        cv.text(
            letters,
            cv.uid("toast"),
            t.text,
            fx(TOAST_X + 14),
            fy(TOAST_Y + 38),
            int(fh(TOAST_W - 28)),
            int(fh(44)),
            size,
            color=cv.ink,
            align="start",
            wrap="none",
        )
        slide = [(t.start, fh(TOAST_W + 60)), (t.start + TOAST_SLIDE, 0.0)]
        shake = [(t.start + TOAST_SLIDE + dt, fh(dx)) for dt, dx in BUZZ_SHAKE]
        cv.keys(card, "x", slide + shake[1:], hold=False, local=False)


@register("graphic", "toon-board-text", summary="Words in blue marker on the meeting room's whiteboard")
def board_text(
    cv: Canvas, parent, text: str, size: int = 40, start: float | None = None, end: float | None = None
) -> None:
    if not text.strip() or len(text) > 40:
        raise ToonDataError("board text is 1 to 40 characters")
    kw = {k: v for k, v in (("start", start), ("end", end)) if v is not None}
    g = cv.group(parent, cv.uid("g"), **kw)
    x, y, w, _ = BOARD_BOX
    width = min(w - 20, BOARD_SEEN - (x + 10))  # the board runs off the frame: wrap inside the part on screen
    cv.text(
        g, cv.uid("board"), text, fx(x + 10), fy(y + 14), int(fh(width)), int(fh(120)), size, color=MARKER, wrap="word"
    )


def scale_keys(sizes: Sequence[tuple[float, float]], grow: float = GROW) -> list[tuple[float, float]]:
    """Linear keys that hold each scale and change to the next over ``grow`` seconds: ``sizes`` are
    ``(project second, scale)`` in rising order; the first scale holds from 0."""
    checks.positive(grow, ToonDataError, f"a size change needs a grow over 0 s, got {grow!r}")
    if not sizes or any(not (checks.number(t) and checks.number(s) and s > 0) for t, s in sizes):
        raise ToonDataError("sizes need finite times and positive scales")
    if any(b[0] < a[0] + grow for a, b in zip(sizes, sizes[1:], strict=False)) or sizes[0][0] < 0:
        raise ToonDataError(f"sizes need rising project seconds at least {grow} s apart")
    keys = [(0.0, sizes[0][1])]
    for (t, s), prev in zip(sizes, [sizes[0][1]] + [s for _, s in sizes[:-1]], strict=True):
        if t > 0:
            keys += [(round(t, 6), prev), (round(t + grow, 6), s)]
    return keys


@register("graphic", "toon-logo", summary="A sun logo on the whiteboard that grows to each asked size")
def logo(
    cv: Canvas, parent, sizes: Sequence[tuple[float, float]] = ((0.0, 1.0),), shadow: tuple[float, float] | None = None
) -> None:
    """A smiling sun centred on the board, scaled about its centre by ``sizes`` (see :func:`scale_keys`); a drop
    shadow shows through the ``shadow`` span ("make it pop")."""
    keys = scale_keys(sizes)
    cx, cy = LOGO_CENTRE
    g = cv.group(parent, cv.uid("g"))

    def sun(parent, dx: float, dy: float, fill: str | None) -> None:
        for k in range(8):
            a = math.radians(k * 45)
            ray = brush.stroke(
                [(cx + dx + (LOGO_R + 8) * math.cos(a), cy + dy + (LOGO_R + 8) * math.sin(a)),
                 (cx + dx + (LOGO_R + 26) * math.cos(a), cy + dy + (LOGO_R + 26) * math.sin(a))],
                9, brush.EVEN, steps=3,
            )  # fmt: skip
            flat(cv, parent, ray, fill or LOGO_RAY)
        ring = [
            (cx + dx + LOGO_R * math.cos(math.radians(k * 30)), cy + dy + LOGO_R * math.sin(math.radians(k * 30)))
            for k in range(12)
        ]
        flat(cv, parent, brush.rim(ring, FINE_W / 2, brush.EVEN, steps=3), fill or cv.ink)
        flat(cv, parent, brush.outline(ring, steps=3), fill or LOGO_SUN)
        if fill is None:
            for ex in (-14, 14):
                flat(cv, parent, brush.ellipse(cx + ex, cy - 8, 4.5, 6), cv.ink)
            smile = brush.stroke(
                [(cx - 18, cy + 8), (cx - 8, cy + 20), (cx + 8, cy + 20), (cx + 18, cy + 8)], 4, brush.EVEN, steps=4
            )
            flat(cv, parent, smile, cv.ink)

    if shadow is not None:
        a, b = shadow
        if not (checks.number(a) and checks.number(b) and 0 <= a < b):
            raise ToonDataError("shadow needs 0 <= start < end")
        sh = cv.group(g, cv.uid("g"), anchorX=fx(cx), anchorY=fy(cy), x=fx(cx), y=fy(cy))
        sun(sh, 7, 9, LOGO_SHADOW)
        cv.keys(sh, "scaleX", keys, hold=False, local=False)
        cv.keys(sh, "scaleY", keys, hold=False, local=False)
        cv.keys(sh, "opacity", [(0.0, 0), (a, 0.35), (b, 0)], local=False)
    body = cv.group(g, cv.uid("g"), anchorX=fx(cx), anchorY=fy(cy), x=fx(cx), y=fy(cy))
    sun(body, 0, 0, None)
    cv.keys(body, "scaleX", keys, hold=False, local=False)
    cv.keys(body, "scaleY", keys, hold=False, local=False)


@register("graphic", "toon-badge", summary="A dark call badge under the captions: a red dot and who is on the line")
def badge(
    cv: Canvas, parent, text: str, start: float, end: float, measure: Callable[[str], float], size: int = 28
) -> None:
    if not text.strip() or len(text) > 30:
        raise ToonDataError("badge text is 1 to 30 characters")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError("badge needs 0 <= start < end")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    width = round(measure(text.upper()) + fh(56), 2)
    top, height = fy(BADGE_TOP), fh(36)
    cv.rect(g, round(cv.width / 2 - width / 2, 2), top, width, height, BADGE_BG, cv.clear, 0, radius=round(height / 2))
    cv.ellipse(g, round(cv.width / 2 - width / 2 + fh(14), 2), top + height / 2 - fh(6), fh(12), fh(12), BADGE_DOT)
    cv.text(
        g,
        cv.uid("badge"),
        text.upper(),
        round(cv.width / 2 - width / 2 + fh(30), 2),
        top,
        int(width - fh(30)),
        int(height),
        size,
        color=cv.white,
        wrap="none",
    )
