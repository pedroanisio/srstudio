"""Pedro's sculpt: the head as one continuous field, and the surfaces laid on it (ADR 0072).

The numbers start as the sculpt's and are corrected by eye: the head is 50 tall, y runs down from the crown, z runs away
from the lens. :func:`front` is the face as a height over x and y, the place every lip, brow and goatee stroke is laid.
The skin is the outer surface of :func:`field`, seen from inside the head and laid out on a fixed grid (:func:`grid`). A
grid and not a voxel extraction, because speech needs one skin whose vertices stay the same vertices in every state: an
open mouth moves them, it does not remesh them.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

import numpy as np

__all__ = ["CENTRE", "COLS", "ROWS", "field", "front", "grid", "lay", "stream", "strokes", "tube", "width"]

_YS = np.array((0, 2, 5, 9, 15, 20, 25, 30, 35, 40, 44, 47, 49, 50), float)
_WIDE = (0.08, 9.2, 14.4, 17.0, 17.9, 18.4, 19.0, 18.9, 17.9, 16.4, 14.5, 11.7, 7.0, 0.08)
_FORE = (0.08, 7.4, 12.2, 14.0, 14.0, 13.4, 12.7, 12.8, 12.5, 12.2, 11.8, 10.2, 6.0, 0.08)
_BACK = (0.08, 7.6, 12.0, 14.0, 14.7, 14.7, 14.2, 12.8, 10.0, 7.0, 5.2, 3.6, 1.8, 0.08)
CENTRE = np.array((0.0, 27.0, 0.0))  # the skin is star-shaped about this point
ROWS, COLS = 361, 441
_FACE_ROWS = (0.6, 2.75, 7.0)  # polar angles the face runs between, and how much denser its rows are than the rest
_OUTSIDE, _STEP, _BISECTIONS = 40.0, 0.8, 16


def _slopes(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """The slope at each knot of a monotone cubic: never past the data, so the head has no bulge the sculpt lacks."""
    h, delta = np.diff(xs), np.diff(ys) / np.diff(xs)
    out = np.zeros(len(xs))
    for k in range(1, len(xs) - 1):
        if delta[k - 1] * delta[k] > 0.0:
            w1, w2 = 2.0 * h[k] + h[k - 1], h[k] + 2.0 * h[k - 1]
            out[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    def edge(h0: float, h1: float, d0: float, d1: float) -> float:
        d = ((2.0 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if d * d0 <= 0.0:
            return 0.0
        return 3.0 * d0 if d0 * d1 <= 0.0 and abs(d) > 3.0 * abs(d0) else d

    out[0], out[-1] = edge(h[0], h[1], delta[0], delta[1]), edge(h[-1], h[-2], delta[-1], delta[-2])
    return out


def _profile(values: Sequence[float]):
    ys = np.array(values, float)
    slopes = _slopes(_YS, ys)

    def at(y) -> np.ndarray:
        y = np.asarray(y, float)
        k = np.clip(np.searchsorted(_YS, y, side="right") - 1, 0, len(_YS) - 2)
        h = _YS[k + 1] - _YS[k]
        t = (y - _YS[k]) / h
        return (
            (2 * t**3 - 3 * t**2 + 1) * ys[k]
            + (t**3 - 2 * t**2 + t) * h * slopes[k]
            + (-2 * t**3 + 3 * t**2) * ys[k + 1]
            + (t**3 - t**2) * h * slopes[k + 1]
        )

    return at


width, _fore, _back = _profile(_WIDE), _profile(_FORE), _profile(_BACK)


def _g(x, y, cx: float, cy: float, sx: float, sy: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - cx) / sx) ** 2 - 0.5 * ((y - cy) / sy) ** 2)


def front(x, y) -> np.ndarray:
    """The z of the face at ``x, y``: the sculpt's sockets, brow ridge, cheeks, nose and chin on its outline."""
    x = np.asarray(x, float)
    y = np.clip(np.asarray(y, float), 0.001, 49.999)
    q = np.minimum(0.99999, np.abs(x) / width(y))
    base = -_fore(y) * (1.0 - q * q) ** 0.36
    z = base.copy()
    for side in (-1.0, 1.0):
        z = z + 1.3 * _g(x, y, side * 7.6, 24.1, 4.4, 2.8)  # eyes set deep
        z = z - 1.7 * _g(x, y, side * 7.7, 19.4, 5.0, 1.5)  # under a strong ridge
        z = z - 1.45 * _g(x, y, side * 11.5, 27.8, 4.0, 2.8)  # cheekbones
        z = z + 0.8 * _g(x, y, side * 13.2, 36.4, 3.4, 3.4)  # and the hollow under them
        z = z - 0.25 * _g(x, y, side * 10.0, 34, 4.2, 3.2)
        z = z - 0.15 * _g(x, y, side * 12.8, 41, 3.2, 3.0)
        z = z - 0.32 * _g(x, y, side * 7.7, 22.4, 4.2, 0.7)  # the fold that hoods the eye
        z = z - 0.14 * _g(x, y, side * 7.7, 26.5, 3.8, 0.75)  # a soft bag under it
        z = z + 0.07 * _g(x, y, side * 8.0, 27.7, 4.6, 0.32)
    z = z - 1.35 * _g(x, y, 0, 27.6, 2.2, 5.0)  # a straight bridge
    z = z - 1.7 * _g(x, y, 0, 33.0, 3.4, 2.2)  # to a broad tip
    z = z + 0.32 * _g(x, y, 0, 36.2, 2.0, 0.6)
    z = z - 0.75 * _g(x, y, 0, 38.5, 6.0, 3.0) - 1.3 * _g(x, y, 0, 45.7, 7.0, 3.1)
    for side in (-1.0, 1.0):
        z = z + 0.20 * _g(x, y, side * 1.25, 20.1, 0.36, 1.55)
    return base + (z - base) * (1.0 - q * q) ** 0.35


def lay(x, y, off=0.0) -> np.ndarray:
    """Points on the face at ``x, y``, ``off`` towards the lens, as ``(..., 3)``."""
    xs, ys, offs = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(off, float))
    return np.stack((xs, ys, front(xs, ys) - offs), axis=-1)


def _ball(x, y, z, c: Sequence[float], r: Sequence[float]) -> np.ndarray:
    q = ((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2
    return (np.sqrt(q) - 1.0) * min(r)


def _union(a, b, k: float) -> np.ndarray:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _nose(x, y, z) -> np.ndarray:
    d = _ball(x, y, z, (0, 27.4, -13.6), (2.9, 7.2, 2.5))
    d = _union(d, _ball(x, y, z, (0, 32.9, -15.0), (3.6, 2.3, 2.9)), 1.6)
    for side in (-1, 1):
        d = _union(d, _ball(x, y, z, (side * 3.7, 33.9, -14.7), (1.8, 1.3, 1.9)), 0.85)
    return d


def field(x, y, z) -> np.ndarray:
    """Below 0 inside his head: the outline, the face on it and the nose, melted together."""
    x, y, z = np.asarray(x, float), np.asarray(y, float), np.asarray(z, float)
    yc = np.clip(y, 0.001, 49.999)
    rx, fd, bd = width(yc), _fore(yc), _back(yc)
    q = np.minimum(0.99999, np.abs(x) / rx)
    delta = front(x, yc) + fd * (1.0 - q * q) ** 0.36
    depth = np.where(z < 0, fd, bd)
    height = np.where(z < 0, np.maximum(0.0, -z + delta), np.maximum(z, 0.0))
    radial = (x / rx) ** 2 + (height / depth) ** np.where(z < 0, 1.0 / 0.36, 1.0 / 0.41)
    base = (np.sqrt(radial) - 1.0) * np.minimum(rx, depth)
    base = np.maximum(base, np.maximum(-y, y - 50.0))
    return _union(base, _nose(x, y, z), 1.35)


def _radius(directions: np.ndarray) -> np.ndarray:
    """How far from :data:`CENTRE` the head ends along each unit direction: the last crossing, coming from outside."""
    far = np.full(len(directions), _OUTSIDE)
    near = far.copy()
    active = np.arange(len(directions))
    t = _OUTSIDE
    while len(active) and t > 0.0:
        t -= _STEP
        p = CENTRE + directions[active] * t
        inside = field(p[:, 0], p[:, 1], p[:, 2]) <= 0.0
        near[active[inside]] = t
        far[active[inside]] = t + _STEP
        active = active[~inside]
    for _ in range(_BISECTIONS):
        mid = (near + far) / 2.0
        p = CENTRE + directions * mid[:, None]
        inside = field(p[:, 0], p[:, 1], p[:, 2]) <= 0.0
        near, far = np.where(inside, mid, near), np.where(inside, far, mid)
    return (near + far) / 2.0


def _polar() -> np.ndarray:
    """The polar angle of each row, from the crown: rows crowd into the face, where the mouth must cut clean."""
    start, stop, dense = _FACE_ROWS
    fine = np.linspace(0.0, math.pi, 8001)
    density = np.where((fine > start) & (fine < stop), dense, 1.0)
    total = np.concatenate(([0.0], np.cumsum((density[1:] + density[:-1]) / 2.0)))
    return np.interp(np.linspace(0.0, total[-1], ROWS), total, fine)


@lru_cache(maxsize=1)
def grid() -> tuple[np.ndarray, np.ndarray]:
    """The skin at rest: its ``ROWS * COLS`` points and its triangles. Most columns face the lens."""
    u = np.linspace(-1.0, 1.0, COLS)
    around = math.pi * (0.32 * u + 0.68 * u**3)
    polar = _polar()
    sin = np.sin(polar)[:, None]
    directions = np.stack(
        (sin * np.sin(around)[None, :], -np.cos(polar)[:, None] * np.ones(COLS), -sin * np.cos(around)[None, :]), axis=2
    ).reshape(-1, 3)
    points = CENTRE + directions * _radius(directions)[:, None]
    a = (np.arange(ROWS - 1)[:, None] * COLS + np.arange(COLS - 1)[None, :]).ravel()
    tris = np.concatenate((np.stack((a, a + 1, a + COLS + 1), 1), np.stack((a, a + COLS + 1, a + COLS), 1)))
    return points, tris


def stream(seed: int, count: int) -> np.ndarray:
    """``count`` numbers in [0, 1), the same on every build and every numeric library: a splitmix counter."""
    gamma = 0x9E3779B97F4A7C15
    z = np.uint64((seed + 1) * gamma & (1 << 64) - 1) + np.arange(1, count + 1, dtype=np.uint64) * np.uint64(gamma)
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    z = z ^ (z >> np.uint64(31))
    return (z >> np.uint64(11)).astype(float) / float(1 << 53)


def tube(points: np.ndarray, radii, n: int = 5, sides: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """A thin tapered hair along the Bezier of ``points``: its vertices and its normals, ``n`` rings of ``sides``."""
    p = np.asarray(points, float)
    s = np.linspace(0.0, 1.0, n)
    samples = []
    for t in s:
        q = p.copy()
        while len(q) > 1:
            q = q[:-1] * (1.0 - t) + q[1:] * t
        samples.append(q[0])
    centres = np.array(samples)
    tangent = np.gradient(centres, axis=0)
    tangent = tangent / np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    side = np.cross(tangent, (0.0, 0.0, 1.0))
    bad = np.linalg.norm(side, axis=1) < 0.2
    side[bad] = np.cross(tangent[bad], (1.0, 0.0, 0.0))
    side = side / np.linalg.norm(side, axis=1, keepdims=True)
    other = np.cross(tangent, side)
    r = np.interp(s, np.linspace(0.0, 1.0, len(radii)), radii) if np.ndim(radii) else np.full(n, float(radii))
    angles = np.linspace(0.0, math.tau, sides, endpoint=False)
    rings = np.cos(angles)[None, :, None] * side[:, None, :] + np.sin(angles)[None, :, None] * other[:, None, :]
    return (centres[:, None, :] + rings * r[:, None, None]).reshape(-1, 3), rings.reshape(-1, 3)


def strokes(
    items: Sequence[tuple[np.ndarray, np.ndarray]], n: int, sides: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Many :func:`tube` hairs as one mesh's ``vertices, normals, triangles``."""
    tri = []
    for j in range(n - 1):
        for i in range(sides):
            a, b = j * sides + i, j * sides + (i + 1) % sides
            tri += [(a, b, b + sides), (a, b + sides, a + sides)]
    one = np.array(tri)
    size = n * sides
    return (
        np.concatenate([v for v, _ in items]),
        np.concatenate([w for _, w in items]),
        np.concatenate([one + k * size for k in range(len(items))]),
    )
