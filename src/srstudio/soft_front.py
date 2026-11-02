"""A Soft front room: a room straight on with a way out, for the reels where a room itself does something.

The rooms of :mod:`srstudio.soft_sets` hold a cast in one place. This one has an opening in its back wall and a hall
behind it, so something can leave the room and still be seen (``wedged``), and someone can look round the door (``hall``
draws behind the wall). There is a rug with the pale print of what used to stand on it, and no furniture: a reel brings
its own. :func:`mug` is what a person carries into a room, and :func:`star_card` is a row of five stars on a card that
asks to be rated, drawn from no one's interface: no words, no logo, one star filled by a jab.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import checks, look, signature
from .blob import FABRIC_FRONT, FABRIC_LINE, FABRIC_SIDE, FABRIC_TOP, RUG, RUG_LINE
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soft_props import STAR_OFF, STAR_ON, STARS, _star
from .soft_sets import FAR_BLUR, HEIGHT, INK_LINE, OVER, WIDTH, Shot, _framed, _framing

__all__ = ["DOOR", "PRINT", "WALL_FOOT", "SoftFrontError", "front_room", "mug", "shelf", "star_card"]

Slot = Callable[[object], object] | None

MUG_INSIDE = "#E2DACD"
WALL_FOOT = 1290.0  # where the back wall meets the floor
DOOR = (720.0, 760.0, 280.0, 530.0)  # x, y, width and height of the opening in the back wall
PRINT = (500.0, 1500.0, 400.0, 120.0)  # x, y, width and height of the pale print a sofa left on the rug
TRIM = 24.0  # px of door frame round the opening
JAB_DIP = 34.0  # px a card gives under a jab
JAB_BACK = 0.22  # seconds it takes to come back


class SoftFrontError(SrstudioError, ValueError):
    """A Soft front room was asked for something it cannot draw."""


def _spans(rows: Sequence[tuple[float, float]]) -> None:
    last = 0.0
    for start, end in rows:
        if not (checks.number(start) and checks.number(end) and last <= start < end):
            raise SoftFrontError(f"a wedged sofa shows over (start, end) spans in rising time, got {list(rows)!r}")
        last = end


def _sofa_end(cv: Canvas, parent, spans: Sequence[tuple[float, float]], id: str) -> None:
    """A whole sofa jammed across the hall on a slant, one arm and its cushions showing through the door."""
    x, y, w, h = DOOR
    g = cv.group(parent, id, x=x + w / 2 + 210, y=y + h - 190, rotation=-22)
    cv.gate(g, spans)
    for foot in (-250, 250):
        cv.rect(g, foot - 18, 146, 36, 56, "#8A6242", cv.ink, INK_LINE, radius=6)
    cv.rect(g, -320, -170, 640, 330, FABRIC_SIDE, FABRIC_LINE, INK_LINE, radius=44)
    for left in (-246, 4):
        cv.rect(g, left, -146, 242, 150, FABRIC_TOP, FABRIC_LINE, INK_LINE, radius=30)
        cv.rect(g, left, 10, 242, 112, FABRIC_FRONT, FABRIC_LINE, INK_LINE, radius=26)
    for left in (-336, 256):
        cv.rect(g, left, -56, 84, 226, FABRIC_FRONT, FABRIC_LINE, INK_LINE, radius=38)


def _wall(cv: Canvas, room, id: str) -> None:
    """The wall as a sheet with the door cut out of it, so what stands in the hall is behind it."""
    x, y, w, h = DOOR
    paint = cv.grad(f"{id}-paper", [(0.0, "#F3E4CB"), (1.0, "#E8D4B4")], (0, 0, 0, 1))
    g = cv.group(room, f"{id}-wall")
    left, right, top, bottom = -OVER, WIDTH + OVER, -OVER, WALL_FOOT
    outer = f"M {left} {top} L {right} {top} L {right} {bottom} L {left} {bottom} Z"
    inner = f"M {x:g} {y:g} L {x:g} {y + h:g} L {x + w:g} {y + h:g} L {x + w:g} {y:g} Z"
    cv.path(g, f"{outer} {inner}", paint)


@register(
    "location",
    "soft-front-room",
    summary="A living room straight on, empty but for its rug: a far window, an opening to a hall where a sofa can be "
    "wedged, and the pale print of a sofa on the rug",
)
def front_room(
    cv: Canvas,
    parent,
    *,
    shots: Sequence[Shot] = (Shot(0.0),),
    wedged: Sequence[tuple[float, float]] = (),
    hall: Slot = None,
    behind: Slot = None,
    cast: Slot = None,
    id: str = "soft-front-room",
):
    """The room: ``wedged`` spans show a sofa stuck in the hall, ``hall`` draws behind the wall, ``behind`` against it
    and ``cast`` on the rug. ``shots`` frame everything but the shelf, the foreground that holds the marks.
    One shot holds its framing; multiple shots cut. ``wedged`` gates follow ``Canvas.local_time``."""
    _spans(wedged)
    framing = _framing(shots)
    g = cv.group(parent, id)
    room = _framed(cv, g, f"{id}-room", framing)
    x, y, w, h = DOOR
    far = look.depth(cv, room, f"{id}-far", FAR_BLUR)
    cv.rect(far, x - 40, y - 40, w + 80, h + 80, "#CDB898")
    cv.rect(far, x + 64, y + 86, 150, 190, "#B69F7E", "#8A7358", 6)  # a picture at the far end of the hall
    cv.rect(far, x - 40, y + h - 70, w + 80, 120, "#A98A66")
    if wedged:
        _sofa_end(cv, room, wedged, f"{id}-sofa")
    if hall is not None:
        hall(room)
    _wall(cv, room, id)
    window = look.depth(cv, room, f"{id}-window", FAR_BLUR)
    sky = cv.grad(f"{id}-sky", [(0.0, "#A9D6EE"), (1.0, "#DDF0F4")], (0, 0, 0, 1))
    cv.rect(window, 330, 560, 250, 390, "#FBF6EA", "#D2BE9E", 8, radius=8)
    cv.rect(window, 352, 582, 206, 346, sky)
    cv.line(window, 455, 582, 455, 928, "#FBF6EA", 10)
    floor = cv.grad(f"{id}-floor", [(0.0, "#C79A6B"), (1.0, "#AE8054")], (0, 0, 0, 1))
    cv.rect(room, -OVER, WALL_FOOT, WIDTH + 2 * OVER, HEIGHT - WALL_FOOT + OVER, floor)
    cv.rect(room, -OVER, WALL_FOOT - 20, x - TRIM + OVER, 24, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(room, x + w + TRIM, WALL_FOOT - 20, WIDTH + OVER - x - w - TRIM, 24, "#FFFFFF", cv.ink, INK_LINE)
    trim = cv.group(room, f"{id}-door-frame")
    cv.rect(trim, x - TRIM, y - TRIM, TRIM, h + TRIM + 4, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(trim, x + w, y - TRIM, TRIM, h + TRIM + 4, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(trim, x - TRIM, y - TRIM, w + 2 * TRIM, TRIM, "#FFFFFF", cv.ink, INK_LINE)
    if behind is not None:
        behind(room)
    cv.ellipse(room, 90, 1360, 900, 400, RUG, RUG_LINE, INK_LINE)
    cv.ellipse(room, 150, 1392, 780, 336, "#F0D7BC")
    px, py, pw, ph = PRINT
    cv.rect(room, px, py, pw, ph, "#F9EEDF", "#E2C8A8", 4, radius=20)
    for fx, fy in ((px + 22, py + 18), (px + pw - 22, py + 18), (px + 22, py + ph - 18), (px + pw - 22, py + ph - 18)):
        cv.ellipse(room, fx - 15, fy - 9, 30, 18, "#D9BC97")
    if cast is not None:
        cast(room)
    shelf(cv, g, id=f"{id}-front")
    return g


def shelf(cv: Canvas, parent, *, id: str):
    """The foreground shelf in the frame's bottom right corner, with both marks: the room's own, and the one to draw
    over a full-frame insert, so the marks stay in the same place through the cut."""
    front = cv.group(parent, id)
    cv.rect(front, 846, 1752, 260, 190, "#B67B4E", cv.ink, INK_LINE, radius=14)
    cv.rect(front, 830, 1736, 290, 36, "#C98C5C", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, front, 968, 1744, 0.72)
    signature.code(cv, front, 880, 1800, 15, color="#F3DFCF")
    return front


@register("prop", "soft-mug", summary="A plain white mug of coffee, for a hand; no lettering, no brand")
def mug(cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, empty: bool = False, id: str = "soft-mug"):
    """A mug 120 x 120 px at ``scale`` 1, centred on (``x``, ``y``). ``empty`` shows its pale inside, not the coffee."""
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftFrontError(f"a mug sits at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, 26, -32, 62, 62, cv.clear, cv.ink, 16)
    cv.ellipse(g, 33, -24, 48, 46, cv.clear, "#F7F3EC", 8)
    cv.rect(g, -60, -56, 112, 116, "#F7F3EC", cv.ink, 6, radius=18)
    cv.ellipse(g, -56, -68, 104, 30, MUG_INSIDE if empty else "#5B3A26", cv.ink, 6)
    return g


@register(
    "graphic",
    "soft-star-card",
    summary="A white card with a row of five empty stars and no words, that dips under a jab as a star fills",
)
def star_card(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    tap: float | None = None,
    stars: int = 1,
    scale: float = 1,
    id: str = "soft-star-card",
):
    """A card 460 x 150 px at ``scale`` 1, centred on (``x``, ``y``). At ``tap`` the first ``stars`` stars fill and the
    card dips and comes back; without ``tap`` it stays empty and still."""
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftFrontError(f"a star card sits at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    if isinstance(stars, bool) or not isinstance(stars, int) or not 1 <= stars <= STARS:
        raise SoftFrontError(f"a jab fills 1 to {STARS} stars, got {stars!r}")
    if tap is not None and not (checks.number(tap) and tap >= 0):
        raise SoftFrontError(f"a jab is a time on the clock, got {tap!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    if tap is not None:
        cv.keys(g, "y", [(0.0, y), (tap, y + JAB_DIP * scale), (tap + JAB_BACK, y)], False)
    cv.rect(g, -230, -75, 460, 150, cv.white, cv.ink, 6, radius=28)
    centres = [-176 + 88 * k for k in range(STARS)]
    for cx in centres:
        cv.path(g, _star(cx, 2, 38), STAR_OFF, cv.ink, 4)
    if tap is not None:
        for k in range(stars):
            lit = cv.group(g, f"{id}-lit-{k + 1}")
            cv.gate(lit, [(tap, 1e6)])
            cv.path(lit, _star(centres[k], 2, 38), STAR_ON, cv.ink, 4)
    return g
