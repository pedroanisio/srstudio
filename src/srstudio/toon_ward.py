"""A hospital ward for Toon: the room a character wakes up in, and what the crash left on him."""

from __future__ import annotations

from typing import Any

from . import _toon_care_contracts as tc
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy

__all__ = ["BED_TOP", "bandage", "ward", "ward_bed"]

WALL, DADO, CURTAIN, CURTAIN_FOLD, RAIL, METAL = "#d9ebe4", "#a9cfc4", "#f2d9a8", "#e0c188", "#8f9aa0", "#c9d2d6"
SHEET, SHEET_FOLD, BLANKET = "#fbfaf4", "#dde3e2", "#7fb7c7"
GAUZE, GAUZE_FOLD = "#fdfcf6", "#d9d6cb"
BED_TOP = 742.0  # reference y of the sheet's edge, in front of whoever lies in the bed


@register(
    "location",
    "toon-ward",
    contract=tc.contract('toon-ward'),
    summary="A hospital ward: a pale wall, a drawn curtain on its rail and a drip stand",
)
def ward(cv: Canvas, parent) -> None:
    """The wall, a curtain drawn along the left on a rail, and a drip stand on the right with its bag."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, WALL)
    cv.rect(g, fx(-10), fy(640), fh(640), fh(320), DADO, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(-10), fy(146), fh(640), fh(10), RAIL, cv.ink, FINE_W, radius=4)
    cv.rect(g, fx(-10), fy(156), fh(120), fh(600), CURTAIN, cv.ink, INK_W, radius=0)
    for x in range(10, 110, 28):
        cv.rect(g, fx(x), fy(156), fh(10), fh(600), CURTAIN_FOLD, cv.clear, 0, radius=0)
    cv.rect(g, fx(516), fy(150), fh(10), fh(620), METAL, cv.ink, FINE_W, radius=4)
    cv.rect(g, fx(486), fy(196), fh(70), fh(10), METAL, cv.ink, FINE_W, radius=4)
    cv.rect(g, fx(496), fy(206), fh(50), fh(90), "#f7fbfb", cv.ink, INK_W * 0.7, radius=14)
    cv.rect(g, fx(502), fy(240), fh(38), fh(50), "#cfe9ee", cv.clear, 0, radius=10)
    cv.rect(g, fx(519), fy(296), fh(4), fh(180), RAIL, cv.clear, 0, radius=2)


@register(
    "prop",
    "toon-ward-bed",
    contract=tc.contract('toon-ward-bed'),
    summary="The foot of a hospital bed: a turned-down sheet over a blue blanket",
)
def ward_bed(cv: Canvas, parent, marks_in: float = 0.0) -> None:
    """The sheet and blanket across the frame, in front of whoever lies in the bed, up to :data:`BED_TOP`."""
    from . import signature

    g = cv.group(parent, cv.uid("g"))
    blanket = fy(BED_TOP + 56)  # its foot and outline run off the frame, so a shot with no punch-in never shows them
    cv.rect(g, fx(-20), blanket, fh(640), cv.height - blanket + 2 * INK_W, BLANKET, cv.ink, INK_W, radius=0)
    cv.rect(g, fx(-20), fy(BED_TOP), fh(640), fh(64), SHEET, cv.ink, INK_W, radius=18)
    for x in (60, 196, 340, 470):
        cv.rect(g, fx(x), fy(BED_TOP + 10), fh(5), fh(46), SHEET_FOLD, cv.clear, 0, radius=2)
    signature.cactus(cv, g, fx(548 - marks_in), fy(838), 0.7)
    signature.code(cv, g, fx(580 - marks_in), fy(866), 14, color="#0b3a53", opacity=0.9, align="end")


@register(
    "prop",
    "toon-bandage",
    contract=tc.contract('toon-bandage'),
    summary="A bandage round a character's head, and a plaster on the cheek",
)
def bandage(cv: Canvas, parent, start: float, end: float, look: Any) -> Any:
    """A band of gauze across the brow of a rig's ``look``, tied off at the side, and a crossed plaster on one cheek.
    It goes in the face's own group, so it stays on him when he talks. Returns its group."""
    if not 0 <= start < end:
        raise ToonDataError(f"a bandage needs 0 <= start < end, got {start!r}..{end!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    (left, y), (right, _) = look.eyes
    wide = (right - left) * 2.6
    centre = (left + right) / 2
    top = y - 98.0
    cv.rect(g, fx(centre - wide / 2), fy(top), fh(wide), fh(44), GAUZE, cv.ink, INK_W * 0.8, radius=16)
    cv.rect(g, fx(centre - wide / 2 + 14), fy(top + 20), fh(wide - 28), fh(4), GAUZE_FOLD, cv.clear, 0, radius=2)
    cv.rect(g, fx(right + 30), fy(top + 34), fh(16), fh(40), GAUZE, cv.ink, FINE_W, radius=6)
    cheek = (right + 18.0, y + 52.0)
    cv.rect(g, fx(cheek[0] - 22), fy(cheek[1] - 8), fh(44), fh(16), GAUZE, cv.ink, FINE_W, radius=5)
    cv.rect(g, fx(cheek[0] - 8), fy(cheek[1] - 22), fh(16), fh(44), GAUZE, cv.ink, FINE_W, radius=5)
    return g
