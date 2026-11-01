"""A room's quiet trouble in the Toon style: a smoke detector on the ceiling and a folder with a photograph in it.

:func:`smoke_detector` hangs from the top of the frame with a small green light, in frame from the first second, and
its light turns red on a cue. :func:`folder` is a manila folder seen from above that opens on a cue on a photograph of
an unmarked office block, ringed in red pen. Neither letters anything. Bad input is a
:class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _d, _path, fh, fx, fy

__all__ = ["ALARM", "LED", "SKY", "folder", "smoke_detector"]

Point = tuple[float, float]
SHELL, SHELL_SHADE = "#f4f1ea", "#cfc9bb"
LED, ALARM, HALO = "#57b86b", "#e5322d", "#ff8a7a"
MANILA, MANILA_EDGE = "#e7c883", "#c9a55c"
PRINT, SKY, BLOCK, GLASS, GROUND, PEN = "#fbfaf4", "#bfe0f2", "#8d8f9a", "#dbe9f1", "#7f9c6b", "#d42a2a"


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _scale(scale: object) -> float:
    if not (checks.number(scale) and float(scale) > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


def _cue(value: object, what: str) -> None:
    if value is not None and not (checks.number(value) and float(value) >= 0):
        raise ToonDataError(f"{what} on a second from 0, got {value!r}")


@register(
    "prop", "toon-smoke-detector", summary="A smoke detector on the ceiling, its light turning red on cue", style="toon"
)
def smoke_detector(
    cv: Canvas, parent, at: Point = (150.0, 70.0), red: float | None = None, scale: float = 1.0
) -> object:
    """A detector whose plate is on reference ``at``, the top of the frame; green, then red from second ``red``.
    Returns its group."""
    x, y = _point(at, "a detector")
    s = _scale(scale)
    _cue(red, "a detector turns red")
    g = cv.group(parent, cv.uid("g"))
    w, h = 170.0 * s, 62.0 * s
    bottom = y + h + 6 * s
    dome = _d("M", (x - w / 2, y + 14 * s), "C", (x - w / 2 + 12 * s, bottom), (x + w / 2 - 12 * s, bottom),
              (x + w / 2, y + 14 * s), "Z")  # fmt: skip
    _path(cv, g, dome, SHELL, INK_W * 0.8)
    for k in (-1, 0, 1):
        cv.rect(
            g,
            fx(x - 34 * s + k * 0),
            fy(y + 26 * s + (k + 1) * 8 * s),
            fh(68 * s),
            fh(3 * s),
            SHELL_SHADE,
            cv.clear,
            0,
            radius=0,
        )
    cv.rect(
        g,
        fx(x - w / 2 - 8 * s),
        fy(y - 4 * s),
        fh(w + 16 * s),
        fh(20 * s),
        SHELL,
        cv.ink,
        INK_W * 0.8,
        radius=fh(4 * s),
    )
    r = 11.0 * s
    lx, ly = x + 46 * s, y + 34 * s
    if red is None:
        cv.ellipse(g, fx(lx - r), fy(ly - r), fh(2 * r), fh(2 * r), LED, cv.ink, FINE_W * 0.6)
        return g
    green = cv.group(g, cv.uid("g"), end=red)
    cv.ellipse(green, fx(lx - r), fy(ly - r), fh(2 * r), fh(2 * r), LED, cv.ink, FINE_W * 0.6)
    lit = cv.group(g, cv.uid("g"), start=red)
    halo = r * 2.1
    cv.ellipse(lit, fx(lx - halo), fy(ly - halo), fh(2 * halo), fh(2 * halo), HALO, cv.clear, 0, opacity=0.45)
    cv.ellipse(lit, fx(lx - r), fy(ly - r), fh(2 * r), fh(2 * r), ALARM, cv.ink, FINE_W * 0.6)
    return g


@register(
    "prop", "toon-folder", summary="A manila folder from above, opening on a photograph of a building", style="toon"
)
def folder(cv: Canvas, parent, at: Point = (300.0, 430.0), opened: float | None = None, scale: float = 1.0) -> object:
    """A folder centred on reference ``at``, shut, or open on its photograph from ``opened``. Returns its group."""
    x, y = _point(at, "a folder")
    s = _scale(scale)
    _cue(opened, "a folder opens")
    g = cv.group(parent, cv.uid("g"))
    w, h = 440.0 * s, 330.0 * s
    left, top = x - w / 2, y - h / 2
    cv.rect(g, fx(left + 6 * s), fy(top + 8 * s), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(8 * s), opacity=0.18)
    cv.rect(
        g,
        fx(left + 24 * s),
        fy(top - 26 * s),
        fh(130 * s),
        fh(50 * s),
        MANILA_EDGE,
        cv.ink,
        INK_W * 0.7,
        radius=fh(8 * s),
    )
    cv.rect(g, fx(left), fy(top), fh(w), fh(h), MANILA_EDGE, cv.ink, INK_W * 0.8, radius=fh(8 * s))
    if opened is not None:
        photo = cv.group(g, cv.uid("g"), start=opened)
        _photograph(cv, photo, x, y, s)
    cover = cv.group(g, cv.uid("g"), **({"end": opened} if opened is not None else {}))
    cv.rect(cover, fx(left), fy(top + 6 * s), fh(w), fh(h - 6 * s), MANILA, cv.ink, INK_W * 0.8, radius=fh(8 * s))
    return g


def _photograph(cv: Canvas, g, x: float, y: float, s: float) -> None:
    """A print of a plain office block on its lawn, ringed in red pen: no name on it and nobody in it."""
    w, h = 380.0 * s, 280.0 * s
    left, top = x - w / 2, y - h / 2
    cv.rect(g, fx(left), fy(top), fh(w), fh(h), PRINT, cv.ink, FINE_W, radius=fh(3 * s))
    m = 16.0 * s
    cv.rect(g, fx(left + m), fy(top + m), fh(w - 2 * m), fh(h - 2 * m), SKY, cv.clear, 0, radius=0)
    cv.rect(g, fx(left + m), fy(top + h - 66 * s), fh(w - 2 * m), fh(50 * s), GROUND, cv.clear, 0, radius=0)
    bw, bh = 170.0 * s, 170.0 * s
    bx, by = x - bw / 2, top + h - 66 * s - bh
    cv.rect(g, fx(bx), fy(by), fh(bw), fh(bh), BLOCK, cv.ink, FINE_W, radius=0)
    for row in range(4):
        for col in range(4):
            wx, wy = bx + 14 * s + col * 38 * s, by + 12 * s + row * 38 * s
            cv.rect(g, fx(wx), fy(wy), fh(26 * s), fh(26 * s), GLASS, cv.ink, FINE_W * 0.4, radius=0)
    cx, cy, rx, ry = x, by + bh / 2, 134.0 * s, 124.0 * s
    cv.ellipse(g, fx(cx - rx), fy(cy - ry), fh(2 * rx), fh(2 * ry), cv.clear, PEN, FINE_W * 1.5)
