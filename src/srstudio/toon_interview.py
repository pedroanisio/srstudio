"""An interview room in the Toon style: what a company puts on its wall and a desk puts in front of a candidate.

:func:`wall_sign` is a company's name in the set, lettered to read on a phone; :func:`blind` comes down over the window
:func:`srstudio.toon.room` draws, on cue; :func:`tissue_box` and :func:`sample_tray` stand on a desk's top; and
:func:`paper` lies on it. Everything is drawn at reference coordinates into a shot's groups, and bad input is a
:class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from ._toon_story_contracts import contract
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _d, _path, fh, fx, fy
from .toon_sets import _line, _shadow

__all__ = [
    "BLIND_BOX",
    "BLIND_CLOSED",
    "SIGN_BOX",
    "SIGN_MAX",
    "SIGN_SIZE",
    "TOP_Y",
    "blind",
    "paper",
    "sample_tray",
    "tissue_box",
    "wall_sign",
]

Point = tuple[float, float]
TOP_Y = 838.0  # where a thing stands on the desk's top, the cactus's foot
SIGN_BOX = (40.0, 118.0, 512.0, 92.0)  # x, y, w, h: over the caption pill, clear of the show's corner
SIGN_MAX, SIGN_SIZE = 26, 60  # characters on the sign's one line, and their frame pixels
SIGN, SIGN_INK, SIGN_RIM = "#20443a", "#f4e3b2", "#c9a24d"
BLIND_BOX = (372.0, 296.0, 240.0, 400.0)  # the window of srstudio.toon.room, x, y, w, h; it runs off the frame
BLIND_SLAT, BLIND_LINE, BLIND_RAIL = "#efe6d2", "#c8bb9f", "#b7a98c"
BLIND_CLOSED = 0.05  # what is left of the blind's height when it is up
SLATS = 14
TISSUE, TISSUE_BOX, TISSUE_BAND = "#ffffff", "#7fb3d5", "#f6f1e3"
TRAY, TRAY_RIM = "#5d4a3c", "#3c2f27"
GROUTS = ("#e9e4d8", "#b8b3a8", "#7f7a72", "#d8c6a5")  # samples, left to right
PAPER, PAPER_LINE = "#fbfaf4", "#9aa1ad"


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _scale(scale: object) -> float:
    if not (checks.number(scale) and float(scale) > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


@register(
    "prop",
    "toon-wall-sign",
    summary="A company's name on a wall plaque, in the set, read on a phone",
    style="toon",
    contract=contract('toon-wall-sign'),
)
def wall_sign(cv: Canvas, parent, text: str = "DUNMORE GROUT SUPPLY") -> object:
    """``text`` (1 to :data:`SIGN_MAX` characters) on a dark plaque across the top of the wall. Returns its group."""
    if not text.strip() or len(text) > SIGN_MAX:
        raise ToonDataError(f"a wall sign is 1 to {SIGN_MAX} characters, got {text!r}")
    x, y, w, h = SIGN_BOX
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x + 5), fy(y + 7), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(6), opacity=0.16)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), SIGN, cv.ink, INK_W * 0.8, radius=fh(6))
    cv.rect(g, fx(x + 8), fy(y + 8), fh(w - 16), fh(h - 16), cv.clear, SIGN_RIM, FINE_W * 0.5, radius=fh(3))
    cv.text(g, cv.uid("wall-sign"), text, fx(x + 12), fy(y + 12), int(fh(w - 24)), int(fh(h - 24)), SIGN_SIZE,
            color=SIGN_INK, wrap="none")  # fmt: skip
    return g


@register(
    "prop",
    "toon-blind",
    summary="A slatted blind over the room's window, up or coming down on cue",
    style="toon",
    contract=contract('toon-blind'),
)
def blind(cv: Canvas, parent, drop: tuple[float, float] | None = None, down: bool = False) -> object:
    """A blind on :data:`BLIND_BOX`: rolled up under its rail, falling over the ``drop`` span, or ``down`` from the
    first frame. Returns its group."""
    if drop is not None:
        a, b = drop
        if not (checks.number(a) and checks.number(b) and 0 <= a < b):
            raise ToonDataError(f"a blind drops over 0 <= start < end, got {drop!r}")
        if down:
            raise ToonDataError("a blind already down has no drop")
    x, y, w, h = BLIND_BOX
    g = cv.group(parent, cv.uid("g"))
    leaf = cv.group(
        g, cv.uid("g"), anchorX=fx(x), anchorY=fy(y), x=fx(x), y=fy(y), scaleY=1.0 if down else BLIND_CLOSED
    )
    cv.rect(leaf, fx(x), fy(y), fh(w), fh(h), BLIND_SLAT, cv.clear, 0, radius=0)
    step = h / SLATS
    for k in range(1, SLATS + 1):
        cv.rect(leaf, fx(x), fy(y + k * step - 4), fh(w), fh(4), BLIND_LINE, cv.clear, 0, radius=0)
    if drop is not None:
        cv.keys(leaf, "scaleY", [(0.0, BLIND_CLOSED), (drop[0], BLIND_CLOSED), (drop[1], 1.0)], hold=False, local=False)
    cv.rect(g, fx(x - 10), fy(y - 10), fh(w + 20), fh(24), BLIND_RAIL, cv.ink, FINE_W * 0.8, radius=fh(3))
    return g


@register(
    "prop",
    "toon-tissue-box",
    summary="A box of tissues on the desk, one standing up out of it",
    style="toon",
    contract=contract('toon-tissue-box'),
)
def tissue_box(cv: Canvas, parent, at: Point = (300.0, TOP_Y), scale: float = 1.0) -> object:
    """A tissue box whose foot is on reference ``at``. Returns its group."""
    x, y = _point(at, "a tissue box")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    _shadow(cv, g, x, y + 2, 110 * s)
    w, h = 100.0 * s, 52.0 * s
    puff = _d("M", (x - 22 * s, y - h + 4), "C", (x - 26 * s, y - h - 26 * s), (x - 4 * s, y - h - 44 * s),
              (x + 6 * s, y - h - 40 * s), "C", (x + 26 * s, y - h - 34 * s), (x + 20 * s, y - h - 12 * s),
              (x + 24 * s, y - h + 4), "Z")  # fmt: skip
    _path(cv, g, puff, TISSUE, FINE_W)
    _line(cv, g, [(x - 4 * s, y - h - 30 * s), (x + 2 * s, y - h - 6 * s)], 3.0 * s)
    cv.rect(g, fx(x - w / 2), fy(y - h), fh(w), fh(h), TISSUE_BOX, cv.ink, INK_W * 0.8, radius=fh(5 * s))
    cv.rect(g, fx(x - w / 2 + 6 * s), fy(y - h * 0.46), fh(w - 12 * s), fh(9 * s), TISSUE_BAND, cv.clear, 0, radius=0)
    return g


@register(
    "prop",
    "toon-sample-tray",
    summary="A shallow tray of little sample bars, for a trade's samples",
    style="toon",
    contract=contract('toon-sample-tray'),
)
def sample_tray(
    cv: Canvas,
    parent,
    at: Point = (300.0, TOP_Y),
    colours: Sequence[str] = GROUTS,
    missing: tuple[int, float] | None = None,
    scale: float = 1.0,
) -> object:
    """A tray on the desk with one upright bar of each of ``colours``; ``missing`` is ``(index, second)``, that bar
    gone from that second. Returns its group."""
    x, y = _point(at, "a tray")
    s = _scale(scale)
    if not 1 <= len(colours) <= 6:
        raise ToonDataError(f"a tray holds 1 to 6 samples, got {len(colours)}")
    if missing is not None and not (0 <= missing[0] < len(colours) and checks.number(missing[1]) and missing[1] >= 0):
        raise ToonDataError(f"a missing sample is (index, second), got {missing!r}")
    g = cv.group(parent, cv.uid("g"))
    _shadow(cv, g, x, y + 2, 170 * s)
    step = 25.0 * s
    left = x - step * (len(colours) - 1) / 2
    for k, colour in enumerate(colours):
        timed = {"end": missing[1]} if missing is not None and missing[0] == k else {}
        bar = cv.group(g, cv.uid("g"), **timed)
        cv.rect(
            bar,
            fx(left + k * step - 9 * s),
            fy(y - 48 * s),
            fh(18 * s),
            fh(36 * s),
            colour,
            cv.ink,
            FINE_W * 0.6,
            radius=fh(3 * s),
        )
    w = max(step * len(colours) + 16 * s, 80 * s)
    cv.rect(g, fx(x - w / 2), fy(y - 18 * s), fh(w), fh(18 * s), TRAY, cv.ink, INK_W * 0.7, radius=fh(4 * s))
    return g


@register(
    "prop",
    "toon-paper",
    summary="A resume lying on the desk, unlettered, its lines a scrawl",
    style="toon",
    contract=contract('toon-paper'),
)
def paper(cv: Canvas, parent, at: Point = (300.0, 830.0), scale: float = 1.0) -> object:
    """A sheet lying flat on the desk's top, seen low, centred on reference ``at``. Returns its group."""
    x, y = _point(at, "a sheet")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    sheet = _d("M", (x - 58 * s, y + 10 * s), "L", (x - 42 * s, y - 12 * s), "L", (x + 42 * s, y - 12 * s),
               "L", (x + 58 * s, y + 10 * s), "Z")  # fmt: skip
    _path(cv, g, sheet, PAPER, FINE_W * 0.8)
    for k in (-6.0, 0.0, 6.0):
        _line(cv, g, [(x - 34 * s, y + k * s), (x + 34 * s, y + k * s)], 2.5 * s, PAPER_LINE)
    return g
