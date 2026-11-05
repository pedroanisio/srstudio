"""Small Print's Great Wall set: the finding acted out on Rafa's worktop, in his clay world (ADR 0240).

Can you see the wall from space? A board of sandy hills with a wall and its towers snaking over them in nearly the same
earth; a clay space station on a wire arm that orbits over it while a desk lamp, the sun, swings low and high; a clay
Earth with the Moon on a stick drawn away from it; the station's window up close, an astronaut in it looking down and
shaking his head; and a block of the wall pushed by a palette knife into a mound of dirt of its own colour. Everything
is drawn in Rafa's model units (:mod:`srstudio.rafa`): x right, y down, z away from the lens, the worktop's top at
y = -248. A pose is one replacement plate; :mod:`srstudio.smallprint_scene` puts them on the clock.

Every part here is ``proposed`` until the operator has seen it on a rendered clip.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

import numpy as np

from . import checks, clay, plates, rafa, smallprint_props
from .clay import Mesh, Model
from .errors import SrstudioError
from .foley import Burst
from .plates import Material

__all__ = [
    "BOARD",
    "COLOUR_AT",
    "EARTH",
    "MOON_FROM",
    "PIVOT",
    "SCRAPE",
    "SERVO",
    "SWITCH",
    "WallError",
    "astronaut",
    "board",
    "colour_parts",
    "colour_still",
    "dirt",
    "earth",
    "earth_still",
    "finished",
    "keyed",
    "knife",
    "lamp",
    "lamp_light",
    "materials",
    "moon",
    "orbit_parts",
    "servo_spans",
    "station",
    "station_at",
    "wall_block",
    "window_still",
    "yang_parts",
]

TOP = -248.0  # the worktop's top
BOARD = (0.0, TOP, -206.0)  # the land board's middle, on the worktop
BOARD_SIZE = (104.0, 6.0, 128.0)  # wide, thick, deep
PIVOT = (0.0, TOP - 118.0, -142.0)  # the orbit arm's pivot, on its post at the board's back
ARM = 62.0  # the arm's reach from the pivot to the station
DROP = 34.0  # how far the station hangs under the pivot
EARTH = (-14.0, TOP - 52.0, -196.0)  # the globe's middle, on its stand
EARTH_R = 42.0
MOON_FROM = (40.0, TOP - 92.0, -236.0)  # the Moon's middle at the start of its draw away
MOON_R = 16.0
COLOUR_AT = (0.0, TOP, -292.0)  # the colour test, before the land board: the block at its left, the dirt right


class WallError(SrstudioError, ValueError):
    """A pose, a place or a span the wall set does not have."""


OWN: dict[str, tuple[str, float, float, bool]] = {  # colour, roughness, metallic, clay-finished
    "hillshade": ("#BFA073", 0.65, 0.0, True),  # a fold of the same land, a hair darker: the hills read, not the wall
    "boardedge": ("#7A5A3C", 0.55, 0.0, True),
    "post": ("#1A504F", 0.45, 0.0, True),
    "wire": ("#AAB8B4", 0.3, 0.6, False),
    "hull": ("#EDE7DA", 0.45, 0.0, True),
    "hullband": ("#C0392B", 0.45, 0.0, True),
    "solar": ("#26406E", 0.25, 0.2, False),
    "solarrib": ("#D7C9A8", 0.4, 0.3, False),
    "porthole": ("#1C2A4A", 0.12, 0.0, False),
    "lampbody": ("#E3B23C", 0.35, 0.0, True),
    "bulb": ("#FFF4C8", 0.2, 0.0, False),
    "sea": ("#3E7FA6", 0.35, 0.0, True),
    "green": ("#7BA05B", 0.6, 0.0, True),
    "desert": ("#D2B27E", 0.6, 0.0, True),
    "ice": ("#F4F1EA", 0.5, 0.0, True),
    "moonclay": ("#BDB7AC", 0.75, 0.0, True),
    "crater": ("#9C968C", 0.8, 0.0, True),
    "stick": ("#8A5A36", 0.6, 0.0, True),
    "suit": ("#F2EEE6", 0.5, 0.0, True),
    "visor": ("#2E3A55", 0.1, 0.4, False),
    "flagred": ("#C8372D", 0.5, 0.0, True),
    "dirt": ("#C2A275", 0.8, 0.0, True),  # the dirt: the wall's own earth, a shade off it
    "pebble": ("#A88A61", 0.7, 0.0, True),
    "blade": ("#C9D3D0", 0.25, 0.7, False),
    "handle": ("#286A67", 0.5, 0.0, True),
}


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Rafa's world, Small Print's props (the land and the wall's stone among them) and the set's own."""
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
        )  # fmt: skip
        for name, (colour, rough, metal, clayed) in OWN.items()
    }
    return {**smallprint_props.materials(), **own}


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: his clay tile on the set's clay parts, the props' finish on the rest."""
    if mesh.material in OWN:
        return clay.planar(mesh, 70.0) if OWN[mesh.material][3] else mesh
    return smallprint_props.finished(mesh)


def _turned(m: Model, build, spin: np.ndarray, at: Sequence[float], scale: float = 1.0) -> None:
    sub = Model()
    build(sub)
    for mesh in sub.meshes():
        m.surface(mesh.material, scale * mesh.vertices @ spin.T + np.asarray(at, float), mesh.normals @ spin.T,
                  mesh.triangles)  # fmt: skip


def _yaw(degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    return np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])


def _eased(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u)))


def keyed(t: float, keys: Sequence[tuple[float, float]]) -> float:
    """A value eased between ``keys`` of (second, value), held before the first and after the last."""
    if not keys or [k[0] for k in keys] != sorted(k[0] for k in keys):
        raise WallError("keys go forward in time")
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:], strict=False):
        if a <= t <= b:
            return va + (vb - va) * _eased((t - a) / (b - a)) if b > a else vb
    return keys[-1][1]


# -- the land and its wall ---------------------------------------------------------------------------------------------
RUN = ((-50.0, -56.0), (-34.0, -30.0), (-14.0, -36.0), (2.0, -10.0), (18.0, 6.0), (30.0, 30.0), (48.0, 50.0))  # x, z
HILLS = ((-34.0, -34.0, 26.0, 10.0, 22.0), (-6.0, -20.0, 22.0, 8.0, 18.0), (22.0, 10.0, 28.0, 12.0, 24.0),
         (-30.0, 30.0, 20.0, 7.0, 18.0), (40.0, -40.0, 16.0, 6.0, 16.0), (8.0, 46.0, 24.0, 6.0, 14.0),
         (-40.0, -2.0, 14.0, 6.0, 14.0))  # fmt: skip


def _ground(x: float, z: float) -> float:
    """The land's height over the board at (x, z) about the board's middle: the hills' tops, eased."""
    top = 0.0
    for hx, hz, rx, h, rz in HILLS:
        d = ((x - hx) / rx) ** 2 + ((z - hz) / rz) ** 2
        if d < 1.0:
            top = max(top, h * math.sqrt(1.0 - d))
    return top


def board(m: Model) -> None:
    """A board of rolling sandy hills, a long wall with battlements snaking over them and two watchtowers, all in
    nearly one earth: the wall is there, and hard to pick out. No one place's landmark is copied."""
    bx, by, bz = BOARD
    w, h, d = BOARD_SIZE
    m.box("boardedge", (bx, by - h / 2, bz), (w + 2.0, h, d + 2.0), 1.2)
    m.box("land", (bx, by - h - 0.6, bz), (w, 1.4, d), 0.6)
    for k, (hx, hz, rx, hh, rz) in enumerate(HILLS):
        m.ell("land" if k % 2 else "hillshade", (bx + hx, by - h, bz + hz), (rx, hh, rz))
    for (ax, az), (cx, cz) in zip(RUN, RUN[1:], strict=False):
        steps = max(2, int(math.hypot(cx - ax, cz - az) // 3.2))
        for i in range(steps):
            u = (i + 0.5) / steps
            x, z = ax + (cx - ax) * u, az + (cz - az) * u
            g = _ground(x, z)
            yaw = math.degrees(math.atan2(cz - az, cx - ax))
            rise = by - h - g

            def course(s: Model, i: int = i) -> None:
                s.box("wallstone", (0.0, -3.0, 0.0), (3.6, 6.0, 3.0), 0.3)
                if i % 2 == 0:
                    s.box("wallstone", (0.0, -7.0, 0.0), (1.7, 2.0, 3.0), 0.2)

            _turned(m, course, _yaw(-yaw), (bx + x, rise, bz + z))
    for x, z in (RUN[1], RUN[4]):
        g = _ground(x, z)
        m.box("wallstone", (bx + x, by - h - g - 6.0, bz + z), (7.0, 12.0, 7.0), 0.6)
        for dx in (-2.4, 2.4):
            m.box("wallstone", (bx + x + dx, by - h - g - 13.0, bz + z), (1.8, 2.2, 7.0), 0.2)
    px, py, pz = PIVOT
    m.cylinder("post", (px, (TOP + py) / 2, pz), 2.4, TOP - py)
    m.box("post", (px, TOP - 1.0, pz), (14.0, 2.0, 14.0), 0.8)
    m.ell("post", (px, py, pz), (4.0, 4.0, 4.0))


# -- the space station on its arm --------------------------------------------------------------------------------------
def station_at(swing: float) -> tuple[float, float, float]:
    """Where the station's middle is with the arm swung ``swing`` degrees from straight at the lens (+ to frame
    right)."""
    px, py, pz = PIVOT
    a = math.radians(swing)
    return (px + ARM * math.sin(a), py + DROP, pz - ARM * math.cos(a))


def station(m: Model, at: Sequence[float], turn: float = 0.0, size: float = 1.0) -> None:
    """A clay space station: a white hull of three modules with a red band and portholes, a cupola window under it
    facing the ground, and two pairs of blue solar wings on a truss, ribbed."""

    def build(s: Model) -> None:
        s.capsule("hull", (-12.0, 0.0, 0.0), (12.0, 0.0, 0.0), 5.0)
        s.capsule("hull", (0.0, 0.0, -9.0), (0.0, 0.0, 9.0), 3.8)
        for x in (-6.0, 6.0):
            s.rod("hullband", (x - 0.8, 0.0, 0.0), (x + 0.8, 0.0, 0.0), 5.3)
        for x in (-9.0, -3.0, 3.0, 9.0):
            s.ell("porthole", (x, -1.2, -4.9), (1.1, 1.1, 0.5))
        s.ell("porthole", (0.0, 4.6, -1.0), (3.0, 1.6, 3.0))  # the cupola's window, to the ground
        s.rod("wire", (-26.0, 0.0, 0.0), (26.0, 0.0, 0.0), 0.8)
        for x in (-22.0, -15.0, 15.0, 22.0):
            s.box("solar", (x, 0.0, 0.0), (5.6, 0.7, 22.0), 0.2)
            for k in range(-2, 3):
                s.box("solarrib", (x, -0.45, k * 4.4), (5.8, 0.25, 0.5))

    _turned(m, build, _yaw(turn), at, size)


def lamp_light(at: Sequence[float], power: float = 1.0) -> plates.Light:
    """The desk lamp's bulb, the set's sun: it lights the land from where the lamp's head is."""
    return plates.Light("wall-sun", "sphere-area", "#FFE6B8", power, (float(at[0]), float(at[1]), float(at[2])), 6.0)


LAMP_BASE = (-58.0, TOP, -168.0)


def lamp(m: Model, tilt: float) -> None:
    """A clay desk lamp at the board's left, its arm up and its head over the land, tipped ``tilt`` degrees from
    pointing straight down toward the frame's right (a low sun at 60)."""
    if not (checks.number(tilt) and 0.0 <= tilt <= 75.0):
        raise WallError(f"the lamp tips 0 to 75 degrees, got {tilt!r}")
    x, y, z = LAMP_BASE
    m.cylinder("lampbody", (x, y - 1.5, z), 9.0, 3.0)
    elbow = (x + 4.0, y - 58.0, z)
    m.capsule("lampbody", (x, y - 3.0, z), elbow, 1.4)
    head = (elbow[0] + 22.0, elbow[1] + 4.0, z)
    m.capsule("lampbody", elbow, head, 1.4)
    a = math.radians(tilt)
    down = np.array([math.sin(a), math.cos(a), 0.0])
    rim = np.asarray(head) + down * 9.0
    m.rod("lampbody", head, tuple(rim), 4.0)
    m.ell("lampbody", tuple(rim), (8.5, 3.2, 8.5), rotation=-tilt)
    m.ell("bulb", tuple(rim + down * 1.6), (4.6, 2.0, 4.6), rotation=-tilt)


def orbit_parts(m: Model, pose: tuple[float, float]) -> None:
    """The orbit's moving parts: the arm and the station at ``swing`` degrees, the lamp tipped ``tilt``."""
    swing, tilt = pose
    at = station_at(swing)
    m.rod("wire", PIVOT, at, 0.9)
    station(m, at, turn=-swing * 0.3, size=1.45)
    lamp(m, tilt)


def servo_spans(keys: Sequence[tuple[float, float]], least: float = 2.0) -> list[tuple[float, float]]:
    """The spans the arm's servo runs: each pair of keys between which the swing changes by ``least`` degrees or
    more."""
    return [(a, b) for (a, va), (b, vb) in zip(keys, keys[1:], strict=False) if abs(vb - va) >= least]


# -- the Earth and the Moon --------------------------------------------------------------------------------------------
CONTINENTS = ((40.0, -10.0, 0.42, "green"), (70.0, 20.0, 0.38, "desert"), (-10.0, 5.0, 0.36, "green"),
              (110.0, -25.0, 0.3, "desert"), (20.0, 40.0, 0.28, "green"))  # fmt: skip


def earth(m: Model, spin: float = 0.0) -> None:
    """A clay globe: sea, raised land of green and sand, white caps, turned ``spin`` degrees; on its land a wall too
    fine to see at this size, a hair of the same sand."""
    cx, cy, cz = EARTH
    m.ell("sea", EARTH, (EARTH_R, EARTH_R, EARTH_R))
    for lon, lat, size, tone in CONTINENTS:
        a, b = math.radians(lon + spin), math.radians(lat)
        n = np.array([math.sin(a) * math.cos(b) * -1.0, -math.sin(b), -math.cos(a) * math.cos(b)])
        p = np.asarray(EARTH) + n * EARTH_R * 0.97
        m.ell(tone, tuple(p), (EARTH_R * size, EARTH_R * size * 0.8, EARTH_R * size))
    for sign in (-1.0, 1.0):
        m.ell("ice", (cx, cy + sign * EARTH_R * 0.94, cz), (EARTH_R * 0.42, 3.0, EARTH_R * 0.42))


def earth_still(m: Model) -> None:
    """The globe's stand: a teal foot and a brass ring round it, and the Moon's stick's foot at its right."""
    cx, cy, cz = EARTH
    m.cylinder("post", (cx, TOP - 2.0, cz), 16.0, 4.0)
    m.cylinder("post", (cx, (TOP + cy + EARTH_R) / 2, cz), 2.6, TOP - cy - EARTH_R + 2.0)
    ring = [(cx + (EARTH_R + 3.0) * math.cos(a), cy + (EARTH_R + 3.0) * math.sin(a), cz) for a in
            np.linspace(-math.pi / 2, math.pi / 2, 25)]  # fmt: skip
    m.ribbon("copper", ring, 1.2, sides=8)


def moon(m: Model, at: Sequence[float], size: float = 1.0) -> None:
    """A clay Moon on a stick: grey, its craters pressed in, the stick down to its foot on the worktop."""
    x, y, z = (float(v) for v in at)
    r = MOON_R * size
    m.ell("moonclay", (x, y, z), (r, r, r))
    for dx, dy, s in ((-0.4, -0.3, 0.28), (0.3, 0.25, 0.22), (-0.1, 0.45, 0.18), (0.45, -0.35, 0.16), (0.0, 0.0, 0.2)):
        m.ell("crater", (x + dx * r, y + dy * r, z - r * math.sqrt(max(0.05, 1 - dx * dx - dy * dy)) * 0.93),
              (r * s, r * s, r * s * 0.35))  # fmt: skip
    m.rod("stick", (x, y + r, z), (x, TOP - 2.0, z), 1.3 * size)
    m.cylinder("post", (x, TOP - 1.5, z), 7.0 * size, 3.0)


# -- the window and the astronaut --------------------------------------------------------------------------------------
WINDOW = (0.0, TOP - 64.0, -206.0)  # the cupola window's middle, close up: the station hangs over the land
WINDOW_R = 30.0


def _segment(m: Model, material: str, centre: Sequence[float], r: float, below: float) -> None:
    """The part of a flat disc of radius ``r`` facing the lens at ``centre`` that lies under the row ``below`` from
    its middle (y down): the whole disc for ``below`` <= -r."""
    x, y, z = (float(v) for v in centre)
    lo = max(-1.0, min(1.0, below / r))
    a0 = math.asin(lo)
    arc = np.linspace(a0, math.pi - a0, 41)
    pts = [(x + r * math.cos(a), y + r * math.sin(a), z) for a in arc]
    mid = (x, y + (r + max(below, -r)) / 2, z)
    verts = [mid, *pts]
    fan = [(0, i + 1, i + 2) for i in range(len(pts) - 1)] + ([(0, len(pts), 1)] if below <= -r else [])
    m.surface(material, verts, [(0.0, 0.0, -1.0)] * len(verts), fan)


def window_still(m: Model) -> None:
    """The station close up: its white hull round a big round window with a red frame, bolts, two wings' roots, and
    the land board far under it."""
    x, y, z = WINDOW
    m.box("hull", (x, y, z + 14.0), (124.0, 82.0, 22.0), 10.0)
    ring = [(x + WINDOW_R * math.cos(a), y + WINDOW_R * math.sin(a), z + 2.5) for a in np.linspace(0, math.tau, 61)]
    m.ribbon("hullband", ring, 3.4, sides=10)
    for k in range(12):
        a = k * math.tau / 12
        m.ell("solarrib", (x + (WINDOW_R + 7.0) * math.cos(a), y + (WINDOW_R + 7.0) * math.sin(a), z + 2.4),
              (1.3, 1.3, 1.0))  # fmt: skip
    _segment(m, "porthole", (x, y, z + 2.9), WINDOW_R, -WINDOW_R)  # space, dark
    _segment(m, "sea", (x, y, z + 2.8), WINDOW_R, WINDOW_R * 0.35)  # the Earth's curve under him, far down
    _segment(m, "desert", (x - 6.0, y, z + 2.7), WINDOW_R * 0.7, WINDOW_R * 0.62)
    for side in (-1.0, 1.0):
        m.box("solar", (x + side * 82.0, y + 6.0, z + 16.0), (40.0, 1.2, 44.0), 0.4)
        for k in range(-3, 4):
            m.box("solarrib", (x + side * 82.0, y + 5.2, z + 16.0 + k * 6.0), (40.5, 0.4, 0.7))
    for k in range(-3, 4):  # the hull's ribs, under the window
        m.box("hullband" if k == 0 else "solarrib", (x + k * 15.0, y + 39.0, z + 3.0), (1.4, 6.0, 1.4), 0.4)


def astronaut(m: Model, turn: float, nod: float = 0.0) -> None:
    """An astronaut in the window: a white suit's shoulders, a round helmet with a dark visor and a small red patch,
    his head turned ``turn`` degrees (a shake left and right) and tipped ``nod`` degrees down to the ground. No one
    person's likeness."""
    if not (checks.number(turn) and -40.0 <= turn <= 40.0 and checks.number(nod) and -10.0 <= nod <= 40.0):
        raise WallError(f"his head turns -40..40 and nods -10..40 degrees, got {turn!r}, {nod!r}")
    x, y, z = WINDOW
    m.ell("suit", (x, y + 21.0, z + 10.0), (19.0, 9.0, 9.0))
    m.ell("flagred", (x - 10.0, y + 17.0, z + 1.2), (2.8, 2.0, 1.0))

    def head(s: Model) -> None:
        s.ell("suit", (0.0, 0.0, 0.0), (15.0, 15.5, 15.0))
        s.ell("visor", (0.0, 1.0, -10.0), (11.0, 8.5, 6.0))
        s.ell("bulb", (-4.0, -2.0, -15.4), (2.2, 1.4, 0.6))  # the visor's glint

    a, b = math.radians(turn), math.radians(nod)
    yaw = np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])
    pitch = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(b), -math.sin(b)], [0.0, math.sin(b), math.cos(b)]])
    _turned(m, head, yaw @ pitch, (x, y + 2.0, z + 12.0))


def yang_parts(m: Model, pose: tuple[float, float]) -> None:
    astronaut(m, *pose)


# -- the colour test ---------------------------------------------------------------------------------------------------
def wall_block(m: Model, at: Sequence[float]) -> None:
    """A short block of the wall in its stone: a course with battlements and the lines of its bricks."""
    x, y, z = (float(v) for v in at)
    m.box("wallstone", (x, y - 18.0, z), (52.0, 36.0, 20.0), 1.2)
    for k in range(6):
        m.box("wallstone", (x - 22.5 + k * 9.0, y - 40.0, z), (5.0, 8.0, 20.0), 0.6)
    for row in range(1, 6):
        m.box("hillshade", (x, y - row * 6.0, z - 10.1), (52.2, 0.5, 0.3))


def dirt(m: Model) -> None:
    """A mound of dirt of nearly the wall's colour, its pebbles pressed in."""
    x, y, z = COLOUR_AT
    m.ell("dirt", (x + 30.0, y, z + 4.0), (40.0, 40.0, 26.0))
    m.ell("dirt", (x + 56.0, y, z - 6.0), (22.0, 18.0, 18.0))
    rng = np.random.default_rng(2005)
    for _ in range(26):
        a, h = rng.uniform(-1.2, 1.2), rng.uniform(0.15, 0.85)
        px = x + 30.0 + 40.0 * math.sin(a) * math.sqrt(1 - h * h)
        m.ell("pebble", (px, y - 40.0 * h, z + 4.0 - 26.0 * math.cos(a) * math.sqrt(1 - h * h)), (1.6, 1.3, 1.4))


def colour_still(m: Model) -> None:
    """The dirt on its tray, in front of the land board and its wall."""
    board(m)
    dirt(m)
    x, y, z = COLOUR_AT
    m.box("boardedge", (x - 10.0, y - 0.6, z), (110.0, 1.2, 46.0), 0.5)  # a tray they stand on


def knife(m: Model, at: Sequence[float]) -> None:
    """A palette knife, its steel blade flat against the block's left end, its teal handle up and out to the left."""
    x, y, z = (float(v) for v in at)
    m.box("blade", (x, y - 17.0, z), (0.8, 30.0, 18.0), 0.3)
    m.capsule("blade", (x - 0.4, y - 32.0, z), (x - 9.0, y - 44.0, z), 1.0)
    m.capsule("handle", (x - 9.0, y - 44.0, z), (x - 26.0, y - 66.0, z), 3.0)


def colour_parts(m: Model, slide: float) -> None:
    """The block pushed ``slide`` model units to the right, into the dirt, by the knife at its left end."""
    if not (checks.number(slide) and 0.0 <= slide <= 40.0):
        raise WallError(f"the block slides 0 to 40 units, got {slide!r}")
    x, y, z = COLOUR_AT
    at = (x - 40.0 + slide, y, z)
    wall_block(m, at)
    knife(m, (at[0] - 26.6, y, z))


# -- the set's sounds --------------------------------------------------------------------------------------------------
SERVO = Burst(0.9, 2400.0, attack=0.08, decay=0.8, tone_hz=180.0, tone_end_hz=240.0, tone=0.6, flutter_hz=24.0)
SWITCH = Burst(0.05, 7000.0, attack=0.001, decay=0.2, tone_hz=1800.0, tone_end_hz=1400.0, tone=0.4)  # the lamp
SCRAPE = Burst(1.2, 1800.0, attack=0.05, decay=0.9, tone_hz=140.0, tone_end_hz=120.0, tone=0.15, flutter_hz=11.0)
