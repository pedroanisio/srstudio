"""Cutout at a job interview: the hiring office, and the props of applicants who are never quite shown.

The set follows :mod:`srstudio.locations`: it draws in z-order, calls its slots at the right depth, gates its root group
before drawing, and places both signature marks. Its far plane is its own blurred group, so the cast, the props and the
marks stay sharp. The toddler and the baby are never drawn as characters: a crayon CV with shoes under it, and a crib
with a CV over its rail, stand in for them.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, locations, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = locations.Slot

__all__ = [
    "AD_LINE",
    "CutoutHiringError",
    "HAT_LABEL",
    "HIRING_DESK_Y",
    "crayon_cv",
    "crib",
    "hiring_office",
    "job_ad",
    "paper_hat",
    "roller_blind",
]

HIRING_DESK_Y = 1040  # the desk's far edge
AD_LINE = 24  # the most characters a line of a job ad holds
HAT_LABEL = 8  # the most characters a paper hat holds
SHADOW = "#2A2018"
PAPER = "#FBFAF2"
CRAYON = ("#D23A2E", "#2F6FB5", "#3C9A58", "#E39A22")
SKIN = "#F2C9A5"


class CutoutHiringError(SrstudioError, ValueError):
    """A prop or the set asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutHiringError, f"scale must be a positive number, got {scale!r}")


@register(
    "prop",
    "job-ad",
    style="cutout",
    summary="A printed job advert standing on a desk, a small heading over two lines of large type",
)
def job_ad(
    cv: Canvas,
    parent,
    x=540,
    y=1380,
    *,
    heading: str = "NOW HIRING",
    lines: tuple[str, str] = ("ENTRY LEVEL", "10 YEARS' EXPERIENCE"),
    scale: float = 1.0,
    id: str = "job-ad",
):
    """The foot's middle stands on (``x``, ``y``), 640 × 330 at scale 1; ``lines`` are 1 to :data:`AD_LINE` long."""
    cv.require_font("a job ad is printed in it", CutoutHiringError)
    _check_scale(scale)
    if len(lines) != 2 or not all(line.strip() and len(line) <= AD_LINE for line in lines):
        raise CutoutHiringError(f"a job ad has two lines of 1 to {AD_LINE} characters, got {lines!r}")
    if not heading.strip():
        raise CutoutHiringError("a job ad needs a heading")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-1.5)
    look.pool(cv, g, f"{id}-contact", SHADOW + "CC", -330, -26, 700, 56, opacity=0.5)
    cv.rect(g, -320, -330, 640, 330, PAPER, ink, 4)
    cv.rect(g, -320, -330, 640, 66, "#1E2C3C", ink, 4)
    cv.text(g, f"{id}-heading", heading, -310, -324, 620, 54, 34, "#FFFFFF")
    cv.text(g, f"{id}-first", lines[0], -310, -254, 620, 120, 92, "#C8352B")
    cv.text(g, f"{id}-second", lines[1], -310, -122, 620, 90, 50, "#1E2C3C")
    return g


@register(
    "prop",
    "crayon-cv",
    style="cutout",
    summary="A CV in crayon with a clip-on tie, held up by two very small hands, small shoes swinging under it",
)
def crayon_cv(
    cv: Canvas,
    parent,
    x=540,
    y=800,
    *,
    title: str = "MY JOBS",
    swings: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "crayon-cv",
):
    """The sheet's top middle is (``x``, ``y``), 520 × 560 at scale 1, and whoever holds it is entirely behind it.
    The shoes swing in each of the ``swings`` spans."""
    cv.require_font("the CV's title is lettered in it", CutoutHiringError)
    _check_scale(scale)
    if not title.strip():
        raise CutoutHiringError("a CV needs a title")
    checks.spans(
        swings, CutoutHiringError, lambda s: f"a swing is a rising span, got {s!r}", ordered="swings run in order"
    )
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for side, (tag, shift) in enumerate((("left", -74), ("right", 74))):
        shoe = cv.group(g, f"{id}-shoe-{tag}", x=shift, y=540)
        keys: list[tuple[float, float]] = [(0.0, 0.0)]
        for a, b in swings:
            at, sign = a, 1 if side else -1
            while at < b:
                keys.append((at, sign * 16.0))
                at, sign = at + 0.2, -sign
            keys.append((b, 0.0))
        if swings:
            cv.keys(shoe, "rotation", keys, hold=False)
        cv.line(shoe, 0, 0, 0, 74, "#3F4652", 26)
        cv.path(shoe, "M-22 66 L14 66 Q50 72 52 96 L-22 96Z", "#D23A2E", ink, 4)
    cv.rect(g, -260, 0, 520, 560, PAPER, ink, 4)
    cv.text(g, f"{id}-title", title, -240, 192, 480, 90, 66, CRAYON[0])
    for k, yy in enumerate((316, 374, 432, 490)):
        wobble = 16 if k % 2 else -14
        cv.path(g, f"M-200 {yy} Q-90 {yy + wobble} 0 {yy} T{200 - 40 * k} {yy + 4}", stroke=CRAYON[k], sw=11)
    cv.path(g, "M-18 -12 L18 -12 L10 24 L-10 24Z", "#1E2C3C", ink, 3)  # the clip-on tie
    cv.path(g, "M-10 24 L10 24 L24 150 L0 180 L-24 150Z", "#1E2C3C", ink, 3)
    for hx in (-262, 262):
        cv.ellipse(g, hx - 26, 268, 52, 52, SKIN, ink, 3.5)
    return g


@register(
    "prop",
    "crib",
    style="cutout",
    summary="A slatted crib with a mobile over it, whoever is inside hidden, a CV hooked over the rail and a rattle "
    "that shakes on cue",
)
def crib(
    cv: Canvas,
    parent,
    x=540,
    y=1400,
    *,
    rattles: Sequence[tuple[float, float]] = (),
    cv_title: str = "CV",
    scale: float = 1.0,
    id: str = "crib",
):
    """The foot's middle stands on (``x``, ``y``), 800 × 620 at scale 1, the mobile above that."""
    cv.require_font("the CV is lettered in it", CutoutHiringError)
    _check_scale(scale)
    if not cv_title.strip():
        raise CutoutHiringError("a CV needs a title")
    checks.spans(
        rattles, CutoutHiringError, lambda s: f"a rattle is a rising span, got {s!r}", ordered="rattles run in order"
    )
    ink = cv.ink
    wood = "#D9B98D"
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    look.pool(cv, g, f"{id}-contact", SHADOW + "CC", -430, -20, 880, 50, opacity=0.5)
    cv.rect(g, -390, -460, 780, 300, "#FDF5E3", ink, 3)  # the mattress side, behind the bars
    cv.path(g, "M250 -520 L250 -760 L60 -760", stroke=wood, sw=16)
    arm = cv.group(g, f"{id}-mobile", x=60, y=-760)
    cv.keys(arm, "rotation", [(0.0, -4.0), (2.0, 4.0), (4.0, -4.0)], hold=False)
    for k, (hx, colour) in enumerate(((-90, "#E2574A"), (0, "#F0C655"), (90, "#3F7F8C"))):
        cv.line(arm, hx, 0, hx, 90 + 16 * k, "#6E5236", 3)
        cv.ellipse(arm, hx - 26, 90 + 16 * k, 52, 52, colour, ink, 3)
    cv.line(arm, -90, 0, 90, 0, "#6E5236", 5)
    for bar in range(-360, 400, 80):
        cv.rect(g, bar - 9, -500, 18, 500, wood, ink, 3)
    cv.rect(g, -410, -530, 820, 40, wood, ink, 4, radius=12)
    cv.rect(g, -410, -60, 820, 34, wood, ink, 4, radius=8)
    cv.rect(g, -430, -570, 40, 570, wood, ink, 4, radius=8)
    cv.rect(g, 390, -570, 40, 570, wood, ink, 4, radius=8)
    sheet = cv.group(g, f"{id}-cv", x=-250, y=-720, rotation=-3)
    cv.rect(sheet, -120, 0, 240, 300, PAPER, ink, 3.5)
    cv.text(sheet, f"{id}-cv-title", cv_title, -110, 22, 220, 80, 58, "#1E2C3C")
    for k in range(5):
        cv.line(sheet, -90, 122 + k * 32, 90 - (24 if k % 3 == 2 else 0), 122 + k * 32, "#6A6A62", 7)
    cv.ellipse(g, -278, -534, 56, 52, SKIN, ink, 3.5)  # the hand that hooks it over the rail
    toy = cv.group(g, f"{id}-rattle", x=210, y=-540)
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in rattles:
        at, sign = a, 1
        while at < b:
            keys.append((at, sign * 22.0))
            at, sign = at + 0.08, -sign
        keys.append((b, 0.0))
    if rattles:
        cv.keys(toy, "rotation", keys, hold=False)
    cv.rect(toy, -9, -92, 18, 96, "#F0C655", ink, 3, radius=8)
    cv.ellipse(toy, -46, -170, 92, 92, "#E2574A", ink, 3.5)
    cv.ellipse(toy, -25, 0, 50, 46, SKIN, ink, 3.5)
    return g


@register(
    "prop",
    "paper-hat",
    style="cutout",
    summary="A hat folded from one sheet of paper, as worn on a first day, lettered on its band",
)
def paper_hat(cv: Canvas, parent, x=540, y=600, *, label: str = "TRAINEE", scale: float = 1.0, id: str = "paper-hat"):
    """The brim's middle sits on (``x``, ``y``), 220 wide and 130 tall at scale 1."""
    cv.require_font("the hat is lettered in it", CutoutHiringError)
    _check_scale(scale)
    if not label.strip() or len(label) > HAT_LABEL:
        raise CutoutHiringError(f"a hat's label is 1 to {HAT_LABEL} characters, got {label!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-3)
    cv.path(g, "M-110 -34 L0 -132 L110 -34Z", "#FFFFFF", ink, 3.5)
    cv.path(g, "M-34 -34 L0 -132 L24 -34Z", "#E4E1D4", ink, 2)
    cv.rect(g, -112, -36, 224, 44, "#FFFFFF", ink, 3.5)
    cv.text(g, f"{id}-label", label, -108, -36, 216, 42, 30, "#C8352B")
    return g


@register(
    "prop",
    "roller-blind",
    style="cutout",
    summary="A roller blind over an inside window, snapping up on cue, with a pull cord that dips first",
)
def roller_blind(
    cv: Canvas,
    parent,
    x=620,
    y=240,
    w=420,
    h=720,
    *,
    snap: float | None = None,
    colour: str = "#B9B7A6",
    id: str = "roller-blind",
):
    """Over the opening with top left (``x``, ``y``). At ``snap`` the blind rolls up into its box in a fifth of a second
    and the cord, at the left edge, dips just before; with no ``snap`` it stays down."""
    for name, value in (("width", w), ("height", h)):
        checks.positive(value, CutoutHiringError, f"{name} must be positive, got {value!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    sheet = cv.group(g, f"{id}-sheet")
    if snap is not None:
        cv.keys(sheet, "scaleY", [(0.0, 1.0), (snap, 1.0), (snap + 0.2, 0.04)], hold=False)
    cv.rect(sheet, 0, 0, w, h, colour, ink, 3)
    for k in range(1, 7):
        cv.line(sheet, 4, k * h / 7, w - 4, k * h / 7, "#A5A392", 3)
    cv.rect(sheet, -2, h - 14, w + 4, 14, "#8E8C7D", ink, 3)
    cv.rect(g, -14, -26, w + 28, 40, "#E4E1D4", ink, 4, radius=10)
    cord = cv.group(g, f"{id}-cord", x=-30)
    if snap is not None:
        cv.keys(cord, "y", [(0.0, 0.0), (snap - 0.2, 0.0), (snap, 36.0), (snap + 0.2, 0.0)], hold=False)
    cv.line(cord, 0, 0, 0, h - 40, "#3A3A36", 4)
    cv.ellipse(cord, -11, h - 40, 22, 30, "#E4E1D4", ink, 3)
    return g


@register(
    "location",
    "hiring-office",
    style="cutout",
    summary="A hiring manager's office: a slate wall and a poster out of focus, a glass wall onto the next room with "
    "a roller blind, and a desk across the foot of the frame",
)
def hiring_office(
    cv: Canvas,
    parent,
    behind_desk: Slot = None,
    on_desk: Slot = None,
    id: str = "location-hiring-office",
    shots=None,
    next_room: Slot = None,
    *,
    snap: float | None = None,
    depth: float = 7.0,
    code: tuple[float, float, float] = (1000.0, HIRING_DESK_Y + 40, 10.0),
):
    """``next_room`` draws behind the glass and the blind, which covers it until ``snap``; ``behind_desk`` draws who
    sits there, above :data:`HIRING_DESK_Y`; ``on_desk`` draws in front of them. ``code`` is where the signature's
    right end sits and its height, for a reel whose desk things or camera would lose it at the far right."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    cv.rect(g, -10, -10, 1100, 1940, "#5E6F80")  # the frame's edge, where the blur thins out
    far = look.depth(cv, g, f"hiring-depth-{depth:g}", depth)
    wall = cv.grad("hiring-wall", [(0, "#7C8EA0"), (0.6, "#66798B"), (1, "#4E6072")], (0, 0, 1, 0.5))
    cv.rect(far, -300, -300, 1680, 2400, wall)
    cv.rect(far, 60, 150, 400, 520, "#F4EFE0", "#3B3126", 8)
    cv.path(far, "M110 590 L200 430 L280 500 L400 260 L400 590Z", "#3F7F8C")
    cv.ellipse(far, 300, 210, 70, 70, "#F0C655")
    room = cv.group(g, f"{id}-next-room")
    cv.rect(room, 620, 240, 420, 720, "#EFE8D2", ink, 4)
    cv.rect(room, 620, 780, 420, 180, "#D9CFB4")
    locations._call(next_room, room)
    cv.path(g, "M640 250 L720 250 L630 520Z", "#FFFFFF", opacity=0.22)  # the glass
    cv.rect(g, 610, 232, 440, 736, cv.clear, ink, 9)
    roller_blind(cv, g, 620, 240, snap=snap, id=f"{id}-blind")
    locations._call(behind_desk, g)
    top = cv.grad("hiring-desk", [(0, "#9A6E4C"), (0.3, "#A97C53"), (1, "#6F4F35")], (0, 0, 0.2, 1))
    cv.rect(g, -300, HIRING_DESK_Y, 1680, 1200, top, ink, 4)
    cv.rect(g, -300, HIRING_DESK_Y + 4, 1680, 7, "#FFFFFF", opacity=0.25)
    signature.code(cv, g, code[0], code[1], code[2], color="#3B2A1C", align="end")
    signature.cactus(cv, g, 96, HIRING_DESK_Y + 100, 0.55)
    locations._call(on_desk, g)
    return g
