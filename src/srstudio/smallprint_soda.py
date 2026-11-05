"""Small Print's soda bench: a shaken can acted out on Rafa's worktop, in his clay world (ADR 0240).

What happens inside a shaken can is shown as the thing itself, close up and lit as he is:

- a can with a window cut in its front, so the drink inside shows: its cut face, its top, the air pocket over it, the
  specks on its wall where bubbles start, the bubbles themselves, and the rings a shake sends through the drink;
- a lab shaker that rocks a tray of beer cans, as the Danish trial shook theirs;
- a kitchen scale under a can, its needle dropping by what the can loses;
- his hand, a finger out, tapping a can's side;
- a wind-up kitchen timer, its dial turning as the minutes go;
- foam welling out of an opened can and running down its sides.

Everything is drawn in Rafa's model units (:mod:`srstudio.rafa`): x right, y down, z away from the lens, the worktop's
top at y = -248, a can 48 tall and 12 round, as his own can is (:mod:`srstudio.smallprint_props`). No part carries
lettering or a brand. :mod:`srstudio.smallprint_scene` puts them on the clock; a state is one replacement plate.

Every part here is ``proposed`` until the operator has seen it on a rendered clip.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import checks, clay, smallprint_props
from .clay import Mesh, Model
from .errors import SrstudioError
from .plates import Material

__all__ = [
    "CAN_R",
    "CAN_TALL",
    "TOP",
    "WINDOW",
    "Bubble",
    "Can",
    "Ring",
    "SodaError",
    "bubbles",
    "can",
    "closed_can",
    "drink",
    "finished",
    "foam",
    "hand",
    "materials",
    "needle",
    "rings",
    "scale",
    "shaker",
    "timer",
    "timer_dial",
    "tray",
]

TOP = -248.0  # the worktop's top
CAN_R, CAN_TALL = smallprint_props.CAN_R, smallprint_props.CAN_TALL  # his own can's size
WALL = 0.7  # the can's wall, as thick as clay can be and still read as metal
WINDOW = math.radians(45.0)  # the window's half width, as an angle round the can from the side facing the lens
SIDES = 64  # quads round a can: the window's edges fall on them
DRINKS = {"beer": ("beer", "beertop", "beerwave"), "cola": ("cola", "colatop", "colawave")}


class SodaError(SrstudioError, ValueError):
    """A can, a state or a part the soda bench does not have."""


OWN: dict[str, tuple[str, float, float, bool]] = {  # colour, roughness, metallic, clay
    "beerpaint": ("#C98F2E", 0.3, 0.35, False),
    "beer": ("#D99A2B", 0.22, 0.0, False),
    "beertop": ("#F0C25A", 0.2, 0.0, False),
    "beerwave": ("#F7DA8C", 0.25, 0.0, False),
    "cola": ("#5A2A16", 0.2, 0.0, False),
    "colatop": ("#8A4A2A", 0.2, 0.0, False),
    "colawave": ("#B0703F", 0.25, 0.0, False),
    "fizz": ("#FFF8EA", 0.12, 0.0, False),  # a bubble: opaque, as a moving plate has nothing behind it for glass
    "site": ("#2C1B12", 0.6, 0.0, False),  # a speck on the wall a bubble grows from
    "canedge": ("#DDE4E1", 0.3, 0.55, False),  # the cut edge of the window
    "shakerbody": ("#3B8079", 0.5, 0.0, True),
    "shakerknob": ("#CD5A43", 0.4, 0.0, True),
    "scalebody": ("#E4D6BD", 0.55, 0.0, True),
    "scaletrim": ("#1A504F", 0.45, 0.0, True),
    "scaledial": ("#FFF6E4", 0.5, 0.0, False),
    "tick": ("#1C2A4A", 0.4, 0.0, False),
    "mark": ("#C0392B", 0.45, 0.0, False),
    "timerbody": ("#F1E7D3", 0.5, 0.0, True),
    "timertop": ("#CD5A43", 0.4, 0.0, True),
}


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Rafa's world, Small Print's props (his can's paint, the foam, the tin) and the soda bench's own."""
    clay_map = smallprint_props.materials()["oak"].normal_map
    own = {
        name: Material(
            name,
            colour,
            roughness=rough,
            metallic=metal,
            normal_map=clay_map if clayed else None,
            normal_scale=0.5,
            sheen="#FFE9D2" if clayed else "",
        )
        for name, (colour, rough, metal, clayed) in OWN.items()
    }
    return {**smallprint_props.materials(), **own}


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: his clay on the clay parts, the props' finish on the rest."""
    if mesh.material in OWN:
        return clay.planar(mesh, 70.0) if OWN[mesh.material][3] else mesh
    return smallprint_props.finished(mesh)


def _point(p: Sequence[float], what: str) -> tuple[float, float, float]:
    if len(p) != 3 or not all(checks.number(v) for v in p):
        raise SodaError(f"{what} is somewhere: three numbers, got {p!r}")
    return (float(p[0]), float(p[1]), float(p[2]))


def _quad(m: Model, material: str, corners: Sequence[np.ndarray], normals: Sequence[np.ndarray]) -> None:
    m.surface(material, corners, normals, [(0, 1, 2), (0, 2, 3)])


def _disc(m: Model, material: str, centre: Sequence[float], r: float, sides: int = 48) -> None:
    """A flat disc facing up at ``centre``: a lid or a pan's top, lit as a flat top is (a tube's own cap takes its
    side's normals at the rim and shades dark)."""
    x, y, z = centre
    ring = [(x + r * math.sin(a), y, z - r * math.cos(a)) for a in np.linspace(0.0, math.tau, sides, endpoint=False)]
    tris = [(0, 1 + (i + 1) % sides, 1 + i) for i in range(sides)]
    m.surface(material, [(x, y, z), *ring], [(0.0, -1.0, 0.0)] * (sides + 1), tris)


# -- the can with a window --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Can:
    """A can standing at ``foot`` (its base's middle on the worktop), painted ``paint``, with a window in its front
    from ``low`` to ``high`` of its height (0 the base, 1 the lid) and :data:`WINDOW` either side of the lens."""

    foot: tuple[float, float, float]
    paint: str = "canpaint"
    low: float = 0.12
    high: float = 0.86

    def __post_init__(self) -> None:
        _point(self.foot, "a can")
        if not (checks.number(self.low) and checks.number(self.high) and 0.0 < self.low < self.high < 1.0):
            raise SodaError(f"a can's window is inside its height, 0 < low < high < 1, got {self.low}, {self.high}")
        if self.paint not in ("canpaint", "beerpaint"):
            raise SodaError(f"a can is painted canpaint or beerpaint, got {self.paint!r}")

    @property
    def lid(self) -> float:
        """The lid's height: y of the can's top."""
        return self.foot[1] - CAN_TALL

    @property
    def sill(self) -> float:
        """y of the window's bottom edge."""
        return self.foot[1] - CAN_TALL * self.low

    @property
    def lintel(self) -> float:
        """y of the window's top edge."""
        return self.foot[1] - CAN_TALL * self.high

    @property
    def face(self) -> float:
        """z of the drink's cut face: the chord across the window's inside edges."""
        return self.foot[2] - (CAN_R - WALL) * math.cos(WINDOW)

    @property
    def half(self) -> float:
        """Half the cut face's width."""
        return (CAN_R - WALL) * math.sin(WINDOW) - 0.25

    def on_face(self, x: float, y: float, r: float) -> bool:
        """Whether a bubble of radius ``r`` at ``x, y`` (on the cut face) sits wholly inside the window."""
        cx = self.foot[0]
        return abs(x - cx) + r <= self.half and self.lintel + r <= y <= self.sill - r


def _round(a: float, r: float, cx: float, cz: float) -> np.ndarray:
    return np.array([cx + r * math.sin(a), 0.0, cz - r * math.cos(a)])


def can(m: Model, spec: Can) -> None:
    """The can with its window: the painted wall outside and the tin inside, the cut edge round the window, the lid
    and its rim, the base's rim on the worktop and the inside of the base. The tab and the drink are
    :func:`drink`'s, so they move."""
    cx, foot, cz = spec.foot
    rows = sorted({foot, spec.sill, spec.lintel, spec.lid, foot - CAN_TALL * 0.4, foot - CAN_TALL * 0.6})[::-1]
    angles = np.linspace(-math.pi, math.pi, SIDES + 1)
    for i in range(len(rows) - 1):
        y0, y1 = rows[i], rows[i + 1]  # y0 lower on the can (larger y)
        for j in range(SIDES):
            a0, a1 = float(angles[j]), float(angles[j + 1])
            mid = (a0 + a1) / 2
            if abs(mid) < WINDOW and spec.lintel <= (y0 + y1) / 2 <= spec.sill:
                continue
            for r, material, sign in ((CAN_R, spec.paint, 1.0), (CAN_R - WALL, "tin", -1.0)):
                p = [_round(a0, r, cx, cz), _round(a1, r, cx, cz), _round(a1, r, cx, cz), _round(a0, r, cx, cz)]
                for k, y in enumerate((y0, y0, y1, y1)):
                    p[k][1] = y
                n = [sign * np.array([math.sin(a), 0.0, -math.cos(a)]) for a in (a0, a1, a1, a0)]
                if sign < 0:
                    p, n = p[::-1], n[::-1]
                _quad(m, material, p, n)
    for side in (-1.0, 1.0):  # the window's cut sides
        a = side * WINDOW
        outer, inner = _round(a, CAN_R, cx, cz), _round(a, CAN_R - WALL, cx, cz)
        corners = [outer.copy(), inner.copy(), inner.copy(), outer.copy()]
        for k, y in enumerate((spec.sill, spec.sill, spec.lintel, spec.lintel)):
            corners[k][1] = y
        facing = -side * np.array([math.cos(a), 0.0, math.sin(a)])
        _quad(m, "canedge", corners if side < 0 else corners[::-1], [facing] * 4)
    for y, up in ((spec.sill, -1.0), (spec.lintel, 1.0)):  # its cut bottom and top
        arc = np.linspace(-WINDOW, WINDOW, 17)
        for a0, a1 in zip(arc, arc[1:], strict=False):
            corners = [_round(a0, CAN_R, cx, cz), _round(a1, CAN_R, cx, cz), _round(a1, CAN_R - WALL, cx, cz),
                       _round(a0, CAN_R - WALL, cx, cz)]  # fmt: skip
            for c in corners:
                c[1] = y
            _quad(m, "canedge", corners if up < 0 else corners[::-1], [np.array([0.0, up, 0.0])] * 4)
    lid = spec.lid
    m.cylinder("steel", (cx, lid + 0.9, cz), CAN_R - 0.7, 1.4)
    _disc(m, "steel", (cx, lid + 0.15, cz), CAN_R - 0.6)
    ring = [(cx + (CAN_R - 0.5) * math.sin(a), lid - 0.2, cz - (CAN_R - 0.5) * math.cos(a)) for a in
            np.linspace(0.0, math.tau, 65)]  # fmt: skip
    m.ribbon("steel", ring, 0.9, sides=10)
    base = [(cx + (CAN_R - 1.2) * math.sin(a), foot - 0.6, cz - (CAN_R - 1.2) * math.cos(a)) for a in
            np.linspace(0.0, math.tau, 65)]  # fmt: skip
    m.ribbon("steel", base, 0.8, sides=8)
    m.cylinder("tin", (cx, spec.sill + 0.4, cz), CAN_R - WALL - 0.05, 0.6)  # the floor seen through the window


def drink(m: Model, spec: Can, kind: str, level: float, opened: float = 0.0) -> None:
    """The drink inside ``spec`` filled to ``level`` (0 the window's sill, 1 its lintel), ``kind`` beer or cola: its
    cut face behind the window and its top, the air pocket over it, and the tab, lifted ``opened`` 0 to 1 (1 open,
    the dark mouth showing)."""
    if kind not in DRINKS:
        raise SodaError(f"a drink is one of {tuple(DRINKS)}, got {kind!r}")
    if not (checks.number(level) and 0.0 <= level <= 1.0):
        raise SodaError(f"a drink fills its window 0 to 1, got {level!r}")
    if not (checks.number(opened) and 0.0 <= opened <= 1.0):
        raise SodaError(f"a tab is lifted 0 to 1, got {opened!r}")
    body, top, _ = DRINKS[kind]
    cx, _, cz = spec.foot
    y = spec.sill - (spec.sill - spec.lintel) * level
    z, half = spec.face, spec.half
    corners = [np.array(p, float) for p in ((cx - half, spec.sill, z), (cx + half, spec.sill, z), (cx + half, y, z),
                                             (cx - half, y, z))]  # fmt: skip
    _quad(m, body, corners[::-1], [np.array([0.0, 0.0, -1.0])] * 4)
    ri = CAN_R - WALL - 0.05
    xs = np.linspace(-half, half, 25)  # its top, as much of it as the window shows: from the cut face to the back wall
    verts = [(cx + x, y, z) for x in xs] + [(cx + x, y, cz + math.sqrt(ri * ri - x * x)) for x in xs]
    n = len(xs)
    tris = [t for k in range(n - 1) for t in ((k, n + k, n + k + 1), (k, n + k + 1, k + 1))]
    m.surface(top, verts, [(0.0, -1.0, 0.0)] * len(verts), tris)
    lid = spec.lid
    lift = 70.0 * opened  # degrees the tab's back end rises as it levers the mouth open
    hinge = np.array([cx, lid - 1.2, cz + 1.0])
    a = math.radians(lift)
    end = hinge + 6.5 * np.array([0.0, -math.sin(a), math.cos(a)])
    m.capsule("steel", tuple(hinge), tuple(end), 1.0)
    m.ell("steel", tuple(hinge + np.array([0.0, 0.0, -2.2])), (2.4, 0.5, 2.6))
    if opened >= 0.5:
        m.ell("black", (cx, lid - 0.75, cz - 5.0), (3.2, 0.35, 2.0))


# -- what moves in the drink ------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Bubble:
    """A bubble on the drink's cut face at ``x, y`` of radius ``r``."""

    x: float
    y: float
    r: float

    def __post_init__(self) -> None:
        if not all(checks.number(v) for v in (self.x, self.y, self.r)) or self.r <= 0.0:
            raise SodaError(f"a bubble is somewhere and has a size, got {self}")


def bubbles(m: Model, spec: Can, found: Sequence[Bubble], sites: Sequence[tuple[float, float]] = ()) -> None:
    """``found`` bubbles standing out of the cut face of ``spec``'s drink, and ``sites``, the specks (x, y) on the
    wall they grow from. Each must lie inside the window: a bubble outside it is :class:`SodaError`."""
    z = spec.face
    for x, y in sites:
        if not spec.on_face(x, y, 0.3):
            raise SodaError(f"a speck at {x:.1f}, {y:.1f} is outside the window")
        m.ell("site", (x, y, z - 0.05), (0.32, 0.32, 0.12))
    for b in found:
        if not spec.on_face(b.x, b.y, b.r):
            raise SodaError(f"a bubble at {b.x:.1f}, {b.y:.1f} of radius {b.r:.2f} is outside the window")
        m.ell("fizz", (b.x, b.y, z - b.r * 0.45), (b.r, b.r, b.r * 0.8))


@dataclass(frozen=True)
class Ring:
    """A pressure ring in the drink: centred at ``x, y`` on the cut face, ``r`` across, ``fade`` 0 to 1 of its
    strength (it thins as it fades)."""

    x: float
    y: float
    r: float
    fade: float = 0.0

    def __post_init__(self) -> None:
        if not all(checks.number(v) for v in (self.x, self.y, self.r, self.fade)) or self.r <= 0.0:
            raise SodaError(f"a ring is somewhere and has a size, got {self}")
        if not 0.0 <= self.fade < 1.0:
            raise SodaError(f"a ring fades 0 to under 1, got {self.fade}")


def rings(m: Model, spec: Can, kind: str, waves: Sequence[Ring], level: float) -> None:
    """Pressure rings spreading through the drink's cut face: each drawn only where it is inside the drink, broken
    where it meets the wall, as a wave rebounds there."""
    if kind not in DRINKS:
        raise SodaError(f"a drink is one of {tuple(DRINKS)}, got {kind!r}")
    material = DRINKS[kind][2]
    cx = spec.foot[0]
    top = spec.sill - (spec.sill - spec.lintel) * level
    z = spec.face - 0.15
    for w in waves:
        thick = 0.42 * (1.0 - w.fade) + 0.08
        run: list[tuple[float, float, float]] = []
        for a in np.linspace(0.0, math.tau, 97):
            x, y = w.x + w.r * math.cos(a), w.y + w.r * math.sin(a)
            if abs(x - cx) <= spec.half - thick and top + thick <= y <= spec.sill - thick:
                run.append((x, y, z))
                continue
            if len(run) >= 3:
                m.ribbon(material, run, thick, sides=6)
            run = []
        if len(run) >= 3:
            m.ribbon(material, run, thick, sides=6)


def foam(m: Model, spec: Can, amount: float, runs: Sequence[tuple[float, float]] = ()) -> None:
    """Foam welling out of the opened can's mouth, ``amount`` 0 to 1 of its head, and running down its sides:
    ``runs`` are (angle in degrees round the can from the lens, how far down 0 to 1 of the can's height). A run
    never crosses the window: foam goes down the can's sides and back."""
    if not (checks.number(amount) and 0.0 <= amount <= 1.0):
        raise SodaError(f"a can foams 0 to 1, got {amount!r}")
    cx, foot, cz = spec.foot
    lid = spec.lid
    if amount > 0.0:
        for dx, dz, dy, r in ((0.0, -4.0, 2.5, 6.0), (-5.0, -1.0, 1.5, 5.0), (5.0, 0.0, 1.8, 5.2), (0.0, 3.5, 2.0, 5.5),
                              (-1.5, -3.0, 6.5, 4.4), (2.5, 1.0, 9.5, 3.6)):  # fmt: skip
            k = amount * r
            m.ell("foam", (cx + dx * amount, lid - dy * amount, cz + dz), (k, k * 0.72, k))
    for angle, down in runs:
        if not (checks.number(angle) and checks.number(down) and 0.0 <= down <= 1.0):
            raise SodaError(f"a foam run is an angle and a reach 0 to 1, got {angle!r}, {down!r}")
        if abs(math.radians(angle)) < WINDOW + math.radians(10.0):
            raise SodaError(f"a foam run at {angle} degrees would cross the window")
        if down <= 0.02:
            continue
        a = math.radians(angle)
        r = CAN_R + 0.9
        path = [(cx + r * math.sin(a), lid + CAN_TALL * down * u, cz - r * math.cos(a)) for u in np.linspace(0, 1, 9)]
        m.ribbon("foam", path, [2.2, 2.0, 1.9, 1.8, 1.8, 1.7, 1.7, 1.8, 2.1], sides=10)
        m.ell("foam", path[-1], (2.4, 2.0, 2.4))


# -- the closed cans on the shaker ------------------------------------------------------------------------------------
def closed_can(m: Model, foot: Sequence[float], paint: str = "beerpaint") -> None:
    """A plain closed can at ``foot``: one colour with a pale band, the lid's rim and its tab. No lettering."""
    x, y, z = _point(foot, "a can")
    m.cylinder(paint, (x, y - CAN_TALL / 2, z), CAN_R, CAN_TALL)
    m.cylinder("white", (x, y - CAN_TALL * 0.42, z), CAN_R + 0.2, 7.0)
    m.cylinder("steel", (x, y - CAN_TALL - 0.6, z), CAN_R - 1.0, 1.4)
    _disc(m, "steel", (x, y - CAN_TALL - 0.05, z), CAN_R - 0.05)
    _disc(m, "steel", (x, y - CAN_TALL - 1.35, z), CAN_R - 1.05)
    ring = [(x + (CAN_R - 0.6) * math.sin(a), y - CAN_TALL - 0.5, z - (CAN_R - 0.6) * math.cos(a)) for a in
            np.linspace(0.0, math.tau, 49)]  # fmt: skip
    m.ribbon("steel", ring, 0.75, sides=8)
    m.box("steel", (x, y - CAN_TALL - 1.6, z + 2.5), (5.0, 0.6, 9.0), 0.3)


SHAKER = (150.0, 16.0, 108.0)  # the shaker's base: wide, tall, deep
GRID = (5, 4)  # cans across the tray and back


def shaker(m: Model, middle: Sequence[float], size: tuple[float, float, float] = SHAKER) -> None:
    """The lab shaker's base, ``size`` wide, tall and deep, standing on the worktop with its foot's middle at
    ``middle``: a teal box with a red speed knob and a dark seam where the tray rides."""
    x, y, z = _point(middle, "a shaker")
    w, h, d = size
    m.box("shakerbody", (x, y - h / 2, z), (w, h, d), 3.0)
    m.box("scaletrim", (x, y - h + 0.5, z), (w - 4.0, 1.2, d - 4.0), 0.5)
    knob = min(14.0, w / 4)
    m.ell("shakerknob", (x + w / 2 - knob, y - h / 2, z - d / 2 - 0.6), (h * 0.3, h * 0.3, 1.8))
    m.box("tick", (x + w / 2 - knob, y - h / 2 - h * 0.12, z - d / 2 - 2.3), (0.7, h * 0.3, 0.4))


def tray_feet(middle: Sequence[float], shift: float, grid: tuple[int, int] = GRID,
              size: tuple[float, float, float] = SHAKER) -> list[tuple[float, float, float]]:  # fmt: skip
    """Where each can on the tray stands, the tray moved ``shift`` across from its rest on the shaker at ``middle``:
    ``grid`` cans across and back."""
    x, y, z = _point(middle, "a shaker")
    top = y - size[1] - 2.0
    cols, rows = grid
    gap = CAN_R * 2 + 3.0
    return [(x + shift + (c - (cols - 1) / 2) * gap, top, z + (r - (rows - 1) / 2) * gap) for r in range(rows)
            for c in range(cols)]  # fmt: skip


def tray(m: Model, middle: Sequence[float], shift: float, paint: str = "beerpaint", grid: tuple[int, int] = GRID,
         size: tuple[float, float, float] = SHAKER, cans: bool = True) -> None:  # fmt: skip
    """The shaker's steel tray moved ``shift`` across, what rocks, with ``grid`` closed cans on it (or none, when the
    can on it is drawn on its own)."""
    if not checks.number(shift) or abs(shift) > 8.0:
        raise SodaError(f"the tray rocks at most 8 units either way, got {shift!r}")
    x, y, z = _point(middle, "a shaker")
    w, h, d = size
    m.box("steel", (x + shift, y - h - 1.0, z), (w - 10.0, 2.0, d - 8.0), 0.8)
    for sx in (-1.0, 1.0):
        m.box("steel", (x + shift + sx * (w - 11.0) / 2, y - h - 4.0, z), (1.2, 6.0, d - 8.0), 0.4)
    m.box("steel", (x + shift, y - h - 4.0, z - (d - 9.0) / 2), (w - 10.0, 6.0, 1.2), 0.4)
    for foot in tray_feet(middle, shift, grid, size) if cans else ():
        closed_can(m, foot, paint)


# -- the scale --------------------------------------------------------------------------------------------------------
SCALE_BODY = (31.0, 14.0, 30.0)
DIAL_R = 6.0
FULL = -40.0  # degrees the needle reads with a full can on the pan, from the dial's top, clockwise


def dial_centre(middle: Sequence[float]) -> tuple[float, float, float]:
    """The middle of the scale's dial, on its front."""
    x, y, z = _point(middle, "a scale")
    w, h, d = SCALE_BODY
    return (x, y - h / 2, z - d / 2 - 0.6)


def scale(m: Model, middle: Sequence[float]) -> None:
    """A kitchen scale on the worktop with its foot's middle at ``middle``: a cream body, a steel pan, and on its
    front a round dial with ticks and no numbers, a red mark where the needle stood with the full can on it."""
    x, y, z = _point(middle, "a scale")
    w, h, d = SCALE_BODY
    m.box("scalebody", (x, y - h / 2, z), (w, h, d), 4.0)
    m.box("scaletrim", (x, y - 0.8, z), (w + 0.6, 1.6, d + 0.6), 0.6)
    m.cylinder("steel", (x, y - h - 0.9, z), 14.0, 1.6)
    _disc(m, "steel", (x, y - h - 1.72, z), 14.0)
    m.cylinder("scaletrim", (x, y - h - 0.2, z), 4.0, 1.0)
    cx, cy, cz = dial_centre(middle)
    ring = [(cx + (DIAL_R + 0.8) * math.sin(a), cy - (DIAL_R + 0.8) * math.cos(a), cz) for a in
            np.linspace(0.0, math.tau, 49)]  # fmt: skip
    m.ribbon("scaletrim", ring, 0.9, sides=8)
    rim = np.linspace(0.0, math.tau, 49)[:-1]
    disc = [(cx, cy, cz + 0.2)] + [(cx + DIAL_R * math.sin(a), cy - DIAL_R * math.cos(a), cz + 0.2) for a in rim]
    m.surface("scaledial", disc, [(0.0, 0.0, -1.0)] * len(disc),
              [(0, 1 + i, 1 + (i + 1) % len(rim)) for i in range(len(rim))])  # fmt: skip
    for k in range(-6, 7):
        a = math.radians(k * 10.0)
        r0 = DIAL_R * (0.72 if k % 3 == 0 else 0.82)
        m.rod("tick", (cx + r0 * math.sin(a), cy - r0 * math.cos(a), cz - 0.1),
              (cx + DIAL_R * 0.94 * math.sin(a), cy - DIAL_R * 0.94 * math.cos(a), cz - 0.1),
              0.22 if k % 3 else 0.32)  # fmt: skip
    a = math.radians(FULL)
    m.capsule("mark", (cx + DIAL_R * 1.02 * math.sin(a), cy - DIAL_R * 1.02 * math.cos(a), cz - 0.5),
              (cx + DIAL_R * 1.25 * math.sin(a), cy - DIAL_R * 1.25 * math.cos(a), cz - 0.5), 0.5)  # fmt: skip


def needle(m: Model, middle: Sequence[float], reading: float) -> None:
    """The scale's needle at ``reading`` degrees from the dial's top, clockwise, -60 to 60."""
    if not (checks.number(reading) and -60.0 <= reading <= 60.0):
        raise SodaError(f"the needle reads -60 to 60 degrees, got {reading!r}")
    cx, cy, cz = dial_centre(middle)
    a = math.radians(reading)
    tip = (cx + DIAL_R * 0.86 * math.sin(a), cy - DIAL_R * 0.86 * math.cos(a), cz - 0.6)
    tail = (cx - DIAL_R * 0.2 * math.sin(a), cy + DIAL_R * 0.2 * math.cos(a), cz - 0.6)
    m.capsule("mark", tail, tip, 0.35)
    m.ell("tick", (cx, cy, cz - 0.6), (0.9, 0.9, 0.5))


# -- the timer --------------------------------------------------------------------------------------------------------
TIMER_R, TIMER_TALL = 10.0, 9.0


def timer(m: Model, middle: Sequence[float]) -> None:
    """A wind-up kitchen timer's body on the worktop at ``middle``, its red index mark at the front."""
    x, y, z = _point(middle, "a timer")
    m.cylinder("timerbody", (x, y - TIMER_TALL / 2, z), TIMER_R, TIMER_TALL)
    m.ell("timerbody", (x, y - 0.5, z), (TIMER_R + 0.4, 1.0, TIMER_R + 0.4))
    m.capsule("mark", (x, y - TIMER_TALL - 0.6, z - TIMER_R + 0.2), (x, y - TIMER_TALL + 2.5, z - TIMER_R - 0.2), 0.6)


def timer_dial(m: Model, middle: Sequence[float], turn: float) -> None:
    """The timer's turning top at ``turn`` degrees wound back toward zero: a red dome with ticks round its edge and
    a knob, one long tick for zero."""
    if not checks.number(turn):
        raise SodaError(f"a timer turns by a number of degrees, got {turn!r}")
    x, y, z = _point(middle, "a timer")
    base = y - TIMER_TALL
    m.lid("timertop", (x, base, z), (TIMER_R, 6.0, TIMER_R), 1.0)
    m.ell("timertop", (x, base, z), (TIMER_R + 0.3, 0.8, TIMER_R + 0.3))
    knob_a = math.radians(turn)
    with m.at(x, base - 6.6, z, yaw=-turn):
        m.box("timertop", (0.0, 0.0, 0.0), (12.0, 3.0, 2.4), 1.0)
    for k in range(24):
        a = knob_a + k * math.tau / 24
        long = k == 0
        r0, r1 = TIMER_R * (0.62 if long else 0.78), TIMER_R * 0.96
        h0, h1 = (base - 6.0 * math.sqrt(max(0.0, 1.0 - (r / TIMER_R) ** 2)) for r in (r0, r1))
        m.rod("tick" if not long else "white", (x + r0 * math.sin(a), h0 - 0.2, z - r0 * math.cos(a)),
              (x + r1 * math.sin(a), h1 - 0.2, z - r1 * math.cos(a)), 0.35 if long else 0.22)  # fmt: skip


# -- his hand ---------------------------------------------------------------------------------------------------------
def hand(m: Model, tip: Sequence[float], toward: Sequence[float], wrist_up: float = 0.0) -> None:
    """His frame-left hand, a finger out, its fingertip at ``tip`` pointing along ``toward``: the finger, the knuckles
    of a loose fist, the thumb along it, and his cardigan's cuff and sleeve going back out of the shot. ``wrist_up``
    tips the hand up (degrees) as it draws back between taps."""
    p = np.array(_point(tip, "a fingertip"))
    d = np.array(_point(toward, "a finger's direction"))
    if np.linalg.norm(d) < 1e-6:
        raise SodaError("a finger points somewhere")
    d = d / np.linalg.norm(d)
    side = np.cross(d, np.array([0.0, -1.0, 0.0]))
    side = side / (np.linalg.norm(side) or 1.0)
    up = np.cross(side, d)
    a = math.radians(wrist_up)
    up = up * math.cos(a) - d * math.sin(a)
    knuckle = p - d * 10.5
    m.capsule("flesh", tuple(p - d * 2.0), tuple(knuckle), 2.4)
    m.ell("flesh", tuple(p - d * 1.2 + up * 0.6), (2.3, 2.1, 2.3))
    m.ell("skinlight", tuple(p - d * 1.6 + up * 1.7), (1.3, 0.5, 1.1))  # the nail
    fist = knuckle - d * 5.5 - up * 2.0
    m.ell("flesh", tuple(fist), (7.5, 6.5, 6.5))
    for k in range(3):
        f = knuckle - up * (2.6 + k * 2.6) - d * 1.0
        m.capsule("flesh", tuple(f - d * 4.0), tuple(f + d * 0.4 - up * 0.8), 2.2)
    m.capsule("flesh", tuple(fist + side * 5.0 + up * 1.0), tuple(knuckle + side * 2.6 - d * 1.0 + up * 0.6), 2.4)
    wrist = fist - d * 8.0
    cuff = [tuple(wrist - d * 2.0 + side * 6.5 * math.cos(t) + up * 6.5 * math.sin(t)) for t in
            np.linspace(0.0, math.tau, 25)]  # fmt: skip
    m.ribbon("teallight", cuff, 2.0, sides=8)
    m.sweep("teal", (tuple(wrist - d * 2.0), tuple(wrist - d * 30.0 + up * 6.0), tuple(wrist - d * 70.0 + up * 16.0)),
            (7.6, 9.5, 11.0))  # fmt: skip
