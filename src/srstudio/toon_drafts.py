"""An email written by committee in the Toon style: the laptop's screen, the crossed-out notes, a magnifier, an
exclamation mark as a shape, and the corkboard they end up on.

:func:`laptop_screen` shows one :class:`Draft` after another under the desk's edge, a screen in the picture, read on a
phone. :func:`stuck_notes` sticks a crossed-out :class:`Note` to the kitchen at its second. :func:`magnifier` and
:func:`exclaim` are drawn at any size, the second with no font. :func:`corkboard` slides in clear of the corner badge,
with the mark at its center and the notes around it, and no faces. Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _d, _path, fh, fx, fy

__all__ = [
    "BOARD",
    "BODY_MAX",
    "NOTE_MAX",
    "SCREEN",
    "SPOTS",
    "Draft",
    "Note",
    "corkboard",
    "exclaim",
    "laptop_screen",
    "magnifier",
    "stuck_notes",
]

Point = tuple[float, float]
SCREEN = (40.0, 884.0, 512.0, 130.0)  # x, y, w, h: under the desk's edge and the signature code
BOARD = (16.0, 104.0, 480.0, 470.0)  # x, y, w, h: stops short of the corner badge at reference x 508
HEAD_MAX, BODY_MAX, NOTE_MAX = 16, 30, 10
HEAD_SIZE, BODY_SIZE, NOTE_SIZE = 34, 56, 32
BEZEL, GLASS, HEAD_INK = "#2b2b33", "#ffffff", "#6a6f7c"
PAPER, STRIKE = "#ffe680", "#d42a2a"
CORK, CORK_RIM, CORK_DOT = "#c99a62", "#7d5a36", "#b78852"
LENS, BRASS, GRIP = "#d7eef8", "#c9a24d", "#5d3a22"
PIN = "#d42a2a"
NOTE_W, NOTE_H = 104.0, 74.0
SPOTS: tuple[
    tuple[float, float, float], ...
] = (  # x, y, degrees of each note's middle, on the kitchen's cabinets and door
    (66.0, 118.0, -4.0),
    (186.0, 124.0, 3.0),
    (306.0, 114.0, -2.0),
    (426.0, 126.0, 5.0),
    (530.0, 150.0, -3.0),
    (534.0, 300.0, 4.0),
    (534.0, 392.0, -5.0),
    (534.0, 484.0, 3.0),
    (534.0, 576.0, -2.0),
)
BOARD_SPOTS: tuple[tuple[float, float, float], ...] = (  # the same, on the corkboard around its mark
    (92.0, 168.0, -6.0),
    (254.0, 150.0, 3.0),
    (416.0, 170.0, 5.0),
    (86.0, 340.0, 4.0),
    (424.0, 344.0, -4.0),
    (90.0, 498.0, -3.0),
    (420.0, 500.0, 6.0),
)
GREETINGS = ("Dear Joan", "Hi there", "Hello Joan", "Joan,", "Hey!", "Hi Joan,")


@dataclass(frozen=True)
class Draft:
    """What the screen shows from ``start`` to ``end``: a short ``head`` over the ``body``."""

    start: float
    end: float
    head: str
    body: str


@dataclass(frozen=True)
class Note:
    """A crossed-out ``text`` that goes up at second ``at``."""

    at: float
    text: str


def _scale(scale: object) -> float:
    if not (checks.number(scale) and float(scale) > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


def _note(cv: Canvas, parent, x: float, y: float, degrees: float, text: str, **timed: float) -> None:
    g = cv.group(parent, cv.uid("g"), anchorX=fx(x), anchorY=fy(y), x=fx(x), y=fy(y), rotation=degrees, **timed)
    left, top = x - NOTE_W / 2, y - NOTE_H / 2
    cv.rect(g, fx(left), fy(top), fh(NOTE_W), fh(NOTE_H), PAPER, cv.ink, FINE_W * 0.6, radius=fh(2))
    box = fx(left + 4), fy(top + 16), int(fh(NOTE_W - 8)), int(fh(42))
    cv.text(g, cv.uid("note"), text, *box, NOTE_SIZE, color=cv.ink, wrap="none")
    _path(
        cv,
        g,
        _d("M", (left + 6, top + NOTE_H - 14), "L", (left + NOTE_W - 6, top + 16)),
        None,
        FINE_W * 0.8,
        stroke=STRIKE,
    )


@register(
    "prop", "toon-laptop-screen", summary="A laptop's screen under the desk's edge, its draft changing", style="toon"
)
def laptop_screen(cv: Canvas, parent, drafts: Sequence[Draft] = (Draft(0.0, 2.0, "DRAFT 1", "Hi Joan"),)) -> object:
    """Each of ``drafts`` in turn, spans rising, on one screen. Returns its group."""
    if not drafts:
        raise ToonDataError("a screen shows at least one draft")
    if any(not (0 <= d.start < d.end) for d in drafts) or any(
        b.start < a.end for a, b in zip(drafts, drafts[1:], strict=False)
    ):
        raise ToonDataError("a screen's drafts rise, each from 0 <= start < end")
    for d in drafts:
        if len(d.head) > HEAD_MAX or len(d.body) > BODY_MAX or not d.body.strip():
            raise ToonDataError(f"a draft fits the screen in {HEAD_MAX} and {BODY_MAX} characters, got {d!r}")
    x, y, w, h = SCREEN
    g = cv.group(parent, cv.uid("g"), start=drafts[0].start, end=drafts[-1].end)
    cv.rect(g, fx(x + 5), fy(y + 8), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(12), opacity=0.25)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), BEZEL, cv.ink, INK_W * 0.8, radius=fh(12))
    cv.rect(g, fx(x + 12), fy(y + 12), fh(w - 24), fh(h - 24), GLASS, cv.clear, 0, radius=fh(4))
    for d in drafts:
        page = cv.group(g, cv.uid("g"), start=d.start, end=d.end)
        cv.text(page, cv.uid("draft-head"), d.head, fx(x + 26), fy(y + 18), int(fh(w - 52)), int(fh(32)), HEAD_SIZE,
                color=HEAD_INK, wrap="none")  # fmt: skip
        cv.text(page, cv.uid("draft-body"), d.body, fx(x + 26), fy(y + 52), int(fh(w - 52)), int(fh(56)), BODY_SIZE,
                color=cv.ink, wrap="none")  # fmt: skip
    return g


@register(
    "prop", "toon-stuck-notes", summary="Crossed-out sticky notes piling up on a kitchen, one at a time", style="toon"
)
def stuck_notes(cv: Canvas, parent, notes: Sequence[Note] = (Note(0.0, "Dear Joan"),)) -> object:
    """Each of ``notes`` on the next of :data:`SPOTS`, going up at its second. Returns their group."""
    if len(notes) > len(SPOTS):
        raise ToonDataError(f"there are places for {len(SPOTS)} notes, got {len(notes)}")
    g = cv.group(parent, cv.uid("g"))
    for note, (x, y, degrees) in zip(notes, SPOTS, strict=False):
        if not note.text.strip() or len(note.text) > NOTE_MAX:
            raise ToonDataError(f"a note is 1 to {NOTE_MAX} characters, got {note.text!r}")
        if not (checks.number(note.at) and note.at >= 0):
            raise ToonDataError(f"a note goes up on a second from 0, got {note.at!r}")
        _note(cv, g, x, y, degrees, note.text, start=note.at)
    return g


@register("prop", "toon-magnifier", summary="A magnifying glass with a brass ring and a wooden handle", style="toon")
def magnifier(cv: Canvas, parent, at: Point = (300.0, 400.0), scale: float = 1.0) -> object:
    """A glass whose lens is centred on reference ``at``, its handle down and to the left. Returns its group."""
    x, y = float(at[0]), float(at[1])
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    r = 70.0 * s
    handle = _d("M", (x - r * 0.62, y + r * 0.8), "L", (x - r * 1.5, y + r * 1.9), "L", (x - r * 1.28, y + r * 2.08),
                "L", (x - r * 0.42, y + r * 0.98), "Z")  # fmt: skip
    _path(cv, g, handle, GRIP, INK_W * 0.7)
    cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), LENS, BRASS, INK_W * 1.6, opacity=0.4)
    cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), cv.clear, cv.ink, FINE_W * 0.7)
    return g


@register("graphic", "toon-exclaim", summary="An exclamation mark as a shape, at any size, with no font", style="toon")
def exclaim(cv: Canvas, parent, at: Point = (300.0, 400.0), height: float = 300.0, colour: str = "#23232b") -> object:
    """A mark ``height`` reference pixels tall, centred on ``at``. Returns its group."""
    if not (checks.number(height) and height > 0):
        raise ToonDataError(f"a mark's height is over 0, got {height!r}")
    x, y = float(at[0]), float(at[1])
    h = float(height)
    g = cv.group(parent, cv.uid("g"))
    wedge = _d("M", (x - h * 0.13, y - h / 2), "L", (x + h * 0.13, y - h / 2), "L", (x + h * 0.06, y + h * 0.2),
               "L", (x - h * 0.06, y + h * 0.2), "Z")  # fmt: skip
    _path(cv, g, wedge, colour, FINE_W * 0.5)
    r = h * 0.1
    cv.ellipse(g, fx(x - r), fy(y + h / 2 - 2 * r), fh(2 * r), fh(2 * r), colour, cv.ink, FINE_W * 0.5)
    return g


@register(
    "prop",
    "toon-corkboard",
    summary="A corkboard sliding in, a mark pinned at its center and notes around it",
    style="toon",
)
def corkboard(cv: Canvas, parent, texts: Sequence[str] = GREETINGS, slide: tuple[float, float] | None = None) -> object:
    """A board on :data:`BOARD` with :func:`exclaim` pinned at its center and each of ``texts`` crossed out around it;
    with ``slide``, it comes in from the left over that span. Returns its group."""
    if len(texts) > len(BOARD_SPOTS):
        raise ToonDataError(f"a board has places for {len(BOARD_SPOTS)} notes, got {len(texts)}")
    if slide is not None and not (checks.number(slide[0]) and checks.number(slide[1]) and 0 <= slide[0] < slide[1]):
        raise ToonDataError(f"a board slides in over 0 <= start < end, got {slide!r}")
    x, y, w, h = BOARD
    g = cv.group(parent, cv.uid("g"), **({"start": slide[0]} if slide else {}))
    if slide is not None:
        cv.keys(g, "x", [(slide[0], -fx(x + w + 20)), (slide[1], 0.0)], hold=False, local=False, kind="cubic-out")
    cv.rect(g, fx(x + 6), fy(y + 10), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(6), opacity=0.2)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), CORK_RIM, cv.ink, INK_W * 0.8, radius=fh(6))
    cv.rect(g, fx(x + 14), fy(y + 14), fh(w - 28), fh(h - 28), CORK, cv.clear, 0, radius=0)
    for k in range(40):
        cx, cy = x + 24 + (k * 83) % (w - 48), y + 24 + (k * 137) % (h - 48)
        cv.ellipse(g, fx(cx), fy(cy), fh(6), fh(4), CORK_DOT, cv.clear, 0)
    for text, (nx, ny, degrees) in zip(texts, BOARD_SPOTS, strict=False):
        if not text.strip() or len(text) > NOTE_MAX:
            raise ToonDataError(f"a note is 1 to {NOTE_MAX} characters, got {text!r}")
        _note(cv, g, nx, ny, degrees, text)
    mid = (x + w / 2, y + h / 2 + 26.0)
    exclaim(cv, g, mid, 210.0)
    cv.ellipse(g, fx(mid[0] - 12), fy(mid[1] - 117), fh(24), fh(24), PIN, cv.ink, FINE_W * 0.7)
    return g
