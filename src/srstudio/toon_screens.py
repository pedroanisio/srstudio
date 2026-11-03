"""A laptop in a Toon shot: the lid that shuts, and what a screen says, in cards a phone can read.

A Toon shot looks at the back of the lid, so what is on the screen comes to the viewer as a card in the band under the
desk's top edge: :func:`notice` is one line from a system, in the place a voice would take; :func:`lid` is the lid that
:func:`srstudio.toon.desk` draws, with a ``shut`` second. Every word is at phone size (:data:`READ_SIZE`). Bad input is
a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from . import checks
from ._toon_story_contracts import contract
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, LAPTOP, LAPTOP_BASE, ToonDataError, _d, _path, fh, fx, fy

__all__ = ["CARD_BOX", "NOTICE_MAX", "READ_SIZE", "lid", "notice"]

READ_SIZE = 44  # frame pixels: under this a word on a phone is a texture
CARD_BOX = (40.0, 884.0, 512.0, 124.0)  # x, y, w, h: under the desk's top edge, clear of the marks and the safe bottom
NOTICE_MAX = 24  # characters on one line
LAND = 0.14  # seconds a card takes to come up
HINGE_Y, SHUT_LEFT = 762.0, 0.04  # the lid's foot, and what is left of its height when shut
SHUT_TIME = 0.22


def _span(start: object, end: object, what: str) -> tuple[float, float]:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"{what} needs 0 <= start < end, got {start!r}..{end!r}")
    return float(start), float(end)


@register(
    "prop",
    "toon-laptop-lid",
    summary="The back of a laptop lid on the desk, that shuts on cue",
    style="toon",
    contract=contract('toon-laptop-lid'),
)
def lid(cv: Canvas, parent, shut: float | None = None) -> object:
    """The lid and foot :func:`srstudio.toon.desk` draws, without the desk, so it stands on any surface; at ``shut``
    it folds down onto its hinge in :data:`SHUT_TIME` seconds. Returns its group."""
    if shut is not None and not (checks.number(shut) and shut >= 0):
        raise ToonDataError(f"a lid shuts at a second from 0, got {shut!r}")
    g = cv.group(parent, cv.uid("g"))
    leaf = cv.group(g, cv.uid("g"), anchorX=fx(536.0), anchorY=fy(HINGE_Y), x=fx(536.0), y=fy(HINGE_Y))
    _path(cv, leaf, _d("M", (418, 531), "L", (660, 523), "L", (660, 760), "L", (415, 752), "Z"), LAPTOP)
    if shut is not None:
        cv.keys(leaf, "scaleY", [(0.0, 1.0), (shut, 1.0), (shut + SHUT_TIME, SHUT_LEFT)], hold=False, local=False)
    _path(cv, g, _d("M", (412, 751), "L", (660, 759), "L", (660, 766), "L", (411, 758), "Z"), LAPTOP_BASE, 0)
    return g


@register(
    "graphic",
    "toon-notice",
    summary="One line from a system, in a white card under the desk's edge",
    style="toon",
    contract=contract('toon-notice'),
)
def notice(
    cv: Canvas,
    parent,
    head: str = "APPLICATION 213",
    verdict: str = "REJECTED",
    start: float = 0.0,
    end: float = 2.0,
    colour: str = "#c0392b",
) -> object:
    """A card from ``start`` to ``end`` with ``head`` in ink over ``verdict`` in ``colour``; it comes up from below over
    :data:`LAND` seconds. Each is at most :data:`NOTICE_MAX` characters. Returns its group."""
    a, b = _span(start, end, "a notice")
    if b - a <= LAND:
        raise ToonDataError(f"a notice lasts over {LAND} s, got {a}..{b}")
    for text in (head, verdict):
        if not text.strip() or len(text) > NOTICE_MAX:
            raise ToonDataError(f"a notice's line is 1 to {NOTICE_MAX} characters, got {text!r}")
    x, y, w, h = CARD_BOX
    g = cv.group(parent, cv.uid("g"), start=a, end=b)
    cv.keys(g, "y", [(a, fh(40.0)), (a + LAND, 0.0)], hold=False, local=False)
    cv.rect(g, fx(x + 5), fy(y + 8), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(14), opacity=0.25)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), "#ffffff", cv.ink, INK_W * 0.8, radius=fh(14))
    cv.text(g, cv.uid("notice-head"), head, fx(x + 20), fy(y + 12), int(fh(w - 40)), int(fh(40)), READ_SIZE,
            color=cv.ink, wrap="none")  # fmt: skip
    cv.text(g, cv.uid("notice-verdict"), verdict, fx(x + 20), fy(y + 56), int(fh(w - 40)), int(fh(58)), 88,
            color=colour, wrap="none")  # fmt: skip
    _path(cv, g, _d("M", (x + 26, y + 52), "L", (x + w - 26, y + 52)), None, FINE_W * 0.3)
    return g
