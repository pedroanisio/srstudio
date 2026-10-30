"""Cutout at home and in the shops: a study, a shop till, and the props a home printer's ransom demand needs.

Each set follows :mod:`srstudio.locations`: it draws in z-order, calls its slots at the right depth, gates its root
group before drawing, and places both signature marks. A set's far plane is its own blurred group, so the cast, the
props and the marks stay sharp. One light per set, from the window or the ceiling at the top left: every contact
shadow falls down and to the right.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from . import checks, locations, look, props, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = locations.Slot

__all__ = [
    "CutoutHomeError",
    "LCD_CHARS",
    "NOTE_LINE",
    "STUDY_DESK_Y",
    "TILL_TOP",
    "desk_printer",
    "desk_top",
    "hostage_photo",
    "home_study",
    "paper_bag",
    "ransom_note",
    "shop_till",
]

STUDY_DESK_Y = 960  # the desk's far edge: whoever sits behind it is hidden below this line
TILL_TOP = 1120  # the shop counter's far edge
LCD_CHARS = 16  # the most characters the printer's display holds
NOTE_LINE = 12  # the most characters a line of a ransom note holds at its size
CHIPS = (  # paper, letter: magazine scraps; none of them cyan, which is the point
    ("#FBF6E6", "#1B1B1F"),
    ("#1B1B1F", "#FBF6E6"),
    ("#C8352B", "#FFF4DE"),
    ("#F3C54B", "#1B1B1F"),
    ("#FFFFFF", "#C8352B"),
    ("#2F7D4F", "#FFF4DE"),
    ("#E9D8BC", "#3A2A6B"),
)
PAGE = "#FBFAF2"
SHADOW = "#2A2018"


class CutoutHomeError(SrstudioError, ValueError):
    """A prop or a set asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutHomeError, f"scale must be a positive number, got {scale!r}")


def _shadow(cv: Canvas, g, name: str, x, y, w, h, opacity: float = 0.5) -> None:
    """A contact shadow on what a prop rests on, a little to the right of it: the light is at the top left."""
    look.pool(cv, g, name, SHADOW + "CC", x, y, w, h, opacity=opacity)


def _lettering(cv: Canvas, g, x, y, width, lines: int, colour: str, opacity: float = 0.75) -> None:
    """Grey body text as a scrawl: lines of a page too small to read."""
    for k in range(lines):
        end = width if k % 4 != 3 else width * 0.62
        cv.line(g, x, y + k * 26, x + end, y + k * 26, colour, 7, opacity=opacity)


def _shake(cv: Canvas, g, spans: Sequence[tuple[float, float]], reach: float = 5.0) -> None:
    """``g`` rattles sideways in each span, a key every other frame, and rests between them."""
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in spans:
        keys.append((a, 0.0))
        t, sign = a + 0.066, 1
        while t < b:
            keys.append((t, sign * reach))
            t, sign = t + 0.066, -sign
        keys.append((b, 0.0))
    cv.keys(g, "x", keys, hold=False)


@register(
    "prop",
    "desk-printer",
    style="cutout",
    summary="A home printer seen from the front: a display that shows readings over time, a rattle while it whirs, "
    "and sheets that slide into its tray",
)
def desk_printer(
    cv: Canvas,
    parent,
    x=540,
    y=1300,
    *,
    lcd: tuple[tuple[float, str], ...] = ((0.0, "READY"),),
    whirs: Sequence[tuple[float, float]] = (),
    sheets: tuple[tuple[float, float, str], ...] = (),
    scale: float = 1.0,
    id: str = "desk-printer",
):
    """The foot's middle stands on (``x``, ``y``). ``lcd`` is ``(time, text)`` from 0 in rising order, each held until
    the next (1 to :data:`LCD_CHARS` characters); ``whirs`` are spans it rattles; ``sheets`` are ``(start, seconds,
    colour)``: a sheet slides out of the slot over ``seconds`` and lies in the tray, its text in ``colour``, until the
    next sheet."""
    cv.require_font("the printer's display is set in it", CutoutHomeError)
    _check_scale(scale)
    times = [t for t, _ in lcd]
    if not lcd or times[0] != 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise CutoutHomeError(f"lcd readings start at 0 and rise strictly, got {times!r}")
    for _, text in lcd:
        if not text.strip() or len(text) > LCD_CHARS:
            raise CutoutHomeError(f"a reading has 1 to {LCD_CHARS} characters, got {text!r}")
    checks.spans(whirs, CutoutHomeError, lambda s: f"a whir is a rising span, got {s!r}", ordered="whirs run in order")
    starts = [s[0] for s in sheets]
    if any(b <= a for a, b in zip(starts, starts[1:], strict=False)):
        raise CutoutHomeError(f"sheets slide out in time order, got {starts!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    _shadow(cv, g, "printer-contact", -380, -36, 800, 84)
    shell = cv.group(g, f"{id}-shell")
    if whirs:
        _shake(cv, shell, whirs)
    plastic = cv.grad("printer-plastic", [(0, "#F1EFE7"), (0.55, "#D9D6CB"), (1, "#B3B0A6")], (0, 0, 0.4, 1))
    # the feed tray and its paper, behind the body
    cv.path(shell, "M-200 -430 L-186 -556 L186 -556 L200 -430Z", PAGE, ink, 4)
    cv.path(shell, "M-236 -430 L-226 -500 L226 -500 L236 -430Z", "#8E8C84", ink, 4)
    # the body
    cv.rect(shell, -360, -430, 720, 430, plastic, ink, 5, radius=34)
    cv.rect(shell, -340, -412, 150, 10, "#FFFFFF", radius=5, opacity=0.8)  # the lit top edge, from the left
    cv.rect(shell, -290, -166, 580, 36, "#23262A", ink, 4, radius=12)  # the slot
    tray = cv.grad("printer-tray", [(0, "#A9A69C"), (1, "#D7D4C9")], (0, 0, 0, 1))
    cv.path(shell, "M-300 -120 L300 -120 L340 -6 L-340 -6Z", tray, ink, 4)
    for k, (start, seconds, colour) in enumerate(sheets):
        until = sheets[k + 1][0] if k + 1 < len(sheets) else None
        sheet = cv.group(shell, f"{id}-sheet-{k + 1}", y=-260)
        cv.gate(sheet, [(start, until if until is not None else 3600.0)])
        cv.keys(sheet, "y", [(0, -260), (start, -260), (start + seconds, -120)], hold=False)
        cv.rect(sheet, -230, 0, 460, 240, PAGE, ink, 3)
        cv.rect(sheet, -190, 22, 240, 16, colour)
        _lettering(cv, sheet, -190, 66, 380, 6, colour, opacity=0.9)
    # the face of the shell, over the slot's top, hides a sheet until it comes out
    cv.path(
        shell, "M-360 -396 Q-360 -430 -326 -430 L326 -430 Q360 -430 360 -396 L360 -166 L-360 -166Z", plastic, ink, 5
    )
    cv.line(shell, -360, -372, 360, -372, "#A7A49A", 3)
    cv.rect(shell, -250, -348, 400, 124, "#2E3530", ink, 5, radius=14)  # the display's bezel
    cv.rect(shell, -236, -334, 372, 96, "#BFD4A7", radius=6)
    for k, (t, text) in enumerate(lcd):
        shown = cv.group(shell, f"{id}-reading-{k + 1}")
        cv.gate(shown, [(t, lcd[k + 1][0] if k + 1 < len(lcd) else 3600.0)])
        cv.text(shown, f"{id}-lcd-{k + 1}", text, -232, -330, 364, 88, 50, "#1B2A1E")
    cv.ellipse(shell, 190, -340, 44, 44, "#C9C6BB", ink, 3.5)  # two buttons
    cv.ellipse(shell, 262, -340, 44, 44, "#C9C6BB", ink, 3.5)
    cv.ellipse(shell, 226, -270, 30, 30, "#E2574A", ink, 3)  # the warning light
    return g


@register(
    "prop",
    "ransom-note",
    style="cutout",
    summary="A ransom note: a sheet with its demand in letters cut from magazines, each on its own scrap",
)
def ransom_note(
    cv: Canvas,
    parent,
    x=120,
    y=170,
    *,
    lines: tuple[str, ...] = ("WE HAVE", "YOUR", "DOCUMENT"),
    seed: int = 7,
    height: float = 1040,
    size: float = 104,
    id: str = "ransom-note",
):
    """The sheet's top left is (``x``, ``y``), 840 wide and ``height`` tall, a little askew, a shadow to its right.
    Each of the ``lines`` (1 to :data:`NOTE_LINE` characters) is centred, its letters on seeded scraps."""
    cv.require_font("a ransom note's letters are set in it", CutoutHomeError)
    if not lines or not all(isinstance(line, str) and 0 < len(line.strip()) <= NOTE_LINE for line in lines):
        raise CutoutHomeError(f"lines are 1 to {NOTE_LINE} characters each, got {lines!r}")
    checks.positive(height, CutoutHomeError, f"height must be positive, got {height!r}")
    checks.positive(size, CutoutHomeError, f"size must be positive, got {size!r}")
    pitch = size * 1.34
    if len(lines) * pitch > height:
        raise CutoutHomeError(f"{len(lines)} lines at {size} px do not fit a {height} px sheet")
    rng = random.Random(seed)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, rotation=rng.uniform(-1.6, 1.6))
    _shadow(cv, g, "note-contact", 40, 60, 860, height, opacity=0.55)
    cv.rect(g, 0, 0, 840, height, PAGE, ink, 3)
    top = (height - pitch * len(lines)) / 2 + pitch * 0.14
    last = -1
    for row, line in enumerate(lines):
        cell = min(size * 0.96, 800 / max(len(line), 1))
        left = 420 - cell * len(line) / 2
        for k, ch in enumerate(line):
            if ch == " ":
                continue
            choice = rng.randrange(len(CHIPS) - 1)
            last = choice if choice < last else choice + 1
            paper, letter = CHIPS[last]
            high = rng.uniform(0.86, 1.0)
            scrap = cv.group(
                g,
                cv.uid("ransom-scrap"),
                x=left + (k + 0.5) * cell,
                y=top + row * pitch + size * 0.56 + rng.uniform(-8, 8),
                rotation=rng.uniform(-7, 7),
            )
            half = cell * 0.47
            tall = size * 0.62 * high
            cv.path(
                scrap,
                f"M{-half + rng.uniform(-2, 3):.1f} {-tall + rng.uniform(-3, 4):.1f} "
                f"L{half + rng.uniform(-3, 2):.1f} {-tall + rng.uniform(-3, 4):.1f} "
                f"L{half + rng.uniform(-3, 2):.1f} {tall + rng.uniform(-4, 3):.1f} "
                f"L{-half + rng.uniform(-2, 3):.1f} {tall + rng.uniform(-4, 3):.1f}Z",
                paper,
                "#00000033",
                1.5,
            )
            cv.text(
                scrap,
                cv.uid("ransom-letter"),
                ch,
                -half,
                -tall,
                round(2 * half),
                round(2 * tall),
                round(size * high * 0.86),
                letter,
            )
    return g


@register(
    "prop",
    "hostage-photo",
    style="cutout",
    summary="An instant photo of a sheet of paper tied to a chair with rope, under one bulb",
)
def hostage_photo(
    cv: Canvas, parent, x=270, y=760, *, rotation: float = -5, scale: float = 1.0, id: str = "hostage-photo"
):
    """The photo's top left is (``x``, ``y``), 540 × 560 at scale 1, taped to whatever it lies on."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, rotation=rotation, scaleX=scale, scaleY=scale)
    _shadow(cv, g, "photo-contact", 30, 40, 560, 560, opacity=0.5)
    cv.rect(g, 0, 0, 540, 560, "#F7F4EA", ink, 3)
    room = cv.grad("photo-room", [(0, "#5B5148"), (1, "#2C2622")], (0, 0, 0, 1))
    cv.rect(g, 28, 28, 484, 440, room, ink, 2.5)
    look.pool(cv, g, "photo-bulb", "#FFE2A8AA", 90, 40, 360, 330)
    cv.line(g, 270, 28, 270, 84, "#17130F", 4)
    cv.ellipse(g, 254, 82, 32, 34, "#FFF1C4", ink, 2.5)
    # the chair, then the sheet sat on it, then the rope
    cv.rect(g, 164, 136, 16, 300, "#7A5234", ink, 3)
    cv.rect(g, 360, 136, 16, 300, "#7A5234", ink, 3)
    cv.rect(g, 164, 136, 212, 22, "#8E6340", ink, 3)
    cv.rect(g, 150, 340, 240, 22, "#8E6340", ink, 3)
    cv.rect(g, 172, 362, 14, 96, "#7A5234", ink, 3)
    cv.rect(g, 354, 362, 14, 96, "#7A5234", ink, 3)
    sheet = cv.group(g, f"{id}-sheet", x=270, y=250, rotation=3)
    cv.rect(sheet, -82, -106, 164, 212, PAGE, ink, 2.5)
    cv.rect(sheet, -62, -88, 92, 10, "#1B1B1F")
    for k in range(7):
        end = 124 if k % 4 != 3 else 80
        cv.line(sheet, -62, -60 + k * 15, -62 + end, -60 + k * 15, "#55554F", 4, opacity=0.8)
    for yy, tilt in ((194, 6), (288, -5)):
        cv.path(g, f"M146 {yy + tilt} Q270 {yy - tilt + 14} 394 {yy - tilt}", stroke="#D8BE8A", sw=11)
        cv.path(g, f"M146 {yy + tilt} Q270 {yy - tilt + 14} 394 {yy - tilt}", stroke="#8F7443", sw=2)
    tape = cv.group(g, f"{id}-tape", rotation=4)
    cv.rect(tape, 196, -22, 150, 44, "#EFE3B4", radius=2, opacity=0.8)
    return g


@register("prop", "paper-bag", style="cutout", summary="A very small paper carrier bag with string handles")
def paper_bag(cv: Canvas, parent, x=760, y=1300, *, scale: float = 1.0, id: str = "paper-bag"):
    """Its foot's middle stands on (``x``, ``y``)."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    _shadow(cv, g, "bag-contact", -80, -22, 190, 40)
    kraft = cv.grad("bag-kraft", [(0, "#D9B98D"), (1, "#B4906A")], (0, 0, 1, 0.3))
    cv.path(g, "M-44 -150 Q0 -216 44 -150", stroke=ink, sw=5)
    cv.path(g, "M-70 0 L-62 -150 L62 -150 L70 0Z", kraft, ink, 4)
    cv.path(g, "M-62 -150 L-52 -132 L52 -132 L62 -150", stroke="#8F7150", sw=3)
    return g


def desk_top(cv: Canvas, parent, id: str = "study-desk-top"):
    """The study's desk seen from above, filling the frame, for an insert of something lying on it."""
    g = cv.group(parent, id)
    wood = cv.grad("study-desk-above", [(0, "#A97C53"), (0.5, "#8F6845"), (1, "#6F4F35")], (0, 0, 0.3, 1))
    cv.rect(g, 0, 0, 1080, 1920, wood)
    for k, yy in enumerate((180, 420, 690, 930, 1210, 1470, 1740)):
        cv.path(g, f"M-20 {yy} Q300 {yy - 16 + 7 * k} 560 {yy + 6} T1100 {yy - 8}", stroke="#5C4029", sw=3, opacity=0.4)
    return g


def _book(cv: Canvas, g, x, y, w, h, colour):
    cv.rect(g, x, y - h, w, h, colour, "#3B3126", 2)


@register(
    "location",
    "home-study",
    style="cutout",
    summary="A study at home: a sage wall, a window with a curtain, a bookshelf out of focus, and a desk that fills "
    "the foot of the frame",
)
def home_study(
    cv: Canvas,
    parent,
    behind_desk: Slot = None,
    on_desk: Slot = None,
    id: str = "location-home-study",
    shots=None,
    cactus: Slot = None,
    *,
    depth: float = 7.0,
):
    """``behind_desk`` draws whoever sits at the desk, above :data:`STUDY_DESK_Y`; ``on_desk`` draws in front of them
    on the desk top. The window lights the room from the top left. ``depth`` blurs the room behind the desk."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    far = look.depth(cv, g, f"study-depth-{depth:g}", depth)
    wall = cv.grad("study-wall", [(0, "#BACABD"), (0.55, "#A5B9AF"), (1, "#8DA49D")], (0, 0, 1, 0.5))
    cv.rect(far, -300, -300, 1680, 2000, wall)
    sky = cv.grad("study-sky", [(0, "#F6D9A6"), (1, "#FBEFD8")], (0, 0, 0, 1))
    cv.rect(far, 40, 120, 330, 520, sky, "#F4EFE2", 22)
    cv.line(far, 205, 120, 205, 640, "#F4EFE2", 12)
    cv.line(far, 40, 370, 370, 370, "#F4EFE2", 12)
    cv.path(far, "M10 90 Q70 330 30 700 L-60 700 L-60 90Z", "#B4574A")
    cv.path(far, "M400 90 Q340 330 372 700 L440 700 L440 90Z", "#C8695B")
    cv.rect(far, -60, 74, 520, 20, "#6E5236")
    shelf = cv.group(far, f"{id}-shelf")
    for yy in (330, 620, 910):
        cv.rect(shelf, 700, yy, 420, 22, "#7D5C3F")
        xx = 716.0
        rng = random.Random(yy)
        while xx < 1090:
            w = rng.uniform(26, 52)
            _book(
                cv,
                shelf,
                xx,
                yy,
                w,
                rng.uniform(150, 214),
                rng.choice(("#3F6F80", "#C9A24E", "#A44B3F", "#E9E0CC", "#55703F")),
            )
            xx += w + 2
    light = cv.group(g, f"{id}-light")
    cv.path(light, "M60 640 L360 640 L1000 1500 L420 1500Z", "#FFE9BE", cv.clear, 0, opacity=0.16)
    locations._call(behind_desk, g)
    top = cv.grad("study-desk", [(0, "#B98A5E"), (0.35, "#CFA377"), (1, "#8F6A49")], (0, 0, 0.3, 1))
    cv.rect(g, -300, STUDY_DESK_Y, 1680, 1400, top, ink, 4)
    for k, yy in enumerate((1030, 1130, 1260, 1430, 1640, 1830)):
        cv.path(
            g, f"M-20 {yy} Q300 {yy - 12 + 6 * k} 560 {yy + 4} T1100 {yy - 6}", stroke="#7F5B3D", sw=2.5, opacity=0.4
        )
    cv.path(g, "M120 960 L420 960 L960 1800 L420 1800Z", "#FFF2D6", cv.clear, 0, opacity=0.14)  # the window on the desk
    signature.code(cv, props.papers(cv, g, 700, 1570, 0.8, 5), 20, 10, 11, color="#5C625D")
    signature.home_cactus(cv, g, 96, 1050, 0.62, slot=cactus)
    locations._call(on_desk, g)
    return g


@register(
    "location",
    "shop-till",
    style="cutout",
    summary="A shop's till: shelves out of focus and a pale laminate counter that fills the foot of the frame",
)
def shop_till(
    cv: Canvas, parent, on_counter: Slot = None, id: str = "location-shop-till", shots=None, *, depth: float = 9.0
):
    """``on_counter`` draws on the counter, whose far edge is :data:`TILL_TOP`. The ceiling lights it from above left.
    ``depth`` blurs the shelves."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    far = look.depth(cv, g, f"till-depth-{depth:g}", depth)
    cv.rect(far, -300, -300, 1680, 1800, cv.grad("till-wall", [(0, "#EFEBDD"), (1, "#CFCDBE")], (0, 0, 0, 1)))
    rng = random.Random(41)
    for yy in (300, 560, 820, 1080):
        cv.rect(far, -100, yy, 1280, 24, "#8FA6A8")
        xx = -80.0
        while xx < 1160:
            w = rng.uniform(60, 120)
            cv.rect(
                far,
                xx,
                yy - rng.uniform(100, 180),
                w,
                200,
                rng.choice(("#D9694F", "#3F7F8C", "#F0C655", "#6F9A5A", "#ECE4D2")),
            )
            xx += w + 8
    glow = cv.group(g, f"{id}-light")
    look.pool(cv, glow, "till-lamp", "#FFF6D8AA", 120, 200, 840, 760)
    top = cv.grad("till-counter", [(0, "#F4EFE3"), (0.4, "#E6DFCF"), (1, "#BDB5A3")], (0, 0, 0.2, 1))
    cv.rect(g, -300, TILL_TOP, 1680, 1200, top, ink, 4)
    cv.rect(g, -300, TILL_TOP + 4, 1680, 8, "#FFFFFF", opacity=0.7)
    signature.code(cv, g, 1000, TILL_TOP + 40, 10, color="#8A8474", align="end")
    signature.cactus(cv, g, 120, TILL_TOP + 90, 0.55)
    locations._call(on_counter, g)
    return g
