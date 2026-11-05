"""Small Print's lab bench: the things an explainer acts out on Rafa's worktop, in his clay world (ADR 0240).

A finding is shown as the thing itself, close up and lit as he is: a goldfish with fins, eyes and scales that swims by
bending its body; a lab tank with a lever, a feeder and a twenty-four-hour timer dial; a calendar whose pages
tear off. Everything is drawn in Rafa's model units (:mod:`srstudio.rafa`): x right, y down, z away from the lens, the
worktop's top at y = -248. A state is one replacement plate, as his own poses are; :mod:`srstudio.smallprint_scene`
puts them on the clock.

Every part here is ``proposed`` until the operator has seen it on a rendered clip.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache, lru_cache

import numpy as np

from . import checks, clay, plates, rafa, smallprint_props
from .clay import Mesh, Model
from .errors import SrstudioError
from .plates import Line, Material, Print, Texture

__all__ = [
    "BENCH",
    "CALENDAR",
    "DIAL_HOURS",
    "FED_HOUR",
    "GLYPH",
    "HAND_TIP",
    "MARKS",
    "NUMBER_AT",
    "NUMBER_SIZE",
    "PAGE",
    "PRESS",
    "PUSH",
    "TANK",
    "TIP",
    "WEDGE",
    "Box",
    "FishPose",
    "LabError",
    "Mark",
    "Rig",
    "bench",
    "calendar_pages",
    "calendar_stand",
    "chute_mouth",
    "dial_centre",
    "dial_print",
    "finished",
    "goldfish",
    "keyed",
    "lamp",
    "lever",
    "lever_tip",
    "materials",
    "nose_to_middle",
    "numbers_inside",
    "page_material",
    "page_name",
    "page_print",
    "parts",
    "pellet_at",
    "pellets",
    "scales",
    "swim",
    "swim_room",
    "tank",
]

TOP = -248.0  # the worktop's top
BENCH = (0.0, TOP, -197.0)  # where the tank stands on his worktop: its foot's middle
TANK = (84.0, 54.0, 56.0)  # inside width, height and depth of the lab tank
WATER_TOP = 0.86  # the share of the tank's height the water fills
DIAL_HOURS = 24
FED_HOUR = 0  # the hour of the day the feeder gives food: the top of the dial


class LabError(SrstudioError, ValueError):
    """A pose, a state or a page the lab bench does not have."""


def scales(size: int = 256, rows: int = 8) -> np.ndarray:
    """A repeating height field of fish scales: overlapping rounded rows, each row offset half a scale, each scale
    rising to its free edge."""
    y, x = np.mgrid[0:size, 0:size] / size * rows
    field = np.zeros((size, size))
    for shift in (0.0, 0.5):
        u = (x + shift * ((np.floor(y) % 2) * 2 - 1) * 0.5) % 1.0 - 0.5
        v = y % 1.0
        r = np.sqrt(u * u + (v - 0.15) ** 2)
        field = np.maximum(field, np.clip(1.0 - r / 0.62, 0.0, 1.0) ** 0.6 * (0.4 + 0.6 * v))
    return field / float(np.max(field))


_SCALES = Texture(clay.normal_tile(scales(), 1.6))
OWN: dict[str, tuple[str, float, float]] = {  # colour, roughness, transmission
    "goldfish": ("#E8722A", 0.34, 0.0),
    "goldbelly": ("#F4A55C", 0.4, 0.0),
    "goldfin": ("#F6A45A", 0.32, 0.0),
    "finray": ("#D9662A", 0.4, 0.0),
    "fisheye": ("#FFF6E4", 0.2, 0.0),
    "fishpupil": ("#141A1C", 0.08, 0.0),
    "fishlip": ("#C9562A", 0.4, 0.0),
    "fishgill": ("#C85E28", 0.45, 0.0),
    "tankglass": ("#E6F4F2", 0.03, 0.94),
    "tankwater": ("#BFE3E6", 0.06, 0.9),
    "tankback": ("#8FC2BA", 0.7, 0.0),
    "tankside": ("#3B8079", 0.5, 0.0),
    "tankframe": ("#1A504F", 0.45, 0.0),
    "gravel": ("#D8C7A6", 0.75, 0.0),
    "gravelred": ("#B66C4E", 0.75, 0.0),
    "gravelsage": ("#719889", 0.75, 0.0),
    "pellet": ("#8A4A22", 0.55, 0.0),
    "lever": ("#CD5A43", 0.35, 0.0),
    "steelbar": ("#AAB8B4", 0.3, 0.0),
    "feeder": ("#E4D6BD", 0.55, 0.0),
    "feederdark": ("#725440", 0.55, 0.0),
    "dialrim": ("#1A504F", 0.4, 0.0),
    "dialhand": ("#1C2A4A", 0.4, 0.0),
    "fedhour": ("#C0392B", 0.45, 0.0),
    "calendar": ("#FFF6E4", 0.75, 0.0),
    "calendarback": ("#286A67", 0.55, 0.0),
    "bubble": ("#E8F6F4", 0.05, 0.0),  # opaque: a moving plate has nothing behind it for glass to show
}
_CLAYED = {"goldfin", "finray", "fishlip", "fishgill", "feeder", "feederdark", "dialrim", "tankframe", "lever",
           "gravel", "gravelred", "gravelsage", "pellet", "calendarback", "tankside"}  # fmt: skip


@dataclass(frozen=True)
class FishPose:
    """Where the goldfish is and what his body is doing: ``at`` his middle, ``heading`` degrees from frame right
    toward the back of the tank, ``pitch`` degrees nose up, ``phase`` the swim cycle in turns, ``beat`` how hard his
    tail beats (0 still, 1 a full stroke), ``mouth`` open 0 to 1 and ``fins`` the pectoral fins' spread 0 to 1."""

    at: tuple[float, float, float]
    heading: float = 0.0
    pitch: float = 0.0
    phase: float = 0.0
    beat: float = 0.6
    mouth: float = 0.2
    fins: float = 0.5

    def __post_init__(self) -> None:
        if len(self.at) != 3 or not all(checks.number(v) for v in self.at):
            raise LabError(f"a fish is somewhere: three numbers, got {self.at!r}")
        for name in ("heading", "pitch", "phase"):
            if not checks.number(getattr(self, name)):
                raise LabError(f"a fish's {name} is a number, got {getattr(self, name)!r}")
        for name in ("beat", "mouth", "fins"):
            value = getattr(self, name)
            if not (checks.number(value) and 0.0 <= value <= 1.0):
                raise LabError(f"a fish's {name} is from 0 to 1, got {value!r}")
        if abs(self.pitch) > 60.0:
            raise LabError(f"a goldfish tips his nose at most 60 degrees, got {self.pitch!r}")


@dataclass(frozen=True)
class Rig:
    """The lab tank's moving parts: the lever's swing in degrees (0 at rest, toward the right wall when pressed), the
    timer's hand in hours (0 to 24, the fed hour at the top), the pellets in the water (x, y, z each) and the bubbles'
    rise in turns. How full the hopper is stands still, on :func:`bench`."""

    lever: float = 0.0
    hour: float = 6.0
    pellets: tuple[tuple[float, float, float], ...] = ()
    bubbles: float = 0.0

    def __post_init__(self) -> None:
        if not (checks.number(self.lever) and 0.0 <= self.lever <= 30.0):
            raise LabError(f"the lever swings 0 to 30 degrees, got {self.lever!r}")
        if not (checks.number(self.hour) and 0.0 <= self.hour <= DIAL_HOURS):  # a day on: wrap it with % 24
            raise LabError(f"the timer reads 0 to {DIAL_HOURS} hours, got {self.hour!r}")
        if not checks.number(self.bubbles):
            raise LabError(f"the bubbles' rise is a number, got {self.bubbles!r}")
        for p in self.pellets:
            if len(p) != 3 or not all(checks.number(v) for v in p):
                raise LabError(f"a pellet is somewhere: three numbers, got {p!r}")


def _material(name: str, colour: str, rough: float, through: float) -> Material:
    if name in ("goldfish", "goldbelly"):
        return Material(name, colour, roughness=rough, normal_map=_SCALES, normal_scale=0.7, sheen="#FFD9A8")
    clayed = name in _CLAYED
    return Material(
        name,
        colour,
        roughness=rough,
        normal_map=rafa.MATERIALS["oak"].normal_map if clayed else None,
        normal_scale=0.45,
        sheen="#FFE9D2" if clayed else "",
        transmission=through,
        ior=1.33 if name == "tankwater" else 1.5,
    )


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Rafa's world, Small Print's props and the bench's own materials, the timer's printed face among them."""
    own = {name: _material(name, *spec) for name, spec in OWN.items()}
    face = Material("dialface", "#FFFFFF", roughness=0.6, print=dial_print())
    return {**smallprint_props.materials(), **own, "dialface": face}


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: scales on the fish, his clay on the clay parts."""
    if mesh.material in ("goldfish", "goldbelly"):
        return clay.planar(mesh, 9.0)
    if mesh.material in OWN:
        return clay.planar(mesh, 70.0) if mesh.material in _CLAYED else mesh
    return smallprint_props.finished(mesh)


# -- the goldfish -----------------------------------------------------------------------------------------------------
LENGTH, DEPTH, WIDTH = 30.0, 9.0, 5.4  # his body from nose to the root of the tail, its half height and half width
TAIL = 15.0  # how far his tail fin reaches behind the body
SIZE = 0.8  # the whole fish drawn this much smaller: 36 units nose to tail, room to turn in the lab tank


def _girth(u: float) -> float:
    """His body's section at ``u`` along it, nose 0 to tail root 1: blunt at the nose, deepest a third along, a narrow
    root for the tail."""
    return max(0.16, (u**0.42) * (1.0 - u) ** 0.62 / 0.62)


def _bend(u: float, pose: FishPose) -> float:
    """How far his body swings sideways at ``u``: a wave running from his head to his tail."""
    return pose.beat * 2.6 * u * u * math.sin(math.tau * pose.phase - 2.4 * u)


def _bend_slope(pose: FishPose) -> float:
    du = 1e-3
    return (_bend(1.0, pose) - _bend(1.0 - du, pose)) / (du * LENGTH)


def _fin(m: Model, material: str, root: np.ndarray, e1: np.ndarray, e2: np.ndarray, outline, thick: float) -> None:
    """A thin fin: ``outline`` (points in the plane of ``e1`` and ``e2`` about ``root``) given a little thickness, a
    fan from its first point."""
    e1, e2 = np.asarray(e1, float), np.asarray(e2, float)
    n = np.cross(e1, e2)
    n = n / np.linalg.norm(n)
    flat = np.array([root + p * e1 + q * e2 for p, q in outline])
    k = len(flat)
    verts = np.concatenate([flat + n * thick / 2, flat - n * thick / 2])
    normals = np.concatenate([np.tile(n, (k, 1)), np.tile(-n, (k, 1))])
    tris = [(0, i, i + 1) for i in range(1, k - 1)] + [(k, k + i + 1, k + i) for i in range(1, k - 1)]
    m.surface(material, verts, normals, tris)
    centre = flat.mean(axis=0)
    rim_v: list[np.ndarray] = []
    rim_n: list[np.ndarray] = []
    rim_t: list[tuple[int, int, int]] = []
    for i in range(k):
        a, b = flat[i], flat[(i + 1) % k]
        out = (a + b) / 2 - centre
        out = out - n * float(out @ n)
        out = out / (np.linalg.norm(out) or 1.0)
        s = len(rim_v)
        rim_v += [a + n * thick / 2, b + n * thick / 2, b - n * thick / 2, a - n * thick / 2]
        rim_n += [out] * 4
        rim_t += [(s, s + 1, s + 2), (s, s + 2, s + 3)]
    m.surface(material, rim_v, rim_n, rim_t)


def _body(m: Model, pose: FishPose) -> None:
    """His body along x (nose at +x), y down, z his side: a loft whose rings swing with the swim, his belly paler."""
    us = np.linspace(0.0, 1.0, 40)
    xs = LENGTH / 2 - us * LENGTH
    sides = 36
    around = np.linspace(0.0, math.tau, sides, endpoint=False)

    def ring(x: float):
        u = (LENGTH / 2 - x) / LENGTH
        g = _girth(u)
        arch = -1.4 * math.sin(math.pi * u)  # his back arches over the middle
        return (_bend(u, pose) + WIDTH * g * np.sin(around), arch - DEPTH * g * np.cos(around))

    def assign(centroid, normal, row, column) -> str:
        return "goldbelly" if normal[1] > 0.35 else "goldfish"

    m.loft(xs, ring, assign)


def _eyes(m: Model, pose: FishPose) -> None:
    u = 0.16
    x, g = LENGTH / 2 - u * LENGTH, _girth(u)
    for side in (-1.0, 1.0):
        z = _bend(u, pose) + side * WIDTH * g * 0.86
        m.ell("fisheye", (x, -DEPTH * g * 0.2, z), (2.6, 2.6, 1.6))
        m.ell("fishpupil", (x + 0.25, -DEPTH * g * 0.2, z + side * 1.15), (1.55, 1.6, 0.7))
        gill = [(x - 3.6 + 1.6 * math.sin(a), -DEPTH * g * 0.55 * math.cos(a) + 0.6, z - side * 0.55) for a in
                np.linspace(-1.2, 1.2, 9)]  # fmt: skip
        m.ribbon("fishgill", gill, 0.42, sides=8)


def _mouth(m: Model, pose: FishPose) -> None:
    x = LENGTH / 2 + 0.2
    z = _bend(0.0, pose)
    gape = 0.6 + 1.3 * pose.mouth
    m.ell("fishlip", (x - 0.3, 0.6 - gape * 0.45, z), (1.5, 0.9, 2.1))
    m.ell("fishlip", (x - 0.4, 0.6 + gape * 0.45, z), (1.4, 0.9, 1.9))
    m.ell("fishpupil", (x - 0.6, 0.6, z), (0.9, gape * 0.55, 1.4))


def _tail(m: Model, pose: FishPose) -> None:
    """The forked tail fin, swung with the body's last stretch and lagging behind it."""
    root = np.array([-LENGTH / 2 + 0.6, -0.4, _bend(1.0, pose)])
    swing = math.atan(_bend_slope(pose)) + pose.beat * 0.45 * math.sin(math.tau * pose.phase - 3.1)
    back = np.array([-math.cos(swing), 0.0, -math.sin(swing)])
    up = np.array([0.0, -1.0, 0.0])
    lobes = [(0.0, -1.4), (TAIL * 0.55, -6.5), (TAIL, -10.5), (TAIL * 0.86, -4.0), (TAIL * 0.6, 0.0),
             (TAIL * 0.86, 4.2), (TAIL * 0.98, 9.8), (TAIL * 0.5, 6.0), (0.0, 1.4)]  # fmt: skip
    _fin(m, "goldfin", root, back, up, [(p, -q) for p, q in lobes], 0.45)
    for tip in ((TAIL * 0.92, -9.0), (TAIL * 0.8, -4.6), (TAIL * 0.82, 4.4), (TAIL * 0.9, 8.6)):
        ray = [root + back * (tip[0] * f) + up * (-tip[1] * f) for f in np.linspace(0.05, 0.95, 6)]
        m.ribbon("finray", ray, 0.18, sides=6)


def _fins(m: Model, pose: FishPose) -> None:
    """The dorsal fin along his back, the pectoral fins behind the gills, the pelvic and the anal fin underneath."""
    up = np.array([0.0, -1.0, 0.0])
    fwd = np.array([1.0, 0.0, 0.0])
    u0 = 0.32
    root = np.array([LENGTH / 2 - u0 * LENGTH, -DEPTH * _girth(u0) - 1.0, _bend(u0, pose)])
    span = LENGTH * 0.42
    _fin(m, "goldfin", root, -fwd, up, [(0.0, 0.0), (span * 0.12, 6.2), (span * 0.5, 5.4), (span, 1.2), (span, -1.0),
                                        (0.0, -1.2)], 0.4)  # fmt: skip
    flap = 0.5 + 0.5 * pose.fins
    for side in (-1.0, 1.0):
        u = 0.36
        base = np.array([LENGTH / 2 - u * LENGTH, DEPTH * 0.35, _bend(u, pose) + side * WIDTH * _girth(u) * 0.8])
        out = np.array([-math.cos(0.9 * flap), 0.25, side * math.sin(0.9 * flap)])
        _fin(m, "goldfin", base, out / np.linalg.norm(out), fwd * 0.3 + up * 0.95,
             [(0.0, -1.0), (5.5, -2.2), (7.0, 0.2), (5.0, 2.0), (0.0, 1.0)], 0.3)  # fmt: skip
        u = 0.58
        base = np.array([LENGTH / 2 - u * LENGTH, DEPTH * _girth(u) * 0.9, _bend(u, pose) + side * 1.6])
        down = np.array([-0.55, 0.8, side * 0.25])
        _fin(m, "goldfin", base, down / np.linalg.norm(down), -fwd,
             [(0.0, -1.5), (5.0, -0.5), (5.6, 1.4), (0.0, 1.5)], 0.3)  # fmt: skip
    u = 0.8
    base = np.array([LENGTH / 2 - u * LENGTH, DEPTH * _girth(u) * 0.95, _bend(u, pose)])
    _fin(m, "goldfin", base, -up, -fwd, [(0.0, -2.0), (4.8, 0.0), (4.0, 2.6), (0.0, 2.2)], 0.3)


def _spin(heading: float, pitch: float) -> np.ndarray:
    """His local frame (x his nose, y down, z his side) turned ``pitch`` nose up, then ``heading`` toward +z."""
    p, h = math.radians(pitch), math.radians(heading)
    tip = np.array([[math.cos(p), math.sin(p), 0.0], [-math.sin(p), math.cos(p), 0.0], [0.0, 0.0, 1.0]])
    turn = np.array([[math.cos(h), 0.0, -math.sin(h)], [0.0, 1.0, 0.0], [math.sin(h), 0.0, math.cos(h)]])
    return turn @ tip


def goldfish(m: Model, pose: FishPose) -> None:
    """A goldfish at ``pose``: a deep orange body that bends as he swims, a paler belly, scales, big eyes with a gill
    line behind them, a mouth that opens, a dorsal fin, two pectoral and two pelvic fins, an anal fin and a forked tail
    with rays that lags his body's swing. No one fish's likeness."""
    sub = Model()
    _body(sub, pose)
    _eyes(sub, pose)
    _mouth(sub, pose)
    _tail(sub, pose)
    _fins(sub, pose)
    spin = _spin(pose.heading, pose.pitch)
    at = np.array(pose.at, float)
    for mesh in sub.meshes():
        m.surface(mesh.material, SIZE * mesh.vertices @ spin.T + at, mesh.normals @ spin.T, mesh.triangles, mesh.uvs)


# -- the lab tank -----------------------------------------------------------------------------------------------------
# Only the front is glass. A transmissive surface the path tracer sees the plate's clear background through comes out
# opaque, so everything behind the glass is closed: teal sides, a painted back, a lid; and the feeder's window looks
# into its own box.
FOOT = 3.0  # the tank's base under its floor


@dataclass(frozen=True)
class Box:
    """The inside of the tank: x left and right, y of the lid and of the floor, z of the front glass and the back."""

    x0: float
    x1: float
    top: float
    floor: float
    front: float
    back: float

    @property
    def surface(self) -> float:
        return self.floor - (self.floor - self.top) * WATER_TOP

    @property
    def mid_z(self) -> float:
        return (self.front + self.back) / 2


def tank() -> Box:
    x, y, z = BENCH
    w, h, d = TANK
    return Box(x - w / 2, x + w / 2, y - FOOT - h, y - FOOT, z - d / 2, z + d / 2)


def swim_room() -> Box:
    """Where the fish's middle may be: in the front half of the water, clear of the glass, the gravel, the surface
    and the plants at the back."""
    b = tank()
    return Box(b.x0 + 14.0, b.x1 - 10.0, b.surface + 8.0, b.floor - 11.0, b.front + 7.0, b.mid_z + 2.0)


PIVOT_DROP, REACH = 3.0, 24.0  # the lever hangs this far under the lid, and reaches this far down


def lever_pivot() -> tuple[float, float, float]:
    b = tank()
    return (b.x1 - 14.0, b.top + PIVOT_DROP, b.mid_z - 3.0)


def lever_tip(swing: float) -> tuple[float, float, float]:
    """Where the lever's red paddle is at ``swing`` degrees, pushed toward the tank's right wall: what the fish's nose
    touches, swimming right."""
    px, py, pz = lever_pivot()
    a = math.radians(swing)
    return (px + REACH * math.sin(a), py + REACH * math.cos(a), pz)


def chute_mouth() -> tuple[float, float, float]:
    """Where a pellet comes out of the feeder's chute, just under the water's top, in front of the lever."""
    b = tank()
    return (b.x1 - 34.0, b.surface + 1.5, b.mid_z - 6.0)


FEEDER = (36.0, 34.0, 30.0)  # the feeder box on the lid: wide, tall, deep
DIAL_R = 13.0
NUMBER_AT = 0.72  # the printed hours' centres, as a share of the face's radius: a ring outside the hand's reach
NUMBER_SIZE = 56  # their size on the face's 512 px print
GLYPH = 0.62  # the most of its size a printed number reaches from its centre, any way (a two-digit "24" across)
HAND_TIP = 0.42  # the hand's reach as a share of the radius: short of the printed hours
MARKS = (0.88, 0.97)  # the hour marks' ring, outside the hours
WEDGE = (0.9, 0.99)  # the fed-hour wedge's ring: the "24" under it stays clear


def numbers_inside() -> float:
    """The innermost reach of a printed hour, as a share of the face's radius: the hand stays inside it."""
    return NUMBER_AT - GLYPH * NUMBER_SIZE / 256


def feeder_centre() -> tuple[float, float, float]:
    b = tank()
    return (b.x1 - FEEDER[0] / 2 - 2.0, b.top - 2.0 - FEEDER[1] / 2, b.mid_z)


def dial_centre() -> tuple[float, float, float]:
    """The middle of the timer's face, on the feeder's front, toward the lens."""
    fx, fy, fz = feeder_centre()
    return (fx, fy, fz - FEEDER[2] / 2 - 0.9)


HOPPER = (14.0, 30.0, 16.0)  # the pellet hopper beside the feeder, with a window in its front


def hopper_centre() -> tuple[float, float, float]:
    fx, fy, fz = feeder_centre()
    b = tank()
    return (fx - FEEDER[0] / 2 - HOPPER[0] / 2 - 1.0, b.top - 2.0 - HOPPER[1] / 2, b.mid_z - 4.0)


@lru_cache(maxsize=1)
def dial_print() -> Print:
    """The timer's face: the hours of the day at the quarters, in a ring outside the hand's reach and inside the hour
    marks."""
    s, mid = 512, 256
    r, size, ink = NUMBER_AT * mid, NUMBER_SIZE, "#1C2A4A"
    lines = (Line("24", mid, mid - r, size, ink), Line("6", mid + r, mid, size, ink),
             Line("12", mid, mid + r, size, ink), Line("18", mid - r, mid, size, ink))  # fmt: skip
    return Print("#FFF6E4", s, s, lines)


def _dial(m: Model, hour: float) -> None:
    """The feeder's timer: a cream face printed with the hours, the fed hour a red wedge at the top, a hand going
    round once a day, and a rim of his teal."""
    cx, cy, cz = dial_centre()
    ring = [(cx + (DIAL_R + 1.1) * math.sin(a), cy - (DIAL_R + 1.1) * math.cos(a), cz) for a in
            np.linspace(0.0, math.tau, 61)]  # fmt: skip
    m.ribbon("dialrim", ring, 1.4, sides=10)
    rim = np.linspace(0.0, math.tau, 49)[:-1]
    disc = [(cx, cy, cz + 0.5)] + [(cx + DIAL_R * math.sin(a), cy - DIAL_R * math.cos(a), cz + 0.5) for a in rim]
    uvs = [(0.5, 0.5)] + [(0.5 + 0.5 * math.sin(a), 0.5 + 0.5 * math.cos(a)) for a in rim]  # the print's top is up
    fan = [(0, 1 + i, 1 + (i + 1) % len(rim)) for i in range(len(rim))]
    m.surface("dialface", disc, [(0.0, 0.0, -1.0)] * len(disc), fan, uvs)
    _hand(m, hour, still=True)


def _hand(m: Model, hour: float, still: bool) -> None:
    """The dial's marks and its fed-hour wedge (``still``), or its hand at ``hour``."""
    cx, cy, cz = dial_centre()
    wedge = math.tau / DIAL_HOURS
    if still:
        start = FED_HOUR * wedge - wedge / 2
        arc = np.linspace(start, start + wedge, 8)  # one hour of the day: the fed hour, as the test fed them
        pts = [(cx + DIAL_R * r * math.sin(a), cy - DIAL_R * r * math.cos(a), cz - 0.05) for r in WEDGE
               for a in arc]  # fmt: skip
        k = len(arc)
        band = [t for i in range(k - 1) for t in ((i, k + i, k + i + 1), (i, k + i + 1, i + 1))]
        m.surface("fedhour", pts, [(0.0, 0.0, -1.0)] * len(pts), band)  # a ring's slice: the number stays clear
        for k in range(1, DIAL_HOURS):  # the fed hour is its wedge, and a printed hour is its own mark
            if k % 6 == 0:
                continue
            a = k * wedge
            r0, r1 = (DIAL_R * f for f in MARKS)
            m.rod("dialhand", (cx + r0 * math.sin(a), cy - r0 * math.cos(a), cz - 0.2),
                  (cx + r1 * math.sin(a), cy - r1 * math.cos(a), cz - 0.2), 0.3)  # fmt: skip
        return
    a = hour * wedge
    tip = (cx + DIAL_R * HAND_TIP * math.sin(a), cy - DIAL_R * HAND_TIP * math.cos(a), cz - 1.0)
    tail = (cx - DIAL_R * 0.12 * math.sin(a), cy + DIAL_R * 0.12 * math.cos(a), cz - 1.0)
    m.capsule("dialhand", tail, tip, 0.8)
    m.ell("dialhand", (cx, cy, cz - 1.0), (1.7, 1.7, 0.9))


def bench(m: Model, hopper: float = 1.0) -> None:
    """What stands still on his worktop: the lab tank (a glass front, teal sides, a painted back, a lid, gravel and
    plants, the water's top), the feeder on its lid with the timer's face, and its hopper, ``hopper`` 0 to 1 full of
    pellets behind a window. The moving parts are :func:`parts`."""
    if not (checks.number(hopper) and 0.0 <= hopper <= 1.0):
        raise LabError(f"the hopper is 0 to 1 full, got {hopper!r}")
    x, y, z = BENCH
    w, h, d = TANK
    b = tank()
    m.box("tankframe", (x, y - FOOT / 2, z), (w + 6, FOOT, d + 6), 1.0)
    m.box("tankback", (x, (b.top + b.floor) / 2, b.back + 1.0), (w + 2, h, 2.0))
    for sx in (b.x0 - 1.0, b.x1 + 1.0):
        m.box("tankside", (sx, (b.top + b.floor) / 2, z), (2.0, h, d + 2))
    m.box("tankglass", (x, (b.top + b.floor) / 2, b.front - 0.6), (w + 1.6, h, 1.2))
    m.box("tankframe", (x, b.top - 1.0, z), (w + 6, 2.4, d + 6), 0.8)  # the lid
    for cx in (b.x0 - 1.4, b.x1 + 1.4):
        m.box("tankframe", (cx, (b.top + b.floor) / 2, b.front - 1.4), (3.0, h + 1, 3.0), 0.8)
    m.box("tankframe", (x, b.floor + 0.6, b.front - 1.4), (w + 5, 2.6, 3.0), 0.8)
    m.box("tankwater", (x, b.surface + 0.3, z), (w - 0.2, 0.6, d - 0.2))
    rng = np.random.default_rng(1994)
    for k in range(140):
        gx, gz = rng.uniform(b.x0 + 1.5, b.x1 - 1.5), rng.uniform(b.front + 1.5, b.back - 1.5)
        r = rng.uniform(1.2, 2.1)
        tone = ("gravel", "gravelred", "gravelsage")[k % 3]
        m.ell(tone, (gx, b.floor - r * 0.6 - rng.uniform(0, 1.6), gz), (r, r * 0.7, r))
    for k, (px, pz, tall) in enumerate(((b.x0 + 7, b.back - 5, 34.0), (b.x0 + 13, b.back - 8, 25.0),
                                         (b.x0 + 30, b.back - 4, 20.0))):  # fmt: skip
        for i in range(5):
            a = i * 1.3 + k
            tip = (px + math.cos(a) * 5.0, b.floor - tall + i * 3.0, pz + math.sin(a) * 2.5)
            m.tube("leaf", ((px, b.floor - 2.0, pz), (px + math.cos(a) * 2.0, b.floor - tall * 0.5, pz), tip), 0.9)
            m.ell("leaflight" if i % 2 else "leaf", tip, (2.4, 6.0, 1.2), rotation=-20 + i * 9, rotation_y=i * 37)
    px, py, pz = lever_pivot()
    m.box("steelbar", (px, b.top + 1.0, pz), (5.0, 2.0, 5.0), 0.8)  # the lever's bracket under the lid
    fx, fy, fz = feeder_centre()
    m.box("feeder", (fx, fy, fz), FEEDER, 3.0)
    cx, cy, cz = chute_mouth()
    m.tube("feederdark", ((cx, b.top - 1.0, cz), (cx, cy - 1.0, cz)), 2.0)
    m.ell("feederdark", (cx, cy - 0.6, cz), (2.6, 1.0, 2.6))
    hx, hy, hz = hopper_centre()
    hw, hh, hd = HOPPER
    m.box("feeder", (hx, hy, hz + 1.0), (hw, hh, hd), 2.0)
    front = hz + 1.0 - hd / 2  # the hopper's face; the pellets lie in a shallow case on it, behind the window
    m.box("feeder", (hx, hy, front - 0.3), (hw - 3.0, hh - 5.0, 0.6))  # a pale case: the pellets show against it
    for dx, dy, sw, sh in ((0.0, -(hh - 3.0) / 2, hw, 3.0), (0.0, (hh - 3.0) / 2, hw, 3.0),
                           (-(hw - 1.5) / 2, 0.0, 1.5, hh), ((hw - 1.5) / 2, 0.0, 1.5, hh)):  # fmt: skip
        m.box("feeder", (hx + dx, hy + dy, front - 2.0), (sw, sh, 4.0), 0.4)
    m.box("tankglass", (hx, hy, front - 3.6), (hw - 1.0, hh - 1.0, 0.6))
    level = hh - 8.0
    for k in range(int(round(26 * hopper))):
        row, col = divmod(k, 4)
        m.ell("pellet", (hx - 4.0 + col * 2.6 + (row % 2) * 1.0, hy + level / 2 - row * 2.2, front - 1.7),
              (1.3, 1.1, 1.1))  # fmt: skip
    m.tube("feederdark", ((hx + hw / 2 - 1.0, hy - hh / 2 + 6.0, hz), (fx - FEEDER[0] / 2 + 1.0, fy - 8.0, fz)), 1.4)
    _dial(m, 0.0)


def lamp() -> plates.Light:
    """The tank's lamp under its lid, as an aquarium has: it lights the water the lid keeps in shade."""
    b = tank()
    return plates.Light("tank-lamp", "sphere-area", "#FFF1D2", LAMP_POWER, ((b.x0 + b.x1) / 2, b.top + 2.0,
                        b.front + 8.0), 6.0)  # fmt: skip


LAMP_POWER = 1.0


# -- the choreography -------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Mark:
    """Where the fish's middle is at second ``at`` and how he holds himself there."""

    at: float
    where: tuple[float, float, float]
    heading: float = 0.0
    pitch: float = 0.0
    mouth: float = 0.2


STRIDE = 26.0  # model units a full swim stroke carries him
IDLE = 0.9  # strokes a second when he hangs in the water, fanning


def _eased(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u)))


def nose_to_middle(nose: tuple[float, float, float], heading: float, pitch: float = 0.0) -> tuple[float, float, float]:
    """Where his middle is when his mouth is at ``nose``, turned ``heading`` and ``pitch``."""
    off = _spin(heading, pitch) @ (SIZE * np.array([LENGTH / 2 + 1.0, 0.6, 0.0]))
    return tuple(float(v) for v in np.asarray(nose, float) - off)  # type: ignore[return-value]


def swim(marks: Sequence[Mark], t: float) -> FishPose:
    """The fish at second ``t`` along ``marks``: eased from mark to mark, his tail beating harder the faster he goes,
    his strokes counted from the way he has come, his fins fanning, his mouth opening as a mark asks."""
    if not marks or [k.at for k in marks] != sorted(k.at for k in marks):
        raise LabError("a swim is marks going forward in time")
    travelled, speed, k = 0.0, 0.0, 0
    while k + 1 < len(marks) and marks[k + 1].at <= t:
        travelled += math.dist(marks[k].where, marks[k + 1].where)
        k += 1
    a = marks[k]
    if k + 1 < len(marks) and t > a.at:
        b = marks[k + 1]
        span = b.at - a.at
        u = (t - a.at) / span
        e = _eased(u)
        gap = math.dist(a.where, b.where)
        travelled += gap * e
        speed = gap / span * (math.pi / 2) * math.sin(math.pi * u)
        at = tuple(p + (q - p) * e for p, q in zip(a.where, b.where, strict=True))
        heading, pitch = a.heading + (b.heading - a.heading) * e, a.pitch + (b.pitch - a.pitch) * e
        mouth = a.mouth + (b.mouth - a.mouth) * e
    else:
        at, heading, pitch, mouth = a.where, a.heading, a.pitch, a.mouth
    phase = IDLE * t + travelled / STRIDE
    beat = min(0.95, 0.3 + speed / 40.0)
    fins = 0.5 + 0.45 * math.sin(math.tau * 1.3 * t)
    return FishPose(tuple(round(v, 3) for v in at), round(heading, 2), round(pitch, 2), round(phase, 4),  # type: ignore[arg-type]
                    round(beat, 3), round(min(1.0, max(0.0, mouth)), 3), round(fins, 3))  # fmt: skip


PRESS = 14.0  # degrees a nudge swings the lever
PUSH, BACK = 0.12, 0.4  # seconds the lever takes to swing and to fall back


def lever(t: float, presses: Sequence[float]) -> float:
    """The lever's swing at second ``t``, nudged at each of ``presses``: out fast, back slower."""
    swing = 0.0
    for at in presses:
        if at - PUSH <= t < at:
            swing = max(swing, PRESS * _eased((t - at + PUSH) / PUSH))
        elif at <= t < at + BACK:
            swing = max(swing, PRESS * (1.0 - _eased((t - at) / BACK)))
    return round(swing, 2)


SINK = 9.0  # model units a second a pellet sinks


def pellets(t: float, drops: Sequence[tuple[float, float]]) -> tuple[tuple[float, float, float], ...]:
    """The pellets in the water at second ``t``: each of ``drops`` (out of the chute, eaten) sinks from the chute's
    mouth with a little drift until it is eaten."""
    cx, cy, cz = chute_mouth()
    floor = tank().floor - 3.0
    out = []
    for at, eaten in drops:
        if at <= t < eaten:
            d = t - at
            out.append((round(cx + 1.2 * math.sin(d * 3.0), 3), round(min(floor, cy + SINK * d), 3), cz))
    return tuple(out)


def pellet_at(drop: float, t: float) -> tuple[float, float, float]:
    """Where a pellet out of the chute at ``drop`` is at ``t``, for the fish to meet it."""
    return pellets(t, ((drop, t + 1.0),))[0]


def keyed(t: float, keys: Sequence[tuple[float, float]]) -> float:
    """A value eased between ``keys`` of (second, value)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:], strict=False):
        if a <= t <= b:
            return va + (vb - va) * _eased((t - a) / (b - a))
    return keys[-1][1]


def parts(m: Model, state: Rig, fish: FishPose | None) -> None:
    """What moves: the fish at ``fish``, the lever, the timer's hand, the pellets falling and the bubbles. Drawn on
    their own over :func:`bench`, so nothing of the bench may stand in front of them from the lens: the fish swims
    in front of the plants, the lever hangs below the lid, the pellets fall in front of it."""
    b = tank()
    px, py, pz = lever_pivot()
    tip = lever_tip(state.lever)
    m.capsule("steelbar", (px, py, pz), tip, 0.7)
    m.ell("lever", tip, (3.6, 3.6, 3.6))
    _hand(m, state.hour, still=False)
    for p in state.pellets:
        m.ell("pellet", p, (1.5, 1.3, 1.5))
    for i in range(6):  # a thread of bubbles rising from the gravel at the front left
        rise = (state.bubbles + i / 6.0) % 1.0
        by = b.floor - 3.0 - rise * (b.floor - b.surface - 5.0)
        m.ell("bubble", (b.x0 + 15.0 + math.sin(rise * 9.0) * 1.0, by, b.front + 6.0), (0.7 + 0.4 * rise,) * 3)
    if fish is not None:
        goldfish(m, fish)


# -- the calendar -----------------------------------------------------------------------------------------------------
CALENDAR = (-27.0, TOP - FOOT - TANK[1] - 2.2, BENCH[2] - 4.0)  # a tear-off calendar on the tank's lid, at its left
PAGE = 20.0  # a page's side
TIP = 100.0  # degrees a torn page tips forward before it is gone


def page_name(word: str, number: str) -> str:
    return f"page-{word.lower()}-{number}"


@cache
def page_print(word: str, number: str) -> Print:
    """One calendar page: a word over a big number, as tear-off calendars print the day."""
    return Print("#FFF6E4", 512, 512, (Line(word, 256, 112, 96, "#A82E22"), Line(number, 256, 318, 230, "#1C2A4A")))


def page_material(word: str, number: str) -> Material:
    """The printed face of one calendar page."""
    return Material(page_name(word, number), "#FFFFFF", roughness=0.75, print=page_print(word, number))


def calendar_stand(m: Model) -> None:
    """The calendar's stand: a teal base and back board."""
    x, y, z = CALENDAR
    m.box("calendarback", (x, y - 1.5, z), (PAGE + 8.0, 3.0, 12.0), 1.0)
    m.box("calendarback", (x, y - PAGE / 2 - 5.0, z + 3.0), (PAGE + 6.0, PAGE + 8.0, 3.0), 1.5)
    m.box("calendar", (x, y - PAGE / 2 - 4.0, z + 0.8), (PAGE + 2.0, PAGE + 2.0, 2.4), 0.4)


def calendar_pages(m: Model, page: tuple[str, str], under: tuple[str, str] | None = None, lift: float = 0.0) -> None:
    """The calendar's top page, and when one is torn off (``lift`` 0 to 1) the page under it too: the torn page tips
    forward off the pad on its bottom edge, toward the lens and down, so it never rises over the calendar's top."""
    if not (checks.number(lift) and 0.0 <= lift <= 1.0):
        raise LabError(f"a page lifts 0 to 1, got {lift!r}")
    x, y, z = CALENDAR
    cy = y - PAGE / 2 - 4.0
    showing = under if (lift > 0.0 and under is not None) else page
    m.faceplate(page_name(*showing), (x, cy, z - 0.6), PAGE, PAGE)
    if lift > 0.0 and under is not None:
        a = math.radians(TIP * lift)
        hinge = np.array([x, cy + PAGE / 2, z - 0.9])
        up = np.array([0.0, -math.cos(a), -math.sin(a)])
        corners = [hinge + np.array([-PAGE / 2, 0.0, 0.0]), hinge + np.array([PAGE / 2, 0.0, 0.0]),
                   hinge + np.array([PAGE / 2, 0.0, 0.0]) + up * PAGE,
                   hinge + np.array([-PAGE / 2, 0.0, 0.0]) + up * PAGE]  # fmt: skip
        normal = np.cross(corners[1] - corners[0], corners[3] - corners[0])
        normal = normal / np.linalg.norm(normal)
        uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        m.surface(page_name(*page), corners, [normal] * 4, [(0, 1, 2), (0, 2, 3)], uvs)
