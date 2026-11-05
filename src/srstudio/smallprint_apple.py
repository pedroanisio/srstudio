"""Small Print's apple bench: why a cut apple browns, acted out in clay on Rafa's worktop (ADR 0240).

Two sets, both on his worktop and lit as he is:

* **The cells, close up** (:func:`slab`, :func:`slab_parts`): a block of apple flesh with its red skin under it, its
  front a cross-section of whole cells, each holding its green enzyme apart from its amber polyphenols. A knife slices
  across its top and every cell it passes splits open, spilling both; oxygen drifts down out of the air, and where it
  reaches an open cell the enzyme, the polyphenols and the oxygen meet and the cell goes brown, one shade at a time.
  The cells under the cut, never opened, stay pale. (UW-Madison News, 2008: cutting spills the cells' contents and lets
  the enzyme, polyphenol oxidase, at the polyphenols and the oxygen; the brown is melanins.)
* **Bare against lemon** (:func:`halves`, :func:`halves_parts`): two halves of one apple face up on a board. The bare
  half browns from its rim in; his hand squeezes a lemon half over the other, the drops land on its face and it stays
  pale while an hourglass runs, browning only a little at the end: slowed, not stopped. (Illinois Extension, 2020:
  lemon juice slows browning through its vitamin C.)

Everything is in Rafa's model units (:mod:`srstudio.rafa`): x right, y down, z away from the lens, the worktop's top at
y = -248. A state is one replacement plate, as his own poses are; :mod:`srstudio.smallprint_scene` puts them on the
clock. Every part here is ``proposed`` until the operator has seen it on a rendered clip.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import checks, clay, rafa, smallprint_props
from .clay import Mesh, Model
from .errors import SrstudioError
from .foley import Burst
from .plates import Material

__all__ = [
    "AIR",
    "BOARD",
    "CELLS",
    "COLS",
    "DRIP",
    "LAND",
    "POP",
    "SLICE",
    "SQUEEZE",
    "HALF_R",
    "INTACT",
    "LEVELS",
    "OWN",
    "ROWS",
    "SLAB",
    "TOP",
    "AppleError",
    "HalvesPose",
    "SlabPose",
    "Wisp",
    "bare_centre",
    "brown_level",
    "cell_centres",
    "drop_at",
    "finished",
    "halves",
    "halves_parts",
    "kept_centre",
    "knife_x",
    "lemon_centre",
    "materials",
    "open_times",
    "opened",
    "oxygen",
    "oxygen_at",
    "shade",
    "slab",
    "slab_parts",
]

TOP = -248.0  # the worktop's top
LEVELS = 5  # shades of brown a face goes through, 0 (just cut) to LEVELS (as brown as it gets)
PALE, BROWN = "#F3E7BE", "#8E5A2C"  # an apple's flesh just cut, and browned


class AppleError(SrstudioError, ValueError):
    """A pose, a shade or a state the apple bench does not have."""


def _mix(a: str, b: str, u: float) -> str:
    pa = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * u):02X}" for x, y in zip(pa, pb, strict=True))


def shade(level: int) -> str:
    """The material of flesh browned to ``level``."""
    return f"flesh{level}"


OWN: dict[str, tuple[str, float, float, bool]] = {  # colour, roughness, metallic, clay-finished
    **{shade(k): (_mix(PALE, BROWN, k / LEVELS), 0.5 + 0.03 * k, 0.0, True) for k in range(LEVELS + 1)},
    "cellwall": ("#D8C186", 0.55, 0.0, True),
    "cellsap": ("#F6EED0", 0.22, 0.0, False),
    "enzyme": ("#5E9E46", 0.42, 0.0, True),
    "polyphenol": ("#E4AE3C", 0.3, 0.0, False),
    "melanin": ("#4E2C17", 0.5, 0.0, True),
    "oxygen": ("#5FA9D6", 0.2, 0.0, False),
    "skinred": ("#B8352B", 0.4, 0.0, True),
    "skinpale": ("#E3B26A", 0.45, 0.0, True),
    "blade": ("#C7D0CD", 0.18, 0.75, False),
    "bladeedge": ("#EEF2F0", 0.12, 0.8, False),
    "handle": ("#3B2A20", 0.5, 0.0, True),
    "rivet": ("#C9A44A", 0.25, 0.6, False),
    "core": ("#E9D9A3", 0.5, 0.0, True),
    "pip": ("#3F2618", 0.3, 0.0, False),
    "juice": ("#F7EFB8", 0.04, 0.0, False),
    "lemonflesh": ("#F4E08A", 0.3, 0.0, True),
    "lemonpith": ("#FBF3D6", 0.5, 0.0, True),
    "sand": ("#D9B26E", 0.8, 0.0, True),
    "hourglass": ("#E9F3F1", 0.05, 0.0, False),
    "timerwood": ("#7A5236", 0.5, 0.0, True),
    "cuttingboard": ("#7E9E94", 0.6, 0.0, True),  # sage: pale flesh and brown both read on it
}


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Rafa's world, Small Print's props and the bench's own materials: his clay on the clay parts."""
    clay_map = rafa.MATERIALS["oak"].normal_map
    own = {
        name: Material(
            name,
            colour,
            roughness=rough,
            metallic=metal,
            normal_map=clay_map if clayed else None,
            normal_scale=0.5,
            sheen="#FFE9D2" if clayed else "",
            transmission=0.9 if name == "hourglass" else 0.0,
        )
        for name, (colour, rough, metal, clayed) in OWN.items()
    }
    return {**smallprint_props.materials(), **own}


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: his clay on the clay parts, Small Print's finish on the props'."""
    if mesh.material in OWN:
        return clay.planar(mesh, 70.0) if OWN[mesh.material][3] and mesh.uvs is None else mesh
    return smallprint_props.finished(mesh)


def _level(value: object, what: str) -> int:
    if not (isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= LEVELS):
        raise AppleError(f"{what} is a shade from 0 to {LEVELS}, got {value!r}")
    return value


def brown_level(t: float, start: float, over: float) -> int:
    """The shade a face is at second ``t`` when it starts to brown at ``start`` and takes ``over`` seconds to go all
    the way: 0 before, :data:`LEVELS` after, a step at a time between."""
    if not (checks.number(t) and checks.number(start) and checks.number(over) and over > 0):
        raise AppleError(f"a browning is numbers and takes some time, got {t!r}, {start!r}, {over!r}")
    return int(min(LEVELS, max(0.0, math.floor((t - start) / over * LEVELS + 1e-9))))


# -- the cells, close up ----------------------------------------------------------------------------------------------
SLAB = (0.0, -126.0, 60.0, 30.0, 36.0)  # the block of flesh: x and z of its middle, its width, height and depth
SKIN = 5.0  # the red skin under the flesh
COLS, ROWS = 5, 3  # the cells across the cut top, left to right and front to back
CELLS = COLS * ROWS
PITCH = SLAB[2] / COLS
CELL_R = PITCH * 0.44
AIR = 46.0  # how high over the cut the oxygen drifts
INTACT = -1  # a top cell not yet cut


def _slab_box() -> tuple[float, float, float, float, float, float]:
    """x0, x1, the cut top's y, the skin's foot y, the front z and the back z of the block."""
    x, z, w, h, d = SLAB
    return x - w / 2, x + w / 2, TOP - SKIN - h, TOP, z - d / 2, z + d / 2


def cell_centres() -> tuple[tuple[float, float, float], ...]:
    """The middle of every cell across the cut top, row by row from the front, left to right: on the cut's plane."""
    x0, _, cut, _, front, _ = _slab_box()
    return tuple(
        (x0 + PITCH * (c + 0.5), cut, front + (SLAB[4] / ROWS) * (r + 0.5)) for r in range(ROWS) for c in range(COLS)
    )


@dataclass(frozen=True)
class Wisp:
    """One oxygen molecule, two atoms bonded: where its middle is and its turn in degrees."""

    at: tuple[float, float, float]
    turn: float = 0.0

    def __post_init__(self) -> None:
        if len(self.at) != 3 or not all(checks.number(v) for v in self.at) or not checks.number(self.turn):
            raise AppleError(f"an oxygen molecule is somewhere, turned: three numbers and one, got {self}")


@dataclass(frozen=True)
class SlabPose:
    """What moves on the block: the knife's edge at ``knife`` (x; None when it is not in shot), every top cell's state
    in :func:`cell_centres` order (:data:`INTACT`, or open and browned to a shade 0 to :data:`LEVELS`), the oxygen
    in the air, and ``stir``, the turn of the spilled enzymes' and polyphenols' jiggle."""

    knife: float | None
    cells: tuple[int, ...]
    oxygen: tuple[Wisp, ...] = ()
    stir: float = 0.0

    def __post_init__(self) -> None:
        x0, x1, *_ = _slab_box()
        if self.knife is not None and not (checks.number(self.knife) and x0 - 60.0 <= self.knife <= x1 + 60.0):
            raise AppleError(f"the knife's edge runs from {x0 - 60} to {x1 + 60}, got {self.knife!r}")
        if len(self.cells) != CELLS:
            raise AppleError(f"the cut top has {CELLS} cells, got {len(self.cells)}")
        for k in self.cells:
            if k != INTACT:
                _level(k, "an open cell")
        if not checks.number(self.stir):
            raise AppleError(f"the stir is a number, got {self.stir!r}")
        for wisp in self.oxygen:
            if not isinstance(wisp, Wisp):
                raise AppleError(f"the air holds oxygen molecules, got {wisp!r}")


def knife_x(t: float, start: float, end: float) -> float | None:
    """Where the knife's edge is at second ``t`` when it slices across from ``start`` to ``end``: in from the left,
    out at the right, None when it is not in shot."""
    x0, x1, *_ = _slab_box()
    if not (checks.number(start) and checks.number(end) and end > start):
        raise AppleError(f"a slice takes some time, got {start!r} to {end!r}")
    if t < start - 0.4 or t > end + 0.4:
        return None
    u = (t - start) / (end - start)
    return round(x0 - 8.0 + (x1 + 8.0 - (x0 - 8.0)) * u, 2)


def opened(knife: float | None, passed: bool) -> tuple[bool, ...]:
    """Which top cells the knife has opened: those whose middle its edge has gone past, or all once ``passed``."""
    if passed:
        return (True,) * CELLS
    if knife is None:
        return (False,) * CELLS
    return tuple(x <= knife - CELL_R * 0.4 for x, _, _ in cell_centres())


def _wobble(i: int, stir: float, amount: float) -> tuple[float, float]:
    a = math.tau * (stir + i * 0.37)
    return amount * math.sin(a), amount * math.cos(a * 1.3)


def slab(m: Model) -> None:
    """What stands still: a board on his worktop and on it a block of apple flesh, its red skin under it, its front a
    cross-section of whole cells (the cell walls between them), each cell holding a green enzyme in a sac of its own
    and amber polyphenols in its sap, apart. The cut top's cells are :func:`slab_parts`."""
    x0, x1, cut, foot, front, back = _slab_box()
    x, z, w, h, d = SLAB
    m.box("cuttingboard", (x, TOP - 2.0, z), (w + 34.0, 4.0, d + 26.0), 1.5)
    foot -= 4.0  # on the board
    cut -= 4.0
    m.box("skinred", (x, foot - SKIN / 2, z), (w + 1.6, SKIN, d + 1.6), 2.2)
    m.box("skinpale", (x, foot - SKIN - 0.6, z), (w + 0.8, 1.4, d + 0.8), 0.5)
    m.box("cellwall", (x, (cut + foot - SKIN) / 2, z + 0.5), (w, h, d - 1.0), 0.6)
    rows = 2
    tall = h / rows
    rng = np.random.default_rng(2008)
    for r in range(rows):
        for c in range(COLS):
            cx = x0 + PITCH * (c + 0.5) + (rng.uniform(-0.6, 0.6) if 0 < c < COLS - 1 else 0.0)
            cy = cut + tall * (r + 0.5)
            m.box(shade(0), (cx, cy, front - 0.2), (PITCH - 1.4, tall - 1.4, 2.4), 2.6)
            m.ell("cellsap", (cx + 0.8, cy + 0.6, front - 1.3), (PITCH * 0.3, tall * 0.28, 0.5))
            ex, ey = cx - PITCH * 0.22, cy - tall * 0.2
            m.ell("enzyme", (ex, ey, front - 1.8), (1.7, 1.1, 0.9), rotation=rng.uniform(-30, 30))
            m.ribbon("cellwall", [(ex + 2.0 * math.cos(a), ey + 1.5 * math.sin(a), front - 1.6)
                                  for a in np.linspace(0, math.tau, 13)], 0.25, sides=6)  # fmt: skip  # its sac
            for k in range(2):
                m.ell("polyphenol", (cx + 1.2 + k * 1.6, cy + 1.0 - k * 1.1, front - 1.9), (0.8, 0.8, 0.6))
    # the sides: whole cells, as the front
    for side in (-1.0, 1.0):
        sx = x1 + 0.2 if side > 0 else x0 - 0.2
        for r in range(rows):
            for j in range(ROWS):
                m.box(shade(0), (sx, cut + tall * (r + 0.5), front + (d / ROWS) * (j + 0.5)), (2.4, tall - 1.4,
                      d / ROWS - 1.4), 2.6)  # fmt: skip


def _cell(m: Model, i: int, at: tuple[float, float, float], state: int, stir: float) -> None:
    """One top cell: whole (a domed skin over its sap) or split open, its torn rim, its sap browned to ``state``, its
    enzyme and polyphenols spilled on it, and as it browns the brown pigment where they met."""
    x, y, z = at
    y -= 4.0  # on the board
    if state == INTACT:
        m.lid(shade(0), (x, y, z), (CELL_R, CELL_R * 0.75, CELL_R), 0.5)
        m.ell("enzyme", (x - 1.6, y - CELL_R * 0.55, z - 1.0), (1.3, 0.6, 0.9))  # seen through its skin, in its sac
        return
    torn = [(x + (CELL_R + 0.2) * math.cos(a), y - 0.9 - 0.5 * ((k * 7) % 3), z + (CELL_R + 0.2) * math.sin(a)) for
            k, a in enumerate(np.linspace(0, math.tau, 15))]  # fmt: skip
    m.ribbon(shade(min(state, 2)), torn, 0.75, sides=8)
    m.ell(shade(state), (x, y - 0.4, z), (CELL_R - 0.4, 0.5, CELL_R - 0.4))
    m.ell("cellsap", (x + 1.0, y - 0.9, z + 0.8), (CELL_R * 0.4, 0.25, CELL_R * 0.35))
    for k, a in enumerate((0.4, 2.6, 4.6)):  # shards of its skin, flicked back by the knife
        if (i + k) % 2 == 0:
            m.ell(shade(min(state, 1)), (x + CELL_R * 1.05 * math.cos(a), y - 1.6, z + CELL_R * 0.9 * math.sin(a)),
                  (1.6, 0.4, 1.0), rotation=40.0 * (k - 1), rotation_y=a * 57.3)  # fmt: skip
    dx, dz = _wobble(i, stir, 0.7)
    m.ell("enzyme", (x - 1.4 + dx, y - 2.0, z - 0.6 + dz), (1.9, 1.2, 1.3), rotation=30.0 * dx, rotation_y=37.0 * i)
    pigment = state >= 2
    for k in range(3 - min(2, state // 2)):  # polyphenols used up as the pigment forms
        px, pz = _wobble(i * 3 + k, stir * 1.2, 0.5)
        m.ell("polyphenol", (x + 1.6 + px - k * 1.2, y - 1.6, z + 1.0 + pz + k * 0.9), (0.9, 0.9, 0.9))
    if pigment:
        grow = 0.6 + 0.4 * state / LEVELS
        m.ell("melanin", (x + 0.4, y - 1.4, z + 1.6), (2.0 * grow, 0.9 * grow, 1.6 * grow), rotation_y=23.0 * i)
        m.ell("melanin", (x - 2.4, y - 1.2, z + 2.2), (1.1 * grow, 0.6 * grow, 1.0 * grow))


def oxygen(m: Model, wisp: Wisp) -> None:
    """An oxygen molecule: two blue atoms and their bond."""
    a = math.radians(wisp.turn)
    off = np.array([math.cos(a) * 1.5, math.sin(a) * 0.8, math.sin(a) * 1.2])
    p, q = np.array(wisp.at) - off, np.array(wisp.at) + off
    m.ell("oxygen", tuple(p), (1.45, 1.45, 1.45))
    m.ell("oxygen", tuple(q), (1.45, 1.45, 1.45))
    m.rod("oxygen", tuple(p), tuple(q), 0.7)


def _flat(m: Model, material: str, outline: Sequence[tuple[float, float]], y: float, thick: float) -> None:
    """A flat piece lying level at height ``y``: the convex ``outline`` of (x, z) points given ``thick`` of depth, a fan
    from its middle, with its rim."""
    pts = np.array([(x, y, z) for x, z in outline], float)
    mid = pts.mean(axis=0)
    k = len(pts)
    up, down = np.array([0.0, -thick / 2, 0.0]), np.array([0.0, thick / 2, 0.0])
    verts = np.concatenate([[mid + up], pts + up, [mid + down], pts + down])
    normals = [(0.0, -1.0, 0.0)] * (k + 1) + [(0.0, 1.0, 0.0)] * (k + 1)
    tris = [(0, 1 + i, 1 + (i + 1) % k) for i in range(k)]
    tris += [(k + 1, k + 2 + (i + 1) % k, k + 2 + i) for i in range(k)]
    m.surface(material, verts, normals, tris)
    rim_v: list[np.ndarray] = []
    rim_n: list[np.ndarray] = []
    rim_t: list[tuple[int, int, int]] = []
    for i in range(k):
        a, b = pts[i], pts[(i + 1) % k]
        out = (a + b) / 2 - mid
        out[1] = 0.0
        out = out / (np.linalg.norm(out) or 1.0)
        s0 = len(rim_v)
        rim_v += [a + up, b + up, b + down, a + down]
        rim_n += [out] * 4
        rim_t += [(s0, s0 + 1, s0 + 2), (s0, s0 + 2, s0 + 3)]
    m.surface(material, rim_v, rim_n, rim_t)


BLADE = 13.0  # the blade's width, spine to edge


def _knife(m: Model, edge: float) -> None:
    """A kitchen knife lying flat through the top cells: its edge leading to the right, its point toward the lens, a
    bright bevel along the edge, its handle with three rivets off the back of the block."""
    _, _, cut, _, front, back = _slab_box()
    y = cut - 4.0 - CELL_R * 0.35
    heel, tip = back + 6.0, front - 8.0
    spine = edge - BLADE
    arc = [(edge - BLADE * (1 - math.cos(a)) ** 1.6, tip + (heel - tip) * 0.42 * (1 - math.sin(a))) for a in
           np.linspace(0.0, math.pi / 2, 9)][::-1]  # fmt: skip  # the edge sweeping up to the point
    outline = [(spine, heel), (edge, heel), *[(x, z) for x, z in arc], (spine, tip + 6.0)]
    _flat(m, "blade", outline, y, 0.9)
    bevel = [(edge - 1.6, heel), (edge, heel), *[(x, z) for x, z in arc[:5]], (arc[4][0] - 1.6, arc[4][1])]
    _flat(m, "bladeedge", bevel, y - 0.5, 0.2)
    hz = heel + 15.0
    m.box("blade", (spine + BLADE / 2 - 1.0, y - 0.4, heel + 1.0), (BLADE - 1.0, 2.0, 2.4), 0.8)  # the bolster
    m.box("handle", (spine + BLADE / 2 - 1.0, y - 0.6, hz), (BLADE - 3.0, 4.6, 28.0), 2.0)
    for dz in (-8.0, 0.0, 8.0):
        m.ell("rivet", (spine + BLADE / 2 - 1.0, y - 3.0, hz + dz), (1.1, 0.5, 1.1))


def slab_parts(m: Model, pose: SlabPose) -> None:
    """What moves on the block: the top cells as ``pose`` has them, the knife, the oxygen."""
    for i, (at, state) in enumerate(zip(cell_centres(), pose.cells, strict=True)):
        _cell(m, i, at, state, pose.stir)
    if pose.knife is not None:
        _knife(m, pose.knife)
    for wisp in pose.oxygen:
        oxygen(m, wisp)


def oxygen_at(t: float, seed: int, lands: tuple[float, int] | None = None) -> Wisp:
    """Oxygen molecule ``seed`` at second ``t``: drifting in the air over the block on a slow loop of its own, or, with
    ``lands`` (second, cell), coming down onto that cell's spilled enzyme by that second and staying there."""
    rng = np.random.default_rng(seed)
    x0, x1, cut, _, front, back = _slab_box()
    cut -= 4.0
    cx, cz = rng.uniform(x0 + 6, x1 - 6), rng.uniform(front + 4, back - 4)
    cy = cut - rng.uniform(16.0, AIR)
    a, rate = rng.uniform(0, math.tau), rng.uniform(0.25, 0.45)
    turn = rng.uniform(0, 360) + 140.0 * t
    drift = (cx + 6.0 * math.sin(a + rate * math.tau * t), cy + 4.0 * math.sin(a * 1.7 + rate * 4.1 * t),
             cz + 3.0 * math.cos(a + rate * 3.3 * t))  # fmt: skip
    if lands is None:
        return Wisp(tuple(round(v, 2) for v in drift), round(turn % 360, 1))  # type: ignore[arg-type]
    when, cell = lands
    if not (0 <= cell < CELLS):
        raise AppleError(f"the cut top's cells are 0 to {CELLS - 1}, got {cell!r}")
    lx, ly, lz = cell_centres()[cell]
    target = (lx - 1.4, ly - 4.0 - 4.4, lz - 0.6)
    fall = 0.9
    u = min(1.0, max(0.0, (t - (when - fall)) / fall))
    e = u * u * (3 - 2 * u)
    at = tuple(round(p + (q - p) * e, 2) for p, q in zip(drift if u < 1 else target, target, strict=True))
    return Wisp(at, round((turn * (1 - e)) % 360, 1))  # type: ignore[arg-type]


# -- bare against lemon -----------------------------------------------------------------------------------------------
BOARD = (0.0, -110.0)  # the board's middle on his worktop: x and z
HALF_R = 22.0  # an apple half's radius
RINGS = 3  # bands a half's face browns through, rim first
_BARE = (-10.0, -136.0)  # x, z of the bare half: front left
_KEPT = (12.0, -86.0)  # x, z of the half under lemon: back right, near his hand
_TIMER = (-27.0, -62.0)  # the hourglass, back left
_LEMON_DOWN = (32.0, -150.0)  # where the squeezed lemon is put down: front right
GLASS_TALL, GLASS_R = 30.0, 8.0


def bare_centre() -> tuple[float, float, float]:
    """The middle of the bare half's face."""
    return (_BARE[0], TOP - 4.0 - HALF_R * 0.62, _BARE[1])


def kept_centre() -> tuple[float, float, float]:
    """The middle of the face kept under lemon juice."""
    return (_KEPT[0], TOP - 4.0 - HALF_R * 0.62, _KEPT[1])


LEMON_UP = 21.0  # how far over the kept face his hand holds the lemon half
LEMON_BACK = 16.0  # and how far behind its middle, so the lens sees the face under it


def lemon_centre(squeeze: float) -> tuple[float, float, float]:
    """The middle of the lemon half's cut face, held over the kept half and pressed lower as he squeezes."""
    x, y, z = kept_centre()
    return (x + 1.0, y - LEMON_UP + 3.0 * squeeze, z + LEMON_BACK)


@dataclass(frozen=True)
class HalvesPose:
    """Bare against lemon: each half's face browned ring by ring, rim first (shades 0 to :data:`LEVELS`), the lemon's
    ``squeeze`` (0 to 1; None once he has put it down), the drops of juice falling (each from 0 at the lemon to 1 on
    the face), the juice landed on the kept face (0 to 1, as much as there will be) and the sand left in the
    hourglass's top (1 full to 0)."""

    bare: tuple[int, ...]
    kept: tuple[int, ...]
    squeeze: float | None = None
    drops: tuple[float, ...] = ()
    wet: float = 0.0
    sand: float = 1.0

    def __post_init__(self) -> None:
        for name in ("bare", "kept"):
            rings = getattr(self, name)
            if len(rings) != RINGS:
                raise AppleError(f"a face browns through {RINGS} rings, got {len(rings)} on the {name} half")
            for k in rings:
                _level(k, f"the {name} half's ring")
            if list(rings) != sorted(rings, reverse=True):
                raise AppleError(f"a face browns from its rim in: its rings' shades fall inward, got {rings}")
        if self.squeeze is not None and not (checks.number(self.squeeze) and 0.0 <= self.squeeze <= 1.0):
            raise AppleError(f"a squeeze is 0 to 1, got {self.squeeze!r}")
        if self.drops and self.squeeze is None:
            raise AppleError("juice falls only from a lemon in his hand")
        for d in self.drops:
            if not (checks.number(d) and 0.0 <= d <= 1.0):
                raise AppleError(f"a drop falls 0 (at the lemon) to 1 (on the face), got {d!r}")
        for name in ("wet", "sand"):
            value = getattr(self, name)
            if not (checks.number(value) and 0.0 <= value <= 1.0):
                raise AppleError(f"the {name} is 0 to 1, got {value!r}")


def _face(m: Model, centre: tuple[float, float, float], rings: Sequence[int], seed: int) -> None:
    """A half face up: red skin round its curve, a thin pale rim of skin, the flesh in rings browned rim first, the
    core's five-pointed star with its pips."""
    x, y, z = centre
    foot = TOP - 4.0
    m.lid("skinred", (x, y, z), (HALF_R, foot - y, HALF_R), 0.5, lower=True)
    m.ribbon("skinred", [(x + HALF_R * 0.985 * math.cos(a), y - 0.2, z + HALF_R * 0.985 * math.sin(a)) for a in
                         np.linspace(0, math.tau, 49)], 0.9, sides=8)  # fmt: skip
    outer = HALF_R - 1.0
    for k, level in enumerate(rings):
        r = outer * (1.0 - k / RINGS)
        m.ell(shade(level), (x, y - 0.25 - 0.06 * k, z), (r, 0.5, r))
    m.ell("core", (x, y - 0.6, z), (outer * 0.3, 0.45, outer * 0.3))
    for k in range(5):
        a = math.tau * k / 5 + 0.3 * seed
        tip = (x + outer * 0.26 * math.cos(a), y - 0.85, z + outer * 0.26 * math.sin(a))
        m.ell("pip", tip, (1.8, 0.5, 1.0), rotation_y=-math.degrees(a))
        m.ribbon("cellwall", [(x, y - 0.8, z), tip], 0.22, sides=5)


def _lemon(m: Model, squeeze: float) -> None:
    """The lemon half in his hand, cut face down over the kept half, flattening as he squeezes."""
    cx, cy, cz = lemon_centre(squeeze)
    flat = 1.0 - 0.28 * squeeze
    m.lid("lemon", (cx, cy, cz), (9.0 * (1 + 0.08 * squeeze), 8.0 * flat, 9.0), 0.5)
    m.ell("lemonpith", (cx, cy + 0.3, cz), (8.6, 0.6, 8.6))
    for k in range(8):
        a = math.tau * k / 8
        m.ell("lemonflesh", (cx + 4.4 * math.cos(a), cy + 0.7, cz + 4.4 * math.sin(a)), (3.0, 0.5, 1.4),
              rotation_y=-math.degrees(a))  # fmt: skip
    rafa.reach(m, (cx + 22.0, cy - 10.0, cz + 18.0))
    rafa.hold(m, cx + 4.0, cy - 9.0 - 2.0 * squeeze, cz + 2.0)


def drop_at(fall: float) -> tuple[float, float, float]:
    """Where a drop of juice is ``fall`` of the way (0 to 1) from the lemon's face to the kept half's."""
    lx, ly, lz = lemon_centre(1.0)
    x, y, z = kept_centre()
    return (lx + (x - lx) * fall, ly + 1.6 + (y - 1.2 - ly - 1.6) * fall * fall, lz + (z - lz) * fall)


def _juice(m: Model, wet: float) -> None:
    """The juice on the kept face: a shining film spreading from where it landed, and its beads."""
    if wet <= 0.0:
        return
    x, y, z = kept_centre()
    r = (HALF_R - 2.0) * (0.35 + 0.65 * wet)
    m.ell("juice", (x + 1.0, y - 0.95, z - 0.5), (r, 0.3, r * 0.95))
    for k in range(int(round(6 * wet))):
        a = 1.1 + k * 1.9
        m.ell("juice", (x + 1.0 + r * 0.6 * math.cos(a), y - 1.3, z + r * 0.55 * math.sin(a)), (1.2, 0.7, 1.2))


def halves(m: Model) -> None:
    """What stands still: a board on his worktop and an hourglass's wooden ends and posts. The halves, the lemon and
    the sand are :func:`halves_parts`."""
    m.box("cuttingboard", (BOARD[0], TOP - 2.0, BOARD[1]), (96.0, 4.0, 104.0), 1.5)
    tx, tz = _TIMER
    foot = TOP - 4.0
    for y in (foot - 1.5, foot - GLASS_TALL - 4.5):
        m.cylinder("timerwood", (tx, y, tz), GLASS_R + 3.0, 3.0)
    for a in (0.6, 2.7, 4.8):
        px, pz = tx + (GLASS_R + 1.6) * math.cos(a), tz + (GLASS_R + 1.6) * math.sin(a)
        m.rod("timerwood", (px, foot - 3.0, pz), (px, foot - GLASS_TALL - 3.0, pz), 0.9)


def _hourglass(m: Model, sand: float) -> None:
    """The hourglass's two bulbs and the sand: ``sand`` of it left in the top, the rest heaped in the bottom, a thread
    falling between while any is left."""
    tx, tz = _TIMER
    foot = TOP - 7.0
    mid = foot - GLASS_TALL / 2
    half = GLASS_TALL / 2
    m.ell("hourglass", (tx, mid + half / 2, tz), (GLASS_R, half / 2 + 0.6, GLASS_R))
    m.ell("hourglass", (tx, mid - half / 2, tz), (GLASS_R, half / 2 + 0.6, GLASS_R))
    if sand > 0.02:
        top = half * 0.8 * sand
        m.lid("sand", (tx, mid - 1.0, tz), (GLASS_R * (0.45 + 0.4 * sand), top, GLASS_R * (0.45 + 0.4 * sand)), 0.5)
        m.rod("sand", (tx, mid - 1.0, tz), (tx, foot - 0.5, tz), 0.35)
    heap = half * 0.75 * (1.0 - sand) + 0.6
    m.lid("sand", (tx, foot, tz), (GLASS_R * 0.85, heap, GLASS_R * 0.85), 0.5)


def halves_parts(m: Model, pose: HalvesPose) -> None:
    """What moves: the two halves browning, the lemon in his hand and its drops, the juice on the kept face, the
    hourglass's sand."""
    _face(m, bare_centre(), pose.bare, 0)
    _face(m, kept_centre(), pose.kept, 1)
    _juice(m, pose.wet)
    if pose.squeeze is not None:
        _lemon(m, pose.squeeze)
        for fall in pose.drops:
            m.ell("juice", drop_at(fall), (1.0, 1.4, 1.0))
    else:  # squeezed and put down on the board, face up, by the bare half
        x, z = _LEMON_DOWN
        m.lid("lemon", (x, TOP - 11.0, z), (8.0, 7.0, 8.0), 0.5, lower=True)
        m.ell("lemonpith", (x, TOP - 11.2, z), (7.6, 0.5, 7.6))
        for k in range(8):
            a = math.tau * k / 8
            m.ell("lemonflesh", (x + 4.2 * math.cos(a), TOP - 11.6, z + 4.2 * math.sin(a)), (2.8, 0.4, 1.3),
                  rotation_y=-math.degrees(a))  # fmt: skip
    _hourglass(m, pose.sand)


# -- the bench's sounds -----------------------------------------------------------------------------------------------
SLICE = Burst(0.9, 3200.0, attack=0.06, decay=0.7, tone_hz=260.0, tone_end_hz=200.0, tone=0.12, flutter_hz=43.0)  # wet
POP = Burst(0.05, 2600.0, attack=0.001, decay=0.2, tone_hz=900.0, tone_end_hz=520.0, tone=0.6)  # a cell splitting
LAND = Burst(0.06, 5200.0, attack=0.001, decay=0.2, tone_hz=2300.0, tone_end_hz=2700.0, tone=0.5)  # oxygen meets enzyme
SQUEEZE = Burst(0.45, 1800.0, attack=0.06, decay=0.5, tone_hz=180.0, tone_end_hz=140.0, tone=0.2, flutter_hz=29.0)
DRIP = Burst(0.07, 1500.0, attack=0.001, decay=0.25, tone_hz=1300.0, tone_end_hz=700.0, tone=0.7)  # juice on the face


def open_times(start: float, end: float) -> list[float]:
    """The seconds the knife, slicing across from ``start`` to ``end``, opens each column of cells: one pop each, left
    to right, on the frame :func:`opened` first shows it open."""
    if not (checks.number(start) and checks.number(end) and end > start):
        raise AppleError(f"a slice takes some time, got {start!r} to {end!r}")
    x0, x1, *_ = _slab_box()
    lo, hi = x0 - 8.0, x1 + 8.0
    out = []
    for c in range(COLS):
        x = x0 + PITCH * (c + 0.5) + CELL_R * 0.4  # where the edge is when this column opens
        out.append(round(start + (x - lo) / (hi - lo) * (end - start), 6))
    return out
