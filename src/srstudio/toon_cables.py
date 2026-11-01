"""The cable drawer every home has, the one cable nobody can name, the bin, and the hill those cables turn out to run.

:func:`cable_drawer` is a drawer in the front of a counter, yanked open at a second and closed at another, with a knot
of cables in it. :func:`gray_cable` is one cable with a plug, held at a point and carried along timed moves.
:func:`kitchen_bin` is a plain bin in the foreground. :func:`hill_window` is a kitchen window at night on a hill with a
street running down it, whose lights go out one at a time in order and come back on together.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy

__all__ = ["BIN_AT", "DRAWER_AT", "STREET", "cable_drawer", "fridge_light", "gray_cable", "hill_window", "kitchen_bin"]

DRAWER_AT = (300.0, 1030.0)  # the middle of the drawer's front, reference units
DRAWER_W, DRAWER_H = 330.0, 124.0
PANEL, PANEL_EDGE, HANDLE = "#b57d48", "#8d5c30", "#e9e2d2"
TRAY, TRAY_IN = "#d3b184", "#3a2a1e"
OPEN_SCALE = 1.16  # a drawer pulled towards the viewer
YANK, SHUT = 0.14, 0.45  # seconds
CABLES = ("#2b2b33", "#e9e2d2", "#6b7280", "#a33a3a", "#3a6ea8", "#2b2b33", "#e9e2d2", "#6b7280")
GREY, PLUG = "#8b929c", "#5a6069"
CABLE_LENGTH = 150.0  # reference units from where it is held to the plug
BIN_AT = (96.0, 1120.0)  # the foot of the bin
BIN_W, BIN_H = 150.0, 190.0
BIN, BIN_DARK, BIN_RIM = "#7c8796", "#5c6675", "#a7b1bf"
FRIDGE_LIGHT_AT = (532.0, 372.0)  # on the door of the kitchen's fridge
FRIDGE_CASE, FRIDGE_GLOW = "#4a5563", "#d6f2ff"
WALL = "#f4e0c0"
SKY = (("0", "#0f1838"), ("0.7", "#22285a"), ("1", "#3a2f6e"))
HILL, FAR_HILL, ROAD = "#141a33", "#1b2240", "#262d4a"
FRAME_WOOD, FRAME_EDGE = "#efe3d2", "#d7c7ae"
LAMP, GLOW, DARK_LAMP, POLE = "#ffe7a8", "#ffd27a", "#3b4160", "#0b0f20"
HALO_MID = "#6e5426"
HOUSE_LIT, HOUSE_DARK = "#ffd36b", "#232a48"
GLASS = (56.0, 150.0, 480.0, 640.0)  # x, y, width, height of the glass
STREET = (
    (92.0, 380.0, 1.0),
    (150.0, 420.0, 0.95),
    (214.0, 464.0, 0.9),
    (278.0, 508.0, 0.85),
    (336.0, 548.0, 0.8),
    (392.0, 586.0, 0.72),
    (440.0, 622.0, 0.64),
    (484.0, 654.0, 0.56),
)  # top of the hill first, x, y and how near
HOUSES = ((116.0, 520.0), (196.0, 566.0), (306.0, 640.0), (408.0, 500.0), (476.0, 548.0), (82.0, 640.0))
KNOT = (
    "M -130 -30 C -90 -120 -40 -40 -10 -86 S 60 -130 80 -60 S 140 -70 120 -20",
    "M -110 -20 C -60 -70 -30 -130 20 -70 S 90 -30 130 -40",
    "M -70 -24 C -40 -100 30 -110 40 -50 S -10 -20 -60 -60",
    "M -20 -20 C 10 -120 90 -110 96 -60 S 40 -30 10 -70",
    "M -136 -26 C -120 -80 -70 -90 -56 -50 S -90 -24 -110 -40",
    "M 40 -24 C 60 -90 130 -100 126 -46",
    "M -30 -26 C -60 -60 -14 -116 30 -96",
    "M 70 -22 C 100 -60 20 -96 -10 -60",
)


def _point(at: object, what: str) -> tuple[float, float]:
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"a {what} stands at a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


@register("prop", "toon-cable-drawer", summary="A drawer in a counter's front, yanked open on a knot of cables")
def cable_drawer(
    cv: Canvas,
    parent,
    opens: float,
    closes: float | None = None,
    *,
    at: tuple[float, float] = DRAWER_AT,
    end: float | None = None,
    id: str | None = None,
):
    """The drawer's front at reference ``at``, shut until ``opens``, when it comes out over :data:`YANK` seconds on its
    knot, and shut again over :data:`SHUT` seconds from ``closes``. ``end`` is when the shot ends: a drawer holds open
    to it. Returns the drawer's group."""
    x, y = _point(at, "drawer")
    if not (checks.number(opens) and opens >= 0):
        raise ToonDataError(f"a drawer opens at a second >= 0, got {opens!r}")
    if closes is not None and not (checks.number(closes) and closes >= opens + YANK):
        raise ToonDataError(f"a drawer closes after it has opened, got {closes!r} after {opens!r}")
    g = cv.group(parent, id or cv.uid("cable-drawer"), x=fx(x), y=fy(y))
    scale = [(opens, 1.0), (opens + YANK, OPEN_SCALE)]
    if closes is not None:
        scale += [(closes, OPEN_SCALE), (closes + SHUT, 1.0)]
    cv.keys(g, "scaleX", scale, hold=False, local=False)
    cv.keys(g, "scaleY", scale, hold=False, local=False)
    half, h = DRAWER_W / 2, DRAWER_H
    inside = cv.group(g, cv.uid("drawer-in"), start=opens, **({"end": closes + SHUT} if closes is not None else {}))
    cv.rect(inside, fh(-half + 8), fh(-h / 2 - 40), fh(DRAWER_W - 16), fh(46), TRAY_IN, cv.ink, INK_W * 0.7,
            radius=fh(6))  # fmt: skip
    for k, d in enumerate(KNOT):
        cv.path(inside, _scaled(d, fh(1.0), -h / 2 + 8), cv.clear, CABLES[k % len(CABLES)], fh(5.0))
    cv.rect(inside, fh(-half + 2), fh(-h / 2 - 8), fh(DRAWER_W - 4), fh(16), TRAY, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fh(-half), fh(-h / 2), fh(DRAWER_W), fh(h), PANEL, cv.ink, INK_W * 0.8, radius=fh(8))
    cv.rect(g, fh(-half + 12), fh(-h / 2 + 12), fh(DRAWER_W - 24), fh(h - 24), PANEL, PANEL_EDGE, FINE_W, radius=fh(5))
    cv.rect(g, fh(-52), fh(-9), fh(104), fh(18), HANDLE, cv.ink, FINE_W, radius=fh(9))
    return g


def _scaled(d: str, k: float, dy: float) -> str:
    """A path of reference numbers about a point, in frame pixels, moved ``dy`` reference units down."""
    out, axis = [], 0
    for word in d.split():
        if word.isalpha():
            out.append(word)
            axis = 0
            continue
        value = float(word) + (dy if axis % 2 else 0.0)
        out.append(f"{value * k:.2f}")
        axis += 1
    return " ".join(out)


@register("prop", "toon-gray-cable", summary="One gray cable with a plug, held at its top, that goes where it is moved")
def gray_cable(
    cv: Canvas,
    parent,
    moves: Sequence[tuple[float, float, float]],
    start: float,
    end: float,
    *,
    id: str | None = None,
):
    """The cable's top on reference ``(x, y)`` at each ``(second, x, y)`` of ``moves``, going straight from one to the
    next, on screen from ``start`` to ``end``. Returns its group."""
    if not moves or any(not all(checks.number(v) for v in m) for m in moves):
        raise ToonDataError(f"a cable moves through (second, x, y), got {moves!r}")
    if any(b[0] <= a[0] for a, b in zip(moves, moves[1:], strict=False)):
        raise ToonDataError(f"a cable's moves run forward in time, got {moves!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a cable shows over 0 <= start < end, got {start!r}..{end!r}")
    g = cv.group(parent, id or cv.uid("gray-cable"), start=start, end=end, x=fx(moves[0][1]), y=fy(moves[0][2]))
    if len(moves) > 1:
        cv.keys(g, "x", [(t, round(fx(x), 2)) for t, x, _ in moves], hold=False, local=False)
        cv.keys(g, "y", [(t, round(fy(y), 2)) for t, _, y in moves], hold=False, local=False)
    length = fh(CABLE_LENGTH)
    w = fh(1.0)
    cv.path(g, f"M 0 0 C {18 * w:.2f} {length * 0.3:.2f} {-18 * w:.2f} {length * 0.6:.2f} 0 {length:.2f}", cv.clear,
            cv.ink, fh(9.0))  # fmt: skip
    cv.path(g, f"M 0 0 C {18 * w:.2f} {length * 0.3:.2f} {-18 * w:.2f} {length * 0.6:.2f} 0 {length:.2f}", cv.clear,
            GREY, fh(5.0))  # fmt: skip
    cv.rect(g, fh(-12), length, fh(24), fh(30), PLUG, cv.ink, FINE_W, radius=fh(4))
    for dx in (-6, 6):
        cv.rect(g, fh(dx - 2), length + fh(30), fh(4), fh(14), "#c9ced6", cv.ink, FINE_W * 0.4, radius=0)
    return g


@register("prop", "toon-kitchen-bin", summary="A plain gray kitchen bin in the foreground, open at the top")
def kitchen_bin(cv: Canvas, parent, at: tuple[float, float] = BIN_AT):
    """The bin with its foot at reference ``at``. Returns its front, for what lands in it to go behind."""
    x, y = _point(at, "bin")
    g = cv.group(parent, cv.uid("kitchen-bin"))
    left, top = x - BIN_W / 2, y - BIN_H
    cv.rect(g, fx(left), fy(top), fh(BIN_W), fh(BIN_H), BIN, cv.ink, INK_W * 0.8, radius=fh(12))
    cv.rect(g, fx(left + 22), fy(top + 24), fh(24), fh(BIN_H - 40), BIN_DARK, cv.clear, 0, radius=fh(10))
    cv.rect(g, fx(left - 8), fy(top - 12), fh(BIN_W + 16), fh(26), BIN_RIM, cv.ink, INK_W * 0.8, radius=fh(10))
    return g


@register("prop", "toon-fridge-light", summary="A fridge door's lit display, that goes dark with the power")
def fridge_light(
    cv: Canvas,
    parent,
    off: float | None = None,
    on: float | None = None,
    *,
    at: tuple[float, float] = FRIDGE_LIGHT_AT,
):
    """The display centred on reference ``at``, lit until ``off`` and from ``on``. Its case stays when it goes out."""
    x, y = _point(at, "fridge light")
    if off is not None and not (checks.number(off) and off >= 0):
        raise ToonDataError(f"a light goes off at a second >= 0, got {off!r}")
    if on is not None and (off is None or not (checks.number(on) and on > off)):
        raise ToonDataError(f"a light comes back after it went off, got {on!r} after {off!r}")
    g = cv.group(parent, cv.uid("fridge-light"))
    cv.rect(g, fx(x - 34), fy(y - 20), fh(68), fh(40), FRIDGE_CASE, cv.ink, FINE_W, radius=fh(7))
    lit = cv.group(g, cv.uid("fridge-lit"))
    _gate(cv, lit, [(0.0, off)] if off is not None else [], on)
    cv.ellipse(lit, fx(x - 70), fy(y - 56), fh(140), fh(112), FRIDGE_GLOW, opacity=0.35)
    cv.rect(lit, fx(x - 28), fy(y - 14), fh(56), fh(28), FRIDGE_GLOW, cv.clear, 0, radius=fh(4))
    return g


@register("location", "toon-hill-window", summary="A window at night on a hill, its street lights go out in a row")
def hill_window(
    cv: Canvas,
    parent,
    out: Sequence[float] = (),
    on: float | None = None,
):
    """The window, wall around it, on the hill at night. Each street light of :data:`STREET`, from the top of the hill
    down, goes out at its second of ``out`` (none listed: it stays on), and all of them and the houses' windows, which
    go when the last light goes, come back at ``on``."""
    if len(out) not in (0, len(STREET)):
        raise ToonDataError(f"the street has {len(STREET)} lights, got {len(out)} times")
    if any(not (checks.number(t) and t >= 0) for t in out) or any(b <= a for a, b in zip(out, out[1:], strict=False)):
        raise ToonDataError(f"the lights go out in order, got {list(out)!r}")
    if on is not None and not (checks.number(on) and on >= 0 and (not out or on > out[-1])):
        raise ToonDataError(f"the lights come back after the last has gone, got {on!r}")
    g = cv.group(parent, cv.uid("hill-window"))
    cv.rect(g, 0, 0, cv.width, cv.height, WALL, cv.clear, 0, radius=0)
    x, y, w, h = GLASS
    cv.rect(g, fx(x - 20), fy(y - 20), fh(w + 40), fh(h + 40), FRAME_WOOD, cv.ink, INK_W, radius=fh(6))
    sky = cv.grad("toon-hill-sky", [(float(o), c) for o, c in SKY], (0, 0, 0, 1))
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), sky, cv.ink, INK_W * 0.7, radius=fh(4))
    glass = cv.group(g, cv.uid("hill"))
    right, foot = x + w, y + h
    floor = f"L {fx(right):.2f} {fy(foot):.2f} L {fx(x):.2f} {fy(foot):.2f} Z"
    cv.path(glass, f"M {fx(x):.2f} {fy(440):.2f} C {fx(200):.2f} {fy(330):.2f} {fx(360):.2f} {fy(400):.2f} "
            f"{fx(right):.2f} {fy(360):.2f} {floor}", FAR_HILL)  # fmt: skip
    cv.path(glass, f"M {fx(x):.2f} {fy(400):.2f} C {fx(200):.2f} {fy(380):.2f} {fx(360):.2f} {fy(520):.2f} "
            f"{fx(right):.2f} {fy(640):.2f} {floor}", HILL)  # fmt: skip
    halo = cv.rgrad("toon-street-halo", [(0.0, GLOW), (0.3, HALO_MID), (1.0, "#000000")])
    spans = [(0.0, out[-1])] if out else []
    for hx, hy in HOUSES:
        cv.rect(glass, fx(hx - 20), fy(hy), fh(40), fh(30), HOUSE_DARK, cv.clear, 0, radius=0)
        lit = cv.rect(glass, fx(hx - 14), fy(hy + 8), fh(10), fh(12), HOUSE_LIT, cv.clear, 0, radius=0)
        _gate(cv, lit, spans, on)
    for k, (lx, ly, near) in enumerate(STREET):
        pole = fh(46 * near)
        cv.rect(glass, fx(lx) - fh(1.5), fy(ly) - pole, fh(3), pole, POLE, cv.clear, 0, radius=0)
        cv.ellipse(glass, fx(lx) - fh(5 * near), fy(ly) - pole - fh(5 * near), fh(10 * near), fh(10 * near), DARK_LAMP,
                   cv.clear, 0)  # fmt: skip
        light = cv.group(glass, cv.uid("street-light"), blend="screen")
        _gate(cv, light, [(0.0, out[k])] if out else [], on)
        r = 52 * near
        cv.ellipse(light, fx(lx) - fh(r), fy(ly) - pole - fh(r), fh(2 * r), fh(2 * r), halo)
        cv.ellipse(light, fx(lx) - fh(6 * near), fy(ly) - pole - fh(6 * near), fh(12 * near), fh(12 * near), LAMP,
                   cv.clear, 0)  # fmt: skip
    return g


def _gate(cv: Canvas, node, lit: list[tuple[float, float]], on: float | None) -> None:
    """Lit over ``lit`` and from ``on`` on; with neither listed, always."""
    if not lit and on is None:
        return
    keys = [(0.0, 1.0 if lit else 0.0)]
    for _, stop in lit:
        keys.append((stop, 0.0))
    if on is not None:
        keys.append((on, 1.0))
    cv.keys(node, "opacity", keys, local=False)
