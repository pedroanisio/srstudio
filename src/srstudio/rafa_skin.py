"""Rafa's skin: one continuous clay surface for his head (ADR 0068).

A head built from separate balls shows every join, which is what a cheek stuck on as a disc is. Here the balls are only
the armature: :data:`_BLOBS` are blended into one field, and the skin is that field's outer surface, seen from a point
inside his head and laid out on a grid. Pressed marks are :class:`Dent` displacements of the surface. Nothing rests on
the surface's order or on a random stream, so the same call gives the same bytes on every build.

The skin carries its colour as a picture with a pixel per grid point: blush, the shade under his eyes and his stubble
are painted on the clay and not stuck on it. :func:`front` says how far towards the lens the skin comes at a place on
his face, so that lips, brows and lashes can be laid on it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .plates import Texture

__all__ = ["CENTRE", "Cavity", "Dent", "Point3", "front", "paint", "sheet"]

Point3 = tuple[float, float, float]

CENTRE = np.array((0.0, -352.0, -4.0))  # his skin is star-shaped about this point
ROWS, COLS = 241, 421
_BLEND = 2.4  # how far apart two balls start to melt into each other
_OUTSIDE, _STEP, _BISECTIONS = 96.0, 3.0, 9
_BLOBS = (  # centre, radii: the armature of his head, in the study's units
    ((0.0, -359.0, 0.0), (51.0, 65.0, 43.0)),  # the jaw and the cranium
    ((0.0, -330.0, -7.0), (39.0, 35.0, 35.0)),  # the chin
    ((-29.0, -345.0, -24.0), (17.0, 12.0, 11.0)),  # the cheeks
    ((29.0, -345.0, -24.0), (17.0, 12.0, 11.0)),
    ((0.0, -358.0, -43.0), (7.5, 18.0, 11.0)),  # the bridge of the nose
    ((0.0, -347.0, -51.0), (13.5, 9.0, 13.0)),  # the ball of the nose
    ((-11.0, -344.5, -45.0), (5.5, 5.0, 7.0)),  # its wings
    ((11.0, -344.5, -45.0), (5.5, 5.0, 7.0)),
    ((-17.0, -386.0, -37.0), (15.0, 5.5, 5.0)),  # the ridge of his brows
    ((17.0, -386.0, -37.0), (15.0, 5.5, 5.0)),
    ((-20.0, -355.0, -39.0), (12.5, 3.2, 4.4)),  # the bags under his eyes
    ((20.0, -355.0, -39.0), (12.5, 3.2, 4.4)),
    ((0.0, -323.0, -33.0), (21.0, 14.0, 8.0)),  # the muzzle the mouth sits on
)
_SIZES = np.array([size for _, size in _BLOBS])
_WEIGHT = _SIZES.min(axis=1)
_AT = np.array([at for at, _ in _BLOBS])


@dataclass(frozen=True)
class Dent:
    """A press into the skin of ``depth`` at ``at``, fading to nothing at ``reach`` on each axis."""

    at: tuple[float, float, float]
    reach: tuple[float, float, float]
    depth: float


@dataclass(frozen=True)
class Cavity:
    """The inside of an open mouth: ``xs`` along it, its ``top`` and ``bottom`` lines there, how far back it runs."""

    xs: tuple[float, ...]
    top: tuple[float, ...]
    bottom: tuple[float, ...]
    depth: float


_FOREVER = (  # his sockets, the crease under his bags, nostrils, philtrum, the hollow of his temples
    Dent((-20.0, -370.0, -46.0), (19.0, 14.0, 14.0), 3.6),
    Dent((20.0, -370.0, -46.0), (19.0, 14.0, 14.0), 3.6),
    Dent((-20.0, -350.5, -42.0), (14.0, 2.4, 8.0), 0.6),
    Dent((20.0, -350.5, -42.0), (14.0, 2.4, 8.0), 0.6),
    Dent((-6.5, -340.0, -58.0), (3.2, 2.2, 8.0), 2.6),
    Dent((6.5, -340.0, -58.0), (3.2, 2.2, 8.0), 2.6),
    Dent((0.0, -334.0, -46.0), (2.6, 5.0, 9.0), 0.8),
    Dent((-46.0, -384.0, -12.0), (10.0, 16.0, 16.0), 1.5),
    Dent((46.0, -384.0, -12.0), (10.0, 16.0, 16.0), 1.5),
)


def _field(points: np.ndarray) -> np.ndarray:
    """Below 0 inside him: the balls of :data:`_BLOBS`, melted together."""
    rel = (points[:, None, :] - _AT) / _SIZES
    distance = (np.sqrt((rel * rel).sum(axis=2)) - 1.0) * _WEIGHT
    return -_BLEND * np.log(np.exp(np.clip(-distance / _BLEND, -60.0, 60.0)).sum(axis=1))


def _radius(directions: np.ndarray) -> np.ndarray:
    """How far from :data:`CENTRE` the armature ends along each unit direction."""
    far = np.full(len(directions), _OUTSIDE)
    near = far.copy()
    active = np.arange(len(directions))
    t = _OUTSIDE
    while len(active) and t > 0.0:
        t -= _STEP
        inside = _field(CENTRE + directions[active] * t) <= 0.0
        near[active[inside]] = t
        far[active[inside]] = t + _STEP
        active = active[~inside]
    for _ in range(_BISECTIONS):
        mid = (near + far) / 2.0
        inside = _field(CENTRE + directions * mid[:, None]) <= 0.0
        near, far = np.where(inside, mid, near), np.where(inside, far, mid)
    return (near + far) / 2.0


def _dents(points: np.ndarray, dents: Sequence[Dent]) -> np.ndarray:
    out = np.zeros(len(points))
    for dent in dents:
        rel = (points - np.array(dent.at)) / np.array(dent.reach)
        fade = np.clip(1.0 - (rel * rel).sum(axis=1), 0.0, 1.0)
        out -= dent.depth * fade * fade * (3.0 - 2.0 * fade)
    return out


def _recess(points: np.ndarray, cavity: Cavity | None) -> np.ndarray:
    if cavity is None:
        return np.zeros(len(points))
    x, y = points[:, 0], points[:, 1]
    xs = np.array(cavity.xs)
    edge = np.minimum(
        (xs[-1] - np.abs(x)), np.minimum(y - np.interp(x, xs, cavity.top), np.interp(x, xs, cavity.bottom) - y)
    )
    grow = np.clip(edge / 2.0, 0.0, 1.0)
    return -cavity.depth * grow * grow * (3.0 - 2.0 * grow) * (points[:, 2] < CENTRE[2] - 10.0)


_BUMPS = tuple(  # direction, wavelength, height: thumb marks, then the finer marks of a tool
    (
        np.array(
            (
                math.sin(a * 2.399) * math.sqrt(1.0 - (2.0 * (a + 0.5) / 18.0 - 1.0) ** 2),
                2.0 * (a + 0.5) / 18.0 - 1.0,
                math.cos(a * 2.399) * math.sqrt(1.0 - (2.0 * (a + 0.5) / 18.0 - 1.0) ** 2),
            )
        ),
        (9.0 if a % 3 == 0 else 15.0) if a < 12 else 2.7 + (a % 3) * 0.5,
        (0.03 if a < 12 else 0.012),
        a * 1.7,
    )
    for a in range(18)
)


def _thumbed(points: np.ndarray) -> np.ndarray:
    """The hand-made surface: a deterministic sum of waves, so that a fingerprint survives a numeric library."""
    out = np.zeros(len(points))
    for direction, wavelength, height, phase in _BUMPS:
        out += height * np.sin(points @ direction * math.tau / wavelength + phase)
    return out


def _on(points: np.ndarray, dents: Sequence[Dent], cavity: Cavity | None) -> np.ndarray:
    return _dents(points, (*_FOREVER, *dents)) + _recess(points, cavity)


@lru_cache(maxsize=1)
def _grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The unit directions of the grid, its armature radius and its armature points: most columns face the lens."""
    u = np.linspace(-1.0, 1.0, COLS)
    around = math.pi * (0.35 * u + 0.65 * u**3)
    polar = np.linspace(0.0, math.pi, ROWS)
    sin = np.sin(polar)[:, None]
    directions = np.stack(
        (sin * np.sin(around)[None, :], -np.cos(polar)[:, None] * np.ones(COLS), -sin * np.cos(around)[None, :]), axis=2
    ).reshape(-1, 3)
    radius = _radius(directions)
    return directions, radius, CENTRE + directions * radius[:, None]


def sheet(dents: Sequence[Dent] = (), cavity: Cavity | None = None):
    """His skin as ``vertices, normals, triangles, uvs``, marked with ``dents`` and an open mouth's ``cavity``."""
    directions, radius, armature = _grid()
    moved = radius + _on(armature, dents, cavity) + _thumbed(armature)
    verts = CENTRE + directions * moved[:, None]
    grid = verts.reshape(ROWS, COLS, 3)
    down = np.gradient(grid, axis=0)
    along = np.gradient(grid, axis=1)
    normals = np.cross(along, down).reshape(-1, 3)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(length > 1e-9, normals / np.maximum(length, 1e-9), directions)
    flip = (normals * directions).sum(axis=1) < 0.0
    normals[flip] *= -1.0
    a = (np.arange(ROWS - 1)[:, None] * COLS + np.arange(COLS - 1)[None, :]).ravel()
    tris = np.concatenate((np.stack((a, a + 1, a + COLS + 1), 1), np.stack((a, a + COLS + 1, a + COLS), 1)))
    v, w = np.meshgrid(1.0 - np.arange(ROWS) / (ROWS - 1), np.arange(COLS) / (COLS - 1), indexing="ij")
    return verts, normals, tris, np.stack((w, v), axis=2).reshape(-1, 2)


def front(x, y, dents: Sequence[Dent] = ()) -> np.ndarray:
    """How far towards the lens his skin comes at ``x, y``: the z of the surface, with its ``dents``."""
    xs, ys = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = np.full(xs.shape, -40.0)
    for _ in range(14):
        rel = np.stack((xs.ravel(), ys.ravel(), z.ravel()), axis=1) - CENTRE
        reach = np.linalg.norm(rel, axis=1)
        directions = rel / reach[:, None]
        radius = _radius(directions)
        radius += _on(CENTRE + directions * radius[:, None], dents, None)
        z = (CENTRE[2] + rel[:, 2] * radius / reach).reshape(xs.shape)
    return z


def _rgb(color: str) -> np.ndarray:
    return np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)], float)


def _spot(points: np.ndarray, at: Sequence[float], reach: Sequence[float]) -> np.ndarray:
    rel = (points - np.array(at)) / np.array(reach)
    return np.exp(-(rel * rel).sum(axis=1))[:, None]


def paint(palette: dict[str, str]) -> Texture:
    """The colours on his clay, smooth, one pixel a grid point. ``palette`` names his skin's tones."""
    _, _, points = _grid()
    out = np.tile(_rgb(palette["skin"]), (len(points), 1))

    def lay(color: str, amount: np.ndarray) -> None:
        nonlocal out
        share = np.clip(amount, 0.0, 1.0)
        out = out * (1.0 - share) + _rgb(color) * share

    for side in (-1.0, 1.0):
        lay(palette["blush"], 0.42 * _spot(points, (side * 30.0, -345.0, -30.0), (17.0, 12.0, 16.0)))
        lay(palette["shade"], 0.5 * _spot(points, (side * 20.0, -352.5, -40.0), (14.0, 3.8, 10.0)))
        lay(palette["shade"], 0.22 * _spot(points, (side * 20.0, -372.0, -40.0), (15.0, 9.0, 12.0)))
        lay(palette["deep"], 0.8 * _spot(points, (side * 6.5, -340.5, -52.0), (2.8, 1.7, 7.0)))
    lay(palette["light"], 0.75 * _spot(points, (0.0, -350.0, -58.0), (13.0, 13.0, 12.0)))
    lay(palette["light"], 0.3 * _spot(points, (0.0, -398.0, -36.0), (26.0, 10.0, 12.0)))
    jaw = np.clip((points[:, 1:2] + (334.0, 0.0))[:, 0] / 26.0, 0.0, 1.0)[:, None]
    away = 1.0 - _spot(points, (0.0, -326.0, -44.0), (21.0, 13.0, 12.0))
    lay(palette["stubble"], 0.2 * jaw * away)
    rows = np.empty((ROWS, COLS, 4), np.uint8)
    rows[..., :3] = np.round(out.reshape(ROWS, COLS, 3))
    rows[..., 3] = 255
    return Texture(rows)
