"""Cutout, what a building keeps on someone who keeps coming back: a wall plaque, a lanyard, a cake and streamers.

The plaque is a wall's worth of scrawl until the reel says it is read: a far shot never carries lettering too small to
read, and its ``read`` spans show the real words for the close-up. Nothing here is a real company's: the lettering is
generic and given by the reel. Every refusal is a :class:`CutoutLobbyError`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import _cutout_contracts, checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutLobbyError", "id_lanyard", "paper_streamers", "sheet_cake", "wall_plaque"]

TITLE = 24  # the most characters a plaque's title holds
NAME = 12  # and its name
YEARS = 12  # the most years engraved on it
CAKE_LINE = 12  # the most characters piped on a line of cake
CARD_LABEL = 12  # the most characters on a lanyard's card
BRASS = "#D9B65C"
WOOD = "#5B3C26"
STREAMERS = ("#E2574C", "#F0C233", "#3FA6A0", "#7A5BD0")
ICING = "#FBF3E4"
SPONGE = "#E8C38E"


class CutoutLobbyError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _scale(scale) -> None:
    checks.positive(scale, CutoutLobbyError, f"scale must be a positive number, got {scale!r}")


def _line(value: str, most: int, what: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > most:
        raise CutoutLobbyError(f"{what} is 1 to {most} characters, got {value!r}")


@register(
    "prop",
    "wall-plaque",
    style="cutout",
    summary="A brass plaque on a wood back, scrawl until it is read",
    contract=_cutout_contracts.contract('wall-plaque'),
)
def wall_plaque(
    cv: Canvas,
    parent,
    x=300,
    y=500,
    *,
    title: str = "EMPLOYEE OF THE YEAR",
    name: str = "A NAME",
    years: Sequence[str] = ("2024", "2025"),
    read: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "wall-plaque",
):
    """The middle sits on (``x``, ``y``), 240 × 190 at scale 1. ``read`` are the spans its real lettering shows, for a
    close-up; outside them it is scrawl."""
    _line(title, TITLE, "a plaque's title")
    _line(name, NAME, "a plaque's name")
    if not 1 <= len(years) <= YEARS:
        raise CutoutLobbyError(f"a plaque holds 1 to {YEARS} years, got {len(years)}")
    for year in years:
        _line(year, 6, "a plaque's year")
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -120, -95, 240, 190, WOOD, ink, 3.5, radius=6)
    cv.rect(g, -106, -82, 212, 164, BRASS, ink, 2.5, radius=3)
    for sx in (-96, 96):
        for sy in (-72, 72):
            cv.ellipse(g, sx - 3, sy - 3, 6, 6, "#8A6F2F")
    far = cv.group(g, f"{id}-scrawl")
    if read:
        cv.keys(far, "opacity", [(0.0, 1), *((t, v) for a, b in read for t, v in ((a, 0), (b, 1)))])
    for k, (half, top) in enumerate(((78, -62), (40, -40), (30, -14), (30, 2), (30, 18), (30, 34), (30, 50))):
        for side in (-1, 1) if k > 1 else (0,):
            cv.line(far, side * 44 - half, top, side * 44 + half, top, "#6E5722", 5 if k < 2 else 3)
    if not read:
        return g
    near = cv.group(g, f"{id}-read")
    cv.gate(near, read)
    cv.require_font("a plaque is lettered in it", CutoutLobbyError)
    cv.text(near, f"{id}-title", title, -102, -76, 204, 22, 15, "#3B2A10")
    cv.text(near, f"{id}-name", name, -102, -54, 204, 34, 28, "#3B2A10")
    per_column = (len(years) + 1) // 2
    for n, year in enumerate(years):
        column = n // per_column
        cv.text(near, f"{id}-year-{n}", year, -90 + column * 92, -14 + n % per_column * 15, 88, 15, 12, "#4C3814")
    return g


@register(
    "prop",
    "sheet-cake",
    style="cutout",
    summary="A white sheet cake on a board, piped with two lines of icing",
    contract=_cutout_contracts.contract('sheet-cake'),
)
def sheet_cake(
    cv: Canvas,
    parent,
    x=540,
    y=1060,
    *,
    lines: tuple[str, str] = ("WELL", "DONE"),
    scale: float = 1.0,
    id: str = "sheet-cake",
):
    """The board's middle stands on (``x``, ``y``), 460 × 170 at scale 1; ``lines`` are 1 to :data:`CAKE_LINE` long."""
    if len(lines) != 2:
        raise CutoutLobbyError(f"a cake is piped with two lines, got {lines!r}")
    for line in lines:
        _line(line, CAKE_LINE, "a line of cake")
    _scale(scale)
    cv.require_font("a cake is piped in it", CutoutLobbyError)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -240, -18, 480, 26, "#C9C2B2", ink, 3)
    cv.rect(g, -214, -156, 428, 146, SPONGE, ink, 3.5, radius=10)
    cv.path(g, "M-214 -146 Q-214 -158 -202 -158 L202 -158 Q214 -158 214 -146 L214 -70 Q190 -52 172 -74 Q150 -44 "
               "120 -74 Q84 -52 52 -74 Q14 -48 -20 -74 Q-58 -50 -92 -74 Q-126 -54 -152 -74 Q-186 -48 -214 -74Z",
            ICING, ink, 3)  # fmt: skip
    cv.text(g, f"{id}-line-1", lines[0], -200, -152, 400, 34, 26, "#C8352B")
    cv.text(g, f"{id}-line-2", lines[1], -200, -120, 400, 34, 26, "#C8352B")
    for k in range(9):
        cv.ellipse(g, -192 + k * 44, -22, 22, 16, "#F7B7C4", ink, 2)
    return g


@register(
    "prop",
    "id-lanyard",
    style="cutout",
    summary="A staff lanyard with a clip and a card with a small photo",
    contract=_cutout_contracts.contract('id-lanyard'),
    slots=('photo',),
)
def id_lanyard(
    cv: Canvas,
    parent,
    x=400,
    y=800,
    *,
    photo: Callable | None = None,
    label: str = "STAFF",
    scale: float = 1.0,
    id: str = "id-lanyard",
):
    """The top of the loop hangs from (``x``, ``y``), 270 long to the bottom of a 136 × 170 card at scale 1. ``photo``
    receives a child group at local y=178; draw around (0, 0) within its 88 × 84 window. It is not clipped."""
    _line(label, CARD_LABEL, "a lanyard's card")
    _scale(scale)
    cv.require_font("a lanyard's card is printed in it", CutoutLobbyError)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-30 0 L-5 86 L5 86 L30 0", stroke=ink, sw=9)
    cv.path(g, "M-30 0 L-5 86 L5 86 L30 0", stroke="#2F6FB5", sw=6)
    cv.rect(g, -9, 84, 18, 18, "#B9BEC4", ink, 2.5, radius=3)
    cv.rect(g, -68, 100, 136, 170, cv.white, ink, 3.5, radius=8)
    cv.rect(g, -68, 100, 136, 28, "#2F6FB5", ink, 2.5, radius=8)
    cv.rect(g, -32, 104, 64, 8, cv.white, radius=3)
    window = cv.group(g, f"{id}-photo", y=178)
    cv.rect(window, -44, -44, 88, 84, "#D5DEE6", ink, 2.5)
    if photo is not None:
        photo(window)
    cv.rect(g, -44, 224, 88, 44, cv.white)
    cv.text(g, f"{id}-label", label, -62, 228, 124, 28, 20, "#1E2C3C")
    return g


@register(
    "prop",
    "paper-streamers",
    style="cutout",
    summary="Swags of crepe paper pinned along a wall, for a party",
    contract=_cutout_contracts.contract('paper-streamers'),
)
def paper_streamers(
    cv: Canvas, parent, x0=100, x1=980, y=200, *, swags: int = 4, sag: float = 90.0, id: str = "paper-streamers"
):
    """Pinned along ``y`` from ``x0`` to ``x1`` at the ends of ``swags`` swags that hang ``sag`` at their middle."""
    if isinstance(swags, bool) or not isinstance(swags, int) or swags < 1:
        raise CutoutLobbyError(f"streamers hang at least one whole swag, got {swags!r}")
    checks.positive(sag, CutoutLobbyError, f"sag must be a positive number, got {sag!r}")
    if not (checks.number(x0) and checks.number(x1) and checks.number(y)) or x1 <= x0:
        raise CutoutLobbyError(f"streamers run left to right along a wall, got {x0!r} to {x1!r} at {y!r}")
    ink = cv.ink
    g = cv.group(parent, id)
    step = (x1 - x0) / swags
    for n in range(swags):
        a, b = x0 + n * step, x0 + (n + 1) * step
        mid = (a + b) / 2
        paper = STREAMERS[n % len(STREAMERS)]
        cv.path(g, f"M{a:g} {y:g} Q{mid:g} {y + 2 * sag:g} {b:g} {y:g} Q{mid:g} {y + 2 * sag - 44:g} {a:g} {y:g}Z",
                paper, ink, 2.5)  # fmt: skip
        cv.ellipse(g, a - 9, y - 9, 18, 18, STREAMERS[(n + 1) % len(STREAMERS)], ink, 2.5)
    cv.ellipse(g, x1 - 9, y - 9, 18, 18, STREAMERS[0], ink, 2.5)
    return g
