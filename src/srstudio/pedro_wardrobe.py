"""Pedro's clothes: a navy blazer over a black crew-neck tee, the tee alone, or a quilted puffer (ADR 0072).

Each coat is one implicit shell, so shoulder, sleeve and chest cannot read as separate pieces. :func:`contour` takes
the surface of such a field by marching tetrahedra, a dozen lines of array code, so the library takes no meshing
dependency for him. Only what a head-and-chest frame shows is here: his trousers, shoes and hands are not.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

from .clay import ClayError, Model, first_caps

__all__ = ["blazer", "body", "contour", "jacket", "puffer", "tee"]

_TETS = ((0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7), (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7))
_EPS = 0.045  # how far apart the field is read for a surface normal
_NECK_HOLE = 10.2  # the radius of the jacket's neck
_NECK_Z, _NECK_DEEP = 2.5, 1.05  # where the neck's opening sits, and how much deeper it is than wide
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


def _shell(x, y, z) -> np.ndarray:
    """A broad chest and softly padded shoulders, merging into bent sleeves."""
    d = _ball(x, y, z, (0, -110, 1), (24.2, 35, 13.2))
    d = _union(d, _ball(x, y, z, (0, -91, 1), (22, 16, 12.8)), 3)
    d = _union(d, _ball(x, y, z, (0, -124, 5), (19, 13, 10.5)), 4)  # the yoke, rising to the collar across his back
    for side in (-1, 1):
        d = _union(d, _ball(x, y, z, (side * 20, -129, 1), (11, 11, 12.5)), 3)
        d = _union(d, _capsule(x, y, z, (side * 25, -128, 1), (side * 33, -108, 1), 8.5), 3)
        d = _union(d, _capsule(x, y, z, (side * 33, -108, 1), (side * 31, -79, -3), 6.2), 3)
    return d


def _padded(x, y, z) -> np.ndarray:
    """The shell quilted: full baffles that pinch in at each channel, and the nylon creasing a little over them."""
    creases = 0.11 * np.sin(1.1 * x + 0.4 * y) * np.cos(0.8 * y - 0.5 * x + 0.6 * z)
    return _shell(x, y, z) - 0.85 * np.abs(np.sin((y + 79) * np.pi / 12)) ** 0.7 + creases


def _gap(y) -> np.ndarray:
    """How far the jacket stands open at height ``y``."""
    return np.interp(y, (-146, -140, -132, -120, -77), (6.8, 8.3, 7.0, 3.4, 2.8))


def jacket(x, y, z) -> np.ndarray:
    """The jacket as a field: the shell, open down the front and round the neck, cut off at the hem."""
    d = _padded(x, y, z)
    d = np.maximum(d, -np.maximum(np.abs(x) - _gap(y), z + 3.3))
    d = np.maximum(d, -np.maximum(np.hypot(x, (z - _NECK_Z) / _NECK_DEEP) - _NECK_HOLE, y + 135.0))
    return np.maximum(d, y + 78.0)


def _on_jacket(
    xs: np.ndarray, ys: np.ndarray, near: float = -24.0, far: float = 1.0, shell: Field | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """The z of a coat's outer surface at each ``x, y``, coming from the lens, and whether it has one there."""
    surface = _padded if shell is None else shell
    depths = np.linspace(near, far, 100)
    values = surface(xs[:, None], ys[:, None], depths[None, :])
    crossed = (values[:, :-1] > 0.0) & (values[:, 1:] <= 0.0)
    found = crossed.any(axis=1)
    first = crossed.argmax(axis=1)
    lo, hi = depths[first], depths[first + 1]
    for _ in range(24):
        mid = (lo + hi) / 2.0
        outside = surface(xs, ys, mid) > 0.0
        lo, hi = np.where(outside, mid, lo), np.where(outside, hi, mid)
    return (lo + hi) / 2.0, found


def _collar(m: Model) -> None:
    """The high stand collar, one quilted band round his neck: taller at the back, flared at the foot where it joins the
    shoulders, with a channel round its middle, and thinning to an edge where it opens at the front."""
    ends = (0.8, math.tau - 0.8)
    ts = np.linspace(*ends, 140)[:, None]
    around = np.linspace(0.0, math.tau, 72, endpoint=False)[None, :]
    cos, sin = np.cos(around), np.sin(around)
    top = -143.2 + 3.4 * np.cos(ts)
    foot = -130.0
    mid, half = (top + foot) / 2.0, (foot - top) / 2.0
    y = mid - half * sin
    share = (sin + 1.0) / 2.0  # 0 at the foot of the band, 1 at its top
    edge = np.clip(np.minimum(ts - ends[0], ends[1] - ts) / 0.3, 0.0, 1.0) ** 0.5
    channel = 1.0 - 0.7 * np.exp(-((sin / 0.16) ** 2))
    thick = np.where(cos > 0.0, 0.8 + 0.9 * share, 0.5) * cos * channel * edge
    radius = 10.3 + 0.9 * (1.0 - share) ** 2 + 0.6 * share + thick
    rows = np.stack((radius * 1.04 * np.sin(ts), y, _NECK_Z - _NECK_DEEP * radius * np.cos(ts)), axis=2)
    _ring(m, "nylon", rows)


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


_NECK_YS = (-162.0, -147.0, -137.0, -125.0)  # his neck is a column into the skull, leaning a little forward at the top
_NECK_HALF = (6.5, 7.0, 7.5, 10.0)  # half its width, narrower than his jaw
_NECK_FRONT = (-0.5, -2.2, -3.0, -3.5)  # the z of its front
_NECK_BACK = (7.0, 8.0, 8.8, 15.0)  # and of its back, under the nape
_FIGURE = (-44, 44), (-146, -74), (-21, 27)  # the box a coat is contoured in
_STEP = 1.06


def _figure(x, y, z) -> np.ndarray:
    """A lean man's chest, sloping shoulders and arms, the shape both the blazer and the tee are cut from."""
    d = _ball(x, y, z, (0, -104, 2), (20.5, 31, 14.8))
    d = _union(d, _ball(x, y, z, (0, -124, 6.5), (15, 11, 10)), 3.5)  # the upper back, rising to the nape
    deep = (z - 2.0) / 1.45 + 2.0  # a shoulder and an arm are deeper than they are wide
    for side in (-1, 1):
        d = _union(d, _capsule(x, y, z, (side * 5, -134.5, 7.5), (side * 19, -126, 4.5), 4.4), 4.0)  # the trapezius
        d = _union(d, _capsule(x, y, deep, (side * 8, -132.5, 2), (side * 23, -125.5, 2), 5.0), 3.5)
        d = _union(d, _capsule(x, y, deep, (side * 24, -124.5, 2), (side * 27, -96, 2), 5.6), 2.5)
        d = _union(d, _capsule(x, y, deep, (side * 27, -96, 2), (side * 26, -70, -1), 5.0), 2.5)
    return d


def _blazer_shell(x, y, z) -> np.ndarray:
    """The figure with a layer of cloth on it, and the small creases cloth takes."""
    creases = 0.05 * np.sin(0.6 * x + 0.25 * y) * np.cos(0.4 * y - 0.3 * x + 0.5 * z)
    return _figure(x, y, z) - 1.1 + creases


def _vee(y) -> np.ndarray:
    """How far the blazer stands open at height ``y``: a narrow V of the tee."""
    return np.interp(y, (-146, -132, -118, -100, -76), (8.2, 7.4, 4.7, 2.8, 2.2))


def _cut(d: np.ndarray, hole: np.ndarray) -> np.ndarray:
    """``d`` with ``hole`` taken out on a soft edge, one a contour of this step can follow without a saw tooth."""
    return -_union(-d, hole, 0.9)


def blazer_field(x, y, z) -> np.ndarray:
    """The blazer as a field: open down the front and round the neck, cut off at the hem."""
    d = _blazer_shell(x, y, z)
    d = _cut(d, np.maximum(np.abs(x) - _vee(y), z + 2.5))
    d = _cut(d, np.maximum(np.hypot(x, (z - _NECK_Z) / _NECK_DEEP) - 9.4, y + 131.0))
    return np.maximum(d, y + 76.0)


def _laid(
    side: float, inner: np.ndarray, outer: np.ndarray, rows: int = 10, *, lift: tuple[float, float] = (0.35, 0.35)
) -> np.ndarray:
    """A piece of cloth on the blazer between two edges given as ``x, y``: a grid that rolls up off the chest."""
    ts = np.linspace(0.0, 1.0, rows)[:, None, None]
    flat = inner[None, :, :] * (1.0 - ts) + outer[None, :, :] * ts
    xs, ys = side * flat[..., 0].ravel(), flat[..., 1].ravel()
    zs, _ = _on_jacket(xs, ys, far=4.0, shell=_blazer_shell)
    raised = lift[0] + (lift[1] - lift[0]) * ts[:, 0] + 0.3 * np.sin(ts[:, 0] * np.pi)
    grid = np.stack((xs, ys, zs - np.broadcast_to(raised, (rows, inner.shape[0])).ravel()), axis=1)
    return grid.reshape(rows, inner.shape[0], 3)


def _cloth(m: Model, material: str, rows: np.ndarray, *, up: bool = False) -> None:
    height, width = rows.shape[:2]
    along, across = np.gradient(rows, axis=0), np.gradient(rows, axis=1)
    normals = np.cross(across, along)
    normals /= np.maximum(np.linalg.norm(normals, axis=2, keepdims=True), 1e-9)
    if normals[..., 1 if up else 2].sum() > 0.0:
        normals = -normals
    tris = []
    for r in range(height - 1):
        for c in range(width - 1):
            a, b = r * width + c, r * width + c + 1
            tris += [(a, b, b + width), (a, b + width, a + width)]
    m.surface(material, rows.reshape(-1, 3), normals.reshape(-1, 3), tris)


def _curve(points: Sequence[tuple[float, float]], count: int) -> np.ndarray:
    """``count`` points along straight runs, spaced by length, so two edges pair off along their lengths."""
    line = np.array(points, float)
    lengths = np.concatenate(((0.0,), np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))))
    at = np.linspace(0.0, lengths[-1], count)
    return np.stack((np.interp(at, lengths, line[:, 0]), np.interp(at, lengths, line[:, 1])), axis=1)


def _lapels(m: Model) -> None:
    """Notched lapels rolling from the button to the gorge, and the collar from there round the back of his neck."""
    for side in (-1.0, 1.0):
        roll = _curve([(float(_vee(y)) - 0.3, y) for y in np.linspace(-82.0, -128.5, 12)], 30)
        lapel = _curve(((2.6, -82.0), (10.5, -106.0), (16.2, -119.5), (11.4, -122.0)), 30)
        rows = _laid(side, roll, lapel, lift=(0.55, 0.45))
        _cloth(m, "blazer", rows)
        m.tube("blazer-edge", rows[-1], 0.2, 70, 6)
        m.tube("blazer-edge", rows[0], 0.14, 60, 6)
        fall_in = _curve(((7.6, -127.5), (8.6, -131.0), (9.7, -134.5)), 16)
        fall_out = _curve(((11.4, -122.0), (13.2, -127.0), (13.4, -131.0), (12.6, -134.5)), 16)
        rows = _laid(side, fall_in, fall_out, 6, lift=(0.5, 0.5))
        _cloth(m, "blazer", rows)
        m.tube("blazer-edge", rows[-1], 0.18, 40, 6)
        at = np.array(((side * 11.2, -112.5), (side * 12.8, -113.5)))
        zs, _ = _on_jacket(at[:, 0], at[:, 1], far=4.0, shell=_blazer_shell)
        m.tube("jacket-shadow", list(np.stack((at[:, 0], at[:, 1], zs - 1.0), axis=1)), 0.11, 6, 5)
    _nape_collar(m)


def _shoulder_top(x: np.ndarray, z: np.ndarray) -> np.ndarray:
    """The y of the blazer's shell under ``x, z``, coming down from above his shoulders."""
    above, inside = np.full_like(x, -152.0), np.full_like(x, -112.0)
    for _ in range(24):
        mid = (above + inside) / 2.0
        outside = _blazer_shell(x, mid, z) > 0.0
        above, inside = np.where(outside, mid, above), np.where(outside, inside, mid)
    return (above + inside) / 2.0


def _collar_stand(ts: np.ndarray) -> np.ndarray:
    """How high the collar stands by the neck at ``ts`` round it: most at the nape, and nothing at either end, where
    it lies down into the lapels."""
    share = (1.0 - np.cos(ts)) / 2.0  # 0 in front, 1 at his nape
    t = np.clip((math.pi - np.abs(ts - math.pi) - 1.0) / 0.9, 0.0, 1.0)
    return (1.2 + 3.0 * share) * t * t * (3.0 - 2.0 * t)


def _nape_collar(m: Model) -> None:
    """The collar round the back of his neck: it stands by the neck and falls on to the shoulders, and it takes its
    height from them, so it covers the edge of the neck's opening at every turn."""
    ts = np.linspace(1.0, math.tau - 1.0, 120)[:, None]
    rs = np.linspace(0.0, 1.0, 12)[None, :]
    radius = 8.5 + 5.2 * rs
    x, z = radius * 1.03 * np.sin(ts), _NECK_Z - _NECK_DEEP * radius * np.cos(ts)
    rows = np.stack((x, _shoulder_top(x, z) - 0.45 - _collar_stand(ts) * (1.0 - rs) ** 1.6, z), axis=2)
    _cloth(m, "blazer", rows, up=True)
    m.tube("blazer-edge", list(rows[:, 0]), 0.3, 120, 6)
    m.tube("blazer-edge", list(rows[:, -1]), 0.18, 120, 6)


def _ring(m: Model, material: str, rows: np.ndarray) -> None:
    along, across = np.gradient(rows, axis=0), (np.roll(rows, -1, axis=1) - np.roll(rows, 1, axis=1)) / 2.0
    normals = np.cross(across, along)
    normals /= np.maximum(np.linalg.norm(normals, axis=2, keepdims=True), 1e-9)
    middle = rows.mean(axis=1, keepdims=True)
    if ((rows - middle) * normals).sum() < 0.0:
        normals = -normals
    count, sides = rows.shape[:2]
    tris = []
    for r in range(count - 1):
        for c in range(sides):
            a, b = r * sides + c, r * sides + (c + 1) % sides
            tris += [(a, b, b + sides), (a, b + sides, a + sides)]
    m.surface(material, rows.reshape(-1, 3), normals.reshape(-1, 3), tris)


def _tee_field(x, y, z) -> np.ndarray:
    return np.maximum(_figure(x, y, z) - 0.1, y + 74.0)


def _neck_at(y) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """His neck at height ``y``: its half width, the z of its middle, and its half depth."""
    half = np.interp(y, _NECK_YS, _NECK_HALF)
    front, back = np.interp(y, _NECK_YS, _NECK_FRONT), np.interp(y, _NECK_YS, _NECK_BACK)
    return half, (front + back) / 2.0, (back - front) / 2.0


def _neck(m: Model) -> None:
    ys = np.linspace(_NECK_YS[0], _NECK_YS[-1], 40)[:, None]
    around = np.linspace(0.0, math.tau, 48, endpoint=False)[None, :]
    half, middle, deep = _neck_at(ys)
    rows = np.stack((half * np.sin(around), ys * np.ones_like(around), middle - deep * np.cos(around)), axis=2)
    _ring(m, "skin", rows)


def _neckline() -> np.ndarray:
    """Where his neck comes out of the tee, round the front and sides: the crew neck follows it."""
    out = []
    for t in np.linspace(-1.75, 1.75, 40):
        ys = np.linspace(-146.0, -122.0, 241)
        half, middle, deep = _neck_at(ys)
        xs, zs = half * math.sin(t), middle - deep * math.cos(t)
        inside = _tee_field(xs, ys, zs) < 0.0
        k = int(np.argmax(inside))
        out.append((float(xs[k]), float(ys[k]) + 0.25, float(zs[k])))
    return np.array(out)


def _tee_surface(m: Model) -> None:
    """The tee: the figure itself, with a ribbed band where his neck leaves it."""
    _neck(m)
    verts, normals, tris = contour(_tee_field, _FIGURE, _STEP)
    m.surface("shirt", verts, normals, tris)
    m.tube("shirt", list(_neckline()), 0.62, 60, 7)


@first_caps
def tee(m: Model) -> None:
    """Him in the black tee alone."""
    _tee_surface(m)


@first_caps
def blazer(m: Model) -> None:
    """The tee, and the blazer over it."""
    _tee_surface(m)
    verts, normals, tris = contour(blazer_field, _FIGURE, _STEP)
    m.surface("blazer", verts, normals, tris)
    _lapels(m)


@first_caps
def puffer(m: Model) -> None:
    """The quilted puffer: a neck, the tee, the jacket, its zip, seams and collar."""
    _neck(m)
    m.ell("shirt", (0, -109, 1), (22.3, 32.5, 11.9))
    verts, normals, tris = contour(jacket, ((-44, 44), (-146, -76), (-19, 20)), _STEP)
    m.surface("nylon", verts, normals, tris)
    _seams(m)
    _collar(m)


@first_caps
def body(m: Model) -> None:
    """Everything of him below the head, as he stands by default: the tee and the blazer."""
    blazer(m)
