"""A bed for two in the Toon style: the two-shot :func:`srstudio.toon_house.bedroom` cannot hold, its headboard and
quilt being cut for one.

:func:`double_bed` is the wall behind it, day or night, a window with its blind and two pillows on one headboard;
:func:`double_quilt` goes in front of the cast with the nightstand that signs the shot. :func:`floor_corner` and
:func:`bedside_drawer` are the same room from the floor, a drawer large enough to act: it buzzes and slides out on its
cues, a phone's light in the gap, and :func:`quilt_heap` is what covers a lap on that floor. :func:`swung_arm` is a limb
of a character's coat, swinging about its shoulder, for the arm a Toon figure does not have free: thrown across a
partner, or stretched at the ceiling. Nothing here letters a word but the signature code. Bad input is a
:class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from . import _toon_care_contracts as tc
from . import anatomy_ledger, checks, signature
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_house import BEDROOM_WALL, HEADBOARD, NIGHTSTAND, NIGHTSTAND_FRONT, PILLOW, QUILTS

__all__ = [
    "BLIND",
    "NIGHTSTAND_TOP",
    "PHONE_SPOT",
    "SKY",
    "SUN_BAND",
    "bedside_drawer",
    "double_bed",
    "double_quilt",
    "floor_corner",
    "quilt_heap",
    "swung_arm",
]

Point = tuple[float, float]
DAY_WALL = (("0", "#f8e9c8"), ("0.7", "#f3dfb6"), ("1", "#ecd3a3"))
BLIND, BLIND_LINE, SKY, SUN, SUN_BAND = "#3a4570", "#2c3559", "#bfe6f7", "#fff3b8", "#ffe89a"
FRAME, ROLLED = "#efe6d6", "#d6cbb8"
FLOOR, FLOOR_DARK, SKIRTING = "#7a5a44", "#5f4534", "#d9cfbd"
GAP, GLOW = "#17110d", "#bcd6ff"
WINDOW = (118.0, 320.0, 150.0, 150.0)  # x, y, w, h, reference pixels: over the headboard, under the caption pill,
# and left of the middle, so a cut in on the left of the bed keeps it out of the show's corner
HEAD = (6.0, 456.0, 476.0, 620.0)  # the headboard
PILLOWS = ((22.0, 590.0, 226.0, 190.0), (244.0, 590.0, 226.0, 190.0))
QUILT_TOP = 820.0
QUILT_X, QUILT_W = -20.0, 506.0
NIGHTSTAND_X, NIGHTSTAND_W = 484.0, 126.0
NIGHTSTAND_TOP = 836.0  # the surface a phone stands on
PHONE_SPOT = (516.0, NIGHTSTAND_TOP)
HEAP_TOP = 836.0
FLOOR_Y = 1010.0  # where the corner's wall meets its floor
STAND = (318.0, 548.0, 330.0, 560.0)  # the close nightstand: x, y, w, h
DRAWER = (344.0, 592.0, 300.0, 150.0)  # the front of its top drawer
SLIDE = 0.45  # seconds the drawer takes to slide
SHAKE = ((0.0, 0.0), (0.04, -7.0), (0.09, 7.0), (0.14, -6.0), (0.19, 6.0), (0.24, -3.0), (0.3, 0.0))  # seconds, pixels
ARM_WIDTH = 66.0
HEX = re.compile(r"#[0-9a-fA-F]{6}")


def _wall(cv: Canvas, g, day: bool) -> None:
    stops = DAY_WALL if day else BEDROOM_WALL
    paint = cv.grad(
        "toon-double-bed-day" if day else "toon-bedroom-wall", [(float(o), c) for o, c in stops], (0, 0, 0, 1)
    )
    cv.rect(g, 0, 0, cv.width, cv.height, paint)


def _window(cv: Canvas, g, day: bool) -> None:
    x, y, w, h = WINDOW
    if day:
        cv.rect(g, fx(x), fy(y), fh(w), fh(h), SKY, cv.ink, INK_W * 0.8, radius=fh(4))
        cv.ellipse(g, fx(x + w - 66), fy(y + 18), fh(46), fh(46), SUN)
        cv.rect(g, fx(x + w / 2 - 3), fy(y), fh(6), fh(h), FRAME)
        cv.rect(g, fx(x), fy(y + h / 2 - 3), fh(w), fh(6), FRAME)
        cv.rect(g, fx(x - 8), fy(y - 10), fh(w + 16), fh(22), ROLLED, cv.ink, FINE_W * 0.8, radius=fh(3))
        return
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), BLIND, cv.ink, INK_W * 0.8, radius=fh(4))
    for k in range(1, 8):
        cv.rect(g, fx(x), fy(y + k * h / 8), fh(w), fh(3), BLIND_LINE)


@register(
    "location",
    "toon-double-bed",
    contract=tc.contract('toon-double-bed'),
    summary="A headboard and two pillows for a couple in bed, the wall behind by night with the blind down or by day",
    style="toon",
)
def double_bed(cv: Canvas, parent, *, day: bool = False) -> object:
    """The wall, the window and the bed behind the two characters; :func:`double_quilt` goes in front of them. Returns
    its group."""
    g = cv.group(parent, cv.uid("g"))
    _wall(cv, g, day)
    _window(cv, g, day)
    x, y, w, h = HEAD
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), HEADBOARD, cv.ink, INK_W * 0.8, radius=fh(40))
    for px, py, pw, ph in PILLOWS:
        cv.rect(g, fx(px), fy(py), fh(pw), fh(ph), PILLOW, cv.ink, INK_W * 0.7, radius=fh(84))
    return g


@register(
    "prop",
    "toon-double-quilt",
    contract=tc.contract('toon-double-quilt'),
    summary="A quilt across a double bed in front of the cast, a nightstand beside it signed as the desk is",
    style="toon",
)
def double_quilt(cv: Canvas, parent, pattern: str = "plum", *, day: bool = False, signed: bool = True) -> object:
    """A quilt from side to side of :func:`double_bed`, one of :data:`srstudio.toon_house.QUILTS`, the nightstand with
    the cactus and the code, and by ``day`` the sun in bands across it. A reel whose close shots lose the nightstand
    signs on something they keep and passes ``signed=False``. Returns its group."""
    if pattern not in QUILTS:
        raise ToonDataError(f"a quilt is one of {sorted(QUILTS)}, got {pattern!r}")
    base, patch = QUILTS[pattern]
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(NIGHTSTAND_X), fy(NIGHTSTAND_TOP), fh(NIGHTSTAND_W), fh(18), NIGHTSTAND, cv.ink, FINE_W, radius=fh(3))
    cv.rect(
        g,
        fx(NIGHTSTAND_X),
        fy(NIGHTSTAND_TOP + 18),
        fh(NIGHTSTAND_W),
        fh(320),
        NIGHTSTAND_FRONT,
        cv.ink,
        FINE_W,
        radius=0,
    )
    if signed:
        signature.cactus(cv, g, fx(NIGHTSTAND_X + 66), fy(NIGHTSTAND_TOP), 0.7)
        signature.code(
            cv, g, fx(NIGHTSTAND_X + 96), fy(NIGHTSTAND_TOP + 30), 14, color="#b9a48f", opacity=0.9, align="end"
        )
    cv.rect(g, fx(QUILT_X), fy(QUILT_TOP), fh(QUILT_W), fh(420), base, cv.ink, INK_W, radius=fh(30))
    for row, top in enumerate(range(int(QUILT_TOP) + 30, 1130, 76)):
        for col, left in enumerate(range(0, 400, 92)):
            if (row + col) % 2 == 0:
                cv.rect(g, fx(left), fy(top), fh(78), fh(62), patch, cv.clear, 0, radius=fh(6))
    if day:
        for ray in (70.0, 214.0, 358.0):
            cv.path(
                g,
                f"M {fx(ray)} {fy(QUILT_TOP + 6)} L {fx(ray + 84)} {fy(QUILT_TOP + 6)} "
                f"L {fx(ray + 40)} {cv.height} L {fx(ray - 44)} {cv.height} Z",
                SUN_BAND,
                cv.clear,
                0,
                opacity=0.28,
            )
    return g


@register(
    "location",
    "toon-bedroom-corner",
    contract=tc.contract('toon-bedroom-corner'),
    summary="The floor beside the bed: the wall by night or day, a skirting board and floorboards",
    style="toon",
)
def floor_corner(cv: Canvas, parent, *, day: bool = False) -> object:
    """The wall and the floor a character sits on beside the bed. Returns its group."""
    g = cv.group(parent, cv.uid("g"))
    _wall(cv, g, day)
    cv.rect(g, 0, fy(FLOOR_Y - 26), cv.width, fh(26), SKIRTING, cv.ink, FINE_W)
    cv.rect(g, 0, fy(FLOOR_Y), cv.width, cv.height - fy(FLOOR_Y), FLOOR)
    for top in (FLOOR_Y + 40, FLOOR_Y + 90):
        cv.rect(g, 0, fy(top), cv.width, fh(4), FLOOR_DARK)
    return g


@register(
    "prop",
    "toon-quilt-heap",
    contract=tc.contract('toon-quilt-heap'),
    summary="A quilt dragged down and heaped in the foreground, over the lap of whoever sits on the floor behind it",
    style="toon",
)
def quilt_heap(cv: Canvas, parent, pattern: str = "plum", *, x: float = -30.0, width: float = 430.0) -> object:
    """A heap of one of :data:`srstudio.toon_house.QUILTS` from reference ``x`` across ``width``, standing on the
    frame's foot, its top at :data:`HEAP_TOP`. Returns its group."""
    if pattern not in QUILTS:
        raise ToonDataError(f"a quilt is one of {sorted(QUILTS)}, got {pattern!r}")
    if not (checks.number(x) and checks.number(width) and width > 0):
        raise ToonDataError(f"a heap's x and width are numbers, the width over 0, got {x}, {width}")
    base, patch = QUILTS[pattern]
    g = cv.group(parent, cv.uid("g"))
    x0, x1, top, foot = fx(x), fx(x + width), fy(HEAP_TOP), float(cv.height) + 20.0
    bump = (x1 - x0) / 3
    d = (
        f"M {x0} {foot} L {x0} {top + 40} "
        f"C {x0 + bump * 0.4} {top - 26} {x0 + bump * 0.8} {top - 20} {x0 + bump} {top + 14} "
        f"C {x0 + bump * 1.3} {top - 34} {x0 + bump * 1.8} {top - 30} {x0 + bump * 2} {top + 10} "
        f"C {x0 + bump * 2.4} {top - 20} {x1 + 10} {top + 10} {x1 + 40} {foot} Z"
    )
    cv.path(g, d, base, cv.ink, INK_W)
    for row, y in enumerate((HEAP_TOP + 40.0, HEAP_TOP + 120.0, HEAP_TOP + 200.0)):
        for col in range(4):
            if (row + col) % 2 == 0:
                cv.rect(g, fx(x + 24 + col * 84), fy(y), fh(70), fh(56), patch, cv.clear, 0, radius=fh(6))
    return g


def _cue(value: object, what: str) -> float:
    if not (checks.number(value) and float(value) >= 0):
        raise ToonDataError(f"{what} on a second from 0, got {value!r}")
    return float(value)


@register(
    "prop",
    "toon-bedside-drawer",
    contract=tc.contract('toon-bedside-drawer'),
    summary="A nightstand close up, its drawer buzzing against whatever leans on it and sliding out by itself on cue",
    style="toon",
)
def bedside_drawer(
    cv: Canvas, parent, *, buzzes: Sequence[float] = (), slides: float | None = None, lit: float = 0.0
) -> object:
    """The nightstand from the floor with the cactus on it and the code on its side, its top drawer shaking at each of
    ``buzzes`` and easing out from second ``slides``, ``lit`` the finite 0..1 opacity of the light in the gap.
    Motion and light use composition keys; the light remains on after opening. Returns only the moving drawer
    front, nested inside the cabinet. Use a caller-owned parent to move or hide the whole nightstand."""
    shakes = [_cue(t, "a drawer's buzz") for t in buzzes]
    out = None if slides is None else _cue(slides, "a drawer slides")
    if not (checks.number(lit) and 0 <= lit <= 1):
        raise ToonDataError(f"a drawer's light is a finite opacity from 0 to 1, got {lit!r}")
    g = cv.group(parent, cv.uid("g"))
    x, y, w, h = STAND
    cv.rect(g, fx(x), fy(y - 22), fh(w), fh(26), NIGHTSTAND, cv.ink, INK_W * 0.8, radius=fh(5))
    cv.rect(g, fx(x + 10), fy(y), fh(w), fh(h), NIGHTSTAND_FRONT, cv.ink, INK_W * 0.8)
    signature.cactus(cv, g, fx(x + 150), fy(y - 22), 1.1)
    dx, dy, dw, dh = DRAWER
    signature.code(cv, g, fx(x + 240), fy(dy + dh + 44), 18, color="#b9a48f", opacity=0.9, align="end")
    cv.rect(g, fx(dx), fy(dy), fh(dw), fh(dh), GAP)
    if out is not None and lit > 0:
        glow = cv.rect(g, fx(dx), fy(dy), fh(dw), fh(26), GLOW, opacity=lit)
        light_keys = ([(0.0, 0.0)] if out else []) + [(out, lit)]
        cv.keys(glow, "opacity", light_keys, local=False)
    drawer = cv.group(g, cv.uid("g"), anchorX=fx(dx + dw / 2), anchorY=fy(dy + dh), x=fx(dx + dw / 2), y=fy(dy + dh))
    cv.rect(drawer, fx(dx), fy(dy), fh(dw), fh(dh), NIGHTSTAND, cv.ink, FINE_W, radius=fh(4))
    cv.ellipse(drawer, fx(dx + dw / 2 - 18), fy(dy + dh / 2 - 18), fh(36), fh(36), "#c9a56b", cv.ink, FINE_W * 0.7)
    if shakes:
        cv.keys(
            drawer,
            "x",
            [(t + at, round(fx(dx + dw / 2) + px, 2)) for t in shakes for at, px in SHAKE],
            hold=False,
            local=False,
        )
    if out is not None:
        for prop, far in (("scaleX", 1.05), ("scaleY", 0.86)):
            cv.keys(
                drawer, prop, [(0.0, 1.0), (out, 1.0), (out + SLIDE, far)], hold=False, kind="sine-in-out", local=False
            )
    return drawer


@register(
    "prop",
    "toon-swung-arm",
    contract=tc.contract('toon-swung-arm'),
    summary="A character's arm in its own coat, swinging about the shoulder: flopped across a partner or stretched up",
    style="toon",
)
def swung_arm(
    cv: Canvas,
    parent,
    shoulder: Point,
    coat: str,
    swing: Sequence[tuple[float, float]],
    start: float,
    end: float,
    *,
    length: float = 190.0,
    width: float = ARM_WIDTH,
) -> object:
    """An arm from ``shoulder`` (reference pixels) in ``coat``, on screen from ``start`` to ``end``, at the angles of
    ``swing``: ``(project second, degrees)``, 0 pointing right, turning clockwise. Returns its group. It ends in a hand,
    so it is drawn in ``anatomy_ledger.on_arm`` naming whose arm it is, which records the hand there; otherwise the
    build is refused as a hand on no character's arm (ADR 0174)."""
    if not swing or not all(checks.number(t) and checks.number(deg) for t, deg in swing):
        raise ToonDataError(f"an arm's swing is (second, degrees) rows, got {swing!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"an arm needs 0 <= start < end, got {start}..{end}")
    if not (isinstance(coat, str) and HEX.fullmatch(coat)):
        raise ToonDataError(f"an arm's coat is a #rrggbb colour, got {coat!r}")
    if not (checks.number(length) and length > 0 and checks.number(width) and width > 0):
        raise ToonDataError(f"an arm's length and width are over 0, got {length}, {width}")
    g = cv.group(
        parent, cv.uid("g"), start=start, end=end, anchorX=0.0, anchorY=0.0, x=fx(shoulder[0]), y=fy(shoulder[1])
    )
    cv.keys(g, "rotation", list(swing), hold=False, kind="cubic-out", local=False)
    anatomy_ledger.loose_hand(cv, "toon-swung-arm", g.id)  # whose arm it is, from anatomy_ledger.on_arm (ADR 0174)
    long, half = fh(length), fh(width) / 2
    knuckle = long - half * 0.3
    edge = (
        f"M 0 {-half * 1.25} C {long * 0.4} {-half * 1.1} {long * 0.7} {-half * 0.9} {knuckle} {-half} "
        f"C {long + half} {-half} {long + half} {half} {knuckle} {half} "
        f"C {long * 0.7} {half * 0.9} {long * 0.4} {half * 1.1} 0 {half * 1.25}"
    )
    cv.path(g, f"{edge} Z", coat, cv.clear, 0)  # filled to the shoulder, inked only along its length: it grows out of
    cv.path(g, edge, None, cv.ink, FINE_W)  # the body it joins, with no seam across it
    for k in (-0.42, 0.0, 0.42):
        cv.path(
            g,
            f"M {knuckle + half * 0.1} {half * k} L {knuckle + half * 0.62} {half * k * 0.8}",
            None,
            cv.ink,
            FINE_W * 0.7,
        )
    return g
