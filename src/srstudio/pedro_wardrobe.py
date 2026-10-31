"""Pedro's clothes: a navy quilted jacket over a black T-shirt, with a padded stand collar (ADR 0072).

The jacket is one implicit shell, so shoulder, sleeve and chest cannot read as separate pieces. :func:`contour` takes
the surface of such a field by marching tetrahedra, a dozen lines of array code, so the library takes no meshing
dependency for him. Only what a head-and-chest frame shows is here: his trousers, shoes and hands are not.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

from .clay import ClayError, Model

__all__ = ["body", "contour", "jacket"]

_TETS = ((0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7), (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7))
_EPS = 0.045  # how far apart the field is read for a surface normal
Field = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


def _table() -> dict[int, list[tuple[tuple[int, int], ...]]]:
    """For each inside-corner mask of a tetrahedron, its triangles as triples of crossed edges."""
    table: dict[int, list[tuple[tuple[int, int], ...]]] = {}
    for mask in range(1, 15):
        inside = [i for i in range(4) if mask >> i & 1]
        outside = [i for i in range(4) if not mask >> i & 1]
        if len(inside) == 2:
            a, b = inside
            c, d = outside
            table[mask] = [((a, c), (a, d), (b, d)), ((a, c), (b, d), (b, c))]
        else:
            lone, rest = (inside[0], outside) if len(inside) == 1 else (outside[0], inside)
            table[mask] = [tuple((lone, other) for other in rest)]
    return table


def contour(fn: Field, bounds: Sequence[tuple[float, float]], step: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The zero surface of ``fn`` inside ``bounds``, as ``vertices, normals, triangles``, facing up the field."""
    axes = [np.arange(lo, hi + step, step) for lo, hi in bounds]
    nx, ny, nz = (len(axis) for axis in axes)
    x, y, z = np.meshgrid(*axes, indexing="ij")
    values = fn(x, y, z).ravel()
    i, j, k = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), np.arange(nz - 1), indexing="ij")
    origin = (i * ny * nz + j * nz + k).ravel()
    corner = np.array([(c & 1) * ny * nz + (c >> 1 & 1) * nz + (c >> 2 & 1) for c in range(8)])
    keys: list[np.ndarray] = []
    for tet in _TETS:
        at = origin[:, None] + corner[list(tet)]
        masks = ((values[at] < 0.0) * (1 << np.arange(4))).sum(axis=1)
        for mask, triangles in _table().items():
            hit = at[masks == mask]
            for triangle in triangles:
                edges = [np.sort(hit[:, list(edge)], axis=1) for edge in triangle]
                keys.append(np.stack([e[:, 0] * values.size + e[:, 1] for e in edges], axis=1))
    if not any(len(rows) for rows in keys):
        raise ClayError("this field has no surface inside its bounds")
    unique, inverse = np.unique(np.concatenate(keys), return_inverse=True)
    triangles_ = inverse.reshape(-1, 3)
    lo, hi = unique // values.size, unique % values.size
    t = values[lo] / (values[lo] - values[hi])
    grid = np.stack((x.ravel(), y.ravel(), z.ravel()), axis=1)
    verts = grid[lo] + (grid[hi] - grid[lo]) * t[:, None]
    normals = np.zeros_like(verts)
    for axis in range(3):
        plus, minus = verts.copy(), verts.copy()
        plus[:, axis] += _EPS
        minus[:, axis] -= _EPS
        normals[:, axis] = fn(*plus.T) - fn(*minus.T)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
    faces = np.cross(
        verts[triangles_[:, 1]] - verts[triangles_[:, 0]], verts[triangles_[:, 2]] - verts[triangles_[:, 0]]
    )
    flip = (faces * normals[triangles_].mean(axis=1)).sum(axis=1) < 0.0
    triangles_[flip] = triangles_[flip][:, ::-1]
    return verts, normals, triangles_


def _ball(x, y, z, c: Sequence[float], r: Sequence[float]) -> np.ndarray:
    q = ((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2
    return (np.sqrt(q) - 1.0) * min(r)


def _capsule(x, y, z, a: Sequence[float], b: Sequence[float], r: float) -> np.ndarray:
    v = np.array(b, float) - np.array(a, float)
    ax, ay, az = x - a[0], y - a[1], z - a[2]
    t = np.clip((ax * v[0] + ay * v[1] + az * v[2]) / np.dot(v, v), 0.0, 1.0)
    return np.sqrt((ax - v[0] * t) ** 2 + (ay - v[1] * t) ** 2 + (az - v[2] * t) ** 2) - r


def _union(a, b, k: float) -> np.ndarray:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _outer(x, y, z) -> np.ndarray:
    """A broad chest and softly padded shoulders, merging into bent sleeves, with shallow quilt channels."""
    d = _ball(x, y, z, (0, -110, 1), (24.2, 35, 13.2))
    d = _union(d, _ball(x, y, z, (0, -91, 1), (22, 16, 12.8)), 3)
    for side in (-1, 1):
        d = _union(d, _ball(x, y, z, (side * 20, -129, 1), (11, 11, 12.5)), 3)
        d = _union(d, _capsule(x, y, z, (side * 25, -128, 1), (side * 33, -108, 1), 8.5), 3)
        d = _union(d, _capsule(x, y, z, (side * 33, -108, 1), (side * 31, -79, -3), 6.2), 3)
    return d - 0.55 * (1.0 - np.cos((y + 79) * math.tau / 12))


def _gap(y) -> np.ndarray:
    """How far the jacket stands open at height ``y``."""
    return np.interp(y, (-146, -140, -132, -120, -77), (6.8, 8.3, 7.0, 3.4, 2.8))


def jacket(x, y, z) -> np.ndarray:
    """The jacket as a field: the shell, open down the front and round the neck, cut off at the hem."""
    d = _outer(x, y, z)
    d = np.maximum(d, -np.maximum(np.abs(x) - _gap(y), z + 3.3))
    d = np.maximum(d, -np.maximum(np.sqrt(x * x + (z - 1.0) ** 2) - 8.75, y + 137.0))
    return np.maximum(d, y + 78.0)


def _on_jacket(xs: np.ndarray, ys: np.ndarray, near: float = -24.0, far: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """The z of the jacket's outer surface at each ``x, y``, coming from the lens, and whether it has one there."""
    depths = np.linspace(near, far, 100)
    values = _outer(xs[:, None], ys[:, None], depths[None, :])
    crossed = (values[:, :-1] > 0.0) & (values[:, 1:] <= 0.0)
    found = crossed.any(axis=1)
    first = crossed.argmax(axis=1)
    lo, hi = depths[first], depths[first + 1]
    for _ in range(24):
        mid = (lo + hi) / 2.0
        outside = _outer(xs, ys, mid) > 0.0
        lo, hi = np.where(outside, mid, lo), np.where(outside, hi, mid)
    return (lo + hi) / 2.0, found


def _collar(m: Model) -> None:
    ends = (0.75, math.tau - 0.75)
    ts = np.linspace(*ends, 90)
    around = np.linspace(0.0, math.tau, 24, endpoint=False)
    rad = 1.20 * np.sign(np.cos(around)) * np.abs(np.cos(around)) ** 0.4
    tall = 4.10 * np.sign(np.sin(around)) * np.abs(np.sin(around)) ** 0.4
    x = (9.8 + rad[None, :]) * np.sin(ts)[:, None]
    z = 1.0 - (8.7 + rad[None, :]) * np.cos(ts)[:, None]
    y = np.broadcast_to(-139.5 + tall, x.shape)
    rows = np.stack((x, y, z), axis=2)
    middle = np.stack((9.8 * np.sin(ts), np.full(len(ts), -139.5), 1.0 - 8.7 * np.cos(ts)), axis=1)
    normals = rows - middle[:, None, :]
    normals /= np.maximum(np.linalg.norm(normals, axis=2, keepdims=True), 1e-9)
    tris = []
    for r in range(len(ts) - 1):
        for c in range(len(around)):
            a, b = r * len(around) + c, r * len(around) + (c + 1) % len(around)
            tris += [(a, b, b + len(around)), (a, b + len(around), a + len(around))]
    m.surface("nylon", rows.reshape(-1, 3), normals.reshape(-1, 3), tris)
    for t in ends:
        m.ell("nylon", (9.8 * math.sin(t), -139.5, 1.0 - 8.7 * math.cos(t)), (1.21, 4.10, 1.21))


def _seams(m: Model) -> None:
    for side in (-1.0, 1.0):
        ys = np.linspace(-139.0, -79.0, 45)
        xs = side * (_gap(ys) + 0.10)
        zs, found = _on_jacket(xs, ys)
        edge = np.stack((xs, ys, zs - 0.10), axis=1)[found]
        m.tube("jacket-edge", edge, 0.20, 60, 6)
        if side > 0:
            for p in edge[4:]:
                m.tube("zip", ((p[0] - 0.13, p[1], p[2] - 0.12), (p[0] + 0.21, p[1], p[2] - 0.12)), 0.07, 2, 4)
        for y in (-127.0, -115.0, -103.0, -91.0, -80.5):
            across = side * np.linspace(float(_gap(y)) + 0.5, 39.0, 42)
            zs, found = _on_jacket(across, np.full(len(across), y), far=0.0)
            line = np.stack((across, np.full(len(across), y), zs - 0.11), axis=1)[found]
            if len(line) > 3:
                m.tube("jacket-shadow", line, 0.085, 48, 5)
                m.tube("stitch", line + (0.0, 0.16, 0.0), 0.032, 48, 4)
        ys = np.linspace(-107.0, -94.0, 12)
        pocket = side * (15.5 - (ys + 107.0) * 0.10)
        zs, found = _on_jacket(pocket, ys, far=0.0)
        m.tube("jacket-shadow", np.stack((pocket, ys, zs - 0.12), axis=1)[found], 0.15, 22, 6)


def body(m: Model) -> None:
    """Everything of him below the head: a neck, the tee, the jacket, its zip, seams and collar."""
    m.ell("skin", (0, -143, 1), (9.2, 11.5, 8.6))
    m.ell("shirt", (0, -109, 1), (22.3, 32.5, 11.9))
    m.tube("shirt", [(9 * math.sin(t), -137.0, 1 - 8.5 * math.cos(t)) for t in np.linspace(-1.4, 1.4, 20)], 0.35, 32, 7)
    verts, normals, tris = contour(jacket, ((-44, 44), (-146, -76), (-19, 20)), 1.06)
    m.surface("nylon", verts, normals, tris)
    _seams(m)
    _collar(m)
