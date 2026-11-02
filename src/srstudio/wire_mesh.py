"""The wire car as a real 3D model: welded meshes with smooth normals, for the engine's own 3D pass.

The wire car draws a car as quads (``Car.masks``, each with the material it is made of). This module turns the same
quads into triangle meshes in the sculpt's scene units (a metre is a hundred units, y down, z away from the lens), so a
scene can put the car in a world, light it, shoot it with a real camera and paint over what the camera sees. Nothing
here projects: the perspective, the shadows and the depth are the engine's.

- Vertices are welded by position and each corner takes the average normal of the faces round it that lie within
  :data:`CREASE` degrees of its own face, so a bonnet is smooth and a door's edge is not.
- A surface is made outward from a spine through the middle of the car (a body) or from its axle (a tyre), so a mesh is
  consistent whichever way its quads were wound.
- The wheels are parts of their own, placed at their hubs, so a scene turns each one about its axle. A wheel has a rim
  built here (a barrel, a hub and as many spokes as the car has), because the wire car draws those as lines only.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .clay import Mesh
from .wire_car import Car, WireCarError, make_car
from .wire_jet import Jet, WireJetError, make_jet
from .wire_view import MATERIALS, WireError

__all__ = [
    "CREASE",
    "SCENE_UNITS",
    "CarModel",
    "JetModel",
    "Part",
    "WireMeshError",
    "car_model",
    "jet_model",
    "smooth_mesh",
]

CREASE = 38.0  # degrees: faces that meet at a sharper angle keep a visible edge
SCENE_UNITS = 100.0  # a metre in the scene's units
EPS = 1e-12
# The material a wire kind is made of in a scene, by the number of its kind (``wire_view.MATERIALS``).
KIND_MATERIAL = {name: f"car-{name}" for name in MATERIALS}
RIM_MATERIAL = "car-alloy"
JET_MATERIAL = {name: f"jet-{name}" for name in ("paint", "dark", "trim", "leather")}


class WireMeshError(WireError):
    """A model that cannot be made into a mesh."""


@dataclass(frozen=True, eq=False)
class Part:
    """One mesh of a model and where its own origin is, in scene units from the model's origin. A wheel's origin is its
    hub, so turning it about that point turns it about its axle."""

    name: str
    material: str
    mesh: Mesh
    at: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True, eq=False)
class CarModel:
    """A car in scene units: its parts, the anchors a person sits at, and its wheels (name -> hub, radius, side)."""

    parts: tuple[Part, ...]
    anchors: dict[str, tuple[float, float, float]]
    wheels: dict[str, tuple[tuple[float, float, float], float, float]]
    length: float
    width: float


def to_scene(point: Sequence[float]) -> tuple[float, float, float]:
    """A point of the wire car (metres, y up, z across) in the sculpt's scene units (y down, z away from the lens)."""
    x, y, z = point
    return (SCENE_UNITS * x, -SCENE_UNITS * y, -SCENE_UNITS * z)


def smooth_mesh(quads: Sequence[Sequence[Sequence[float]]], material: str, outward, *, crease: float = CREASE) -> Mesh:
    """The quads (four corners each, in order round) as one mesh of triangles with smooth normals, in scene units.
    ``outward(centre)`` is the direction the surface faces at a face's centre, and each face is turned to it."""
    if not 0.0 < crease < 90.0:
        raise WireMeshError(f"a crease is an angle above 0 and below 90 degrees, got {crease!r}")
    if not material:
        raise WireMeshError("a mesh needs a material")
    pts = np.asarray([[to_scene(p) for p in quad] for quad in quads], float).reshape(-1, 4, 3)
    if not len(pts):
        raise WireMeshError(f"no quads to make a {material} mesh from")
    if not np.isfinite(pts).all():
        raise WireMeshError(f"a {material} quad has a corner that is not a finite number")
    # The face normal of each quad from its diagonals, turned to face outward; the area is its length.
    raw = np.cross(pts[:, 2] - pts[:, 0], pts[:, 3] - pts[:, 1]) / 2.0
    area = np.linalg.norm(raw, axis=1)
    keep = area > EPS
    pts, raw, area = pts[keep], raw[keep], area[keep]
    if not len(pts):
        raise WireMeshError(f"every {material} quad has no area")
    unit = raw / area[:, None]
    centre = pts.mean(axis=1)
    out = np.array([outward(c) for c in centre], float)
    flip = np.einsum("ij,ij->i", unit, out) < 0
    unit[flip] *= -1.0
    cos = math.cos(math.radians(crease))
    corners: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for face, quad in enumerate(pts):
        for corner in quad:
            corners[tuple(np.round(corner, 3).astype(int))].append(face)  # a thousandth of a unit: welded
    normals = np.zeros_like(pts)
    for face, quad in enumerate(pts):
        for k, corner in enumerate(quad):
            around = corners[tuple(np.round(corner, 3).astype(int))]
            sharing = [g for g in around if unit[g] @ unit[face] >= cos]
            blend = (unit[sharing] * area[sharing, None]).sum(axis=0)
            length = np.linalg.norm(blend)
            normals[face, k] = blend / length if length > EPS else unit[face]
    count = len(pts)
    base = np.arange(count) * 4
    triangles = np.stack([base, base + 1, base + 2, base, base + 2, base + 3], axis=1).reshape(count, 2, 3)
    # a triangle winds the way the face is turned: swap two corners where the quad was wound against its normal
    wound = np.einsum("ij,ij->i", raw / area[:, None], unit) < 0
    triangles[wound] = triangles[wound][:, :, [0, 2, 1]]
    return Mesh(material, pts.reshape(-1, 3), normals.reshape(-1, 3), triangles.reshape(-1, 3))


def _solids(quads: Sequence[Sequence[Sequence[float]]], otherwise):
    """Where each quad faces: out of its own solid when it belongs to a closed one, whatever shape that solid is, so a
    seat is wound as a seat and not by where it sits in the car. A quad of an open sheet asks ``otherwise``.

    Winding spreads from face to face across shared edges, which needs no idea of the shape, and a piece's signed
    volume then says which way round all of it is.
    """
    pts = np.asarray([[to_scene(p) for p in quad] for quad in quads], float).reshape(-1, 4, 3)
    _, ids = np.unique(np.round(pts.reshape(-1, 3), 3), axis=0, return_inverse=True)
    rounds = [_round(corners) for corners in ids.ravel().reshape(-1, 4).tolist()]
    raw = np.cross(pts[:, 2] - pts[:, 0], pts[:, 3] - pts[:, 1])
    edges: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for face, walk in enumerate(rounds):
        for a, b in walk:
            edges[min(a, b), max(a, b)].append((face, 1 if a < b else -1))
    facing: dict[tuple[float, float, float], np.ndarray] = {}
    turned = np.zeros(len(pts), int)
    for seed in range(len(pts)):
        if turned[seed]:
            continue
        turned[seed] = 1
        stack, piece, closed = [seed], [seed], True
        while stack:
            face = stack.pop()
            for a, b in rounds[face]:
                users = edges[min(a, b), max(a, b)]
                closed &= len(users) == 2
                way = 1 if a < b else -1
                for other, other_way in users:
                    if not turned[other]:
                        turned[other] = -turned[face] * way * other_way
                        stack.append(other)
                        piece.append(other)
        if closed:
            sign = 1 if _volume(pts[piece], turned[piece]) >= 0 else -1
            for face in piece:
                facing[_where(pts[face].mean(axis=0))] = raw[face] * turned[face] * sign

    def outward(centre: np.ndarray) -> np.ndarray:
        found = facing.get(_where(centre))
        return otherwise(centre) if found is None else found

    return outward


def _round(corners: list[int]) -> list[tuple[int, int]]:
    """The edges of a face in order round, without those a fan's repeated corner leaves empty."""
    return [(a, b) for a, b in zip(corners, corners[1:] + corners[:1], strict=True) if a != b]


def _volume(faces: np.ndarray, turned: np.ndarray) -> float:
    """The signed volume of a closed piece of quads, each wound by its ``turned`` sign."""
    middle = faces.reshape(-1, 3).mean(axis=0)
    p, q, r, s = (faces[:, k] - middle for k in range(4))
    sides = np.einsum("ij,ij->i", np.cross(p, q), r) + np.einsum("ij,ij->i", np.cross(p, r), s)
    return float((sides * turned).sum())


def _where(point: np.ndarray) -> tuple[float, float, float]:
    x, y, z = np.round(point, 3).tolist()
    return (x, y, z)


def _spine(car: Car):
    """Where a point of the body faces away from: the middle line of the car, from just inside its nose to its tail."""
    xs = [p[0] for quad in car.masks for p in quad]
    low, high = min(xs) + 0.3, max(xs) - 0.3
    height = 0.55

    def outward(centre: np.ndarray) -> np.ndarray:
        x = centre[0] / SCENE_UNITS
        spine = np.array([min(max(x, low), high), -height, 0.0]) * np.array([SCENE_UNITS] * 3)
        return centre - spine

    return outward


def _axle(hub: tuple[float, float, float]):
    """A tyre faces away from its axle (the line through the hub along the car's width)."""

    def outward(centre: np.ndarray) -> np.ndarray:
        rel = centre - np.array(hub)
        return np.array([rel[0], rel[1], 0.0]) if abs(rel[0]) + abs(rel[1]) > EPS else np.array([0.0, 0.0, 1.0])

    return outward


def _rim(
    car: Car, hub: tuple[float, float, float], side: float
) -> list[tuple[str, str, list[list[tuple[float, float, float]]]]]:
    """The barrel, the hub and the spokes of a wheel, as quads in the wire car's metres about the hub's centre. ``side``
    is +1 or -1: which way the wheel's face looks across the car."""
    r = car.radius
    cx, cy, cz = hub

    def at(u: float, a: float, depth: float) -> tuple[float, float, float]:
        return (cx + r * u * math.cos(a), cy + r * u * math.sin(a), cz + side * depth)

    pieces: list[tuple[str, str, list[list[tuple[float, float, float]]]]] = []
    steps = [2 * math.pi * i / 48 for i in range(49)]
    barrel = [[at(0.72, a, d) for a in steps] for d in (0.105, 0.05, -0.02, -0.1)]
    pieces.append((RIM_MATERIAL, "round", _grid(barrel)))
    lip = [[at(u, a, d) for a in steps] for u, d in ((0.74, 0.104), (0.72, 0.114), (0.69, 0.108))]
    pieces.append((RIM_MATERIAL, "round", _grid(lip)))
    cap = [[at(u, a, 0.112) for a in steps] for u in (0.0, 0.09, 0.17)]
    pieces.append((RIM_MATERIAL, "flat", _grid(cap)))
    spokes = max(car.spokes, 3)
    quads: list[list[tuple[float, float, float]]] = []
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        w0, w1 = 0.085, 0.05  # half-width at the hub and at the rim, as an angle across the radius
        for u0, u1, d in ((0.17, 0.4, 0.098), (0.4, 0.71, 0.086)):
            f0, f1 = (w0 + (w1 - w0) * (u0 - 0.17) / 0.54), (w0 + (w1 - w0) * (u1 - 0.17) / 0.54)
            quads.append([at(u0, a - f0, d), at(u0, a + f0, d), at(u1, a + f1, d - 0.012), at(u1, a - f1, d - 0.012)])
    pieces.append((RIM_MATERIAL, "flat", quads))
    face = [[at(u, a, 0.04) for a in steps] for u in (0.0, 0.72)]  # the dark behind the spokes
    pieces.append((KIND_MATERIAL["dark"], "flat", _grid(face)))
    return pieces


def _grid(rows) -> list[list[tuple[float, float, float]]]:
    return [
        [p, q, s, r]
        for a, b in zip(rows, rows[1:], strict=False)
        for p, q, r, s in zip(a, a[1:], b, b[1:], strict=False)
    ]


def car_model(seed: str | int, *, crease: float = CREASE) -> CarModel:
    """The car seeded by ``seed`` as meshes: one per material for the body and the inside, and for each wheel a tyre and
    a rim about its hub. Scene units, the nose towards -x, the roof at -y."""
    car = make_car(seed)
    if not car.masks or not car.hubs:
        raise WireCarError(f"the car {seed!r} has no surfaces to make a model of")
    wheel_range = {part: span for part, span in car.wheel_masks.items()}
    in_wheel: set[int] = set()
    for start, end in wheel_range.values():
        in_wheel.update(range(start, end))
    by_kind: dict[str, list] = defaultdict(list)
    for i, (quad, kind) in enumerate(zip(car.masks, car.mask_kinds, strict=True)):
        if i not in in_wheel:
            by_kind[KIND_MATERIAL[MATERIALS[kind]]].append(quad)
    for name, quads in car.interior_masks.items():
        by_kind[KIND_MATERIAL["leather" if "seat" in name or "bench" in name else "trim"]].extend(quads)
    out = _spine(car)
    parts = [
        Part(f"body-{material}", material, smooth_mesh(quads, material, _solids(quads, out), crease=crease))
        for material, quads in sorted(by_kind.items())
    ]
    wheels: dict[str, tuple[tuple[float, float, float], float, float]] = {}
    for part, (axle, face) in sorted(car.hubs.items()):
        side = 1.0 if face >= 0 else -1.0
        start, end = wheel_range[part]
        centre = (axle, car.radius, face - side * 0.115)  # the middle of the tyre's width
        hub_scene = to_scene(centre)
        tyre = smooth_mesh(
            [_local(q, centre) for q in car.masks[start:end]],
            KIND_MATERIAL["tire"],
            _axle((0.0, 0.0, 0.0)),
            crease=crease,
        )
        parts.append(Part(f"{part}-tyre", KIND_MATERIAL["tire"], tyre, hub_scene))
        for n, (material, shape, quads) in enumerate(_rim(car, centre, side)):
            facing = _axle((0.0, 0.0, 0.0)) if shape == "round" else _flat(side)
            rim = smooth_mesh([_local(q, centre) for q in quads], material, facing, crease=crease)
            parts.append(Part(f"{part}-rim{n}", material, rim, hub_scene))
        wheels[part] = (hub_scene, car.radius * SCENE_UNITS, side)
    anchors = {name: to_scene(point) for name, point in car.anchors.items()}
    xs = [p[0] for quad in car.masks for p in quad]
    return CarModel(tuple(parts), anchors, wheels, (max(xs) - min(xs)) * SCENE_UNITS, car.width * SCENE_UNITS)


def _local(quad, centre) -> list[tuple[float, float, float]]:
    """A quad of the wire car with ``centre`` taken out, so a wheel's mesh is about its own origin."""
    return [(p[0] - centre[0], p[1] - centre[1], p[2] - centre[2]) for p in quad]


def _flat(side: float):
    """A rim's faces look out of the car's side the wheel is on, whatever they are made of."""

    def outward(_centre: np.ndarray) -> np.ndarray:
        return np.array([0.0, 0.0, -side])  # scene z is the car's z turned about

    return outward


@dataclass(frozen=True, eq=False)
class JetModel:
    """A jet in scene units: its parts and the anchors its pilots sit at."""

    parts: tuple[Part, ...]
    anchors: dict[str, tuple[float, float, float]]
    length: float
    wingspan: float


def _jet_outward(quads) -> object:
    """A jet part faces away from the middle line of its own height: from the axis for a body, and straight up or down
    for a wing or a tail, whose faces are thin sheets about their own plane."""
    pts = np.asarray([p for quad in quads for p in quad], float)
    middle = float(pts[:, 1].mean())
    sheet = (pts[:, 2].max() - pts[:, 2].min()) > 2.0 * (pts[:, 1].max() - pts[:, 1].min()) + 1.0

    def outward(centre: np.ndarray) -> np.ndarray:
        axis = np.array([centre[0], -SCENE_UNITS * middle, centre[2] if sheet else 0.0])
        return centre - axis

    return outward


def jet_model(seed: str | int, *, model: str | None = None, crease: float = CREASE) -> JetModel:
    """The jet seeded by ``seed`` as meshes, one per part of the airframe. Scene units; the glass canopy is left out
    (a mesh with no glass is open to the lens, which the clay-and-ink look wants)."""
    jet: Jet = make_jet(seed, model=model)
    if not jet.masks:
        raise WireJetError(f"the jet {seed!r} has no surfaces to make a model of")
    parts = []
    for name, quads in sorted(jet.masks.items()):
        if name == "Canopy glass" or not quads:
            continue
        material = JET_MATERIAL[_kind(name)]
        parts.append(
            Part(name, material, smooth_mesh(quads, material, _solids(quads, _jet_outward(quads)), crease=crease))
        )
    anchors = {name: to_scene(point) for name, point in jet.anchors.items()}
    return JetModel(tuple(parts), anchors, jet.length * SCENE_UNITS, jet.wingspan * SCENE_UNITS)


def _kind(part: str) -> str:
    if part.startswith("Cockpit seat"):
        return "leather"
    if part.startswith(("Cockpit", "Canopy")):
        return "trim"
    return "dark" if part.startswith("Exhaust") else "paint"
