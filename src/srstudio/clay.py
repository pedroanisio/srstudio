"""Clay: small procedural geometry for path-traced plates, baked to meshes (ADR 0068).

A clay character is modelled here so that it can be path-traced once and composited, and a rigid object seen from
more than one angle is modelled here for :mod:`srstudio.proxy` (ADR 0091). :class:`Model` is a sketchbook of the
shapes such a character is made of, ellipsoids, rounded
boxes, rods, tubes and sweeps, built in centimetre-like scene units with y down and z away from the lens. Every shape
is baked to triangles at once, in the frame :meth:`Model.at` holds, and :meth:`Model.meshes` merges them by material.

Baking instead of using the engine's primitives is what makes a head turn cheap and exact: a whole head becomes one
mesh per material about its neck, and a pose is two rotations on the placed object (:mod:`srstudio.plates`). It also
means the same model gives the same bytes on every build, so a mesh can be named by its digest.
"""

from __future__ import annotations

import enum
import functools
import hashlib
import math
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Concatenate, ParamSpec, TypeVar

import numpy as np

from . import checks
from .errors import SrstudioError

__all__ = [
    "Caps",
    "ClayError",
    "Mesh",
    "Model",
    "bezier",
    "first_caps",
    "normal_tile",
    "obj_bytes",
    "planar",
    "superellipse",
    "thumbed",
    "knit",
]

Point = Sequence[float] | np.ndarray
Points = Sequence[Point] | np.ndarray
SEGMENTS = 64  # round the long way, on every ellipsoid and cylinder
CORNER = 6  # samples across a rounded box's corner
OBJ_SCALE = (
    0.01,
    -0.01,
    -0.01,
)  # scene units to the engine's OBJ axes: a metre to a hundred units, y up, z to the lens
_NORMAL_FLIP = (1.0, -1.0, -1.0)


class ClayError(SrstudioError, ValueError):
    """Geometry that cannot be built: a shape of no size, a curve of one point, a mesh that indexes nothing."""


@dataclass(frozen=True, eq=False)
class Mesh:
    """Triangles in one material, in scene units: ``uvs`` only on a surface that carries a printed label."""

    material: str
    vertices: np.ndarray
    normals: np.ndarray
    triangles: np.ndarray
    uvs: np.ndarray | None = None

    @cached_property
    def obj(self) -> bytes:
        return _write_obj(self)

    @cached_property
    def sha256(self) -> str:
        return hashlib.sha256(self.obj).hexdigest()


def _rows(prefix: str, rows: np.ndarray) -> str:
    clean = np.round(rows, 7) + 0.0  # no "-0.0000000": a zero is one zero in the digest
    return "".join(prefix + " ".join(f"{v:.7f}" for v in row) + "\n" for row in clean.tolist())


def _write_obj(mesh: Mesh) -> bytes:
    uv = mesh.uvs is not None
    faces = mesh.triangles + 1
    tris = "".join("f " + " ".join(f"{i}/{i}/{i}" if uv else f"{i}//{i}" for i in tri) + "\n" for tri in faces.tolist())
    text = _rows("v ", mesh.vertices * np.array(OBJ_SCALE)) + _rows("vn ", mesh.normals * np.array(_NORMAL_FLIP))
    if mesh.uvs is not None:
        text += _rows("vt ", mesh.uvs)
    return (text + "s 1\n" + tris).encode()


def obj_bytes(mesh: Mesh) -> bytes:
    """``mesh`` as a Wavefront OBJ in the engine's axes, the same bytes on every build."""
    return mesh.obj


_P = ParamSpec("_P")
_R = TypeVar("_R")


def first_caps(build: Callable[Concatenate[Model, _P], _R]) -> Callable[Concatenate[Model, _P], _R]:
    """``build(m, ...)`` baking its tube caps :attr:`Caps.FIRST`: the builder of an approved version that was approved
    before the cap fix. The model's winding comes back as it was, and ``pinned_caps`` names the winding kept."""

    @functools.wraps(build)
    def pinned(m: Model, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with m.caps(Caps.FIRST):
            return build(m, *args, **kwargs)

    pinned.pinned_caps = Caps.FIRST  # type: ignore[attr-defined]
    return pinned


def bezier(points: Sequence[Point], n: int = 32) -> np.ndarray:
    """``n`` samples along the Bézier curve of ``points``, by de Casteljau."""
    p = np.array(points, float)
    if len(p) < 2:
        raise ClayError(f"a curve needs at least 2 points, got {len(p)}")
    out = []
    for t in np.linspace(0.0, 1.0, n):
        q = p.copy()
        while len(q) > 1:
            q = q[:-1] * (1 - t) + q[1:] * t
        out.append(q[0])
    return np.array(out)


def _unit(v: np.ndarray, what: str) -> np.ndarray:
    size = float(np.linalg.norm(v))
    if size == 0.0:
        raise ClayError(f"{what} has no direction")
    return v / size


def _spin_z(degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    return np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])


def _spin_y(degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    return np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])


def _sizes(size: Point, what: str) -> np.ndarray:
    values = np.array(size, float)
    if len(values) != 3 or not (np.isfinite(values).all() and (values > 0).all()):
        raise ClayError(f"{what} needs three sizes above 0, got {size!r}")
    return values


def _sheet(rows: int, cols: int, wrap: bool) -> list[tuple[int, int, int]]:
    """The triangles of a grid of ``rows`` by ``cols`` vertices, closed round the columns when ``wrap``."""
    tris = []
    for r in range(rows - 1):
        for c in range(cols if wrap else cols - 1):
            a, b = r * cols + c, r * cols + (c + 1) % cols
            d, e = a + cols, b + cols
            tris += [(a, b, e), (a, e, d)]
    return tris


class Caps(enum.Enum):
    """How a tube's starting cap is wound. ``OUTWARD`` agrees with the cap's normal, and every new drawing takes it.
    ``FIRST`` is the winding the drawings approved before that fix were baked with: an approved version keeps the mesh
    bytes it was approved with (ADR 0047), so its builders bake ``FIRST`` and a new version of the part takes
    ``OUTWARD``. Only the starting cap's triangle order differs; vertices and normals are the same."""

    FIRST = "first"
    OUTWARD = "outward"


class Model:
    """Shapes baked as they are built: see the module's notes. Meshes come out merged by material, in a fixed order."""

    def __init__(self) -> None:
        self.caps_winding = Caps.OUTWARD
        self._spin = np.eye(3)
        self._shift = np.zeros(3)
        self._scale = 1.0
        self._parts: dict[str, list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]]] = {}

    @contextmanager
    def at(self, x: float = 0, y: float = 0, z: float = 0, yaw: float = 0, scale: float = 1) -> Iterator[Model]:
        """Build inside a frame moved to ``(x, y, z)``, turned ``yaw`` degrees about the vertical and scaled."""
        held = self._spin, self._shift, self._scale
        self._spin, self._shift, self._scale = _spin_y(yaw), np.array([x, y, z], float), float(scale)
        try:
            yield self
        finally:
            self._spin, self._shift, self._scale = held

    @contextmanager
    def caps(self, winding: Caps) -> Iterator[Model]:
        """Build with tube caps wound ``winding`` (:class:`Caps`), and wind them as before afterwards."""
        if not isinstance(winding, Caps):
            raise ClayError(f"a cap winding is one of {[c.name for c in Caps]}, got {winding!r}")
        held, self.caps_winding = self.caps_winding, winding
        try:
            yield self
        finally:
            self.caps_winding = held

    def _add(self, material: str, verts: np.ndarray, normals: np.ndarray, tris, uvs: np.ndarray | None = None) -> None:
        if not (isinstance(material, str) and material):
            raise ClayError(f"a shape needs a material, got {material!r}")
        triangles = np.array(tris, int).reshape(-1, 3)
        if len(verts) != len(normals) or (uvs is not None and len(uvs) != len(verts)):
            raise ClayError(f"{len(verts)} vertices, {len(normals)} normals: every vertex needs one of each")
        if len(triangles) and (triangles.min() < 0 or triangles.max() >= len(verts)):
            raise ClayError(f"a triangle indexes past the {len(verts)} vertices of a {material} shape")
        placed = verts @ self._spin.T * self._scale + self._shift
        turned = normals @ self._spin.T
        self._parts.setdefault(material, []).append((placed, turned, triangles, uvs))

    def surface(self, material: str, verts: Points, normals: Points, tris, uvs=None) -> None:
        """Triangles exactly as given."""
        points, facing = np.array(verts, float).reshape(-1, 3), np.array(normals, float).reshape(-1, 3)
        if not (np.isfinite(points).all() and np.isfinite(facing).all()):
            raise ClayError(f"a {material} surface has a vertex or a normal that is not a number")
        self._add(material, points, facing, tris, None if uvs is None else np.array(uvs, float).reshape(-1, 2))

    def _shell(self, material: str, p: Point, size: np.ndarray, spin: np.ndarray, last: float) -> None:
        """An ellipsoid from its top down to the polar angle ``last``."""
        rows, cols = SEGMENTS // 2 + 1, SEGMENTS
        polar = np.linspace(0.0, last, rows)[:, None]
        around = np.linspace(0.0, math.tau, cols, endpoint=False)[None, :]
        unit = np.stack(
            (np.sin(polar) * np.sin(around), -np.cos(polar) * np.ones_like(around), np.sin(polar) * np.cos(around)),
            axis=2,
        ).reshape(-1, 3)
        verts = unit * size
        normals = unit / size
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        self._add(material, verts @ spin.T + np.array(p, float), normals @ spin.T, _sheet(rows, cols, True))

    def ell(self, material: str, p: Point, size: Point, rotation: float = 0, rotation_y: float = 0) -> None:
        """An ellipsoid of radii ``size``, turned ``rotation`` degrees (+x towards +y) and then ``rotation_y``."""
        self._shell(material, p, _sizes(size, "an ellipsoid"), _spin_y(rotation_y) @ _spin_z(rotation), math.pi)

    def lid(self, material: str, p: Point, size: Point, share: float, lower: bool = False) -> None:
        """The top ``share`` of an ellipsoid's height, 0 to 1: an eyelid over an eye; ``lower`` takes it from below."""
        if not (checks.number(share) and 0.0 < share <= 1.0):
            raise ClayError(f"a lid covers a share of the eye above 0 and up to 1, got {share!r}")
        spin = _spin_z(180.0) if lower else np.eye(3)
        self._shell(material, p, _sizes(size, "a lid"), spin, math.acos(1.0 - 2.0 * share))

    def box(self, material: str, p: Point, size: Point, radius: float = 0, rotation: float = 0) -> None:
        """A box, its corners rounded by ``radius``, turned ``rotation`` degrees."""
        half = _sizes(size, "a box") / 2.0
        spin = _spin_z(rotation)
        r = min(float(radius), float(np.min(half)) * 0.99)
        verts: list[np.ndarray] = []
        normals: list[np.ndarray] = []
        tris: list[tuple[int, int, int]] = []
        for axis in range(3):
            a, b = [j for j in range(3) if j != axis]
            for sign in (-1.0, 1.0):
                start = len(verts)
                across = self._samples(half[a], r)
                along = self._samples(half[b], r)
                for v in along:
                    for u in across:
                        q = np.zeros(3)
                        q[axis], q[a], q[b] = sign * half[axis], u, v
                        core = np.clip(q, -half + r, half - r)
                        n = _unit(q - core, "a box's face") if r else _flat(axis, sign)
                        verts.append(core + n * r if r else q)
                        normals.append(n)
                cols = len(across)
                tris += [(start + t[0], start + t[1], start + t[2]) for t in _sheet(len(along), cols, False)]
        at = np.array(p, float)
        self._add(material, np.array(verts) @ spin.T + at, np.array(normals) @ spin.T, tris)

    @staticmethod
    def _samples(half: float, r: float) -> np.ndarray:
        if not r:
            return np.array([-half, half])
        return np.unique(np.r_[np.linspace(-half, -half + r, CORNER), 0.0, np.linspace(half - r, half, CORNER)])

    def _ring_body(self, material: str, centres: np.ndarray, us, vs, radii: np.ndarray, sides: int, wide=1.0) -> None:
        """A skin of ``sides`` sides round ``centres``, closed at both ends."""
        rows = len(centres)
        around = np.linspace(0.0, math.tau, sides, endpoint=False)
        verts, normals = [], []
        for j in range(rows):
            for a in around:
                n = us[j] * math.cos(a) + vs[j] * math.sin(a)
                verts.append(centres[j] + radii[j] * (us[j] * math.cos(a) + vs[j] * math.sin(a) * wide))
                normals.append(n)
        tris = _sheet(rows, sides, True)
        ends = (0, -1)
        for end, row in zip(ends, (0, rows - 1), strict=True):
            hub = len(verts)
            tangent = centres[min(row + 1, rows - 1)] - centres[max(row - 1, 0)]
            verts.append(centres[end])
            normals.append(_unit(tangent, "a tube") * (-1.0 if row == 0 else 1.0))
            cap = [(hub, row * sides + i, row * sides + (i + 1) % sides) for i in range(sides)]
            # The starting cap faces against the path tangent. Its normal and
            # triangle winding must agree, including after OBJ axis conversion;
            # Caps.FIRST keeps the order approved drawings were baked with.
            outward = row == 0 and self.caps_winding is Caps.OUTWARD
            tris += [(a, c, b) for a, b, c in cap] if outward else cap
        self._add(material, np.array(verts), np.array(normals), tris)

    def rod(self, material: str, a: Point, b: Point, r: float) -> None:
        """A straight round bar from ``a`` to ``b``."""
        start, stop = np.array(a, float), np.array(b, float)
        axis = _unit(stop - start, "a rod")
        u = _unit(np.cross(axis, (0.0, 0.0, 1.0) if abs(axis[2]) < 0.95 else (1.0, 0.0, 0.0)), "a rod")
        v = np.cross(axis, u)
        centres = np.array([start, stop])
        self._ring_body(material, centres, [u, u], [v, v], np.array([r, r], float), 24)

    def cylinder(self, material: str, p: Point, r: float, height: float) -> None:
        """An upright cylinder centred on ``p``."""
        at = np.array(p, float)
        self.rod(material, at + (0.0, height / 2.0, 0.0), at - (0.0, height / 2.0, 0.0), r)

    def capsule(self, material: str, a: Point, b: Point, r: float) -> None:
        self.rod(material, a, b, r)
        self.ell(material, a, (r, r, r))
        self.ell(material, b, (r, r, r))

    def ribbon(self, material: str, path: Points, radii: float | Sequence[float], sides: int = 10) -> None:
        """A round tube through exactly the points of ``path``, ``radii`` one size or one per point."""
        line = np.array(path, float).reshape(-1, 3)
        if len(line) < 2:
            raise ClayError(f"a ribbon needs at least 2 points, got {len(line)}")
        n = len(line)
        size = np.full(n, float(radii)) if isinstance(radii, int | float) else np.array(radii, float)
        if len(size) != n:
            raise ClayError(f"a ribbon of {n} points has {len(size)} radii")
        us, vs = [], []
        for j in range(n):
            tangent = _unit(line[min(j + 1, n - 1)] - line[max(j - 1, 0)], "a ribbon")
            ref = np.array([1.0, 0.0, 0.0]) if abs(float(tangent[2])) > 0.95 else np.array([0.0, 0.0, 1.0])
            u = _unit(np.cross(tangent, ref), "a ribbon")
            us.append(u)
            vs.append(np.cross(tangent, u))
        self._ring_body(material, line, us, vs, size, sides)

    def tube(self, material: str, points: Sequence[Point], r: float = 2.0, n: int = 32, sides: int = 10) -> None:
        """A round tube along the Bézier curve of ``points``."""
        self.ribbon(material, bezier(points, n), float(r), sides)

    def sweep(
        self,
        material: str,
        control: Sequence[Point],
        radii: Sequence[float],
        depth: float = 1.0,
        *,
        n: int = 40,
        sides: int = 24,
    ) -> None:
        """A limb along the curve of ``control``, its radius eased through ``radii``, squashed to ``depth`` front to
        back, in ``n`` rings of ``sides``: where two limbs cross near the lens, more of both keeps the join smooth."""
        path = bezier(control, n)
        us, vs = [], []
        for j in range(n):
            tangent = _unit(path[min(j + 1, n - 1)] - path[max(j - 1, 0)], "a sweep")
            u = _unit(np.cross(tangent, (0.0, 0.0, 1.0)), "a sweep")
            us.append(u)
            vs.append(np.cross(tangent, u))
        size = np.interp(np.arange(n) / (n - 1), np.linspace(0.0, 1.0, len(radii)), radii)
        self._ring_body(material, path, us, vs, size, sides, depth)

    def loft(self, xs: Points, ring: Callable, assign: Callable) -> None:
        """Rings along x with both ends capped: ``ring(x)`` gives a ring's z and y, and ``assign(centroid, normal,
        row, column)`` names each quad's material, or None to leave it open."""
        if not len(xs):
            raise ClayError("a loft needs at least one ring")
        rows = [ring(float(x)) for x in np.asarray(xs, float)]
        v = np.array(
            [[(x, y, z) for z, y in zip(r[0], r[1], strict=True)] for x, r in zip(xs, rows, strict=True)], float
        )
        v = np.concatenate([np.array(_closing(v[0])[::-1]), v, np.array(_closing(v[-1]))])
        n = _grid_normals(v)
        flip = np.sum(n * (v - v.mean(axis=1, keepdims=True))) < 0
        n = -n if flip else n
        nr, nc = v.shape[:2]
        points, normals = v.reshape(-1, 3), n.reshape(-1, 3)
        parts: dict[str, list] = {}
        for i in range(nr - 1):
            for j in range(nc):
                a, b, c, d = i * nc + j, i * nc + (j + 1) % nc, (i + 1) * nc + (j + 1) % nc, (i + 1) * nc + j
                name = assign((points[a] + points[c]) / 2, normals[a], i, j)
                if name:
                    parts.setdefault(name, []).extend([(a, c, b), (a, d, c)] if flip else [(a, b, c), (a, c, d)])
        for name, triangles in parts.items():
            self.surface(name, points, normals, triangles)

    def _capped(self, material: str, rows: Sequence[np.ndarray]) -> None:
        v = np.array(rows, float)
        start, end = v[0].mean(0), v[-1].mean(0)
        v = np.concatenate([np.repeat(start[None, None], v.shape[1], 1), v, np.repeat(end[None, None], v.shape[1], 1)])
        n = _grid_normals(v)
        n = -n if np.sum(n * (v - v.mean(axis=1, keepdims=True))) < 0 else n
        nr, nc = v.shape[:2]
        triangles = []
        for i in range(nr - 1):
            for j in range(nc):
                a, b, c, d = i * nc + j, i * nc + (j + 1) % nc, (i + 1) * nc + (j + 1) % nc, (i + 1) * nc + j
                triangles += [(a, b, c), (a, c, d)]
        self.surface(material, v.reshape(-1, 3), n.reshape(-1, 3), triangles)

    def strut(
        self, material: str, path: Points, width: float | Sequence[float], thick: float, out: Point, n: float = 4.0
    ) -> None:
        """A flat bar along ``path``, ``width`` across and ``thick`` deep, its face toward ``out``; ``n`` squares off
        its section."""
        line = np.array(path, float)
        if len(line) < 2:
            raise ClayError(f"a strut needs a path of two points, got {len(line)}")
        face = _unit(np.array(out, float), "a strut's face")
        widths = np.asarray(width, float)
        if widths.ndim and len(widths) != len(line):
            raise ClayError(f"a strut of {len(line)} points needs one width or one each, got {len(widths)}")
        along = np.gradient(line, axis=0)
        u, w = superellipse(28, n)
        rows = []
        for point, step, wide in zip(line, along, np.broadcast_to(widths, (len(line),)), strict=True):
            t = _unit(step, "a strut's path")
            side = _unit(np.cross(t, face), "a strut running along its face")
            rows.append(point + np.outer(u * wide / 2, side) + np.outer(w * thick / 2, np.cross(side, t)))
        self._capped(material, rows)

    def revolve(self, material: str, profile: Points, sides: int = 64) -> None:
        """A surface of revolution about the local z axis: ``profile`` rows are (radius, z)."""
        p = np.array(profile, float)
        if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2 or p[:, 0].min() < 0:
            raise ClayError(f"a revolved profile needs two rows of radius and z, radii not negative, got {profile!r}")
        if sides < 3:
            raise ClayError(f"a revolved surface needs three sides, got {sides}")
        angles = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        v = np.array([[(r * math.cos(a), r * math.sin(a), z) for a in angles] for r, z in p])
        n = _grid_normals(v)
        n = -n if np.sum(n * (v * np.array([1, 1, 0]))) < 0 else n
        triangles = []
        for i in range(len(p) - 1):
            for j in range(sides):
                a, b = i * sides + j, i * sides + (j + 1) % sides
                c, d = (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j
                triangles += [(a, b, c), (a, c, d)]
        self.surface(material, v.reshape(-1, 3), n.reshape(-1, 3), triangles)

    def faceplate(self, material: str, p: Point, w: float, h: float) -> None:
        """A printed flat facing the lens, as thin as paint."""
        x, y, z = p
        verts = [
            (x - w / 2, y - h / 2, z),
            (x + w / 2, y - h / 2, z),
            (x + w / 2, y + h / 2, z),
            (x - w / 2, y + h / 2, z),
        ]
        uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        self.surface(material, verts, [(0.0, 0.0, -1.0)] * 4, [(0, 1, 2), (0, 2, 3)], uvs)

    def curved_label(self, material: str, r: float, y0: float, y1: float, arc: float = 1.7) -> None:
        """A printed band round an upright cylinder of radius ``r``, from ``y0`` to ``y1`` over ``arc`` radians."""
        n = 40
        angles = np.linspace(-arc / 2, arc / 2, n)
        verts, normals, uvs = [], [], []
        for j, y in enumerate((y0, y1)):
            for i, a in enumerate(angles.tolist()):
                verts.append((r * math.sin(a), y, -r * math.cos(a)))
                normals.append((math.sin(a), 0.0, -math.cos(a)))
                uvs.append((i / (n - 1), 1.0 - j))
        tris = [t for i in range(n - 1) for t in ((i, i + n, i + n + 1), (i, i + n + 1, i + 1))]
        self.surface(material, verts, normals, tris, uvs)

    def meshes(self) -> tuple[Mesh, ...]:
        """One mesh per material, sorted by material."""
        out = []
        for material in sorted(self._parts):
            pieces = self._parts[material]
            offsets = np.cumsum([0, *(len(piece[0]) for piece in pieces[:-1])])
            printed = any(piece[3] is not None for piece in pieces)
            out.append(
                Mesh(
                    material,
                    np.concatenate([piece[0] for piece in pieces]),
                    np.concatenate([piece[1] for piece in pieces]),
                    np.concatenate([piece[2] + at for piece, at in zip(pieces, offsets.tolist(), strict=True)]),
                    np.concatenate([p[3] if p[3] is not None else np.zeros((len(p[0]), 2)) for p in pieces])
                    if printed
                    else None,
                )
            )
        return tuple(out)


def superellipse(m: int, n: float, power: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """``m`` points round a unit superellipse: ``n`` squares it off across, ``power`` (``n`` by default) up and down."""
    up = n if power is None else power
    if m < 3 or n <= 0 or up <= 0:
        raise ClayError(f"a superellipse needs three points and powers above zero, got {m}, {n} and {power}")
    theta = np.linspace(0, 2 * np.pi, m, endpoint=False)
    c, s = np.cos(theta), np.sin(theta)
    return np.sign(c) * np.abs(c) ** (2 / n), np.sign(s) * np.abs(s) ** (2 / up)


def _grid_normals(v: np.ndarray) -> np.ndarray:
    n = np.cross(np.gradient(v, axis=0), np.roll(v, -1, 1) - np.roll(v, 1, 1))
    return n / np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-9)


def _closing(row: np.ndarray) -> list[np.ndarray]:
    centre = row.mean(0)
    return [centre + (row - centre) * k for k in (0.75, 0.45, 0.15, 0.0)]


def _flat(axis: int, sign: float) -> np.ndarray:
    n = np.zeros(3)
    n[axis] = sign
    return n


def planar(mesh: Mesh, tile: float) -> Mesh:
    """``mesh`` with texture coordinates laid along the axis each vertex faces, one tile every ``tile`` units."""
    if not (checks.number(tile) and tile > 0):
        raise ClayError(f"a tile has a size above 0, got {tile!r}")
    x, y, z = mesh.vertices.T
    facing = np.abs(mesh.normals).argmax(axis=1)[:, None]
    uvs = np.where(facing == 2, np.stack((x, y), 1), np.where(facing == 1, np.stack((x, z), 1), np.stack((z, y), 1)))
    return Mesh(mesh.material, mesh.vertices, mesh.normals, mesh.triangles, uvs / tile)


def _hashed(size: int, seed: int) -> np.ndarray:
    """A square of white noise from integer arithmetic alone, so a numeric library's update cannot change a digest."""
    x = (np.arange(size * size, dtype=np.uint64) + np.uint64(seed) * np.uint64(1 << 40)) * np.uint64(0x9E3779B97F4A7C15)
    x = (x ^ (x >> np.uint64(29))) * np.uint64(0xBF58476D1CE4E5B9)
    x = x ^ (x >> np.uint64(32))
    return (x % np.uint64(1 << 20)).astype(float).reshape(size, size) / (1 << 19) - 1.0


def normal_tile(height: np.ndarray, strength: float) -> np.ndarray:
    """The RGBA normal map of a repeating ``height`` field."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    length = np.sqrt(dx * dx + dy * dy + 1.0)
    out = np.empty((*height.shape, 4), np.uint8)
    out[..., 0] = np.round((-dx / length + 1.0) * 127.5)
    out[..., 1] = np.round((dy / length + 1.0) * 127.5)
    out[..., 2] = np.round((1.0 / length + 1.0) * 127.5)
    out[..., 3] = 255
    return out


def _blur(field: np.ndarray, sigma: float) -> np.ndarray:
    """``field`` blurred on its repeating plane, through the Fourier domain."""
    fy, fx = np.fft.fftfreq(field.shape[0]), np.fft.fftfreq(field.shape[1])
    gain = np.exp(-2.0 * (math.pi * sigma) ** 2 * (fy[:, None] ** 2 + fx[None, :] ** 2))
    return np.fft.ifft2(np.fft.fft2(field) * gain).real


def thumbed(size: int, seed: int) -> np.ndarray:
    """A repeating height field of a clay surface: soft thumb dents, finer tool strokes and a little grit."""
    dents = _blur(_hashed(size, seed), size / 22.0)
    strokes = _blur(_hashed(size, seed + 1), size / 110.0)
    grit = _blur(_hashed(size, seed + 2), size / 340.0)
    field = dents / dents.std() + 0.3 * strokes / strokes.std() + 0.07 * grit / grit.std()
    return field / np.abs(field).max()


def knit(size: int, stitches: int) -> np.ndarray:
    """A repeating height field of plain knit, ``stitches`` to the side."""
    y, x = np.mgrid[0:size, 0:size] * math.tau * stitches / size
    wales = np.abs(np.sin((x + np.where(np.sin(y) > 0, math.pi / 2, 0.0)) / 2.0))
    return np.sqrt(wales) * (0.75 + 0.25 * np.abs(np.sin(y)))
